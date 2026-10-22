"""Versión de consola. Ejecutar: contract-generator"""

import re
from datetime import datetime
from pathlib import Path

from ..config import Settings
from ..data import WriterError
from ..domain import ContractType, EditAction, ValidationError
from ..service import ContractService, create_service

HELP = "Comandos: mejorar|acortar|alargar|gramatica <n° cláusula>, ver, guardar, salir"


def ask(label: str) -> str:
    return input(f"{label}: ").strip()


def split_sections(contract: str) -> list[str]:
    """Separa el contrato en [encabezado, cláusula 1, cláusula 2, ...] usando los títulos '## '."""
    return re.split(r"(?m)^(?=## )", contract)


def run(service: ContractService) -> None:
    print("Generador de contratos con IA" + ("" if service.uses_ai else " (modo plantilla, sin API key)"))
    types = list(ContractType)
    for i, contract_type in enumerate(types, 1):
        print(f"  {i}. {contract_type.label}")
    choice = ask("Tipo (número, Enter = personalizado)")
    contract_type = types[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(types) else None

    data = {"type": contract_type.value if contract_type else "", "description": ask("Describe el contrato")}
    print("Datos opcionales (Enter para omitir):")
    data["details"] = {
        "parte_a": ask("  Parte A (proveedor)"),
        "parte_b": ask("  Parte B (cliente)"),
        "monto": ask("  Monto y forma de pago"),
        "vigencia": ask("  Vigencia / fechas"),
        "jurisdiccion": ask("  Jurisdicción"),
    }

    print("\n" + "-" * 60 + "\n")
    contract = ""
    for chunk in service.generate(data):
        print(chunk, end="", flush=True)
        contract += chunk
    print("\n" + "-" * 60)

    while True:
        sections = split_sections(contract)
        print("\n" + HELP)
        cmd = ask(">").split()
        if not cmd:
            continue
        if cmd[0] == "salir":
            break
        if cmd[0] == "ver":
            print(contract)
        elif cmd[0] == "guardar":
            path = Path(f"contrato_{datetime.now():%Y%m%d_%H%M%S}.md")
            path.write_text(contract, encoding="utf-8")
            print(f"Guardado en {path.resolve()}")
        elif len(cmd) == 2 and cmd[1].isdigit() and 1 <= int(cmd[1]) < len(sections):
            n = int(cmd[1])
            try:
                action = EditAction.parse(cmd[0])
                new = service.edit({"text": sections[n], "action": action.value, "context": contract})
            except (ValidationError, WriterError) as exc:
                print(f"Error: {exc}")
                continue
            sections[n] = new + "\n\n"
            contract = "".join(sections)
            print("\n" + new)
        else:
            print(f"Comando no válido. Hay {len(sections) - 1} cláusulas.")


def main() -> None:
    try:
        run(create_service(Settings.from_env()))
    except (ValidationError, WriterError) as exc:
        print(f"\nError: {exc}")
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
