#!/usr/bin/env python3

import subprocess
import time
from typing import Dict, Any, List, Optional
from .config import (
    AccountManager,
    Miner,
    TransactionStatus,
    TestResult,
    TxStatus,
    ApiError,
    AccountInfo,
    ApiResult,
    StacksException,
    StacksAPIException,
    StacksCLIException,
    StacksNetworkException,
    StacksTimeoutException,
)
from .stacks_core_api import StacksCoreAPI, StacksCoreAPIWrapper
from .blockstack_cli import BlockstackCLIWrapper
from .logger import Colors, logger


def prepare_cli_binary(cmd: List[str]) -> bytes:
    """Prepare CLI command and return transaction binary"""
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        hex_output = result.stdout.decode().strip()
        if not hex_output:
            raise StacksCLIException("CLI command returned empty output")
        return bytes.fromhex(hex_output)
    except subprocess.CalledProcessError as e:
        raise StacksCLIException(
            f"CLI command failed: {' '.join(cmd)}",
            return_code=e.returncode,
            stderr=e.stderr.decode() if e.stderr else None,
        ) from e
    except ValueError as e:
        raise StacksCLIException(
            f"Invalid hex output from CLI command: {hex_output}"
        ) from e


def submit_cli_command(api: StacksCoreAPI, cli_cmd: List[str]) -> str:
    """Execute CLI command and submit to blockchain"""
    tx_binary = prepare_cli_binary(cli_cmd)
    return api.post_raw_transaction(tx_binary)


