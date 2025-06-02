"""
Base64 utility functions with error handling for incorrect padding
"""

import base64
import logging

logger = logging.getLogger(__name__)

def safe_base64_decode(encoded_string: str) -> bytes:
    """
    Safely decode a base64 string, handling incorrect padding.
    
    Args:
        encoded_string: The base64 encoded string
        
    Returns:
        The decoded bytes
        
    Raises:
        ValueError: If the string cannot be decoded even after padding correction
    """
    if not encoded_string:
        return b''
    
    # Remove any whitespace
    encoded_string = encoded_string.strip()
    
    # Try to decode as-is first
    try:
        return base64.b64decode(encoded_string)
    except Exception as e:
        logger.debug(f"Initial base64 decode failed: {e}")
    
    # If that fails, try adding padding
    missing_padding = len(encoded_string) % 4
    if missing_padding:
        encoded_string += '=' * (4 - missing_padding)
        
    try:
        return base64.b64decode(encoded_string)
    except Exception as e:
        logger.error(f"Base64 decode failed even after padding correction: {e}")
        logger.error(f"String length: {len(encoded_string)}")
        raise ValueError(f"Invalid base64 string: {str(e)}")

def safe_base64_encode(data: bytes) -> str:
    """
    Safely encode bytes to base64 string.
    
    Args:
        data: The bytes to encode
        
    Returns:
        The base64 encoded string
    """
    if not data:
        return ''
    
    try:
        return base64.b64encode(data).decode('utf-8')
    except Exception as e:
        logger.error(f"Base64 encode failed: {e}")
        raise ValueError(f"Failed to encode data: {str(e)}")

def validate_base64(encoded_string: str) -> bool:
    """
    Check if a string is valid base64.
    
    Args:
        encoded_string: The string to validate
        
    Returns:
        True if valid base64, False otherwise
    """
    try:
        safe_base64_decode(encoded_string)
        return True
    except:
        return False

def fix_base64_padding(encoded_string: str) -> str:
    """
    Fix base64 padding issues.
    
    Args:
        encoded_string: The base64 string with potential padding issues
        
    Returns:
        The corrected base64 string
    """
    if not encoded_string:
        return ''
    
    # Remove any whitespace
    encoded_string = encoded_string.strip()
    
    # Add missing padding if needed
    missing_padding = len(encoded_string) % 4
    if missing_padding:
        encoded_string += '=' * (4 - missing_padding)
        
    return encoded_string