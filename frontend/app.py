import os

import requests
import streamlit as st

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8080").rstrip("/")
LANGUAGES = {"en": "English", "es": "Spanish", "fr": "French", "it": "Italian"}
DOMAINS = ["AI", "Security", "Other"]


def post(path, **kwargs):
    try:
        response = requests.post(f"{AGENT_BASE_URL}/{path}", timeout=180, headers={"X-API-Key": os.getenv("API_ACCESS_TOKEN", "")}, **kwargs)
        if not response.ok:
            messages = {
                400: "Check your input. Use a text-based, unencrypted PDF and a supported language.",
                401: "Access was denied. Contact the maintainer.",
                403: "You do not have permission to use this service.",
                413: "This PDF exceeds the upload limit. Try a smaller paper.",
                422: "Check the required fields and try again.",
                429: "The service is busy. Wait a moment before trying again.",
                502: "A research provider is unavailable. Please try again shortly.",
                503: "The research service is not ready. Please try again later.",
            }
            st.error(messages.get(response.status_code, "The request failed. Please try again later."))
            return None
        return response.json()
    except requests.Timeout:
        st.error("The request took too long. Indexing may still have completed; avoid uploading the same paper again immediately.")
    except requests.RequestException:
        st.error("Cannot reach the research service. Check your connection and try again.")
    except ValueError:
        st.error("The service returned an unreadable response. Please try again later.")
    return None


st.set_page_config(page_title="Between Papers", page_icon=":books:", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1120px; padding-top: 5rem; padding-bottom: 3rem; }
h1, h2, h3 { letter-spacing: -0.035em; }
h1 { font-family: Georgia, serif !important; font-weight: 500 !important; font-size: clamp(2.5rem, 6vw, 4rem) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #4b5b55 !important; }
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
<div class="workspace-kicker">A LITTLE CLARITY FOR YOUR READING LIST</div>
""", unsafe_allow_html=True)
st.title("Between Papers")
st.markdown('<p class="workspace-intro">Turn a dense paper into a conversation. Add your research, ask a focused question, and follow the answer back to its sources.</p>', unsafe_allow_html=True)
st.markdown("""
<div class="workflow" aria-label="How it works">
 <div class="workflow-item"><b>01 &nbsp; Bring a paper</b><span>Upload a PDF and choose its research domain.</span></div>
 <div class="workflow-item"><b>02 &nbsp; Ask a question</b><span>Explore methods, findings and assumptions.</span></div>
 <div class="workflow-item"><b>03 &nbsp; Check the sources</b><span>Review the answer alongside the original papers.</span></div>
</div>
""", unsafe_allow_html=True)
with st.expander("Before you upload: formats and document privacy"):
    st.write("Use text-based PDFs up to 10 MB by default. Scanned pages need OCR first. Uploading the same paper again creates duplicate passages.")
    st.write("Only upload documents you have permission to process. Paper text and questions are sent to external model and translation providers. Everyone using this deployment shares the same paper library.")
    st.caption("Answers can be incomplete or incorrect. Retrieved paper titles help you check the context; they are not verified citations for every sentence.")

tab_upload, tab_ask = st.tabs(["Add a paper", "Ask your papers"])
with tab_upload:
    st.subheader("Start with something worth reading")
    st.write("Add a paper to the shared library. Once it is indexed, you can ask questions in the same research domain.")
    with st.form("upload_form"):
        file = st.file_uploader("Paper PDF", type=["pdf"], help="Choose a text-based PDF. Scanned documents need text recognition before upload.")
        title = st.text_input("Paper title", max_chars=250, placeholder="The title printed on your paper")
        col_domain, col_language = st.columns(2)
        with col_domain:
            domain = st.selectbox("Research domain", DOMAINS, key="upload_domain", help="Use this same domain when asking questions.")
        with col_language:
            language = st.selectbox("Paper language", list(LANGUAGES), format_func=LANGUAGES.get)
        uploaded = st.form_submit_button("Index paper", type="primary", use_container_width=True)
    if uploaded:
        if not file or not title.strip():
            st.warning("Choose a PDF and enter its title.")
        else:
            with st.spinner("Extracting and indexing your paper..."):
                body = post("ingest", files={"file": (file.name, file.getvalue(), "application/pdf")}, data={"paper_title": title.strip(), "domain": domain, "language": language})
            if body is not None:
                if isinstance(body, dict) and isinstance(body.get("inserted_chunks"), int):
                    st.session_state.last_indexed = {"title": title.strip(), "domain": domain}
                    st.session_state.ask_domain = domain
                    st.session_state.pop("answer", None)
                else:
                    st.error("The service returned an incomplete indexing result. Please check before uploading again.")
    if "last_indexed" in st.session_state:
        paper = st.session_state.last_indexed
        st.success(f"Paper indexed: {paper['title']}. Next, open Ask your papers. The {paper['domain']} domain is already selected.")
    else:
        st.caption("Your paper becomes searchable after indexing finishes. There are no preloaded sample papers.")
with tab_ask:
    st.subheader("What would you like to understand?")
    st.write("Ask about a method, a finding or an assumption. Search the domain where your paper was indexed.")
    if "last_indexed" in st.session_state:
        st.caption("Recently added in this session: " + st.session_state.last_indexed["title"])
    else:
        st.info("New here? Start with Add a paper. If a paper is already in the shared library, choose its domain below.")
    with st.form("ask_form"):
        question = st.text_area("Your question", placeholder="What assumptions does the proposed method rely on?", height=130, max_chars=8000)
        col_domain, col_language = st.columns(2)
        with col_domain:
            domain = st.selectbox("Research domain", DOMAINS, key="ask_domain")
        with col_language:
            language = st.selectbox("Question language", ["en", "auto", "es", "fr", "it"], format_func=lambda x: "Detect automatically" if x == "auto" else LANGUAGES[x], help="Choose a language directly to avoid relying on automatic detection.")
        submitted = st.form_submit_button("Find an answer", type="primary", use_container_width=True)
    if submitted:
        st.session_state.pop("answer", None)
        if not question.strip():
            st.warning("Enter a question to search your papers.")
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
            st.subheader("Retrieved papers")
            st.caption("Return to these papers to check the context and supporting evidence.")
            for title in refs:
                with st.container(border=True):
                    st.text(title)
        else:
            st.info("No source papers to display. Add a paper in the selected domain, then ask again.")
    else:
        st.caption("Your answer and retrieved paper titles will appear here after you ask a question.")
st.divider()
st.caption("Made for close reading. English, Spanish, French and Italian. Always check important conclusions against the original paper.")
