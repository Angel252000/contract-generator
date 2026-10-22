"""Punto de entrada para Vercel: expone la app Flask como función serverless."""

import sys
from pathlib import Path

# Vercel no siempre instala el paquete local; se agrega src/ al path por si acaso.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contract_generator.api.web import create_app  # noqa: E402

app = create_app()
