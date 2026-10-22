import pytest

from contract_generator.domain import (
    MAX_DESCRIPTION,
    ContractRequest,
    ContractType,
    EditAction,
    EditRequest,
    ValidationError,
)


def test_request_parses_type_and_trims_details():
    req = ContractRequest.from_dict(
        {"description": " Diseño web ", "type": "servicios", "details": {"parte_a": "  Luna  ", "otro": "x"}}
    )
    assert req.description == "Diseño web"
    assert req.contract_type is ContractType.SERVICIOS
    assert req.details.parte_a == "Luna"
    assert req.details.filled() == [("Parte A (proveedor/emisor)", "Luna")]


def test_type_alone_is_enough():
    assert ContractRequest.from_dict({"type": "nda"}).contract_type is ContractType.NDA


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"description": "   "},
        {"description": "x", "type": "inventado"},
        {"description": "x" * (MAX_DESCRIPTION + 1)},
        {"description": "x", "details": {"monto": "9" * 301}},
    ],
)
def test_invalid_requests(data):
    with pytest.raises(ValidationError):
        ContractRequest.from_dict(data)


def test_edit_request_validation():
    req = EditRequest.from_dict({"text": " hola ", "action": "acortar"})
    assert req.text == "hola" and req.action is EditAction.ACORTAR
    with pytest.raises(ValidationError):
        EditRequest.from_dict({"text": "", "action": "acortar"})
    with pytest.raises(ValidationError):
        EditRequest.from_dict({"text": "hola", "action": "borrar"})


def test_every_type_and_action_has_text():
    assert all(t.label for t in ContractType)
    assert all(a.instruction for a in EditAction)
