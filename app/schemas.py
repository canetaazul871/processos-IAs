"""Modelos de entrada/saída da API."""

from pydantic import BaseModel, Field

# Entregáveis que o assistente pode produzir.
ENTREGAVEIS_VALIDOS = ("firac", "relatorio", "voto", "ementa")
ENTREGAVEIS_PADRAO = list(ENTREGAVEIS_VALIDOS)


class MinutaRequest(BaseModel):
    """Dados do caso para geração da minuta de voto."""

    entregaveis: list[str] = Field(
        default_factory=lambda: list(ENTREGAVEIS_PADRAO),
        description="Seções a produzir: firac, relatorio, voto, ementa.",
    )
    tipo_recurso: str = Field(
        default="",
        description="Tipo de recurso ou classe processual (ex.: Apelação Cível).",
    )
    numero_processo: str = Field(default="", description="Número do processo (CNJ).")
    partes: str = Field(default="", description="Recorrente e recorrido.")
    relatorio: str = Field(
        default="",
        description="Relatório / resumo dos fatos e do andamento processual.",
    )
    decisao_recorrida: str = Field(
        default="", description="Teor da sentença ou decisão de origem."
    )
    razoes_recurso: str = Field(
        default="", description="Pedidos e fundamentos do recorrente."
    )
    contrarrazoes: str = Field(default="", description="Contrarrazões, se houver.")
    posicao_gabinete: str = Field(
        default="",
        description="Orientação do gabinete quanto ao resultado pretendido.",
    )
    questoes_juridicas: str = Field(
        default="", description="Questões jurídicas a enfrentar."
    )
    observacoes: str = Field(default="", description="Observações adicionais.")

    def tem_conteudo_minimo(self) -> bool:
        """Verifica se há informação suficiente para gerar a minuta."""
        return bool(
            (self.relatorio or "").strip()
            or (self.razoes_recurso or "").strip()
            or (self.decisao_recorrida or "").strip()
        )

    def entregaveis_selecionados(self) -> list[str]:
        """Entregáveis válidos solicitados, preservando a ordem canônica."""
        pedidos = {e.strip().lower() for e in self.entregaveis}
        selecionados = [e for e in ENTREGAVEIS_VALIDOS if e in pedidos]
        return selecionados or list(ENTREGAVEIS_PADRAO)
