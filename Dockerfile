FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml setup.cfg README.md LICENSE ./
COPY centri ./centri
COPY scripts ./scripts
COPY sample_agent_router_dataset.json ./

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "if [ ! -f data/compiled/faiss.index ]; then python -m scripts.compile; fi; exec python -m centri.gateway.app"]
