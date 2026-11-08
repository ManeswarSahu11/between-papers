import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

# Exercise the translator API logic without contacting its unofficial upstream.
stub = ModuleType('googletrans')
stub.Translator = Mock
spec = importlib.util.spec_from_file_location('translator_api', Path(__file__).resolve().parents[1] / 'Docker-NLP/app/main.py')
translator = importlib.util.module_from_spec(spec)
with patch.dict('sys.modules', {'googletrans': stub}):
    spec.loader.exec_module(translator)


def test_unsupported_detected_language_is_not_silently_english():
    translator.translator.detect.return_value = Mock(lang='de')
    with pytest.raises(HTTPException) as error:
        translator.detect_language(translator.DetectLanguageRequest(text='Guten Tag'))
    assert error.value.status_code == 400


def test_translation_upstream_failure_is_sanitized():
    translator.translator.translate.side_effect = RuntimeError('secret-token')
    with pytest.raises(HTTPException) as error:
        translator.translate(translator.TranslateRequest(text='Hello', source_language='en', target_language='es'))
    assert error.value.status_code == 502
    assert 'secret-token' not in error.value.detail


def test_same_language_does_not_call_provider():
    translator.translator.translate.reset_mock()
    value = translator.translate(translator.TranslateRequest(text='Hello', source_language='en', target_language='en'))
    assert value.translated_text == 'Hello'
    translator.translator.translate.assert_not_called()
