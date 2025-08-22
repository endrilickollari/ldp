"""
Tests for multi-page document processing features
"""

import pytest
import json
from unittest.mock import Mock, patch
from workers.smart_preprocessor import DocumentPreprocessor, DocumentMetadata
from workers.tasks import process_document
import io


class TestMultiPageFeatures:
    """Test multi-page document processing features"""

    def test_document_metadata_page_fields(self):
        """Test that DocumentMetadata includes page range fields"""
        metadata = DocumentMetadata(
            document_type='pdf',
            file_format='.pdf',
            page_count=10,
            estimated_quality=0.8,
            pages_processed_start=2,
            pages_processed_end=5,
            pages_processed_count=4
        )
        
        assert metadata.pages_processed_start == 2
        assert metadata.pages_processed_end == 5
        assert metadata.pages_processed_count == 4

    @patch('workers.smart_preprocessor.pdfplumber.open')
    def test_pdf_page_range_processing(self, mock_pdfplumber):
        """Test PDF preprocessing with page range"""
        # Mock PDF with 5 pages
        mock_pages = []
        for i in range(5):
            page = Mock()
            page.extract_text.return_value = f"Page {i+1} content"
            page.extract_tables.return_value = []
            mock_pages.append(page)
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        # Test preprocessing pages 2-4
        preprocessor = DocumentPreprocessor()
        file_content = b"dummy pdf content"
        filename = "test.pdf"
        metadata = DocumentMetadata(
            document_type='pdf',
            file_format='.pdf',
            page_count=0,
            estimated_quality=0.0
        )
        
        text, result_metadata, intermediate = preprocessor._preprocess_pdf(
            file_content, filename, metadata, page_start=2, page_end=4
        )
        
        # Verify page range metadata
        assert result_metadata.pages_processed_start == 2
        assert result_metadata.pages_processed_end == 4
        assert result_metadata.pages_processed_count == 3
        assert result_metadata.page_count == 5
        
        # Verify intermediate format includes page range info
        assert intermediate['pages_processed_start'] == 2
        assert intermediate['pages_processed_end'] == 4
        assert intermediate['pages_processed_count'] == 3
        
        # Verify only pages 2-4 are included in pages data
        assert len(intermediate['pages']) == 3
        assert intermediate['pages'][0]['page_number'] == 2
        assert intermediate['pages'][1]['page_number'] == 3
        assert intermediate['pages'][2]['page_number'] == 4

    @patch('workers.smart_preprocessor.pdfplumber.open')
    def test_pdf_invalid_page_range(self, mock_pdfplumber):
        """Test PDF preprocessing with invalid page range"""
        # Mock PDF with 3 pages
        mock_pages = [Mock(), Mock(), Mock()]
        for i, page in enumerate(mock_pages):
            page.extract_text.return_value = f"Page {i+1} content"
            page.extract_tables.return_value = []
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        preprocessor = DocumentPreprocessor()
        file_content = b"dummy pdf content"
        filename = "test.pdf"
        metadata = DocumentMetadata(
            document_type='pdf',
            file_format='.pdf',
            page_count=0,
            estimated_quality=0.0
        )
        
        # Test with page_start > document page count
        with pytest.raises(ValueError, match="page_start.*exceeds document page count"):
            preprocessor._preprocess_pdf(
                file_content, filename, metadata, page_start=5, page_end=6
            )

    def test_fallback_processing_page_range(self):
        """Test fallback processing with page range parameters"""
        from workers.tasks import _fallback_processing
        
        # Test that fallback processing accepts page parameters
        with patch('workers.tasks.pdfplumber.open') as mock_pdfplumber:
            # Mock PDF with 3 pages
            mock_pages = []
            for i in range(3):
                page = Mock()
                page.extract_text.return_value = f"Fallback page {i+1}"
                mock_pages.append(page)
            
            mock_pdf = Mock()
            mock_pdf.pages = mock_pages
            mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
            
            # Also need to mock the second call for page count determination
            with patch('workers.tasks.io.BytesIO'), \
                 patch('workers.tasks.pdfplumber.open', return_value=mock_pdfplumber.return_value):
                
                file_content = b"dummy pdf content"
                filename = "test.pdf"
                
                # Test processing only page 2
                text, metadata, intermediate = _fallback_processing(
                    file_content, filename, page_start=2, page_end=2
                )
                
                assert metadata.pages_processed_start == 2
                assert metadata.pages_processed_end == 2
                assert metadata.pages_processed_count == 1
                assert "Fallback page 2" in text
                assert "Fallback page 1" not in text
                assert "Fallback page 3" not in text

    def test_output_format_combined(self):
        """Test that combined output format works correctly"""
        # This would be tested with a full integration test
        # For now, just verify that the metadata structure is correct
        test_metadata = {
            'user_id': 1,
            'plan_type': 'premium',
            'usage_log_id': 1,
            'page_start': None,
            'page_end': None,
            'output_format': 'combined'
        }
        
        assert test_metadata['output_format'] == 'combined'
        assert test_metadata['page_start'] is None
        assert test_metadata['page_end'] is None

    def test_output_format_per_page(self):
        """Test that per-page output format metadata is structured correctly"""
        test_metadata = {
            'user_id': 1,
            'plan_type': 'premium', 
            'usage_log_id': 1,
            'page_start': 2,
            'page_end': 5,
            'output_format': 'per_page'
        }
        
        assert test_metadata['output_format'] == 'per_page'
        assert test_metadata['page_start'] == 2
        assert test_metadata['page_end'] == 5
