.SILENT:

ARGS = $(filter-out $@,$(MAKECMDGOALS))

run:
	poetry run python app.py

install:
	poetry install

add:
	poetry add $(ARGS)

remove:
	poetry remove $(ARGS)

test:
	powershell -File ci.ps1

backup:
	powershell -File backup.ps1

clean:
	rm -rf __pycache__ .pytest_cache Backup

update:
	poetry update

lock:
	poetry lock

shell:
	poetry shell

%:
	@true
