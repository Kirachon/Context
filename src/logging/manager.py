"""
Logging Manager

Provides get_logger wrapper used across the project. (Restored for tests)
"""
import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

