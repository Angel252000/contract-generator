"""Redactor para proveedores con API compatible con OpenAI: Ollama (local), Groq y Gemini (gratuitos)."""

import logging
from collections.abc import Iterator

import openai

from ..domain import ContractRequest, EditRequest
from .base import WriterError
from .prompts import EDIT_SYSTEM, GENERATE_SYSTEM, build_contract_prompt, build_edit_prompt

log = logging.getLogger(__name__)


class OpenAICompatWriter:
    uses_ai = True

    def __init__(self, name: str, label: str, model: str, base_url: str, api_key: str, client=None):
        self.name = name
        self.label = label
        self.model = model
        # Ollama no valida la clave, pero el SDK exige una.
        self._client = client or openai.OpenAI(base_url=base_url, api_key=api_key or "sin-clave", max_retries=1)

    def stream_contract(self, request: ContractRequest) -> Iterator[str]:
        yield from self._stream(GENERATE_SYSTEM, build_contract_prompt(request), max_tokens=8000)

    def rewrite(self, request: EditRequest) -> str:
        return "".join(self._stream(EDIT_SYSTEM, build_edit_prompt(request), max_tokens=2000)).strip()

    def _stream(self, system: str, user: str, max_tokens: int) -> Iterator[str]:
        finish_reason = None
        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=0.3,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta and choice.delta.content:
                    yield choice.delta.content
                finish_reason = choice.finish_reason or finish_reason
        except openai.AuthenticationError as exc:
            raise WriterError(f"API key de {self.label} inválida.") from exc
        except openai.RateLimitError as exc:
            raise WriterError(f"Se alcanzó el límite gratuito de {self.label}; intenta en un momento.") from exc
        except openai.NotFoundError as exc:
            raise WriterError(f"El modelo '{self.model}' no existe en {self.label}.") from exc
        except openai.APIStatusError as exc:
            log.exception("Error de %s", self.label)
            raise WriterError(f"Error de {self.label} ({exc.status_code}).") from exc
        except openai.APIConnectionError as exc:
            hint = " ¿Está abierto Ollama?" if self.name == "ollama" else ""
            raise WriterError(f"Sin conexión con {self.label}.{hint}") from exc

        if finish_reason == "length":
            yield "\n\n[El texto se cortó por longitud.]"
