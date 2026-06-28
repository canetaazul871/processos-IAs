"""Aplicação FastAPI — Assistente de Desembargador."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app import __version__
from app.claude_client import gerar_minuta_stream
from app.config import settings
from app.jurisprudencia import consultar_datajud, pesquisar_julgados_stream
from app.schemas import DataJudRequest, JurisprudenciaRequest, MinutaRequest

app = FastAPI(
    title="Assistente de Desembargador",
    description="Geração de minutas de voto e ementa com apoio de IA (Claude).",
    version=__version__,
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve a interface web."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    """Verifica status da aplicação e se a chave de API está configurada."""
    return {
        "status": "ok",
        "modelo": settings.anthropic_model,
        "api_key_configurada": bool(settings.anthropic_api_key),
        "versao": __version__,
    }


@app.post("/api/minutar")
def minutar(req: MinutaRequest) -> StreamingResponse:
    """Gera a minuta de voto em streaming (text/plain incremental)."""
    if not settings.anthropic_api_key:
        return StreamingResponse(
            iter(
                [
                    "ERRO: ANTHROPIC_API_KEY não configurada. "
                    "Defina a variável de ambiente (ver .env.example)."
                ]
            ),
            media_type="text/plain; charset=utf-8",
            status_code=503,
        )

    if not req.tem_conteudo_minimo():
        return StreamingResponse(
            iter(
                [
                    "ERRO: informe ao menos o relatório, as razões do recurso "
                    "ou a decisão recorrida para gerar a minuta."
                ]
            ),
            media_type="text/plain; charset=utf-8",
            status_code=400,
        )

    return StreamingResponse(
        gerar_minuta_stream(req),
        media_type="text/plain; charset=utf-8",
    )


@app.post("/api/jurisprudencia")
def jurisprudencia(req: JurisprudenciaRequest) -> StreamingResponse:
    """Pesquisa jurisprudência em fontes oficiais (streaming, text/plain)."""
    if not settings.anthropic_api_key:
        return StreamingResponse(
            iter(["ERRO: ANTHROPIC_API_KEY não configurada."]),
            media_type="text/plain; charset=utf-8",
            status_code=503,
        )
    if not req.consulta.strip():
        return StreamingResponse(
            iter(["ERRO: informe a tese ou o assunto a pesquisar."]),
            media_type="text/plain; charset=utf-8",
            status_code=400,
        )
    return StreamingResponse(
        pesquisar_julgados_stream(req.consulta, req.tribunal or None),
        media_type="text/plain; charset=utf-8",
    )


@app.post("/api/datajud")
def datajud(req: DataJudRequest) -> dict:
    """Consulta processual à API Pública do DataJud (CNJ)."""
    return consultar_datajud(req.numero_processo, req.tribunal)
