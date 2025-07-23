;; Simple NFT Contract for testing
(define-non-fungible-token test-nft uint)

;; Storage
(define-data-var last-token-id uint u0)
(define-data-var token-uri (string-ascii 256) "https://example.com/token/")

;; Core NFT Functions
(define-read-only (get-last-token-id)
  (ok (var-get last-token-id)))

(define-read-only (get-token-uri (id uint))
  (ok (some (var-get token-uri))))

(define-read-only (get-owner (id uint))
  (ok (nft-get-owner? test-nft id)))

;; Transfer function (simplified - caller must own the NFT)
(define-public (transfer (id uint) (recipient principal))
  (let ((owner (unwrap! (nft-get-owner? test-nft id) (err u404))))
    (asserts! (is-eq tx-sender owner) (err u403))
    (try! (nft-transfer? test-nft id owner recipient))
    (ok true)))

;; Mint function
(define-public (mint (recipient principal))
  (let
    ((token-id (+ (var-get last-token-id) u1)))
    (try! (nft-mint? test-nft token-id recipient))
    (var-set last-token-id token-id)
    (print {event: "minted", token-id: token-id, recipient: recipient})
    (ok token-id)))

;; Burn function  
(define-public (burn (id uint))
  (begin
    (try! (nft-burn? test-nft id tx-sender))
    (print {event: "burned", token-id: id, owner: tx-sender})
    (ok id)))

;; Read-only helper functions for testing
(define-read-only (get-token-count)
  (var-get last-token-id))

(define-read-only (get-token-owner (id uint))
  (nft-get-owner? test-nft id))

(define-read-only (check-owner (id uint) (user principal))
  (is-eq (some user) (nft-get-owner? test-nft id)))