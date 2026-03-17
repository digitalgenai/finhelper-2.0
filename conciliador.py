import os
import tempfile

import pandas as pd


class Conciliador:
    """Classe responsável pela leitura, análise e conciliação de arquivos financeiros."""

    TOLERANCIA = 0.01

    # Mapa de colunas por extensão
    COL_LOC = {".csv": "LOC", ".cnf": "loc_cia", ".xlsx": "Localizador/Cód. Confirmação"}
    COL_LIQ = {".csv": "Liquido", ".cnf": "liquido", ".xlsx": "Total Fornec. (-DF)"}
    COL_PAX = {".csv": "Passageiro", ".cnf": "nome_pax", ".xlsx": "Pax"}

    XLSX_EXTRAS = ["Venda Nº", "Cod. Cliente", "Cod. Emissor", "Markup", "Total Tarifa", "Total Taxas",
                   "Total DU/RAV (Bruta)", "Over Agência", "Total Outras Taxas"]

    # Mapeamento campo a campo: (nome_exibição, colunas_fornecedor, coluna_xlsx)
    # colunas_fornecedor = lista de possíveis nomes (CSV e CNF)
    CAMPO_MAP = [
        ("Tarifa",          ["Tarifa R$", "tarifa_brl"],   "Total Tarifa"),
        ("Taxa",            ["Taxa", "tx_emb"],            "Total Taxas"),
        ("Taxa de Embarque",["TxDU", "repasse_du"],        "Total DU/RAV (Bruta)"),
        ("Over/Incentivo",  ["Incentivo", "incentivo"],    "Over Agência"),
    ]

    # ── Utilitários ──

    @staticmethod
    def moeda_br(v):
        """Converte string monetária brasileira para float."""
        if pd.isna(v) or str(v).strip() == "":
            return 0.0
        if isinstance(v, (int, float)):
            return round(float(v), 2)
        return round(float(str(v).strip().replace(".", "").replace(",", ".")), 2)

    @staticmethod
    def rotulo(ext: str) -> str:
        return "Sistema Wintour" if ext == ".xlsx" else "Fornecedor"

    # ── Leitura ──

    def ler(self, caminho: str):
        """Lê arquivo (.xlsx, .csv ou .cnf) e retorna (DataFrame, extensão)."""
        ext = os.path.splitext(caminho)[1].lower()

        if ext == ".xlsx":
            df = pd.read_excel(caminho, header=5, engine="openpyxl")
        elif ext == ".csv":
            df = pd.read_csv(caminho, sep=";", encoding="latin-1", on_bad_lines="skip")
        elif ext == ".cnf":
            # CNF tem ; no final de cada linha de dados, gerando 1 campo extra
            # index_col=False evita que pandas use a primeira coluna como índice
            df = pd.read_csv(caminho, sep=";", encoding="latin-1", on_bad_lines="skip",
                             index_col=False)
        else:
            raise ValueError(f"Formato {ext} não suportado")

        df = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(how="all")

        col_loc = self.COL_LOC[ext]
        col_liq = self.COL_LIQ[ext]

        df[col_loc] = df[col_loc].astype(str).str.strip().str.upper()

        if ext == ".xlsx":
            df[col_liq] = df[col_liq].apply(lambda v: round(float(v), 2) if pd.notna(v) else 0.0)
        else:
            df[col_liq] = df[col_liq].apply(self.moeda_br)

        return df, ext

    # ── Agrupamento ──

    # Colunas extras do CSV/CNF que precisamos para comparação campo a campo
    CSV_EXTRAS = ["Tarifa R$", "Taxa", "TxDU", "Incentivo",
                  "tarifa_brl", "tx_emb", "repasse_du", "incentivo", "comissao", "acrescimos"]

    def agrupar(self, df: pd.DataFrame, ext: str) -> dict:
        """Agrupa registros por localizador."""
        cl = self.COL_LOC[ext]
        cq = self.COL_LIQ[ext]
        cp = self.COL_PAX[ext]

        grupos = {}
        for _, r in df.iterrows():
            k = str(r[cl]).strip().upper()
            if not k or k in ("NAN", "NONE", "NAT"):
                continue
            item = {"liquido": r[cq], "pax": str(r.get(cp, "")).strip()}
            if ext == ".xlsx":
                for c in self.XLSX_EXTRAS:
                    item[c] = str(r.get(c, "")).strip() if pd.notna(r.get(c)) else ""
            elif ext in (".csv", ".cnf"):
                for c in self.CSV_EXTRAS:
                    item[c] = str(r.get(c, "")).strip() if pd.notna(r.get(c)) else ""
            grupos.setdefault(k, []).append(item)
        return grupos

    # ── Extras XLSX ──

    @staticmethod
    def _extras_xlsx(registros: list) -> dict:
        """Extrai dados extras do primeiro registro xlsx."""
        r = registros[0]
        return {
            "venda": r.get("Venda Nº", ""),
            "cliente": r.get("Cod. Cliente", ""),
            "emissor": r.get("Cod. Emissor", ""),
            "markup": r.get("Markup", ""),
            "tarifa": r.get("Total Tarifa", ""),
            "taxas": r.get("Total Taxas", ""),
        }

    # ── Comparação campo a campo ──

    @staticmethod
    def _safe_float(v):
        """Converte valor para float sem aplicar lógica de moeda BR."""
        if v is None or str(v).strip() in ("", "nan", "NaN", "None"):
            return 0.0
        try:
            return round(float(v), 2)
        except (ValueError, TypeError):
            return 0.0

    def _comparar_campos(self, registros_csv, registros_xlsx):
        """Compara campos correspondentes entre CSV/CNF e XLSX e retorna descrição da divergência."""
        diferencas = []
        for nome, cols_fornec, col_xlsx in self.CAMPO_MAP:
            # Soma dos valores do CSV/CNF (moeda BR: 1.234,56)
            total_csv = 0.0
            for r in registros_csv:
                # Tenta cada coluna possível até encontrar uma com valor
                val = 0
                for col in cols_fornec:
                    v = r.get(col, "")
                    if v and str(v).strip() not in ("", "0", "0.0", "0,00"):
                        val = v
                        break
                    if not val:
                        val = r.get(col, 0)
                total_csv += self.moeda_br(val)
            total_csv = round(total_csv, 2)

            # Soma dos valores do XLSX (já são float ou string decimal: 1234.56)
            total_xlsx = 0.0
            for r in registros_xlsx:
                total_xlsx += self._safe_float(r.get(col_xlsx, 0))
            total_xlsx = round(total_xlsx, 2)

            dif_val = round(abs(total_csv - total_xlsx), 2)
            if dif_val > self.TOLERANCIA:
                diferencas.append({
                    "campo": nome,
                    "fornec": total_csv,
                    "wintour": total_xlsx,
                    "dif": round(total_csv - total_xlsx, 2)
                })

        if diferencas:
            campos = [d["campo"] for d in diferencas]
            detalhe = " | ".join([f"{d['campo']}: Fornec {d['fornec']:.2f} x Wintour {d['wintour']:.2f} (dif: {d['dif']:.2f})" for d in diferencas])
            return {
                "resumo": ", ".join(campos),
                "detalhe": detalhe
            }
        return {"resumo": "", "detalhe": ""}

    # ── Conciliação ──

    def conciliar(self, g1: dict, g2: dict, lbl1: str, lbl2: str, ext1: str, ext2: str) -> list:
        """Compara dois conjuntos de localizadores e retorna lista de resultados."""
        locs1, locs2 = set(g1), set(g2)
        resultado = []

        def get_extras(loc):
            if ext1 == ".xlsx" and loc in g1:
                return self._extras_xlsx(g1[loc])
            if ext2 == ".xlsx" and loc in g2:
                return self._extras_xlsx(g2[loc])
            return {"venda": "", "cliente": "", "emissor": "", "markup": "", "tarifa": "", "taxas": ""}

        def safe_float(v):
            try:
                return round(float(v), 2)
            except Exception:
                return 0.0

        # Localizadores presentes em ambos
        for loc in sorted(locs1 & locs2):
            s1 = round(sum(r["liquido"] for r in g1[loc]), 2)
            s2 = round(sum(r["liquido"] for r in g2[loc]), 2)
            dif = round(s1 - s2, 2)
            pax = g1[loc][0]["pax"] or g2[loc][0]["pax"]
            extras = get_extras(loc)

            tarifa = safe_float(extras["tarifa"])
            markup = safe_float(extras["markup"])
            taxas = safe_float(extras["taxas"])
            esperado = round((tarifa + taxas) - markup, 2)

            # Verifica consistência interna do xlsx:
            # Total Fornec. (-DF) deve ser igual a (Total Tarifa + Total Taxas) - Markup
            if ext1 == ".xlsx":
                liq_wintour = s1
            else:
                liq_wintour = s2

            if tarifa > 0 or markup > 0:
                dif_interna = round(liq_wintour - esperado, 2)
                divergencia_interna = abs(dif_interna) > self.TOLERANCIA
            else:
                dif_interna = 0.0
                divergencia_interna = False

            status = "Ok" if abs(dif) < self.TOLERANCIA else "Divergente"

            # Comparação campo a campo para identificar origem da divergência
            origem_dif = ""
            origem_dif_detalhe = ""
            if status == "Divergente":
                # Determinar qual grupo é CSV e qual é XLSX
                comp = {"resumo": "", "detalhe": ""}
                if ext1 in (".csv", ".cnf") and ext2 == ".xlsx":
                    comp = self._comparar_campos(g1[loc], g2[loc])
                elif ext1 == ".xlsx" and ext2 in (".csv", ".cnf"):
                    comp = self._comparar_campos(g2[loc], g1[loc])
                origem_dif = comp["resumo"]
                origem_dif_detalhe = comp["detalhe"]

            resultado.append({
                "loc": loc, "pax": pax, "status": status,
                f"liq_{lbl1}": s1, f"liq_{lbl2}": s2, "dif": dif,
                "origem_dif": origem_dif,
                "origem_dif_detalhe": origem_dif_detalhe,
                "esperado_fornecedor": esperado,
                "divergencia_interna": divergencia_interna,
                "dif_interna": dif_interna,
                **extras,
            })

        # Somente no grupo 1
        for loc in sorted(locs1 - locs2):
            s = round(sum(r["liquido"] for r in g1[loc]), 2)
            status = "Somente Fornecedor" if ext1 != ".xlsx" else "Somente Wintour"
            resultado.append({
                "loc": loc, "pax": g1[loc][0]["pax"], "status": status,
                f"liq_{lbl1}": s, f"liq_{lbl2}": "", "dif": "",
                "origem_dif": f"Localizador ausente no {lbl2}",
                "esperado_fornecedor": "",
                "divergencia_interna": False, "dif_interna": "",
                **get_extras(loc),
            })

        # Somente no grupo 2
        for loc in sorted(locs2 - locs1):
            s = round(sum(r["liquido"] for r in g2[loc]), 2)
            status = "Somente Fornecedor" if ext2 != ".xlsx" else "Somente Wintour"
            resultado.append({
                "loc": loc, "pax": g2[loc][0]["pax"], "status": status,
                f"liq_{lbl1}": "", f"liq_{lbl2}": s, "dif": "",
                "origem_dif": f"Localizador ausente no {lbl1}",
                "esperado_fornecedor": "",
                "divergencia_interna": False, "dif_interna": "",
                **get_extras(loc),
            })

        # INTERFACE detectado em Emissor ou Cliente → sempre Divergente
        for r in resultado:
            e = str(r.get("emissor", "")).strip().upper()
            c = str(r.get("cliente", "")).strip().upper()
            if e == "EINTERFACE" or c == "CINTERFACE":
                old_status = r["status"]
                r["status"] = "Divergente"
                # Adicionar EINTERFACE na origem se não tinha outra explicação
                origem = r.get("origem_dif", "")
                if not origem or "ausente" in origem:
                    r["origem_dif"] = "EINTERFACE" + (f" ({old_status})" if old_status != "Divergente" else "")

        return resultado

    # ── Geração XLSX ──

    def gerar_xlsx(self, resultado: list, lbl1: str, lbl2: str) -> str:
        """Gera planilha Excel com o resultado da conciliação e retorna o caminho."""
        rows = []
        for r in resultado:
            div_int = r.get("divergencia_interna", False)
            rows.append({
                "Localizador": r["loc"],
                "Passageiro": r["pax"],
                "Status": r["status"],
                f"Liq. {lbl1}": r.get(f"liq_{lbl1}", ""),
                f"Liq. {lbl2}": r.get(f"liq_{lbl2}", ""),
                "Diferenca": r.get("dif", ""),
                "Campo Divergente": r.get("origem_dif", ""),
                "Detalhe da Diferença": r.get("origem_dif_detalhe", ""),
                "Esperado Fornecedor (Tarifa+Taxas-Markup)": r.get("esperado_fornecedor", ""),
                "Diverg. Interna (Fornec vs Tarifa+Taxas-Markup)": "SIM" if div_int else "Não",
                "Dif. Interna": r.get("dif_interna", ""),
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

    # ── Pipeline completo ──

    def processar_arquivos(self, caminho1: str, caminho2: str):
        """Lê, agrupa, concilia e gera XLSX. Retorna (resumo, resultado, lbl1, lbl2, xlsx_path)."""
        df1, ext1 = self.ler(caminho1)
        df2, ext2 = self.ler(caminho2)

        lbl1, lbl2 = self.rotulo(ext1), self.rotulo(ext2)
        # Se os dois labels ficaram iguais, diferenciar
        if lbl1 == lbl2:
            lbl1 = "Fornecedor"
            lbl2 = "Sistema Wintour"
        g1 = self.agrupar(df1, ext1)
        g2 = self.agrupar(df2, ext2)

        resultado = self.conciliar(g1, g2, lbl1, lbl2, ext1, ext2)
        xlsx_path = self.gerar_xlsx(resultado, lbl1, lbl2)

        resumo = {
            "lbl1": lbl1,
            "lbl2": lbl2,
            "locs_1": len(g1),
            "locs_2": len(g2),
            "ok": sum(1 for r in resultado if r["status"] == "Ok"),
            "divergentes": sum(1 for r in resultado if r["status"] == "Divergente"),
            "somente_fornecedor": sum(1 for r in resultado if r["status"] == "Somente Fornecedor"),
            "somente_wintour": sum(1 for r in resultado if r["status"] == "Somente Wintour"),
        }

        return resumo, resultado, lbl1, lbl2, xlsx_path
