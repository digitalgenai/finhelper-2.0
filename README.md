# FinHelper 2.0 — Conciliacao Financeira com IA

**FinHelper** e uma aplicacao web que automatiza a **conciliacao financeira** entre arquivos de diferentes sistemas (fornecedores e o sistema interno Wintour), integrando um **assistente de IA** baseado na OpenAI para analise dos resultados.

Desenvolvido para a **Wee Travel**, o projeto elimina o trabalho manual de cruzar planilhas, identificar divergencias de valores e gerar relatorios consolidados.

---

## O que faz

- **Compara valores liquidos** por localizador entre dois arquivos financeiros (fornecedor vs. sistema Wintour).
- **Identifica automaticamente** registros:
  - **Ok** — valores batem entre os dois arquivos.
  - **Divergente** — valores diferentes entre os arquivos.
  - **Somente Fornecedor** / **Somente Wintour** — localizador presente em apenas um dos arquivos.
- **Comparacao campo a campo** — identifica exatamente ONDE esta a divergencia:
  - Tarifa com Tarifa
  - Taxa com Taxa
  - Markup com Markup
  - Taxa de embarque com Taxa de embarque
  - Over com Incentivo (campos correspondentes com nomes diferentes)
- **Detecta divergencias internas** no Wintour: verifica se `Total Fornec. (-DF) == Total Tarifa - Markup`.
- **Gera planilha Excel** consolidada com todos os resultados.
- **Chat com IA** para perguntar sobre os dados processados.

---

## Arquitetura

O projeto possui **dois modos de execucao**: interface web moderna (FastAPI + HTML/CSS/JS) e interface Gradio (legado).

```
finhelper-2.0/
|
|-- server.py              # Backend FastAPI (API REST)
|-- conciliador.py         # Motor de conciliacao financeira
|-- finhelper.py           # Integracao com OpenAI Assistants API
|-- app.py                 # Interface Gradio (modo legado)
|
|-- static/                # Frontend web
|   |-- index.html         # Pagina principal
|   |-- style.css          # Estilos (paleta Wee Travel)
|   |-- app.js             # Logica do frontend
|   |-- logo-wee.png       # Logo Wee Travel
|
|-- Dockerfile             # Container do backend (Python)
|-- Dockerfile.frontend    # Container do frontend (Nginx)
|-- docker-compose.yml     # Orquestracao dos containers
|-- nginx.conf             # Configuracao do Nginx (proxy reverso)
|
|-- requirements.txt       # Dependencias completas (inclui Gradio)
|-- requirements.docker.txt # Dependencias para Docker (sem Gradio)
|-- .env.example           # Modelo de variaveis de ambiente
|-- .dockerignore          # Arquivos ignorados pelo Docker
```

### Modulos

| Arquivo | Responsabilidade |
|---|---|
| `server.py` | API REST com FastAPI. Endpoints: processar arquivos, download Excel, chat IA. Serve os arquivos estaticos. |
| `conciliador.py` | Classe `Conciliador` — leitura de arquivos, agrupamento por localizador, comparacao de valores liquidos, comparacao campo a campo, deteccao de divergencias e geracao de planilha Excel. |
| `finhelper.py` | Classe `FinHelper` — integracao com a API de Assistentes da OpenAI. Cria threads de conversa com o contexto dos dados e responde perguntas. |
| `app.py` | Interface Gradio (modo legado). Pode ser usado independentemente do frontend web. |

