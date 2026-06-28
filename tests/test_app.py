"""Testes de fumaça — não exigem ANTHROPIC_API_KEY nem acesso à rede."""

import io

from docx import Document
from fastapi.testclient import TestClient

from app.docx_export import montar_docx
from app.jurisprudencia import DATAJUD_ALIASES, DOMINIOS_PERMITIDOS, consultar_datajud
from app.main import app
from app.pdf_autos import extrair_dados_pdf
from app.prompts import montar_prompt_usuario
from app.schemas import ExportarDocxRequest, MinutaRequest
from app.triagem import classificar_processo

client = TestClient(app)


def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_entregaveis_ordem_e_fallback():
    req = MinutaRequest(entregaveis=["ementa", "firac", "invalido"])
    assert req.entregaveis_selecionados() == ["firac", "ementa"]
    assert MinutaRequest(entregaveis=[]).entregaveis_selecionados() == [
        "firac",
        "relatorio",
        "voto",
        "ementa",
    ]


def test_prompt_inclui_secoes_selecionadas():
    prompt = montar_prompt_usuario(
        MinutaRequest(entregaveis=["firac", "voto"], relatorio="fato")
    )
    assert "ANÁLISE FIRAC" in prompt
    assert "VOTO" in prompt
    assert "RELATÓRIO" not in prompt.split("DADOS DO CASO")[0]


def test_dominios_e_aliases():
    assert "jusbrasil.com.br" in DOMINIOS_PERMITIDOS
    assert {"stj", "tjpa", "tjsp"} <= DATAJUD_ALIASES


def test_datajud_validacoes_offline():
    assert "erro" in consultar_datajud("123", "tjsp")  # número inválido
    assert "erro" in consultar_datajud("0" * 20, "xxxx")  # tribunal inválido


def test_pdf_e_triagem_validacoes_offline():
    assert "erro" in extrair_dados_pdf(b"isto nao e um pdf")
    assert "erro" in classificar_processo("   ")


def test_docx_gerado_valido():
    texto = "VOTO\n\nNego provimento. **Mantida** a sentença."
    blob = montar_docx(texto, titulo="Apelação Cível")
    assert blob[:2] == b"PK"  # arquivo zip/docx
    doc = Document(io.BytesIO(blob))
    estilos = {p.style.name for p in doc.paragraphs if p.text.strip()}
    assert "Heading 1" in estilos  # 'VOTO' vira título


def test_nome_arquivo_seguro():
    req = ExportarDocxRequest(
        texto="x", numero_processo="0000000-00.0000/8.26.0100 (cópia)"
    )
    nome = req.nome_arquivo()
    assert nome.endswith(".docx")
    assert " " not in nome and "/" not in nome


def test_exportar_docx_endpoint():
    resp = client.post("/api/exportar-docx", json={"texto": "VOTO\n\nNego."})
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.headers["content-type"]
    assert client.post("/api/exportar-docx", json={"texto": "  "}).status_code == 400
