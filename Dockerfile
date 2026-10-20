# Imagem de produção. A mesma imagem roda os três processos do projeto:
#   API (padrão):  fastapi run, porta $PORT (8000 se não definida)
#   worker:        python -m app.worker
#   migrations:    alembic upgrade head (precisa rodar antes da API e do worker)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências antes do código: enquanto o requirements.txt não mudar, o Docker
# reaproveita esta camada em cache e o build leva segundos.
# Só as dependências de produção: pytest e Ruff ficam de fora da imagem.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Só o que a aplicação precisa para rodar. Testes, .env e .git ficam de fora
# (ver .dockerignore).
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Processo sem privilégios de root: se alguém explorar uma falha na aplicação,
# não ganha controle total do container.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# Sem HEALTHCHECK aqui de propósito: o worker usa esta mesma imagem e não serve
# HTTP, então seria marcado como "unhealthy". A checagem do /health fica na
# plataforma de deploy, configurada só para a API.

# Forma shell com exec: o ${PORT} é expandido (o Render define essa variável) e o
# exec faz o fastapi virar o processo 1, recebendo o SIGTERM direto do Docker.
CMD ["sh", "-c", "exec fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}"]
