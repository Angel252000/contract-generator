# Generador de contratos con IA

[![CI](https://github.com/Angel252000/contract-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Angel252000/contract-generator/actions/workflows/ci.yml)

Describe el contrato que necesitas, obtén un borrador completo redactado por IA, edítalo en el
navegador y descárgalo en Word, HTML o PDF. Funciona con **IA gratuita** (Ollama en local, Groq o Gemini en
la nube) o con Claude. Incluye versión web y de consola.

**Demo:** https://contract-generator-ten-tau.vercel.app (modo plantilla, sin IA)

> Los borradores son orientativos y no constituyen asesoría legal.

![Pantalla de inicio: caja tipo chat con Subir y Generar](docs/hero.png)

![Editor con el menú de edición con IA](docs/editor.png)

## Funciones

- **Caja tipo chat** con sugerencias de un clic (servicios, NDA, mantenimiento, carta de autorización, pago,
  contratista independiente) que rellenan la descripción y el tipo de contrato.
- **Subir documento** (.docx, .txt, .md) para usarlo como base o fuente de datos del borrador.
- **6 tipos de contrato:** prestación de servicios, acuerdo de pago, NDA, mantenimiento, contratista
  independiente y personalizado, más campos opcionales (partes, monto, vigencia, jurisdicción).
- **Generación en streaming:** el contrato aparece mientras se redacta.
- **Edición con IA sobre la selección:** mejorar redacción, acortar, alargar, corregir gramática.
- **Edición manual** directa en la hoja; el borrador se guarda en el navegador.
- **Exportación:** Word (.docx real), HTML, PDF (imprimir) y copiar.
- **Varios proveedores de IA, elegidos solos:** Ollama (local, gratis, sin cuenta), Groq y Gemini (nube,
  plan gratuito) o Claude. Sin ninguno, **modo plantilla** offline.
- **CLI:** mismo flujo en la terminal, con edición por número de cláusula.

## Inicio rápido

Requiere Python 3.11+ y [uv](https://docs.astral.sh/uv/) (o `pip`).

```bash
git clone https://github.com/Angel252000/contract-generator.git
cd contract-generator
uv venv && uv pip install -e ".[dev]"
cp .env.example .env          # opcional: claves de Groq, Gemini o Anthropic

.venv/bin/contract-generator-web   # web → http://127.0.0.1:5050
.venv/bin/contract-generator       # consola
```

### IA gratis

| Opción | Cómo | Notas |
|---|---|---|
| **Ollama** (local) | Instala [Ollama](https://ollama.com), `ollama pull gemma3:4b`, `OLLAMA_MODEL=gemma3:4b` | Sin cuenta ni internet. Solo en tu equipo: no sirve en Vercel. |
| **Groq** (nube) | Clave gratis en [console.groq.com/keys](https://console.groq.com/keys) → `GROQ_API_KEY` | Muy rápido; modelo por defecto `llama-3.3-70b-versatile`. |
| **Gemini** (nube) | Clave gratis en [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → `GEMINI_API_KEY` | Modelo por defecto `gemini-2.5-flash`. |

Orden de elección automática: `AI_PROVIDER` si está definido → primera clave encontrada (Anthropic, Groq,
Gemini) → Ollama si responde en `localhost:11434` → modo plantilla.

| Variable | Por defecto | Uso |
|---|---|---|
| `AI_PROVIDER` | automático | `anthropic`, `groq`, `gemini`, `ollama` o `plantilla`. |
| `AI_MODEL` | según proveedor | Modelo a usar. |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | — | Claves de cada proveedor. |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | `gemma3:1b` / `http://localhost:11434/v1` | Ollama local. |
| `HOST` / `PORT` | `127.0.0.1` / `5050` | Dirección del servidor web. |
| `FLASK_DEBUG` | — | `1` usa el servidor de desarrollo de Flask en vez de waitress. |

## Arquitectura

```
src/contract_generator/
├── domain/     entidades y validación (tipos de contrato, solicitudes, acciones de edición)
├── data/       redactores detrás de la interfaz ContractWriter: Claude, compatibles con OpenAI
│               (Ollama, Groq, Gemini) y plantilla offline
├── service/    casos de uso (generar, editar) y exportación a .docx
├── api/        web (Flask + SSE, servida con waitress) y CLI
├── templates/  interfaz HTML
└── static/     CSS y JS del editor
```

Las dependencias van hacia adentro: `api → service → data → domain`. El redactor se elige al arrancar
(`create_service`) según el proveedor que resuelve `Settings.from_env()`.

### API HTTP

| Método | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| `POST` | `/api/generate` | `{description, type, details, reference}` | `text/event-stream` con `{text}`, `{done}` o `{error}` |
| `POST` | `/api/extract` | multipart `file` (.docx/.txt/.md) | `{name, text, chars}` |
| `POST` | `/api/edit` | `{text, action, context}` | `{text}` |
| `POST` | `/api/export/docx` | `{html, title}` | archivo `.docx` |
| `GET` | `/healthz` | — | `{status, version, writer}` |

Errores de validación → `400`; fallos de la API de Claude → `502`; cuerpo > 5 MB → `413`.

## Despliegue en Vercel

Vercel detecta Flask solo: `api/index.py` expone `app` y las dependencias salen de `pyproject.toml`.
No hace falta `vercel.json` (una regla `rewrites` hacia `/api/index` rompe las rutas: Flask recibe la ruta
reescrita y devuelve 404).

```bash
vercel deploy --prod --project contract-generator
vercel env add GROQ_API_KEY production   # IA gratis en producción (o GEMINI_API_KEY)
vercel deploy --prod --project contract-generator   # redesplegar para que tome la clave
```

> Ollama no funciona en Vercel (corre en tu equipo). Con una clave puesta, cualquiera con el enlace consume
> tu cuota gratuita; con `ANTHROPIC_API_KEY`, tus créditos de pago.

## Desarrollo

```bash
pytest --cov=contract_generator   # pruebas (sin red: los proveedores se simulan)
ruff check . && ruff format .     # lint y formato
```

CI corre lint y pruebas en Python 3.11–3.13 en cada push y PR.

## Licencia

MIT
