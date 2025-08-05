import subprocess
import shlex
import json
from typing import List, Optional, Tuple, Dict, Any
from .colors import Colors, logger

class BlockstackCLIWrapper:
    """
    A comprehensive Python wrapper for the blockstack-cli command-line tool.
    This class provides a 1-to-1 mapping for all commands and options documented
    in the provided help text.
    """
    def __init__(self, cli_path: str = "blockstack-cli"):
        self.cli_path = cli_path

    def _run_command(self, command_parts: List[str], testnet: bool, chain_id: Optional[str]) -> Tuple[Optional[str], Optional[str], int]:
        """Internal helper to construct and execute the final command."""
        base_cmd = [self.cli_path]
        if testnet:
            base_cmd.append(f"--testnet{f'={chain_id}' if chain_id else ''}")
        
        full_command = base_cmd + command_parts
        command_str = shlex.join(full_command)
        logger.debug(f"Executing command: {command_str}")
        
        try:
            process = subprocess.run(full_command, capture_output=True, text=True, check=False)
            stdout = process.stdout.strip() if process.stdout else None
            stderr = process.stderr.strip() if process.stderr else None
            
            if process.returncode != 0:
                logger.error(f"Command failed with exit code {process.returncode}")
                if stderr:
                    logger.error(f"STDERR: {Colors.format_fail(stderr)}")
                return None, stderr, process.returncode
            
            logger.debug(f"Return Code: {process.returncode}")
            if stdout: logger.debug(f"STDOUT:\n{stdout}")
            if stderr: logger.warning(f"STDERR:\n{stderr}")
                
            return stdout, stderr, process.returncode
        except FileNotFoundError:
            logger.critical(f"Executable not found at '{self.cli_path}'. Please ensure it is installed and in your PATH.")
            return None, f"Executable not found at '{self.cli_path}'", 1
        except Exception as e:
            logger.critical(f"An unexpected error occurred: {e}")
            return None, str(e), 1

    def publish_contract(self, publisher_sk: str, fee_rate: int, nonce: int, contract_name: str, file_name: str, *, testnet: bool = True) -> List[str]:
        """Build blockstack-cli publish command - returns command array for direct execution"""
        cmd = ["blockstack-cli"]
        if testnet:
            cmd.append("--testnet")
        cmd.extend(["publish", publisher_sk, str(fee_rate), str(nonce), contract_name, file_name])
        return cmd

    def call_contract(self, origin_sk: str, fee_rate: int, nonce: int, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None, *, testnet: bool = True) -> List[str]:
        """Build blockstack-cli contract-call command - returns command array for direct execution"""
        cmd = ["blockstack-cli"]
        if testnet:
            cmd.append("--testnet")
        cmd.extend(["contract-call", origin_sk, str(fee_rate), str(nonce), contract_address, contract_name, function_name])
        if args:
            for arg in args:
                cmd.extend(["-e", arg])
        return cmd

    def generate_sk(self, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """USAGE: blockstack-cli generate-sk"""
        cmd = ["generate-sk"]
        stdout, _, retcode = self._run_command(cmd, testnet, chain_id)
        if retcode == 0 and stdout: return json.loads(stdout)
        return None

    def token_transfer(self, origin_sk: str, fee_rate: int, nonce: int, recipient_address: str, amount: int, memo: Optional[str] = None, *, testnet: bool = True) -> List[str]:
        """Build blockstack-cli token-transfer command - returns command array for direct execution"""
        cmd = ["blockstack-cli"]
        if testnet:
            cmd.append("--testnet")
        cmd.extend(["token-transfer", origin_sk, str(fee_rate), str(nonce), recipient_address, str(amount)])
        if memo:
            cmd.append(memo)
        return cmd

    def get_addresses(self, secret_key: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """USAGE: blockstack-cli addresses [secret-key-hex]"""
        cmd = ["addresses", secret_key]
        stdout, _, retcode = self._run_command(cmd, testnet, chain_id)
        if retcode == 0 and stdout: return json.loads(stdout)
        return None

    def _decode_helper(self, command: str, hex_data: str, *, testnet: bool, chain_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Internal helper for all decode commands."""
        cmd = [command, hex_data]
        stdout, _, retcode = self._run_command(cmd, testnet, chain_id)
        if retcode == 0 and stdout:
            try: return json.loads(stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from stdout for command '{command}'.")
                return None
        return None

    def decode_tx(self, tx_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Usage: blockstack-cli decode-tx [transaction-hex-or-stdin]"""
        return self._decode_helper("decode-tx", tx_hex, testnet=testnet, chain_id=chain_id)

    def decode_header(self, header_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Usage: blockstack-cli decode-header [block-path-or-stdin]"""
        return self._decode_helper("decode-header", header_hex, testnet=testnet, chain_id=chain_id)

    def decode_block(self, block_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Usage: blockstack-cli decode-block [block-path-or-stdin]"""
        return self._decode_helper("decode-block", block_hex, testnet=testnet, chain_id=chain_id)

    def decode_microblock(self, microblock_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Usage: blockstack-cli decode-microblock [microblock-path-or-stdin]"""
        return self._decode_helper("decode-microblock", microblock_hex, testnet=testnet, chain_id=chain_id)
        
    def decode_microblocks(self, microblocks_hex: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Usage: blockstack-cli decode-microblocks [microblocks-path-or-stdin]"""
        return self._decode_helper("decode-microblocks", microblocks_hex, testnet=testnet, chain_id=chain_id)