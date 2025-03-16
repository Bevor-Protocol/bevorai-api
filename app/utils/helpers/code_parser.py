import json
import re

from solidity_parser import parser as solidity_parser

from app.db.models import Contract
from app.utils.logger import get_logger
from app.utils.schema.response import StaticAnalysisTokenResult

logger = get_logger("api")


class SourceCodeParser:

    def __init__(self, source_input: dict):
        self.proxy_contract = source_input.get("Implementation", "")
        self.is_proxy = self.proxy_contract != ""
        self.contract_name = source_input.get("ContractName")

        source_code = source_input.get("SourceCode")

        if isinstance(source_code, str):
            # Check if it's a double-braced JSON (Etherscan format)
            source_code = source_code.strip(" '")
            if source_code.startswith("{{") and source_code.endswith("}}"):
                source_code = source_code[1:-1]
            try:
                # Try to parse as JSON
                parsed_json = json.loads(source_code)
                self.is_object = True
                self.raw_content = parsed_json
            except json.JSONDecodeError:
                # Not JSON, treat as raw Solidity code
                self.is_object = False
                self.raw_content = source_code
        else:
            # Already a dictionary
            self.is_object = True
            self.raw_content = source_code

    @classmethod
    def from_contract_instance(cls, contract: Contract):
        """
        Create a SourceCodeParser instance directly from raw source code string
        without needing to create a source_input dictionary.
        """
        instance = cls.__new__(cls)
        instance.proxy_contract = None
        instance.is_proxy = contract.is_proxy
        instance.contract_name = contract.contract_name
        instance.is_object = False
        instance.raw_content = contract.raw_code
        instance.source = contract.raw_code
        return instance

    def extract_raw_code(self):
        if not self.is_object:
            self.source = self.raw_content
            return self.source

        agg_contract = ""
        for k, v in self.raw_content["sources"].items():
            agg_contract += f"// File: {k}\n\n"
            agg_contract += v["content"]
            agg_contract += "\n\n"

        agg_contract = agg_contract.strip()
        self.source = agg_contract

    # DEPRECATED
    def generate_ast(self):
        if not self.source:
            raise NotImplementedError("must call extract raw code")

        code = self.source
        code = code.replace("\\'", "___SINGLE_QUOTE___")
        code = code.replace('\\"', "___DOUBLE_QUOTE___")

        code = code.replace("\\n", "\n")
        code = code.replace("\\t", "\t")
        code = code.replace("\\r", "\r")
        code = code.replace("\r\n", "\n")

        code = re.sub(
            r"(\w+(?:\.\w+)*){value:\s*([^}]+)}(\([^)]*\))",
            r"\1\3 /* value: \2 */",
            code,
        )

        code = re.sub(r"assembly\s*{[^}]*}", "", code, flags=re.DOTALL)

        # Replace storage pointers with direct access
        code = re.sub(r"\b(\w+)\s+storage\s+\$\s*=\s*\w+\(\);", "", code)
        code = re.sub(r"\$\.(\w+)", r"\1", code)

        # Replace custom errors with require statements
        code = re.sub(
            r"revert\s+(\w+)\(([^)]*)\);", r'require(false, "\1 error");', code
        )

        code = code.replace("___SINGLE_QUOTE___", "'")
        code = code.replace("___DOUBLE_QUOTE___", '"')
        if code.startswith("\ufeff"):
            code = code[1:]

        try:
            ast = solidity_parser.parse(code)
            self.ast = ast
        except Exception as err:
            logger.exception(err)
            self.ast = None

    # DEPRECATED
    def analyze_contract(self) -> StaticAnalysisTokenResult:
        """
        Analyzes contract AST for various security and functionality characteristics.
        Returns a dictionary of analysis results.
        """
        if not self.ast:
            raise NotImplementedError("must call generate_ast first")

        results = {
            "is_mintable": {"internal_mint": False, "public_mint": False},
            "is_honeypot": False,
            "can_steal_fees": False,
            "can_self_destruct": False,
            "has_proxy_functions": False,
            "has_allowlist": False,
            "has_blocklist": False,
            "can_terminate_transactions": False,
        }

        def traverse_nodes(nodes):
            for node in nodes:
                if node.get("type") == "ContractDefinition":
                    subnodes = node.get("subNodes", [])
                    for node in subnodes:
                        if node.get("type") == "FunctionDefinition":
                            name = node.get("name", "").lower()
                            visibility = node.get("visibility", "")
                            body = str(node.get("body", {}))

                            # Mintable checks
                            if name == "mint" and visibility in ["public", "external"]:
                                results["is_mintable"]["public_mint"] = True
                            elif name == "_mint":
                                results["is_mintable"]["internal_mint"] = True
                            elif (
                                visibility in ["public", "external"] and "_mint" in body
                            ):
                                results["is_mintable"]["public_mint"] = True

                            # Honeypot checks
                            if ("require" in body and "transfer" in body) or (
                                "revert" in body and "transfer" in body
                            ):
                                results["is_honeypot"] = True

                            # Fee stealing checks
                            if any(
                                x in name for x in ["withdraw", "claim", "collect"]
                            ) and visibility in ["public", "external"]:
                                results["can_steal_fees"] = True

                            # Self-destruct checks
                            if "selfdestruct" in body or "suicide" in body:
                                results["can_self_destruct"] = True

                            # Proxy function checks
                            if "delegatecall" in body or "callcode" in body:
                                results["has_proxy_functions"] = True

                            # Transaction termination checks
                            if "assert" in body or "revert" in body:
                                results["can_terminate_transactions"] = True

                        # Check variable names for allow/blocklists
                        name = str(node.get("name", "")).lower()
                        if any(
                            x in name for x in ["whitelist", "allowlist", "allowed"]
                        ):
                            results["has_allowlist"] = True
                        if any(x in name for x in ["blacklist", "blocklist", "banned"]):
                            results["has_blocklist"] = True
                elif isinstance(node, dict):
                    for value in node.values():
                        if isinstance(value, list):
                            traverse_nodes(value)

        traverse_nodes(self.ast.get("children", []))

        # Final mintable check combining internal and public results
        results["is_mintable"] = (
            results["is_mintable"]["internal_mint"]
            and results["is_mintable"]["public_mint"]
        )

        return StaticAnalysisTokenResult(**results)
