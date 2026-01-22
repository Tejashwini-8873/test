import streamlit as st
import tempfile
import logging
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
# Import backend functions
import depo_functions as df

# --- Configuration ---
st.set_page_config(page_title="RLG | Depo Summarizer", page_icon="📜", layout="wide")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)

# --- Session State Initialization ---
st.session_state.setdefault("summary_status", "idle")
st.session_state.setdefault("summary_future", None)
st.session_state.setdefault("summary_result", None)
st.session_state.setdefault("summary_log", [])
st.session_state.setdefault("summary_error", None)
st.session_state.setdefault("summary_completed_once", False)
st.session_state.setdefault("summary_needs_rerun", False)
st.session_state.setdefault("show_status_msg", False)
st.session_state.setdefault("pause_autorefresh", False)
if "user_responses" not in st.session_state:
    st.session_state["user_responses"] = []
if "selected_chat_index" not in st.session_state:
    st.session_state["selected_chat_index"] = None

# --- Auto-refresh Logic for Background Tasks ---
if st.session_state.summary_status == "running" and not st.session_state.pause_autorefresh:
    st_autorefresh(interval=15000, key="summary_poll")

if st.session_state.summary_status == "running":
    future = st.session_state.get("summary_future")
    if future and future.done():
        result = future.result()
        st.session_state.summary_log = result.get("log", [])

        if result.get("path"):
            st.session_state.summary_result = result["path"]
            st.session_state.summary_status = "done"
            st.session_state.show_status_msg = False   
        else:
            st.session_state.summary_error = result.get("error", "Unknown error")
            st.session_state.summary_status = "error"
            st.session_state.show_status_msg = False  
        
        st.session_state.summary_completed_once = True

if st.session_state.summary_needs_rerun:
    st.session_state.summary_needs_rerun = False
    st.rerun()

if st.session_state.summary_completed_once:
    st.session_state.summary_completed_once = False
    st.rerun()

# --- CSS Styling ---
st.markdown("""
    <style>
        .main, body, [class*="block-container"] {
            background-color: #f2fbf5 !important;  /* 🌿 light mint green */
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        .main {
            background-color: #f5f8f5;
        }
        
        /* Top Bar */
        .top-bar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 56px; 
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding: 0.6rem 1.2rem;
            background: linear-gradient(90deg, #009e60, #00b26d);
            color: white;
            border-bottom: 2px solid #007c48;
            z-index: 1000;
        }

        .logo {
            height: 50px;
            margin-right: 14px;
            border-radius: 6px;
            box-shadow: 0 0 6px rgba(0,0,0,0.1);
        }
        .title {
            font-size: 1.9rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        /* Buttons */
        .stButton>button {
            background-color: #009e60;
            color: white;
            font-weight: 600;
            border-radius: 10px;
            padding: 0.6em 1.3em;
            border: none;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,158,96,0.2);
        }
        .stButton>button:hover {
            background-color: #00b26d;
            transform: scale(1.03);
            box-shadow: 0 5px 12px rgba(0,158,96,0.25);
        }

        /* Sidebar */
        .sidebar-title {
            font-weight: 700;
            color: #009e60;
            margin-bottom: 0.5rem;
            font-size: 1.1em;
        }
        .chat-item {
            background: #ffffff;
            border-radius: 10px;
            padding: 0.6rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            cursor: pointer;
            transition: 0.2s;
        }
        .chat-item:hover {
            background: #e5f7ec;
        }

        /* Response Cards */
        .response-box {
            background-color: #ffffff;
            border-left: 6px solid #009e60;
            border-radius: 15px;
            padding: 1em 1.3em;
            box-shadow: 0 3px 8px rgba(0,0,0,0.06);
            margin-bottom: 1.2em;
        }
        .question {
            font-weight: 600;
            color: #006b3f;
        }
        .answer {
            background: #f2fbf5;
            border-left: 4px solid #00b26d;
            padding: 0.8em 1em;
            border-radius: 8px;
            margin-top: 0.4em;
        }

        /* Footer */
        .footer {
            text-align: center;
            color: #444;
            font-size: 0.9em;
            padding-top: 20px;
            border-top: 1px solid #b6dec2;
            margin-top: 35px;
        }

        /* Misc Layout Adjustments */
        section[data-testid="stSidebar"] {
            margin-top: 150px !important;
        }
        div[data-testid="collapsedControl"] {
            position: fixed !important;
            top: 150px !important;
            left: 10px !important;
            z-index: 5005 !important;
        }
        header {
            position: relative !important;
            z-index: 1 !important;
        }

        /* CSS loader */
        .loader {
            border: 4px solid #f3f3f3;
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 30px;
            height: 30px;
            margin: 0 auto 10px auto;
            -webkit-animation: spin 1s linear infinite;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
    </style>
""", unsafe_allow_html=True)

