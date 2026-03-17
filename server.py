import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from conciliador import Conciliador
from finhelper import FinHelper

app = FastAPI(title="FinHelper")
app.mount("/static", StaticFiles(directory="static"), name="static")

conciliador = Conciliador()
finhelper = FinHelper()

# Estado em memória (single-user)
_state = {"thread_id": None, "xlsx_path": None}


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/api/processar")
async def processar(arquivo1: UploadFile = File(...), arquivo2: UploadFile = File(...)):
    tmp1 = _salvar_temp(arquivo1)
    tmp2 = _salvar_temp(arquivo2)

    try:
        resumo, resultado, lbl1, lbl2, xlsx_path = conciliador.processar_arquivos(tmp1, tmp2)
    finally:
        os.unlink(tmp1)
        os.unlink(tmp2)

    _state["xlsx_path"] = xlsx_path

    # Cria thread para o chat (não bloqueia o processamento se falhar)
    try:
        contexto = _serializar(resultado, lbl1, lbl2)
        _state["thread_id"] = finhelper.criar_thread(contexto)
    except Exception:
        _state["thread_id"] = None  # Chat indisponível, mas processamento ok

    return {"resumo": resumo, "resultado": resultado, "lbl1": lbl1, "lbl2": lbl2}


@app.get("/api/download")
async def download():
    path = _state.get("xlsx_path")
    if not path or not os.path.exists(path):
        return {"error": "Nenhum arquivo disponível"}
    return FileResponse(path, filename="conciliacao.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class ChatMsg(BaseModel):
    mensagem: str


@app.post("/api/chat")
async def chat(msg: ChatMsg):
    tid = _state.get("thread_id")
    if not tid:
        return {"resposta": "Processe os arquivos primeiro antes de usar o chat."}
    resposta = finhelper.enviar_mensagem(tid, msg.mensagem)
    return {"resposta": resposta}


# ── Helpers ──

def _salvar_temp(upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename)[1]
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(upload.file.read())
    return path


def _serializar(resultado, lbl1, lbl2):
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

        origem = r.get("origem_dif", "")

        linha = (
            f"LOC: {r['loc']} | PAX: {r['pax']} | Status: {r['status']}"
            f" | Liq. {lbl1}: {liq1} | Liq. {lbl2}: {liq2}"
            f" | Diferença: {dif} | Origem: {origem}"
            f" | Esperado Fornecedor: {esp}"
            f" | Diverg. Interna: {'SIM' if div_int else 'Não'}"
            f" | Dif. Interna: {dif_int}"
            f" | Nº Venda: {r.get('venda', '')} | Cliente: {r.get('cliente', '')}"
            f" | Emissor: {r.get('emissor', '')} | Markup: {r.get('markup', '')}"
            f" | Tarifa Total: {r.get('tarifa', '')}"
        )
        linhas.append(linha)
    return "\n".join(linhas)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
