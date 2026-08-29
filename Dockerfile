FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --home-dir /app app

COPY requirements.txt ./requirements.txt
# As dependências diretas usam pins exatos e são auditadas no gate de qualidade.
RUN python -m pip install --no-cache-dir --requirement requirements.txt  # NOSONAR

COPY --chown=app:app app ./app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
