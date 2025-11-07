"""
Parameter Parsing Utilities for MCP Tools

Provides helper functions to parse parameters that may be serialized
in different formats by various MCP clients.
"""

import json
import logging
from typing import Optional, Union, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def parse_list_param(param: Optional[Union[str, List[T]]]) -> Optional[List[T]]:
    """
    Parse a parameter that could be a JSON string or a list.
    
    This handles cases where MCP clients serialize lists as JSON strings
    instead of actual arrays. This is common with some MCP client implementations
    like Claude Code CLI.
    
    Args:
        param: Either a list, a JSON string representing a list, or None
        
    Returns:
        Parsed list or None
        
    Examples:
        >>> parse_list_param(["a", "b", "c"])
        ["a", "b", "c"]
        
        >>> parse_list_param('["a", "b", "c"]')
        ["a", "b", "c"]
        
        >>> parse_list_param(None)
        None
        
        >>> parse_list_param("invalid json")
        None
    """
    if param is None:
        return None
        
    if isinstance(param, list):
        return param
        
    if isinstance(param, str):
        try:
            parsed = json.loads(param)
            if isinstance(parsed, list):
                return parsed
            logger.warning(f"Parsed JSON is not a list: {type(parsed)}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON string: {param} - {e}")
            return None
            
    logger.warning(f"Unexpected parameter type: {type(param)}")
    return None

