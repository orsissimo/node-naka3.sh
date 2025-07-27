#!/usr/bin/env python3
"""
Script to generate graduated contract sizes to find exact Stacks deployment limits
"""

def generate_contract_template(function_count, size_kb, filename):
    """Generate a contract with specified number of functions"""
    
    contract_content = f""";; CONTRACT {size_kb}KB - Testing size limits
;; Generated with {function_count} functions

;; Error constants
(define-constant ERR-UNAUTHORIZED u5001)
(define-constant ERR-INVALID-INPUT u5002)

;; Contract administration
(define-constant CONTRACT-DEPLOYER tx-sender)
(define-data-var contract-admin principal tx-sender)
(define-data-var contract-paused bool false)

;; Read-only functions
(define-read-only (get-contract-admin)
    (var-get contract-admin))

(define-read-only (is-contract-paused)
    (var-get contract-paused))

;; Admin functions
(define-public (emergency-shutdown)
    (begin
        (asserts! (is-eq tx-sender (var-get contract-admin)) (err ERR-UNAUTHORIZED))
        (var-set contract-paused true)
        (ok true)))

;; Generated functions for size testing
"""

    # Generate the specified number of functions
    for i in range(1, function_count + 1):
        contract_content += f"""(define-public (calc-function-{i:04d} (x uint))
    (ok (+ (* x u{12000 + i}) u{50000 + i})))
"""

    # Add test function
    contract_content += f"""
;; Test function to verify contract works
(define-public (test-contract-functions (sample-input uint))
    (let ((test1 (unwrap-panic (calc-function-0001 sample-input))))
        (ok test1)))
"""

    return contract_content

def main():
    print("🎯 Generating graduated contracts to find exact Stacks size limits...")
    
    # Generate contracts of many different sizes to find the exact limit
    # We know: 117KB works, 2.2MB fails
    # So let's test the range in between systematically
    
    contracts = [
        # Small sizes (known to work)
        (100, 8, "contract-8kb.clar"),
        (200, 16, "contract-16kb.clar"),  
        (300, 24, "contract-24kb.clar"),
        (500, 40, "contract-40kb.clar"),
        (750, 60, "contract-60kb.clar"),
        (1000, 80, "contract-80kb.clar"),
        (1250, 100, "contract-100kb.clar"),
        (1500, 120, "contract-120kb.clar"),
        
        # Medium sizes (testing where it might break)
        (2000, 160, "contract-160kb.clar"),
        (2500, 200, "contract-200kb.clar"),
        (3000, 240, "contract-240kb.clar"),
        (3750, 300, "contract-300kb.clar"),
        (5000, 400, "contract-400kb.clar"),
        (6250, 500, "contract-500kb.clar"),
        (7500, 600, "contract-600kb.clar"),
        (8750, 700, "contract-700kb.clar"),
        (10000, 800, "contract-800kb.clar"),
        (11250, 900, "contract-900kb.clar"),
        (12500, 1000, "contract-1000kb.clar"),
        
        # Large sizes (likely to start failing somewhere here)
        (15000, 1200, "contract-1200kb.clar"),
        (18750, 1500, "contract-1500kb.clar"),
        (25000, 2000, "contract-2000kb.clar"),
        (28125, 2250, "contract-2250kb.clar"),  # This one might be close to the limit
        
        # Massive size (known to fail, rename from 5mb to actual size)
        (56250, 4500, "contract-2200kb.clar"),  # This is actually ~2.2MB
    ]
    
    print(f"📊 Generating {len(contracts)} contracts from 8KB to 2200KB...")
    
    for function_count, size_kb, filename in contracts:
        print(f"📄 Generating {size_kb}KB contract with {function_count} functions...")
        contract_content = generate_contract_template(function_count, size_kb, filename)
        
        filepath = f'/home/simone/Desktop/node-naka3.sh/tests/contracts/{filename}'
        with open(filepath, 'w') as f:
            f.write(contract_content)
        
        contract_size = len(contract_content.encode('utf-8'))
        actual_kb = contract_size / 1024
        print(f"✅ {filename}: {contract_size:,} bytes ({actual_kb:.1f} KB)")
    
    print(f"\n🔬 Generated {len(contracts)} contracts for binary search of Stacks size limits!")
    print("🎯 Range: 8KB (should work) → 2200KB (should fail)")
    print("📈 This will help us find the exact deployment size limit!")

if __name__ == "__main__":
    main()