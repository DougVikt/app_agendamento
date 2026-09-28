.SILENT:

ARGS = $(filter-out $@,$(MAKECMDGOALS))
POETRY_RUN = poetry run python
DJANGO_RUN = $(POETRY_RUN) manage.py


# django comandos
app-run:
	$(DJANGO_RUN) startapp $(ARGS)

check:
	$(DJANGO_RUN) check

migrate:
	$(DJANGO_RUN) migrate

runserver:
	$(DJANGO_RUN) runserver

# poetry comandos
run-poetry:
	$(POETRY_RUN) $(ARGS)

install:
	poetry install

add:
	poetry add $(ARGS)

remove:
	poetry remove $(ARGS)

update:
	poetry update

lock:
	poetry lock

shell:
	poetry shell

