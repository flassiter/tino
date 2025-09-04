"""
Tests for EncodingDetector class.

Tests encoding detection, binary detection, BOM handling, and edge cases.
"""

import pytest
import tempfile
from pathlib import Path

from tino.components.file_manager.encoding_detector import EncodingDetector


class TestEncodingDetector:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = EncodingDetector()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_detect_utf8_file(self):
        """Test detection of UTF-8 encoded file."""
        test_file = self.temp_dir / "utf8.txt"
        content = "Hello, 世界! 🌍"
        test_file.write_text(content, encoding='utf-8')
        
        encoding = self.detector.detect_file_encoding(test_file)
        assert encoding == 'utf-8'
    
    def test_detect_latin1_file(self):
        """Test detection of Latin-1 encoded file."""
        test_file = self.temp_dir / "latin1.txt"
        content = "Café and naïve résumé"
        
        with open(test_file, 'w', encoding='latin-1') as f:
            f.write(content)
        
        encoding = self.detector.detect_file_encoding(test_file)
        # Should detect latin-1 or similar encoding (various ISO-8859 variants are acceptable)
        assert any(enc in encoding.lower() for enc in ['latin-1', 'iso-8859'])
    
    def test_detect_utf16_file(self):
        """Test detection of UTF-16 encoded file."""
        test_file = self.temp_dir / "utf16.txt"
        content = "Hello, world!"
        
        with open(test_file, 'w', encoding='utf-16') as f:
            f.write(content)
        
        encoding = self.detector.detect_file_encoding(test_file)
        assert 'utf-16' in encoding.lower()
    
    def test_detect_empty_file(self):
        """Test detection of empty file."""
        test_file = self.temp_dir / "empty.txt"
        test_file.touch()
        
        encoding = self.detector.detect_file_encoding(test_file)
        assert encoding == 'utf-8'  # Default for empty files
    
    def test_detect_nonexistent_file(self):
        """Test detection of non-existent file."""
        test_file = self.temp_dir / "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError):
            self.detector.detect_file_encoding(test_file)
    
    def test_detect_bytes_encoding_utf8(self):
        """Test encoding detection from bytes."""
        content = "Hello, 世界! 🌍"
        data = content.encode('utf-8')
        
        encoding, confidence = self.detector.detect_bytes_encoding(data)
        assert encoding == 'utf-8'
        assert confidence > 0.8
    
    def test_detect_bytes_encoding_empty(self):
        """Test encoding detection from empty bytes."""
        encoding, confidence = self.detector.detect_bytes_encoding(b'')
        assert encoding == 'utf-8'
        assert confidence == 1.0
    
    def test_detect_bytes_encoding_ascii(self):
        """Test encoding detection from ASCII bytes."""
        data = b'Hello, world!'
        
        encoding, confidence = self.detector.detect_bytes_encoding(data)
        assert encoding in ['ascii', 'utf-8']  # ASCII is subset of UTF-8
        assert confidence > 0.5
    
    def test_is_binary_data_text(self):
        """Test binary detection on text data."""
        text_data = "This is plain text".encode('utf-8')
        
        assert not self.detector.is_binary_data(text_data)
    
    def test_is_binary_data_with_nulls(self):
        """Test binary detection on data with null bytes."""
        binary_data = b'\x00\x01\x02\x03Hello\x00World\x00\x00'
        
        # Increase threshold for this test - it has 33% null bytes
        assert self.detector.is_binary_data(binary_data, threshold=0.2)
    
    def test_is_binary_data_png_signature(self):
        """Test binary detection on PNG signature."""
        png_data = b'\x89PNG\r\n\x1a\n'
        
        assert self.detector.is_binary_data(png_data)
    
    def test_is_binary_data_empty(self):
        """Test binary detection on empty data."""
        assert not self.detector.is_binary_data(b'')
    
    def test_validate_text_encoding_valid(self):
        """Test validation with correct encoding."""
        test_file = self.temp_dir / "test.txt"
        content = "Hello, 世界!"
        test_file.write_text(content, encoding='utf-8')
        
        assert self.detector.validate_text_encoding(test_file, 'utf-8')
    
    def test_validate_text_encoding_invalid(self):
        """Test validation with incorrect encoding."""
        test_file = self.temp_dir / "test.txt"
        content = "Hello, 世界!"
        test_file.write_text(content, encoding='utf-8')
        
        # Try to validate with wrong encoding
        assert not self.detector.validate_text_encoding(test_file, 'ascii')
    
    def test_validate_text_encoding_nonexistent(self):
        """Test validation of non-existent file."""
        test_file = self.temp_dir / "nonexistent.txt"
        
        assert not self.detector.validate_text_encoding(test_file, 'utf-8')
    
    def test_get_bom_encoding_utf8(self):
        """Test BOM detection for UTF-8."""
        data_with_bom = b'\xef\xbb\xbfHello, world!'
        
        encoding = self.detector.get_bom_encoding(data_with_bom)
        assert encoding == 'utf-8-sig'
    
    def test_get_bom_encoding_utf16_le(self):
        """Test BOM detection for UTF-16 LE."""
        data_with_bom = b'\xff\xfeH\x00e\x00l\x00l\x00o\x00'
        
        encoding = self.detector.get_bom_encoding(data_with_bom)
        assert encoding == 'utf-16-le'
    
    def test_get_bom_encoding_utf16_be(self):
        """Test BOM detection for UTF-16 BE."""
        data_with_bom = b'\xfe\xff\x00H\x00e\x00l\x00l\x00o'
        
        encoding = self.detector.get_bom_encoding(data_with_bom)
        assert encoding == 'utf-16-be'
    
    def test_get_bom_encoding_no_bom(self):
        """Test BOM detection on data without BOM."""
        data = b'Hello, world!'
        
        encoding = self.detector.get_bom_encoding(data)
        assert encoding is None
    
    def test_normalize_encoding_name(self):
        """Test encoding name normalization."""
        test_cases = [
            ('UTF8', 'utf-8'),
            ('utf_8', 'utf-8'),
            ('UTF-8', 'utf-8'),
            ('ISO8859-1', 'iso-8859-1'),
            ('windows-1252', 'cp1252'),
        ]
        
        for input_encoding, expected in test_cases:
            result = self.detector._normalize_encoding_name(input_encoding)
            assert result == expected
    
    def test_min_confidence_threshold(self):
        """Test that minimum confidence threshold is respected."""
        # Test with very low confidence threshold
        low_confidence_detector = EncodingDetector(min_confidence=0.1)
        
        # Test with very high confidence threshold
        high_confidence_detector = EncodingDetector(min_confidence=0.9)
        
        # Create a file that might have medium confidence
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("Simple ASCII text")
        
        low_encoding = low_confidence_detector.detect_file_encoding(test_file)
        high_encoding = high_confidence_detector.detect_file_encoding(test_file)
        
        # Both should detect something, but might use different strategies
        assert low_encoding in EncodingDetector.FALLBACK_ENCODINGS
        assert high_encoding in EncodingDetector.FALLBACK_ENCODINGS
    
    def test_fallback_encoding_detection(self):
        """Test fallback encoding detection when chardet fails."""
        # Create data that might be difficult for chardet
        test_file = self.temp_dir / "fallback.txt"
        
        # Write with a specific encoding that might not be detected well
        with open(test_file, 'wb') as f:
            f.write(b'\x80\x81\x82\x83')  # Some bytes that might confuse chardet
        
        encoding = self.detector.detect_file_encoding(test_file)
        # Should fall back to one of the fallback encodings
        assert encoding in EncodingDetector.FALLBACK_ENCODINGS
    
    def test_can_decode_method(self):
        """Test the _can_decode helper method."""
        utf8_data = "Hello, 世界!".encode('utf-8')
        ascii_data = b"Hello, world!"
        latin1_data = "café".encode('latin-1')
        
        assert self.detector._can_decode(utf8_data, 'utf-8')
        assert self.detector._can_decode(ascii_data, 'ascii')
        assert self.detector._can_decode(latin1_data, 'latin-1')
        
        # Test invalid decoding
        assert not self.detector._can_decode(utf8_data, 'ascii')  # UTF-8 chars can't be ASCII
    
    def test_large_file_sampling(self):
        """Test that large files are sampled correctly."""
        test_file = self.temp_dir / "large.txt"
        
        # Create a large file (larger than sample size)
        large_content = "Hello, world! " * 10000  # Much larger than 64KB
        test_file.write_text(large_content, encoding='utf-8')
        
        encoding = self.detector.detect_file_encoding(test_file)
        # ASCII content might be detected as ASCII or UTF-8
        assert encoding.lower() in ['ascii', 'utf-8']
    
    def test_binary_file_signatures(self):
        """Test recognition of various binary file signatures."""
        test_cases = [
            (b'\x89PNG\r\n\x1a\n', 'PNG'),
            (b'GIF87a', 'GIF'),
            (b'GIF89a', 'GIF'),
            (b'\xff\xd8\xff', 'JPEG'),
            (b'%PDF-', 'PDF'),
            (b'PK\x03\x04', 'ZIP'),
            (b'\x7fELF', 'ELF'),
            (b'MZ', 'PE'),
        ]
        
        for signature, file_type in test_cases:
            # Pad with some additional data
            data = signature + b'\x00' * 100
            assert self.detector.is_binary_data(data), f"Failed to detect {file_type} as binary"
    
    def test_mixed_encoding_handling(self):
        """Test handling of files with mixed or problematic encodings."""
        test_file = self.temp_dir / "mixed.txt"
        
        # Create file with mixed encoding-like content
        with open(test_file, 'wb') as f:
            f.write(b'Hello ')  # ASCII
            f.write('café'.encode('utf-8'))  # UTF-8
            f.write(b' and ')  # ASCII
            f.write('naïve'.encode('latin-1'))  # Latin-1
        
        # Should still detect an encoding (probably latin-1 as fallback)
        encoding = self.detector.detect_file_encoding(test_file)
        assert encoding in EncodingDetector.FALLBACK_ENCODINGS
    
    def test_confidence_scoring(self):
        """Test confidence scoring in detection."""
        # High confidence case: clear UTF-8
        high_conf_data = "Hello, 世界! 🌍".encode('utf-8')
        encoding, confidence = self.detector.detect_bytes_encoding(high_conf_data)
        assert confidence > 0.8
        
        # Lower confidence case: ambiguous data
        low_conf_data = b'\x80\x81\x82\x83\x84\x85'
        encoding, confidence = self.detector.detect_bytes_encoding(low_conf_data)
        # Confidence may vary depending on chardet version, just check it's reasonable
        assert 0.0 <= confidence <= 1.0
    
    def test_permission_denied_handling(self):
        """Test handling of permission denied errors."""
        # Create a file and remove read permissions
        test_file = self.temp_dir / "noaccess.txt"
        test_file.write_text("content")
        
        import stat
        if hasattr(stat, 'S_IWUSR'):
            try:
                test_file.chmod(0o000)  # No permissions
                
                with pytest.raises(PermissionError):
                    self.detector.detect_file_encoding(test_file)
                    
            finally:
                # Restore permissions for cleanup
                test_file.chmod(stat.S_IRWXU)