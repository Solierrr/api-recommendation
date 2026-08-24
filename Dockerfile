FROM python:3.12-slim

WORKDIR /app

# Instala as dependências antes de copiar o código da aplicação para
# aproveitar o cache de camadas do Docker (só reinstala quando o
# requirements.txt muda, não a cada alteração de código).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Executa a aplicação com um usuário sem privilégios de root, reduzindo o
# impacto de uma eventual vulnerabilidade explorada dentro do container.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
