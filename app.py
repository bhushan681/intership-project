import streamlit as st
import pandas as pd
import json
import time
import os
from collections import defaultdict
from markitdown import MarkItDown
import google.generativeai as genai
from google.api_core import exceptions

# Configure Streamlit page layout
st.set_page_config(page_title="AI PO Extraction Portal", layout="centered")

st.title("📦 Purchase Order Extraction Portal")
st.subheader("Upload PO documents to extract validated structural data")

# SECURELY FETCH KEY (No user inputs shown)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🔒 Configuration Error: App API key not found in cloud setup.")
    st.stop()

# Initialize MarkItDown in-memory helper
md = MarkItDown()

# ==========================================
# SYSTEM INSTRUCTION
# ==========================================
SYSTEM_INSTRUCTION = """
You are an elite financial data extraction and validation agent. I will give you Markdown text ripped from a file group representing a single Purchase Order (PO) transaction. 

YOUR MISSION:
1. Document Verification: Determine if the document text reflects a finalized Purchase Order. If a file within the group is a quotation or estimate, ensure it does not corrupt or overwrite the fields of the actual Purchase Order.
2. Flat Data Extraction: Extract global header and financial values. Do NOT extract individual item lists, item details, or item quantities. 
3. Mathematical Validation: Verify and compute tax values to ensure financial integrity.
4. Data Integrity: Do not invent, estimate, or guess data. If a field is missing, return null.

STRICT EXTRACTION & VALIDATION RULES:

1. MIXED DOCUMENT / QUOTATION FILTER:
* If the text contains information from both a Quotation and a finalized Purchase Order, you must exclusively prioritize the data from the final Purchase Order. 
* If the entire file group contains ONLY a quotation/estimate and no valid PO exists, flag it: set "discrepancy_found": true and set "discrepancy_details": "REJECTED: Document is a QUOTATION/ESTIMATE, not a Purchase Order."

2. VENDOR CONTACT STRICT TARGETING:
* You must STRICTLY extract the phone number belonging to the VENDOR/SUPPLIER.
* EXCLUDE ALL OTHERS: You are absolutely forbidden from extracting phone numbers belonging to the "Site Engineer", "Delivery Location", "Buyer", or "Company Office".
* FORMAT: Prioritize the vendor's cell/mobile phone number. If the vendor also lists a landline/telephone number, include both separated by a slash (e.g., "+91 9876543210 / 020-123456"). If only one exists, output that one.

3. INTERNAL EMAIL EXCLUSION:
* You must STRICTLY extract the email address of the VENDOR/SUPPLIER.
* EXCLUDE INTERNAL EMAILS: You are absolutely forbidden from extracting "rupesh@architectsevolution.com" or ANY email address ending with "@architectsevolution.com". 
* If the only email addresses found on the document belong to Architects Evolution, you must output null for "email_id".

4. TAX MATHEMATICAL VALIDATION:
* If "tax_amount" is missing or empty in the text, but "total_amount" and "basic_amount" are present, calculate it precisely: tax_amount = total_amount - basic_amount.
* If all three values (Basic, Tax, Total) are present, cross-check the math: Is basic_amount + tax_amount == total_amount?
* If the math does not match up (off by more than 1 unit due to rounding), set "discrepancy_found": true and detail the mathematical mismatch in "discrepancy_details".

5. SYNONYMS FOR COLUMNS:
* "Site": Look for "Ship To", "Delivery Location", "Project Site", or "Workplace".
* "Basic Amount": Look for "Subtotal", "Amount Before Tax", "Taxable Value", or "Value of Goods".
* "Total Amount": Look for "Grand Total", "Net Payable", "PO Value", or "Total Including Tax".

OUTPUT EXACTLY IN THIS FLAT JSON SCHEMA (NO LINE ITEMS ARRAY):
{
    "po_number": "string or null",
    "po_date": "string or null",
    "site": "string or null",
    "vendor_name": "string or null",
    "contact_number": "string or null",
    "email_id": "string or null",
    "basic_amount": number or null,
    "tax_amount": number or null,
    "total_amount": number or null,
    "discrepancy_found": boolean,
    "discrepancy_details": "String explaining tax mismatches, quotation rejections, or null"
}
"""

