.SILENT:

ARGS = $(filter-out $@,$(MAKECMDGOALS))
POETRY_RUN = poetry run python
DJANGO_RUN = $(POETRY_RUN) manage.py


# django comandos
app-run: # inicia um novo app 
	$(DJANGO_RUN) startapp $(ARGS)

check: # checa a sintaxe 
	$(DJANGO_RUN) check

makemigrations:
	$(DJANGO_RUN) makemigrations

migrate: makemigrations # inicia as migrações
	$(DJANGO_RUN) migrate

runserver: # roda o servidor django
	$(DJANGO_RUN) runserver

cmd: # para executar comandos do django
	$(DJANGO_RUN) $(ARGS)

# poetry comandos
run-poetry: # rodar comando dentro do ambiente
	$(POETRY_RUN) $(ARGS)

install: # instala dependencia do pyproject
	poetry install

add: # instala novas dependencias
	poetry add $(ARGS)

remove: # remove dependencia
	poetry remove $(ARGS)

update: # sincroniza as denpendencias de acordo suas atualizações
	poetry update

lock: # calcula e atualiza o arquivo poetry.lock sem alterar o arquivo pyproject.toml
	poetry lock

shell: # ativa o ambiente virtual do projeto diretamente pelo terminal
	poetry shell

