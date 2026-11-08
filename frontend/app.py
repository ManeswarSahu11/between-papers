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


st.set_page_config(page_title="Between Papers", page_icon="??", layout="wide")
st.markdown("RESEARCH WORKSPACE")
st.title("Between Papers")
st.write("Read deeply. Ask clearly. Return to the source.")
st.caption("Explore the papers you upload, with questions in English, Spanish, French or Italian.")

with st.expander("How to use this workspace and document privacy"):
    st.subheader("Your reading workflow")
    st.write("1. Upload a text-based PDF.\n2. Choose its research domain.\n3. Ask a question in the same domain.")
    st.divider()
    st.caption("Only upload documents you have permission to process. Text and questions are sent to external research and translation providers.")
    st.caption("The library is shared by everyone using this deployment. It is not a private document vault.")

tab_ask, tab_upload = st.tabs(["Ask your papers", "Add a paper"])
with tab_ask:
    st.subheader("What would you like to understand?")
    st.caption("Start with a specific question about a paper you have indexed. Answers can be incomplete; check the original papers.")
    with st.form("ask_form"):
        question = st.text_area("Your question", placeholder="What assumptions does the proposed method rely on?", height=130, max_chars=8000)
        domain = st.selectbox("Research domain", DOMAINS, key="ask_domain")
        language = st.selectbox("Question language", ["en", "auto", "es", "fr", "it"], format_func=lambda x: "Detect automatically" if x == "auto" else LANGUAGES[x], help="Choose a language directly to avoid relying on automatic detection.")
        submitted = st.form_submit_button("Find an answer", type="primary", use_container_width=True)
    if submitted:
        st.session_state.pop("answer", None)
        if not question.strip():
            st.warning("Enter a question to search your papers.")
        else:
            with st.spinner("Reading relevant passages?"):
                body = post("ask", json={"question": question.strip(), "domain": domain, "source_language": None if language == "auto" else language})
            if body is not None:
                if isinstance(body, dict) and isinstance(body.get("answer"), str):
                    st.session_state.answer = body
                else:
                    st.error("The service returned an incomplete answer. Please try again.")
    if "answer" in st.session_state:
        body = st.session_state.answer
        st.subheader("Answer")
        st.write(body["answer"])
        refs = body.get("references", [])
        if refs:
            st.subheader("Retrieved papers")
            st.caption("These papers supplied retrieved passages. This is not a claim that every sentence has been verified.")
            for title in refs:
                st.text(title)
        else:
            st.info("No source papers to display. Add a paper in the selected domain, then ask again.")
    else:
        st.info("Your answer and retrieved paper titles will appear here after you ask a question.")
with tab_upload:
    st.subheader("Bring a paper into the conversation")
    st.caption("Text-based PDFs only, up to 10 MB by default. Scanned documents need OCR before upload. Re-uploading a paper creates duplicate passages.")
    with st.form("upload_form"):
        file = st.file_uploader("Paper PDF", type=["pdf"])
        title = st.text_input("Paper title", max_chars=250, placeholder="Use the title printed on the paper")
        domain = st.selectbox("Research domain", DOMAINS, key="upload_domain")
        language = st.selectbox("Paper language", list(LANGUAGES), format_func=LANGUAGES.get)
        uploaded = st.form_submit_button("Index paper", type="primary", use_container_width=True)
    if uploaded:
        if not file or not title.strip():
            st.warning("Choose a PDF and enter its title.")
        else:
            with st.spinner("Extracting and indexing your paper?"):
                body = post("ingest", files={"file": (file.name, file.getvalue(), "application/pdf")}, data={"paper_title": title.strip(), "domain": domain, "language": language})
            if body is not None:
                if isinstance(body, dict) and isinstance(body.get("inserted_chunks"), int):
                    st.success(f"Paper indexed: {title.strip()}. You can now ask questions in {domain}.")
                else:
                    st.error("The service returned an incomplete indexing result. Please check before uploading again.")