### Endpoints da API

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/` | Serve a pagina HTML principal |
| `POST` | `/api/processar` | Recebe 2 arquivos, retorna resumo + resultados JSON |
| `GET` | `/api/download` | Download da planilha Excel gerada |
| `POST` | `/api/chat` | Envia mensagem para o assistente IA, retorna resposta |

### Formatos de arquivo suportados

| Extensao | Sistema | Separador | Encoding |
|---|---|---|---|
| `.xlsx` | Wintour / Fornecedor | — | — |
| `.csv` | Fornecedor | `;` | latin-1 |
| `.cnf` | Fornecedor | `;` | latin-1 |

---

## Regras de Negocio — Comparacao Campo a Campo

Quando o sistema encontra valores diferentes entre os dois arquivos para o mesmo localizador, ele compara campo a campo:

| Campo Fornecedor | Campo Wintour | Descricao |
|---|---|---|
| Tarifa | Total Tarifa | Valor da tarifa |
| Taxa | Total Taxas | Taxas do bilhete |
| TxDU | Total DU/RAV | Taxa de embarque |
| Incentivo | Over Agencia | Over / Incentivo (nomes diferentes) |

**Saida esperada:** Quando encontra divergencia, informa qual campo divergiu.
- Exemplo: `Diferenca em: Taxa (Fornec: 50.00 x Wintour: 35.00)`
- Exemplo: `Diferenca em: Tarifa (Fornec: 2000.00 x Wintour: 1800.00)`

**Regra de localizadores repetidos:** Um mesmo localizador pode ter varias pessoas (passageiros) ou servicos diferentes, gerando vendas distintas. O sistema **nunca esconde** localizadores repetidos — todos aparecem na planilha.

---

## Como a IA funciona

O FinHelper utiliza a **OpenAI Assistants API** (com threads persistentes):

1. **Criacao do contexto**: Quando o usuario processa os dois arquivos, o sistema serializa todo o resultado da conciliacao em texto estruturado.
2. **Injecao na thread**: Os dados sao enviados como mensagem inicial da thread com instrucoes detalhadas e regras de negocio.
3. **Chat interativo**: Cada pergunta do usuario e adicionada a mesma thread. O assistente responde com base nos dados reais da conciliacao.
4. **Tolerancia a falhas**: Se a API da OpenAI estiver fora do ar, o processamento funciona normalmente — apenas o chat fica indisponivel.

O assistente e configurado via um **Assistant ID** pre-criado na plataforma OpenAI (variavel `OPENAI_ASSISTANT_ID`).

---

## Configuracao e Instalacao

### Pre-requisitos

- **Python 3.10+**
- **Docker** e **Docker Compose** (para rodar com containers)
- Conta na **OpenAI** com acesso a Assistants API
- Um **Assistant** criado no painel da OpenAI

### Opcao 1: Rodar com Docker (Recomendado)

#### Passo 1 — Clone o repositorio

```bash
git clone <url-do-repositorio>
cd finhelper-2.0
```

#### Passo 2 — Configure as variaveis de ambiente

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env`:

```env
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_ASSISTANT_ID=asst_seu-id-aqui
```

