import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent-service'))
from app import main, config
from app.schemas import AskRequest
from app.vector_store import SearchResult
from app.rag_pipeline import to_references


@pytest.fixture
def client(monkeypatch):
    main.get_services.cache_clear()
    monkeypatch.setattr(config, 'GOOGLE_API_KEY', '')
    return TestClient(main.app)


@pytest.fixture
def services(monkeypatch):
    value = main.Services(Mock(), Mock(), Mock())
    value.embeddings.embed_query.return_value = [0.1, 0.2]
    value.embeddings.embed_documents.return_value = [[0.1, 0.2]]
    value.graph.invoke.return_value = {'answer_en': 'Fixture answer from context.'}
    monkeypatch.setattr(main, 'get_services', lambda: value)
    return value


def test_health_without_credentials(client):
    assert client.get('/healthz').json() == {'ok': True}
    assert client.get('/readyz').status_code == 503


@pytest.mark.parametrize('question', ['', '   ', 'x' * 8001])
def test_invalid_questions(client, question):
    assert client.post('/ask', json={'question': question, 'domain': 'AI'}).status_code == 422


def test_invalid_domain(client):
    assert client.post('/ask', json={'question': 'Why?', 'domain': 'fake', 'source_language': 'en'}).status_code == 400


def test_missing_credentials(client):
    assert client.post('/ask', json={'question': 'Why?', 'domain': 'AI', 'source_language': 'en'}).status_code == 503


def test_empty_library_does_not_generate(client, services, monkeypatch):
    monkeypatch.setattr(main, 'search_similar', lambda *a, **kw: [])
    body = client.post('/ask', json={'question': 'Why?', 'domain': 'AI', 'source_language': 'en'}).json()
    assert body['references'] == []
    assert 'No indexed passages' in body['answer']
    services.graph.invoke.assert_not_called()


def test_answer_and_domain_filter(client, services, monkeypatch):
    search = Mock(return_value=[SearchResult('Evidence', 'Fixture Paper', 0.8)])
    monkeypatch.setattr(main, 'search_similar', search)
    result = client.post('/ask', json={'question': 'Why?', 'domain': 'Security', 'source_language': 'en'})
    assert result.status_code == 200
    assert result.json()['references'] == ['Fixture Paper']
    assert search.call_args.kwargs['domain'] == 'Security'
    assert services.graph.invoke.call_args.args[0]['retrieved_chunks'] == ['Evidence']


def test_provider_error_is_sanitized(client, services):
    services.embeddings.embed_query.side_effect = RuntimeError('secret-token')
    result = client.post('/ask', json={'question': 'Why?', 'domain': 'AI', 'source_language': 'en'})
    assert result.status_code == 502
    assert 'secret-token' not in result.text


def test_translation_failure(client, monkeypatch):
    monkeypatch.setattr(main, 'detect_language', Mock(side_effect=ConnectionError('private-url')))
    result = client.post('/ask', json={'question': 'Hola?', 'domain': 'AI'})
    assert result.status_code == 502
    assert 'private-url' not in result.text


def test_multilingual_flow(client, services, monkeypatch):
    monkeypatch.setattr(main, 'search_similar', lambda *a, **kw: [SearchResult('Evidence', 'Paper', 0.8)])
    translate = Mock(side_effect=['English question', 'Respuesta'])
    monkeypatch.setattr(main, 'translate', translate)
    result = client.post('/ask', json={'question': 'Pregunta?', 'domain': 'AI', 'source_language': 'es'})
    assert result.json()['answer'] == 'Respuesta'
    assert result.json()['language'] == 'es'
    services.embeddings.embed_query.assert_called_once_with('English question')


@pytest.mark.parametrize('content,filename,status', [(b'not pdf', 'paper.pdf', 400), (b'%PDF-invalid', 'paper.pdf', 400), (b'text', 'file.txt', 400)])
def test_bad_upload(client, content, filename, status):
    response = client.post('/ingest', data={'paper_title': 'Paper', 'domain': 'AI', 'language': 'en'}, files={'file': (filename, content, 'application/pdf')})
    assert response.status_code == status