# --- Header ---
logo_path = r"https://raw.githubusercontent.com/Tejashwini-8873/test/main/assets/RLG.jpg"
logo_base64 = df.get_base64_image(logo_path)

st.markdown(f"""
    <style>
        .top-header {{
            position: fixed;
            top: 0px;
            left: 0;
            width: 100%;
            height: 120px;
            background: linear-gradient(90deg, rgba(0,158,96,0.9), rgba(0,178,109,0.92)),
                        url("data:image/webp;base64,{logo_base64}") no-repeat left center;
            background-size: auto 120px;
            background-blend-mode: overlay;
            border-bottom: 3px solid #007c48;
            box-shadow: 0 3px 8px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            z-index: 1000;
        }}
        .top-header h1 {{
            color: white;
            font-size: 1.8rem;
            font-weight: 900;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
        }}
        .top-header p {{
            color: #e8ffe9;
            font-size: 0.95rem;
            font-style: italic;
            margin: 0;
        }}
    </style>

    <div class="top-header">
        <h1>📜 RLG Deposition Summarizer</h1>
        <p>AI-powered legal deposition analysis — with The Wonderful touch 🍃</p>
    </div>
""", unsafe_allow_html=True)

# --- Main Logic ---

# Create two columns
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    uploaded_file = st.file_uploader("📂 Upload a deposition document (PDF only) and let AI summarize and extract key legal insights effortlessly.", type=["pdf"])

    json_format= """{
                "subject": "<short header summarizing the topic of these pages>",
                "content": "<1-2 line factual mini-summary of the testimony or events in these pages>",
                "line_numbers": {
                "<page_number>": [<only the most relevant line numbers from this page>],
                "<page_number>": [<only the most relevant line numbers from this page>]
                }
            },
            {
                "subject": "<short header summarizing the topic of these pages>",
                "content": "<1-2 line factual mini-summary of the testimony or events in these pages>",
                "line_numbers": {
                "<page_number>": [<only the most relevant line numbers from this page>],
                "<page_number>": [<only the most relevant line numbers from this page>]
                }
            }
            """

    prompt = f"""
            You are a senior legal analyst specializing in deposition analysis. Your task is to review a full deposition transcript and perform two critical functions:
            1. Page-Group Subject Summaries
            2. A structured, professional legal summary

            ---
            
            # ### 1. Page-Group Subject Summaries
                - You must review the entire deposition transcript thoroughly from start to end. 
                - Divide the transcript into sequential, non-overlapping chunks. Each chunk must:
                    • Cover a continuous range of pages in order.  
                    • Group together related discussions, testimony, or objections that form a coherent subject.  
                    • Ensure that every page of the transcript is included in exactly one chunk (no page may be skipped or left out).  
                - For each chunk:
                    • Identify a concise subject line summarizing the primary topic or testimony for that page range.  
                    • Write a 2–3 line factual mini-summary of the testimony in that chunk.  
                    • Keep the summary neutral, objective, and legally relevant (no opinions or speculation).  
                    - Provide a **2–3 line factual mini-summary** of the content in those pages make sure all pages are included.
                    - Keep it **neutral, objective, and legally relevant**.
                    • Ensure that every page of the transcript is considered in sequence, but you may omit chunks if:
                        – The pages contain no substantive facts to summarize (e.g., filler, procedural headers , word glossary ).  
                        – The pages have no valid line numbers available for extraction
                - Output must cover the **entire deposition**, from the first page to the last, in properly ordered chunks.
                                
                - **Line_Numbers**:  
                    - Never invent or guess line numbers. Use only numbers that truly appear on that page (available_lines or parsed from page_text).
                    - Parsing: Each page is already provided as a dictionary (`1: "...", 2: "...", ...`).   — i.e., a dict mapping **page → list of 4–5 line numbers**.
                    Inside each page, every `\\n` corresponds to a new line number, which is marked at the start (e.g., `1`, `2`, `3`).  
                    This allows you to map: **page → line numbers → text** cleanly.  
                    - Select only line numbers that directly support the chunk’s subject/summary.
                    - Do not include every line or filler text (e.g., "Page X", "Veritext Legal Solutions").
                    - Output as a dict: "page": [line1, line2, ...].
                    - Each page-group must have unique, relevant line numbers — no reusing or repeating sets.
                    - Do not return full-page listings, only substantive testimony, objections, or statements.
                    - If a page has no relevant or duplicate line numbers, omit it.
                    - Do not return full-page listings — only the specific lines tied to substantive testimony, objections, or statements.
                    - If incase a page has no relevant lines or same block of pagenumbers are repeating , you can omit that page from the line number dictionary.
                    - Ignore if any two pages have the same array of line numbers.
                VALIDATION CHECK (you must perform before finalizing Section 1):
                1. For each page in "line_numbers", confirm every number is present on that page.
                2. Confirm no two different pages use the exact same list of line numbers.
                3. Confirm arrays are strictly increasing and 2–6 items long.
                4. If any check fails, revise the selections to comply.

                    
            For every extracted chunk, include:
            - "subject": A 1-line title summarizing the main focus of these pages.
            - "content": A concise 2–3 line factual summary.
            -  "line_numbers" : A dictionary mapping page numbers to lists of line numbers that support the summary.
            Return all extracted page-group summaries in strict JSON format:
            {json_format}

            ---

            ### 2. Structured Deposition Summary
            Create a professional, litigation-ready summary organized into the following sections:  
            
            #### 1. Exhibits Table
                    
            Extract all exhibits introduced or referenced in the deposition and present them in a table format:

            | Exhibit No./Name | Page Numbers | Brief Description & Relevance |
            |------------------|--------------|-------------------------------|
            | EX-1             | 12, 14, 47   | [1–2 line factual relevance]  |
            | EX-2             | 33           | [1–2 line factual relevance]  |

            Instructions:
            - Capture **every exhibit identifier** exactly as it appears (e.g., "Exhibit 12", "EX-3", "Plaintiff’s Exhibit A").  
            - Include **all page numbers** where the exhibit is either introduced, marked, or referenced in testimony.  
            - If an exhibit appears on multiple non-contiguous pages, list all page numbers separated by commas.  
            - Provide a **1–2 line neutral factual description** of the exhibit’s content or its relevance to the case.  
            - Keep it concise, litigation-ready, and fact-focused (no opinions).  
            #### 2. Legal Issue
            - Identify the primary legal issue(s) or disputes.
            - Note claims, defenses, or counterclaims.
            - Highlight if issues are contractual, statutory, regulatory, or procedural.
            - Indicate whether disputes involve interpretation of documents or factual disagreements.

            #### 3. Purpose of Deposition
            - State why this deposition was conducted.
            - Identify the strategic objective (timeline clarification, admissions, etc.).
            - Indicate type of witness (party, fact, or expert).
            - Highlight trial preparation, settlement leverage, or compliance purposes.

            #### 4. Roles
            - Name the deponent’s title and job function.
            - Explain their relevance to the case.
            - Mention if they are a decision-maker or fact witness.
            - Note other key individuals referenced.

            #### 5. Policies, Laws, or Definitions Referenced
            - List relevant policies mentioned.
            - Include applicable laws, statutes, or regulations.
            - Identify key contract clauses.
            - Note formal definitions clarified.

            #### 6. Situational Background and Key Testimony
            - Summarize critical events leading to deposition.
            - Provide chronological context.
            - Highlight crucial facts established or disputed.
            - Identify key concessions or contradictions.

            #### 7. Key Witness Statements Supporting the Case
            For each impactful or repeated statement (quoted or paraphrased in 1–2 lines), include:
            - **Speaker** — name and/or role.
            - **Situation/Context** — when and why it was said (e.g., during cross-examination, discussing an exhibit, responding to a timeline question).
            - **Impact** — concise explanation of how this strengthens the deposition’s value to the case.

           
            #### 8. Legal Recommendations
            - Suggest next litigation or discovery steps.
            - Identify additional evidence or witnesses needed.
            - Recommend motions or filings.
            - Flag risks or gaps requiring follow-up.

            ---
            
            ### General Instructions
            - Ensure the JSON summaries and the structured summary are **neutral and litigation-ready**.
            - Avoid speculation.
            - Return the final output in two sections:
            1. "Page-Group Subject Summaries (JSON)"
            2. "Structured Deposition Summary"
            """

    # File Upload Handler
    if uploaded_file is not None:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()

        if file_ext != ".pdf":
            st.error("❌ Invalid file format. Please upload a PDF deposition document only.")
            st.stop()

        # Run only once per new upload
        if st.session_state.get("last_uploaded") != uploaded_file.name:

            st.session_state["last_uploaded"] = uploaded_file.name

            # 1️⃣ Upload file to Azure Blob
            blob_name, deposition_sas_url = df.upload_file_to_blob(uploaded_file)
            st.session_state["deposition_sas_url"] = deposition_sas_url
            st.session_state["blob_name"] = blob_name

            # 2️⃣ Download blob locally for text extraction
            temp_path = df.download_blob_to_temp(blob_name)

            # 3️⃣ Extract text from PDF or DOCX
            if temp_path.lower().endswith(".pdf"):
                text = df.extract_text_from_pdf(temp_path)
            else:
                text = df.extract_text_from_docx(temp_path)

            # Save extracted text
            st.session_state["file_text"] = text

            # 4️⃣ Show success message once
            st.success("✅ File uploaded & text extracted automatically!")


    # --- Callback for Generate Button ---
    def on_start_summary(blob_name_arg, api_key_arg, prompt_arg):
        if blob_name_arg is None:
            st.error("Please upload and read file first.")
            return

        st.session_state.summary_status = "running"
        st.session_state.summary_log = []
        st.session_state.summary_error = None
        
        # helper to run background job
        future = executor.submit(
            df.background_summary,
            blob_name_arg,
            api_key_arg,
            prompt_arg
        )
        st.session_state.summary_future = future


    # --- GENERATE SUMMARY BUTTON ---
    if st.session_state.summary_status == "idle":
        st.button(
            "🧠 Generate Summary in Background",
            on_click=on_start_summary,
            args=(st.session_state.get("blob_name"), df.api_key, prompt)
        )

    # ------------------ STATUS SECTION ------------------
    status_container = st.container()

    with status_container:
        if st.session_state.summary_status == "running":
            st.markdown("""
                <div style="text-align: center; background-color: #e3f2fd; padding: 20px; border-radius: 10px; border: 1px solid #bbdefb;">
                    <div class="loader"></div>
                    <div style="color: #0d47a1; font-weight: 600;">Generating summary...</div>
                    <div style="color: #555; font-size: 0.9em;">It will download automatically when ready.</div>
                </div>
            """, unsafe_allow_html=True)

        elif st.session_state.summary_status == "done":
             st.markdown("""
                <div style="
                    text-align: center;
                    background-color: #e8f5e9;
                    padding: 15px;
                    border-radius: 10px;
                    border: 1px solid #c8e6c9;
                    margin-bottom: 10px;
                ">
                    <div style="font-size: 1.2em; font-weight: 600;">
                        ✅ Summary Ready! It has downloaded automatically.
                    </div>
                    <div style="font-size: 0.9em; margin-top: 6px; color: #2e7d32;">
                        If not, click the button below to download again.
                    </div>
                </div>
            """, unsafe_allow_html=True)
             
             # --- AUTO DOWNLOAD LOGIC ---
             if "auto_download_triggered" not in st.session_state:
                st.session_state.auto_download_triggered = False

             if not st.session_state.auto_download_triggered:
                st.session_state.auto_download_triggered = True
                file_url = st.session_state.summary_result
                st.toast("🚀 Auto-download started!", icon="📥")
                components.html(
                    f"""<script>window.location.href = "{file_url}";</script>""",
                    height=0, width=0
                )
             
            # Button
             try:
                file_bytes = requests.get(st.session_state.summary_result).content
                st.download_button(
                    label="⬇️ Download Summary Again",
                    data=file_bytes,
                    file_name="deposition_summary.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
             except Exception as e:
                st.error(f"Download Error: {e}")

        elif st.session_state.summary_status == "error":
            st.markdown(f"""
                <div style="text-align: center; background-color: #ffebee; padding: 15px; border-radius: 10px; border: 1px solid #ffcdd2;">
                   ❌ Summary failed: {st.session_state.summary_error}
                </div>
            """, unsafe_allow_html=True)

# --- Right Column: Deposition Inquiry Assistant ---
with right_col:
    # --- Query Section ---
    st.markdown("###  ⌨️Deposition Inquiry Assistant")
    query_type = st.radio("Choose Input Type:", ["Dropdown", "Text Input"], horizontal=True)

    st.markdown("""
        <style>
            /* 🌿 Dropdown / Multiselect Field Styling */
            div[data-baseweb="select"] {
                background-color: #e9f8ee !important;  /* light green background */
                border-radius: 10px !important;
                border: 1px solid #b6dec2 !important;
                padding: 5px !important;
                transition: all 0.2s ease-in-out;
            }

            /* Hover effect for dropdown area */
            div[data-baseweb="select"]:hover {
                background-color: #dcf5e5 !important;  /* slightly brighter green */
                border-color: #00b26d !important;
            }

            /* Selected value text */
            div[data-baseweb="select"] > div {
                color: #006b3f !important;
                font-weight: 500 !important;
            }

            /* Option list background */
            ul[role="listbox"] {
                background-color: #f5fbf6 !important;  /* dropdown open background */
                border-radius: 8px !important;
                border: 1px solid #b6dec2 !important;
            }

            /* Each dropdown item */
            li[role="option"] {
                color: #004d2c !important;
                padding: 8px 10px !important;
                border-radius: 6px !important;
            }

            /* Hover effect for each option */
            li[role="option"]:hover {
                background-color: #d8f2de !important;
                color: #003820 !important;
            }

            /* Selected tags (for multiselect) */
            div[data-baseweb="tag"] {
                background-color: #009e60 !important;
                color: white !important;
                border-radius: 12px !important;
                font-weight: 600 !important;
                padding: 4px 10px !important;
            }

            div[data-baseweb="tag"]:hover {
                background-color: #00b26d !important;
            }
        </style>
    """, unsafe_allow_html=True)

    if query_type == "Dropdown":
    
        depo_fields = [
        "Summarize the deposition in 5 key bullet points.",
        "List all parties, attorneys, and witnesses involved.",
        "Identify the deponent’s role and relevance to the case.",
        "What are the key issues or topics discussed in this deposition?",
        "List all exhibits referred to or marked during the deposition.",
        "Summarize the witness’s main statements related to liability.",
        "Summarize any discussions related to damages or compensation.",
        "Summarize admissions made by the deponent, if any.",
        "Identify mentions of key individuals, companies, or organizations.",
        "Summarize any clarifications or corrections made by the witness."
    ]

        user_input = st.multiselect("Select Deposition Fields (you can select multiple):", depo_fields)
        if len(user_input) == 0:
            st.warning("Please select at least one field.")
            # st.stop() # Removed stop to prevent right col from blocking
    else:
        query =user_input= st.text_input("📝 Enter your Query:")

    # --- Dialog Function for Modal (History) ---
    @st.dialog(" ", width="large")
    def view_history_modal():
        responses = st.session_state.get('user_responses', [])
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        if responses:
            for q, r in reversed(responses):
                st.markdown(f"""
                <div class="user-msg" style="background-color: transparent !important; color: inherit !important; box-shadow: none !important; padding: 0 !important; margin-bottom: 0.5rem;">
                    <div class="msg-label" style="color: #006400; font-weight: 800; font-size: 1rem;">🧑‍💼 Question:</div>
                    <div style="background-color: #f1f8e9; padding: 10px; border-radius: 8px; color: #1b5e20; border: 1px solid #c8e6c9;">
                        {q}
                    </div>
                </div>
                <div class="ai-msg" style="margin-top: 0;">
                    <div class="msg-label">AI Answer:</div>
                    {r}
                </div>
                <hr style="margin: 1.5rem 0; border-top: 1px solid #eee;">
                """, unsafe_allow_html=True)
        else:
             st.info("No history yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Buttons Row ---
    btn_col1, btn_col2 = st.columns([1, 1])
    
    with btn_col1:
        if st.button("💬 Ask AI"):
            st.session_state.pause_autorefresh = True
            text_data = st.session_state.get('file_text', '')
            
            if not text_data:
                st.warning("Please upload and read a file first.")
            else:
                user_responses = st.session_state.get('user_responses', [])
                # Logic for query construction
                if query_type == "Dropdown" and user_input:
                    query = f"Extract the following fields: {', '.join(user_input)}"
                elif isinstance(user_input, str):
                     query = user_input
                else:
                    st.warning("Please enter or select a query.")
                    query = None 

                if query:
                    with st.spinner("Thinking... 💭"):
                        response = df.get_chatgpt_response(query, text_data, df.api_key, model="gpt-4-turbo")
                        user_responses.append((query, response))
                        st.session_state['user_responses'] = user_responses
                        # Trigger the modal with history
                        view_history_modal()
    
    with btn_col2:
        if st.button("📜 View History"):
             view_history_modal()

# --- Footer ---
st.markdown("""
<div class="footer">
    © The Wonderful Company LLC 🌳 All Rights Reserved.
</div>
""", unsafe_allow_html=True)
