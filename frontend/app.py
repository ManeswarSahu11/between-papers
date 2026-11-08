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
.block-container { max-width: 1120px; padding-top: 5rem; padding-bottom: 3rem; }
h1, h2, h3 { letter-spacing: -0.035em; }
h1 { font-family: Georgia, serif !important; font-weight: 500 !important; font-size: clamp(2.5rem, 6vw, 4rem) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #4b5b55 !important; opacity: 1 !important; }
[data-testid="stForm"] { border-radius: 16px; background: #ffffff; padding: 1.4rem; }
[data-baseweb="tab-list"] { gap: 1.25rem; margin-bottom: 1rem; }
[data-baseweb="tab"] { font-size: 1rem; padding-bottom: 0.8rem; }
.workspace-kicker { color: #245c50; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.16em; margin-bottom: 0.3rem; }
.workspace-intro { font-size: 1.12rem; color: #42554c; max-width: 680px; line-height: 1.7; }
.workflow { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin: 1.4rem 0 1.8rem; }
.workflow-item { border: 1px solid #d8dfd6; border-radius: 12px; padding: 1rem; background: #f2f4ed; }
.workflow-item b { display: block; color: #203d32; margin-bottom: 0.3rem; }
.workflow-item span { color: #4b5b55; font-size: 0.9rem; }
@media (max-width: 640px) {
 .block-container { padding-top: 4.5rem; }
 .workflow { grid-template-columns: 1fr; gap: 0.5rem; }
 .workflow-item { padding: 0.8rem 1rem; }
 [data-testid="stForm"] { padding: 1rem; }
}
</style>
<div class="workspace-kicker">LESS SEARCHING. MORE UNDERSTANDING.</div>
""", unsafe_allow_html=True)
st.title("Pagewise")
st.markdown('<p class="workspace-intro">Your PDFs have a lot to say. Bring a manual, report, set of notes or research paper, and turn the pages into a conversation.</p>', unsafe_allow_html=True)
st.markdown("""
<div class="workflow" aria-label="How it works">
 <div class="workflow-item"><b>01 &nbsp; Bring a PDF</b><span>Add a text-based document and choose a category.</span></div>
 <div class="workflow-item"><b>02 &nbsp; Ask a question</b><span>Ask for an explanation, a detail or a summary.</span></div>
 <div class="workflow-item"><b>03 &nbsp; Check the sources</b><span>Check the answer against your original documents.</span></div>
</div>
""", unsafe_allow_html=True)
with st.expander("Before you upload: formats and document privacy"):
    st.write("Use text-based PDFs up to 10 MB by default. Scanned pages need OCR first. Uploading the same PDF again creates duplicate passages.")
    st.write("Only upload documents you have permission to process. Document text and questions are sent to external model and translation providers. Everyone using this deployment shares the same document library.")
    st.caption("Answers can be incomplete or incorrect. Retrieved document titles help you check the context; they are not verified citations for every sentence.")

tab_upload, tab_ask = st.tabs(["Add a PDF", "Ask your documents"])
with tab_upload:
    st.subheader("Give your next question a starting point")
    st.write("Manuals, reports, study notes and research papers are welcome. Add a PDF, then ask questions in its category.")
    with st.form("upload_form"):
        file = st.file_uploader("PDF document", type=["pdf"], help="Choose a text-based PDF. Scanned documents need text recognition before upload.")
        title = st.text_input("Document title", max_chars=250, placeholder="A name you will recognize in your sources")
        col_domain, col_language = st.columns(2)
        with col_domain:
            domain = st.selectbox("Document category", DOMAINS, format_func=CATEGORY_LABELS.get, key="upload_domain", help="Use this same category when asking questions.")
        with col_language:
            language = st.selectbox("Document language", list(LANGUAGES), format_func=LANGUAGES.get)
        with st.expander("Optional: research paper settings"):
            exclude_references = st.checkbox("Skip reference sections", value=False, help="Stops at a detected References or Bibliography heading and ignores everything after it. Leave off to keep the full document.")
        uploaded = st.form_submit_button("Make PDF searchable", type="primary", use_container_width=True)
    if uploaded:
        if not file or not title.strip():
            st.warning("Choose a PDF and give your document a title.")
        else:
            with st.spinner("Making your document searchable..."):
                body = post("ingest", files={"file": (file.name, file.getvalue(), "application/pdf")}, data={"paper_title": title.strip(), "domain": domain, "language": language, "exclude_references": str(exclude_references).lower()})
            if body is not None:
                if isinstance(body, dict) and isinstance(body.get("inserted_chunks"), int):
                    st.session_state.last_indexed = {"title": title.strip(), "domain": domain}
                    st.session_state.ask_domain = domain
                    st.session_state.pop("answer", None)
                else:
                    st.error("The service returned an incomplete indexing result. Please check before uploading again.")
    if "last_indexed" in st.session_state:
        paper = st.session_state.last_indexed
        st.success(f"Document ready: {paper['title']}. Next, open Ask your documents. The {CATEGORY_LABELS[paper['domain']]} category is already selected.")
    else:
        st.caption("Text-based PDFs up to 10 MB. Scanned pages need OCR before upload. No sample documents are preloaded.")
with tab_ask:
    st.subheader("What would you like to understand?")
    st.write("Get to the detail you need: explain a concept, find a fact or summarize an idea. Search the category where your PDF was added.")
    if "last_indexed" in st.session_state:
        st.caption("Recently added in this session: " + st.session_state.last_indexed["title"])
    else:
        st.info("New here? Start with Add a PDF. If a document is already in the shared library, choose its category below.")
    with st.form("ask_form"):
        question = st.text_area("Your question", placeholder="What are the key steps described in this document?", height=130, max_chars=8000)
        col_domain, col_language = st.columns(2)
        with col_domain:
            domain = st.selectbox("Document category", DOMAINS, format_func=CATEGORY_LABELS.get, key="ask_domain")
        with col_language:
            language = st.selectbox("Question language", ["en", "auto", "es", "fr", "it"], format_func=lambda x: "Detect automatically" if x == "auto" else LANGUAGES[x], help="Choose a language directly to avoid relying on automatic detection.")
        submitted = st.form_submit_button("Find an answer", type="primary", use_container_width=True)
    if submitted:
        st.session_state.pop("answer", None)
        if not question.strip():
            st.warning("Enter a question to search your documents.")
        else:
            with st.spinner("Reading relevant passages..."):
                body = post("ask", json={"question": question.strip(), "domain": domain, "source_language": None if language == "auto" else language})
            if body is not None:
                if isinstance(body, dict) and isinstance(body.get("answer"), str):
                    st.session_state.answer = body
                else:
                    st.error("The service returned an incomplete answer. Please try again.")
    if "answer" in st.session_state:
        body = st.session_state.answer
        st.divider()
        st.subheader("Answer")
        st.write(body["answer"])
        refs = body.get("references", [])
        if refs:
            st.subheader("Source documents")
            st.caption("These documents supplied the retrieved passages. Check the originals for context; titles do not verify every sentence.")
            for title in refs:
                with st.container(border=True):
                    st.text(title)
        else:
            st.info("No source documents to display. Add a PDF in the selected category, then ask again.")
    else:
        st.caption("Your answer and source document titles will appear here after you ask a question.")
st.divider()
st.caption("A clearer way through your documents. English, Spanish, French and Italian. Always check important conclusions against the original document.")
