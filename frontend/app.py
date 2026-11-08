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


QUESTION_STARTERS = {
    "en": ["Explain the main idea described in the documents.", "What are the main steps described in the documents?", "What conditions or exceptions are mentioned in the documents?"],
    "es": ["Explica la idea principal descrita en los documentos.", "\u00bfCu\u00e1les son los pasos principales descritos en los documentos?", "\u00bfQu\u00e9 condiciones o excepciones se mencionan en los documentos?"],
    "fr": ["Expliquez l'id\u00e9e principale pr\u00e9sent\u00e9e dans les documents.", "Quelles sont les principales \u00e9tapes d\u00e9crites dans les documents ?", "Quelles conditions ou exceptions sont mentionn\u00e9es dans les documents ?"],
    "it": ["Spiega l'idea principale descritta nei documenti.", "Quali sono i passaggi principali descritti nei documenti?", "Quali condizioni o eccezioni sono menzionate nei documenti?"],
}


def use_starter(index):
    language = st.session_state.get("question_language", "en")
    st.session_state.question_input = QUESTION_STARTERS.get(language, QUESTION_STARTERS["en"])[index]


def show_saved_answer():
    entry = st.session_state.question_history[st.session_state.history_choice]
    st.session_state.answer = entry["response"]
    st.session_state.answer_context = entry
    st.session_state.question_input = entry["question"]
    st.session_state.ask_domain = entry["domain"]
    st.session_state.question_language = entry["source_language"]


def clear_question_history():
    for key in ("question_history", "history_choice", "answer", "answer_context"):
        st.session_state.pop(key, None)
    st.session_state.question_input = ""


def answer_markdown(entry):
    response = entry["response"]
    titles = response.get("references", [])
    sources = "\n".join("- " + " ".join(title.splitlines()) for title in titles) or "No source documents were retrieved."
    language = LANGUAGES.get(response.get("language"), "Not recorded")
    return (
        "# Pagewise answer\n\n## Question\n" + entry["question"]
        + "\n\nCategory: " + CATEGORY_LABELS[entry["domain"]]
        + "\nAnswer language: " + language
        + "\n\n## Answer\n" + response["answer"]
        + "\n\n## Retrieved document titles\n" + sources
        + "\n\nAI-generated answer. Verify important information in the original documents. "
          "Document titles are not page-level or claim-level citations.\n"
    )


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

[data-testid="stToolbar"] { display: none; }
h1 { display: flex; align-items: center; gap: 0.7rem; }
h1::before { content: ""; display: inline-block; flex-shrink: 0; width: 42px; height: 44px; border-radius: 12px; background: #6552d8 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='26' height='26' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='1.6' stroke-linejoin='round'%3E%3Cpath d='M3 4c3-1 6 0 9 2 3-2 6-3 9-2v15c-3-1-6 0-9 2-3-2-6-3-9-2zM12 6v15'/%3E%3C/svg%3E") center / 26px no-repeat; box-shadow: 0 5px 16px #6552d82a; }
[data-testid="stForm"] { border-color: #e4e0f1; border-radius: 18px; padding: 1.6rem; box-shadow: 0 8px 30px #34305a06; }
[data-testid="stFileUploaderDropzone"] { min-height: 185px; border: 1.5px dashed #b7a8e7; border-radius: 12px; background: linear-gradient(135deg, #f1edff, #faf8ff); display: flex; align-items: center; padding: 1.5rem; }
[data-testid="stFileUploaderDropzone"] button { color: #fff; background: #6552d8; border-color: #6552d8; border-radius: 8px; font-weight: 600; }
[data-baseweb="tab-list"] { background: #fff; padding: 6px; border: 1px solid #e4e0f1; border-radius: 12px; width: fit-content; gap: 5px; }
[data-baseweb="tab"] { border-radius: 8px; padding: 0.65rem 1.1rem; }
[data-baseweb="tab"][aria-selected="true"] { background: #eeebfc; color: #5543b9; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }
[data-testid="stBaseButton-primary"] { background: #6552d8; border-color: #6552d8; border-radius: 9px; min-height: 45px; }
[data-testid="stBaseButton-primary"]:hover { background: #5140b5; border-color: #5140b5; }
[data-testid="stForm"] input, [data-testid="stForm"] textarea { background: #faf9fd; }

@media (max-width: 640px) {
 .block-container { padding-top: 4.3rem; }
 [data-testid="stForm"] { padding: 1rem; }
 [data-testid="stFileUploaderDropzone"] { min-height: 170px; padding: 1rem; }
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
                        st.session_state.pop("answer_context", None)
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
        with st.expander("Question language & starters"):
            language = st.selectbox("Question language", ["en", "auto", "es", "fr", "it"], format_func=lambda x: "Detect automatically" if x == "auto" else LANGUAGES[x], help="Select the language of your question. The answer will use the same language.", key="question_language")
            st.caption("Choose a starter, then edit it before submitting. It uses your selected question language; automatic detection starts in English.")
            for index, (column, label) in enumerate(zip(st.columns(3), ["Explain the main idea", "List the main steps", "Find conditions"])):
                with column:
                    st.button(label, on_click=use_starter, args=(index,), use_container_width=True)
        with st.form("ask_form"):
            question = st.text_area("Your question", placeholder="What are the main steps described in this document?", height=140, max_chars=8000, key="question_input")
            domain = st.selectbox("Search category", DOMAINS, format_func=CATEGORY_LABELS.get, key="ask_domain", help="Choose the category used when the PDF was uploaded. Answers may use multiple documents in that category.")
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
                        entry = {"question": question.strip(), "domain": domain, "source_language": language, "response": body}
                        st.session_state.answer = body
                        st.session_state.answer_context = entry
                        st.session_state.question_history = [entry] + st.session_state.get("question_history", [])[:9]
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
        context = st.session_state.get("answer_context")
        if context:
            st.caption("Question: " + context["question"] + " | Category: " + CATEGORY_LABELS[context["domain"]])
            st.download_button("Download answer", data=answer_markdown(context), file_name="pagewise-answer.md", mime="text/markdown", help="Save this question, answer and retrieved document titles as a Markdown file.")
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
    history = st.session_state.get("question_history", [])
    if history:
        with st.expander("Recent questions in this session"):
            st.caption("Your last 10 successful questions, newest first. Reopening an answer does not call the model again. History is temporary and is not shared with other users.")
            st.selectbox("Choose a previous question", list(range(len(history))), format_func=lambda index: history[index]["question"][:100] + " | " + CATEGORY_LABELS[history[index]["domain"]], key="history_choice")
            reopen, clear = st.columns(2)
            with reopen:
                st.button("Show saved answer", on_click=show_saved_answer, use_container_width=True)
            with clear:
                st.button("Clear session history", on_click=clear_question_history, use_container_width=True)
            st.caption("Clearing removes this session's questions and displayed answer. Uploaded documents remain in the shared library.")
st.divider()
st.caption("AI-generated answers can be incomplete or incorrect. Verify important information in the original documents.")