def test_upload_limit(client, monkeypatch):
    monkeypatch.setattr(config, 'MAX_UPLOAD_BYTES', 8)
    result = client.post('/ingest', data={'paper_title': 'Paper', 'domain': 'AI', 'language': 'en'}, files={'file': ('paper.pdf', b'%PDF-' + b'x'*20)})
    assert result.status_code == 413


def test_blank_pdf(client):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    result = client.post('/ingest', data={'paper_title': 'Paper', 'domain': 'AI', 'language': 'en'}, files={'file': ('paper.pdf', output.getvalue())})
    assert result.status_code == 400
    assert 'No parseable text' in result.text


def test_ingestion(client, services, monkeypatch):
    monkeypatch.setattr(main, 'extract_pdf_text', lambda *a, **kw: 'Fixture text')
    insert = Mock(return_value=1)
    monkeypatch.setattr(main, 'insert_chunks', insert)
    result = client.post('/ingest', data={'paper_title': ' Paper ', 'domain': 'AI', 'language': 'en'}, files={'file': ('paper.pdf', b'%PDF-fixture')})
    assert result.status_code == 200
    assert result.json()['inserted_chunks'] == 1
    assert insert.call_args.kwargs['paper_title'] == 'Paper'


def test_numbered_references_stop_extraction(monkeypatch):
    from app import pdf_utils
    pages = [Mock(), Mock()]
    pages[0].extract_text.return_value = 'Useful text\n7. References\nExcluded'
    pages[1].extract_text.return_value = 'Also excluded'
    monkeypatch.setattr(pdf_utils, 'PdfReader', lambda _: Mock(pages=pages))
    assert pdf_utils.extract_text_without_references(b'fixture') == 'Useful text'


def test_cosine_recommendation_uses_best_similarity():
    references, recommended = to_references([SearchResult('a', 'Paper', 0.9), SearchResult('b', 'Paper', 0.3)])
    assert references == ['Paper']
    assert recommended[0]['score'] == 0.9


def test_managed_database_connection(monkeypatch):
    from app import vector_store
    monkeypatch.setattr(config, 'MILVUS_URI', 'https://fixture.invalid')
    monkeypatch.setattr(config, 'MILVUS_TOKEN', 'fixture-token')
    connect = Mock()
    monkeypatch.setattr(vector_store.connections, 'connect', connect)
    vector_store.connect_milvus()
    connect.assert_called_once_with(alias='default', uri='https://fixture.invalid', token='fixture-token', timeout=15)


def test_api_token_denied_and_allowed(client, monkeypatch):
    monkeypatch.setattr(config, 'API_ACCESS_TOKEN', 'fixture-access-token')
    assert client.get('/healthz').status_code == 200
    assert client.get('/readyz').status_code == 401
    result = client.get('/readyz', headers={'X-API-Key': 'fixture-access-token'})
    assert result.status_code == 503  # Authorized but no research provider configured.


def test_general_pdf_keeps_text_after_references(monkeypatch):
    from app import pdf_utils
    page = Mock()
    page.extract_text.return_value = 'Guide\nReferences\nImportant appendix'
    monkeypatch.setattr(pdf_utils, 'PdfReader', lambda _: Mock(pages=[page]))
    assert pdf_utils.extract_pdf_text(b'fixture') == 'Guide\nReferences\nImportant appendix'
    assert pdf_utils.extract_pdf_text(b'fixture', exclude_references=True) == 'Guide'


@pytest.mark.parametrize('exclude', ['true', 'false'])
def test_ingest_forwards_reference_option(client, services, monkeypatch, exclude):
    extract = Mock(return_value='Manual text')
    monkeypatch.setattr(main, 'extract_pdf_text', extract)
    monkeypatch.setattr(main, 'insert_chunks', Mock(return_value=1))
    result = client.post('/ingest', data={'paper_title': 'Manual', 'domain': 'Other', 'language': 'en', 'exclude_references': exclude}, files={'file': ('manual.pdf', b'%PDF-fixture')})
    assert result.status_code == 200
    extract.assert_called_once_with(b'%PDF-fixture', exclude_references=(exclude == 'true'))
