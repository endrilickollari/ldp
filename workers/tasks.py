from .celery_app import celery_app
from .smart_preprocessor import DocumentPreprocessor
from celery import states
from celery.exceptions import Ignore
import logging
import io
import json
import time
import re
import pandas as pd
import pdfplumber
import google.generativeai as genai  # type: ignore
from app.core.config import settings
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    if settings.GOOGLE_API_KEY:
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # type: ignore
    else:
        logger.warning("GOOGLE_API_KEY not configured. Please set it in your .env file.")
except Exception as e:
    logger.error(f"Failed to configure Google AI: {e}. Please set GOOGLE_API_KEY in your .env file.")

def extract_json_from_response(text: str) -> str:
    """
    Extracts a JSON string from a raw model response that might be
    wrapped in markdown code blocks.
    """
    # Find JSON wrapped in markdown fences
    match = re.search(r'```(json)?\s*({.*}|\[.*\])\s*```', text, re.DOTALL)
    if match:
        return match.group(2)
    
    # Fallback for JSON that starts at the beginning of the string but might have trailing text
    json_start = text.find('{')
    if json_start != -1:
        json_end = text.rfind('}')
        if json_end > json_start:
            return text[json_start:json_end+1]
            
    return text # Return original text if no clear JSON is found

def build_gemini_prompt(text_content: str, metadata: Optional[dict] = None, intermediate_data: Optional[dict] = None) -> str:
    """
    Builds a specialized Gemini prompt based on the detected document type.
    """
    doc_type = metadata.get('document_type', 'unknown') if metadata else 'unknown'

    # Router to select the appropriate prompt builder
    if 'invoice' in doc_type:
        return build_invoice_prompt(text_content, metadata)
    elif 'receipt' in doc_type:
        return build_receipt_prompt(text_content, metadata)
    elif 'contract' in doc_type:
        return build_contract_prompt(text_content, metadata)
    else:
        return build_generic_prompt(text_content, metadata)

def build_invoice_prompt(text_content: str, metadata: dict) -> str:
    """Generates a highly specific prompt for extracting data from invoices."""
    return f"""
**Your Role:** You are an expert AI specializing in invoice data extraction.

**Mission:** Analyze the invoice text and extract all key information into a structured JSON format. Pay close attention to detail.

**JSON Schema for Invoices:**
- `document_type`: "invoice"
- `invoice_number`: The unique invoice identifier.
- `issue_date`: The date the invoice was issued.
- `due_date`: The date payment is due.
- `vendor`: {{ "name": "...", "tax_id": "...", "address": "..." }}
- `customer`: {{ "name": "...", "tax_id": "...", "address": "..." }}
- `line_items`: [ {{ "description": "...", "quantity": ..., "unit_price": ..., "total_price": ... }} ]
- `financial_summary`: {{ "subtotal": ..., "tax_amount": ..., "total_amount": ..., "currency": "..." }}
- `payment_details`: {{ "method": "...", "iban": "...", "swift_code": "..." }}

**Critical Instructions:**
1.  **Extract All Fields:** Populate every field in the JSON schema. If a value is not present, use `null`.
2.  **Data Types:** Ensure all numbers (prices, quantities) are `float` or `int`, and dates are in `YYYY-MM-DD` format.
3.  **Line Items:** Accurately capture every single line item in the `line_items` array.
4.  **Return ONLY JSON:** Your response must be a valid JSON object and nothing else.

**Document Text to Analyze:**
---
{text_content}
---
    """

def build_receipt_prompt(text_content: str, metadata: dict) -> str:
    """Generates a highly specific prompt for extracting data from receipts."""
    return f"""
**Your Role:** You are a specialist AI for extracting data from sales receipts.

**Mission:** Analyze the receipt text and extract all key transaction details into a structured JSON format.

**JSON Schema for Receipts:**
- `document_type`: "receipt"
- `receipt_number`: The unique receipt identifier.
- `transaction_date`: The date of the transaction.
- `transaction_time`: The time of the transaction.
- `merchant`: {{ "name": "...", "address": "...", "phone_number": "..." }}
- `line_items`: [ {{ "description": "...", "quantity": ..., "unit_price": ..., "total_price": ... }} ]
- `financial_summary`: {{ "subtotal": ..., "tax_amount": ..., "total_amount": ..., "currency": "..." }}
- `payment_details`: {{ "method": "...", "card_type": "...", "last_four_digits": "..." }}

**Critical Instructions:**
1.  **Capture All Details:** Fill in all fields of the JSON schema. Use `null` for missing information.
2.  **Data Types:** Numbers must be `float` or `int`, dates `YYYY-MM-DD`, and time `HH:MM:SS`.
3.  **Payment Method:** Accurately identify the payment method (e.g., "Credit Card", "Cash") and any associated details.
4.  **Return ONLY JSON:** Your response must be a valid JSON object.

**Document Text to Analyze:**
---
{text_content}
---
    """

