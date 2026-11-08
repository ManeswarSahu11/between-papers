# Setup

Maintainer: Maneswar Sahu <maneswar.sahu2005@gmail.com>.

Use Python 3.12. Keep the translator in a separate virtual environment: its
legacy googletrans dependency pins an old HTTP client incompatible with modern
agent development tools.

```sh
python -m venv .venv
# Windows: .venv/Scripts/activate; macOS/Linux: source .venv/bin/activate
python -m pip install -r agent-service/requirements.txt -r frontend/requirements.txt -r requirements-dev.txt
```

Copy `.env.example` to `.env` and set values privately. Environment files are not
automatically loaded by these services: export the values in each process shell
or configure them in the hosting dashboard. Never commit API keys.

1. Start a reachable Milvus 2.5 server; set `MILVUS_HOST`, `MILVUS_PORT`, and any credentials.
2. Set `GOOGLE_API_KEY` and a Gemini model available to that account. Defaults are configuration, not verified model availability. Collection dimension must match the embedding model (default 3072).
3. Start the agent from `agent-service/`: `python -m uvicorn app.main:app --port 8080`.
4. In an independent environment install `Docker-NLP/requirements.txt`; from `Docker-NLP/` run `python -m uvicorn app.main:app --port 8000`.
5. Set `TRANSLATOR_BASE_URL=http://localhost:8000` on the agent and `AGENT_BASE_URL=http://localhost:8080` on the frontend.
6. From `frontend/`, run `python -m streamlit run app.py`. Running here loads the committed theme and upload setting.

English questions with English explicitly selected do not require the translator.
Automatic detection and non-English questions do. PDF text is embedded in its
original language; questions use an English translation pivot. Cross-language
retrieval quality has not been benchmarked.

## Checks

```sh
python -m pytest -q
python -m compileall -q agent-service frontend Docker-NLP
python -m pip check
```

Regression tests use deterministic provider substitutes and small generated PDF
fixtures. They do not establish Gemini, Milvus or Google Translate availability.
See [validation](VALIDATION.md) for what was actually run.


## Managed vector database

For a managed Milvus-compatible endpoint, set `MILVUS_URI` to the HTTPS endpoint
and `MILVUS_TOKEN` privately. URI mode takes precedence over host/port settings.
For Zilliz Cloud set `MILVUS_INDEX_TYPE=AUTOINDEX`; the default `HNSW` is for
self-hosted Milvus. Never put the token in Git or the frontend's public URL.

[Google key setup](https://ai.google.dev/gemini-api/docs/api-key) and
[Zilliz free clusters](https://docs.zilliz.com/docs/free-trials) describe the
required account actions. Checked 8 November 2026. Free access depends on account,
region and provider limits; these settings do not establish live compatibility.

Set `API_ACCESS_TOKEN` to the same strong private value on all services for
public hosting. Without it, APIs remain open for local development. Never expose
the token in browser-facing code; Streamlit sends it from the server.
