"""Casos de uso: generar un contrato y editar un fragmento."""

from collections.abc import Iterator

from ..config import Settings
from ..data import ClaudeWriter, ContractWriter, TemplateWriter
from ..domain import ContractRequest, EditRequest


class ContractService:
    def __init__(self, writer: ContractWriter):
        self.writer = writer

    @property
    def uses_ai(self) -> bool:
        return self.writer.uses_ai

    def generate(self, data: dict) -> Iterator[str]:
        """Valida la solicitud (lanza ValidationError) y devuelve el contrato por fragmentos."""
        request = ContractRequest.from_dict(data)
        return self.writer.stream_contract(request)

    def edit(self, data: dict) -> str:
        return self.writer.rewrite(EditRequest.from_dict(data))


def create_service(settings: Settings) -> ContractService:
    """Usa Claude si hay credenciales; si no, la plantilla offline."""
    if settings.has_credentials:
        return ContractService(ClaudeWriter(settings.model))
    return ContractService(TemplateWriter())
