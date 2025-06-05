"""
Mock validators module - temporary version without libmagic dependency
"""

import os
from typing import Tuple, Optional
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def validate_upload_file(file_path: str, original_filename: str) -> Tuple[bool, Optional[str], dict]:
    """
    Mock file validation - basic checks only
    """
    try:
        # Basic file existence check
        if not os.path.exists(file_path):
            return False, "File does not exist", {}
        
        # Basic extension check
        file_ext = Path(original_filename).suffix.lower()
        if file_ext != '.pdf':
            return False, f"Only PDF files are allowed, got: {file_ext}", {}
        
        # Basic size check
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty", {}
        
        # Return success with basic file info
        file_info = {
            "filename": original_filename,
            "size": file_size,
            "extension": file_ext,
            "mock": True
        }
        
        logger.info(f"Mock validation passed for: {original_filename}")
        return True, None, file_info
        
    except Exception as e:
        logger.error(f"Mock validation error: {e}")
        return False, f"Validation error: {str(e)}", {}


def sanitize_filename(filename: str) -> str:
    """
    Mock filename sanitization
    """
    # Basic sanitization - remove dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized


def is_safe_filename(filename: str) -> bool:
    """
    Mock filename safety check
    """
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    return not any(char in filename for char in dangerous_chars) 