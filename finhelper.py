import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class FinHelper:
    """Wrapper para o assistente OpenAI que responde sobre conciliação financeira."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
            self.disponivel = True
        else:
            self.client = None
            self.assistant_id = None
            self.disponivel = False

    def criar_thread(self, contexto: str) -> str | None:
        if not self.disponivel:
            return None
        """Cria uma thread e envia os dados de conciliação como contexto inicial.

        O contexto é adicionado como primeira mensagem (sem run),
        de modo que o assistente o enxergue quando a primeira pergunta for enviada.
        """
        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "Você receberá perguntas sobre os dados de conciliação financeira abaixo. "
                "Use esses dados como base de verdade absoluta para suas respostas. "
                "Responda de forma clara e objetiva, citando os valores exatos dos dados.\n\n"
                "REGRAS DE NEGÓCIO IMPORTANTES:\n"
                "1. Para pagamentos 'IV' (dinheiro/invoice): o 'Esp. Fornec.' = (Tarifa + Taxas) - Markup. "
                "Para outros pagamentos (cartão CC, CA etc.): 'Esp. Fornec.' = -Markup (tarifa e taxas não são repassadas). "
                "Quando 'Diverg. Interna' = SIM, o Total Fornec. (-DF) difere do esperado. 'Dif. Interna' mostra a diferença.\n"
                "2. A coluna 'Dif. Over' = Over Agência (Wintour) - Incentivo (Fornecedor). "
                "Se 'Over OK' = OK significa que os valores batem; se 'Divergente', há diferença no Over/Incentivo.\n\n"
                "DADOS DA CONCILIAÇÃO:\n"
                f"{contexto}"
            ),
        )
        return thread.id

    def enviar_mensagem(self, thread_id: str, mensagem: str) -> str:
        """Envia uma mensagem do usuário, cria um run e retorna a resposta do assistente."""
        if not self.disponivel:
            return "Chat IA indisponível — configure OPENAI_API_KEY nas variáveis de ambiente."
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=mensagem,
        )
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )
        run = self._aguardar_run(thread_id, run.id)

        if run.status == "completed":
            mensagens = self.client.beta.threads.messages.list(thread_id=thread_id)
            for msg in mensagens.data:
                if msg.role == "assistant":
                    return msg.content[0].text.value
        return "Erro: não foi possível obter resposta do assistente."

    def _aguardar_run(self, thread_id: str, run_id: str):
        """Polling até o run sair do estado 'queued'/'in_progress'."""
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )
            if run.status not in ("queued", "in_progress", "cancelling"):
                return run
            time.sleep(1)
