from types import SimpleNamespace

import httpx2 as httpx
import openai
import pytest

from contract_generator.data import OpenAICompatWriter, WriterError
from contract_generator.domain import ContractRequest, EditRequest


def chunk(text=None, finish=None):
    delta = SimpleNamespace(content=text)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish)])


def fake_client(chunks=(), error=None):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return iter(chunks)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return client, calls


def writer(client, name="ollama"):
    return OpenAICompatWriter(name, name.title(), "modelo-x", "http://x/v1", "", client=client)


def test_streams_content_and_sends_prompts():
    client, calls = fake_client([chunk("# NDA"), SimpleNamespace(choices=[]), chunk("\n\nTexto", "stop")])
    out = "".join(writer(client).stream_contract(ContractRequest.from_dict({"type": "nda"})))
    assert out == "# NDA\n\nTexto"
    kwargs = calls[0]
    assert kwargs["model"] == "modelo-x" and kwargs["stream"] is True
    assert kwargs["messages"][0]["role"] == "system"
    assert "Acuerdo de confidencialidad" in kwargs["messages"][1]["content"]


def test_marks_truncated_output():
    client, _ = fake_client([chunk("Hola", "length")])
    out = "".join(writer(client).stream_contract(ContractRequest.from_dict({"type": "nda"})))
    assert out.endswith("[El texto se cortó por longitud.]")


def test_rewrite_strips_whitespace():
    client, _ = fake_client([chunk("  Texto corregido. "), chunk(None, "stop")])
    out = writer(client).rewrite(EditRequest.from_dict({"text": "texto", "action": "gramatica"}))
    assert out == "Texto corregido."


REQUEST = httpx.Request("POST", "http://x/v1/chat/completions")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (openai.APIConnectionError(request=REQUEST), "¿Está abierto Ollama?"),
        (openai.RateLimitError("r", response=httpx.Response(429, request=REQUEST), body=None), "límite gratuito"),
        (openai.NotFoundError("n", response=httpx.Response(404, request=REQUEST), body=None), "no existe"),
        (openai.AuthenticationError("a", response=httpx.Response(401, request=REQUEST), body=None), "inválida"),
    ],
)
def test_errors_become_writer_errors(error, message):
    client, _ = fake_client(error=error)
    with pytest.raises(WriterError, match=message):
        writer(client).rewrite(EditRequest.from_dict({"text": "hola", "action": "mejorar"}))
