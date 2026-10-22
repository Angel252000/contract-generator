from contract_generator.api import cli
from contract_generator.service import ContractService


def test_split_sections():
    sections = cli.split_sections("# T\n\nIntro\n\n## PRIMERA\n\nA\n\n## SEGUNDA\n\nB")
    assert len(sections) == 3
    assert sections[2].startswith("## SEGUNDA")


def test_cli_flow(monkeypatch, tmp_path, template_writer, capsys):
    answers = iter(["3", "NDA para un prototipo", "Ana", "Beto", "", "", "Costa Rica", "acortar 2", "guardar", "salir"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.chdir(tmp_path)

    cli.run(ContractService(template_writer))

    out = capsys.readouterr().out
    assert "ACUERDO DE CONFIDENCIALIDAD" in out
    saved = list(tmp_path.glob("contrato_*.md"))
    assert len(saved) == 1
    assert "## SEGUNDA. INFORMACIÓN CONFIDENCIAL" in saved[0].read_text(encoding="utf-8")


def test_cli_rejects_bad_command(monkeypatch, template_writer, capsys):
    answers = iter(["", "Servicio de limpieza", "", "", "", "", "", "borrar 1", "mejorar 99", "salir"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    cli.run(ContractService(template_writer))
    out = capsys.readouterr().out
    assert "Error: Acción desconocida: borrar" in out
    assert "Comando no válido" in out
