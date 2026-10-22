"""Redactor offline: plantilla fija, sin IA. Se usa cuando no hay credenciales."""

import re
from collections.abc import Iterator
from datetime import date

from ..domain import ContractRequest, ContractType, EditAction, EditRequest

ORDINALS = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA", "OCTAVA", "NOVENA", "DÉCIMA"]


class TemplateWriter:
    name = "plantilla"
    uses_ai = False

    def __init__(self, today: date | None = None):
        self._today = today

    def stream_contract(self, request: ContractRequest) -> Iterator[str]:
        d = request.details
        a = d.parte_a or "[Nombre de la Parte A]"
        b = d.parte_b or "[Nombre de la Parte B]"
        hoy = (self._today or date.today()).strftime("%d/%m/%Y")

        yield f"# {request.contract_type.label.upper()}\n\n[Ciudad], {hoy}\n\n"
        yield (
            f"Entre **{a}**, en adelante «la Parte A», y **{b}**, en adelante «la Parte B», "
            "se celebra el presente contrato sujeto a las siguientes cláusulas:\n\n"
        )
        for ordinal, (name, body) in zip(ORDINALS, self._clauses(request, a, b), strict=False):
            yield f"## {ordinal}. {name}\n\n{body}\n\n"
        yield "---\n\n"
        for who in (a, b):
            yield (
                f"**{who}**\n\nFirma: ______________________\n\n"
                "Nombre y documento: ______________________\n\nFecha: ____/____/______\n\n"
            )

    def rewrite(self, request: EditRequest) -> str:
        text = request.text.strip()
        if request.action is EditAction.ACORTAR:
            heading = ""
            if text.startswith("#"):  # conservar el título de la cláusula
                heading, _, text = text.partition("\n")
                heading += "\n\n"
            sentences = re.split(r"(?<=[.;])\s+", text.strip())
            return heading + " ".join(sentences[: max(1, (len(sentences) + 1) // 2)])
        if request.action is EditAction.GRAMATICA:
            fixed = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"[ \t]+", " ", text))
            return fixed[:1].upper() + fixed[1:]
        if request.action is EditAction.ALARGAR:
            return text + " Lo anterior se interpretará de buena fe y conforme a la naturaleza del presente contrato."
        return text

    @staticmethod
    def _clauses(request: ContractRequest, a: str, b: str) -> list[tuple[str, str]]:
        d = request.details
        objeto = request.description or "[Descripción del objeto del contrato]"
        clauses = [("OBJETO", f"El presente contrato tiene por objeto: {objeto}")]
        if request.contract_type is ContractType.NDA:
            clauses += [
                (
                    "INFORMACIÓN CONFIDENCIAL",
                    "Se considera confidencial toda información técnica, comercial o financiera que una parte "
                    "revele a la otra, por cualquier medio, salvo la que sea de dominio público.",
                ),
                (
                    "OBLIGACIONES DE CONFIDENCIALIDAD",
                    "La parte receptora usará la información solo para los fines de este acuerdo, no la "
                    "divulgará a terceros sin autorización escrita y la devolverá o destruirá al terminar.",
                ),
            ]
        else:
            clauses += [
                (
                    "OBLIGACIONES DE LAS PARTES",
                    f"{a} se obliga a cumplir el objeto descrito con diligencia y conforme a lo pactado. "
                    f"{b} se obliga a brindar la información y colaboración necesarias "
                    "y a cumplir los pagos acordados.",
                ),
                ("PRECIO Y FORMA DE PAGO", f"Las partes acuerdan: {d.monto or '[Monto y forma de pago]'}."),
            ]
        clauses += [
            (
                "VIGENCIA",
                f"Este contrato estará vigente desde {d.vigencia or '[Fecha de inicio] hasta [Fecha de término]'}.",
            ),
            (
                "CONFIDENCIALIDAD",
                "Las partes guardarán reserva sobre la información que conozcan con motivo de este contrato.",
            ),
            (
                "TERMINACIÓN",
                "Cualquiera de las partes podrá terminar el contrato con un preaviso escrito de [30] días, "
                "o de inmediato ante incumplimiento grave de la otra parte.",
            ),
            (
                "LEY APLICABLE Y CONTROVERSIAS",
                f"Este contrato se rige por las leyes de {d.jurisdiccion or '[País / jurisdicción]'}. Las partes "
                "procurarán resolver sus diferencias de buena fe antes de acudir a los tribunales competentes.",
            ),
            (
                "DISPOSICIONES GENERALES",
                "Toda modificación deberá constar por escrito y firmada por ambas partes. "
                "Si una cláusula fuese nula, las demás seguirán vigentes.",
            ),
        ]
        return clauses
