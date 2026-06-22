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

# ==========================================
# PAGE CONFIGURATION & DESIGN SYSTEM
# ==========================================
st.set_page_config(page_title="AI PO Processing Suite", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS Design System
st.markdown("""
<style>
/* Design System Tokens */
:root {
    --primary-dark: #1E293B;
    --primary-accent: #0891B2;
    --accent-light: #06B6D4;
    --success-green: #10B981;
    --warning-amber: #F59E0B;
    --error-red: #EF4444;
    --neutral-50: #F9FAFB;
    --neutral-100: #F3F4F6;
    --neutral-200: #E5E7EB;
    --neutral-700: #374151;
    --neutral-900: #111827;
}

/* Global Typography */
body, * {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Main container */
.main {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

/* ==================== HERO HEADER ==================== */
.hero-container {
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
    padding: 3rem 2rem;
    border-radius: 12px;
    margin-bottom: 2.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
    border: 1px solid rgba(8, 145, 178, 0.1);
    position: relative;
    overflow: hidden;
}

.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(8, 145, 178, 0.15) 0%, transparent 70%);
    border-radius: 50%;
}

.hero-content {
    position: relative;
    z-index: 2;
    color: white;
}

.hero-title {
    font-size: 2.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0 0 0.75rem 0;
    line-height: 1.2;
    background: linear-gradient(135deg, #ffffff 0%, #cffafe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    font-size: 1.1rem;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.85);
    margin: 0;
    line-height: 1.6;
    max-width: 600px;
}

.hero-divider {
    width: 60px;
    height: 3px;
    background: linear-gradient(90deg, #0891B2, #06B6D4);
    margin: 1.5rem 0 1.5rem 0;
    border-radius: 2px;
}

.hero-instructions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-top: 2rem;
}

.instruction-item {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(8, 145, 178, 0.2);
    padding: 1rem;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.instruction-item:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(8, 145, 178, 0.4);
    transform: translateY(-2px);
}

.instruction-step {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.instruction-number {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, #0891B2, #06B6D4);
    border-radius: 50%;
    color: white;
    font-weight: 600;
    font-size: 0.9rem;
    flex-shrink: 0;
}

.instruction-text {
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.9);
    line-height: 1.4;
}

/* ==================== FILE UPLOADER ==================== */
.upload-container {
    background: white;
    border: 2px dashed #E5E7EB;
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
    transition: all 0.3s ease;
}

.upload-container:hover {
    border-color: #0891B2;
    background: rgba(8, 145, 178, 0.02);
}

.upload-label {
    font-size: 1rem;
    font-weight: 600;
    color: #1E293B;
    margin-bottom: 0.5rem;
    display: block;
}

.upload-hint {
    font-size: 0.9rem;
    color: #6B7280;
    margin-top: 0.5rem;
}

/* ==================== STATUS INDICATORS ==================== */
.status-container {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    border-left: 4px solid #0891B2;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.status-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    font-weight: 600;
    color: #1E293B;
}

.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: #DBEAFE;
    color: #0369A1;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.status-progress-bar {
    width: 100%;
    height: 6px;
    background: #E5E7EB;
    border-radius: 3px;
    overflow: hidden;
    margin: 1rem 0;
}

.status-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0891B2, #06B6D4);
    border-radius: 3px;
    transition: width 0.3s ease;
}

.status-text {
    font-size: 0.95rem;
    color: #4B5563;
    font-family: 'Monaco', 'Courier New', monospace;
    padding: 0.75rem;
    background: #F9FAFB;
    border-radius: 6px;
    border-left: 2px solid #0891B2;
}

.status-complete {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.05) 100%);
    border-left-color: #10B981;
}

.status-complete .status-badge {
    background: #DCFCE7;
    color: #166534;
}

/* ==================== METRIC CARDS ==================== */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
}

.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.75rem;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #0891B2, #06B6D4);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s ease;
}

.metric-card:hover {
    box-shadow: 0 4px 12px rgba(8, 145, 178, 0.15);
    border-color: #0891B2;
}

.metric-card:hover::before {
    transform: scaleX(1);
}

.metric-label {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6B7280;
    margin-bottom: 0.75rem;
}

.metric-value {
    font-size: 2.25rem;
    font-weight: 700;
    color: #1E293B;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}

.metric-subtext {
    font-size: 0.9rem;
    color: #6B7280;
    line-height: 1.4;
}

.metric-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

/* ==================== RESULTS TABS ==================== */
.tabs-container {
    margin: 2rem 0;
}

.results-header {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1E293B;
    margin: 2rem 0 1.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.results-section {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.download-button-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}

/* ==================== ALERTS ==================== */
.alert {
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    border-left: 4px solid;
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

.alert-success {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
    border-left-color: #10B981;
    color: #166534;
}

.alert-error {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
    border-left-color: #EF4444;
    color: #991B1B;
}

.alert-warning {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
    border-left-color: #F59E0B;
    color: #92400E;
}

.alert-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
}

.alert-content {
    flex: 1;
    font-size: 0.95rem;
    line-height: 1.5;
}

/* ==================== DATAFRAME ==================== */
.dataframe-container {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #E5E7EB;
}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 768px) {
    .hero-title {
        font-size: 1.75rem;
    }
    
    .hero-subtitle {
        font-size: 1rem;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .hero-instructions {
        grid-template-columns: 1fr;
    }
    
    .metric-value {
        font-size: 1.75rem;
    }
}

/* ==================== UTILITY CLASSES ==================== */
.divider {
    height: 1px;
    background: #E5E7EB;
    margin: 2rem 0;
}

.success-checkmark {
    color: #10B981;
    font-weight: bold;
}

.spacer-small {
    margin-bottom: 1rem;
}

.spacer-medium {
    margin-bottom: 2rem;
}

.spacer-large {
    margin-bottom: 3rem;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# HERO HEADER SECTION
# ==========================================
st.markdown("""
<div class="hero-container">
    <div class="hero-content">
        <h1 class="hero-title">📦 Enterprise PO Processing Suite</h1>
        <p class="hero-subtitle">Intelligent extraction and validation of purchase orders from PDFs, Excel sheets, and ZIP archives</p>
        <div class="hero-divider"></div>
        
        <div class="hero-instructions">
            <div class="instruction-item">
                <div class="instruction-step">
                    <div class="instruction-number">1</div>
                    <div>
                        <div class="instruction-text"><strong>Upload</strong> your PO files (PDF, Excel, or ZIP)</div>
                    </div>
                </div>
            </div>
            <div class="instruction-item">
                <div class="instruction-step">
                    <div class="instruction-number">2</div>
                    <div>
                        <div class="instruction-text"><strong>Process</strong> with AI extraction engine</div>
                    </div>
                </div>
            </div>
            <div class="instruction-item">
                <div class="instruction-step">
                    <div class="instruction-number">3</div>
                    <div>
                        <div class="instruction-text"><strong>Download</strong> validated structured data</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# FILE UPLOADER SECTION
# ==========================================
st.markdown("""
<div class="upload-container">
    <label class="upload-label">📄 Select Purchase Order Documents</label>
    <p class="upload-hint">Drop PDFs, Excel files, or a single ZIP archive containing multiple PO documents</p>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    label="Select files",
    type=["pdf", "xlsx", "xls", "zip"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# ==========================================
# SECURE API KEY CONFIGURATION
# ==========================================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.markdown("""
    <div class="alert alert-error">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <strong>Configuration Error:</strong> Gemini API key not found in secrets. 
            Please add GEMINI_API_KEY to your Streamlit secrets configuration.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Initialize MarkItDown globally
md = MarkItDown()

# ==========================================
# SYSTEM INSTRUCTION (DO NOT MODIFY)
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
# PROCESSING PIPELINE WITH STYLED STATUS
# ==========================================
process_button = st.button("🚀 Start Production Pipeline", use_container_width=True)

if process_button and uploaded_files:
    
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
        st.markdown("""
        <div class="alert alert-error">
            <div class="alert-icon">❌</div>
            <div class="alert-content">
                <strong>No Valid Files Found:</strong> No PDF or Excel documents were discovered in your upload. 
                Please check your files and try again.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ==========================================
    # STYLED PROCESSING STATUS INDICATORS
    # ==========================================
    status_container = st.container()
    
    with status_container:
        st.markdown("""
        <div class="status-container">
            <div class="status-header">
                ⚙️ Processing In Progress
                <span class="status-badge">ACTIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    master_data = []
    discrepancy_report = []
    missing_info_report = []
    processed_count = 0
    total_groups = len(file_groups)

    # Process Transaction Groups Loop
    for idx, (base_name, target_files) in enumerate(file_groups.items()):
        current_progress = idx / total_groups
        progress_bar.progress(current_progress)
        
        status_text.markdown(f"""
        <div class="status-text">
        📋 Extracting Group <strong>{idx+1}/{total_groups}</strong> → <code>{base_name}</code>
        </div>
        """, unsafe_allow_html=True)
        
        combined_text = ""
        for file_obj in target_files:
            combined_text += f"\n--- CONTENTS OF {file_obj['name']} ---\n"
            try:
                # Use secure temporary file structures
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_obj["name"])[1]) as temp_file:
                    temp_file.write(file_obj['bytes'])
                    temp_path = temp_file.name
                
                extension = os.path.splitext(file_obj["name"])[1].lower()

                # Let MarkItDown unify conversion matrices cleanly
                if extension in [".pdf", ".xlsx", ".xls"]:
                    extracted = md.convert(temp_path)
                    combined_text += extracted.text_content
                else:
                    combined_text += f"\n[Unsupported file type: {extension}]\n"
                
                # Cleanup safely
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
            except Exception as e:
                st.markdown(f"""
                <div class="alert alert-error">
                    <div class="alert-icon">⚠️</div>
                    <div class="alert-content">
                        <strong>File Processing Error:</strong> Could not process <code>{file_obj['name']}</code>
                    </div>
                </div>
                """, unsafe_allow_html=True)
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
            st.markdown("""
            <div class="alert alert-error">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <strong>API Quota Exhausted:</strong> Rate limit reached. Processing paused.
                </div>
            </div>
            """, unsafe_allow_html=True)
            break
        except exceptions.GoogleAPICallError as api_err:
            st.markdown(f"""
            <div class="alert alert-error">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <strong>API Gateway Fault:</strong> {api_err.message}
                </div>
            </div>
            """, unsafe_allow_html=True)
            break
        except Exception as e:
            st.markdown(f"""
            <div class="alert alert-warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <strong>Skipped:</strong> Could not extract data from {base_name}
                </div>
            </div>
            """, unsafe_allow_html=True)

        time.sleep(4)  # Pacing cadence throttle

    progress_bar.progress(1.0)
    status_text.empty()

    # ==========================================
    # VALIDATION, COMPILATION & EXCEL GENERATION
    # ==========================================
    if master_data:
        master_df = pd.DataFrame(master_data)
        
        # Calculate strict math validation flags
        master_df['Math Valid'] = master_df.apply(
            lambda x: pd.isna(x['Total Amount']) or 
                      round((pd.to_numeric(x['Basic Amount'], errors='coerce') or 0) + 
                            (pd.to_numeric(x['Tax Amount'], errors='coerce') or 0), 2) == 
                      round(pd.to_numeric(x['Total Amount'], errors='coerce'), 2), 
            axis=1
        )
        
        # Deduplicate and scrub empty values
        master_df.drop_duplicates(subset=['PO Number'], keep='first', inplace=True)
        master_df.dropna(subset=['PO Number'], inplace=True)

        clean_target_columns = [
            "PO Number", "PO Date", "Site", "Vendor Name", "Contact Number", 
            "Email ID", "Basic Amount", "Tax Amount", "Total Amount", "Math Valid"
        ]
        master_df = master_df.reindex(columns=clean_target_columns)

        # Build Summary Report Data blocks
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

        # ==========================================
        # RESULTS SECTION WITH METRICS DASHBOARD
        # ==========================================
        st.markdown('<div class="spacer-medium"></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="alert alert-success">
            <div class="alert-icon">✅</div>
            <div class="alert-content">
                <strong>Extraction Complete:</strong> All documents have been processed and validated successfully.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics Dashboard
        st.markdown('<h2 class="results-header">📊 Validation Summary</h2>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">📦</div>
                <div class="metric-label">Groups Processed</div>
                <div class="metric-value">{processed_count}</div>
                <div class="metric-subtext">Total PO transactions</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">📋</div>
                <div class="metric-label">Records Exported</div>
                <div class="metric-value">{len(master_df)}</div>
                <div class="metric-subtext">Deduplicated rows</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            missing_count = len(missing_info_report)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">⚠️</div>
                <div class="metric-label">Incomplete Data</div>
                <div class="metric-value">{missing_count}</div>
                <div class="metric-subtext">Missing contact info</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            discrepancy_count = len(discrepancy_report)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">❌</div>
                <div class="metric-label">Discrepancies</div>
                <div class="metric-value">{discrepancy_count}</div>
                <div class="metric-subtext">Issues detected</div>
            </div>
            """, unsafe_allow_html=True)

        # Package data into structured Excel spreadsheet buffer stream
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            master_df.to_excel(writer, sheet_name='Master PO Data', index=False)
            pd.DataFrame(missing_info_report).to_excel(writer, sheet_name='Missing Info Report', index=False)
            pd.DataFrame(discrepancy_report).to_excel(writer, sheet_name='Discrepancies', index=False)
            summary_df.to_excel(writer, sheet_name='Validation Summary', index=False)

        # ==========================================
        # RESULTS & DOWNLOAD SECTION
        # ==========================================
        st.markdown('<h2 class="results-header">📥 Export Results</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="results-section">
        """, unsafe_allow_html=True)
        
        st.download_button(
            label="⬇️ Download Structured Excel Report Package",
            data=buffer.getvalue(),
            file_name="Structured_PO_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.markdown("</div>", unsafe_allow_html=True)

        # Data Preview with Tabs
        st.markdown('<h2 class="results-header">📊 Data Preview</h2>', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Master PO Data",
            "Missing Info Report",
            "Discrepancies",
            "Summary Statistics"
        ])
        
        with tab1:
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(master_df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            if missing_info_report:
                st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(missing_info_report), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert alert-success">
                    <div class="alert-icon">✅</div>
                    <div class="alert-content">
                        All records have complete contact information.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with tab3:
            if discrepancy_report:
                st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(discrepancy_report), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert alert-success">
                    <div class="alert-icon">✅</div>
                    <div class="alert-content">
                        No data integrity issues detected. All POs passed validation.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with tab4:
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(summary_df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="alert alert-error">
            <div class="alert-icon">❌</div>
            <div class="alert-content">
                <strong>No Records Extracted:</strong> Unable to extract data from the provided documents. 
                Please verify file formats and content.
            </div>
        </div>
        """, unsafe_allow_html=True)

elif process_button and not uploaded_files:
    st.markdown("""
    <div class="alert alert-warning">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <strong>No Files Selected:</strong> Please upload at least one PDF, Excel file, or ZIP archive before processing.
        </div>
    </div>
    """, unsafe_allow_html=True)
