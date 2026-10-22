"""Redactor que usa la API de Claude (Anthropic)."""

import logging
from collections.abc import Iterator
from datetime import date

import anthropic

from ..domain import ContractRequest, EditRequest
from .base import WriterError

log = logging.getLogger(__name__)

GENERATE_SYSTEM = """Eres un redactor de contratos profesional. A partir de la descripción del usuario \
redactas un contrato completo y listo para revisar.

Formato (Markdown):
- Título en `#`, luego lugar y fecha, y la identificación de las partes.
- Antecedentes o considerandos si aportan algo.
- Cláusulas numeradas con `##` (PRIMERA, SEGUNDA, ...) que cubran: objeto, alcance, obligaciones de cada \
parte, precio y forma de pago (si aplica), plazo y vigencia, confidencialidad, propiedad intelectual \
(si aplica), terminación, incumplimiento, resolución de conflictos y ley aplicable, y disposiciones generales.
- Bloque de firmas al final con líneas para nombre, cargo/documento, firma y fecha de cada parte.

Reglas:
- Escribe en el idioma de la descripción (español por defecto).
- Usa los datos que dé el usuario; lo que falte va entre corchetes, p. ej. [Nombre del cliente], [Monto], \
sin inventar nombres, cifras ni leyes concretas que no te hayan dado.
- Devuelve solo el contrato, sin comentarios antes ni después."""

EDIT_SYSTEM = """Editas fragmentos de un contrato. Devuelve únicamente el fragmento reescrito, en el mismo \
idioma y con el mismo formato Markdown que el original (si es una línea, una línea). \
Sin comillas, sin explicaciones."""


def build_contract_prompt(request: ContractRequest, today: date | None = None) -> str:
    lines = [
        f"Tipo de contrato: {request.contract_type.label}",
        f"Descripción: {request.description or '(sin descripción)'}",
    ]
    lines += [f"{label}: {value}" for label, value in request.details.filled()]
    lines.append(f"Fecha de hoy: {(today or date.today()).isoformat()}")
    return "\n".join(lines)


def build_edit_prompt(request: EditRequest) -> str:
    prompt = f"Instrucción: {request.action.instruction}\n\nFragmento:\n{request.text}"
    if request.context:
        prompt = f"Contrato completo (solo como contexto):\n{request.context}\n\n---\n\n{prompt}"
    return prompt


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
