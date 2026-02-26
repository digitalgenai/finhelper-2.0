# FinHelper — Conciliação Financeira com IA

**FinHelper** é uma aplicação web que automatiza a **conciliação financeira** entre arquivos de diferentes sistemas (fornecedores e o sistema interno Wintour), integrando um **assistente de IA** baseado na OpenAI para análise e tirar dúvidas sobre os resultados.

Desenvolvido para a **Wee Travel**, o projeto elimina o trabalho manual de cruzar planilhas, identificar divergências de valores e gerar relatórios consolidados.

---

## O que faz

- **Compara valores líquidos** por localizador entre dois arquivos financeiros (fornecedor vs. sistema Wintour).
- **Identifica automaticamente** registros:
  - **Ok** — valores batem entre os dois arquivos.
  - **Divergente** — valores diferentes entre os arquivos.
  - **Somente Fornecedor** / **Somente Wintour** — localizador presente em apenas um dos arquivos.
- **Detecta divergências internas** no Wintour: verifica se `Total Fornec. (-DF) == Total Tarifa - Markup`.
- **Gera uma planilha Excel** consolidada com todos os resultados.
- **Chat com IA** para perguntar sobre os dados processados (ex: "Quais localizadores estão divergentes?", "Qual a diferença no localizador XYZ?").

---

## Arquitetura

O projeto é composto por **3 módulos principais**:

```
┌──────────────────────────────────────────────────────────┐
│                     app.py (Interface)                   │
│              Gradio Web UI — Upload + Chat               │
├──────────────┬───────────────────────────┬───────────────┤
│              │                           │               │
│   conciliador.py                  finhelper.py           │
│   (Motor de Conciliação)          (Assistente IA)        │
│                                                          │
│   • Leitura de .xlsx/.csv/.cnf    • OpenAI Assistants API│
│   • Agrupamento por localizador   • Threads de conversa  │
│   • Comparação de valores         • Contexto financeiro  │
│   • Geração de Excel              • Chat interativo      │
└──────────────────────────────────────────────────────────┘
```

### Módulos

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Interface web com Gradio. Orquestra o fluxo de upload → conciliação → chat. |
| `conciliador.py` | Classe `Conciliador` — leitura de arquivos, agrupamento por localizador, comparação de valores líquidos, detecção de divergências e geração de planilha Excel. |
| `finhelper.py` | Classe `FinHelper` — integração com a API de Assistentes da OpenAI. Cria threads de conversa com o contexto dos dados e responde perguntas. |

### Formatos suportados

| Extensão | Sistema | Separador | Encoding |
|---|---|---|---|
| `.xlsx` | Wintour | — | — |
| `.csv` | Fornecedor | `;` | latin-1 |
| `.cnf` | Fornecedor | `\t` (tab) | latin-1 |

---

## Como a IA funciona

O FinHelper utiliza a **OpenAI Assistants API** (com threads persistentes) para criar um assistente financeiro contextual:

1. **Criação do contexto**: Quando o usuário processa os dois arquivos, o sistema serializa todo o resultado da conciliação (localizadores, valores, status, divergências) em texto estruturado.

2. **Injeção na thread**: Os dados são enviados como mensagem inicial da thread com instruções detalhadas, incluindo regras de negócio (ex: `Total Fornec. (-DF)` deve ser igual a `Total Tarifa - Markup`).

3. **Chat interativo**: Cada pergunta do usuário é adicionada à mesma thread. O assistente responde com base nos dados reais da conciliação, citando valores exatos.

4. **Polling assíncrono**: Após enviar uma mensagem, o sistema faz polling do status do `run` até que a resposta fique pronta.

O assistente é configurado via um **Assistant ID** pré-criado na plataforma OpenAI (variável `OPENAI_ASSISTANT_ID`), o que permite personalizar instruções, modelo e comportamento diretamente no painel da OpenAI.

---

## Para que serve

O FinHelper resolve um problema recorrente em agências de viagem: a **conciliação financeira entre fornecedores (companhias aéreas, hotéis, etc.) e o sistema interno de gestão (Wintour)**.

Sem a ferramenta, o processo envolve:
- Abrir planilhas manualmente
- Cruzar localizadores um a um
- Calcular diferenças de valor
- Identificar registros ausentes

Com o FinHelper, tudo isso é feito em **segundos**, com um relatório detalhado e um assistente de IA para tirar dúvidas.

---

## Como rodar o projeto

### Pré-requisitos

- **Python 3.10+**
- Conta na **OpenAI** com acesso à Assistants API
- Um **Assistant** criado no painel da OpenAI (com as instruções desejadas)

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd finhelper-api
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto baseado no exemplo:

```bash
cp env.example .env
```

Edite o `.env` com suas credenciais:

```env
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_ASSISTANT_ID=asst_seu-id-aqui
```

> **Nota:** O `OPENAI_ASSISTANT_ID` é o ID do assistente criado na [plataforma da OpenAI](https://platform.openai.com/assistants).

### 5. Execute a aplicação

```bash
python app.py
```

A interface estará disponível em: **http://127.0.0.1:7860**

### 6. Uso

1. Faça upload de dois arquivos financeiros (um do fornecedor e um do Wintour).
2. Clique em **Enviar** para processar a conciliação.
3. Veja o resumo, a tabela de resultados e baixe a planilha Excel.
4. Use o **chat** para tirar dúvidas com a IA sobre os dados processados.

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| [Python](https://python.org) | Linguagem principal |
| [Gradio](https://gradio.app) | Interface web |
| [OpenAI Assistants API](https://platform.openai.com/docs/assistants) | IA conversacional |
| [Pandas](https://pandas.pydata.org) | Manipulação de dados |
| [OpenPyXL](https://openpyxl.readthedocs.io) | Leitura/escrita de Excel |
