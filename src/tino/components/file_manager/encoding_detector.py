"""
Encoding Detector for robust file encoding detection.

Uses chardet library with fallback strategies to reliably detect
file encodings for cross-platform compatibility.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import chardet

logger = logging.getLogger(__name__)


class EncodingDetector:
    """
    Robust encoding detection using chardet with fallback strategies.
    
    Provides reliable encoding detection for text files with various
    fallback strategies for edge cases.
    """
    
    # Common encodings to try as fallbacks
    FALLBACK_ENCODINGS = [
        'utf-8',
        'utf-16',
        'utf-16-le',
        'utf-16-be',
        'latin-1',
        'cp1252',  # Windows-1252
        'iso-8859-1',
        'ascii',
    ]
    
    # Minimum confidence threshold for chardet results
    MIN_CONFIDENCE = 0.7
    
    def __init__(self, min_confidence: float = MIN_CONFIDENCE) -> None:
        """
        Initialize the encoding detector.
        
        Args:
            min_confidence: Minimum confidence threshold for chardet (0.0-1.0)
        """
        self.min_confidence = max(0.0, min(1.0, min_confidence))
    
    def detect_file_encoding(self, file_path: Path) -> str:
        """
        Detect the encoding of a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Detected encoding name (e.g., 'utf-8', 'latin-1')
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Read sample bytes for detection
            with open(file_path, 'rb') as f:
                # Read up to 64KB for detection
                raw_data = f.read(65536)
            
            if not raw_data:
                # Empty file, assume UTF-8
                logger.debug(f"Empty file, assuming UTF-8: {file_path}")
                return 'utf-8'
            
            # Try chardet first
            encoding = self._detect_with_chardet(raw_data)
            if encoding:
                logger.debug(f"Chardet detected {encoding} for {file_path}")
                return encoding
            
            # Fall back to trying common encodings
            encoding = self._detect_with_fallbacks(raw_data)
            if encoding:
                logger.debug(f"Fallback detected {encoding} for {file_path}")
                return encoding
            
            # Last resort: latin-1 (can decode any byte sequence)
            logger.warning(f"Could not reliably detect encoding for {file_path}, using latin-1")
            return 'latin-1'
            
        except PermissionError as e:
            logger.error(f"Permission denied reading {file_path}: {e}")
            raise
        except OSError as e:
            logger.error(f"I/O error reading {file_path}: {e}")
            raise
    
    def _detect_with_chardet(self, data: bytes) -> Optional[str]:
        """
        Detect encoding using chardet library.
        
        Args:
            data: Raw bytes to analyze
            
        Returns:
            Detected encoding if confidence is high enough, None otherwise
        """
        try:
            result = chardet.detect(data)
            
            if result and result.get('encoding'):
                confidence = result.get('confidence', 0.0)
                raw_encoding = result['encoding']
                if raw_encoding is not None:
                    encoding = raw_encoding.lower()
                
                logger.debug(f"Chardet result: {encoding} (confidence: {confidence:.2f})")
                
                if confidence >= self.min_confidence:
                    # Normalize some common encoding names
                    encoding = self._normalize_encoding_name(encoding)
                    return encoding
            
        except Exception as e:
            logger.debug(f"Chardet detection failed: {e}")
        
        return None
    
    def _detect_with_fallbacks(self, data: bytes) -> Optional[str]:
        """
        Try to detect encoding using fallback strategies.
        
        Args:
            data: Raw bytes to analyze
            
        Returns:
            Detected encoding if successful, None otherwise
        """
        for encoding in self.FALLBACK_ENCODINGS:
            if self._can_decode(data, encoding):
                return encoding
        
        return None
    
    def _can_decode(self, data: bytes, encoding: str) -> bool:
        """
        Test if data can be decoded with the given encoding.
        
        Args:
            data: Raw bytes to test
            encoding: Encoding to try
            
        Returns:
            True if data can be decoded without errors
        """
        try:
            data.decode(encoding)
            return True
        except (UnicodeDecodeError, LookupError):
            return False
    
    def _normalize_encoding_name(self, encoding: str) -> str:
        """
        Normalize encoding name to standard form.
        
        Args:
            encoding: Raw encoding name
            
        Returns:
            Normalized encoding name
        """
        encoding = encoding.lower().replace('_', '-')
        
        # Common normalizations
        normalizations = {
            'utf8': 'utf-8',
            'utf16': 'utf-16',
            'iso8859-1': 'iso-8859-1',
            'windows-1252': 'cp1252',
        }
        
        return normalizations.get(encoding, encoding)
    
    def detect_bytes_encoding(self, data: bytes) -> Tuple[str, float]:
        """
        Detect encoding of raw bytes with confidence score.
        
        Args:
            data: Raw bytes to analyze
            
        Returns:
            Tuple of (encoding, confidence) where confidence is 0.0-1.0
        """
        if not data:
            return 'utf-8', 1.0
        
        # Try chardet first
        try:
            result = chardet.detect(data)
            if result and result.get('encoding'):
                confidence = result.get('confidence', 0.0)
                raw_encoding = result['encoding']
                if raw_encoding is not None:
                    encoding = self._normalize_encoding_name(raw_encoding)
                    return encoding, confidence
        except Exception:
            pass
        
        # Try fallbacks
        for encoding in self.FALLBACK_ENCODINGS:
            if self._can_decode(data, encoding):
                # Assign arbitrary confidence based on position in fallback list
                confidence = max(0.1, 1.0 - (self.FALLBACK_ENCODINGS.index(encoding) * 0.1))
                return encoding, confidence
        
        # Last resort
        return 'latin-1', 0.1
    
    def is_binary_data(self, data: bytes, threshold: float = 0.2) -> bool:
        """
        Heuristically determine if data is binary.
        
        Args:
            data: Raw bytes to analyze
            threshold: Ratio of null bytes that indicates binary data
            
        Returns:
            True if data appears to be binary
        """
        if not data:
            return False
        
        # Check for common binary file signatures first
        binary_signatures = [
            b'\x89PNG',  # PNG
            b'GIF8',     # GIF
            b'\xff\xd8\xff',  # JPEG
            b'%PDF-',    # PDF
            b'PK\x03\x04',  # ZIP
            b'\x50\x4b',  # ZIP alternative
            b'\x7fELF',  # ELF binary
            b'MZ',       # Windows PE
        ]
        
        for signature in binary_signatures:
            if data.startswith(signature):
                return True
        
        # Count null bytes and non-printable characters
        null_count = data.count(b'\x00')
        null_ratio = null_count / len(data)
        
        # Lower threshold for null bytes (20% instead of 30%)
        if null_ratio > threshold:
            return True
        
        # Additional heuristics for binary detection
        # Check for consecutive null bytes (strong indicator of binary)
        if b'\x00\x00\x00' in data:
            return True
        
        # Check for high concentration of null bytes in first part
        sample_size = min(512, len(data))
        first_sample_nulls = data[:sample_size].count(b'\x00')
        if sample_size > 0 and first_sample_nulls / sample_size > 0.15:
            return True
        
        # Check for other non-printable control characters
        control_chars = 0
        for byte in data[:sample_size]:
            # Count control characters (except common whitespace)
            if byte < 32 and byte not in (9, 10, 13):  # Tab, LF, CR are OK
                control_chars += 1
        
        if sample_size > 0 and control_chars / sample_size > 0.1:
            return True
        
        return False
    
    def validate_text_encoding(self, file_path: Path, encoding: str) -> bool:
        """
        Validate that a file can be read with the specified encoding.
        
        Args:
            file_path: Path to the file
            encoding: Encoding to validate
            
        Returns:
            True if file can be read with the encoding
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Read a chunk to validate
                f.read(1024)
            return True
        except (UnicodeDecodeError, FileNotFoundError, PermissionError, LookupError):
            return False
    
    def get_bom_encoding(self, data: bytes) -> Optional[str]:
        """
        Detect encoding from Byte Order Mark (BOM).
        
        Args:
            data: Raw bytes to check for BOM
            
        Returns:
            Encoding if BOM is found, None otherwise
        """
        bom_encodings = [
            (b'\xef\xbb\xbf', 'utf-8-sig'),
            (b'\xff\xfe\x00\x00', 'utf-32-le'),
            (b'\x00\x00\xfe\xff', 'utf-32-be'),
            (b'\xff\xfe', 'utf-16-le'),
            (b'\xfe\xff', 'utf-16-be'),
        ]
        
        for bom, encoding in bom_encodings:
            if data.startswith(bom):
                return encoding
        
        return None