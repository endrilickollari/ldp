from pydantic import BaseModel, Field
from typing import List, Optional, Any
import uuid

# --- API Schemas ---

class JobCreateResponse(BaseModel):
    job_id: str  # Changed from uuid.UUID to str
    status: str
    status_url: str

class JobStatusResponse(BaseModel):
    job_id: str  # Changed from uuid.UUID to str
    status: str
    stage: Optional[str] = None
    progress: Optional[int] = None
    result: Optional[Any] = None  # Changed to Any to handle strings and dicts
    
    # Allow extra fields for dynamic content
    class Config:
        extra = "allow"

# --- LLM Output Schema ---

class VendorInfo(BaseModel):
    name: Optional[str] = Field(None, description="The name/company of the vendor.")
    tax_id: Optional[str] = Field(None, description="Tax identification number (NIPT).")
    address: Optional[str] = Field(None, description="Complete vendor address.")

class CustomerInfo(BaseModel):
    name: Optional[str] = Field(None, description="The name/company of the customer/buyer.")
    tax_id: Optional[str] = Field(None, description="Customer tax identification number (NIPT).")
    address: Optional[str] = Field(None, description="Complete customer address.")
    country: Optional[str] = Field(None, description="Customer country code.")

class LineItem(BaseModel):
    description: str = Field(description="Description of the product/service.")
    code: Optional[str] = Field(None, description="Product/service code.")
    unit: Optional[str] = Field(None, description="Unit of measurement.")
    quantity: float = Field(description="Quantity of the item.")
    unit_price: float = Field(description="Price per unit excluding tax.")
    total_price_no_tax: Optional[float] = Field(None, description="Total price without tax.")
    tax_rate: Optional[str] = Field(None, description="Tax rate applied.")
    total_price_with_tax: Optional[float] = Field(None, description="Total price including tax.")

class TaxInfo(BaseModel):
    tax_type: Optional[str] = Field(None, description="Type of tax (e.g., 'TVSH', 'VAT').")
    taxable_amount: Optional[float] = Field(None, description="Amount subject to tax.")
    tax_amount: Optional[float] = Field(None, description="Tax amount.")

class BankInfo(BaseModel):
    bank_name: Optional[str] = Field(None, description="Name of the bank.")
    swift_code: Optional[str] = Field(None, description="SWIFT/BIC code.")
    iban: Optional[str] = Field(None, description="IBAN account number.")
    currency: Optional[str] = Field(None, description="Account currency.")

class ExtractedData(BaseModel):
    # Invoice Header
    invoice_number: Optional[str] = Field(None, description="The unique invoice number.")
    invoice_date: Optional[str] = Field(None, description="Date the invoice was issued.")
    due_date: Optional[str] = Field(None, description="Payment due date.")
    invoice_type: Optional[str] = Field(None, description="Type of invoice (e.g., 'Tax Invoice').")
    
    # Parties
    vendor: Optional[VendorInfo] = Field(None, description="Vendor/seller information.")
    customer: Optional[CustomerInfo] = Field(None, description="Customer/buyer information.")
    
    # Payment Details
    payment_method: Optional[str] = Field(None, description="Method of payment.")
    exchange_rate: Optional[str] = Field(None, description="Currency exchange rate if applicable.")
    
    # Line Items
    line_items: List[LineItem] = Field(default_factory=list, description="List of products/services.")
    
    # Financial Summary
    subtotal_no_tax: Optional[float] = Field(None, description="Subtotal amount without tax.")
    total_tax: Optional[float] = Field(None, description="Total tax amount.")
    total_with_tax: Optional[float] = Field(None, description="Total amount including tax.")
    
    # Tax Breakdown
    tax_details: List[TaxInfo] = Field(default_factory=list, description="Detailed tax information.")
    
    # Banking Information
    bank_details: List[BankInfo] = Field(default_factory=list, description="Bank account information.")
    
    # Additional Fields
    operator_id: Optional[str] = Field(None, description="Operator or employee ID.")
    location_id: Optional[str] = Field(None, description="Business location identifier.")
    reference_codes: Optional[dict] = Field(None, description="Various reference codes (NSLF, NIVF, etc.).")
    
    # Currency Information
    primary_currency: Optional[str] = Field(None, description="Primary currency of the invoice.")
    secondary_currency: Optional[str] = Field(None, description="Secondary currency if applicable.")
    primary_total: Optional[float] = Field(None, description="Total in primary currency.")
    secondary_total: Optional[float] = Field(None, description="Total in secondary currency.")
