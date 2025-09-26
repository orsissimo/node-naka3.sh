import subprocess
import shlex
import json
from typing import List, Optional, Tuple, Dict, Any, TypeVar, Type, cast
from pydantic import BaseModel
from .logger import logger
from .parsers import parse_cli_response
from .types.api import AddressInfo, SecretKeyInfo
from .types.wrappers import String
from .types.exceptions import *

T = TypeVar("T")


class BlockstackCLI:
    def __init__(self, cli_path: str = "blockstack-cli"):
        self._cli_path = self._validate_cli_path(cli_path)

    def _validate_cli_path(self, cli_path: str) -> str:
        if not cli_path:
            raise ValueError("CLI path cannot be empty")
        if not isinstance(cli_path, str):
            raise TypeError("CLI path must be a string")
        cli_path = cli_path.strip()  # Strip whitespace and ensure no path injection
        if not cli_path:
            raise ValueError("CLI path cannot be only whitespace")
        return cli_path

    @property
    def cli_path(self) -> str:
        return self._cli_path

    def _execute_command(
        self,
        command_parts: List[str],
        response_type: Type[T],
        testnet: bool = True,
        chain_id: Optional[str] = None,
        operation_name: str = "CLI operation",
    ) -> T:
        """Execute CLI command and return parsed object."""
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
            if stderr:
                logger.warning(f"STDERR:\n{stderr}")
            if stdout:
                logger.debug(f"STDOUT:\n{stdout}")
            else:
                raise StacksCLIException(f"{operation_name} returned empty output")
            if response_type is String:
                return cast(
                    T, String(stdout.strip())
                )  # FIXME: I don't like 'cast' that much
            else:
                return parse_cli_response(stdout, response_type)  # type: ignore # FIXME: Can we avoid this ignore?

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
        file_name: str,  # Path to the .clar file
        *,
        testnet: bool = True,
    ) -> String:
        """CLI: publish - Generate contract deployment transaction hex."""
        cmd = [
            "publish",
            publisher_sk,
            str(fee_rate),
            str(nonce),
            contract_name,
            file_name,
        ]
        return self._execute_command(cmd, String, testnet, None, "Publish contract")

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
    ) -> String:
        """CLI: contract-call - Generate contract function call transaction hex. Args must be Clarity values (e.g. 'u100', '"hello"')."""
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
        return self._execute_command(cmd, String, testnet, None, "Contract call")

    def generate_sk(
        self, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> SecretKeyInfo:
        """CLI: generate-sk - Generate a new secret key."""
        cmd = ["generate-sk"]
        return self._execute_command(
            cmd, SecretKeyInfo, testnet, chain_id, "Generate Secret Key"
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
    ) -> String:
        """CLI: token-transfer - Generate STX token transfer transaction hex. Amount is in microstx."""
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
        return self._execute_command(cmd, String, testnet, None, "Transfer token")

    def get_addresses(
        self, secret_key: str, *, testnet: bool = False, chain_id: Optional[str] = None
    ) -> AddressInfo:
        """CLI: addresses - Get addresses from secret key."""
        cmd = ["addresses", secret_key]
        return self._execute_command(
            cmd, AddressInfo, testnet, chain_id, "Get addresses"
        )
