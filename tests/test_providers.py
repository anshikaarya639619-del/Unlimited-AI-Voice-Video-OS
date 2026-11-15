import pytest
from app.providers import get_providers, MockProvider, KokoroProvider, GPTSoVITSProvider

def test_mock_provider_for_pipeline(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "mock")
    assert isinstance(get_providers()[0], MockProvider)

def test_kokoro_provider_selection(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "kokoro")
    assert isinstance(get_providers()[0], KokoroProvider)

def test_gpt_sovits_provider_selection(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "gpt-sovits")
    assert isinstance(get_providers()[0], GPTSoVITSProvider)

def test_ordered_fallback(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "kokoro,gpt-sovits")
    assert [p.name for p in get_providers()] == ["kokoro", "gpt-sovits"]

def test_mock_cannot_be_mixed(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "mock,kokoro")
    with pytest.raises(RuntimeError):
        get_providers()