# ==========================================
# INTERFACE & FILE UPLOAD
# ==========================================
uploaded_files = st.file_uploader(
    "Drag and drop your PO PDFs or Excel Files here", 
    type=["pdf", "xlsx", "xls"], 
    accept_multiple_files=True
)

if uploaded_files and st.button("🚀 Start Data Extraction", use_container_width=True):
    # Configure Gemini Client securely
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-flash-lite-latest',
        generation_config={"response_mime_type": "application/json"}
    )

    # Group uploaded files by their base filename
    file_groups = defaultdict(list)
    for uploaded_file in uploaded_files:
        base_name, _ = os.path.splitext(uploaded_file.name)
        file_groups[base_name].append(uploaded_file)

    master_data = []
    discrepancy_report = []
    missing_info_report = []

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_groups = len(file_groups)

    for idx, (base_name, files) in enumerate(file_groups.items()):
        status_text.text(f"Processing group ({idx+1}/{total_groups}): {base_name}...")
        
        combined_text = ""
        for f in files:
            combined_text += f"\n--- CONTENTS OF {f.name} ---\n"
            try:
                temp_path = f"temp_{f.name}"
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(f.getvalue())
                
                extracted = md.convert(temp_path)
                combined_text += extracted.text_content
                os.remove(temp_path)
            except Exception as e:
                combined_text += f"[Error reading file: {e}]"

        # AI Extraction with Guardrails for Limits
        try:
            response = model.generate_content(
                SYSTEM_INSTRUCTION + "\n\n" + combined_text,
                request_options={"timeout": 120}
            )
            
            clean_response = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_response)
            
            if data.get("discrepancy_found"):
                discrepancy_report.append({
                    "PO Number": data.get("po_number", base_name),
                    "Files Checked": ", ".join([f.name for f in files]),
                    "Issue": data.get("discrepancy_details")
                })
            if not data.get("contact_number") or not data.get("email_id"):
                missing_info_report.append({
                    "PO Number": data.get("po_number", base_name),
                    "Vendor Name": data.get("vendor_name", "Unknown"),
                    "Missing Contact": "Yes" if not data.get("contact_number") else "No",
                    "Missing Email": "Yes" if not data.get("email_id") else "No"
                })

            master_data.append({
                "PO Number": data.get("po_number"),
                "PO Date": data.get("po_date"),
                "Site": data.get("site"),
                "Vendor Name": data.get("vendor_name"),
                "Contact Number": data.get("contact_number"),
                "Email ID": data.get("email_id"),
                "Basic Amount": data.get("basic_amount"),
                "Tax Amount": data.get("tax_amount"),
                "Total Amount": data.get("total_amount")
            })

        except exceptions.ResourceExhausted:
            st.error(f"⚠️ **API Limit Reached!** Rate limits hit. Please wait a minute before processing remaining items.")
            break
        except exceptions.GoogleAPICallError as api_err:
            st.error(f"⚠️ **Gemini Server Error:** {api_err.message}")
            break
        except Exception as e:
            st.warning(f"Failed parsing group {base_name}: {e}")

        progress_bar.progress((idx + 1) / total_groups)
        time.sleep(4)  # Cooldown pacing to avoid spamming the API

    status_text.text("Extraction completed.")

    # ==========================================
    # BUILD EXCEL EXPORT AFTER COMPLETION
    # ==========================================
    if master_data:
        master_df = pd.DataFrame(master_data)
        master_df.drop_duplicates(subset=['PO Number'], keep='first', inplace=True)
        master_df.dropna(subset=['PO Number'], inplace=True)
        
        clean_target_columns = ["PO Number", "PO Date", "Site", "Vendor Name", "Contact Number", "Email ID", "Basic Amount", "Tax Amount", "Total Amount"]
        master_df = master_df.reindex(columns=clean_target_columns)

        output_filename = "extracted_po_report.xlsx"
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            master_df.to_excel(writer, sheet_name='Master PO Data', index=False)
            pd.DataFrame(missing_info_report).to_excel(writer, sheet_name='Missing Info Report', index=False)
            pd.DataFrame(discrepancy_report).to_excel(writer, sheet_name='Discrepancies', index=False)
        
        st.success("🎉 Processing Complete! Data is ready for download.")
        st.download_button(
            label="📥 Download Processed Excel File",
            data=buffer.getvalue(),
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(master_df)
    else:
        st.error("No valid PO Data structural layers could be extracted.")