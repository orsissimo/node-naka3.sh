#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import logger
from utils.stacks.hiro_api import HiroAPI


def test_and_capture_responses():
    """Test all Hiro API endpoints and capture full responses."""
    api = HiroAPI()

    # Prepare output data
    output_data = {
        "test_timestamp": datetime.now().isoformat(),
        "base_url": api.base_url,
        "endpoints_tested": {},
        "summary": {},
    }

    logger.header("TESTING ALL HIRO API ENDPOINTS WITH RESPONSE CAPTURE")

    # Test 1: Status
    logger.info("1. Testing get_status()...")
    try:
        status = api.get_status()
        output_data["endpoints_tested"]["get_status"] = {
            "endpoint": "/extended",
            "method": "GET",
            "success": True,
            "response": status.model_dump()
            if hasattr(status, "model_dump")
            else status.__dict__,
        }
        logger.success(f"Status: {status.status}")
    except Exception as e:
        output_data["endpoints_tested"]["get_status"] = {
            "endpoint": "/extended",
            "method": "GET",
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_status failed: {e}")

    # Test 2: Recent transactions
    logger.info("2. Testing get_transaction_list()...")
    txs = None
    try:
        txs = api.get_transaction_list(limit=5)
        output_data["endpoints_tested"]["get_transaction_list"] = {
            "endpoint": "/extended/v1/tx/",
            "method": "GET",
            "parameters": {"limit": 5},
            "success": True,
            "response": txs.model_dump()
            if hasattr(txs, "model_dump")
            else txs.__dict__,
        }
        logger.success(f"Found {len(txs.results)} transactions")
    except Exception as e:
        output_data["endpoints_tested"]["get_transaction_list"] = {
            "endpoint": "/extended/v1/tx/",
            "method": "GET",
            "parameters": {"limit": 5},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_transaction_list failed: {e}")

    # Test 3: Multiple transactions (use real tx IDs from above)
    tx_ids = []
    if txs and txs.results:
        logger.info("3. Testing get_tx_list_details()...")
        try:
            tx_ids = [tx.tx_id for tx in txs.results[:2]]
            details = api.get_tx_list_details(tx_ids)
            output_data["endpoints_tested"]["get_tx_list_details"] = {
                "endpoint": "/extended/v1/tx/multiple",
                "method": "GET",
                "parameters": {"tx_id": tx_ids},
                "success": True,
                "response": details,
            }
            logger.success(f"Got details for {len(details)} transactions")
        except Exception as e:
            output_data["endpoints_tested"]["get_tx_list_details"] = {
                "endpoint": "/extended/v1/tx/multiple",
                "method": "GET",
                "parameters": {"tx_id": tx_ids},
                "success": False,
                "error": str(e),
            }
            logger.error(f"get_tx_list_details failed: {e}")

    # Test 4: Single transaction (use real tx ID)
    if txs and txs.results:
        logger.info("4. Testing get_transaction_by_id()...")
        try:
            tx = api.get_transaction_by_id(txs.results[0].tx_id)
            output_data["endpoints_tested"]["get_transaction_by_id"] = {
                "endpoint": f"/extended/v1/tx/{txs.results[0].tx_id}",
                "method": "GET",
                "parameters": {"tx_id": txs.results[0].tx_id},
                "success": True,
                "response": tx.model_dump()
                if hasattr(tx, "model_dump")
                else tx.__dict__,
            }
            logger.success(f"Got transaction: {tx.tx_id[:16]}...")
        except Exception as e:
            output_data["endpoints_tested"]["get_transaction_by_id"] = {
                "endpoint": f"/extended/v1/tx/{txs.results[0].tx_id}",
                "method": "GET",
                "parameters": {"tx_id": txs.results[0].tx_id},
                "success": False,
                "error": str(e),
            }
            logger.error(f"get_transaction_by_id failed: {e}")

    # Test 5: Raw transaction
    if txs and txs.results:
        logger.info("5. Testing get_raw_transaction_by_id()...")
        try:
            raw = api.get_raw_transaction_by_id(txs.results[0].tx_id)
            output_data["endpoints_tested"]["get_raw_transaction_by_id"] = {
                "endpoint": f"/extended/v1/tx/{txs.results[0].tx_id}/raw",
                "method": "GET",
                "parameters": {"tx_id": txs.results[0].tx_id},
                "success": True,
                "response": raw,
                "response_length": len(raw),
            }
            logger.success(f"Got raw data: {len(raw)} chars")
        except Exception as e:
            output_data["endpoints_tested"]["get_raw_transaction_by_id"] = {
                "endpoint": f"/extended/v1/tx/{txs.results[0].tx_id}/raw",
                "method": "GET",
                "parameters": {"tx_id": txs.results[0].tx_id},
                "success": False,
                "error": str(e),
            }
            logger.error(f"get_raw_transaction_by_id failed: {e}")

    # Test 6: Contract info (use well-known contract)
    logger.info("6. Testing get_contract_by_id()...")
    contract_id = "SPV9K21TBFAK4KNRJXF5DFP8N7W46G4V9RCJDC22.btcr-pre-faktory"
    try:
        contract = api.get_contract_by_id(contract_id)
        output_data["endpoints_tested"]["get_contract_by_id"] = {
            "endpoint": f"/extended/v1/contract/{contract_id}",
            "method": "GET",
            "parameters": {"contract_id": contract_id},
            "success": True,
            "response": contract.model_dump()
            if hasattr(contract, "model_dump")
            else contract.__dict__,
        }
        logger.success(f"Got contract: {contract.contract_id}")
    except Exception as e:
        output_data["endpoints_tested"]["get_contract_by_id"] = {
            "endpoint": f"/extended/v1/contract/{contract_id}",
            "method": "GET",
            "parameters": {"contract_id": contract_id},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_contract_by_id failed: {e}")

    # Test 7: Contract events
    logger.info("7. Testing get_contract_events_by_id()...")
    try:
        events = api.get_contract_events_by_id(contract_id)
        output_data["endpoints_tested"]["get_contract_events_by_id"] = {
            "endpoint": f"/extended/v1/contract/{contract_id}/events",
            "method": "GET",
            "parameters": {"contract_id": contract_id},
            "success": True,
            "response": events.model_dump()
            if hasattr(events, "model_dump")
            else events.__dict__,
        }
        results_count = len(events.results)
        logger.success(f"Found {results_count} contract events")
    except Exception as e:
        output_data["endpoints_tested"]["get_contract_events_by_id"] = {
            "endpoint": f"/extended/v1/contract/{contract_id}/events",
            "method": "GET",
            "parameters": {"contract_id": contract_id},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_contract_events_by_id failed: {e}")

    # Test 8: Account assets
    logger.info("8. Testing get_account_assets()...")
    test_address = "SP7SX9AT5H41YGYRV8MACR1NESBYF6TRMC6P82DV"
    try:
        assets = api.get_account_assets(test_address, limit=3)
        output_data["endpoints_tested"]["get_account_assets"] = {
            "endpoint": f"/extended/v1/address/{test_address}/assets",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": True,
            "response": assets.model_dump()
            if hasattr(assets, "model_dump")
            else assets.__dict__,
        }
        logger.success(f"Found {len(assets.results)} assets")
    except Exception as e:
        output_data["endpoints_tested"]["get_account_assets"] = {
            "endpoint": f"/extended/v1/address/{test_address}/assets",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_account_assets failed: {e}")

    # Test 9: Inbound STX transfers
    logger.info("9. Testing get_account_inbound()...")
    try:
        inbound = api.get_account_inbound(test_address, limit=3)
        output_data["endpoints_tested"]["get_account_inbound"] = {
            "endpoint": f"/extended/v1/address/{test_address}/stx_inbound",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": True,
            "response": inbound.model_dump()
            if hasattr(inbound, "model_dump")
            else inbound.__dict__,
        }
        logger.success(f"Found {len(inbound.results)} inbound transfers")
    except Exception as e:
        output_data["endpoints_tested"]["get_account_inbound"] = {
            "endpoint": f"/extended/v1/address/{test_address}/stx_inbound",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_account_inbound failed: {e}")

    # Test 10: Mempool transactions
    logger.info("10. Testing get_address_mempool_transactions()...")
    try:
        mempool = api.get_address_mempool_transactions(test_address, limit=3)
        output_data["endpoints_tested"]["get_address_mempool_transactions"] = {
            "endpoint": f"/extended/v1/address/{test_address}/mempool",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": True,
            "response": mempool.model_dump()
            if hasattr(mempool, "model_dump")
            else mempool.__dict__,
        }
        logger.success(f"Found {len(mempool.results)} mempool transactions")
    except Exception as e:
        output_data["endpoints_tested"]["get_address_mempool_transactions"] = {
            "endpoint": f"/extended/v1/address/{test_address}/mempool",
            "method": "GET",
            "parameters": {"principal": test_address, "limit": 3},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_address_mempool_transactions failed: {e}")

    # Test 11: Account nonces
    logger.info("11. Testing get_account_nonces()...")
    try:
        nonces = api.get_account_nonces(test_address)
        output_data["endpoints_tested"]["get_account_nonces"] = {
            "endpoint": f"/extended/v1/address/{test_address}/nonces",
            "method": "GET",
            "parameters": {"principal": test_address},
            "success": True,
            "response": nonces.model_dump()
            if hasattr(nonces, "model_dump")
            else nonces.__dict__,
        }
        logger.success(f"Next nonce: {nonces.possible_next_nonce}")
    except Exception as e:
        output_data["endpoints_tested"]["get_account_nonces"] = {
            "endpoint": f"/extended/v1/address/{test_address}/nonces",
            "method": "GET",
            "parameters": {"principal": test_address},
            "success": False,
            "error": str(e),
        }
        logger.error(f"get_account_nonces failed: {e}")

    # Test 12: Search
    logger.info("12. Testing search_by_id()...")
    try:
        search = api.search_by_id(test_address)
        output_data["endpoints_tested"]["search_by_id"] = {
            "endpoint": f"/extended/v1/search/{test_address}",
            "method": "GET",
            "parameters": {"id": test_address},
            "success": True,
            "response": search.model_dump()
            if hasattr(search, "model_dump")
            else search.__dict__,
        }
        logger.success(f"Search result: {search.found}")
    except Exception as e:
        output_data["endpoints_tested"]["search_by_id"] = {
            "endpoint": f"/extended/v1/search/{test_address}",
            "method": "GET",
            "parameters": {"id": test_address},
            "success": False,
            "error": str(e),
        }
        logger.error(f"search_by_id failed: {e}")

    # Generate summary
    total_tests = len(output_data["endpoints_tested"])
    successful_tests = sum(
        1
        for test in output_data["endpoints_tested"].values()
        if test.get("success", False)
    )
    failed_tests = total_tests - successful_tests

    output_data["summary"] = {
        "total_endpoints_tested": total_tests,
        "successful_tests": successful_tests,
        "failed_tests": failed_tests,
        "success_rate": f"{(successful_tests/total_tests)*100:.1f}%"
        if total_tests > 0
        else "0%",
    }

    # Save to output file
    output_file = "hiro_api_test_responses.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    logger.header(f"TEST COMPLETE - Full responses saved to {output_file}")
    logger.info(
        f"Summary: {successful_tests}/{total_tests} tests passed ({output_data['summary']['success_rate']})"
    )

    return output_file


if __name__ == "__main__":
    test_and_capture_responses()
