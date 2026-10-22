import pytest

from contract_generator import config
from contract_generator.config import Settings
from contract_generator.data import ClaudeWriter, OpenAICompatWriter, TemplateWriter
from contract_generator.service.contracts import build_writer

ENV_VARS = [
    "AI_PROVIDER", "AI_MODEL", "CONTRACT_MODEL", "OLLAMA_MODEL", "OLLAMA_BASE_URL",
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GROQ_API_KEY", "GEMINI_API_KEY",
]  # fmt: skip


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda: None)  # que un .env local no altere las pruebas
    monkeypatch.setattr(config, "_ollama_running", lambda _url: False)


def test_no_keys_and_no_ollama_uses_template():
    s = Settings.from_env()
    assert s.provider == "plantilla" and not s.uses_ai
    assert isinstance(build_writer(s), TemplateWriter)


def test_ollama_detected_when_running(monkeypatch):
    monkeypatch.setattr(config, "_ollama_running", lambda _url: True)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    s = Settings.from_env()
    assert (s.provider, s.model, s.base_url) == ("ollama", "qwen2.5:3b", "http://localhost:11434/v1")
    assert s.free
    writer = build_writer(s)
    assert isinstance(writer, OpenAICompatWriter) and writer.name == "ollama"


@pytest.mark.parametrize(
    ("env", "provider", "model"),
    [
        ({"GROQ_API_KEY": "g"}, "groq", "llama-3.3-70b-versatile"),
        ({"GEMINI_API_KEY": "m"}, "gemini", "gemini-2.5-flash"),
        ({"ANTHROPIC_API_KEY": "a", "GROQ_API_KEY": "g"}, "anthropic", "claude-opus-5-5"),
        ({"ANTHROPIC_API_KEY": "a", "CONTRACT_MODEL": "claude-sonnet-5-5"}, "anthropic", "claude-sonnet-5-5"),
        ({"GROQ_API_KEY": "g", "AI_PROVIDER": "gemini", "GEMINI_API_KEY": "m", "AI_MODEL": "x"}, "gemini", "x"),
    ],
)
def test_provider_resolution(monkeypatch, env, provider, model):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    s = Settings.from_env()
    assert (s.provider, s.model) == (provider, model)


def test_groq_settings_build_compat_writer(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave")
    s = Settings.from_env()
    assert s.api_key == "clave" and s.base_url.startswith("https://api.groq.com")
    assert isinstance(build_writer(s), OpenAICompatWriter)


def test_anthropic_settings_build_claude_writer(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert isinstance(build_writer(Settings.from_env()), ClaudeWriter)


def test_unknown_provider_fails(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "otro")
    with pytest.raises(ValueError):
        Settings.from_env()
