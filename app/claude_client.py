"""Integração com a API da Claude (Anthropic) para gerar as minutas."""

from collections.abc import Iterator

import anthropic

from app.config import settings
from app.prompts import SYSTEM_PROMPT, montar_prompt_usuario
from app.schemas import MinutaRequest

# Cliente único; resolve a credencial a partir de ANTHROPIC_API_KEY no ambiente.
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)


def gerar_minuta_stream(req: MinutaRequest) -> Iterator[str]:
    """Gera a minuta de voto em streaming, devolvendo blocos de texto.

    Usa o modelo configurado com raciocínio adaptativo e streaming, conforme
    recomendado para saídas longas (evita timeouts de requisição).
    """
    prompt_usuario = montar_prompt_usuario(req)

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
