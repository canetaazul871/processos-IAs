"""Pesquisa de jurisprudência: busca em fontes oficiais (A) e DataJud/CNJ (B).

- A) Busca web com a Claude, restrita a domínios oficiais (.jus.br, planalto),
  retornando julgados reais e citáveis.
- B) Consulta à API Pública do DataJud (CNJ) por número de processo.
"""

import re
from collections.abc import Iterator

import anthropic
import httpx

from app.config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)

# Domínios permitidos na busca web. "jus.br" cobre todos os tribunais brasileiros
# (stf.jus.br, stj.jus.br, scon.stj.jus.br, tjpa.jus.br, tj*.jus.br, trf*.jus.br…);
# "planalto.gov.br" cobre a legislação oficial; "jusbrasil.com.br" é fonte
# complementar (apenas leitura de páginas públicas pela busca, sem credenciais).
DOMINIOS_PERMITIDOS = ["jus.br", "planalto.gov.br", "jusbrasil.com.br"]

SYSTEM_BUSCA = """\
Você é um pesquisador de jurisprudência que apoia o gabinete de um(a) \
Desembargador(a). Use a ferramenta de busca para localizar julgados REAIS em \
fontes oficiais (tribunais brasileiros e legislação).

Para cada julgado relevante encontrado, apresente em tópicos:
- Tribunal e órgão julgador (câmara/turma)
- Classe e número do processo
- Relator(a)
- Data de julgamento
- Tese / ementa resumida (2 a 4 linhas)
- LINK da fonte oficial

Ao final, sintetize: a TESE PREDOMINANTE sobre a questão e eventuais DIVERGÊNCIAS \
(quando houver), indicando o tribunal de cada corrente.

Regras:
- NÃO invente julgados, números, datas, relatores ou ementas. Use somente o que \
encontrar nas fontes.
- Se não localizar julgados pertinentes, diga isso de forma explícita, em vez de \
preencher com suposições.
- Priorize STF, STJ e o tribunal indicado pelo gabinete (por exemplo, o TJPA \
quando pertinente). O Jusbrasil pode ser usado como fonte complementar; sempre \
que possível, confirme o julgado na fonte oficial (.jus.br) e prefira o link \
oficial.
"""

# Aliases válidos da API Pública do DataJud (subconjunto comum). O STF não
# integra o DataJud. Fonte: documentação pública do CNJ (api_publica_<alias>).
DATAJUD_ALIASES = {
    "stj", "tst", "tse", "stm",
    "trf1", "trf2", "trf3", "trf4", "trf5", "trf6",
    "tjac", "tjal", "tjam", "tjap", "tjba", "tjce", "tjdft", "tjes", "tjgo",
    "tjma", "tjmg", "tjms", "tjmt", "tjpa", "tjpb", "tjpe", "tjpi", "tjpr",
    "tjrj", "tjrn", "tjro", "tjrr", "tjrs", "tjsc", "tjse", "tjsp", "tjto",
    "trt1", "trt2", "trt3", "trt4", "trt5", "trt15",
}

DATAJUD_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search"


def _tools(tribunal_preferencial: str | None) -> list[dict]:
    return [
        {
            "type": "web_search_20260209",
            "name": "web_search",
            "allowed_domains": DOMINIOS_PERMITIDOS,
            "max_uses": 6,
        }
    ]


def pesquisar_julgados_stream(
    consulta: str, tribunal_preferencial: str | None = None
) -> Iterator[str]:
    """Pesquisa julgados em fontes oficiais e devolve o texto em streaming."""
    pedido = consulta.strip()
    if tribunal_preferencial:
        pedido += f"\n\nTribunal preferencial: {tribunal_preferencial}."

    with _client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=settings.max_output_tokens,
        system=[{"type": "text", "text": SYSTEM_BUSCA}],
        tools=_tools(tribunal_preferencial),
        messages=[{"role": "user", "content": pedido}],
    ) as stream:
        for texto in stream.text_stream:
            yield texto


def pesquisar_julgados(
    consulta: str, tribunal_preferencial: str | None = None
) -> str:
    """Versão não-streaming: coleta o resultado da pesquisa em uma string."""
    return "".join(pesquisar_julgados_stream(consulta, tribunal_preferencial))


def consultar_datajud(numero_processo: str, alias: str) -> dict:
    """Consulta a API Pública do DataJud (CNJ) por número de processo.

    Retorna um dicionário com os processos encontrados (dados resumidos) ou um
    campo 'erro' descritivo. Não levanta exceção para o chamador.
    """
    alias = (alias or "").strip().lower()
    if alias not in DATAJUD_ALIASES:
        return {"erro": f"Tribunal '{alias}' não suportado no DataJud."}

    numero = re.sub(r"\D", "", numero_processo or "")
    if len(numero) != 20:
        return {
            "erro": "Número de processo inválido: informe os 20 dígitos do "
            "padrão CNJ (a máscara é opcional)."
        }

    url = DATAJUD_URL.format(alias=alias)
    body = {"size": 5, "query": {"match": {"numeroProcesso": numero}}}
    headers = {
        "Authorization": f"APIKey {settings.datajud_api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=30.0)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {"erro": f"DataJud respondeu {exc.response.status_code}."}
    except httpx.HTTPError as exc:
        return {"erro": f"Falha ao consultar o DataJud: {exc}."}

    hits = resp.json().get("hits", {}).get("hits", [])
    if not hits:
        return {
            "alias": alias,
            "numero": numero,
            "total": 0,
            "processos": [],
            "aviso": "Nenhum processo encontrado para esse número neste tribunal.",
        }

    processos = [_resumir_processo(h.get("_source", {})) for h in hits]
    return {"alias": alias, "numero": numero, "total": len(processos), "processos": processos}


def _resumir_processo(src: dict) -> dict:
    """Extrai os campos mais úteis de um documento do DataJud."""
    assuntos = [a.get("nome") for a in src.get("assuntos", []) if a.get("nome")]
    movimentos = sorted(
        src.get("movimentos", []),
        key=lambda m: m.get("dataHora", ""),
    )
    ultimos = [
        {"data": m.get("dataHora"), "nome": m.get("nome")}
        for m in movimentos[-8:]
    ]
    return {
        "numeroProcesso": src.get("numeroProcesso"),
        "tribunal": src.get("tribunal"),
        "grau": src.get("grau"),
        "classe": (src.get("classe") or {}).get("nome"),
        "orgaoJulgador": (src.get("orgaoJulgador") or {}).get("nome"),
        "assuntos": assuntos,
        "dataAjuizamento": src.get("dataAjuizamento"),
        "ultimosMovimentos": ultimos,
    }
