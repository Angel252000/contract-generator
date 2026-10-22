"""Redactor que usa la API de Claude (Anthropic)."""

import logging
from collections.abc import Iterator

import anthropic

from ..domain import ContractRequest, EditRequest
from .base import WriterError
from .prompts import EDIT_SYSTEM, GENERATE_SYSTEM, build_contract_prompt, build_edit_prompt

log = logging.getLogger(__name__)


class ClaudeWriter:
    name = "claude"
    uses_ai = True

    def __init__(self, model: str, client: anthropic.Anthropic | None = None):
        self.model = model
        self._client = client or anthropic.Anthropic()

    def stream_contract(self, request: ContractRequest) -> Iterator[str]:
        yield from self._stream(GENERATE_SYSTEM, build_contract_prompt(request), effort="medium", max_tokens=32000)

    def rewrite(self, request: EditRequest) -> str:
        return "".join(self._stream(EDIT_SYSTEM, build_edit_prompt(request), effort="low", max_tokens=8000)).strip()

    def _stream(self, system: str, user: str, effort: str, max_tokens: int) -> Iterator[str]:
        try:
            with self._client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": effort},
                # Si el modelo rechaza, la API reintenta en un modelo alternativo.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                yield from stream.text_stream
                final = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise WriterError("API key inválida.") from exc
        except anthropic.RateLimitError as exc:
            raise WriterError("Límite de uso alcanzado; intenta en un momento.") from exc
        except anthropic.APIStatusError as exc:
            log.exception("Error de la API de Anthropic")
            raise WriterError(f"Error de la API ({exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise WriterError("Sin conexión con la API.") from exc

        if final.stop_reason == "refusal":
            raise WriterError("El modelo se negó a redactar este contenido.")
        if final.stop_reason == "max_tokens":
            yield "\n\n[El texto se cortó por longitud.]"
