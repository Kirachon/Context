"""
Retry utilities for resilient operations
"""

import time
import random
from functools import wraps
from typing import Callable, Type, Tuple, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


def default_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Default retry decorator with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry on
        jitter: Whether to add random jitter to delay
        on_retry: Optional callback called on each retry attempt
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. "
                            f"Final error: {e}"
                        )
                        raise

                    # Log retry attempt
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}). "
                        f"Error: {e}. Retrying in {current_delay:.2f}s..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")

                    # Wait before retry
                    if jitter:
                        actual_delay = current_delay * (0.5 + random.random() * 0.5)
                    else:
                        actual_delay = current_delay

                    time.sleep(actual_delay)
                    current_delay *= backoff

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator


def linear_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Linear retry decorator with fixed delay between attempts

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Fixed delay between attempts in seconds
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback called on each retry attempt
    """
    return default_retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=1.0,  # No exponential growth
        jitter=False,
        exceptions=exceptions,
        on_retry=on_retry,
    )


def no_retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Helper to create a no-retry decorator (single attempt)

    Args:
        exceptions: Tuple of exceptions to catch (but not retry)
    """
    return default_retry(
        max_attempts=1,
        delay=0.0,
        exceptions=exceptions,
    )


# Common retry configurations
database_retry = default_retry(
    max_attempts=5,
    delay=0.5,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError, OSError),
)

network_retry = default_retry(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError, OSError),
)

api_retry = default_retry(
    max_attempts=3,
    delay=2.0,
    backoff=1.5,
    exceptions=(ConnectionError, TimeoutError, OSError),
)

quick_retry = default_retry(
    max_attempts=2,
    delay=0.1,
    backoff=2.0,
    exceptions=(Exception,),
)