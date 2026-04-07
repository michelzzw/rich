"""
Rich Render Service — MGL842 TP2
A minimal FastAPI service that exposes Rich's rendering capabilities over HTTP.
Used to demonstrate Docker containerisation, CI/CD deployment, and observability.
"""
import io
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax

# ── Structured JSON logging (parsed by Loki) ─────────────────────────────────
handler = logging.StreamHandler()
handler.setFormatter(
    jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("rich_service")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Rich Render Service",
    description="HTTP wrapper around the Rich Python library (MGL842 TP2 demo).",
    version="1.0.0",
)

# ── CORS (allow file:// and any local origin for demo) ───────────────────────
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Prometheus metrics (auto-instruments all endpoints) ──────────────────────
Instrumentator().instrument(app).expose(app)


class RenderRequest(BaseModel):
    content: str
    format: str = "markdown"  # "markdown" | "syntax" | "text"
    language: str = "python"  # used when format == "syntax"


class RenderResponse(BaseModel):
    html: str
    ansi: str
    format: str
    content_length: int


@app.get("/health")
def health():
    """Liveness probe — used by Docker HEALTHCHECK and Kubernetes."""
    return {"status": "ok", "service": "rich-render"}


@app.post("/render", response_model=RenderResponse)
def render(request: RenderRequest):
    """
    Render *content* using Rich and return both an ANSI string and an HTML export.

    Supported formats:
    - ``markdown``: Rich Markdown renderer
    - ``syntax``:   Syntax-highlighted code block (language defaults to ``python``)
    - ``text``:     Plain Rich console output
    """
    logger.info(
        "render request",
        extra={
            "format": request.format,
            "language": request.language,
            "size": len(request.content),
        },
    )

    try:
        if request.format == "markdown":
            renderable = Markdown(request.content)
        elif request.format == "syntax":
            renderable = Syntax(
                request.content, request.language, theme="monokai", line_numbers=True
            )
        elif request.format == "text":
            renderable = request.content
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown format '{request.format}'. Use 'markdown', 'syntax', or 'text'.",
            )

        # ANSI output (for terminal consumers)
        ansi_buf = io.StringIO()
        ansi_console = Console(file=ansi_buf, force_terminal=True, width=100)
        ansi_console.print(renderable)

        # HTML output (for web consumers / reports)
        html_console = Console(record=True, width=100)
        html_console.print(renderable)

        return RenderResponse(
            html=html_console.export_html(),
            ansi=ansi_buf.getvalue(),
            format=request.format,
            content_length=len(request.content),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("render failed", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc
