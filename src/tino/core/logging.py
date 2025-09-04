"""
Structured logging configuration for the tino editor.

Provides centralized logging setup with proper levels, rotating file handlers,
and platform-specific log directories using platformdirs.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import traceback
from datetime import datetime

try:
    from platformdirs import user_log_dir, user_cache_dir
except ImportError:
    # Fallback if platformdirs not available
    import os
    def user_log_dir(appname: str) -> str:  # type: ignore[misc]
        if sys.platform == "win32":
            return os.path.join(os.environ.get("LOCALAPPDATA", ""), appname, "logs")
        else:
            return os.path.join(os.path.expanduser("~"), ".local", "share", appname, "logs")
    
    def user_cache_dir(appname: str) -> str:  # type: ignore[misc]
        if sys.platform == "win32":
            return os.path.join(os.environ.get("LOCALAPPDATA", ""), appname, "cache")
        else:
            return os.path.join(os.path.expanduser("~"), ".cache", appname)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        exc_info = record.exc_info
        if exc_info is True:
            exc_info = sys.exc_info()
        
        if exc_info and isinstance(exc_info, tuple) and exc_info != (None, None, None):
            log_data['exception'] = {
                'type': exc_info[0].__name__ if exc_info[0] else None,
                'message': str(exc_info[1]) if exc_info[1] else None,
                'traceback': traceback.format_exception(*exc_info)
            }
        
        # Add extra fields if present
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'):
                extra_fields[key] = value
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Console formatter with color support for different log levels.
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Format the message
        formatted = f"{color}{timestamp} [{record.levelname:>8}] {record.name}: {record.getMessage()}{reset}"
        
        # Add exception info if present
        exc_info = record.exc_info
        if exc_info is True:
            exc_info = sys.exc_info()
        
        if exc_info and isinstance(exc_info, tuple) and exc_info != (None, None, None):
            formatted += f"\n{color}{self.formatException(exc_info)}{reset}"
        
        return formatted


class TinoLogger:
    """
    Main logging configuration and management class for tino.
    """
    
    def __init__(self, app_name: str = "tino"):
        """
        Initialize the tino logger.
        
        Args:
            app_name: Application name for log directories
        """
        self.app_name = app_name
        self.log_dir = Path(user_log_dir(app_name))
        self.cache_dir = Path(user_cache_dir(app_name))
        self._handlers: Dict[str, logging.Handler] = {}
        self._configured = False
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def configure(
        self, 
        level: str = "INFO",
        console_output: bool = True,
        file_output: bool = True,
        structured_logs: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        debug_mode: bool = False
    ) -> None:
        """
        Configure logging with specified settings.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
            file_output: Whether to output to file
            structured_logs: Whether to use structured JSON logging
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup files to keep
            debug_mode: Enable debug mode with verbose output
        """
        
        if self._configured:
            self.cleanup()
        
        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        
        # Configure console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            
            if structured_logs:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(ColoredConsoleFormatter())
            
            if debug_mode:
                console_handler.setLevel(logging.DEBUG)
            else:
                console_handler.setLevel(getattr(logging, level.upper()))
            
            root_logger.addHandler(console_handler)
            self._handlers['console'] = console_handler
        
        # Configure file handler
        if file_output:
            log_file = self.log_dir / "tino.log"
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            
            if structured_logs:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
            
            file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
            root_logger.addHandler(file_handler)
            self._handlers['file'] = file_handler
        
        # Configure debug file handler if debug mode
        if debug_mode:
            debug_file = self.log_dir / "debug.log"
            
            debug_handler = logging.handlers.RotatingFileHandler(
                debug_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            
            debug_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)-8s] %(name)s.%(funcName)s:%(lineno)d: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S.%f'
            )
            debug_handler.setFormatter(debug_formatter)
            debug_handler.setLevel(logging.DEBUG)
            
            root_logger.addHandler(debug_handler)
            self._handlers['debug'] = debug_handler
        
        self._configured = True
        
        # Log configuration success
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {level}, Console: {console_output}, File: {file_output}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    def set_level(self, level: str, handler: Optional[str] = None) -> None:
        """
        Change logging level for specific handler or all handlers.
        
        Args:
            level: New logging level
            handler: Specific handler name ('console', 'file', 'debug') or None for all
        """
        log_level = getattr(logging, level.upper())
        
        if handler and handler in self._handlers:
            self._handlers[handler].setLevel(log_level)
        else:
            # Set for all handlers
            for h in self._handlers.values():
                h.setLevel(log_level)
            
            # Also set root logger level
            logging.getLogger().setLevel(log_level)
    
    def cleanup(self) -> None:
        """Clean up all logging handlers."""
        root_logger = logging.getLogger()
        
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        
        self._handlers.clear()
        self._configured = False
    
    def get_log_files(self) -> List[Path]:
        """
        Get list of current log files.
        
        Returns:
            List of log file paths
        """
        log_files: List[Path] = []
        if self.log_dir.exists():
            log_files.extend(self.log_dir.glob("*.log*"))
        return sorted(log_files)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging statistics
        """
        stats = {
            'configured': self._configured,
            'handlers': list(self._handlers.keys()),
            'log_directory': str(self.log_dir),
            'log_files': [str(f) for f in self.get_log_files()],
        }
        
        # Add file sizes
        for log_file in self.get_log_files():
            try:
                stats[f'{log_file.name}_size'] = log_file.stat().st_size
            except OSError:
                pass
        
        return stats
    
    def rotate_logs(self) -> bool:
        """
        Manually trigger log rotation.
        
        Returns:
            True if rotation was successful
        """
        try:
            for handler_name, handler in self._handlers.items():
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.doRollover()
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to rotate logs: {e}")
            return False


# Global logger instance
_default_logger: Optional[TinoLogger] = None


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = TinoLogger()
        _default_logger.configure()
    
    return _default_logger.get_logger(name)


def configure_logging(**kwargs: Any) -> TinoLogger:
    """
    Configure the default logging system.
    
    Args:
        **kwargs: Configuration options for TinoLogger.configure()
        
    Returns:
        Configured TinoLogger instance
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = TinoLogger()
    
    _default_logger.configure(**kwargs)
    return _default_logger


def cleanup_logging() -> None:
    """Clean up the default logging system."""
    global _default_logger
    if _default_logger:
        _default_logger.cleanup()
        _default_logger = None


# Context manager for temporary log level changes
class LogLevel:
    """Context manager for temporarily changing log level."""
    
    def __init__(self, level: str, logger_name: Optional[str] = None):
        """
        Initialize log level context manager.
        
        Args:
            level: Temporary log level
            logger_name: Specific logger name or None for root logger
        """
        self.new_level = getattr(logging, level.upper())
        self.logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        self.old_level: Optional[int] = None
    
    def __enter__(self) -> 'LogLevel':
        """Enter context and change log level."""
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore original log level."""
        if self.old_level is not None:
            self.logger.setLevel(self.old_level)