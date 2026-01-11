"""
Security Utilities

Provides input validation and prompt injection detection for user inputs.
"""

import re
from typing import Tuple
from urllib.parse import urlparse
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Prompt injection detection patterns (STRICT MODE)
PROMPT_INJECTION_PATTERNS = [
    # Instruction manipulation
    r'(?:ignore|disregard|bypass|override)\s+(?:your|previous|all)\s+(?:instructions?|orders?|prompts?|rules?)',
    r'(?:forget|clear|delete)\s+(?:your|all|previous)',
    r'(?:you are now|act as|pretend to be|roleplay as)\s+\w+',
    r'(?:system\s+)?prompts?\s*:',
    r'new\s+(?:instruction|directive|command)',

    # Template/code injection
    r'\$\{.*?\}',  # Template injection
    r'<!--.*?-->',  # HTML comments
    r'<script|<iframe|<object|<embed',  # HTML injection

    # Format manipulation
    r'(?:^|\n)\s*---+\s*(?:\n|$)',  # YAML/Markdown separators
    r'(?:^|\n)\s*```',  # Code blocks

    # Common jailbreak patterns
    r'developer\s+mode',
    r'jailbreak',
    r'(?:DAN|do anything now)',
]

# Compiled regex patterns for performance
COMPILED_INJECTION_PATTERNS = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in PROMPT_INJECTION_PATTERNS]

# Dangerous URL schemes
DANGEROUS_URL_SCHEMES = {
    'javascript',
    'data',
    'file',
    'vbscript',
    'about',
}

# Maximum lengths for various input types
MAX_URL_LENGTH = 2048
MAX_TEXT_LENGTH = 500
MAX_TOPICS_LENGTH = 1000
MAX_DOMAIN_LIST_LENGTH = 500


def validate_url(url: str) -> bool:
    """
    Validate URL format, scheme, and safety.

    Args:
        url: URL string to validate

    Returns:
        bool: True if URL is valid and safe, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    # Check length
    if len(url) > MAX_URL_LENGTH:
        logger.warning(f"URL exceeds maximum length: {len(url)} > {MAX_URL_LENGTH}")
        return False

    # Check for newlines or control characters
    if '\n' in url or '\r' in url or '\t' in url:
        logger.warning("URL contains newlines or control characters")
        return False

    # Check for control characters (ASCII 0-31)
    if any(ord(char) < 32 for char in url):
        logger.warning("URL contains control characters")
        return False

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.warning(f"URL parsing failed: {str(e)}")
        return False

    # Check scheme
    if parsed.scheme and parsed.scheme.lower() in DANGEROUS_URL_SCHEMES:
        logger.warning(f"Dangerous URL scheme detected: {parsed.scheme}")
        return False

    # Require scheme for external URLs (http or https)
    if parsed.scheme and parsed.scheme.lower() not in ['http', 'https', '']:
        logger.warning(f"Invalid URL scheme: {parsed.scheme}")
        return False

    # Check for netloc if scheme is present
    if parsed.scheme and not parsed.netloc:
        logger.warning("URL has scheme but no netloc")
        return False

    return True


def detect_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Detect potential prompt injection patterns in text.

    Args:
        text: Text to check for injection patterns

    Returns:
        Tuple[bool, str]: (is_suspicious, reason)
    """
    if not text or not isinstance(text, str):
        return (False, "")

    # Check each pattern
    for i, pattern in enumerate(COMPILED_INJECTION_PATTERNS):
        match = pattern.search(text)
        if match:
            matched_text = match.group(0)
            reason = f"Suspicious pattern detected: '{matched_text[:50]}...'"
            logger.warning(f"Prompt injection attempt detected: {reason}")
            return (True, reason)

    return (False, "")


def validate_domain_list(domains_csv: str) -> Tuple[bool, str]:
    """
    Validate comma-separated domain list.

    Args:
        domains_csv: Comma-separated list of domains

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not domains_csv or not isinstance(domains_csv, str):
        return (True, "")  # Empty is valid

    # Check length
    if len(domains_csv) > MAX_DOMAIN_LIST_LENGTH:
        return (False, f"Domain list exceeds maximum length ({MAX_DOMAIN_LIST_LENGTH} characters)")

    # Split by comma
    domains = [d.strip().lower() for d in domains_csv.split(',')]

    # Validate each domain
    domain_pattern = re.compile(
        r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
    )

    for domain in domains:
        if not domain:  # Skip empty entries
            continue

        # Check for IP addresses (simple check)
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
            return (False, f"IP addresses not allowed: {domain}")

        # Check for localhost/special domains
        if domain in ['localhost', '127.0.0.1', '0.0.0.0']:
            return (False, f"Localhost/special domains not allowed: {domain}")

        # Validate domain format
        if not domain_pattern.match(domain):
            return (False, f"Invalid domain format: {domain}")

    return (True, "")


def validate_text_input(text: str, max_length: int = MAX_TEXT_LENGTH) -> Tuple[bool, str]:
    """
    Validate general text input for prompt safety.

    Args:
        text: Text to validate
        max_length: Maximum allowed length

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not text or not isinstance(text, str):
        return (True, "")  # Empty is valid

    # Check length
    if len(text) > max_length:
        return (False, f"Input exceeds maximum length ({max_length} characters)")

    # Check for excessive newlines (more than 5 consecutive)
    if '\n\n\n\n\n' in text:
        return (False, "Input contains excessive newlines")

    # Check for control characters (except common whitespace)
    for char in text:
        ascii_val = ord(char)
        # Allow: space (32), tab (9), newline (10), carriage return (13)
        # Disallow: other control characters (0-31 except 9,10,13) and DEL (127)
        if ascii_val < 32 and ascii_val not in [9, 10, 13]:
            return (False, "Input contains invalid control characters")
        if ascii_val == 127:
            return (False, "Input contains invalid control characters")

    # Check for null bytes
    if '\x00' in text:
        return (False, "Input contains null bytes")

    return (True, "")


def validate_isbn(isbn: str) -> Tuple[bool, str]:
    """
    Validate ISBN-10 or ISBN-13 format.

    Args:
        isbn: ISBN string to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isbn or not isinstance(isbn, str):
        return (True, "")  # Empty is valid

    # Remove hyphens and spaces
    clean_isbn = isbn.replace('-', '').replace(' ', '')

    # Check length (ISBN-10 or ISBN-13)
    if len(clean_isbn) not in [10, 13]:
        return (False, "ISBN must be 10 or 13 digits")

    # Check if all characters are digits (ISBN-10 can have 'X' as last char)
    if len(clean_isbn) == 10:
        # ISBN-10 can end with X
        if not (clean_isbn[:-1].isdigit() and (clean_isbn[-1].isdigit() or clean_isbn[-1].upper() == 'X')):
            return (False, "ISBN-10 must contain only digits (and optionally 'X' as last character)")
    elif len(clean_isbn) == 13:
        if not clean_isbn.isdigit():
            return (False, "ISBN-13 must contain only digits")

    return (True, "")
