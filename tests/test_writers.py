from datetime import date
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

from contract_generator.data import ClaudeWriter, WriterError
from contract_generator.data.claude_writer import build_contract_prompt
from contract_generator.domain import ContractRequest, EditRequest


def contract(text):
    return "".join(text)


# --- Plantilla offline ---


def test_template_uses_details(template_writer):
    req = ContractRequest.from_dict(
        {"description": "Diseño web", "type": "servicios", "details": {"parte_a": "Luna", "monto": "USD 900"}}
    )
    text = contract(template_writer.stream_contract(req))
    assert text.startswith("# CONTRATO DE PRESTACIÓN DE SERVICIOS")
    assert "21/10/2026" in text
    assert "**Luna**" in text and "USD 900" in text
    assert "[Nombre de la Parte B]" in text


def test_template_nda_has_confidentiality_clauses(template_writer):
    text = contract(template_writer.stream_contract(ContractRequest.from_dict({"type": "nda"})))
    assert "INFORMACIÓN CONFIDENCIAL" in text
    assert "PRECIO Y FORMA DE PAGO" not in text


def test_template_shorten_keeps_heading(template_writer):
    section = "## SEGUNDA. PAGO\n\nUno. Dos. Tres. Cuatro."
    out = template_writer.rewrite(EditRequest.from_dict({"text": section, "action": "acortar"}))
    assert out == "## SEGUNDA. PAGO\n\nUno. Dos."


def test_template_grammar(template_writer):
    out = template_writer.rewrite(EditRequest.from_dict({"text": "uno .  dos ; tres", "action": "gramatica"}))
    assert out == "Uno. dos; tres"


# --- Claude (cliente simulado, sin red) ---


class FakeStream:
    def __init__(self, chunks, stop_reason):
        self.text_stream = iter(chunks)
        self._final = SimpleNamespace(stop_reason=stop_reason)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


def fake_client(chunks=("Hola", " mundo"), stop_reason="end_turn", error=None):
    calls = []

    def stream(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return FakeStream(chunks, stop_reason)

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    return client, calls


def test_claude_writer_request_shape():
    client, calls = fake_client()
    writer = ClaudeWriter("claude-opus-5-5", client=client)
    out = contract(writer.stream_contract(ContractRequest.from_dict({"description": "NDA", "type": "nda"})))
    assert out == "Hola mundo"
    kwargs = calls[0]
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert "Acuerdo de confidencialidad" in kwargs["messages"][0]["content"]


def test_claude_writer_refusal_raises():
    client, _ = fake_client(stop_reason="refusal")
    writer = ClaudeWriter("m", client=client)
    with pytest.raises(WriterError):
        contract(writer.stream_contract(ContractRequest.from_dict({"type": "nda"})))


def test_claude_writer_maps_auth_error():
    response = httpx.Response(401, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    error = anthropic.AuthenticationError("bad key", response=response, body=None)
    client, _ = fake_client(error=error)
    with pytest.raises(WriterError, match="API key"):
        ClaudeWriter("m", client=client).rewrite(EditRequest.from_dict({"text": "hola", "action": "mejorar"}))


def test_contract_prompt_includes_only_filled_details():
    req = ContractRequest.from_dict({"description": "Web", "details": {"jurisdiccion": "Costa Rica"}})
    prompt = build_contract_prompt(req, today=date(2026, 1, 2))
    assert "Jurisdicción / ley aplicable: Costa Rica" in prompt
    assert "Parte A" not in prompt
    assert "2026-01-02" in prompt
