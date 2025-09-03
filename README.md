cd naka3/playbooks/three-miners && ./three-miners.sh snapshot create

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 tests/example-transfer.py

---

Exception Hierarchy:
Exception
  └── StacksException (base)
      ├── StacksAPIException
      ├── StacksCLIException
      ├── StacksValidationException
      └── StacksNetworkException
          └── StacksTimeoutException

  1. StacksException (Base exception)
    - Base exception for all Stacks-related errors
    - Parent class for all other custom exceptions
  2. StacksAPIException
    - Inherits from: StacksException
    - Purpose: API-related exceptions
    - Extra attributes: status_code, error_details
    - Used for: HTTP errors, API response failures
  3. StacksCLIException
    - Inherits from: StacksException
    - Purpose: CLI-related exceptions
    - Extra attributes: return_code, stderr
    - Used for: Blockstack CLI command failures
  4. StacksValidationException
    - Inherits from: StacksException
    - Purpose: Data validation exceptions
    - Used for: Invalid data/parameter validation failures
  5. StacksNetworkException
    - Inherits from: StacksException
    - Purpose: Network/connection related exceptions
    - Used for: Network connectivity issues
  6. StacksTimeoutException
    - Inherits from: StacksNetworkException
    - Purpose: Timeout-specific exceptions
    - Used for: Operation timeouts (confirmation waits, miner startup, etc.)

---

pip packages

Pydantic is a Python library for data validation and parsing using type hints. We're using it for:
  1. Type-safe data models - All classes like Account, TransferInfo, DeploymentInfo inherit from BaseModel
  2. Automatic validation - Ensures data types are correct when creating objects
  3. IDE autocompletion - Provides full IntelliSense support
  4. JSON serialization/deserialization - Easy conversion to/from JSON

Black is an opinionated formatter that automatically fixes code style issues like spacing, line breaks, and quote consistency.
  Common usage:
  - black . - Format all Python files in current directory
  - black --line-length 100 . - Use 100 char line limit instead of default 88

---