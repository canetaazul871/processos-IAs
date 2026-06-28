"""Integração com a API da Claude (Anthropic) para gerar as minutas."""

from collections.abc import Iterator

import anthropic

from app.config import settings
from app.jurisprudencia import pesquisar_julgados
from app.prompts import SYSTEM_PROMPT, montar_prompt_usuario
from app.schemas import MinutaRequest

# Cliente único; resolve a credencial a partir de ANTHROPIC_API_KEY no ambiente.
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)


def _bloco_jurisprudencia(req: MinutaRequest) -> tuple[str, str]:
    """Pesquisa julgados oficiais para o caso.

    Retorna (texto_para_exibir, bloco_para_o_prompt). Em caso de falha ou
    consulta vazia, retorna strings vazias para não interromper a geração.
    """
    consulta = req.consulta_jurisprudencia()
    if not consulta:
        return "", ""
    try:
        resultado = pesquisar_julgados(consulta, req.tipo_recurso or None).strip()
    except Exception as exc:  # busca é best-effort; não pode derrubar a minuta
        return f"\n[Aviso: falha na pesquisa de jurisprudência: {exc}]\n", ""
    if not resultado:
        return "", ""
    exibir = (
        "## JURISPRUDÊNCIA PESQUISADA (fontes oficiais)\n\n"
        f"{resultado}\n\n"
        "---\n\n"
    )
    bloco_prompt = (
        "\n\n=== JURISPRUDÊNCIA PESQUISADA EM FONTES OFICIAIS ===\n"
        "Use APENAS os julgados abaixo como precedentes citáveis. Cite-os pelo "
        "tribunal, número e link indicados; não acrescente outros precedentes "
        "que não constem desta lista.\n\n"
        f"{resultado}\n"
    )
    return exibir, bloco_prompt


def gerar_minuta_stream(req: MinutaRequest) -> Iterator[str]:
    """Gera a minuta de voto em streaming, devolvendo blocos de texto.

    Usa o modelo configurado com raciocínio adaptativo e streaming, conforme
    recomendado para saídas longas (evita timeouts de requisição).
    """
    prompt_usuario = montar_prompt_usuario(req)

    if req.pesquisar_jurisprudencia:
        yield "🔎 Pesquisando jurisprudência em fontes oficiais…\n\n"
        exibir, bloco_prompt = _bloco_jurisprudencia(req)
        if exibir:
            yield exibir
        prompt_usuario += bloco_prompt

    with _client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=settings.max_output_tokens,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                # Prompt de sistema é estável → faz cache para reduzir custo/latência.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        thinking={"type": "adaptive"},
        output_config={"effort": settings.model_effort},
        messages=[{"role": "user", "content": prompt_usuario}],
    ) as stream:
        for texto in stream.text_stream:
            yield texto
