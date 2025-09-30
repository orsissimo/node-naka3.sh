import requests
import json
import sys

# Base URL for the Hiro Mainnet API
STACKS_API_BASE_URL = "https://api.hiro.so"

def get_transaction_json(tx_id: str):
    """
    Fetches transaction details from the Stacks API and prints only the JSON response.
    """
    api_path = f"/extended/v1/tx/{tx_id}"
    url = STACKS_API_BASE_URL + api_path

    try:
        # Make the GET request
        response = requests.get(url)
        
        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        
        # Print the JSON response directly to stdout
        # Using json.dumps to ensure it's well-formatted
        print(json.dumps(response.json(), indent=4))

    except requests.exceptions.HTTPError as http_err:
        # Handle cases like 404 Not Found for an invalid tx_id
        error_json = {
            "error": "HTTPError",
            "message": str(http_err),
            "status_code": response.status_code, # type: ignore
            "url": url
        }
        print(json.dumps(error_json, indent=4))
        sys.exit(1)
        
    except requests.exceptions.RequestException as req_err:
        # Handle other network-related errors
        error_json = {
            "error": "RequestException",
            "message": str(req_err),
            "url": url
        }
        print(json.dumps(error_json, indent=4))
        sys.exit(1)

def main():
    """
    Main function to parse command-line arguments.
    """
    if len(sys.argv) != 2:
        # Provide usage instructions as a JSON error message
        usage_error = {
            "error": "Invalid Usage",
            "message": "Please provide a single transaction ID (tx_id) as an argument.",
            "example": f"python {sys.argv[0]} 0x1f92c6c0b9e829378877e8a936a282f645800045e7f1ef550a273e970220c37f"
        }
        print(json.dumps(usage_error, indent=4), file=sys.stderr)
        sys.exit(1)

    tx_id = sys.argv[1]
    get_transaction_json(tx_id)

if __name__ == "__main__":
    main()

# transfer: 0x0349bc16678d856839efd2e90fc00a0ad3d54fcc5e6efd0ad716d1296ad5c793
# contract_call: 0xa65143e69c7f93e390ecb3c71a84feb52c8a8d6f5a131dffd0c46649ba13fbb3