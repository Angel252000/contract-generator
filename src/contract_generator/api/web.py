"""Aplicación web (Flask). Ejecutar: contract-generator-web  →  http://127.0.0.1:5050"""

import json
import logging
import re
import unicodedata
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from .. import __version__
from ..config import Settings
from ..data import WriterError
from ..domain import ContractType, ValidationError
from ..service import ContractService, create_service, extract_text, html_to_docx

log = logging.getLogger(__name__)
PACKAGE_DIR = Path(__file__).resolve().parent.parent
MAX_BODY_BYTES = 5_000_000

# Sugerencias bajo la caja de texto: (etiqueta, tipo, texto de ejemplo)
SUGGESTIONS = [
    (
        "Acuerdo de servicios",
        "servicios",
        "Crea un acuerdo de servicios claro para trabajo freelance de diseño web, con 3 rondas de revisiones, "
        "50% de anticipo y entrega en 4 semanas.",
    ),
    (
        "Acuerdo de confidencialidad",
        "nda",
        "NDA mutuo para compartir el prototipo de una app con un posible inversor durante 2 años.",
    ),
    (
        "Acuerdo de mantenimiento",
        "mantenimiento",
        "Contrato de mantenimiento mensual de equipos de aire acondicionado para una oficina, con visitas "
        "trimestrales y atención de emergencias en 24 horas.",
    ),
    (
        "Carta de autorización",
        "personalizado",
        "Carta de autorización para que un familiar retire documentos y realice trámites en mi nombre ante "
        "una universidad.",
    ),
    (
        "Acuerdo de pago",
        "pago",
        "Acuerdo de pago en 6 cuotas mensuales para saldar una deuda de USD 3.000 entre dos personas.",
    ),
    (
        "Contratista independiente",
        "contratista",
        "Contrato de contratista independiente para un desarrollador que trabajará a distancia por horas, "
        "con propiedad intelectual a favor de la empresa.",
    ),
]
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "contrato"


def create_app(service: ContractService | None = None, settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    service = service or create_service(settings)

    app = Flask(__name__, template_folder=str(PACKAGE_DIR / "templates"), static_folder=str(PACKAGE_DIR / "static"))
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(WriterError)
    def writer_error(exc):
        return jsonify(error=str(exc)), 502

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify(error="La solicitud es demasiado grande."), 413

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            types=list(ContractType),
            suggestions=SUGGESTIONS,
            ai=service.uses_ai,
            provider=settings.label,
            model=settings.model,
            free=settings.free,
            version=__version__,
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok", version=__version__, writer=service.writer.name, model=settings.model)

    @app.post("/api/generate")
    def generate():
        chunks = service.generate(request.get_json(silent=True) or {})  # valida antes de abrir el stream

        def events():
            try:
                for chunk in chunks:
                    yield _sse({"text": chunk})
                yield _sse({"done": True})
            except WriterError as exc:
                yield _sse({"error": str(exc)})
            except Exception:
                log.exception("Fallo inesperado generando el contrato")
                yield _sse({"error": "Error inesperado al generar el contrato."})

        return Response(events(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.post("/api/edit")
    def edit():
        return jsonify(text=service.edit(request.get_json(silent=True) or {}))

    @app.post("/api/extract")
    def extract():
        upload = request.files.get("file")
        if upload is None:
            raise ValidationError("No se recibió ningún archivo.")
        text = extract_text(upload.filename or "", upload.read())
        return jsonify(name=upload.filename, text=text, chars=len(text))

    @app.post("/api/export/docx")
    def export_docx():
        data = request.get_json(silent=True) or {}
        html = str(data.get("html") or "")
        if not html.strip():
            raise ValidationError("No hay contenido para exportar.")
        filename = _slug(str(data.get("title") or "contrato")) + ".docx"
        return Response(
            html_to_docx(html),
            mimetype=DOCX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()
    app = create_app(settings=settings)
    mode = f"IA {settings.label} ({settings.model})" if settings.uses_ai else "plantilla (sin IA)"
    log.info("Generador de contratos en http://%s:%s — modo %s", settings.host, settings.port, mode)
    if settings.debug:
        app.run(host=settings.host, port=settings.port, debug=True, threaded=True)
    else:
        from waitress import serve

        serve(app, host=settings.host, port=settings.port, threads=8)


if __name__ == "__main__":
    main()
