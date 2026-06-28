"""Extração de dados do caso a partir do PDF dos autos."""

import base64

from app.claude_client import gerar_json

# Limite de tamanho do PDF aceito pela API (32 MB por requisição).
MAX_PDF_BYTES = 32 * 1024 * 1024

SYSTEM_PDF = """\
Você apoia o gabinete de um(a) Desembargador(a) extraindo, de peças processuais \
(PDF dos autos), os dados necessários para análise do recurso. Leia o documento \
e preencha os campos solicitados de forma objetiva e fiel ao que consta nos \
autos. Não invente informações: se um campo não puder ser determinado a partir \
do documento, deixe-o como string vazia. O campo 'relatorio' deve trazer um \
resumo estruturado dos fatos, da decisão recorrida e do andamento processual.
"""

SCHEMA_PDF = {
    "type": "object",
    "properties": {
        "tipo_recurso": {"type": "string"},
        "numero_processo": {"type": "string"},
        "partes": {"type": "string"},
        "relatorio": {"type": "string"},
        "decisao_recorrida": {"type": "string"},
        "razoes_recurso": {"type": "string"},
        "contrarrazoes": {"type": "string"},
        "questoes_juridicas": {"type": "string"},
    },
    "required": [
        "tipo_recurso",
        "numero_processo",
        "partes",
        "relatorio",
        "decisao_recorrida",
        "razoes_recurso",
        "contrarrazoes",
        "questoes_juridicas",
    ],
    "additionalProperties": False,
}


def extrair_dados_pdf(pdf_bytes: bytes) -> dict:
    """Extrai os campos do caso a partir do PDF dos autos."""
    if not pdf_bytes.startswith(b"%PDF"):
        return {"erro": "O arquivo enviado não parece ser um PDF válido."}
    if len(pdf_bytes) > MAX_PDF_BYTES:
        return {"erro": "PDF muito grande (limite de 32 MB por requisição)."}

    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        },
        {
            "type": "text",
            "text": (
                "Extraia os dados do caso a partir destes autos, preenchendo "
                "os campos do formato solicitado."
            ),
        },
    ]
    return gerar_json(SYSTEM_PDF, content, SCHEMA_PDF, max_tokens=8000)
