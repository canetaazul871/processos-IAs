# Assistente de Desembargador

Web app que auxilia o gabinete de um(a) Desembargador(a) na elaboração de
**minutas de voto e ementa** para julgamento de recursos em segunda instância,
usando a API da Claude (Anthropic).

> ⚖️ As minutas são geradas por IA e servem como **rascunho de apoio**. Devem
> ser conferidas, ajustadas e validadas pelo gabinete antes de qualquer uso
> oficial. O assistente não decide o caso — organiza e redige a fundamentação.

## Funcionalidades

- Formulário com os dados do caso (relatório, decisão recorrida, razões do
  recurso, contrarrazões, orientação do gabinete, questões jurídicas).
- Quatro entregáveis selecionáveis, gerados em **streaming** (o texto aparece
  conforme é redigido):
  - **Análise FIRAC** do processo — Fatos, Questões (_Issues_), Regra (_Rule_),
    Aplicação (_Analysis_) e Conclusão.
  - **Relatório** do acórdão.
  - **Voto** (fundamentação: admissibilidade e mérito; dispositivo).
  - **Ementa** no padrão dos tribunais.
- **Pesquisa de jurisprudência** integrada:
  - **Busca em fontes oficiais** — a Claude pesquisa julgados reais e citáveis,
    restrita a domínios `.jus.br` (STF, STJ, TJPA, demais TJs/TRFs),
    `planalto.gov.br` (legislação) e `jusbrasil.com.br` (complementar). Pode ser
    incorporada automaticamente à fundamentação do voto.
  - **DataJud (CNJ)** — consulta processual oficial por número CNJ via API
    Pública (não cobre o STF).
- Marcadores entre colchetes para lacunas que dependem dos autos ou de
  precedentes a serem conferidos (o modelo é instruído a **não inventar**
  citações, súmulas ou números de processos).

## Stack

- **Backend:** FastAPI + Uvicorn
- **IA:** API da Claude (`claude-opus-4-8`) com raciocínio adaptativo e streaming
- **Frontend:** página HTML estática (sem build)

## Como rodar

1. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure a chave de API:

   ```bash
   cp .env.example .env
   # edite .env e preencha ANTHROPIC_API_KEY
   ```

4. Inicie a aplicação:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Acesse <http://localhost:8000>.

## Configuração (.env)

| Variável             | Padrão            | Descrição                                      |
| -------------------- | ----------------- | ---------------------------------------------- |
| `ANTHROPIC_API_KEY`  | —                 | Chave da API da Anthropic (obrigatória).       |
| `ANTHROPIC_MODEL`    | `claude-opus-4-8` | Modelo da Claude.                              |
| `MODEL_EFFORT`       | `high`            | Esforço de raciocínio: low/medium/high/xhigh/max. |
| `MAX_OUTPUT_TOKENS`  | `32000`           | Limite de tokens da minuta gerada.             |

## Endpoints

- `GET /` — interface web.
- `GET /api/health` — status e se a chave está configurada.
- `POST /api/minutar` — gera a minuta (resposta em streaming `text/plain`).
- `POST /api/jurisprudencia` — pesquisa julgados em fontes oficiais (streaming).
- `POST /api/datajud` — consulta processual à API Pública do DataJud (CNJ).
- `GET /docs` — documentação interativa (Swagger).

> **Rede:** a busca em fontes oficiais usa a ferramenta de busca server-side da
> Anthropic. Já a consulta ao **DataJud** faz requisição direta a
> `api-publica.datajud.cnj.jus.br` — garanta que a saída para esse host esteja
> liberada no ambiente onde a aplicação roda.

## Estrutura

```
app/
├── main.py            # rotas FastAPI
├── config.py          # configurações (.env)
├── claude_client.py   # integração com a API da Claude (geração das minutas)
├── jurisprudencia.py  # busca em fontes oficiais + consulta ao DataJud (CNJ)
├── prompts.py         # prompt de sistema + montagem do prompt do caso
├── schemas.py         # modelos de entrada
└── static/index.html  # interface web
```

## Próximos passos possíveis

- Resumo automático de peças (upload de PDF dos autos).
- Triagem/classificação de processos por matéria e urgência.
- Exportação da minuta em `.docx`.
