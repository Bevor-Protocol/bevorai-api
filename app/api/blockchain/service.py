import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

import httpx
from solidity_parser import parser as solidity_parser

from app.utils.clients.explorer import ExplorerClient
from app.utils.clients.web3 import Web3Client
from app.utils.types.enums import NetworkEnum
from app.utils.types.errors import NoSourceCodeError


class BlockchainService:

    async def get_gas(self) -> dict:
        explorer_client = ExplorerClient()

        async with httpx.AsyncClient() as client:
            response = await explorer_client.get_gas(
                client=client, network=NetworkEnum.ETH
            )
            response.raise_for_status()

            data = response.json()
            return data

    def __parse_source_code(self, scan_results: str):
        """
        Etherscan response object can be a plaintext response,
        or a object of dependencies.
        Extract source code of contract of interest.
        """

        if not scan_results:
            return

        scan_result = scan_results[0]
        source_code: str = scan_result.get("SourceCode")

        if not source_code.startswith("{{"):
            return source_code

        source_code = source_code[1:-1]

        contract_name = scan_result["ContractName"]
        file_name = contract_name + ".sol"

        source_code = json.loads(source_code.strip(" '"))

        for k, v in source_code["sources"].items():
            if file_name in k:
                return v["content"]

        raise NoSourceCodeError("Unable to parse source code")

    async def fetch_contract_source_code_from_explorer(
        self, client: httpx.AsyncClient, address: str, network: NetworkEnum
    ) -> dict:
        explorer_client = ExplorerClient()

        logging.info(f"SCANNING {network} for address {address}")

        obj = {
            "network": network,
            "address": address,
            "has_source_code": False,
            "found": False,
            "source_code": None,
        }

        try:
            response = await explorer_client.get_source_code(
                client=client, network=network, address=address
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if result and isinstance(result, list) and len(result) > 0:
                obj["found"] = True
                source_code = self.__parse_source_code(result)
                if source_code:
                    obj["has_source_code"] = True
                    obj["source_code"] = source_code
            raise NoSourceCodeError()
        except NoSourceCodeError:
            obj["found"] = True
        except Exception as err:
            logging.exception(err)
            pass
        finally:
            return obj

    async def get_credits(self, address: str) -> float:
        web3_client = Web3Client()
        provider = web3_client.get_deployed_provider()

        env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
        if env == "production":
            contract_address = provider.to_checksum_address(
                "0x1bdEEe6376572F1CAE454dC68a936Af56A803e96"
            )
        elif env == "staging":
            contract_address = provider.to_checksum_address(
                "0xbc14A36c59154971A8Eb431031729Af39f97eEd1"
            )
        else:
            contract_address = provider.to_checksum_address(
                "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
            )

        user_address = provider.to_checksum_address(address)

        abi = [
            {
                "inputs": [{"type": "address"}],
                "name": "apiCredits",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        contract = provider.eth.contract(address=contract_address, abi=abi)

        # Call apiCredits mapping to get credits for the address
        credits_raw = await contract.functions.apiCredits(user_address).call()
        credits = credits_raw / 10**18

        return credits


class SoliditySourceParser:
    """
    Parser for Solidity source code that can handle both raw contract code
    and JSON compiler output. Extracts source code, detects proxies, and
    provides methods for static analysis.
    """

    # Common proxy patterns to detect
    PROXY_PATTERNS = [
        r"delegatecall\s*\(",  # delegatecall usage
        r"implementation\s*\(",  # implementation function calls
        r"upgradeable",  # upgradeable keyword
        r"proxy",  # proxy keyword
        r"_implementation\s*=",  # implementation storage
        r"function\s+_setImplementation",  # implementation setter
        r"function\s+upgradeTo",  # upgrade function
    ]

    def __init__(
        self,
        source_input: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the parser with either raw Solidity code or compiler JSON output,
        and optional metadata from Etherscan.

        Args:
            source_input: Either a string containing raw Solidity code or a dictionary
                         containing compiler JSON output
            metadata: Optional metadata from Etherscan API response
        """
        # Handle string input that might be JSON
        if isinstance(source_input, str):
            # Check if it's a double-braced JSON (Etherscan format)
            if source_input.startswith("{{") and source_input.endswith("}}"):
                source_input = source_input[1:-1]

            try:
                # Try to parse as JSON
                parsed_json = json.loads(source_input)
                self.is_json_input = True
                self.raw_source = parsed_json
                self.original_input = source_input
            except json.JSONDecodeError:
                # Not JSON, treat as raw Solidity code
                self.is_json_input = False
                self.raw_source = source_input
                self.original_input = source_input
        else:
            # Already a dictionary
            self.is_json_input = True
            self.raw_source = source_input
            self.original_input = json.dumps(source_input)

        self.contracts = {}
        self.main_contract_name = None
        self.is_proxy = False
        self.ast = None
        self.full_source_code = ""

        # Store metadata from Etherscan
        self.metadata = metadata or {}

        # Extract key metadata
        self.etherscan_contract_name = self.metadata.get("ContractName", "")
        self.implementation_address = self.metadata.get("Implementation", "")
        self.is_proxy_from_etherscan = self.metadata.get("Proxy") == "1"
        self.compiler_version = self.metadata.get("CompilerVersion", "")
        self.license_type = self.metadata.get("LicenseType", "")

        self._parse_source()

        # Use Etherscan metadata to help determine main contract and proxy status
        self._apply_metadata()

    def _apply_metadata(self):
        """Apply Etherscan metadata to enhance the parser's information."""
        # Use ContractName from Etherscan to help determine main contract
        if (
            self.etherscan_contract_name
            and self.etherscan_contract_name in self.contracts
        ):
            self.main_contract_name = self.etherscan_contract_name

        # Use Proxy flag from Etherscan to help determine proxy status
        if self.is_proxy_from_etherscan:
            self.is_proxy = True

        # If Implementation address is provided, this is definitely a proxy
        if self.implementation_address:
            self.is_proxy = True

    def _parse_source(self) -> None:
        """Parse the source input and extract contracts."""
        if self.is_json_input:
            self._parse_json_output()
        else:
            self._parse_raw_source()
            self.full_source_code = self.raw_source

        # Detect if the main contract is a proxy
        if self.main_contract_name and self.main_contract_name in self.contracts:
            self.is_proxy = self._detect_proxy(self.contracts[self.main_contract_name])

    def _parse_json_output(self) -> None:
        """Parse JSON compiler output to extract contracts."""
        try:
            data = self.raw_source

            # Handle different JSON output formats
            if "sources" in data:
                # Format with sources field (like the example provided)
                for file_path, file_data in data["sources"].items():
                    if "content" in file_data:
                        source_code = file_data["content"]
                        self.full_source_code = source_code

                        # Parse the source code to extract contracts
                        try:
                            parsed = solidity_parser.parse(source_code)

                            # Extract contract definitions
                            if "children" in parsed:
                                for node in parsed["children"]:
                                    if node.get("type") == "ContractDefinition":
                                        contract_name = node.get("name", "")
                                        if contract_name:
                                            if "range" in node:
                                                start, end = node["range"]
                                                contract_source = source_code[start:end]
                                                self.contracts[contract_name] = (
                                                    contract_source
                                                )

                                                file_name = file_path.split("/")[
                                                    -1
                                                ].replace(".sol", "")
                                                if contract_name == file_name:
                                                    self.main_contract_name = (
                                                        contract_name
                                                    )
                        except Exception as e:
                            logging.warning(
                                f"Failed to parse with solidity_parser: {str(e)}"
                            )

                            # Fallback: simple regex-based extraction
                            contract_matches = re.finditer(
                                r"(contract|abstract contract|interface|library)\s+(\w+)(?:\s+is\s+[^{]+)?\s*{",  # noqa
                                source_code,
                            )

                            for match in contract_matches:
                                contract_type, contract_name = match.groups()
                                start_pos = match.start()

                                # Find the matching closing brace
                                brace_count = 0
                                end_pos = start_pos

                                for i in range(start_pos, len(source_code)):
                                    if source_code[i] == "{":
                                        brace_count += 1
                                    elif source_code[i] == "}":
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_pos = i + 1
                                            break

                                if end_pos > start_pos:
                                    self.contracts[contract_name] = source_code[
                                        start_pos:end_pos
                                    ]

                                    # Try to determine the main contract (usually the one with the same name as the file)
                                    file_name = file_path.split("/")[-1].replace(
                                        ".sol", ""
                                    )
                                    if contract_name == file_name:
                                        self.main_contract_name = contract_name

            elif "contracts" in data:
                # Standard compiler output format
                for file_path, file_contracts in data["contracts"].items():
                    for contract_name, contract_data in file_contracts.items():
                        if "source" not in contract_data and "content" in data.get(
                            "sources", {}
                        ).get(file_path, {}):
                            # Extract source from the sources section if not in contract data
                            contract_data["source"] = data["sources"][file_path][
                                "content"
                            ]
                            self.full_source_code = data["sources"][file_path][
                                "content"
                            ]

                        self.contracts[contract_name] = contract_data.get("source", "")

                        # Try to determine the main contract (usually the one with the same name as the file)
                        file_name = file_path.split("/")[-1].replace(".sol", "")
                        if contract_name == file_name:
                            self.main_contract_name = contract_name

            # If we couldn't determine the main contract, use the last one
            # (often the main contract is defined last in the file)
            if not self.main_contract_name and self.contracts:
                self.main_contract_name = list(self.contracts.keys())[-1]

        except Exception as e:
            logging.error(f"Error parsing JSON source: {str(e)}")
            raise ValueError(f"Invalid JSON source format: {str(e)}")

    def _parse_raw_source(self) -> None:
        """Parse raw Solidity source code to extract contracts."""
        try:
            source_code = self.raw_source

            # Use solidity_parser to parse the source code
            try:
                self.ast = solidity_parser.parse(source_code)

                # Extract contract names and their code
                if "children" in self.ast:
                    for node in self.ast["children"]:
                        if node.get("type") == "ContractDefinition":
                            contract_name = node.get("name", "")
                            if contract_name:
                                # Extract the contract source code based on its position
                                if "range" in node:
                                    start, end = node["range"]
                                    contract_source = source_code[start:end]
                                    self.contracts[contract_name] = contract_source

                                    # Assume the last contract is the main one
                                    self.main_contract_name = contract_name
            except Exception as e:
                logging.warning(f"Failed to parse with solidity_parser: {str(e)}")

                # Fallback: simple regex-based extraction
                contract_matches = re.finditer(
                    r"(contract|abstract contract|interface|library)\s+(\w+)(?:\s+is\s+[^{]+)?\s*{",
                    source_code,
                )

                for match in contract_matches:
                    contract_type, contract_name = match.groups()
                    start_pos = match.start()

                    # Find the matching closing brace
                    brace_count = 0
                    end_pos = start_pos

                    for i in range(start_pos, len(source_code)):
                        if source_code[i] == "{":
                            brace_count += 1
                        elif source_code[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break

                    if end_pos > start_pos:
                        self.contracts[contract_name] = source_code[start_pos:end_pos]

                        # Assume the last contract is the main one
                        self.main_contract_name = contract_name

            # If we have only one contract, it's the main one
            if len(self.contracts) == 1:
                self.main_contract_name = list(self.contracts.keys())[0]

        except Exception as e:
            logging.error(f"Error parsing raw source: {str(e)}")
            raise ValueError(f"Invalid Solidity source format: {str(e)}")

    def _detect_proxy(self, contract_source: str) -> bool:
        """
        Detect if a contract is likely a proxy based on common patterns.

        Args:
            contract_source: The source code of the contract

        Returns:
            bool: True if the contract is likely a proxy, False otherwise
        """
        for pattern in self.PROXY_PATTERNS:
            if re.search(pattern, contract_source, re.IGNORECASE):
                return True
        return False

    def get_inheritance_hierarchy(
        self, contract_name: Optional[str] = None
    ) -> List[str]:
        """
        Get the inheritance hierarchy of a contract.

        Args:
            contract_name: The name of the contract. If None, uses the main contract.

        Returns:
            List[str]: List of parent contract names
        """
        target_name = contract_name or self.main_contract_name
        if not target_name or target_name not in self.contracts:
            return []

        contract_source = self.contracts[target_name]
        parents = []

        # Extract inheritance using regex
        inheritance_match = re.search(
            r"contract\s+" + re.escape(target_name) + r"\s+is\s+([^{]+)",
            contract_source,
        )

        if inheritance_match:
            inheritance_str = inheritance_match.group(1).strip()
            # Split by commas and clean up
            parents = [parent.strip() for parent in inheritance_str.split(",")]

        return parents

    def analyze_functions(
        self, contract_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze functions in a contract.

        Args:
            contract_name: The name of the contract to analyze. If None, uses the main contract.

        Returns:
            List[Dict[str, Any]]: List of function details
        """
        target_name = contract_name or self.main_contract_name
        if not target_name or target_name not in self.contracts:
            return []

        contract_source = self.contracts[target_name]
        functions = []

        # Use regex to find function definitions
        function_pattern = r"function\s+(\w+)\s*\(([^)]*)\)\s*(public|private|internal|external)?\s*(pure|view|payable)?\s*(?:returns\s*\(([^)]*)\))?\s*(?:{|;)"

        for match in re.finditer(function_pattern, contract_source):
            name, params_str, visibility, mutability, returns_str = match.groups()

            # Parse parameters
            parameters = []
            if params_str and params_str.strip():
                param_items = [p.strip() for p in params_str.split(",")]
                for param in param_items:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = " ".join(parts[:-1])
                        param_name = parts[-1]
                        parameters.append({"type": param_type, "name": param_name})

            # Parse return parameters
            return_parameters = []
            if returns_str and returns_str.strip():
                return_items = [r.strip() for r in returns_str.split(",")]
                for ret in return_items:
                    parts = ret.split()
                    if len(parts) >= 1:
                        if len(parts) == 1:
                            return_parameters.append({"type": parts[0], "name": ""})
                        else:
                            return_type = " ".join(parts[:-1])
                            return_name = parts[-1]
                            return_parameters.append(
                                {"type": return_type, "name": return_name}
                            )

            functions.append(
                {
                    "name": name,
                    "visibility": visibility
                    or "public",  # Default visibility is public
                    "stateMutability": mutability or "",
                    "parameters": parameters,
                    "returnParameters": return_parameters,
                }
            )

        return functions

    def analyze_state_variables(
        self, contract_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze state variables in a contract.

        Args:
            contract_name: The name of the contract to analyze. If None, uses the main contract.

        Returns:
            List[Dict[str, Any]]: List of state variable details
        """
        target_name = contract_name or self.main_contract_name
        if not target_name or target_name not in self.contracts:
            return []

        contract_source = self.contracts[target_name]
        variables = []

        # Use regex to find state variable definitions
        # This pattern matches common state variable declarations
        var_pattern = r"([\w\[\]]+(?:\s+[\w\[\]]+)*)\s+(public|private|internal)?\s+(\w+)\s*(?:=\s*([^;]+))?\s*;"

        for match in re.finditer(var_pattern, contract_source):
            var_type, visibility, name, initial_value = match.groups()

            # Skip function definitions that might be caught by the regex
            if name in ["function", "constructor", "event", "modifier"]:
                continue

            variables.append(
                {
                    "type": var_type.strip(),
                    "name": name,
                    "visibility": visibility
                    or "internal",  # Default visibility is internal
                    "initialValue": initial_value.strip() if initial_value else None,
                }
            )

        return variables

    def analyze_events(
        self, contract_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze events in a contract.

        Args:
            contract_name: The name of the contract to analyze. If None, uses the main contract.

        Returns:
            List[Dict[str, Any]]: List of event details
        """
        target_name = contract_name or self.main_contract_name
        if not target_name or target_name not in self.contracts:
            return []

        contract_source = self.contracts[target_name]
        events = []

        # Use regex to find event definitions
        event_pattern = r"event\s+(\w+)\s*\(([^)]*)\)\s*;"

        for match in re.finditer(event_pattern, contract_source):
            name, params_str = match.groups()

            # Parse parameters
            parameters = []
            if params_str and params_str.strip():
                param_items = [p.strip() for p in params_str.split(",")]
                for param in param_items:
                    indexed = "indexed" in param
                    param = param.replace("indexed", "").strip()
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = " ".join(parts[:-1])
                        param_name = parts[-1]
                        parameters.append(
                            {"type": param_type, "name": param_name, "indexed": indexed}
                        )

            events.append({"name": name, "parameters": parameters})

        return events

    def analyze_security_patterns(
        self, contract_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform static analysis to detect security-related patterns in a contract.

        Args:
            contract_name: The name of the contract to analyze. If None, uses the main contract.

        Returns:
            Dict[str, Any]: Dictionary of security analysis results
        """
        target_name = contract_name or self.main_contract_name
        if not target_name or target_name not in self.contracts:
            return {}

        # Initialize results dictionary
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

        # Get functions and state variables
        functions = self.analyze_functions(target_name)
        state_vars = self.analyze_state_variables(target_name)

        logging.info(functions)
        logging.info(state_vars)

        # Check for mintable functions
        mint_function_names = ["mint", "_mint", "createToken", "generateToken"]
        for func in functions:
            name = func["name"].lower()
            visibility = func["visibility"].lower()

            # Check for mint functions
            if any(mint_name in name.lower() for mint_name in mint_function_names):
                if visibility in ["public", "external"]:
                    results["is_mintable"]["public_mint"] = True
                else:
                    results["is_mintable"]["internal_mint"] = True

            # Check for self-destruct capability
            if "selfdestruct" in name.lower() or "suicide" in name.lower():
                results["can_self_destruct"] = True

            # Check for proxy functions
            if "upgradeto" in name.lower() or "setimplementation" in name.lower():
                results["has_proxy_functions"] = True

            # Check for allowlist/blocklist functions
            if any(
                term in name.lower() for term in ["whitelist", "allowlist", "allowed"]
            ):
                results["has_allowlist"] = True

            if any(
                term in name.lower() for term in ["blacklist", "blocklist", "banned"]
            ):
                results["has_blocklist"] = True

            # Check for fee-related functions that might indicate fee stealing
            if "fee" in name.lower() and "set" in name.lower():
                results["can_steal_fees"] = True

        # Check state variables for allowlist/blocklist
        for var in state_vars:
            var_name = var["name"].lower()

            if any(term in var_name for term in ["whitelist", "allowlist", "allowed"]):
                results["has_allowlist"] = True

            if any(term in var_name for term in ["blacklist", "blocklist", "banned"]):
                results["has_blocklist"] = True

        # Get the contract source to check for specific code patterns
        contract_source = self.contracts[target_name]

        # Check for delegatecall usage (proxy pattern)
        if "delegatecall" in contract_source:
            results["has_proxy_functions"] = True

        # Check for selfdestruct usage
        if "selfdestruct" in contract_source or "suicide" in contract_source:
            results["can_self_destruct"] = True

        # Check for transaction termination patterns
        termination_indicators = [
            "require(msg.sender == owner())",
            "onlyOwner",
            "require(!isBlacklisted",
            "require(isWhitelisted",
        ]

        for indicator in termination_indicators:
            if indicator in contract_source:
                results["can_terminate_transactions"] = True
                break

        # Check for potential honeypot characteristics
        honeypot_indicators = [
            "return false",  # Transfer function that always returns false
            'revert("',  # Unexpected reverts
            "require(balanceOf(msg.sender)",  # Balance checks that might trap tokens
        ]

        # Count honeypot indicators
        honeypot_count = sum(
            1 for indicator in honeypot_indicators if indicator in contract_source
        )
        if honeypot_count >= 2:
            results["is_honeypot"] = True

        # Final mintable check combining internal and public results
        results["is_mintable"] = (
            results["is_mintable"]["internal_mint"]
            or results["is_mintable"]["public_mint"]
        )

        return results

    def get_main_contract(self) -> Optional[str]:
        """
        Get the source code of the main contract.

        Returns:
            Optional[str]: The source code of the main contract, or None if not found
        """
        if self.main_contract_name and self.main_contract_name in self.contracts:
            return self.contracts[self.main_contract_name]
        return None

    def get_contract_names(self) -> List[str]:
        """
        Get the names of all contracts in the source.

        Returns:
            List[str]: List of contract names
        """
        return list(self.contracts.keys())

    def get_contract(self, name: str) -> Optional[str]:
        """
        Get the source code of a specific contract.

        Args:
            name: The name of the contract

        Returns:
            Optional[str]: The source code of the contract, or None if not found
        """
        return self.contracts.get(name)

    def is_proxy_contract(self) -> bool:
        """
        Check if the main contract is a proxy.

        Returns:
            bool: True if the main contract is a proxy, False otherwise
        """
        return self.is_proxy

    def get_implementation_address(self) -> str:
        """
        Get the implementation address for a proxy contract.

        Returns:
            str: The implementation address, or empty string if not a proxy
        """
        return self.implementation_address

    def get_compiler_version(self) -> str:
        """
        Get the compiler version used for the contract.

        Returns:
            str: The compiler version
        """
        return self.compiler_version

    def get_license_type(self) -> str:
        """
        Get the license type of the contract.

        Returns:
            str: The license type
        """
        return self.license_type

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get all metadata from Etherscan.

        Returns:
            Dict[str, Any]: All metadata
        """
        return self.metadata

    def get_full_source_code(self) -> str:
        """
        Get the full source code from the input.

        Returns:
            str: The full source code
        """
        return self.full_source_code

    def get_original_input(self) -> str:
        """
        Get the original input string.

        Returns:
            str: The original input
        """
        return self.original_input
