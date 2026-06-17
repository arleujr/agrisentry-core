# Dockerfile (agrisentry-core)

FROM python:3.11-slim

WORKDIR /opt/agrisentry/core

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd --system agrisentry_grp && \
    useradd --system --gid agrisentry_grp --no-create-home --shell /sbin/nologin agrisentry_usr

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Correção: Agora copia o arquivo correto de dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

RUN chown -R agrisentry_usr:agrisentry_grp /opt/agrisentry/core

USER agrisentry_usr:agrisentry_grp

CMD ["python", "-m", "src.main"]