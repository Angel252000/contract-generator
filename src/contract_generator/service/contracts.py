"""Casos de uso: generar un contrato y editar un fragmento."""

from collections.abc import Iterator

from ..config import Settings
from ..data import ClaudeWriter, ContractWriter, OpenAICompatWriter, TemplateWriter
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


def build_writer(settings: Settings) -> ContractWriter:
    if settings.provider == "anthropic":
        return ClaudeWriter(settings.model)
    if settings.provider == "plantilla":
        return TemplateWriter()
    return OpenAICompatWriter(settings.provider, settings.label, settings.model, settings.base_url, settings.api_key)


def create_service(settings: Settings) -> ContractService:
    return ContractService(build_writer(settings))
