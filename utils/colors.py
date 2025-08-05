import logging

class Colors:
    """A simple utility class for adding color to terminal output."""
    ORANGE = '\033[38;5;208m'
    WHITE = '\033[97m'
    GREY = '\033[90m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    @staticmethod
    def format_header(text: str) -> str:
        return f"{Colors.BLUE}{text}{Colors.RESET}"

    @staticmethod
    def format_grey(text: str) -> str:
        return f"{Colors.GREY}{text}{Colors.RESET}"

    @staticmethod
    def format_success(text: str) -> str:
        return f"{Colors.GREEN}✓ {Colors.WHITE}{text}{Colors.RESET}"

    @staticmethod
    def format_fail(text: str, error_msg: str = "") -> str:
        error_part = f": {Colors.RED}{error_msg}{Colors.RESET}" if error_msg else ""
        return f"{Colors.RED}✗ {Colors.WHITE}{text}{error_part}"

    @staticmethod
    def format_warn(text: str) -> str:
        return f"{Colors.YELLOW}⚠ {text}{Colors.RESET}"
    
    @staticmethod
    def format_info(text: str) -> str:
        return f"{Colors.WHITE}{text}{Colors.RESET}"
    
    @staticmethod
    def format_error(text: str) -> str:
        return f"{Colors.RED}✗ {text}{Colors.RESET}"
    
    @staticmethod
    def format_dim(text: str) -> str:
        return f"{Colors.DIM}{text}{Colors.RESET}"
    
    @staticmethod
    def format_subheader(text: str) -> str:
        return f"{Colors.CYAN}{text}{Colors.RESET}"

class ColorizingFormatter(logging.Formatter):
    """A logging formatter that adds color based on the log level."""
    LEVEL_COLORS = {
        logging.DEBUG: Colors.GREY,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: f"{Colors.BOLD}{Colors.RED}",
    }

    def format(self, record):
        # Override the levelname with a colored version
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        record.levelname = f"{color}{record.levelname:<8}{Colors.RESET}"
        # Make the timestamp grey
        record.asctime = f"{Colors.GREY}{self.formatTime(record, self.datefmt)}{Colors.RESET}"
        return super().format(record)

# --- Initialize Logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set default level

# Prevent duplicate handlers if this module is imported multiple times
if not logger.handlers:
    handler = logging.StreamHandler()
    # Use a format that doesn't hardcode colors, as the formatter handles them
    formatter = ColorizingFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)