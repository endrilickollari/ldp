#!/usr/bin/env python3
"""
Demo script showing the dynamic schema generation approach.
This simulates what would happen when processing your Albanian invoice.
"""

from workers.tasks import build_gemini_prompt

def demo_dynamic_schema():
    # Your Albanian invoice text
    invoice_text = """
Prodigia
Endri Liçkollari
NIPT:
M31509050U
Adresa:
Tirane
, Tirane
Rruga Frosina Plaku, Pallati 21, Shaklla B, Apartamenti 9,
FATURË
BLERËSI:
Jona Salillari
Adresa:
Shteti:
NIPT:
ALB
M41703038B
Rruga Skënder Kosturi , Nd. 68, H.2, Ap. 28, Tirane
Data:
12-08-2025 12:11:36
Numri:
8/2025
Operatori:
th137td149
Vendi i ushtrimit të veprimtarisë:
zv326lu756
Afati i pagesës:
11-09-2025
Mënyra e pagesës: Transaksion nga llogaria
Kursi i këmbimit:
EUR 1x97.23
Lloji i faturës:
Faturë tatimore
Artikulli/ Shërbimi Kodi Njësia Sasia Çmimi pa TVSH Vlefta pa TVSH TVSH Vlefta me TVSH
IT Consulting &
Developments ICD Vlere
monetare 1.00 1,600.00 1,600.00 Pa TVSH 1,600.00
Nivelet e TVSH
TVSH Vlera pa TVSH Vlera e TVSH
Pa TVSH 1600 0
Total pa TVSH 1,600.00 EUR
TVSH 0.00 EUR
Total me TVSH 1,600.00 EUR
Total pa TVSH 155,568.00 LEK
TVSH 0.00 LEK
Total me TVSH 155,568.00 LEK
Llogaritë
Banka SWIFT IBAN Monedha
Banka Kombëtare Tregtare NCBAALTX 422010580CLPRCLALLB ALL
NSLF: 918132B0A4FD7C5FB51520E6AA94DDB0
NIVF: 2228be71-e301-488a-bb8b-777a4673d60b
"""

    print("🧪 Dynamic Schema Generation Demo")
    print("=" * 50)
    print("📄 Input: Albanian Invoice (complex multi-currency document)")
    print("\n🤖 Generating dynamic prompt for LLM...")
    
    # Generate the prompt - note: no predefined schema needed!
    prompt = build_gemini_prompt(invoice_text)
    
    print("✅ Dynamic prompt generated!")
    print(f"📊 Prompt length: {len(prompt):,} characters")
    print("\n🎯 Key advantages of this approach:")
    print("  • No predefined schema limitations")
    print("  • LLM adapts to ANY document type")
    print("  • Captures ALL available information")
    print("  • Creates optimal structure for each document")
    print("  • Handles multi-language documents")
    print("  • Preserves exact formatting and values")
    
    print("\n📋 Expected comprehensive output would include:")
    print("  • Document type identification")
    print("  • Complete vendor details (name, NIPT, address)")
    print("  • Complete customer details (name, NIPT, address, country)")
    print("  • Invoice metadata (number, dates, operator, location)")
    print("  • Detailed line items with all fields")
    print("  • Multi-currency financial breakdowns")
    print("  • Tax information and calculations")
    print("  • Banking details (bank, SWIFT, IBAN)")
    print("  • System reference codes (NSLF, NIVF)")
    print("  • Payment terms and methods")
    
    print("\n🚀 With this approach, your Albanian invoice will be fully parsed!")
    print("   Instead of just 4 fields, you'll get 20+ structured data points!")

if __name__ == "__main__":
    demo_dynamic_schema()
