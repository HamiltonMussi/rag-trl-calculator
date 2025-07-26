"""Centralized logging configuration for the RAG-TRL backend."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    config = get_logging_config(log_level, log_file)
    logging.config.dictConfig(config)
    
    # Set specific loggers to appropriate levels
    _configure_external_loggers()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level: {log_level}")


def get_logging_config(log_level: str = "INFO", log_file: str = None) -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
        
    Returns:
        Logging configuration dictionary
    """
    handlers = ["console"]
    if log_file:
        handlers.append("file")
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed",
                "stream": sys.stdout
            }
        },
        "root": {
            "level": log_level,
            "handlers": handlers
        },
        "loggers": {
            "trl-api": {
                "level": log_level,
                "handlers": handlers,
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": handlers,
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": handlers,
                "propagate": False
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": handlers,
                "propagate": False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": str(log_path),
            "maxBytes": 10_000_000,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
    
    return config


def _configure_external_loggers() -> None:
    """Configure logging levels for external libraries."""
    # Reduce verbosity of external libraries
    external_loggers = [
        "transformers",
        "torch",
        "chromadb",
        "openai",
        "httpx",
        "httpcore",
        "urllib3"
    ]
    
    for logger_name in external_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Add context to logger."""
        new_logger = StructuredLogger(self.logger.name)
        new_logger.context = {**self.context, **kwargs}
        return new_logger
    
    def _format_message(self, message: str) -> str:
        """Format message with context."""
        if not self.context:
            return message
        
        context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{message} | {context_str}"
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message), *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message), *args, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)