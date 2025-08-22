#!/usr/bin/env python3
"""
Example script demonstrating the multi-page document processing features
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"  # Replace with your actual API key

def upload_and_process_document(filepath, page_start=None, page_end=None, output_format="combined"):
    """
    Upload and process a document with multi-page options
    
    Args:
        filepath: Path to the PDF file
        page_start: Starting page number (1-indexed)
        page_end: Ending page number (1-indexed) 
        output_format: "combined" or "per_page"
    """
    
    # Prepare the multipart form data
    files = {'file': open(filepath, 'rb')}
    data = {
        'output_format': output_format
    }
    
    # Add page range parameters if specified
    if page_start is not None:
        data['page_start'] = page_start
    if page_end is not None:
        data['page_end'] = page_end
    
    headers = {'X-API-Key': API_KEY}
    
    print(f"📄 Uploading document: {filepath}")
    if page_start or page_end:
        print(f"📊 Page range: {page_start or 1}-{page_end or 'end'}")
    print(f"🔄 Output format: {output_format}")
    
    # Upload the document
    try:
        response = requests.post(f"{BASE_URL}/v1/jobs", files=files, data=data, headers=headers)
        response.raise_for_status()
        
        job_data = response.json()
        job_id = job_data['job_id']
        
        print(f"✅ Job created successfully! Job ID: {job_id}")
        
        # Poll for completion
        print("⏳ Waiting for processing to complete...")
        
        while True:
            status_response = requests.get(f"{BASE_URL}/v1/jobs/{job_id}", headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            print(f"📊 Status: {status_data['status']} - {status_data.get('stage', 'N/A')} ({status_data.get('progress', 0)}%)")
            
            if status_data['status'] == 'SUCCESS':
                print("🎉 Processing completed successfully!")
                return status_data['result']
            elif status_data['status'] == 'FAILURE':
                print("❌ Processing failed!")
                print(f"Error: {status_data.get('result', 'Unknown error')}")
                return None
            
            time.sleep(2)  # Wait 2 seconds before polling again
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    finally:
        files['file'].close()

def main():
    """Demonstrate different multi-page processing scenarios"""
    
    print("🚀 Multi-Page Document Processing Examples")
    print("=" * 50)
    
    # Example 1: Process entire document with combined output
    print("\n📖 Example 1: Complete document processing (combined output)")
    result1 = upload_and_process_document(
        "sample-document.pdf",
        output_format="combined"
    )
    
    if result1:
        print("📋 Result structure:")
        print(f"   - Output format: {result1.get('output_format')}")
        print(f"   - Document type: {result1.get('document_type', 'N/A')}")
        if 'preprocessing_metadata' in result1:
            meta = result1['preprocessing_metadata']
            print(f"   - Total pages: {meta.get('page_count', 'N/A')}")
            print(f"   - Pages processed: {meta.get('pages_processed_count', 'N/A')}")
    
    # Example 2: Process specific page range with combined output
    print("\n📄 Example 2: Page range processing (pages 3-7, combined output)")
    result2 = upload_and_process_document(
        "sample-document.pdf",
        page_start=3,
        page_end=7,
        output_format="combined"
    )
    
    if result2:
        print("📋 Result structure:")
        print(f"   - Output format: {result2.get('output_format')}")
        if 'preprocessing_metadata' in result2:
            meta = result2['preprocessing_metadata']
            print(f"   - Pages processed: {meta.get('pages_processed_start')}-{meta.get('pages_processed_end')}")
    
    # Example 3: Process page range with per-page output
    print("\n📑 Example 3: Per-page analysis (pages 5-8)")
    result3 = upload_and_process_document(
        "sample-document.pdf",
        page_start=5,
        page_end=8,
        output_format="per_page"
    )
    
    if result3:
        print("📋 Result structure:")
        print(f"   - Output format: {result3.get('output_format')}")
        if 'pages' in result3:
            print(f"   - Individual pages analyzed: {len(result3['pages'])}")
            for i, page in enumerate(result3['pages'][:2]):  # Show first 2 pages
                print(f"     * Page {page.get('page_number')}: {page.get('extraction_method')} extraction")
                if 'structured_data' in page:
                    data_keys = list(page['structured_data'].keys())[:3]  # First 3 keys
                    print(f"       Data fields: {', '.join(data_keys)}...")

if __name__ == "__main__":
    print("⚠️  Note: Make sure to:")
    print("   1. Start your LDP server (uvicorn app.main:app --reload)")
    print("   2. Set your API_KEY in this script") 
    print("   3. Have a sample PDF file named 'sample-document.pdf'")
    print("   4. Install requests: pip install requests")
    print()
    
    # Uncomment the line below to run the examples
    # main()
    
    print("📚 Uncomment main() call to run the examples!")
