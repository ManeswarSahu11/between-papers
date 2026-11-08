import os

import requests
import streamlit as st

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8080").rstrip("/")
LANGUAGES = {"en": "English", "es": "Spanish", "fr": "French", "it": "Italian"}
DOMAINS = ["Other", "AI", "Security"]
CATEGORY_LABELS = {"Other": "General documents", "AI": "AI & technology", "Security": "Security"}


def post(path, **kwargs):
    try:
        response = requests.post(f"{AGENT_BASE_URL}/{path}", timeout=180, headers={"X-API-Key": os.getenv("API_ACCESS_TOKEN", "")}, **kwargs)
        if not response.ok:
            messages = {
                400: "Check your input. Use a text-based, unencrypted PDF and a supported language.",
                401: "Access was denied. Contact the maintainer.",
                403: "You do not have permission to use this service.",
                413: "This PDF exceeds the upload limit. Try a smaller document.",
                422: "Check the required fields and try again.",
                429: "The service is busy. Wait a moment before trying again.",
                502: "A document service is unavailable. Please try again shortly.",
                503: "The document service is not ready. Please try again later.",
            }
            st.error(messages.get(response.status_code, "The request failed. Please try again later."))
            return None
        return response.json()
    except requests.Timeout:
        if path == "ingest":
            st.error("The upload took too long. The service may be waking up, and indexing may still complete. Avoid uploading the same PDF again immediately.")
        else:
            st.error("The answer took too long. The service may be waking up; please try again shortly.")
    except requests.RequestException:
        st.error("Cannot reach the document service. Check your connection and try again.")
    except ValueError:
        st.error("The service returned an unreadable response. Please try again later.")
    return None


