"""Deterministic UI test provider. Never deploy this fixture server."""
import sys
import os
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent-service'))
from app import main
from app.vector_store import SearchResult
import uvicorn

stored = []
embeddings = Mock()
embeddings.embed_documents.side_effect = lambda chunks: [[0.1, 0.2] for _ in chunks]
embeddings.embed_query.return_value = [0.1, 0.2]
graph = Mock()
graph.invoke.return_value = {'answer_en': 'This deterministic test paper describes a method that compares retrieved passages. This is a test fixture, not a live model answer.'}
main.get_services = lambda: main.Services(embeddings, graph, object())
def insert(collection, paper_title, domain, language, chunks, embeddings):
    stored.extend((domain, SearchResult(text, paper_title, 0.9)) for text in chunks)
    return len(chunks)
main.insert_chunks = insert
main.search_similar = lambda collection, query_embedding, domain, top_k: [result for topic, result in stored if topic == domain][:top_k]
uvicorn.run(main.app, host='127.0.0.1', port=int(os.getenv("FIXTURE_PORT", "18080")))
