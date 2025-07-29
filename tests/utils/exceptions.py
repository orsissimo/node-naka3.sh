class BatchProcessingError(Exception):
    """Custom exception for failures during batch transaction processing."""
    def __init__(self, message, successful_submissions, failed_submissions, expected_nonce, actual_nonce):
        self.message = message
        self.successful_submissions = successful_submissions
        self.failed_submissions = failed_submissions
        self.expected_nonce = expected_nonce
        self.actual_nonce = actual_nonce
        super().__init__(self.message)