> **Onde conseguir:**
> - `OPENAI_API_KEY`: Acesse [platform.openai.com/api-keys](https://platform.openai.com/api-keys) e crie uma nova chave.
> - `OPENAI_ASSISTANT_ID`: Acesse [platform.openai.com/assistants](https://platform.openai.com/assistants), crie um assistente e copie o ID (comeca com `asst_`).

#### Passo 3 — Suba os containers

```bash
docker compose up --build
```

Aguarde ate ver no terminal:
```
backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1 | ... ready for start up
```

#### Passo 4 — Acesse a aplicacao

Abra o navegador em: **http://localhost**

| Servico | URL | Porta |
|---|---|---|
| Frontend (Nginx) | http://localhost | 80 |
| Backend (FastAPI) | http://localhost:8000 | 8000 |

#### Comandos uteis do Docker

```bash
# Subir os containers em segundo plano
docker compose up -d --build

# Ver logs em tempo real
docker compose logs -f

# Parar os containers
docker compose down

# Rebuildar apos mudancas no codigo
docker compose up --build

# Ver status dos containers
docker compose ps
```

---

### Opcao 2: Rodar localmente (sem Docker)

#### Passo 1 — Clone o repositorio

```bash
git clone <url-do-repositorio>
cd finhelper-2.0
```

#### Passo 2 — Crie e ative um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

#### Passo 3 — Instale as dependencias

```bash
pip install -r requirements.txt
```

#### Passo 4 — Configure as variaveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais (mesmo procedimento da Opcao 1, Passo 2).

#### Passo 5 — Execute o servidor

**Frontend moderno (FastAPI):**
```bash
python server.py
```
Acesse: **http://localhost:8000**

**Interface Gradio (legado):**
```bash
python app.py
```
Acesse: **http://localhost:7860**

---

## Como usar

1. Acesse a aplicacao no navegador.
2. No campo **FLYTOUR**, faca upload do arquivo do fornecedor (`.csv`, `.xlsx` ou `.cnf`).
3. No campo **WINTOUR**, faca upload do arquivo do sistema Wintour (`.xlsx`).
4. Clique em **Processar**.
5. Veja o **Resumo** com os totais de cada status.
6. Use os **filtros** (Todos, Divergente, Somente Fornecedor, Somente Wintour, Ok) para navegar pelos resultados.
7. Clique em **Baixar Excel** para download da planilha consolidada.
8. Use o **Chat IA** (botao no canto superior direito) para tirar duvidas sobre os dados.

### Exemplos de perguntas para o Chat IA

- "Quais localizadores estao divergentes?"
- "Qual a diferenca no localizador C9WAQD?"
- "Quantos registros estao somente no fornecedor?"
- "Onde esta a divergencia do passageiro Carlos Abreu?"

---

## Funcionalidades do Frontend

| Funcionalidade | Descricao |
|---|---|
| Upload com drag & drop | Arraste os arquivos para as areas de upload |
| Botao X no upload | Remove o arquivo individualmente para trocar |
| Cabecalho fixo da tabela | O header roxo fica fixo ao rolar a tabela |
| Tooltip nas celulas | Passe o mouse sobre celulas truncadas para ver o texto completo |
| Celulas coloridas | Valores divergentes sao destacados com cores (vermelho = maior, amarelo = menor, ciano = presente, rosa = ausente) |
| Badges de status | Ok (verde), Divergente (vermelho), Somente Fornecedor (ciano), Somente Wintour (amarelo) |
| Chat lateral retratil | Abre/fecha pelo botao "Chat IA" no header, empurra o conteudo sem sobrepor |
| Logo como botao Home | Clique na logo para voltar ao topo da pagina |
| Divergentes primeiro | A tabela sempre ordena divergentes no topo |

---

## Paleta de Cores (Identidade Visual Wee Travel)

| Cor | Hex | Uso |
|---|---|---|
| Roxo | `#7F2EC2` | Header, botoes primarios, badges |
| Ciano | `#00EAE1` | Upload boxes, destaques, badges |
| Cinza | `#BDBFBF` | Textos secundarios, bordas |
| Verde | `#22C55E` | Status Ok |
| Vermelho | `#EF4444` | Status Divergente |
| Amarelo | `#EAB308` | Status Somente Wintour |

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| [Python 3.12](https://python.org) | Linguagem principal |
| [FastAPI](https://fastapi.tiangolo.com) | Backend / API REST |
| [Uvicorn](https://www.uvicorn.org) | Servidor ASGI |
| [Pandas](https://pandas.pydata.org) | Manipulacao de dados |
| [OpenPyXL](https://openpyxl.readthedocs.io) | Leitura/escrita de Excel |
| [OpenAI Assistants API](https://platform.openai.com/docs/assistants) | IA conversacional |
| [Nginx](https://nginx.org) | Servidor web / proxy reverso (Docker) |
| [Docker](https://docker.com) | Containerizacao |
| HTML/CSS/JS | Frontend moderno |
| [Gradio](https://gradio.app) | Interface legado |

---

## Troubleshooting

| Problema | Solucao |
|---|---|
| Erro 500 ao processar | Verifique os logs do backend (`docker compose logs backend`). Pode ser formato de arquivo nao suportado. |
| Chat nao responde | Verifique se `OPENAI_API_KEY` e `OPENAI_ASSISTANT_ID` estao corretos no `.env`. A API da OpenAI pode estar fora do ar. |
| Porta 8000 ocupada | Mate o processo: `taskkill /F /IM python.exe` (Windows) ou `kill $(lsof -ti:8000)` (Linux/Mac). |
| Porta 80 ocupada (Docker) | Altere a porta no `docker-compose.yml`: `"3000:80"` e acesse `http://localhost:3000`. |
| Docker build falha no pip | Use `requirements.docker.txt` (sem Gradio). Verifique o `Dockerfile`. |
| Tabela com scroll horizontal | Isso nao deveria acontecer. Limpe o cache do navegador (Ctrl+Shift+R). |
| Arquivo .cnf nao carrega | Verifique se o separador e `;` e o encoding e `latin-1`. |

---

## Licenca

Projeto interno da **Wee Travel**. Uso restrito.
