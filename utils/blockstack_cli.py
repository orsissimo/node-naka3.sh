import subprocess
import shlex
import json
from typing import List, Optional, Tuple, Dict, Any, TypeVar, Type
from pydantic import BaseModel, ValidationError
from .logger import logger
from .types.api import AddressInfo, SecretKeyInfo
from .types.exceptions import *

T = TypeVar("T", bound=BaseModel)


class BlockstackCLI:
    """
    Core 1:1 CLI executor for blockstack-cli commands with automatic
    JSON→typed object parsing. This class provides direct access to
    all CLI commands without additional abstraction layers.
    """

    def __init__(self, cli_path: str = "blockstack-cli"):
        self._cli_path = self._validate_cli_path(cli_path)

    def _validate_cli_path(self, cli_path: str) -> str:
        """Validate CLI path"""
        if not cli_path:
            raise ValueError("CLI path cannot be empty")
        if not isinstance(cli_path, str):
            raise TypeError("CLI path must be a string")
        # Strip whitespace and ensure no path injection
        cli_path = cli_path.strip()
        if not cli_path:
            raise ValueError("CLI path cannot be only whitespace")
        return cli_path

    @property
    def cli_path(self) -> str:
        """Get the CLI executable path (read-only)"""
        return self._cli_path

    def _parse_json_response(self, stdout: str, response_type: Type[T]) -> T:
        """
        Automatic JSON→typed object parsing.
        Raises exceptions instead of returning None for better error handling.
        """
        if not stdout or not stdout.strip():
            raise StacksValidationException(
                f"Empty or None stdout for {response_type.__name__}"
            )

        json_data = None
        try:
            # Parse JSON from stdout
            json_data = json.loads(stdout.strip())
            logger.debug(f"Parsed JSON data: {json_data}")

            # Automatic validation and object creation via Pydantic
            parsed_object = response_type.model_validate(json_data)
            logger.debug(f"Successfully created {response_type.__name__} object")
            return parsed_object

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {response_type.__name__}: {e}")
            logger.error(f"Raw stdout: {repr(stdout)}")
            raise StacksValidationException(
                f"JSON decode error for {response_type.__name__}: {e}"
            ) from e
        except ValidationError as e:
            logger.error(f"Pydantic validation error for {response_type.__name__}: {e}")
            logger.error(f"JSON data: {json_data if json_data is not None else 'N/A'}")
            raise StacksValidationException(
                f"Validation failed for {response_type.__name__}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error parsing {response_type.__name__}: {e}")
            raise StacksCLIException(
                f"Unexpected error parsing {response_type.__name__}: {e}"
            ) from e

    def _execute_command_for_hex(
        self,
        command_parts: List[str],
        testnet: bool = True,
        chain_id: Optional[str] = None,
        operation_name: str = "CLI operation",
    ) -> str:
        stdout, stderr, returncode = self._run_command(command_parts, testnet, chain_id)
        if not stdout:
            raise StacksCLIException(f"{operation_name} returned empty output")
        return stdout.strip()

    def _execute_command_for_json(
        self,
        command_parts: List[str],
        response_type: Type[T],
        testnet: bool = True,
        chain_id: Optional[str] = None,
        operation_name: str = "CLI operation",
    ) -> T:
        stdout, stderr, returncode = self._run_command(command_parts, testnet, chain_id)
        if not stdout:
            raise StacksCLIException(f"{operation_name} returned empty output")
        return self._parse_json_response(stdout, response_type)

    def _run_command(
        self, command_parts: List[str], testnet: bool, chain_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], int]:
        base_cmd = [self._cli_path]
        if testnet:
            base_cmd.append(f"--testnet{f'={chain_id}' if chain_id else ''}")

        full_command = base_cmd + command_parts
        command_str = shlex.join(full_command)
        logger.debug(f"Executing command: {command_str}")

        try:
            process = subprocess.run(
                full_command, capture_output=True, text=True, check=False
            )
            stdout = process.stdout.strip() if process.stdout else None
            stderr = process.stderr.strip() if process.stderr else None

            if process.returncode != 0:
                logger.error(f"Command failed with exit code {process.returncode}")
                if stderr:
                    logger.error(f"STDERR: {stderr}")
                raise StacksCLIException(
                    f"CLI command failed: {command_str}",
                    return_code=process.returncode,
                    stderr=stderr,
                )

            logger.debug(f"Return Code: {process.returncode}")
            if stdout:
                logger.debug(f"STDOUT:\n{stdout}")
            if stderr:
                logger.warning(f"STDERR:\n{stderr}")

            return stdout, stderr, process.returncode
        except FileNotFoundError as e:
            logger.error(
                f"Executable not found at '{self._cli_path}'. "
                f"Please ensure it is installed and in your PATH."
            )
            raise StacksCLIException(
                f"Executable not found at '{self._cli_path}'", return_code=1
            ) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise StacksCLIException(
                f"An unexpected error occurred: {e}", return_code=1
            ) from e

    def generate_contract_deploy_tx_hex(
        self,
        publisher_sk: str,
        fee_rate: int,
        nonce: int,
        contract_name: str,
        file_name: str,
        *,
        testnet: bool = True,
    ) -> str:
        """CLI: publish - Generate contract deployment transaction hex.

        File_name must be path to .clar file. Returns transaction hex for use with api.post_raw_transaction(bytes.fromhex(result)).
        """
        cmd = [
            "publish",
            publisher_sk,
            str(fee_rate),
            str(nonce),
            contract_name,
            file_name,
        ]
        return self._execute_command_for_hex(cmd, testnet, None, "Contract publish")

    def generate_contract_call_tx_hex(
        self,
        origin_sk: str,
        fee_rate: int,
        nonce: int,
        contract_address: str,
        contract_name: str,
        function_name: str,
        args: Optional[List[str]] = None,
        *,
        testnet: bool = True,
    ) -> str:
        """CLI: contract-call - Generate contract function call transaction hex.

        Args must be Clarity values (e.g. 'u100', '"hello"'). Returns transaction hex for use with api.post_raw_transaction(bytes.fromhex(result)).
        """
        cmd = [
            "contract-call",
            origin_sk,
            str(fee_rate),
            str(nonce),
            contract_address,
            contract_name,
            function_name,
        ]
        if args:
            for arg in args:
                cmd.extend(["-e", arg])
        return self._execute_command_for_hex(cmd, testnet, None, "Contract call")

    def generate_sk(
        self, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> SecretKeyInfo:
        """CLI: generate-sk - Generate a new secret key.

        Returns SecretKeyInfo with secret_key, stacks_address, and btc_address fields.
        """
        cmd = ["generate-sk"]
        return self._execute_command_for_json(
            cmd, SecretKeyInfo, testnet, chain_id, "generate-sk"
        )

    def generate_token_transfer_tx_hex(
        self,
        origin_sk: str,
        fee_rate: int,
        nonce: int,
        recipient_address: str,
        amount: int,
        memo: Optional[str] = None,
        *,
        testnet: bool = True,
    ) -> str:
        """CLI: token-transfer - Generate STX token transfer transaction hex.

        Amount is in microstx. Returns transaction hex for use with api.post_raw_transaction(bytes.fromhex(result)).
        """
        cmd = [
            "token-transfer",
            origin_sk,
            str(fee_rate),
            str(nonce),
            recipient_address,
            str(amount),
        ]
        if memo:
            cmd.append(memo)
        return self._execute_command_for_hex(cmd, testnet, None, "Token transfer")

    def get_addresses(
        self, secret_key: str, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> AddressInfo:
        """CLI: addresses - Get addresses from secret key.

        Returns AddressInfo with stacks_address and btc_address fields.
        """
        cmd = ["addresses", secret_key]
        return self._execute_command_for_json(
            cmd, AddressInfo, testnet, chain_id, "addresses command"
        )

    def _decode_helper(
        self, command: str, hex_data: str, *, testnet: bool, chain_id: Optional[str]
    ) -> Dict[str, Any]:
        hex_arg = hex_data if hex_data.startswith("0x") else f"0x{hex_data}"
        cmd = [command, hex_arg]
        stdout = self._execute_command_for_hex(
            cmd, testnet, chain_id, f"{command} command"
        )
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON from stdout for command '{command}': {e}"
            )
            logger.error(f"Raw stdout: {repr(stdout)}")
            raise StacksValidationException(
                f"JSON decode error for {command}: {e}"
            ) from e

    def decode_tx(
        self, tx_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """CLI: decode-tx - Decode a raw transaction hex.

        Hex must be without 0x prefix. Returns dict with decoded transaction structure and details.
        """
        return self._decode_helper(
            "decode-tx", tx_hex, testnet=testnet, chain_id=chain_id
        )

    # FIXME: Unused and untested for now
    def decode_header(
        self, header_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """CLI: decode-header - Decode a block header hex.

        Returns dict with decoded header information and metadata.
        """
        return self._decode_helper(
            "decode-header", header_hex, testnet=testnet, chain_id=chain_id
        )

    # FIXME: Unused and untested for now
    def decode_block(
        self, block_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """CLI: decode-block - Decode a raw block hex.

        Returns dict with decoded block structure, transactions, and metadata.
        """
        return self._decode_helper(
            "decode-block", block_hex, testnet=testnet, chain_id=chain_id
        )
