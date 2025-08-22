"""
Smart Document Preprocessing Module

This module provides comprehensive document preprocessing capabilities to improve
OCR accuracy and standardize documents before LLM processing.
"""

import io
import logging
import json
import re
from typing import Dict, Any, Optional, Tuple, List, Union
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np
import pandas as pd
import pdfplumber
import pytesseract
from datetime import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Optional OpenCV import - graceful fallback if not available
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    cv2 = None
    HAS_OPENCV = False

logger = logging.getLogger(__name__)

@dataclass
class DocumentMetadata:
    """Metadata extracted from document preprocessing"""
    document_type: str
    file_format: str
    page_count: int
    estimated_quality: float
    language: Optional[str] = None
    creation_date: Optional[datetime] = None
    preprocessing_applied: List[str] = field(default_factory=list)
    # Page range processing metadata
    pages_processed_start: Optional[int] = None
    pages_processed_end: Optional[int] = None
    pages_processed_count: Optional[int] = None

class DocumentPreprocessor:
    """Main document preprocessing class with smart enhancement capabilities"""
    
    def __init__(self):
        self.supported_formats = {
            'pdf': ['.pdf'],
            'excel': ['.xlsx', '.xls', '.csv'],
            'image': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
            'word': ['.docx', '.doc']  # Future support
        }
        
        if not HAS_OPENCV:
            logger.warning("OpenCV not available - some advanced image preprocessing features will be disabled")
        
    def preprocess_document(self, file_content: bytes, filename: str, page_start: Optional[int] = None, page_end: Optional[int] = None) -> Tuple[str, DocumentMetadata, Dict[str, Any]]:
        """
        Main preprocessing pipeline that handles different document types
        
        Returns:
            - Extracted and cleaned text
            - Document metadata
            - Intermediate structured format
        """
        file_extension = self._get_file_extension(filename)
        document_type = self._detect_document_type(file_extension)
        
        logger.info(f"Preprocessing {document_type} document: {filename}")
        
        metadata = DocumentMetadata(
            document_type=document_type,
            file_format=file_extension,
            page_count=0,
            estimated_quality=0.0
        )
        
        # Route to appropriate preprocessing method
        if document_type == 'pdf':
            text, metadata, intermediate = self._preprocess_pdf(file_content, filename, metadata, page_start, page_end)
        elif document_type == 'excel':
            text, metadata, intermediate = self._preprocess_excel(file_content, filename, metadata)
        elif document_type == 'image':
            text, metadata, intermediate = self._preprocess_image(file_content, filename, metadata)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        # Apply general text cleaning
        cleaned_text = self._clean_text(text)
        metadata.preprocessing_applied.append("text_cleaning")
        
        return cleaned_text, metadata, intermediate
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        return '.' + filename.lower().split('.')[-1] if '.' in filename else ''
    
    def _detect_document_type(self, file_extension: str) -> str:
        """Detect document type based on file extension"""
        for doc_type, extensions in self.supported_formats.items():
            if file_extension in extensions:
                return doc_type
        return 'unknown'
    
    def _preprocess_pdf(self, file_content: bytes, filename: str, metadata: DocumentMetadata, page_start: Optional[int] = None, page_end: Optional[int] = None) -> Tuple[str, DocumentMetadata, Dict[str, Any]]:
        """Preprocess PDF documents with smart text/image detection"""
        file_stream = io.BytesIO(file_content)
        extracted_text = ""
        pages_data = []
        text_based_pages = 0
        image_based_pages = 0
        
        try:
            with pdfplumber.open(file_stream) as pdf:
                metadata.page_count = len(pdf.pages)
                
                # Determine page range to process
                start_page = max(1, page_start or 1)
                end_page = min(metadata.page_count, page_end or metadata.page_count)
                
                # Validate page range
                if start_page > metadata.page_count:
                    raise ValueError(f"page_start ({start_page}) exceeds document page count ({metadata.page_count})")
                
                if end_page < start_page:
                    raise ValueError(f"Invalid page range: {start_page}-{end_page}")
                
                logger.info(f"Processing pages {start_page}-{end_page} of {metadata.page_count} total pages")
                
                # Update metadata for actual pages being processed
                metadata.pages_processed_start = start_page
                metadata.pages_processed_end = end_page
                metadata.pages_processed_count = end_page - start_page + 1
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Skip pages outside the requested range
                    if page_num < start_page or page_num > end_page:
                        continue
                        
                    page_text = page.extract_text()
                    page_data = {
                        "page_number": page_num,
                        "extraction_method": "text",
                        "content": "",
                        "tables": [],
                        "images": []
                    }
                    
                    if page_text and page_text.strip():
                        # Text-based page
                        page_data["content"] = page_text
                        extracted_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                        text_based_pages += 1
                        
                        # Extract tables if present
                        tables = page.extract_tables()
                        if tables:
                            page_data["tables"] = self._process_pdf_tables(tables)
                            metadata.preprocessing_applied.append(f"table_extraction_page_{page_num}")
                    else:
                        # Image-based page - apply OCR with preprocessing
                        logger.info(f"Applying OCR to page {page_num}")
                        try:
                            img = page.to_image(resolution=300).original
                            enhanced_img = self._enhance_image_for_ocr(img)
                            ocr_text = pytesseract.image_to_string(enhanced_img)
                            
                            page_data["extraction_method"] = "ocr"
                            page_data["content"] = ocr_text
                            extracted_text += f"\n--- Page {page_num} (OCR) ---\n{ocr_text}\n"
                            image_based_pages += 1
                            metadata.preprocessing_applied.append(f"ocr_enhancement_page_{page_num}")
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {e}")
                            page_data["content"] = "[OCR_FAILED]"
                    
                    pages_data.append(page_data)
                
                # Calculate quality estimation based on processed pages
                processed_pages = metadata.pages_processed_count or metadata.page_count
                quality_score = text_based_pages / processed_pages if processed_pages > 0 else 0
                metadata.estimated_quality = quality_score
                
        except Exception as e:
            logger.error(f"PDF preprocessing failed: {e}")
            raise
        
        intermediate_format = {
            "document_type": "pdf",
            "total_pages": metadata.page_count,
            "pages_processed_start": metadata.pages_processed_start,
            "pages_processed_end": metadata.pages_processed_end,
            "pages_processed_count": metadata.pages_processed_count,
            "text_based_pages": text_based_pages,
            "image_based_pages": image_based_pages,
            "quality_score": metadata.estimated_quality,
            "pages": pages_data,
            "full_text": extracted_text
        }
        
        return extracted_text, metadata, intermediate_format
    
    def _preprocess_excel(self, file_content: bytes, filename: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata, Dict[str, Any]]:
        """Preprocess Excel documents with structured data extraction"""
        file_stream = io.BytesIO(file_content)
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_stream, sheet_name=None)
            sheets_data = []
            full_text = ""
            
            for sheet_name, df in excel_data.items():
                # Clean and standardize data
                df_cleaned = self._clean_dataframe(df)
                
                sheet_info = {
                    "sheet_name": sheet_name,
                    "rows": len(df_cleaned),
                    "columns": len(df_cleaned.columns),
                    "column_names": df_cleaned.columns.tolist(),
                    "data_types": df_cleaned.dtypes.astype(str).to_dict(),
                    "sample_data": df_cleaned.head(5).to_dict('records') if len(df_cleaned) > 0 else [],
                    "summary_stats": self._generate_dataframe_summary(df_cleaned)
                }
                sheets_data.append(sheet_info)
                
                # Convert to readable text
                sheet_text = f"\n--- Sheet: {sheet_name} ---\n"
                sheet_text += f"Columns: {', '.join(df_cleaned.columns)}\n"
                sheet_text += f"Rows: {len(df_cleaned)}\n\n"
                sheet_text += df_cleaned.to_string(max_rows=100) + "\n"
                full_text += sheet_text
            
            metadata.page_count = len(excel_data)
            metadata.estimated_quality = 1.0  # Excel data is typically clean
            metadata.preprocessing_applied.append("dataframe_cleaning")
            metadata.preprocessing_applied.append("data_type_detection")
            
        except Exception as e:
            logger.error(f"Excel preprocessing failed: {e}")
            raise
        
        intermediate_format = {
            "document_type": "excel",
            "total_sheets": len(sheets_data),
            "sheets": sheets_data,
            "full_text": full_text
        }
        
        return full_text, metadata, intermediate_format
    
    def _preprocess_image(self, file_content: bytes, filename: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata, Dict[str, Any]]:
        """Preprocess image documents with advanced OCR enhancement"""
        file_stream = io.BytesIO(file_content)
        
        try:
            # Load and analyze image
            original_image = Image.open(file_stream)
            image_info = self._analyze_image(original_image)
            
            # Apply preprocessing based on image characteristics
            enhanced_image = self._enhance_image_for_ocr(original_image)
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(enhanced_image)
            
            # Try to detect document structure
            layout_info = self._detect_document_layout(enhanced_image)
            
            metadata.page_count = 1
            metadata.estimated_quality = self._estimate_ocr_quality(ocr_text)
            metadata.preprocessing_applied.extend([
                "image_enhancement",
                "noise_reduction", 
                "contrast_adjustment"
            ])
            
            if HAS_OPENCV:
                metadata.preprocessing_applied.append("deskewing")
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise
        
        intermediate_format = {
            "document_type": "image",
            "image_properties": image_info,
            "layout_detection": layout_info,
            "ocr_confidence": metadata.estimated_quality,
            "extracted_text": ocr_text
        }
        
        return ocr_text, metadata, intermediate_format
    
    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Apply comprehensive image enhancement for better OCR results"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Basic PIL-based enhancements that work without OpenCV
        enhanced_image = image
        
        # Apply sharpening
        enhanced_image = enhanced_image.filter(ImageFilter.SHARPEN)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(enhanced_image)
        enhanced_image = enhancer.enhance(1.2)
        
        # Enhance brightness if image is too dark
        enhancer = ImageEnhance.Brightness(enhanced_image)
        enhanced_image = enhancer.enhance(1.1)
        
        # Apply OpenCV enhancements if available
        if HAS_OPENCV:
            enhanced_image = self._opencv_enhancements(enhanced_image)
        
        return enhanced_image
    
    def _opencv_enhancements(self, image: Image.Image) -> Image.Image:
        """Apply OpenCV-based enhancements if available"""
        if not HAS_OPENCV or cv2 is None:
            return image
        
        try:
            # Convert to numpy array for OpenCV operations
            img_array = np.array(image)
            img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)  # type: ignore
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(img_gray)  # type: ignore
            
            # Deskewing
            deskewed = self._deskew_image(denoised)
            
            # Contrast enhancement with CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))  # type: ignore
            enhanced = clahe.apply(deskewed)  # type: ignore
            
            # Convert back to PIL Image
            result_image = Image.fromarray(enhanced)
            
            return result_image
        except Exception as e:
            logger.warning(f"OpenCV enhancements failed, using PIL fallback: {e}")
            return image
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Automatically detect and correct image skew"""
        if not HAS_OPENCV or cv2 is None:
            return image
        
        try:
            # Use Hough line transform to detect skew
            edges = cv2.Canny(image, 50, 150, apertureSize=3)  # type: ignore
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)  # type: ignore
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:10]:  # Use top 10 lines
                    angle = theta * 180 / np.pi
                    if angle < 45:
                        angles.append(angle)
                    elif angle > 135:
                        angles.append(angle - 180)
                
                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:  # Only correct if skew is significant
                        center = (image.shape[1] // 2, image.shape[0] // 2)
                        # Convert numpy float to Python float for OpenCV
                        angle_float = float(median_angle)
                        rotation_matrix = cv2.getRotationMatrix2D(center, angle_float, 1.0)  # type: ignore
                        image = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]),  # type: ignore
                                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)  # type: ignore
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
        
        return image
    
    def _analyze_image(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze image properties"""
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
            "aspect_ratio": image.width / image.height,
            "estimated_dpi": image.info.get('dpi', (72, 72))
        }
    
    def _detect_document_layout(self, image: Image.Image) -> Dict[str, Any]:
        """Detect document layout structure"""
        if HAS_OPENCV and cv2 is not None:
            try:
                # Convert to numpy array
                img_array = np.array(image.convert('L'))
                
                # Simple layout detection using contours
                contours, _ = cv2.findContours(img_array, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # type: ignore
                
                layout_info = {
                    "detected_regions": len(contours),
                    "layout_type": "single_column" if len(contours) < 5 else "multi_column",
                    "estimated_text_blocks": min(len(contours), 10),
                    "opencv_available": True
                }
            except Exception as e:
                logger.warning(f"OpenCV layout detection failed: {e}")
                layout_info = {
                    "detected_regions": 0,
                    "layout_type": "unknown",
                    "estimated_text_blocks": 1,
                    "opencv_available": True,
                    "detection_error": str(e)
                }
        else:
            # Fallback without OpenCV
            layout_info = {
                "detected_regions": 1,
                "layout_type": "unknown",
                "estimated_text_blocks": 1,
                "opencv_available": False
            }
        
        return layout_info
    
    def _estimate_ocr_quality(self, text: str) -> float:
        """Estimate OCR quality based on text characteristics"""
        if not text or len(text.strip()) == 0:
            return 0.0
        
        # Count various text quality indicators
        total_chars = len(text)
        alphabetic_chars = sum(c.isalpha() for c in text)
        digit_chars = sum(c.isdigit() for c in text)
        space_chars = sum(c.isspace() for c in text)
        special_chars = total_chars - alphabetic_chars - digit_chars - space_chars
        
        # Calculate quality score
        quality_score = 0.0
        
        # Higher score for more alphabetic content
        quality_score += (alphabetic_chars / total_chars) * 0.5
        
        # Bonus for reasonable word lengths
        words = text.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 3 <= avg_word_length <= 8:  # Reasonable word length
                quality_score += 0.2
        
        # Penalty for too many special characters (OCR errors)
        if special_chars / total_chars > 0.2:
            quality_score -= 0.3
        
        return max(0.0, min(1.0, quality_score))
    
    def _clean_text(self, text: str) -> str:
        """Apply general text cleaning and normalization"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        text = self._fix_common_ocr_errors(text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return '\n'.join(lines)
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """Fix common OCR recognition errors"""
        # Common character substitutions
        ocr_corrections = {
            'l': ['1', 'I', '|'],
            'I': ['l', '1', '|'],
            '1': ['l', 'I'],
            'O': ['0'],
            '0': ['O'],
            'S': ['5'],
            '5': ['S'],
            'G': ['6'],
            '6': ['G']
        }
        
        # Apply corrections in context-aware manner
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Simple heuristic: if word contains digits, prefer numeric characters
            if word.isalnum() and any(c.isdigit() for c in word):
                corrected_word = word
                for correct, errors in ocr_corrections.items():
                    for error in errors:
                        if error in word and correct.isdigit():
                            corrected_word = corrected_word.replace(error, correct)
                corrected_words.append(corrected_word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize DataFrame data"""
        if df.empty:
            return df
            
        # Make a copy to avoid modifying original
        df_clean = df.copy()
        
        # Clean column names
        df_clean.columns = df_clean.columns.astype(str)
        df_clean.columns = [col.strip().replace('\n', ' ').replace('\r', ' ') for col in df_clean.columns]
        
        # Remove completely empty rows and columns
        df_clean = df_clean.dropna(how='all', axis=0)  # Remove empty rows
        df_clean = df_clean.dropna(how='all', axis=1)  # Remove empty columns
        
        # Clean string columns (handle potential dtype issues)
        for col in df_clean.columns:
            try:
                if hasattr(df_clean[col], 'dtype') and df_clean[col].dtype == 'object':
                    df_clean[col] = df_clean[col].astype(str).str.strip()
            except Exception as e:
                logger.warning(f"Could not clean column {col}: {e}")
                # Convert to string as fallback
                df_clean[col] = df_clean[col].astype(str)
        
        return df_clean
    
    def _generate_dataframe_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for DataFrame"""
        if df.empty:
            return {
                "shape": {"rows": 0, "columns": 0},
                "column_info": {},
                "data_quality": {"null_percentage": 0, "duplicate_rows": 0}
            }
            
        summary = {
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "column_info": {},
            "data_quality": {
                "null_percentage": (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100 if len(df) > 0 and len(df.columns) > 0 else 0,
                "duplicate_rows": df.duplicated().sum()
            }
        }
        
        for col in df.columns:
            try:
                col_info = {
                    "data_type": str(df[col].dtype) if hasattr(df[col], 'dtype') else 'object',
                    "null_count": df[col].isnull().sum(),
                    "unique_values": df[col].nunique()
                }
                
                # Add numeric statistics if applicable
                if hasattr(df[col], 'dtype') and df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                    try:
                        col_info.update({
                            "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                            "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                            "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None
                        })
                    except Exception as e:
                        logger.warning(f"Could not compute statistics for column {col}: {e}")
                
                summary["column_info"][col] = col_info
            except Exception as e:
                logger.warning(f"Could not generate summary for column {col}: {e}")
                summary["column_info"][col] = {
                    "data_type": "unknown",
                    "null_count": 0,
                    "unique_values": 0,
                    "error": str(e)
                }
        
        return summary
    
    def _process_pdf_tables(self, tables: List) -> List[Dict[str, Any]]:
        """Process extracted PDF tables into structured format"""
        processed_tables = []
        
        for i, table in enumerate(tables):
            if table and len(table) > 0:  # Skip empty tables
                try:
                    # Convert table to DataFrame for easier processing
                    # Handle case where table might not have headers
                    if len(table) > 1 and table[0]:
                        df = pd.DataFrame(table[1:], columns=table[0])
                    else:
                        df = pd.DataFrame(table)
                    
                    # Only process if DataFrame has data
                    if not df.empty:
                        df_clean = self._clean_dataframe(df)
                        
                        table_info = {
                            "table_id": i + 1,
                            "rows": len(df_clean),
                            "columns": len(df_clean.columns),
                            "data": df_clean.to_dict('records'),
                            "summary": self._generate_dataframe_summary(df_clean)
                        }
                        processed_tables.append(table_info)
                except Exception as e:
                    logger.warning(f"Failed to process table {i + 1}: {e}")
                    # Add basic table info even if processing fails
                    processed_tables.append({
                        "table_id": i + 1,
                        "rows": len(table),
                        "columns": len(table[0]) if table and table[0] else 0,
                        "data": table,
                        "processing_error": str(e)
                    })
        
        return processed_tables
    
    def generate_xml_intermediate(self, text: str, metadata: DocumentMetadata, structured_data: Dict[str, Any]) -> str:
        """Generate standardized XML intermediate format"""
        root = ET.Element("document")
        
        # Add metadata
        meta_elem = ET.SubElement(root, "metadata")
        ET.SubElement(meta_elem, "type").text = metadata.document_type
        ET.SubElement(meta_elem, "format").text = metadata.file_format
        ET.SubElement(meta_elem, "pages").text = str(metadata.page_count)
        ET.SubElement(meta_elem, "quality").text = str(metadata.estimated_quality)
        ET.SubElement(meta_elem, "preprocessing").text = ','.join(metadata.preprocessing_applied)
        
        # Add content
        content_elem = ET.SubElement(root, "content")
        ET.SubElement(content_elem, "raw_text").text = text
        
        # Add structured data
        if structured_data:
            struct_elem = ET.SubElement(root, "structured_data")
            struct_elem.text = json.dumps(structured_data, indent=2)
        
        return ET.tostring(root, encoding='unicode')
