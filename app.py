import streamlit as st
import pandas as pd
import json
import time
import os
import io
import zipfile
import tempfile
from collections import defaultdict
from markitdown import MarkItDown
import google.generativeai as genai
from google.api_core import exceptions

# Configure Streamlit page layout
st.set_page_config(page_title="AI PO Processing Suite", layout="centered")

st.title("📦 Enterprise Purchase Order Processing Engine")
st.subheader("Upload raw PO sheets, PDFs, or a compressed .ZIP file archive")

# SECURELY FETCH KEY 
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🔒 Configuration Error: App API key not found in cloud setup.")
    st.stop()

# Initialize MarkItDown globally
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
# INTERFACE & FILE UPLOAD LAYOUT
# ==========================================
uploaded_files = st.file_uploader(
    "Drag and drop PDFs, Excels, or a single .ZIP folder package", 
    type=["pdf", "xlsx", "xls", "zip"], 
    accept_multiple_files=True
)

if uploaded_files and st.button("🚀 Start Production Pipeline", use_container_width=True):
    
    # Initialize Core API Parameters Securely
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-flash-lite-latest',
        generation_config={"response_mime_type": "application/json"}
    )

    # In-Memory Extraction & Grouping Mapping Dictionary
    file_groups = defaultdict(list)
    
    # Check if a ZIP payload was provided
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        
        if filename.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read())) as z:
                for file_info in z.infolist():
                    # Filter internal system files
                    if file_info.is_dir() or file_info.filename.startswith('__MACOSX') or os.path.basename(file_info.filename).startswith('.'):
                        continue
                    
                    if file_info.filename.lower().endswith(('.pdf', '.xlsx', '.xls')):
                        file_bytes = z.read(file_info.filename)
                        base_name = os.path.splitext(os.path.basename(file_info.filename))[0]
                        file_groups[base_name].append({
                            "name": os.path.basename(file_info.filename),
                            "bytes": file_bytes
                        })
        else:
            if filename.lower().endswith(('.pdf', '.xlsx', '.xls')):
                base_name = os.path.splitext(filename)[0]
                file_groups[base_name].append({
                    "name": filename,
                    "bytes": uploaded_file.getvalue()
                })

    if not file_groups:
        st.error("No valid PDF or Excel transactional sheets discovered inside the payload structure.")
        st.stop()

    master_data = []
    discrepancy_report = []
    missing_info_report = []
    processed_count = 0

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_groups = len(file_groups)

    # Process Transaction Groups Loops
    for idx, (base_name, target_files) in enumerate(file_groups.items()):
        status_text.text(f"Extracting Group Data ({idx+1}/{total_groups}): {base_name}...")
        
        combined_text = ""
        for file_obj in target_files:
            combined_text += f"\n--- CONTENTS OF {file_obj['name']} ---\n"
            try:
                temp_path = f"temp_{file_obj['name']}"
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(file_obj['bytes'])
                
                extracted = md.convert(temp_path)
                combined_text += extracted.text_content
                os.remove(temp_path)
            except Exception as e:
                st.error(f"Failed: {file_obj['name']}")
                st.exception(e)
            combined_text += f"[Error processing tracking layers: {e}]"

        # Safe AI Extraction Handling Pipeline
        try:
            response = model.generate_content(
                SYSTEM_INSTRUCTION + "\n\n" + combined_text,
                request_options={"timeout": 120}
            )
            
            clean_response = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_response)
            
            # Capture Discrepancy Reporting Payload
            if data.get("discrepancy_found"):
                discrepancy_report.append({
                    "PO Number": data.get("po_number", base_name),
                    "Files Checked": ", ".join([f['name'] for f in target_files]),
                    "Issue": data.get("discrepancy_details")
                })
                
            # Capture Missing Information Reporting Payload
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
            processed_count += 1

        except exceptions.ResourceExhausted:
            st.error(f"⚠️ **API Quota Exhausted!** Rate limit encountered. Pipeline paused at transaction {base_name}.")
            break
        except exceptions.GoogleAPICallError as api_err:
            st.error(f"⚠️ **API Gateway Fault:** {api_err.message}")
            break
        except Exception as e:
            st.warning(f"Skipping extraction for execution frame {base_name}: {e}")

        progress_bar.progress((idx + 1) / total_groups)
        time.sleep(4) # Pacing cadence throttle

    status_text.text("Extraction runtime executed. Building validation matrices...")

    # ==========================================
    # VALIDATION, COMPILATION & EXCEL COMPILING
    # ==========================================
    if master_data:
        master_df = pd.DataFrame(master_data)
        
        # Calculate strict math validation flags matching your original script layout
        master_df['Math Valid'] = master_df.apply(
            lambda x: pd.isna(x['Total Amount']) or 
                      round((pd.to_numeric(x['Basic Amount'], errors='coerce') or 0) + 
                            (pd.to_numeric(x['Tax Amount'], errors='coerce') or 0), 2) == 
                      round(pd.to_numeric(x['Total Amount'], errors='coerce'), 2), 
            axis=1
        )
        
        # Deduplicate and scrub empty values matching original constraints
        master_df.drop_duplicates(subset=['PO Number'], keep='first', inplace=True)
        master_df.dropna(subset=['PO Number'], inplace=True)

        clean_target_columns = [
            "PO Number", "PO Date", "Site", "Vendor Name", "Contact Number", 
            "Email ID", "Basic Amount", "Tax Amount", "Total Amount", "Math Valid"
        ]
        master_df = master_df.reindex(columns=clean_target_columns)

        # Build Summary Report Data block structures
        summary_data = {
            "Metric": [
                "Total PO Groups Processed", 
                "Total Flat Rows Exported",
                "POs with Missing Contact/Email",
                "POs with PDF/Excel Discrepancies"
            ],
            "Count": [
                processed_count,
                len(master_df),
                len(missing_info_report),
                len(discrepancy_report)
            ]
        }
        summary_df = pd.DataFrame(summary_data)

        # Package data into structured Excel spreadsheet buffer stream
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            master_df.to_excel(writer, sheet_name='Master PO Data', index=False)
            pd.DataFrame(missing_info_report).to_excel(writer, sheet_name='Missing Info Report', index=False)
            pd.DataFrame(discrepancy_report).to_excel(writer, sheet_name='Discrepancies', index=False)
            summary_df.to_excel(writer, sheet_name='Validation Summary', index=False)
        
        st.success("🎉 Comprehensive Verification Log Compiled Successfully!")
        
        st.download_button(
            label="📥 Download Structured Excel Report Package",
            data=buffer.getvalue(),
            file_name="Structured_PO_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.subheader("Data Preview (Master PO Data)")
        st.dataframe(master_df)
    else:
        st.error("No records could be extracted due to systemic context drops or configuration failures.")
