;; Contract: memory-bomb.clar
;; Description: A contract designed to test resource limits of the Stacks blockchain.
;; Contains functions for testing massive maps, deep recursion, large data, and gas exhaustion.

(define-constant ERR-STACK-OVERFLOW u101)
(define-constant ERR-GAS-EXHAUSTED u102)
(define-constant ERR-UNAUTHORIZED u103)

;; 1. MAP TEST: A map to be populated to test storage costs.
(define-map massive-map uint uint)

(define-public (populate-massive-map (count uint))
  ;; This uses a recursive helper to create a list, which also tests stack depth.
  (let ((items (sequence-of count)))
    (fold (lambda (i r) (begin (map-set massive-map i i) (ok true))) items (ok true))
    (ok true)))

;; 2. RECURSION TEST: Classic Fibonacci to test stack depth.
(define-public (deep-recursion-fibonacci (n uint))
  (if (<= n u1)
      (ok n)
      (let ((a (try! (deep-recursion-fibonacci (- n u1))))
            (b (try! (deep-recursion-fibonacci (- n u2)))))
        (ok (+ a b)))))

;; 3. GAS/COST TEST: A recursive helper to simulate a high-cost loop.
(define-private (gas-hog-helper (i uint) (limit uint) (acc uint))
  (if (>= i limit)
    acc
    (gas-hog-helper (+ i u1) limit (+ acc i))))

(define-public (gas-hog (iterations uint))
  (ok (gas-hog-helper u0 iterations u0)))

;; 4. MEMORY ALLOCATION TEST: Creates a list of N tuples.
(define-public (memory-alloc-stress (count uint))
  (ok (map (lambda (i) {id: i, value: (* i i)})
           (sequence-of count))))

;; 5. RECURSIVE HELPER for list generation, itself a stack depth test.
(define-read-only (sequence-of (n uint))
  (if (> n u0)
      (append (sequence-of (- n u1)) (list (- n u1)))
      (list)))

;; Read-only function for verification.
(define-read-only (get-map-entry (key uint))
  (map-get? massive-map key))