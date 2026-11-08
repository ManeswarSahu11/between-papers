# Validation record

Checked 8 November 2026 on Windows with Python 3.12.4.

| Check | Result | Scope |
| --- | --- | --- |
| Initial source compilation | Passed | All three Python services |
| Initial test discovery | No tests existed | Baseline had no regression suite |
| Regression suite | 33 passed | Agent API, translator logic, Streamlit forms |
| Dependency consistency | Passed | Isolated agent/frontend environment |
| Browser interactions | Passed | Chromium at 390?844, 768?1024, 1440?1500 |
| Mermaid rendering | 5 passed | Actual rendering using Mermaid 11.12.2 |
| Markdown links and images | Passed | First-party relative references |
| Live provider connections | Passed | Zilliz authentication, 3072-dimension Gemini embedding and generation |
| Live PDF-to-answer workflow | Passed | Real PDF extraction, embedding, Zilliz retrieval, Gemini answer and source title |
| Public deployment | Passed | Three Render Docker services, free plan, Singapore |
| Public browser checks | Passed | Phone/tablet validation and desktop live PDF-to-answer workflow |
| Live multilingual checks | Passed | Spanish question/answer, French detection and French/Italian translation |

Browser checks upload a generated text PDF, validate required fields, submit a
question by keyboard, and display an answer and retrieved title. There was no
page-width overflow at those sizes. A tablet sidebar overlay was reproduced and
fixed by moving help into an inline expandable panel. Real screenshots in
`docs/images/` use an explicitly labelled deterministic provider fixture.

API regressions cover missing credentials, whitespace questions, malformed,
blank and oversized PDFs, domain filtering, empty retrieval without model
invocation, multilingual routing, service-token rejection, sanitized provider
errors, title normalization, reference-section exclusion and cosine scoring.
Translator logic tests substitute its upstream dependency; they do not validate
installation or the live unofficial translation service.

## Reproduce

See [setup](SETUP.md) for the environment. Run `python -m pytest -q` and
`python -m pip check`. For browser checks, install Chromium with
`python -m playwright install chromium`, start `python tests/fixture_server.py`,
and run Streamlit from `frontend/` with `AGENT_BASE_URL=http://127.0.0.1:18080`
and port 18502. Then run `python tests/browser_check.py`.
**Never deploy the fixture server.** It substitutes deterministic provider output.
Run `python tests/doc_check.py` to check relative references and render diagrams;
it downloads a pinned Mermaid runtime and requires network access.

## Remaining limitations

- Live English ingestion and answering passed against the configured Gemini and
  Zilliz accounts on 8 November 2026. The test used a temporary collection and a
  generated single-sentence PDF; the answer matched its seven sensor readings and
  returned the expected paper title. This is a connectivity and workflow check,
  not a quality benchmark. Initial collection deletion timed out; a subsequent
  collection-list check confirmed no temporary test collections remained.
- Public checks passed on 8 November 2026 at https://between-papers.onrender.com
  against runtime commit `0e62affe945def11068fce93a97093595b7b75d3`. The homepage
  and frontend, agent and translator health endpoints returned HTTP 200. Authorized
  agent readiness returned 200 and unauthenticated readiness returned 401.
- A public browser test indexed a generated PDF and received the correct English
  answer and source title through real Gemini/Zilliz providers. A Spanish question
  also returned the expected translated answer and source. French detection and
  translation to French and Italian passed. The uniquely titled test paper was
  deleted afterward and absence confirmed; existing papers were preserved.
- Public browser checks covered 390?844, 768?1024 and 1440?1500 viewports.
  `docs/images/live-desktop.png` captures the actual public answer.
- Performance under concurrent load and long-idle cold starts remain unverified.
  Account-specific success does not establish availability for other regions or accounts.
- The translator still uses the inherited unofficial googletrans client and
  legacy HTTP stack. It runs in an isolated container; live calls passed, but
  long-term upstream compatibility is not guaranteed.
- Installed dependencies emit deprecation warnings, including the inherited
  Gemini SDK and Milvus ORM. A supported SDK migration remains follow-up work.
- Docker and Terraform are unavailable locally. All three images built on Render
  and ran successfully for the checks. Kubernetes rollout, sustained resource
  usage and free instance-hour longevity remain unverified.
- No automated accessibility audit, screen-reader session or complete WCAG
  conformance test has been performed. Keyboard submission and responsive
  interactions were tested.
- External links are retained as attribution or primary documentation; private
  dataset contents and redistribution rights are not verified. Legacy upstream
  README examples are preserved and excluded from first-party link checks.
- No security audit, load benchmark, tenant isolation, OCR, deduplication or
  claim-level citation verification is supplied.

## Upload-first interface update

The Add a paper tab now opens first. The workspace explains the three-step flow,
uses responsive form columns and clearer text contrast, and carries the uploaded
paper's domain into the question form. Regression coverage checks tab order and
required upload fields. Browser checks passed at phone, tablet and desktop sizes,
including a Security-domain upload followed by a question in that selected domain.

## General PDF workspace

The interface now starts with Add a PDF and uses document-focused wording.
General documents is the default category. The normal PDF path retains text
after References/Bibliography; an optional research setting restores reference
exclusion. API regressions verify retained appendix text, opt-in exclusion and
forwarding of both boolean modes. The previous API default is preserved for
clients that do not send the new field. Caption opacity is explicitly reset to
keep helper text readable. No OCR, DOCX or image-only PDF support is implied.

The general-PDF release `bfd15e6` passed GitHub CI (33 tests) and public
phone/tablet/desktop layout checks. A live PDF containing a References heading
followed by the answer was uploaded through the public interface; Gemini
returned the correct answer and source document title. A direct collection check
confirmed both the heading and following text were indexed before the uniquely
titled test document was removed. Current live screenshots show this release.
The browser test waits for the file-transfer response before submitting the form.
Free-service wake-up checks still experienced timeouts; an always-responsive
service is not claimed. The generic workspace remains limited to text PDFs.
