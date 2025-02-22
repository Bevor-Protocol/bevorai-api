import requests
from solidity_parser import parser
from app.client.explorer import ExplorerClient

def generate_ast(source_code: str):
    try:
        ast = parser.parse(source_code)
        print("AST:", ast)
        return ast
    except Exception as e:
        print("Error parsing source code:", e)
        raise e
    return parser.parse(source_code)

def analyze_contract(ast: dict) -> dict:
    """
    Analyzes contract AST for various security and functionality characteristics.
    Returns a dictionary of analysis results.
    """
    results = {
        'is_mintable': {'internal_mint': False, 'public_mint': False},
        'is_honeypot': False,
        'can_steal_fees': False,
        'can_self_destruct': False,
        'has_proxy_functions': False,
        'has_allowlist': False,
        'has_blocklist': False,
        'can_terminate_transactions': False
    }

    def traverse_nodes(nodes):
        for node in nodes:
            if node.get('type') == 'ContractDefinition':
                analyze_contract_nodes(node.get('subNodes', []))
            elif isinstance(node, dict):
                for value in node.values():
                    if isinstance(value, list):
                        traverse_nodes(value)

    def analyze_contract_nodes(nodes):
        for node in nodes:
            if node.get('type') == 'FunctionDefinition':
                name = node.get('name', '').lower()
                visibility = node.get('visibility', '')
                body = str(node.get('body', {}))

                # Mintable checks
                if name == 'mint' and visibility in ['public', 'external']:
                    results['is_mintable']['public_mint'] = True
                elif name == '_mint':
                    results['is_mintable']['internal_mint'] = True
                elif visibility in ['public', 'external'] and '_mint' in body:
                    results['is_mintable']['public_mint'] = True

                # Honeypot checks
                if ('require' in body and 'transfer' in body) or ('revert' in body and 'transfer' in body):
                    results['is_honeypot'] = True

                # Fee stealing checks
                if any(x in name for x in ['withdraw', 'claim', 'collect']) and visibility in ['public', 'external']:
                    results['can_steal_fees'] = True

                # Self-destruct checks
                if 'selfdestruct' in body or 'suicide' in body:
                    results['can_self_destruct'] = True

                # Proxy function checks
                if 'delegatecall' in body or 'callcode' in body:
                    results['has_proxy_functions'] = True

                # Transaction termination checks
                if 'assert' in body or 'revert' in body:
                    results['can_terminate_transactions'] = True

            # Check variable names for allow/blocklists
            name = str(node.get('name', '')).lower()
            if any(x in name for x in ['whitelist', 'allowlist', 'allowed']):
                results['has_allowlist'] = True
            if any(x in name for x in ['blacklist', 'blocklist', 'banned']):
                results['has_blocklist'] = True

    traverse_nodes(ast.get('children', []))
    
    # Final mintable check combining internal and public results
    results['is_mintable'] = results['is_mintable']['internal_mint'] and results['is_mintable']['public_mint']
    
    return results

def process_static_eval_token(address: str):
    explorer_client = ExplorerClient()
    source = explorer_client.get_source_code(address)

    ast = generate_ast(source)
    analysis = analyze_contract(ast)

    return analysis