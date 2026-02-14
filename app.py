import os, json, tempfile, pandas as pd
import gradio as gr

DOCS = "docs"
TOLERANCIA = 0.01

# Mapa de colunas por extensão
LOC = {".csv": "LOC", ".cnf": "loc_cia", ".xlsx": "Localizador/Cód. Confirmação"}
LIQ = {".csv": "Liquido", ".cnf": "liquido", ".xlsx": "Total Fornec. (-DF)"}
PAX = {".csv": "Passageiro", ".cnf": "nome_pax", ".xlsx": "Pax"}


def moeda_br(v):
    if pd.isna(v) or str(v).strip() == "": return 0.0
    if isinstance(v, (int, float)): return round(float(v), 2)
    return round(float(str(v).strip().replace(".", "").replace(",", ".")), 2)


def ler(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    if ext == ".xlsx":
        df = pd.read_excel(caminho, header=5, engine="openpyxl")
    elif ext == ".csv":
        df = pd.read_csv(caminho, sep=";", encoding="latin-1", on_bad_lines="skip")
    elif ext == ".cnf":
        df = pd.read_csv(caminho, sep="\t", encoding="latin-1", on_bad_lines="skip")
    else:
        raise ValueError(f"Formato {ext} nao suportado")

    df = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(how="all")

    col_loc, col_liq = LOC[ext], LIQ[ext]
    df[col_loc] = df[col_loc].astype(str).str.strip().str.upper()

    if ext == ".xlsx":
        df[col_liq] = df[col_liq].apply(lambda v: round(float(v), 2) if pd.notna(v) else 0.0)
    else:
        df[col_liq] = df[col_liq].apply(moeda_br)

    return df, ext


# Colunas extras só do xlsx
XLSX_EXTRAS = ["Venda Nº", "Cod. Cliente", "Cod. Emissor", "Markup", "Total Tarifa"]

def rotulo(ext):
    return "Sistema Wintour" if ext == ".xlsx" else "Fornecedor"

def agrupar(df, ext):
    cl, cq, cp = LOC[ext], LIQ[ext], PAX[ext]
    g = {}
    for _, r in df.iterrows():
        k = str(r[cl]).strip().upper()
        if not k or k in ("NAN", "NONE", "NAT"):
            continue
        item = {"liquido": r[cq], "pax": str(r.get(cp, "")).strip()}
        if ext == ".xlsx":
            for c in XLSX_EXTRAS:
                item[c] = str(r.get(c, "")).strip() if pd.notna(r.get(c)) else ""
        g.setdefault(k, []).append(item)
    return g


def extras_xlsx(registros):
    """Pega dados extras do primeiro registro xlsx."""
    r = registros[0]
    return {
        "venda": r.get("Venda Nº", ""),
        "cliente": r.get("Cod. Cliente", ""),
        "emissor": r.get("Cod. Emissor", ""),
        "markup": r.get("Markup", ""),
        "tarifa": r.get("Total Tarifa", ""),
    }

def conciliar(g1, g2, lbl1, lbl2, ext1, ext2):
    locs1, locs2 = set(g1), set(g2)
    resultado = []

    # Identifica qual grupo é xlsx e qual é fornecedor
    def get_extras(loc):
        if ext1 == ".xlsx" and loc in g1: return extras_xlsx(g1[loc])
        if ext2 == ".xlsx" and loc in g2: return extras_xlsx(g2[loc])
        return {"venda": "", "cliente": "", "emissor": "", "markup": "", "tarifa": ""}

    def safe_float(v):
        try: return round(float(v), 2)
        except: return 0.0

    for loc in sorted(locs1 & locs2):
        s1 = round(sum(r["liquido"] for r in g1[loc]), 2)
        s2 = round(sum(r["liquido"] for r in g2[loc]), 2)
        dif = round(s1 - s2, 2)
        pax = g1[loc][0]["pax"] or g2[loc][0]["pax"]
        extras = get_extras(loc)

        # Identifica líquido fornecedor e dados wintour
        if ext1 == ".xlsx":
            liq_wintour, liq_fornecedor = s1, s2
        else:
            liq_wintour, liq_fornecedor = s2, s1

        tarifa = safe_float(extras["tarifa"])
        markup = safe_float(extras["markup"])
        esperado = round(tarifa - markup, 2)

        if abs(dif) < TOLERANCIA:
            status = "Ok"
        else:
            status = "Divergente"

        resultado.append({
            "loc": loc, "pax": pax, "status": status,
            f"liq_{lbl1}": s1, f"liq_{lbl2}": s2, "dif": dif,
            "esperado_fornecedor": esperado,
            **extras
        })

    for loc in sorted(locs1 - locs2):
        s = round(sum(r["liquido"] for r in g1[loc]), 2)
        status = "Somente Fornecedor" if ext1 != ".xlsx" else "Somente Wintour"
        resultado.append({"loc": loc, "pax": g1[loc][0]["pax"], "status": status,
                          f"liq_{lbl1}": s, f"liq_{lbl2}": "", "dif": "",
                          "esperado_fornecedor": "", **get_extras(loc)})

    for loc in sorted(locs2 - locs1):
        s = round(sum(r["liquido"] for r in g2[loc]), 2)
        status = "Somente Fornecedor" if ext2 != ".xlsx" else "Somente Wintour"
        resultado.append({"loc": loc, "pax": g2[loc][0]["pax"], "status": status,
                          f"liq_{lbl1}": "", f"liq_{lbl2}": s, "dif": "",
                          "esperado_fornecedor": "", **get_extras(loc)})

    # INTERFACE detectado em Emissor ou Cliente → sempre Divergente
    for r in resultado:
        e = str(r.get("emissor", "")).strip().upper()
        c = str(r.get("cliente", "")).strip().upper()
        if e == "EINTERFACE" or c == "CINTERFACE":
            r["status"] = "Divergente"

    return resultado


def main():
    arqs = sorted([f for f in os.listdir(DOCS) if f.lower().endswith((".xlsx", ".csv", ".cnf"))])
    if len(arqs) < 2:
        print("Coloque pelo menos 2 arquivos na pasta docs/"); return

    for i, a in enumerate(arqs):
        print(f"  [{i}] {a}")

    if len(arqs) == 2:
        i1, i2 = 0, 1
    else:
        i1 = int(input("\nIndice do arquivo 1: "))
        i2 = int(input("Indice do arquivo 2: "))

    c1, c2 = os.path.join(DOCS, arqs[i1]), os.path.join(DOCS, arqs[i2])
    n1, n2 = arqs[i1], arqs[i2]
    print()

    df1, ext1 = ler(c1)
    df2, ext2 = ler(c2)
    g1, g2 = agrupar(df1, ext1), agrupar(df2, ext2)
    lbl1, lbl2 = rotulo(ext1), rotulo(ext2)

    resultado = conciliar(g1, g2, lbl1, lbl2, ext1, ext2)

    n_ok = sum(1 for r in resultado if r["status"] == "Ok")
    n_div = sum(1 for r in resultado if r["status"] == "Divergente")
    n_sf = sum(1 for r in resultado if r["status"] == "Somente Fornecedor")
    n_sw = sum(1 for r in resultado if r["status"] == "Somente Wintour")

    print(f"{'='*55}")
    print(f" {lbl1}  x  {lbl2}")
    print(f"{'='*55}")
    print(f"  Locs {lbl1}: {len(g1)}  |  Locs {lbl2}: {len(g2)}")
    print(f"  OK: {n_ok}  |  Divergentes: {n_div}")
    print(f"  Somente Fornecedor: {n_sf}  |  Somente Wintour: {n_sw}")
    print(f"{'='*55}")
    with open("resultado_conciliacao.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2, default=str)
    print("Salvo em resultado_conciliacao.json")


## ── Geração XLSX ──

def gerar_xlsx(resultado, lbl1, lbl2):
    rows = []
    for r in resultado:
        rows.append({
            "Localizador": r["loc"],
            "Passageiro": r["pax"],
            "Status": r["status"],
            f"Liq. {lbl1}": r.get(f"liq_{lbl1}", ""),
            f"Liq. {lbl2}": r.get(f"liq_{lbl2}", ""),
            "Diferenca": r.get("dif", ""),
            "Esperado Fornecedor (Tarifa-Markup)": r.get("esperado_fornecedor", ""),
            "Nº Venda": r.get("venda", ""),
            "Cliente": r.get("cliente", ""),
            "Emissor": r.get("emissor", ""),
            "Markup": r.get("markup", ""),
            "Tarifa Total": r.get("tarifa", ""),
        })
    df = pd.DataFrame(rows)
    caminho = os.path.join(tempfile.gettempdir(), "conciliacao.xlsx")
    df.to_excel(caminho, index=False, engine="openpyxl")
    return caminho


## ── Gradio ──

def processar(arquivo1, arquivo2):
    if not arquivo1 or not arquivo2:
        return "Envie os dois arquivos.", "", None

    try:
        df1, ext1 = ler(arquivo1)
        df2, ext2 = ler(arquivo2)
    except Exception as e:
        return f"Erro na leitura: {e}", "", None

    lbl1, lbl2 = rotulo(ext1), rotulo(ext2)
    g1, g2 = agrupar(df1, ext1), agrupar(df2, ext2)
    resultado = conciliar(g1, g2, lbl1, lbl2, ext1, ext2)

    n_ok = sum(1 for r in resultado if r["status"] == "Ok")
    n_div = sum(1 for r in resultado if r["status"] == "Divergente")
    n_sf = sum(1 for r in resultado if r["status"] == "Somente Fornecedor")
    n_sw = sum(1 for r in resultado if r["status"] == "Somente Wintour")

    resumo = (
        f"**{lbl1}** x **{lbl2}**\n\n"
        f"- Localizadores {lbl1}: {len(g1)}\n"
        f"- Localizadores {lbl2}: {len(g2)}\n"
        f"- Ok: {n_ok}\n"
        f"- Divergentes: {n_div}\n"
        f"- Somente Fornecedor: {n_sf}\n"
        f"- Somente Wintour: {n_sw}\n"
    )

    # Tabela única com todos os registros
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

    xlsx_path = gerar_xlsx(resultado, lbl1, lbl2)

    return resumo, tabela, xlsx_path


with gr.Blocks(title="FinHelper — Conciliacao Financeira") as app:
    gr.Markdown("# FinHelper — Conciliação Financeira\nEnvie dois arquivos para comparar o valor líquido por localizador.")

    arq1 = gr.File(label="Arquivo 1 (.xlsx, .csv ou .cnf)", file_types=[".xlsx", ".csv", ".cnf"])
    arq2 = gr.File(label="Arquivo 2 (.xlsx, .csv ou .cnf)", file_types=[".xlsx", ".csv", ".cnf"])

    with gr.Row():
        btn_enviar = gr.Button("Enviar", variant="primary")
        btn_limpar = gr.Button("Limpar")

    out_resumo = gr.Markdown(label="Resumo")
    out_xlsx = gr.File(label="Baixar Excel")
    out_tabela = gr.Markdown(label="Resultado")

    btn_enviar.click(fn=processar, inputs=[arq1, arq2], outputs=[out_resumo, out_tabela, out_xlsx])
    btn_limpar.click(fn=lambda: (None, None, "", "", None), inputs=[], outputs=[arq1, arq2, out_resumo, out_tabela, out_xlsx])

if __name__ == "__main__":
    app.launch()
