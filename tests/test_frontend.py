from pathlib import Path
from unittest.mock import patch, Mock
import requests
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'frontend/app.py')


def test_empty_question():
    app = AppTest.from_file(APP).run()
    next(button for button in app.button if button.label == 'Find an answer').click().run()
    assert not app.exception
    assert 'Enter a question' in app.warning[0].value


def test_network_failure():
    with patch('requests.post', side_effect=requests.ConnectionError):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Find an answer').click().run()
    assert not app.exception
    assert 'Cannot reach' in app.error[0].value


def test_answer_persists_and_empty_sources():
    response = Mock(ok=True)
    response.json.return_value = {'answer': 'No indexed passages.', 'references': []}
    with patch('requests.post', return_value=response):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Find an answer').click().run()
        app.run()
    assert not app.exception
    assert any('No source papers' in entry.value for entry in app.info)


def test_denied_permission():
    with patch('requests.post', return_value=Mock(ok=False, status_code=403)):
        app = AppTest.from_file(APP).run()
        app.text_area[0].input('What is the method?')
        next(button for button in app.button if button.label == 'Find an answer').click().run()
    assert not app.exception
    assert 'permission' in app.error[0].value


def test_upload_is_first_and_empty_upload_has_guidance():
    app = AppTest.from_file(APP).run()
    assert [tab.label for tab in app.tabs] == ['Add a paper', 'Ask your papers']
    next(button for button in app.button if button.label == 'Index paper').click().run()
    assert not app.exception
    assert 'Choose a PDF' in app.warning[0].value
