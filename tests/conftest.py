from collections.abc import Iterator
from datetime import date

import pytest

from contract_generator.api.web import create_app
from contract_generator.config import Settings
from contract_generator.data import TemplateWriter, WriterError
from contract_generator.domain import ContractRequest, EditRequest
from contract_generator.service import ContractService

SETTINGS = Settings(provider="anthropic", model="test-model", port=0)


class FakeWriter:
    """Redactor de prueba: devuelve texto fijo y registra lo que recibe."""

    name = "fake"
    uses_ai = True

    def __init__(self, fail_with: str | None = None):
        self.fail_with = fail_with
        self.requests: list = []

    def stream_contract(self, request: ContractRequest) -> Iterator[str]:
        self.requests.append(request)
        yield "# CONTRATO\n\n"
        if self.fail_with:
            raise WriterError(self.fail_with)
        yield "## PRIMERA. OBJETO\n\nTexto."

    def rewrite(self, request: EditRequest) -> str:
        self.requests.append(request)
        if self.fail_with:
            raise WriterError(self.fail_with)
        return f"[{request.action.value}] {request.text}"


@pytest.fixture
def fake_writer():
    return FakeWriter()


@pytest.fixture
def client(fake_writer):
    app = create_app(ContractService(fake_writer), SETTINGS)
    app.testing = True
    return app.test_client()


@pytest.fixture
def template_writer():
    return TemplateWriter(today=date(2026, 10, 21))
