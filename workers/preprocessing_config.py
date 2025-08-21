"""
Document Preprocessing Configuration

This file contains configuration settings for the smart document preprocessing pipeline.
"""

from typing import Dict, Any, List

# OCR Configuration
OCR_CONFIG = {
    "tesseract_config": "--oem 3 --psm 6",  # OCR Engine Mode and Page Segmentation Mode
    "language": "eng",  # Primary language for OCR
    "dpi": 300,  # Resolution for image to text conversion
    "confidence_threshold": 0.5,  # Minimum confidence for OCR results
}

# Image Enhancement Settings
IMAGE_ENHANCEMENT = {
    "enable_deskewing": True,
    "enable_denoising": True,
    "enable_contrast_enhancement": True,
    "enable_sharpening": True,
    "clahe_clip_limit": 2.0,  # Contrast Limited Adaptive Histogram Equalization
    "clahe_tile_grid_size": (8, 8),
    "gaussian_blur_kernel": 3,
    "sharpening_strength": 1.2,
    "brightness_adjustment": 1.1,
    "contrast_adjustment": 1.2,
}

# PDF Processing Settings
PDF_CONFIG = {
    "extract_tables": True,
    "extract_images": True,
    "fallback_to_ocr": True,
    "ocr_threshold": 50,  # If less than 50 chars extracted, try OCR
    "page_resolution": 300,
    "table_detection_settings": {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3
    }
}

# Excel Processing Settings
EXCEL_CONFIG = {
    "max_rows_preview": 100,  # Maximum rows to include in text output
    "include_formatting": False,
    "detect_merged_cells": True,
    "skip_empty_sheets": True,
    "clean_column_names": True,
    "infer_data_types": True
}

# Text Cleaning Configuration
TEXT_CLEANING = {
    "remove_excessive_whitespace": True,
    "fix_common_ocr_errors": True,
    "normalize_line_breaks": True,
    "remove_empty_lines": True,
    "min_word_length": 1,
    "max_special_char_ratio": 0.3,  # Maximum ratio of special chars to total
    "common_ocr_substitutions": {
        "l": ["1", "I", "|"],
        "I": ["l", "1", "|"],
        "1": ["l", "I"],
        "O": ["0"],
        "0": ["O"],
        "S": ["5"],
        "5": ["S"],
        "G": ["6"],
        "6": ["G"]
    }
}

# Quality Assessment Thresholds
QUALITY_THRESHOLDS = {
    "excellent": 0.9,   # 90%+ quality
    "good": 0.7,        # 70-89% quality  
    "fair": 0.5,        # 50-69% quality
    "poor": 0.3,        # 30-49% quality
    # Below 30% is considered very poor
}

# Supported File Formats
SUPPORTED_FORMATS = {
    "pdf": {
        "extensions": [".pdf"],
        "mime_types": ["application/pdf"],
        "max_size_mb": 50,
        "preprocessing_pipeline": ["text_extraction", "table_extraction", "ocr_fallback"]
    },
    "excel": {
        "extensions": [".xlsx", ".xls", ".csv"],
        "mime_types": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                      "application/vnd.ms-excel", "text/csv"],
        "max_size_mb": 25,
        "preprocessing_pipeline": ["dataframe_processing", "data_cleaning", "type_inference"]
    },
    "image": {
        "extensions": [".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
        "mime_types": ["image/png", "image/jpeg", "image/tiff", "image/bmp"],
        "max_size_mb": 20,
        "preprocessing_pipeline": ["image_enhancement", "ocr_extraction", "layout_detection"]
    }
}

# Preprocessing Pipeline Configuration
PIPELINE_CONFIG = {
    "enable_smart_preprocessing": True,
    "fallback_on_error": True,
    "log_preprocessing_steps": True,
    "save_intermediate_results": False,  # For debugging
    "parallel_processing": False,  # Future feature for multi-page docs
    "cache_enhanced_images": False,  # Cache enhanced images for reprocessing
}

# Advanced Features
ADVANCED_FEATURES = {
    "document_type_detection": True,
    "language_detection": False,  # Future feature
    "content_extraction_optimization": True,
    "structure_preservation": True,
    "metadata_enrichment": True,
}

# Logging Configuration for Preprocessing
PREPROCESSING_LOGGING = {
    "log_level": "INFO",
    "log_preprocessing_time": True,
    "log_quality_metrics": True,
    "log_applied_enhancements": True,
    "detailed_error_logging": True
}

def get_config_for_document_type(document_type: str) -> Dict[str, Any]:
    """Get configuration specific to document type"""
    configs = {
        "pdf": PDF_CONFIG,
        "excel": EXCEL_CONFIG,
        "image": IMAGE_ENHANCEMENT,
    }
    return configs.get(document_type, {})

def get_quality_label(quality_score: float) -> str:
    """Get quality label based on score"""
    if quality_score >= QUALITY_THRESHOLDS["excellent"]:
        return "excellent"
    elif quality_score >= QUALITY_THRESHOLDS["good"]:
        return "good"
    elif quality_score >= QUALITY_THRESHOLDS["fair"]:
        return "fair"
    elif quality_score >= QUALITY_THRESHOLDS["poor"]:
        return "poor"
    else:
        return "very_poor"

def is_format_supported(filename: str) -> bool:
    """Check if file format is supported"""
    file_ext = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
    for format_info in SUPPORTED_FORMATS.values():
        if file_ext in format_info["extensions"]:
            return True
    return False

def get_preprocessing_pipeline(document_type: str) -> List[str]:
    """Get preprocessing pipeline steps for document type"""
    format_info = SUPPORTED_FORMATS.get(document_type, {})
    return format_info.get("preprocessing_pipeline", ["basic_extraction"])
