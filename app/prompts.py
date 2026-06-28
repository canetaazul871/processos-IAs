"""Prompts de sistema e montagem do prompt do usuário para minutar votos."""

from app.schemas import MinutaRequest

# Descrição de cada entregável, usada para montar a instrução dinâmica.
SECOES = {
    "firac": (
        "ANÁLISE FIRAC",
        """\
Produza uma análise estruturada do caso pelo método FIRAC, com subtítulos:
- **F — Fatos**: fatos juridicamente relevantes, em ordem cronológica, sem \
juízo de valor.
- **I — Questões (Issues)**: as questões jurídicas controvertidas a decidir, \
formuladas como perguntas objetivas.
- **R — Regra (Rule)**: normas, princípios e, quando cabível, precedentes \
aplicáveis a cada questão (sem inventar números/súmulas — ver regras abaixo).
- **A — Aplicação (Analysis)**: subsunção dos fatos à regra, confrontando as \
teses das partes e a prova; é a parte mais densa da análise.
- **C — Conclusão**: resposta a cada questão e o resultado a que conduzem.
Esta análise é instrumento de trabalho do gabinete e antecede o voto.""",
    ),
    "relatorio": (
        "RELATÓRIO",
        """\
Redija o relatório do acórdão: identificação do recurso e das partes, síntese \
da pretensão inicial, do teor da decisão recorrida, das razões do recurso e das \
contrarrazões, e do que mais for relevante para o julgamento. Texto descritivo, \
sem antecipar o mérito.""",
    ),
    "voto": (
        "VOTO",
        """\
Redija o voto com FUNDAMENTAÇÃO (admissibilidade do recurso — cabimento, \
tempestividade, preparo, legitimidade, interesse, quando houver elementos; e \
mérito, com análise das teses e das provas) e DISPOSITIVO (conhecer/não \
conhecer; dar/negar provimento, total ou parcial). Enfrente os fundamentos \
relevantes das partes, sem deixar questão essencial sem análise (art. 489, §1º, \
CPC).""",
    ),
    "ementa": (
        "EMENTA",
        """\
Redija a ementa no padrão dos tribunais brasileiros: cabeçalho com ramo do \
direito e tese, itens numerados com a fundamentação essencial e item final com \
o resultado do julgamento.""",
    ),
}

SYSTEM_PROMPT = """\
Você é um assistente jurídico especializado que auxilia um(a) Desembargador(a) \
de Tribunal de Justiça brasileiro na análise de processos e na elaboração de \
MINUTAS (análise FIRAC, relatório, voto e ementa) para julgamento de recursos \
em segunda instância.

Seu papel é produzir um trabalho técnico, fundamentado e bem estruturado, a \
partir das informações fornecidas pelo gabinete. Você NÃO decide o caso: você \
organiza e redige a fundamentação na linha indicada pelo gabinete (ou, quando \
não houver posição definida, apresenta a análise das teses de forma equilibrada \
e indica a solução juridicamente mais consistente, deixando claro tratar-se de \
sugestão).

Diretrizes gerais de redação:
- Use linguagem jurídica formal, técnica e impessoal, em português do Brasil.
- Produza APENAS as seções solicitadas, na ordem indicada, cada uma com um \
título em caixa-alta separando-a das demais.
- Mantenha coerência entre as seções (a conclusão do FIRAC, o dispositivo do \
voto e o resultado da ementa devem ser compatíveis).

Regras importantes sobre citações e fontes:
- Você pode mencionar dispositivos legais e princípios jurídicos consolidados.
- NÃO invente números de precedentes, súmulas, datas de julgamento ou citações \
literais. Se não tiver certeza de uma referência específica, indique o ponto em \
que um precedente seria cabível usando um marcador como \
"[inserir precedente: tema/assunto]" para que o gabinete complete.
- Sinalize claramente qualquer lacuna de informação que dependa dos autos com \
marcadores entre colchetes, p. ex. "[confirmar nos autos: ...]".

Encerre SEMPRE a saída com o aviso:
"— Minuta gerada por IA para revisão. Deve ser conferida, ajustada e validada \
pelo(a) Desembargador(a) antes de qualquer uso oficial."
"""


def _campo(rotulo: str, valor: str | None) -> str:
    """Formata um campo opcional; retorna string vazia se ausente."""
    valor = (valor or "").strip()
    if not valor:
        return ""
    return f"## {rotulo}\n{valor}\n\n"


def montar_prompt_usuario(req: MinutaRequest) -> str:
    """Monta o conteúdo da mensagem do usuário a partir do formulário."""
    selecionados = req.entregaveis_selecionados()
    titulos = ", ".join(SECOES[s][0] for s in selecionados)

    instrucoes = "\n".join(
        f"{i}. {SECOES[s][0]}\n{SECOES[s][1]}"
        for i, s in enumerate(selecionados, start=1)
    )

    partes: list[str] = [
        "Para o caso descrito abaixo, produza as seguintes seções, nesta "
        f"ordem: {titulos}.\n\n"
        "Instruções de cada seção:\n"
        f"{instrucoes}\n\n"
        "=== DADOS DO CASO ===\n\n",
    ]

    partes.append(_campo("Tipo de recurso / classe processual", req.tipo_recurso))
    partes.append(_campo("Número do processo", req.numero_processo))
    partes.append(_campo("Partes (recorrente / recorrido)", req.partes))
    partes.append(_campo("Relatório / resumo dos fatos e do processo", req.relatorio))
    partes.append(_campo("Decisão recorrida (sentença/acórdão de origem)", req.decisao_recorrida))
    partes.append(_campo("Razões do recurso (pedidos e fundamentos do recorrente)", req.razoes_recurso))
    partes.append(_campo("Contrarrazões", req.contrarrazoes))
    partes.append(_campo("Posição/orientação do gabinete sobre o resultado", req.posicao_gabinete))
    partes.append(_campo("Questões jurídicas a enfrentar", req.questoes_juridicas))
    partes.append(_campo("Observações adicionais", req.observacoes))

    return "".join(p for p in partes if p)
