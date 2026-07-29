FROM python:3.13-slim

WORKDIR /app

RUN pip install poetry==2.4.1

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

COPY alembic.ini ./
COPY src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