st.set_page_config(page_title="Pagewise", page_icon=":books:", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1160px; padding-top: 4.8rem; padding-bottom: 2rem; }
h1, h2, h3 { letter-spacing: -0.025em; }
h1 { font-size: clamp(2.3rem, 5vw, 3rem) !important; font-weight: 650 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #46596b !important; opacity: 1 !important; }
[data-testid="stForm"] { background: #ffffff; border: 1px solid #d5dfe9; border-radius: 12px; padding: 1.4rem; }
[data-baseweb="tab-list"] { gap: 0.5rem; margin-top: 0.8rem; margin-bottom: 1rem; }
[data-baseweb="tab"] { font-size: 1rem; padding: 0.7rem 1rem; }
[data-baseweb="tab"][aria-selected="true"] { font-weight: 650; }
.workspace-intro { color: #3c5063; font-size: 1.08rem; line-height: 1.65; max-width: 760px; margin-bottom: 1rem; }
@media (max-width: 640px) {
 .block-container { padding-top: 4.3rem; }
 [data-testid="stForm"] { padding: 1rem; }
 [data-baseweb="tab"] { padding: 0.65rem 0.5rem; }
}
</style>
""", unsafe_allow_html=True)
st.title("Pagewise")
st.markdown('<p class="workspace-intro">Upload a PDF and ask questions about its contents. Get an answer with the titles of documents used as context.</p>', unsafe_allow_html=True)

tab_upload, tab_ask = st.tabs(["Upload a PDF", "Ask questions"])
with tab_upload:
    main, guide = st.columns([2.1, 1], gap="large")
    with main:
        st.subheader("Add your document")
        with st.form("upload_form"):
            file = st.file_uploader("PDF file", type=["pdf"], help="Text-based PDF, up to 10 MB. Scanned or image-only PDFs need text recognition first.")
            st.caption("Text-based PDF only. Maximum file size: 10 MB.")
            title = st.text_input("Document title", max_chars=250, placeholder="For example: Employee handbook", help="This title will appear when the document is used to answer a question.")
            col_category, col_language = st.columns(2)
            with col_category:
                domain = st.selectbox("Document category", DOMAINS, format_func=CATEGORY_LABELS.get, key="upload_domain", help="Questions search all documents in the selected category. Use General documents unless a more specific category fits.")
            with col_language:
                language = st.selectbox("Document language", list(LANGUAGES), format_func=LANGUAGES.get)
            with st.expander("Optional: skip reference sections"):
                exclude_references = st.checkbox("Stop at References or Bibliography", value=False)
                st.caption("Only text before the detected heading will be kept. Any appendices after it will also be skipped. Leave this off for most PDFs.")
            uploaded = st.form_submit_button("Upload PDF", type="primary", use_container_width=True)
        if uploaded:
            if not file or not title.strip():
                st.warning("Choose a PDF and enter a document title.")
            else:
                with st.spinner("Preparing your PDF for questions..."):
                    body = post("ingest", files={"file": (file.name, file.getvalue(), "application/pdf")}, data={"paper_title": title.strip(), "domain": domain, "language": language, "exclude_references": str(exclude_references).lower()})
                if body is not None:
                    if isinstance(body, dict) and isinstance(body.get("inserted_chunks"), int):
                        st.session_state.last_indexed = {"title": title.strip(), "domain": domain}
                        st.session_state.ask_domain = domain
                        st.session_state.pop("answer", None)
                    else:
                        st.error("The service did not confirm that the PDF was prepared. Check before uploading it again.")
        if "last_indexed" in st.session_state:
            document = st.session_state.last_indexed
            st.success(f"Ready to use: {document['title']}. Open Ask questions to continue. Category: {CATEGORY_LABELS[document['domain']]}.")
    with guide:
        st.subheader("Before you upload")
        with st.container(border=True):
            st.markdown("**Supported documents**")
            st.write("Manuals, reports, study notes, guides and research papers saved as text-based PDFs.")
            st.markdown("**Scanned pages**")
            st.write("If the text cannot be selected in a PDF reader, run text recognition (OCR) before uploading.")
            st.markdown("**Avoid duplicate uploads**")
            st.write("Uploading the same PDF again adds another copy of its text to the library.")
        st.info("Shared library: other users can ask questions about uploaded content. Do not upload private or confidential documents.")
        st.caption("Upload only documents you have permission to process. Document text and questions are sent to external AI and translation services.")

with tab_ask:
    main, guide = st.columns([2.1, 1], gap="large")
    with main:
        st.subheader("Ask about your documents")
        if "last_indexed" in st.session_state:
            st.caption("Last document added in this session: " + st.session_state.last_indexed["title"])
        else:
            st.caption("Upload a PDF first, or choose a category that already contains documents in the shared library.")
        with st.form("ask_form"):
            question = st.text_area("Your question", placeholder="What are the main steps described in this document?", height=140, max_chars=8000)
            col_category, col_language = st.columns(2)
            with col_category:
                domain = st.selectbox("Search category", DOMAINS, format_func=CATEGORY_LABELS.get, key="ask_domain", help="Choose the category used when the PDF was uploaded. Answers may use multiple documents in that category.")
            with col_language:
                language = st.selectbox("Question language", ["en", "auto", "es", "fr", "it"], format_func=lambda x: "Detect automatically" if x == "auto" else LANGUAGES[x], help="Select the language of your question. The answer will use the same language.")
            submitted = st.form_submit_button("Get answer", type="primary", use_container_width=True)
        if submitted:
            st.session_state.pop("answer", None)
            if not question.strip():
                st.warning("Enter a question about your documents.")
            else:
                with st.spinner("Finding relevant text and preparing your answer..."):
                    body = post("ask", json={"question": question.strip(), "domain": domain, "source_language": None if language == "auto" else language})
                if body is not None:
                    if isinstance(body, dict) and isinstance(body.get("answer"), str):
                        st.session_state.answer = body
                    else:
                        st.error("The service returned an incomplete answer. Please try again.")
    with guide:
        st.subheader("Get a useful answer")
        with st.container(border=True):
            st.markdown("**Choose the right category**")
            st.write("Pagewise searches all documents in that category, not just the last PDF you uploaded.")
            st.markdown("**Ask a specific question**")
            st.write("Name the topic, process or rule you want explained. Include relevant details in your question.")
            st.markdown("**Check the original PDF**")
            st.write("Source titles identify documents used as context. They are not page citations or proof that every sentence is correct.")
    if "answer" in st.session_state:
        body = st.session_state.answer
        st.divider()
        st.subheader("Answer")
        with st.container(border=True):
            st.write(body["answer"])
        refs = body.get("references", [])
        if refs:
            st.subheader("Source documents")
            st.caption("Documents retrieved as context for this answer. Review the originals to verify important details.")
            for title in refs:
                with st.container(border=True):
                    st.text(title)
        else:
            st.info("No source documents to display. Check the category or upload a PDF before asking again.")
    else:
        st.caption("Your answer and source document titles will appear below after you submit a question.")
st.divider()
st.caption("AI-generated answers can be incomplete or incorrect. Verify important information in the original documents.")
