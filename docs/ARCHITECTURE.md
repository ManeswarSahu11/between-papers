# Architecture

## Service boundaries

```mermaid
flowchart LR
    User[Reader] --> UI[Streamlit interface]
    UI -->|PDF or question over HTTP| API[FastAPI agent]
    API -->|Document and query embeddings| Gemini[External Gemini API]
    API -->|Context and question| Gemini
    API -->|Store and retrieve passages| Milvus[Milvus vector database]
    API -->|Only auto detection or translation| T[FastAPI translator]
    T --> GT[External Google Translate via googletrans]
    API -->|503 or 502 on failure| UI
```

## Main request flow

```mermaid
sequenceDiagram
    participant R as Reader
    participant U as Streamlit
    participant A as Agent
    participant T as Translator
    participant M as Milvus
    participant G as Gemini
    R->>U: Question and domain
    U->>A: POST /ask
    opt Language not explicitly selected
        A->>T: Detect language
    end
    opt Non-English question
        A->>T: Translate to English
    end
    A->>G: Embed question
    A->>M: Search with domain filter
    alt No passages
        A-->>U: Empty result with upload guidance
    else Passages found
        A->>G: Generate using retrieved text
        opt Non-English answer
            A->>T: Translate answer
        end
        A-->>U: Answer and retrieved paper titles
    end
    Note over A,U: Dependency failures return a useful 502 or 503 without a fabricated answer
```

## Core ingestion and retrieval algorithm

```mermaid
flowchart TD
    P[PDF upload] --> V{Valid type and size?}
    V -->|No| E[Reject with input error]
    V -->|Yes| X[Extract full text or optionally stop at reference heading]
    X --> C{Parseable text?}
    C -->|No| E
    C -->|Yes| S[Split into overlapping chunks]
    S --> B[Gemini document embeddings]
    B --> I[Insert metadata and vectors into Milvus]
    Q[Question] --> L[Detect or use chosen language]
    L --> EN[Translate to English if required]
    EN --> QE[Embed question]
    QE --> D[Filter by domain and retrieve top K]
    I -.-> D
    D --> H{Any passages?}
    H -->|No| N[Return empty result guidance]
    H -->|Yes| G[LangGraph generation from passages]
    G --> O[Translate answer if required]
    O --> R[Answer and paper title references]
```

LangGraph contains a pass-through retrieval node and a generation node. Retrieval
actually occurs before graph invocation; this is not autonomous web research or
a general tool-selecting agent. Recommendations choose the two most frequent
paper titles among retrieved chunks. Similarity scores are not confidence scores.
References contain document titles, not links, page citations, or verified claim spans.
The legacy API field names `paper_title` and `domain` remain for compatibility.
UI category General documents maps to `Other`; AI & technology maps to `AI`.
The frontend sends `exclude_references=false` by default. Existing API clients
that omit that field keep the original reference-excluding behavior.

All users share one collection. There are no accounts, ownership filters,
delete endpoints, OCR, automatic deduplication, or web search. Repeated uploads
create more chunks. Prompt instructions request context-grounded answers but do
not guarantee factuality or defend against all instructions embedded in papers.

## Session conveniences

Question starters are predefined templates and make no provider call. Successful
responses are stored with the submitted question, category and language in
Streamlit session state (maximum ten). Reopening an entry reads that response
without rerunning retrieval or generation. It is not conversation memory for
the model, an account history or a private document library.

Markdown downloads use the saved request context, so editing an unsubmitted
question does not relabel an old answer. Clearing session history also clears
the displayed answer and question; it does not delete indexed documents.
