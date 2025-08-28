#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from .logger import logger
from .config import AccountInfo, TxStatus, ApiResult, ApiError

class StacksCoreAPI:
    """
    A 1:1 Python port of the Stacks 3.0+ RPC API, covering all endpoints from 
    the provided OpenAPI specification with automatic JSON→object parsing and 
    centralized error handling. This class provides direct access to all API 
    endpoints without additional abstraction layers.
    """
    def __init__(self, base_url: str = "http://localhost:20443", auth_token: Optional[str] = None):
        self.base_url = base_url
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({'Authorization': f'Basic {auth_token}'})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make raw API request and return response object for centralized handling"""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"-> {method} {url}")
        
        try:
            response = self.session.request(method, url, **kwargs, timeout=20)
            # Add visual indicator based on status code with colors
            if 200 <= response.status_code < 300:
                from .logger import Colors
                indicator = f"{Colors.GREEN}✓{Colors.RESET}"
            elif 400 <= response.status_code < 500:
                from .logger import Colors
                indicator = f"{Colors.RED}✗{Colors.RESET}"
            elif 500 <= response.status_code < 600:
                from .logger import Colors
                indicator = f"{Colors.RED}✗{Colors.RESET}"
            else:
                from .logger import Colors
                indicator = f"{Colors.YELLOW}?{Colors.RESET}"
            
            from .logger import Colors
            logger.debug(f"<- Status: {response.status_code} {indicator}")
            return response
        except requests.exceptions.RequestException as e:
            logger.critical(f"An HTTP request error occurred: {str(e)}")
            raise e
    
    def handle_api_response(self, response: requests.Response) -> Any:
        """
        Centralized handler for all API responses - matches ignore-this pattern.
        On success (200), intelligently parses and returns the body content.
        On failure, parses detailed JSON error and raises descriptive RuntimeError.
        """
        if response.status_code != 200:
            try:
                error_details = response.json()
                reason = error_details.get('reason', 'Unknown API error')
                reason_data = error_details.get('reason_data', {})
                error_message = f"API Error ({response.status_code}): {reason} - Details: {reason_data}"
            except json.JSONDecodeError:
                error_message = f"API Error ({response.status_code}): {response.text}"
            
            logger.error(f"API call failed: {error_message}")
            raise RuntimeError(error_message)

        # Handle successful responses
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json()
        elif 'application/octet-stream' in content_type:
            return response.content
        else:
            return response.text.strip('"')
    
    def _parse_hex_balance(self, balance_hex: str) -> int:
        """Convert hex balance string to integer."""
        if balance_hex.startswith('0x'):
            return int(balance_hex, 16)
        return int(balance_hex)

    # --- V2 Transactions, Accounts, and Info ---
    def get_info(self) -> 'NodeInfo':
        """GET /v2/info - Get Core API information as typed object."""
        response = self._make_request('GET', '/v2/info')
        data = self.handle_api_response(response)
        return NodeInfo(
            peer_version=data['peer_version'],
            pox_consensus=data['pox_consensus'], 
            burn_block_height=data['burn_block_height'],
            stable_pox_consensus=data['stable_pox_consensus'],
            stable_burn_block_height=data['stable_burn_block_height'],
            server_version=data['server_version'],
            network_id=data['network_id'],
            parent_network_id=data['parent_network_id'],
            stacks_tip_height=data['stacks_tip_height'],
            stacks_tip=data['stacks_tip'],
            stacks_tip_consensus_hash=data['stacks_tip_consensus_hash'],
            genesis_chainstate_hash=data['genesis_chainstate_hash'],
            unanchored_tip=data.get('unanchored_tip'),
            unanchored_seq=data.get('unanchored_seq'),
            tenure_height=data['tenure_height'],
            exit_at_block_height=data.get('exit_at_block_height'),
            is_fully_synced=data['is_fully_synced'],
            node_public_key=data.get('node_public_key'),
            node_public_key_hash=data.get('node_public_key_hash'),
            affirmations=data.get('affirmations'),
            last_pox_anchor=data.get('last_pox_anchor'),
            stackerdbs=data.get('stackerdbs')
        )

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> Optional[str]:
        """POST /v2/transactions - Broadcast a raw transaction."""
        response = self._make_request('POST', '/v2/transactions', data=raw_tx_bytes, headers={'Content-Type': 'application/octet-stream'})
        return self.handle_api_response(response)

    def get_account_info(self, principal: str, *, proof: Optional[int] = None, tip: Optional[str] = None) -> AccountInfo:
        """GET /v2/accounts/{principal} - Get account information as typed object."""
        params = {k: v for k, v in {'proof': proof, 'tip': tip}.items() if v is not None}
        response = self._make_request('GET', f'/v2/accounts/{principal}', params=params)
        data = self.handle_api_response(response)
        
        # Parse balance from hex to int
        balance = self._parse_hex_balance(data.get('balance', '0x0'))
        
        return AccountInfo(
            address=principal,
            balance=balance,
            nonce=data['nonce']
        )
        
    def get_pox_info(self, *, tip: Optional[str] = None) -> 'PoxInfo':
        """GET /v2/pox - Get Proof of Transfer (PoX) information as typed object."""
        response = self._make_request('GET', '/v2/pox', params={'tip': tip} if tip else {})
        data = self.handle_api_response(response)
        
        # Parse current and next cycles
        current_cycle_data = data['current_cycle']
        next_cycle_data = data['next_cycle']
        
        current_cycle = PoxCycle(
            id=current_cycle_data['id'],
            min_threshold_ustx=current_cycle_data['min_threshold_ustx'],
            stacked_ustx=current_cycle_data['stacked_ustx'],
            is_pox_active=current_cycle_data['is_pox_active']
        )
        
        next_cycle = PoxCycle(
            id=next_cycle_data['id'],
            min_threshold_ustx=next_cycle_data['min_threshold_ustx'],
            stacked_ustx=next_cycle_data['stacked_ustx'],
            is_pox_active=next_cycle_data['is_pox_active']
        )
        
        return PoxInfo(
            contract_id=data['contract_id'],
            pox_activation_threshold_ustx=data['pox_activation_threshold_ustx'],
            first_burnchain_block_height=data['first_burnchain_block_height'],
            current_burnchain_block_height=data['current_burnchain_block_height'],
            prepare_phase_block_length=data['prepare_phase_block_length'],
            reward_phase_block_length=data['reward_phase_block_length'],
            reward_slots=data['reward_slots'],
            rejection_fraction=data.get('rejection_fraction'),
            total_liquid_supply_ustx=data['total_liquid_supply_ustx'],
            current_cycle=current_cycle,
            next_cycle=next_cycle,
            epochs=data['epochs'],
            min_amount_ustx=data['min_amount_ustx'],
            prepare_cycle_length=data['prepare_cycle_length'],
            reward_cycle_id=data['reward_cycle_id'],
            reward_cycle_length=data['reward_cycle_length'],
            rejection_votes_left_required=data.get('rejection_votes_left_required'),
            next_reward_cycle_in=data['next_reward_cycle_in'],
            contract_versions=data['contract_versions']
        )

    # --- V2 Smart Contracts and Clarity ---
    def call_read_only_function(self, contract_address: str, contract_name: str, function_name: str, sender: str, arguments: List[str], *, tip: Optional[str] = None) -> Optional[Dict]:
        """POST /v2/contracts/call-read/{...} - Call a read-only function."""
        endpoint = f'/v2/contracts/call-read/{contract_address}/{contract_name}/{function_name}'
        response = self._make_request('POST', endpoint, json={'sender': sender, 'arguments': arguments}, params={'tip': tip} if tip else {})
        return self.handle_api_response(response)

    def get_contract_source(self, contract_address: str, contract_name: str, *, proof: Optional[int] = None, tip: Optional[str] = None) -> Optional[Dict]:
        """GET /v2/contracts/source/{...} - Get contract source code."""
        params = {k: v for k, v in {'proof': proof, 'tip': tip}.items() if v is not None}
        response = self._make_request('GET', f'/v2/contracts/source/{contract_address}/{contract_name}', params=params)
        return self.handle_api_response(response)

    def get_contract_interface(self, contract_address: str, contract_name: str, *, tip: Optional[str] = None) -> Optional[Dict]:
        """GET /v2/contracts/interface/{...} - Get contract interface."""
        response = self._make_request('GET', f'/v2/contracts/interface/{contract_address}/{contract_name}', params={'tip': tip} if tip else {})
        return self.handle_api_response(response)

    def get_map_entry(self, contract_address: str, contract_name: str, map_name: str, key_hex_json_string: str, *, proof: Optional[int] = None, tip: Optional[str] = None) -> Optional[Dict]:
        """POST /v2/map_entry/{...} - Get a data-map entry."""
        endpoint = f'/v2/map_entry/{contract_address}/{contract_name}/{map_name}'
        params = {k: v for k, v in {'proof': proof, 'tip': tip}.items() if v is not None}
        response = self._make_request('POST', endpoint, json=key_hex_json_string, params=params)
        return self.handle_api_response(response)
    
    def get_constant_value(self, contract_address: str, contract_name: str, constant_name: str, *, tip: Optional[str] = None) -> Optional[Dict]:
        """POST /v2/constant_val/{...} - Get the value of a constant."""
        endpoint = f'/v2/constant_val/{contract_address}/{contract_name}/{constant_name}'
        response = self._make_request('POST', endpoint, params={'tip': tip} if tip else {})
        return self.handle_api_response(response)

    def get_is_trait_implemented(self, contract_address: str, contract_name: str, trait_contract_address: str, trait_contract_name: str, trait_name: str, *, tip: Optional[str] = None) -> Optional[Dict]:
        """GET /v2/traits/{...} - Check if a contract implements a trait."""
        endpoint = f'/v2/traits/{contract_address}/{contract_name}/{trait_contract_address}/{trait_contract_name}/{trait_name}'
        response = self._make_request('GET', endpoint, params={'tip': tip} if tip else {})
        return self.handle_api_response(response)
        
    def get_clarity_marf_value(self, marf_key: str, *, proof: Optional[int] = None, tip: Optional[str] = None) -> Optional[Dict]:
        """POST /v2/clarity/marf/{...} - Get the MARF value for a key."""
        params = {k: v for k, v in {'proof': proof, 'tip': tip}.items() if v is not None}
        response = self._make_request('POST', f'/v2/clarity/marf/{marf_key}', params=params)
        return self.handle_api_response(response)
        
    def get_clarity_metadata(self, contract_address: str, contract_name: str, metadata_key: str, *, tip: Optional[str] = None) -> Optional[Dict]:
        """POST /v2/clarity/metadata/{...} - Get contract metadata."""
        endpoint = f'/v2/clarity/metadata/{contract_address}/{contract_name}/{metadata_key}'
        response = self._make_request('POST', endpoint, params={'tip': tip} if tip else {})
        return self.handle_api_response(response)

    # --- V2 Fees ---
    def get_fee_rate_for_transfer(self) -> Optional[Dict]:
        """GET /v2/fees/transfer - Get estimated fee rate for STX transfers."""
        response = self._make_request('GET', '/v2/fees/transfer')
        return self.handle_api_response(response)
        
    def get_fee_estimate_for_transaction(self, transaction_payload_hex: str, *, estimated_len: Optional[int] = None) -> Optional[Dict]:
        """POST /v2/fees/transaction - Get an estimated fee for a given transaction payload."""
        payload = {'transaction_payload': transaction_payload_hex}
        if estimated_len is not None: payload['estimated_len'] = estimated_len
        response = self._make_request('POST', '/v2/fees/transaction', json=payload)
        return self.handle_api_response(response)
    
    # --- V3 Blocks, Tenures, and Transactions ---
    def get_block_by_id(self, block_id: str) -> Optional[bytes]:
        """GET /v3/blocks/{block_id} - Fetch a Nakamoto block by its ID hash."""
        response = self._make_request('GET', f'/v3/blocks/{block_id}')
        return self.handle_api_response(response)

    def get_block_by_height(self, block_height: int, *, tip: Optional[str] = None) -> Optional[bytes]:
        """GET /v3/blocks/height/{block_height} - Fetch a Nakamoto block by height."""
        response = self._make_request('GET', f'/v3/blocks/height/{block_height}', params={'tip': tip} if tip else {})
        return self.handle_api_response(response)
        
    def get_transaction_by_id(self, txid: str) -> 'TransactionDetails':
        """GET /v3/transaction/{txid} - Retrieve transaction details as typed object.
        NOTE: The OpenAPI spec incorrectly lists this as a POST endpoint. Real-world
        testing shows it is a GET endpoint. This implementation uses GET.
        """
        response = self._make_request('GET', f'/v3/transaction/{txid}')
        data = self.handle_api_response(response)
        
        return TransactionDetails(
            txid=data.get('txid', txid),
            tx_status=data.get('tx_status', 'unknown'),
            tx_type=data.get('tx_type', 'unknown'),
            receipt_time=data.get('receipt_time'),
            receipt_time_iso=data.get('receipt_time_iso')
        )
        
    def get_tenure_info(self) -> Optional[Dict]:
        """GET /v3/tenures/info - Fetch metadata about the ongoing Nakamoto tenure."""
        response = self._make_request('GET', '/v3/tenures/info')
        return self.handle_api_response(response)

    def get_tenure_blocks(self, block_id: str, *, stop: Optional[str] = None) -> Optional[bytes]:
        """GET /v3/tenures/{block_id} - Fetch a sequence of Nakamoto blocks in a tenure."""
        response = self._make_request('GET', f'/v3/tenures/{block_id}', params={'stop': stop} if stop else {})
        return self.handle_api_response(response)
        
    def get_sortitions(self, *, lookup_kind: Optional[str] = None, lookup: Optional[str] = None) -> Optional[Dict]:
        """GET /v3/sortitions/{lookup_kind}/{lookup} - Fetch information about evaluated burnchain blocks."""
        endpoint = '/v3/sortitions'
        if lookup_kind and lookup:
            endpoint += f'/{lookup_kind}/{lookup}'
        elif lookup_kind:
            endpoint += f'/{lookup_kind}'
        response = self._make_request('GET', endpoint)
        return self.handle_api_response(response)

    # --- V3 Mining and Stacking ---
    def post_block_proposal(self, block_proposal_data: Dict) -> Optional[Dict]:
        """POST /v3/block_proposal - Validate a proposed Stacks block. Requires auth."""
        response = self._make_request('POST', '/v3/block_proposal', json=block_proposal_data)
        return self.handle_api_response(response)
        
    def get_stacker_set(self, cycle_number: int) -> Optional[Dict]:
        """GET /v3/stacker_set/{cycle_number} - Fetch stacker set info for a cycle."""
        response = self._make_request('GET', f'/v3/stacker_set/{cycle_number}')
        return self.handle_api_response(response)
        
    def get_signer_block_count(self, signer_pubkey: str, cycle_number: int) -> Optional[int]:
        """GET /v3/signer/{signer}/{cycle_number} - Get number of blocks signed by a signer in a cycle."""
        response = self._make_request('GET', f'/v3/signer/{signer_pubkey}/{cycle_number}')
        resp = self.handle_api_response(response)
        return int(resp) if resp and isinstance(resp, str) and resp.isdigit() else None

@dataclass
class NodeInfo:
    """Typed node information from /v2/info endpoint."""
    peer_version: int
    pox_consensus: str
    burn_block_height: int
    stable_pox_consensus: str
    stable_burn_block_height: int
    server_version: str
    network_id: int
    parent_network_id: int
    stacks_tip_height: int
    stacks_tip: str
    stacks_tip_consensus_hash: str
    genesis_chainstate_hash: str
    unanchored_tip: Optional[str]
    unanchored_seq: Optional[int]
    tenure_height: int
    exit_at_block_height: Optional[int]
    is_fully_synced: bool
    node_public_key: Optional[str]
    node_public_key_hash: Optional[str]
    affirmations: Optional[Dict]
    last_pox_anchor: Optional[Dict]
    stackerdbs: Optional[List]

@dataclass
class PoxCycle:
    """PoX cycle information."""
    id: int
    min_threshold_ustx: int
    stacked_ustx: int
    is_pox_active: bool

@dataclass
class PoxInfo:
    """Typed PoX information from /v2/pox endpoint."""
    contract_id: str
    pox_activation_threshold_ustx: int
    first_burnchain_block_height: int
    current_burnchain_block_height: int
    prepare_phase_block_length: int
    reward_phase_block_length: int
    reward_slots: int
    rejection_fraction: Optional[int]
    total_liquid_supply_ustx: int
    current_cycle: PoxCycle
    next_cycle: PoxCycle
    epochs: List[Dict]  # Can be further typed if needed
    min_amount_ustx: int
    prepare_cycle_length: int
    reward_cycle_id: int
    reward_cycle_length: int
    rejection_votes_left_required: Optional[int]
    next_reward_cycle_in: int
    contract_versions: List[Dict]  # Can be further typed if needed

@dataclass
class TransactionDetails:
    """Transaction details from /v3/transaction endpoint."""
    txid: str
    tx_status: str  # Raw string from API
    tx_type: str
    receipt_time: Optional[int] = None
    receipt_time_iso: Optional[str] = None
    
    @property
    def status(self) -> TxStatus:
        """Get transaction status as typed enum with IDE autocompletion."""
        if self.tx_status == 'success':
            return TxStatus.SUCCESS
        elif self.tx_status == 'abort_by_response':
            return TxStatus.ABORT_BY_RESPONSE
        elif self.tx_status == 'abort_by_post_condition':
            return TxStatus.ABORT_BY_POST_CONDITION
        elif self.tx_status == 'pending':
            return TxStatus.PENDING
        else:
            return TxStatus.UNKNOWN
    # Additional fields can be added as needed

@dataclass
class StackerSet:
    """Stacker set information from /v3/stacker_set endpoint."""
    cycle_number: int
    # Additional fields based on actual response structure

@dataclass
class TenureInfo:
    """Tenure information from /v3/tenures/info endpoint."""
    consensus_hash: str
    tenure_start_block_id: str
    # Additional fields based on actual response structure


class StacksCoreAPIWrapper:
    """
    High-level wrapper around StacksCoreAPI providing convenient methods,
    error handling, and abstraction for common operations. This class provides
    the wrapper functionality mentioned in the FIXME comment.
    """
    
    def __init__(self, api: Optional['StacksCoreAPI'] = None):
        self.api = api or StacksCoreAPI()
    
    
    def get_account_info_result(self, address: str) -> ApiResult:
        """Get account info with typed error handling and result wrapper."""
        try:
            account_info = self.api.get_account_info(address)
            return ApiResult(success=True, data=account_info)
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return ApiResult(success=False, error=ApiError.NOT_FOUND, error_message=error_msg)
            elif "timeout" in error_msg.lower():
                return ApiResult(success=False, error=ApiError.TIMEOUT, error_message=error_msg)
            elif "connection" in error_msg.lower():
                return ApiResult(success=False, error=ApiError.CONNECTION_ERROR, error_message=error_msg)
            else:
                return ApiResult(success=False, error=ApiError.UNKNOWN_ERROR, error_message=error_msg)
    
    def wait_for_tx_confirmation(self, txid: str, timeout: int = 60) -> bool:
        """Wait for transaction confirmation with smart polling."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                tx_details = self.api.get_transaction_by_id(txid)
                # Use typed enum with full IDE autocompletion
                if tx_details.status in [TxStatus.SUCCESS, TxStatus.ABORT_BY_RESPONSE, TxStatus.ABORT_BY_POST_CONDITION]:
                    return tx_details.status == TxStatus.SUCCESS
                time.sleep(2)
            except Exception:
                time.sleep(3)
        
        return False
    
    def get_balance_in_stx(self, address: str) -> float:
        """Get account balance converted to STX (from microSTX)."""
        account_info = self.api.get_account_info(address)
        return account_info.balance / 1_000_000  # Convert microSTX to STX
    
    def get_block_height(self) -> int:
        """Get current block height from the Stacks API."""
        return self.api.get_info().stacks_tip_height
    
    def get_info(self) -> 'NodeInfo':
        """Get Core API information as typed object."""
        return self.api.get_info()
    
    # NOTE: UNUSED
    def safe_api_call(self, func, *args, **kwargs) -> ApiResult:
        """Safely call any API function and return typed result with error handling."""
        try:
            result = func(*args, **kwargs)
            return ApiResult(success=True, data=result)
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return ApiResult(success=False, error=ApiError.NOT_FOUND, error_message=error_msg)
            elif "timeout" in error_msg.lower():
                return ApiResult(success=False, error=ApiError.TIMEOUT, error_message=error_msg)
            elif "connection" in error_msg.lower():
                return ApiResult(success=False, error=ApiError.CONNECTION_ERROR, error_message=error_msg)
            else:
                return ApiResult(success=False, error=ApiError.UNKNOWN_ERROR, error_message=error_msg)