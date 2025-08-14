#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any
from .logger import Colors, logger

class StacksCoreAPIWrapper:
    """
    A comprehensive Python wrapper for the Stacks 3.0+ RPC API, covering all
    endpoints from the provided OpenAPI specification and correcting for
    discrepancies between the spec and actual server behavior.
    """
    def __init__(self, base_url: str = "http://localhost:20443", auth_token: Optional[str] = None):
        self.base_url = base_url
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({'Authorization': f'Basic {auth_token}'})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make raw API request and return response object for centralized handling"""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"-> {Colors.format_header(method)} {Colors.format_grey(url)}")
        
        try:
            response = self.session.request(method, url, **kwargs, timeout=20)
            status_color_fn = Colors.format_success if 200 <= response.status_code < 300 else Colors.format_warn if response.status_code < 500 else Colors.format_fail
            logger.debug(f"<- Status: {status_color_fn(str(response.status_code))}")
            return response
        except requests.exceptions.RequestException as e:
            logger.critical(f"An HTTP request error occurred: {Colors.format_fail(str(e))}")
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
            
            logger.error(f"API call failed: {Colors.format_fail(error_message)}")
            raise RuntimeError(error_message)

        # Handle successful responses
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json()
        elif 'application/octet-stream' in content_type:
            return response.content
        else:
            return response.text.strip('"')

    # --- V2 Transactions, Accounts, and Info ---
    def get_info(self) -> Optional[Dict]:
        """GET /v2/info - Get Core API information."""
        response = self._make_request('GET', '/v2/info')
        return self.handle_api_response(response)

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> Optional[str]:
        """POST /v2/transactions - Broadcast a raw transaction."""
        response = self._make_request('POST', '/v2/transactions', data=raw_tx_bytes, headers={'Content-Type': 'application/octet-stream'})
        return self.handle_api_response(response)

    def get_account_info(self, principal: str, *, proof: Optional[int] = None, tip: Optional[str] = None) -> Optional[Dict]:
        """GET /v2/accounts/{principal} - Get account information."""
        params = {k: v for k, v in {'proof': proof, 'tip': tip}.items() if v is not None}
        response = self._make_request('GET', f'/v2/accounts/{principal}', params=params)
        return self.handle_api_response(response)
        
    def get_pox_info(self, *, tip: Optional[str] = None) -> Optional[Dict]:
        """GET /v2/pox - Get Proof of Transfer (PoX) information."""
        response = self._make_request('GET', '/v2/pox', params={'tip': tip} if tip else {})
        return self.handle_api_response(response)

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
        
    def get_transaction_by_id(self, txid: str) -> Optional[Dict]:
        """GET /v3/transaction/{txid} - Retrieve transaction details.
        NOTE: The OpenAPI spec incorrectly lists this as a POST endpoint. Real-world
        testing shows it is a GET endpoint. This implementation uses GET.
        """
        response = self._make_request('GET', f'/v3/transaction/{txid}')
        return self.handle_api_response(response)
        
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