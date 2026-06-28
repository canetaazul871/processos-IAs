"""Triagem e classificação de processos para o gabinete."""

from app.claude_client import gerar_json

SYSTEM_TRIAGEM = """\
Você apoia a triagem de processos no gabinete de um(a) Desembargador(a). A partir \
da descrição/relatório do processo, classifique-o de forma objetiva para apoiar a \
organização do acervo. Baseie-se apenas nas informações fornecidas; quando algo \
não puder ser determinado, seja conservador e registre como pendência.

- materia: área do direito predominante (ex.: Direito Civil, Penal, Tributário).
- assunto: assunto principal, no padrão das tabelas do CNJ quando possível.
- competencia: órgão/câmara/seção sugerida para o julgamento, se inferível.
- urgencia: 'alta', 'média' ou 'baixa'.
- urgencia_justificativa: breve justificativa da urgência atribuída.
- prioridade_legal: hipóteses de tramitação prioritária identificadas (ex.: \
idoso, pessoa com deficiência, réu preso, ECA), com a base legal quando souber.
- pendencias: pontos a verificar/conferir nos autos antes do julgamento.
- resumo: uma a duas frases sintetizando o processo.
"""

SCHEMA_TRIAGEM = {
    "type": "object",
    "properties": {
        "materia": {"type": "string"},
        "assunto": {"type": "string"},
        "competencia": {"type": "string"},
        "urgencia": {"type": "string", "enum": ["alta", "média", "baixa"]},
        "urgencia_justificativa": {"type": "string"},
        "prioridade_legal": {"type": "array", "items": {"type": "string"}},
        "pendencias": {"type": "array", "items": {"type": "string"}},
        "resumo": {"type": "string"},
    },
    "required": [
        "materia",
        "assunto",
        "competencia",
        "urgencia",
        "urgencia_justificativa",
        "prioridade_legal",
        "pendencias",
        "resumo",
    ],
    "additionalProperties": False,
}


def classificar_processo(texto: str) -> dict:
    """Classifica um processo a partir de sua descrição/relatório."""
    conteudo = (texto or "").strip()
    if not conteudo:
        return {"erro": "Informe a descrição ou o relatório do processo."}
    return gerar_json(SYSTEM_TRIAGEM, conteudo, SCHEMA_TRIAGEM, max_tokens=4000)
