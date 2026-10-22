"""Interfaz de los redactores de contratos."""

from collections.abc import Iterator
from typing import Protocol

from ..domain import ContractRequest, EditRequest


class WriterError(RuntimeError):
    """Fallo del redactor con un mensaje apto para mostrar al usuario."""


class ContractWriter(Protocol):
    name: str
    uses_ai: bool

    def stream_contract(self, request: ContractRequest) -> Iterator[str]:
        """Devuelve el contrato en Markdown, por fragmentos."""
        ...

    def rewrite(self, request: EditRequest) -> str:
        """Devuelve el fragmento reescrito según la acción pedida."""
        ...
