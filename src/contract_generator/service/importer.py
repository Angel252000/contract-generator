"""Extrae el texto de un documento subido (.txt, .md, .docx) para usarlo como referencia."""

from io import BytesIO
from pathlib import PurePath

from docx import Document

from ..domain import MAX_REFERENCE, ValidationError

SUPPORTED = {".txt", ".md", ".docx"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = PurePath(filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise ValidationError("Formato no soportado. Sube un archivo .docx, .txt o .md.")
    if suffix == ".docx":
        try:
            doc = Document(BytesIO(content))
        except Exception as exc:  # python-docx lanza varios tipos ante archivos corruptos
            raise ValidationError("No se pudo leer el archivo .docx.") from exc
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        text = content.decode("utf-8", errors="replace")
    text = text.strip()
    if not text:
        raise ValidationError("El documento está vacío.")
    return text[:MAX_REFERENCE]
