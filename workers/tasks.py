from .celery_app import celery_app
from celery import states
from celery.exceptions import Ignore
import logging
import io
import json
import time
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

def build_gemini_prompt(text_content: str) -> str:
    return f"""
    **Your Role:** You are an expert document analysis AI that excels at understanding and structuring any type of business document or data.

    **Mission:** Analyze the provided document text and create the most comprehensive and logical JSON structure that captures ALL the information present. Think like a data analyst - what would be the most useful way to structure this data?

    **Critical Instructions:**
    1. **READ AND UNDERSTAND:** Carefully analyze the entire document to understand its type, purpose, and all the data it contains
    2. **CREATE OPTIMAL STRUCTURE:** Design a JSON structure that:
       - Captures EVERY piece of information from the document
       - Uses logical, descriptive field names
       - Groups related information into nested objects where appropriate
       - Uses arrays for multiple similar items
       - Preserves exact values, numbers, dates, and text as found
    3. **BE COMPREHENSIVE:** Don't miss any detail - names, numbers, dates, addresses, codes, references, totals, line items, etc.
    4. **USE SMART NAMING:** Use clear, descriptive field names in English (e.g., "invoice_number", "vendor_details", "line_items", "tax_breakdown")
    5. **HANDLE DIFFERENT DOCUMENT TYPES:** Whether it's an invoice, receipt, contract, report, or any other document - adapt the structure accordingly
    6. **RETURN ONLY JSON:** Your response must be ONLY a valid JSON object, no explanations or extra text

    **Examples of Good Structuring:**

    **For an Invoice:**
    ```json
    {{
      "document_type": "invoice",
      "invoice_number": "8/2025",
      "issue_date": "12-08-2025",
      "due_date": "11-09-2025",
      "vendor": {{
        "name": "Company Name",
        "tax_id": "M31509050U",
        "address": "Full address details"
      }},
      "customer": {{
        "name": "Customer Name",
        "tax_id": "M41703038B", 
        "address": "Customer address",
        "country": "ALB"
      }},
      "line_items": [
        {{
          "description": "IT Consulting & Developments",
          "code": "ICD",
          "unit": "Vlere monetare",
          "quantity": 1.0,
          "unit_price_excluding_tax": 1600.0,
          "total_excluding_tax": 1600.0,
          "tax_status": "Pa TVSH",
          "total_including_tax": 1600.0
        }}
      ],
      "financial_summary": {{
        "subtotal_excluding_tax": 1600.0,
        "total_tax": 0.0,
        "total_including_tax": 1600.0,
        "currency": "EUR"
      }},
      "currency_conversion": {{
        "primary_currency": "EUR",
        "secondary_currency": "LEK",
        "exchange_rate": "1x97.23",
        "total_in_lek": 155568.0
      }},
      "payment_details": {{
        "method": "Transaksion nga llogaria",
        "due_date": "11-09-2025"
      }},
      "banking_information": [
        {{
          "bank_name": "Banka Kombëtare Tregtare",
          "swift_code": "NCBAALTX",
          "iban": "422010580CLPRCLALLB",
          "currency": "ALL"
        }}
      ],
      "system_information": {{
        "operator_id": "th137td149",
        "location_id": "zv326lu756",
        "nslf_code": "918132B0A4FD7C5FB51520E6AA94DDB0",
        "nivf_code": "2228be71-e301-488a-bb8b-777a4673d60b"
      }},
      "tax_breakdown": [
        {{
          "tax_type": "Pa TVSH",
          "taxable_amount": 1600.0,
          "tax_amount": 0.0
        }}
      ]
    }}
    ```

    **For other document types, create appropriate structures. For example:**
    - Receipts: focus on transaction details, items, payment method
    - Contracts: focus on parties, terms, dates, obligations
    - Reports: focus on data categories, metrics, time periods
    - Forms: focus on field names and values

    **Document Text to Analyze:**
    ---
    {text_content}
    ---

    Analyze this document and create the most comprehensive JSON structure that captures all its information:
    """

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def process_document(self, file_content: bytes, original_filename: str, metadata: Optional[dict] = None):
    start_time = time.time()  # Initialize start_time before try block
    try:
        logger.info(f"Starting processing for job {self.request.id} on file {original_filename}")
        self.update_state(state='PROGRESS', meta={'stage': 'Parsing', 'progress': 25})
        
        extracted_text = ""
        file_stream = io.BytesIO(file_content)

        if original_filename.lower().endswith('.pdf'):
            try:
                with pdfplumber.open(file_stream) as pdf:
                    extracted_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                logger.info("Extracted text from text-based PDF.")
            except Exception:
                from PIL import Image
                import pytesseract
                logger.warning("Failed to parse as text-based PDF, attempting OCR.")
                with pdfplumber.open(file_stream) as pdf:
                    for page in pdf.pages:
                        img = page.to_image(resolution=300).original
                        extracted_text += pytesseract.image_to_string(img) + "\n"
                logger.info("Extracted text from image-based PDF using OCR.")
        elif original_filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_stream)
            extracted_text = df.to_string()
            logger.info("Extracted data from Excel file.")
        elif original_filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            from PIL import Image
            import pytesseract
            image = Image.open(file_stream)
            extracted_text = pytesseract.image_to_string(image)
            logger.info("Extracted text from image using OCR.")
        else:
            raise ValueError(f"Unsupported file type: {original_filename}")

        self.update_state(state='PROGRESS', meta={'stage': 'Analyzing with Gemini', 'progress': 70})
        
        if not extracted_text.strip():
            logger.warning(f"No text extracted from {original_filename}. Completing job with empty result.")
            structured_result = {}
        else:
            # Generate dynamic prompt without predefined schema
            prompt = build_gemini_prompt(extracted_text)
            
            model = genai.GenerativeModel('gemini-1.5-pro-latest')  # type: ignore
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            self.update_state(state='PROGRESS', meta={'stage': 'Processing AI Response', 'progress': 90})
            
            try:
                # Parse the JSON response - no schema validation, let LLM create its own structure
                llm_output = json.loads(response.text)
                structured_result = llm_output
                logger.info(f"Successfully received dynamic structured data from Gemini with {len(llm_output)} top-level fields.")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                # If JSON parsing fails, return the raw text as fallback
                structured_result = {
                    "raw_response": response.text,
                    "parsing_error": str(e),
                    "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
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
