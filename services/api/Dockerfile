FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system zenit && adduser --system --ingroup zenit zenit

COPY pyproject.toml README.md ./
COPY services/api/src ./services/api/src
COPY services/geospatial-worker/src ./services/geospatial-worker/src

RUN python -m pip install --upgrade pip \
    && python -m pip install .

USER zenit

EXPOSE 8000

CMD ["uvicorn", "zenit_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
