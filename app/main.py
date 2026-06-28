"""Aplicação FastAPI — Assistente de Desembargador."""

from pathlib import Path

from fastapi import FastAPI, File, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app import __version__
from app.claude_client import gerar_minuta_stream
from app.config import settings
from app.docx_export import montar_docx
from app.jurisprudencia import consultar_datajud, pesquisar_julgados_stream
from app.pdf_autos import extrair_dados_pdf
from app.schemas import (
    DataJudRequest,
    ExportarDocxRequest,
    JurisprudenciaRequest,
    MinutaRequest,
    TriagemRequest,
)
from app.triagem import classificar_processo

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

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


@app.post("/api/extrair-pdf")
async def extrair_pdf(arquivo: UploadFile = File(...)) -> dict:
    """Extrai os dados do caso a partir do PDF dos autos."""
    if not settings.anthropic_api_key:
        return {"erro": "ANTHROPIC_API_KEY não configurada."}
    dados = await arquivo.read()
    if not dados:
        return {"erro": "Arquivo vazio."}
    return extrair_dados_pdf(dados)


@app.post("/api/triagem")
def triagem(req: TriagemRequest) -> dict:
    """Classifica e tria um processo a partir de sua descrição."""
    if not settings.anthropic_api_key:
        return {"erro": "ANTHROPIC_API_KEY não configurada."}
    return classificar_processo(req.texto)


@app.post("/api/exportar-docx")
def exportar_docx(req: ExportarDocxRequest) -> Response:
    """Converte a minuta em documento Word (.docx) para download."""
    if not req.texto.strip():
        return Response(content="Texto vazio.", status_code=400)
    conteudo = montar_docx(req.texto, titulo=req.titulo())
    return Response(
        content=conteudo,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{req.nome_arquivo()}"'
        },
    )
