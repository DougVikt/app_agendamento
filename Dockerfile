# Dockerfile para app-agendamento Django + Poetry
FROM python:3.12-slim

WORKDIR /app

# Copia dependencias primeiro para cache
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev --no-interaction

# Copia codigo
COPY . .

# Define variavel para Django
ENV DJANGO_SETTINGS_MODULE=mainsetup.settings
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
