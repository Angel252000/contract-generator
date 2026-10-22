"""Configuración leída del entorno (y de un archivo .env si existe).

El proveedor de IA se elige así: AI_PROVIDER si está definido; si no, el primero con clave
(Anthropic, Groq, Gemini); si no, Ollama si responde en local; si no, la plantilla offline.
"""

import os
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Provider:
    label: str
    base_url: str
    default_model: str
    key_envs: tuple[str, ...] = ()
    free: bool = False


PROVIDERS = {
    "anthropic": Provider("Claude", "", "claude-opus-5-5", ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")),
    "groq": Provider("Groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", ("GROQ_API_KEY",), True),
    "gemini": Provider(
        "Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash",
        ("GEMINI_API_KEY",),
        True,
    ),
    "ollama": Provider("Ollama", "http://localhost:11434/v1", "gemma3:1b", (), True),
    "plantilla": Provider("Plantilla", "", "", ()),
}
KEY_ORDER = ("anthropic", "groq", "gemini")


def _first_key(provider: Provider) -> str:
    return next((os.environ[k] for k in provider.key_envs if os.environ.get(k)), "")


def _ollama_running(base_url: str) -> bool:
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        with urllib.request.urlopen(f"{root}/api/version", timeout=0.5):
            return True
    except OSError:
        return False


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    host: str = "127.0.0.1"
    port: int = 5050
    debug: bool = False

    @property
    def label(self) -> str:
        return PROVIDERS[self.provider].label

    @property
    def uses_ai(self) -> bool:
        return self.provider != "plantilla"

    @property
    def free(self) -> bool:
        return PROVIDERS[self.provider].free

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        ollama_url = os.environ.get("OLLAMA_BASE_URL", PROVIDERS["ollama"].base_url)
        name = os.environ.get("AI_PROVIDER", "").strip().lower()
        if name and name not in PROVIDERS:
            raise ValueError(f"AI_PROVIDER desconocido: {name}. Opciones: {', '.join(PROVIDERS)}")
        if not name:
            name = next((p for p in KEY_ORDER if _first_key(PROVIDERS[p])), "")
        if not name:
            name = "ollama" if _ollama_running(ollama_url) else "plantilla"

        provider = PROVIDERS[name]
        model = os.environ.get("AI_MODEL", "")
        if not model and name == "anthropic":
            model = os.environ.get("CONTRACT_MODEL", "")  # nombre anterior de la variable
        if not model and name == "ollama":
            model = os.environ.get("OLLAMA_MODEL", "")
        return cls(
            provider=name,
            model=model or provider.default_model,
            api_key=_first_key(provider),
            base_url=ollama_url if name == "ollama" else provider.base_url,
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5050")),
            debug=os.environ.get("FLASK_DEBUG") == "1",
        )
