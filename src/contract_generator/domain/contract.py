"""Entidades del dominio: tipos de contrato, solicitudes y acciones de edición."""

from dataclasses import dataclass, field
from enum import StrEnum

MAX_DESCRIPTION = 4000
MAX_DETAIL = 300
MAX_EDIT_TEXT = 8000
MAX_CONTEXT = 40000
MAX_REFERENCE = 20000


class ValidationError(ValueError):
    """Datos de entrada inválidos (se traduce a HTTP 400)."""


class ContractType(StrEnum):
    SERVICIOS = "servicios"
    PAGO = "pago"
    NDA = "nda"
    MANTENIMIENTO = "mantenimiento"
    CONTRATISTA = "contratista"
    PERSONALIZADO = "personalizado"

    @property
    def label(self) -> str:
        return _TYPE_LABELS[self]

    @classmethod
    def parse(cls, value: str | None) -> "ContractType":
        if not value:
            return cls.PERSONALIZADO
        try:
            return cls(value)
        except ValueError as exc:
            raise ValidationError(f"Tipo de contrato desconocido: {value}") from exc


_TYPE_LABELS = {
    ContractType.SERVICIOS: "Contrato de prestación de servicios",
    ContractType.PAGO: "Acuerdo de pago",
    ContractType.NDA: "Acuerdo de confidencialidad (NDA)",
    ContractType.MANTENIMIENTO: "Contrato de mantenimiento",
    ContractType.CONTRATISTA: "Contrato de contratista independiente",
    ContractType.PERSONALIZADO: "Contrato personalizado",
}


class EditAction(StrEnum):
    MEJORAR = "mejorar"
    ACORTAR = "acortar"
    ALARGAR = "alargar"
    GRAMATICA = "gramatica"

    @property
    def instruction(self) -> str:
        return _EDIT_INSTRUCTIONS[self]

    @classmethod
    def parse(cls, value: str | None) -> "EditAction":
        try:
            return cls(value or "")
        except ValueError as exc:
            raise ValidationError(f"Acción desconocida: {value}") from exc


_EDIT_INSTRUCTIONS = {
    EditAction.MEJORAR: "Mejora la redacción: hazla más clara, precisa y profesional, con lenguaje jurídico adecuado.",
    EditAction.ACORTAR: "Acorta el texto conservando su significado, obligaciones y datos clave.",
    EditAction.ALARGAR: "Amplía el texto con contexto y lenguaje de apoyo útil para un contrato, "
    "sin inventar cifras ni nombres.",
    EditAction.GRAMATICA: "Corrige gramática, puntuación, ortografía y estructura de las oraciones. "
    "No cambies el contenido.",
}


@dataclass(frozen=True)
class ContractDetails:
    parte_a: str = ""
    parte_b: str = ""
    monto: str = ""
    vigencia: str = ""
    jurisdiccion: str = ""

    LABELS = {
        "parte_a": "Parte A (proveedor/emisor)",
        "parte_b": "Parte B (cliente/receptor)",
        "monto": "Monto y forma de pago",
        "vigencia": "Vigencia / fechas",
        "jurisdiccion": "Jurisdicción / ley aplicable",
    }

    @classmethod
    def from_dict(cls, data: dict | None) -> "ContractDetails":
        data = data or {}
        values = {}
        for key in cls.LABELS:
            value = str(data.get(key) or "").strip()
            if len(value) > MAX_DETAIL:
                raise ValidationError(f"El campo '{key}' supera {MAX_DETAIL} caracteres.")
            values[key] = value
        return cls(**values)

    def filled(self) -> list[tuple[str, str]]:
        """Pares (etiqueta, valor) de los campos con contenido."""
        return [(label, getattr(self, key)) for key, label in self.LABELS.items() if getattr(self, key)]


@dataclass(frozen=True)
class ContractRequest:
    description: str
    contract_type: ContractType = ContractType.PERSONALIZADO
    details: ContractDetails = field(default_factory=ContractDetails)
    reference: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ContractRequest":
        description = str(data.get("description") or "").strip()
        contract_type = ContractType.parse(data.get("type"))
        reference = str(data.get("reference") or "").strip()
        if not description and not reference and contract_type is ContractType.PERSONALIZADO:
            raise ValidationError("Describe el contrato, elige un tipo o sube un documento.")
        if len(description) > MAX_DESCRIPTION:
            raise ValidationError(f"La descripción supera {MAX_DESCRIPTION} caracteres.")
        if len(reference) > MAX_REFERENCE:
            raise ValidationError(f"El documento de referencia supera {MAX_REFERENCE} caracteres.")
        return cls(description, contract_type, ContractDetails.from_dict(data.get("details")), reference)


@dataclass(frozen=True)
class EditRequest:
    text: str
    action: EditAction
    context: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "EditRequest":
        text = str(data.get("text") or "").strip()
        if not text:
            raise ValidationError("No hay texto seleccionado.")
        if len(text) > MAX_EDIT_TEXT:
            raise ValidationError(f"La selección supera {MAX_EDIT_TEXT} caracteres.")
        context = str(data.get("context") or "")[:MAX_CONTEXT]
        return cls(text, EditAction.parse(data.get("action")), context)
