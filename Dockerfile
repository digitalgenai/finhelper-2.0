FROM python:3.12-slim

# Criar grupo e usuário não-privilegiado
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --gid 1001 appuser

WORKDIR /app

COPY requirements.docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.txt

COPY server.py conciliador.py finhelper.py ./
COPY static/ ./static/

# Ajustar permissões para o usuário não-privilegiado
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
