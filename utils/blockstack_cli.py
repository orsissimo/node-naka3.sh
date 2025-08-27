import subprocess
import shlex
import json
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from .logger import Colors, logger

@dataclass
class SecretKeyInfo:
    """Typed response from generate-sk command."""
    secret_key: str
    public_key: str
    stacks_address: str

@dataclass 
class AddressInfo:
    """Typed response from addresses command."""
    stx_address: str
    btc_address: str

@dataclass
class TransactionResult:
    """Typed result for transaction commands."""
    tx_hex: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class CLIResult:
    """Generic typed result for CLI commands."""
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    return_code: int = 0

class BlockstackCLI:
    """
    Core 1:1 CLI executor for blockstack-cli commands with automatic 
    JSON→typed object parsing. This class provides direct access to 
    all CLI commands without additional abstraction layers.
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

    def publish_contract(self, publisher_sk: str, fee_rate: int, nonce: int, contract_name: str, file_name: str, *, testnet: bool = True) -> Optional[str]:
        """Execute blockstack-cli publish command and return transaction hex"""
        cmd = ["publish", publisher_sk, str(fee_rate), str(nonce), contract_name, file_name]
        
        stdout, stderr, returncode = self._run_command(cmd, testnet, None)
        if returncode != 0 or not stdout:
            logger.error(f"Contract publish failed: {stderr}")
            return None
        return stdout.strip()

    def call_contract(self, origin_sk: str, fee_rate: int, nonce: int, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None, *, testnet: bool = True) -> Optional[str]:
        """Execute blockstack-cli contract-call command and return transaction ID"""
        cmd = ["contract-call", origin_sk, str(fee_rate), str(nonce), contract_address, contract_name, function_name]
        if args:
            for arg in args:
                cmd.extend(["-e", arg])
        
        stdout, stderr, returncode = self._run_command(cmd, testnet, None)
        if returncode != 0 or not stdout:
            logger.error(f"Contract call failed: {stderr}")
            return None
        return stdout.strip()

    def generate_sk(self, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[SecretKeyInfo]:
        """Generate a new secret key as typed object."""
        cmd = ["generate-sk"]
        stdout, _, retcode = self._run_command(cmd, testnet, chain_id)
        if retcode == 0 and stdout:
            data = json.loads(stdout)
            return SecretKeyInfo(
                secret_key=data["secretKey"],
                public_key=data["publicKey"],
                stacks_address=data["stacksAddress"]
            )
        return None

    def token_transfer(self, origin_sk: str, fee_rate: int, nonce: int, recipient_address: str, amount: int, memo: Optional[str] = None, *, testnet: bool = True) -> Optional[str]:
        """Execute blockstack-cli token-transfer command and return transaction ID"""
        cmd = ["token-transfer", origin_sk, str(fee_rate), str(nonce), recipient_address, str(amount)]
        if memo:
            cmd.append(memo)
        
        stdout, stderr, returncode = self._run_command(cmd, testnet, None)
        if returncode != 0 or not stdout:
            logger.error(f"Token transfer failed: {stderr}")
            return None
        return stdout.strip()

    def get_addresses(self, secret_key: str, *, testnet: bool = False, chain_id: Optional[str] = None) -> Optional[AddressInfo]:
        """Get addresses from secret key as typed object."""
        cmd = ["addresses", secret_key]
        stdout, _, retcode = self._run_command(cmd, testnet, chain_id)
        if retcode == 0 and stdout:
            data = json.loads(stdout)
            return AddressInfo(
                stx_address=data["STX"],
                btc_address=data["BTC"]
            )
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


class BlockstackCLIWrapper:
    """
    High-level wrapper around BlockstackCLI providing convenient methods,
    error handling, and abstraction for common operations. This class provides
    the wrapper functionality for the CLI.
    """
    
    def __init__(self, cli: Optional['BlockstackCLI'] = None):
        self.cli = cli or BlockstackCLI()
    
    def create_new_account(self, testnet: bool = True) -> CLIResult:
        """Create a new account with safe error handling."""
        try:
            sk_info = self.cli.generate_sk(testnet=testnet)
            if sk_info:
                return CLIResult(success=True, data=sk_info)
            else:
                return CLIResult(success=False, error_message="Failed to generate secret key")
        except Exception as e:
            return CLIResult(success=False, error_message=str(e))
    
    def get_account_addresses(self, secret_key: str, testnet: bool = True) -> CLIResult:
        """Get addresses with error handling."""
        try:
            addresses = self.cli.get_addresses(secret_key, testnet=testnet)
            if addresses:
                return CLIResult(success=True, data=addresses)
            else:
                return CLIResult(success=False, error_message="Failed to get addresses")
        except Exception as e:
            return CLIResult(success=False, error_message=str(e))
    
    def transfer_tokens(self, origin_sk: str, recipient: str, amount_stx: float, memo: str = "", testnet: bool = True) -> CLIResult:
        """Transfer STX tokens with error handling and STX→microSTX conversion."""
        try:
            # Convert STX to microSTX (1 STX = 1,000,000 microSTX)
            amount_microstx = int(amount_stx * 1_000_000)
            
            # For this we need nonce and fee rate - this would typically come from the API
            # This is a simplified version
            result = self.cli.token_transfer(
                origin_sk=origin_sk,
                fee_rate=1000,  # Default fee rate
                nonce=0,        # This should be fetched from API in real use
                recipient_address=recipient,
                amount=amount_microstx,
                memo=memo if memo else None,
                testnet=testnet
            )
            
            if result:
                return CLIResult(success=True, data=TransactionResult(tx_hex=result, success=True))
            else:
                return CLIResult(success=False, error_message="Token transfer failed")
        except Exception as e:
            return CLIResult(success=False, error_message=str(e))


# Note: BlockstackCLIWrapper is now the high-level wrapper class
# BlockstackCLI is the 1:1 CLI executor with typed responses