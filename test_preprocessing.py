"""
Smart Preprocessing Test Utility

This script provides testing and demonstration capabilities for the smart document preprocessing system.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from workers.smart_preprocessor import DocumentPreprocessor, DocumentMetadata
from workers.preprocessing_config import get_quality_label, QUALITY_THRESHOLDS

def test_preprocessing(file_path: str, verbose: bool = True) -> Dict[str, Any]:
    """Test the smart preprocessing on a single file"""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Read file content
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    filename = os.path.basename(file_path)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Testing Smart Preprocessing: {filename}")
        print(f"File size: {len(file_content)} bytes")
        print(f"{'='*60}")
    
    # Initialize preprocessor
    preprocessor = DocumentPreprocessor()
    
    # Run preprocessing
    start_time = time.time()
    try:
        extracted_text, metadata, intermediate_data = preprocessor.preprocess_document(
            file_content, filename
        )
        processing_time = time.time() - start_time
        success = True
        error = None
        
    except Exception as e:
        processing_time = time.time() - start_time
        success = False
        error = str(e)
        extracted_text = ""
        metadata = DocumentMetadata("unknown", "", 0, 0.0)
        intermediate_data = {}
    
    # Generate results
    results = {
        "filename": filename,
        "success": success,
        "processing_time": round(processing_time, 3),
        "error": error,
        "metadata": {
            "document_type": metadata.document_type,
            "file_format": metadata.file_format,
            "page_count": metadata.page_count,
            "quality_score": metadata.estimated_quality,
            "quality_label": get_quality_label(metadata.estimated_quality),
            "preprocessing_applied": metadata.preprocessing_applied
        },
        "extraction": {
            "text_length": len(extracted_text),
            "text_preview": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
            "word_count": len(extracted_text.split()) if extracted_text else 0,
            "has_content": bool(extracted_text.strip())
        },
        "intermediate_data_keys": list(intermediate_data.keys()) if intermediate_data else []
    }
    
    if verbose:
        print_results(results, intermediate_data)
    
    return results

def print_results(results: Dict[str, Any], intermediate_data: Dict[str, Any]):
    """Print detailed results"""
    
    print(f"\n📄 Processing Results:")
    print(f"   Status: {'✅ Success' if results['success'] else '❌ Failed'}")
    print(f"   Time: {results['processing_time']}s")
    
    if results['error']:
        print(f"   Error: {results['error']}")
        return
    
    metadata = results['metadata']
    print(f"\n📊 Document Analysis:")
    print(f"   Type: {metadata['document_type']}")
    print(f"   Format: {metadata['file_format']}")
    print(f"   Pages: {metadata['page_count']}")
    print(f"   Quality: {metadata['quality_score']:.2f} ({metadata['quality_label']})")
    
    if metadata['preprocessing_applied']:
        print(f"   Preprocessing: {', '.join(metadata['preprocessing_applied'])}")
    
    extraction = results['extraction']
    print(f"\n📝 Text Extraction:")
    print(f"   Text Length: {extraction['text_length']} characters")
    print(f"   Word Count: {extraction['word_count']} words")
    print(f"   Has Content: {'Yes' if extraction['has_content'] else 'No'}")
    
    if extraction['text_preview']:
        print(f"\n📖 Content Preview:")
        print(f"   {extraction['text_preview']}")
    
    if results['intermediate_data_keys']:
        print(f"\n🔧 Intermediate Data Available:")
        print(f"   Keys: {', '.join(results['intermediate_data_keys'])}")
        
        # Show some intermediate data details
        if 'pdf' in intermediate_data.get('document_type', ''):
            pdf_data = intermediate_data
            print(f"   PDF Details: {pdf_data.get('text_based_pages', 0)} text pages, "
                  f"{pdf_data.get('image_based_pages', 0)} OCR pages")
        
        if 'excel' in intermediate_data.get('document_type', ''):
            excel_data = intermediate_data
            print(f"   Excel Details: {excel_data.get('total_sheets', 0)} sheets")
        
        if 'image' in intermediate_data.get('document_type', ''):
            image_data = intermediate_data
            props = image_data.get('image_properties', {})
            if props:
                print(f"   Image Details: {props.get('width', 0)}x{props.get('height', 0)} pixels")

def batch_test(directory_path: str, extensions: Optional[list] = None) -> Dict[str, Any]:
    """Test preprocessing on multiple files in a directory"""
    
    if extensions is None:
        extensions = ['.pdf', '.xlsx', '.xls', '.png', '.jpg', '.jpeg']
    
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    results = []
    total_files = 0
    successful_files = 0
    total_time = 0
    
    print(f"\n{'='*60}")
    print(f"Batch Testing Smart Preprocessing")
    print(f"Directory: {directory_path}")
    print(f"Extensions: {', '.join(extensions)}")
    print(f"{'='*60}")
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            total_files += 1
            
            try:
                result = test_preprocessing(str(file_path), verbose=False)
                results.append(result)
                
                if result['success']:
                    successful_files += 1
                
                total_time += result['processing_time']
                
                # Quick status
                status = "✅" if result['success'] else "❌"
                quality = result['metadata']['quality_score']
                print(f"{status} {file_path.name} - Quality: {quality:.2f} - Time: {result['processing_time']}s")
                
            except Exception as e:
                print(f"❌ {file_path.name} - Error: {str(e)}")
                results.append({
                    "filename": file_path.name,
                    "success": False,
                    "error": str(e),
                    "processing_time": 0
                })
    
    # Summary
    success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
    avg_time = total_time / total_files if total_files > 0 else 0
    
    summary = {
        "total_files": total_files,
        "successful_files": successful_files,
        "failed_files": total_files - successful_files,
        "success_rate": round(success_rate, 1),
        "total_time": round(total_time, 3),
        "average_time": round(avg_time, 3),
        "results": results
    }
    
    print(f"\n📈 Batch Results Summary:")
    print(f"   Total Files: {total_files}")
    print(f"   Successful: {successful_files}")
    print(f"   Failed: {total_files - successful_files}")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Total Time: {total_time:.3f}s")
    print(f"   Average Time: {avg_time:.3f}s per file")
    
    return summary

def quality_analysis(results: list) -> Dict[str, Any]:
    """Analyze quality distribution from test results"""
    
    quality_counts = {"excellent": 0, "good": 0, "fair": 0, "poor": 0, "very_poor": 0}
    quality_scores = []
    
    for result in results:
        if result['success']:
            quality = result['metadata']['quality_score']
            quality_scores.append(quality)
            label = get_quality_label(quality)
            quality_counts[label] += 1
    
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        min_quality = min(quality_scores)
        max_quality = max(quality_scores)
    else:
        avg_quality = min_quality = max_quality = 0.0
    
    analysis = {
        "quality_distribution": quality_counts,
        "statistics": {
            "average_quality": round(avg_quality, 3),
            "min_quality": round(min_quality, 3),
            "max_quality": round(max_quality, 3),
            "total_processed": len(quality_scores)
        }
    }
    
    return analysis

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Smart Document Preprocessing")
    parser.add_argument("path", help="File or directory path to test")
    parser.add_argument("--batch", action="store_true", help="Process directory of files")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--extensions", nargs="+", default=[".pdf", ".xlsx", ".png", ".jpg"],
                       help="File extensions to process (for batch mode)")
    
    args = parser.parse_args()
    
    try:
        if args.batch:
            results = batch_test(args.path, args.extensions)
            
            # Quality analysis
            quality_analysis_result = quality_analysis(results['results'])
            results['quality_analysis'] = quality_analysis_result
            
            print(f"\n🎯 Quality Analysis:")
            for label, count in quality_analysis_result['quality_distribution'].items():
                percentage = (count / quality_analysis_result['statistics']['total_processed'] * 100) if quality_analysis_result['statistics']['total_processed'] > 0 else 0
                print(f"   {label.title()}: {count} files ({percentage:.1f}%)")
            
        else:
            results = test_preprocessing(args.path)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
