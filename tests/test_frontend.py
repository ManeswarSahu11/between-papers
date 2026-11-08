from pathlib import Path
from unittest.mock import patch, Mock
import requests
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'frontend/app.py')


def test_empty_question():
    app = AppTest.from_file(APP).run()
    next(button for button in app.button if button.label == 'Get answer').click().run()
    assert not app.exception
    assert 'Enter a question' in app.warning[0].value


def test_network_failure():
    with patch('requests.post', side_effect=requests.ConnectionError):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Get answer').click().run()
    assert not app.exception
    assert 'Cannot reach' in app.error[0].value


def test_answer_persists_and_empty_sources():
    response = Mock(ok=True)
    response.json.return_value = {'answer': 'No indexed passages.', 'references': []}
    with patch('requests.post', return_value=response):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Get answer').click().run()
        app.run()
    assert not app.exception
    assert any('No source documents' in entry.value for entry in app.info)


def test_denied_permission():
    with patch('requests.post', return_value=Mock(ok=False, status_code=403)):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Get answer').click().run()
    assert not app.exception
    assert 'permission' in app.error[0].value


def test_upload_is_first_and_empty_upload_has_guidance():
    app = AppTest.from_file(APP).run()
    assert [tab.label for tab in app.tabs] == ['Upload a PDF', 'Ask questions']
    next(button for button in app.button if button.label == 'Upload PDF').click().run()
    assert not app.exception
    assert 'Choose a PDF' in app.warning[0].value


def test_general_category_and_full_document_are_defaults():
    app = AppTest.from_file(APP).run()
    assert app.selectbox[0].value == 'Other'
    assert app.checkbox[0].value is False


def click(app, label):
    return next(button for button in app.button if button.label == label).click().run()


def fixture_response(answer='Fixture answer'):
    response = Mock(ok=True)
    response.json.return_value = {'answer': answer, 'language': 'en', 'references': ['Fixture guide']}
    return response


def test_starter_prefills_without_provider_call():
    with patch('requests.post') as post:
        app = AppTest.from_file(APP).run()
        click(app, 'List the main steps')
        assert 'main steps' in app.text_area[0].value
        post.assert_not_called()
    assert not app.exception


def test_starter_respects_selected_language():
    app = AppTest.from_file(APP).run()
    app.selectbox(key='question_language').select('fr').run()
    click(app, 'List the main steps')
    assert app.text_area[0].value.startswith('Quelles sont')
    assert not app.exception


def test_history_restores_answer_category_and_question_without_call():
    with patch('requests.post', side_effect=[fixture_response('First answer'), fixture_response('Second answer')]) as post:
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('First question')
        click(app, 'Get answer')
        app.selectbox(key='ask_domain').select('Security')
        app.text_area[0].input('Second question')
        click(app, 'Get answer')
        assert len(app.session_state['question_history']) == 2
        app.selectbox(key='history_choice').select(1).run()
        click(app, 'Show saved answer')
        assert app.session_state['answer']['answer'] == 'First answer'
        assert app.text_area[0].value == 'First question'
        assert app.selectbox(key='ask_domain').value == 'Other'
        assert post.call_count == 2
    assert not app.exception


def test_history_is_bounded_and_can_be_cleared():
    with patch('requests.post', return_value=fixture_response()):
        app = AppTest.from_file(APP).run()
        for index in range(12):
            app.text_area[0].input(f'Question {index}')
            click(app, 'Get answer')
        history = app.session_state['question_history']
        assert len(history) == 10
        assert history[0]['question'] == 'Question 11'
        assert history[-1]['question'] == 'Question 2'
        click(app, 'Clear session history')
        assert 'question_history' not in app.session_state
        assert 'answer' not in app.session_state
        assert app.text_area[0].value == ''
    assert not app.exception


def test_failed_question_does_not_enter_history():
    with patch('requests.post', side_effect=requests.ConnectionError):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('Failed question')
        click(app, 'Get answer')
        assert 'question_history' not in app.session_state
    assert not app.exception


def test_answer_context_is_not_changed_by_draft_edits():
    with patch('requests.post', return_value=fixture_response()):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('Original question')
        click(app, 'Get answer')
        app.text_area[0].input('Unsubmitted draft')
        app.selectbox(key='ask_domain').select('Security').run()
        assert app.session_state['answer_context']['question'] == 'Original question'
        assert app.session_state['answer_context']['domain'] == 'Other'
    assert not app.exception


def test_recent_history_is_isolated_between_sessions():
    with patch('requests.post', return_value=fixture_response()):
        first = AppTest.from_file(APP).run()
        first.text_area[0].input('Session one question')
        click(first, 'Get answer')
        second = AppTest.from_file(APP).run()
        assert len(first.session_state['question_history']) == 1
        assert 'question_history' not in second.session_state
        assert 'answer' not in second.session_state
    assert not second.exception
