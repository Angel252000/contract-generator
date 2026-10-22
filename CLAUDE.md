# contract-generator

Generador de contratos con IA (réplica del flujo de Jotform AI Contract Generator): web Flask + CLI. IA: Claude (SDK `anthropic`) o gratis vía API compatible con OpenAI (Ollama local, Groq, Gemini).

## Stack

Python 3.11+, Flask 3, waitress, anthropic 2.x y openai 3.x (ambos usan `httpx2`, no `httpx`), python-docx, python-dotenv. Frontend sin build: HTML + `static/app.js` con marked y DOMPurify desde cdnjs.

## Mapa

- `src/contract_generator/domain/contract.py` — `ContractType`, `EditAction`, `ContractRequest`, `EditRequest`; toda la validación de entrada (lanza `ValidationError`).
- `src/contract_generator/config.py` — `PROVIDERS` y `Settings.from_env()`: `AI_PROVIDER` → primera clave (Anthropic, Groq, Gemini) → Ollama si responde → plantilla.
- `src/contract_generator/data/` — `ContractWriter` (Protocol) con `ClaudeWriter` (streaming + fallbacks), `OpenAICompatWriter` (Ollama/Groq/Gemini) y `TemplateWriter` (offline); prompts compartidos en `prompts.py`.
- `src/contract_generator/service/contracts.py` — `ContractService`, `build_writer` y `create_service`.
- `src/contract_generator/service/export.py` — HTML del editor → `.docx`.
- `src/contract_generator/service/importer.py` — texto de un .docx/.txt/.md subido (campo `reference` de la solicitud).
- `src/contract_generator/api/web.py` — `create_app(service, settings)`; rutas `/`, `/healthz`, `/api/generate` (SSE), `/api/edit`, `/api/extract`, `/api/export/docx`. `SUGGESTIONS` define las sugerencias de la portada.
- `src/contract_generator/static/app.css` — tema "Aurora Legal" (oscuro): aurora y haz de luz con `@property --angle`; respeta `prefers-reduced-motion`.
- `src/contract_generator/api/cli.py` — CLI interactiva.
- `tests/` — `FakeWriter` en `conftest.py`; Claude se simula con un cliente falso, sin red.

## Arquitectura

Capas `domain → data → service → api`. Lógica de negocio fuera de `api/`; un redactor nuevo implementa `ContractWriter` en `data/`.

## Comandos

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/contract-generator-web     # http://127.0.0.1:5050 (o ~/.claude/scripts/local.sh contratos)
.venv/bin/contract-generator         # CLI
.venv/bin/pytest --cov=contract_generator
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Gotchas

- `ContractService.generate` valida **antes** de devolver el iterador: así `/api/generate` responde 400 en vez de abrir un stream con error.
- Los errores durante el stream viajan como evento SSE `{error}`, no como código HTTP.
- `claude-opus-5-5` no acepta `temperature` ni `thinking: disabled`; la profundidad se controla con `output_config.effort`.
- El HTML que entra al editor siempre pasa por `DOMPurify.sanitize`.