def build_contract_prompt(text_content: str, metadata: dict) -> str:
    """Generates a highly specific prompt for extracting data from contracts."""
    return f"""
**Your Role:** You are an AI expert in legal contract analysis.

**Mission:** Analyze the contract text and extract key legal and business terms into a structured JSON format.

**JSON Schema for Contracts:**
- `document_type`: "contract"
- `contract_title`: The title of the agreement.
- `effective_date`: The date the contract becomes effective.
- `termination_date`: The date the contract ends.
- `parties`: [ {{ "name": "...", "role": "...", "address": "..." }} ]
- `terms_and_conditions`: {{ "governing_law": "...", "confidentiality_clause": "...", "liability_clause": "..." }}
- `payment_terms`: {{ "amount": ..., "payment_schedule": "...", "currency": "..." }}

**Critical Instructions:**
1.  **Identify Parties:** List all parties involved in the contract with their roles (e.g., "Landlord", "Tenant").
2.  **Key Clauses:** Summarize the main points of important clauses like confidentiality and liability.
3.  **Dates are Crucial:** Accurately extract all relevant dates.
4.  **Return ONLY JSON:** Your response must be a valid JSON object.

**Document Text to Analyze:**
---
{text_content}
---
    """

def build_generic_prompt(text_content: str, metadata: dict) -> str:
    """
    Generates a generic but effective prompt for unknown document types.
    """
    return f"""
**Your Role:** You are an expert document analysis AI.

**Mission:** Analyze the document text and create a comprehensive JSON structure that captures all the information present.

**Critical Instructions:**
1.  **Infer Structure:** Determine the document's type (e.g., "report", "form", "statement") and create a logical JSON structure for it.
2.  **Use Descriptive Names:** Create clear, descriptive field names in English.
3.  **Capture Everything:** Do not miss any details—names, numbers, dates, addresses, etc.
4.  **Nested Objects:** Group related information into nested JSON objects.
5.  **Return ONLY JSON:** Your response must be a valid JSON object.

**Document Text to Analyze:**
---
{text_content}
---
    """

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def process_document(self, file_content: bytes, original_filename: str, metadata: Optional[dict] = None):
    start_time = time.time()  # Initialize start_time before try block
    try:
        logger.info(f"Starting smart preprocessing for job {self.request.id} on file {original_filename}")
        self.update_state(state='PROGRESS', meta={'stage': 'Smart Preprocessing', 'progress': 10})
        
        # Initialize the smart preprocessor
        preprocessor = DocumentPreprocessor()
        
        # Extract page processing parameters from metadata
        page_start = metadata.get('page_start') if metadata else None
        page_end = metadata.get('page_end') if metadata else None
        output_format = metadata.get('output_format', 'combined') if metadata else 'combined'
        
        try:
            # Apply smart preprocessing with page parameters
            extracted_text, doc_metadata, intermediate_data = preprocessor.preprocess_document(
                file_content, original_filename, page_start, page_end
            )
            
            logger.info(f"Smart preprocessing completed for {original_filename}:")
            logger.info(f"  - Document Type: {doc_metadata.document_type}")
            logger.info(f"  - Quality Score: {doc_metadata.estimated_quality:.2f}")
            logger.info(f"  - Pages: {doc_metadata.page_count}")
            logger.info(f"  - Preprocessing Applied: {', '.join(doc_metadata.preprocessing_applied)}")
            
        except Exception as e:
            logger.warning(f"Smart preprocessing failed, falling back to basic processing: {e}")
            # Fallback to basic processing if smart preprocessing fails
            extracted_text, doc_metadata, intermediate_data = self._fallback_processing(
                file_content, original_filename, page_start, page_end
            )
        
        self.update_state(state='PROGRESS', meta={'stage': 'Analyzing with Gemini', 'progress': 70})
        
        if not extracted_text.strip():
            logger.warning(f"No text extracted from {original_filename}. Completing job with empty result.")
            structured_result = {
                "document_metadata": {
                    "type": doc_metadata.document_type,
                    "quality": doc_metadata.estimated_quality,
                    "preprocessing_applied": doc_metadata.preprocessing_applied
                },
                "extraction_failed": True,
                "reason": "No text could be extracted from document"
            }
        else:
            # Convert metadata to dict for prompt building
            metadata_dict = {
                'document_type': doc_metadata.document_type,
                'file_format': doc_metadata.file_format,
                'estimated_quality': doc_metadata.estimated_quality,
                'page_count': doc_metadata.page_count,
                'pages_processed_start': doc_metadata.pages_processed_start,
                'pages_processed_end': doc_metadata.pages_processed_end,
                'pages_processed_count': doc_metadata.pages_processed_count,
                'preprocessing_applied': doc_metadata.preprocessing_applied
            }
            
            if output_format == 'per_page' and 'pages' in intermediate_data:
                # Process each page separately
                self.update_state(state='PROGRESS', meta={'stage': 'Processing Pages Individually', 'progress': 70})
                page_results = []
                
                for i, page_data in enumerate(intermediate_data['pages']):
                    page_text = page_data.get('content', '')
                    if page_text.strip():
                        # Generate prompt for individual page
                        page_prompt = build_gemini_prompt(page_text, metadata_dict, {'page_data': page_data})
                        
                        model = genai.GenerativeModel('gemini-2.5-flash-lite')  # type: ignore
                        page_response = model.generate_content(
                            page_prompt,
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        try:
                            cleaned_json = extract_json_from_response(page_response.text)
                            page_result = json.loads(cleaned_json)
                            page_results.append({
                                "page_number": page_data['page_number'],
                                "extraction_method": page_data['extraction_method'],
                                "structured_data": page_result,
                                "tables": page_data.get('tables', [])
                            })
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse AI response for page {page_data['page_number']}: {e}")
                            page_results.append({
                                "page_number": page_data['page_number'],
                                "extraction_method": page_data['extraction_method'],
                                "error": "Failed to parse AI response",
                                "raw_text": page_text[:500] + "..." if len(page_text) > 500 else page_text
                            })
                    
                    # Update progress
                    progress = 70 + int((i + 1) / len(intermediate_data['pages']) * 20)
                    self.update_state(state='PROGRESS', meta={'stage': f'Processing page {i+1}', 'progress': progress})
                
                structured_result = {
                    "output_format": "per_page",
                    "pages": page_results,
                    "preprocessing_metadata": {
                        "document_type": doc_metadata.document_type,
                        "file_format": doc_metadata.file_format,
                        "quality_score": doc_metadata.estimated_quality,
                        "page_count": doc_metadata.page_count,
                        "pages_processed_start": doc_metadata.pages_processed_start,
                        "pages_processed_end": doc_metadata.pages_processed_end,
                        "pages_processed_count": doc_metadata.pages_processed_count,
                        "preprocessing_applied": doc_metadata.preprocessing_applied,
                        "intermediate_data_available": bool(intermediate_data)
                    }
                }
            else:
                # Combined processing (original behavior)
                # Generate enhanced prompt with preprocessing context
                prompt = build_gemini_prompt(extracted_text, metadata_dict, intermediate_data)
                
                model = genai.GenerativeModel('gemini-2.5-flash-lite')  # type: ignore
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                self.update_state(state='PROGRESS', meta={'stage': 'Processing AI Response', 'progress': 90})
                
                try:
                    # Parse the JSON response
                    cleaned_json = extract_json_from_response(response.text)
                    llm_output = json.loads(cleaned_json)
                    
                    # Enhance the result with preprocessing metadata
                    structured_result = {
                        "output_format": "combined",
                        **llm_output,
                        "preprocessing_metadata": {
                            "document_type": doc_metadata.document_type,
                            "file_format": doc_metadata.file_format,
                            "quality_score": doc_metadata.estimated_quality,
                            "page_count": doc_metadata.page_count,
                            "pages_processed_start": doc_metadata.pages_processed_start,
                            "pages_processed_end": doc_metadata.pages_processed_end,
                            "pages_processed_count": doc_metadata.pages_processed_count,
                            "preprocessing_applied": doc_metadata.preprocessing_applied,
                            "intermediate_data_available": bool(intermediate_data)
                        }
                    }
                    
                    logger.info(f"Successfully processed document with {len(llm_output)} top-level fields and quality score {doc_metadata.estimated_quality:.2f}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM JSON response: {e}")
                    # Enhanced fallback with preprocessing context
                    structured_result = {
                        "output_format": "combined",
                        "raw_response": response.text,
                        "parsing_error": str(e),
                        "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
                        "preprocessing_metadata": {
                            "document_type": doc_metadata.document_type,
                            "file_format": doc_metadata.file_format,
                            "quality_score": doc_metadata.estimated_quality,
                            "page_count": doc_metadata.page_count,
                            "pages_processed_start": doc_metadata.pages_processed_start,
                            "pages_processed_end": doc_metadata.pages_processed_end,
                            "pages_processed_count": doc_metadata.pages_processed_count,
                            "preprocessing_applied": doc_metadata.preprocessing_applied,
                            "intermediate_data_available": bool(intermediate_data)
                        }
                    }

        final_meta = {'stage': 'Completed', 'progress': 100, 'result': structured_result}
        self.update_state(state=states.SUCCESS, meta=final_meta)
        
        # Update usage log if metadata provided
        if metadata and 'usage_log_id' in metadata:
            try:
                from app.database import SessionLocal
                from app.models.user import UsageLog
                
                db = SessionLocal()
                usage_log = db.query(UsageLog).filter(UsageLog.id == metadata['usage_log_id']).first()
                if usage_log:
                    setattr(usage_log, 'success', True)
                    setattr(usage_log, 'processing_time_seconds', time.time() - start_time)
                    # Estimate tokens used based on response length
                    setattr(usage_log, 'tokens_used', len(json.dumps(structured_result)) // 4)  # Rough estimate
                    db.commit()
                db.close()
            except Exception as e:
                logger.warning(f"Failed to update usage log: {e}")
        
        return final_meta

    except Exception as e:
        logger.error(f"Task failed for job {self.request.id}: {e}", exc_info=True)
        
        # Update usage log on failure
        if metadata and 'usage_log_id' in metadata:
            try:
                from app.database import SessionLocal
                from app.models.user import UsageLog
                
                db = SessionLocal()
                usage_log = db.query(UsageLog).filter(UsageLog.id == metadata['usage_log_id']).first()
                if usage_log:
                    setattr(usage_log, 'success', False)
                    setattr(usage_log, 'error_message', str(e))
                    setattr(usage_log, 'processing_time_seconds', time.time() - start_time)
                    db.commit()
                db.close()
            except Exception as log_error:
                logger.warning(f"Failed to update usage log on error: {log_error}")
        
        self.update_state(state=states.FAILURE, meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise Ignore()

def _fallback_processing(file_content: bytes, filename: str, page_start: Optional[int] = None, page_end: Optional[int] = None):
    """Fallback processing method using the original approach"""
    from .smart_preprocessor import DocumentMetadata
    
    logger.info(f"Using fallback processing for {filename}")
    
    extracted_text = ""
    file_stream = io.BytesIO(file_content)
    file_extension = '.' + filename.lower().split('.')[-1] if '.' in filename else ''

    if filename.lower().endswith('.pdf'):
        try:
            with pdfplumber.open(file_stream) as pdf:
                # Determine page range
                total_pages = len(pdf.pages)
                start_page = max(1, page_start or 1)
                end_page = min(total_pages, page_end or total_pages)
                
                logger.info(f"Fallback processing pages {start_page}-{end_page} of {total_pages} total pages")
                
                # Extract text from specified page range
                page_texts = []
                for page_num, page in enumerate(pdf.pages, 1):
                    if start_page <= page_num <= end_page:
                        page_text = page.extract_text()
                        if page_text:
                            page_texts.append(page_text)
                
                extracted_text = "\n".join(page_texts)
            logger.info("Extracted text from text-based PDF.")
        except Exception:
            from PIL import Image
            import pytesseract
            logger.warning("Failed to parse as text-based PDF, attempting OCR.")
            with pdfplumber.open(file_stream) as pdf:
                # Apply same page range logic for OCR
                total_pages = len(pdf.pages)
                start_page = max(1, page_start or 1)
                end_page = min(total_pages, page_end or total_pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    if start_page <= page_num <= end_page:
                        img = page.to_image(resolution=300).original
                        extracted_text += pytesseract.image_to_string(img) + "\n"
            logger.info("Extracted text from image-based PDF using OCR.")
    elif filename.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file_stream)
        extracted_text = df.to_string()
        logger.info("Extracted data from Excel file.")
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        from PIL import Image
        import pytesseract
        image = Image.open(file_stream)
        extracted_text = pytesseract.image_to_string(image)
        logger.info("Extracted text from image using OCR.")
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Determine page count for metadata
    page_count = 1
    if filename.lower().endswith('.pdf'):
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                page_count = len(pdf.pages)
        except:
            page_count = 1

    # Create basic metadata
    metadata = DocumentMetadata(
        document_type='pdf' if filename.lower().endswith('.pdf') else 'unknown',
        file_format=file_extension,
        page_count=page_count,
        estimated_quality=0.5,  # Basic fallback quality
        preprocessing_applied=['fallback_processing'],
        pages_processed_start=page_start,
        pages_processed_end=page_end,
        pages_processed_count=(page_end or page_count) - (page_start or 1) + 1 if page_start or page_end else page_count
    )
    
    # Basic intermediate data
    intermediate_data = {
        'document_type': 'unknown',
        'fallback_used': True,
        'full_text': extracted_text
    }
    
    return extracted_text, metadata, intermediate_data
