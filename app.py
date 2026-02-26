import gradio as gr

from conciliador import Conciliador
from finhelper import FinHelper

conciliador = Conciliador()
finhelper = FinHelper()


def serializar_resultado(resultado, lbl1, lbl2):
    """Converte a lista de resultados da conciliação em texto legível para o assistente."""
    linhas = []
    for r in resultado:
        liq1 = r.get(f"liq_{lbl1}", "")
        liq2 = r.get(f"liq_{lbl2}", "")
        if isinstance(liq1, (int, float)):
            liq1 = f"{liq1:.2f}"
        if isinstance(liq2, (int, float)):
            liq2 = f"{liq2:.2f}"
        dif = r.get("dif", "")
        if isinstance(dif, (int, float)):
            dif = f"{dif:.2f}"
        esp = r.get("esperado_fornecedor", "")
        if isinstance(esp, (int, float)):
            esp = f"{esp:.2f}"

        div_int = r.get("divergencia_interna", False)
        dif_int = r.get("dif_interna", "")
        if isinstance(dif_int, (int, float)):
            dif_int = f"{dif_int:.2f}"

        linha = (
            f"LOC: {r['loc']} | PAX: {r['pax']} | Status: {r['status']}"
            f" | Liq. {lbl1}: {liq1} | Liq. {lbl2}: {liq2}"
            f" | Diferença: {dif} | Esperado Fornecedor: {esp}"
            f" | Diverg. Interna (Fornec≠Tarifa-Markup): {'SIM' if div_int else 'Não'}"
            f" | Dif. Interna: {dif_int}"
            f" | Nº Venda: {r.get('venda', '')} | Cliente: {r.get('cliente', '')}"
            f" | Emissor: {r.get('emissor', '')} | Markup: {r.get('markup', '')}"
            f" | Tarifa Total: {r.get('tarifa', '')}"
        )
        linhas.append(linha)
    return "\n".join(linhas)


## ── Gradio ──

def processar(arquivo1, arquivo2):
    if not arquivo1 or not arquivo2:
        return "Envie os dois arquivos.", "", None, None, []

    try:
        resumo, resultado, lbl1, lbl2, xlsx_path = conciliador.processar_arquivos(arquivo1, arquivo2)
    except Exception as e:
        return f"Erro na leitura: {e}", "", None, None, []

    texto_resumo = (
        f"**{resumo['lbl1']}** x **{resumo['lbl2']}**\n\n"
        f"- Localizadores {resumo['lbl1']}: {resumo['locs_1']}\n"
        f"- Localizadores {resumo['lbl2']}: {resumo['locs_2']}\n"
        f"- Ok: {resumo['ok']}\n"
        f"- Divergentes: {resumo['divergentes']}\n"
        f"- Somente Fornecedor: {resumo['somente_fornecedor']}\n"
        f"- Somente Wintour: {resumo['somente_wintour']}\n"
    )

    linhas = []
    for r in resultado:
        liq1 = f"{r[f'liq_{lbl1}']:.2f}" if isinstance(r.get(f"liq_{lbl1}"), (int, float)) else ""
        liq2 = f"{r[f'liq_{lbl2}']:.2f}" if isinstance(r.get(f"liq_{lbl2}"), (int, float)) else ""
        dif = f"{r['dif']:.2f}" if isinstance(r.get("dif"), (int, float)) else ""
        esp = f"{r['esperado_fornecedor']:.2f}" if isinstance(r.get("esperado_fornecedor"), (int, float)) else ""
        linhas.append(
            f"| {r['loc']} | {r['pax']} | {r['status']} "
            f"| {liq1} | {liq2} | {dif} | {esp} "
            f"| {r['venda']} | {r['cliente']} | {r['emissor']} "
            f"| {r['markup']} | {r['tarifa']} |"
        )

    header = (f"| Localizador | Passageiro | Status "
              f"| Liq. {lbl1} | Liq. {lbl2} | Diferenca | Esperado Fornec. "
              f"| Nº Venda | Cliente | Emissor | Markup | Tarifa Total |\n")
    header += "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    tabela = header + "\n".join(linhas) if linhas else "Nenhum registro."

    contexto = serializar_resultado(resultado, lbl1, lbl2)
    thread_id = finhelper.criar_thread(contexto)

    return texto_resumo, tabela, xlsx_path, thread_id, []


def enviar_chat(mensagem, historico, thread_id):
    """Envia mensagem ao assistente e retorna o histórico atualizado."""
    if not mensagem or not mensagem.strip():
        return historico, "", thread_id

    if not thread_id:
        historico = historico + [
            {"role": "user", "content": mensagem},
            {"role": "assistant", "content": "⚠️ Processe os arquivos primeiro antes de usar o chat."},
        ]
        return historico, "", thread_id

    resposta = finhelper.enviar_mensagem(thread_id, mensagem)
    historico = historico + [
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": resposta},
    ]
    return historico, "", thread_id


def limpar():
    return None, None, "", "", None, None, []


with gr.Blocks(title="FinHelper — Conciliacao Financeira") as app:
    gr.Markdown("# FinHelper — Conciliação Financeira\nEnvie dois arquivos para comparar o valor líquido por localizador.")

    thread_state = gr.State(value=None)

    arq1 = gr.File(label="Arquivo 1 (.xlsx, .csv ou .cnf)", file_types=[".xlsx", ".csv", ".cnf"])
    arq2 = gr.File(label="Arquivo 2 (.xlsx, .csv ou .cnf)", file_types=[".xlsx", ".csv", ".cnf"])

    with gr.Row():
        btn_enviar = gr.Button("Enviar", variant="primary")
        btn_limpar = gr.Button("Limpar")

    out_resumo = gr.Markdown(label="Resumo")
    out_xlsx = gr.File(label="Baixar Excel")

    gr.Markdown("### 💬 Chat com FinHelper\nPergunte sobre divergências, localizadores ou qualquer detalhe da conciliação.")
    chatbot = gr.Chatbot(label="FinHelper", height=350)
    with gr.Row():
        chat_input = gr.Textbox(
            placeholder="Ex: Onde deu divergência no localizador XYZ?",
            label="Mensagem",
            scale=4,
        )
        btn_chat = gr.Button("Enviar", variant="primary", scale=1)

    out_tabela = gr.Markdown(label="Resultado")

    btn_enviar.click(
        fn=processar,
        inputs=[arq1, arq2],
        outputs=[out_resumo, out_tabela, out_xlsx, thread_state, chatbot],
    )
    btn_limpar.click(
        fn=limpar,
        inputs=[],
        outputs=[arq1, arq2, out_resumo, out_tabela, out_xlsx, thread_state, chatbot],
    )
    btn_chat.click(
        fn=enviar_chat,
        inputs=[chat_input, chatbot, thread_state],
        outputs=[chatbot, chat_input, thread_state],
    )
    chat_input.submit(
        fn=enviar_chat,
        inputs=[chat_input, chatbot, thread_state],
        outputs=[chatbot, chat_input, thread_state],
    )

if __name__ == "__main__":
    app.launch()
