# Sistema de Agendamento

Sistema web de agendamento para intranet, migrado do app Flask original para
**Django**. A central de atendimento escolhe o profissional e reserva um horário
livre; cada profissional mantém a própria grade, acompanha a agenda e atualiza o
status dos atendimentos; a recepção consulta os agendados e o histórico; e o
administrador aprova os cadastros.

> **Branch `alterDjango`** — o app Flask antigo foi preservado em `app_antigo/`
> apenas como referência e não faz parte da aplicação Django em execução.

## Visão geral

- A central **não escolhe data manualmente**: seleciona o profissional e o
  sistema devolve os horários livres dos próximos 21 dias, gerados a partir da
  grade e do intervalo definidos pelo profissional.
- Os horários são clicáveis e abrem um modal para preencher os dados do cliente.
- O profissional vê o calendário do mês, navega entre meses, clica em um dia e
  consulta a agenda daquele dia.
- Remarcações atualizam o contador e exibem o selo `Remarcado` ou
  `RemarcadoNx`.
- O cadastro cria um usuário inativo e um perfil pendente; a liberação é feita
  pelo administrador no Django Admin.

## Funcionalidades

### Autenticação e cadastro

- Cadastro com nome, usuário, senha, confirmação de senha e escolha do perfil.
- Conta criada como inativa, aguardando aprovação do administrador.
- Login com redirecionamento automático para a página do perfil.
- Bloqueio de acesso para usuários pendentes ou inativos.
- Logout e mensagens de feedback em todas as telas.

### Central de Atendimento

- Seleção do profissional.
- Horários disponíveis agrupados por dia, respeitando o intervalo da grade.
- Reserva por clique no horário, com modal de confirmação.
- Cadastro dos dados do cliente: nome, CPF, telefone, tipo de serviço e
  observações.
- Lista de agendamentos futuros com edição e remarcação.
- Validação de horário disponível antes de gravar, evitando conflitos.

### Profissional

- Painel com atendimentos de hoje, atrasados, próximos e total de grades.
- Calendário mensal clicável com navegação para o mês anterior e o próximo.
- Agenda do dia selecionado.
- Alteração de status: atendido, ausente ou cancelado.
- Remarcação de atendimentos.
- Cadastro e exclusão de grades fixas (data específica) ou semanais.
- Definição do intervalo entre horários (15, 20, 30, 45, 60 ou 90 minutos).

### Recepção

- Consulta dos próximos agendamentos.
- Histórico recente e histórico completo com filtros.
- Sem acesso a atrasados e sem exibição de observações.

### Administração

- Django Admin com usuários, perfis, grades e agendamentos.
- Aprovação ou rejeição de cadastros por action no changelist de perfis.
- Criação de grupos e permissões por data migration.
- Visualização de agendamentos, grades e histórico.

## Regras de negócio

- **Grupos de acesso:** `recepcao`, `central`, `profissional` e superuser/admin.
- **Recepção:** vê apenas agendados e histórico; não vê atrasados nem
  observações.
- **Central:** cria, edita e remarca agendamentos; não vê atrasados.
- **Profissional:** vê hoje, atrasados, calendário, status e remarcação.
- **Cadastro:** cria `User(is_active=False)` e `Profile` com status pendente.
- **Aprovação:** feita pelo admin, que ativa o usuário e o adiciona ao grupo
  correspondente.
- **Grade semanal:** exige `date IS NULL` e `day_week` preenchido.
- **Grade fixa:** exige uma data específica.
- **Conflito de horário:** a constraint `unique_active_slot` impede dois
  agendamentos ativos no mesmo profissional, data e horário.
- **Remarcação:** incrementa `num_reschedules`; o template exibe `Remarcado`
  para 1 e `RemarcadoNx` para 2 ou mais.
- **Horários passados:** não aparecem como disponíveis.

## Tecnologias

- **Backend:** Python 3.12+, Django 6.1, Poetry.
- **Banco de desenvolvimento:** SQLite (`db.sqlite3`).
- **Banco de produção:** PostgreSQL previsto para a etapa de Docker no servidor.
- **Frontend:** Bootstrap 5.3 em tema escuro, Bootstrap Icons, CSS próprio.
- **PWA:** manifest e ícone para instalação na intranet.
- **Testes:** suíte Django com 34 testes.

## Estrutura

```text
app_agendamento/
├── manage.py
├── pyproject.toml
├── poetry.lock
├── .env.example
├── mainsetup/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── control/
│   ├── models.py            # Profile, ScheduleTime, Appointment
│   ├── managers.py          # Consultas de agendamentos
│   ├── services.py          # Geração e disponibilidade de horários
│   ├── forms.py             # Cadastro, agendamento e grade
│   ├── views.py             # Páginas e fluxos por perfil
│   ├── decorators.py        # Restrição por grupo
│   ├── context_processors.py
│   ├── admin.py             # Actions de aprovação/rejeição
│   ├── migrations/
│   ├── templates/
│   │   ├── admin/           # Ajustes do admin
│   │   └── control/
│   │       ├── layouts/      # Layout base
│   │       ├── pages/        # Landing, painéis e histórico
│   │       ├── auth/         # Login, cadastro e aprovação
│   │       ├── appointments/ # Edição e remarcação
│   │       ├── schedules/    # Cadastro de grade
│   │       └── errors/       # Páginas 403, 404 e 500
│   └── tests.py             # 34 testes automatizados
├── static/
│   ├── css/app.css
│   ├── icon.svg
│   └── manifest.json
├── app_antigo/              # Referência Flask (não executar)
├── Dockerfile
├── docker-compose.yaml
└── README.md
```

## Como rodar

### Pré-requisitos

- Python 3.12 ou superior.
- Poetry instalado.
- Git.

### Passos

1. Clone o repositório e entre na pasta:

   ```bash
   git clone <url>
   cd app_agendamento
   ```

2. Instale as dependências:

   ```bash
   poetry install
   ```

3. Crie o arquivo de ambiente:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edite `.env` e defina uma `SECRET_KEY` segura. Em desenvolvimento, mantenha
   `DEBUG=True` e `ALLOWED_HOSTS=127.0.0.1,localhost`.

4. Aplique as migrations:

   ```bash
   poetry run python manage.py migrate
   ```

5. Crie o superusuário:

   ```bash
   poetry run python manage.py createsuperuser
   ```

6. Suba o servidor:

   ```bash
   poetry run python manage.py runserver
   ```

7. Acesse:

   - Aplicação: `http://localhost:8000/agendamento.app/`
   - Admin: `http://localhost:8000/admin/`

> O banco SQLite é criado automaticamente na primeira migration.

## Variáveis de ambiente

| Variável | Descrição | Exemplo |
|---|---|---|
| `SECRET_KEY` | Chave secreta do Django | `chave-django-aqui` |
| `DEBUG` | Modo de desenvolvimento | `True` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula | `127.0.0.1,localhost` |

## Perfis e permissões

| Perfil | Acesso principal | Pode fazer |
|---|---|---|
| Recepção | `/agendamento.app/recepcao/` | Ver agendados e histórico |
| Central | `/agendamento.app/central/` | Agendar, editar e remarcar |
| Profissional | `/agendamento.app/profissional/` | Grade, calendário, status e remarcação |
| Admin | `/admin/` | Aprovar cadastros e administrar dados |

## Fluxo de agendamento

1. O profissional cadastra uma grade (data específica ou semanal) e define o
   intervalo entre atendimentos.
2. A central escolhe o profissional na página **Novo agendamento**.
3. O sistema lista os dias com vaga e os horários livres, já no intervalo
   configurado.
4. A central clica no horário desejado e confirma os dados do cliente no modal.
5. O sistema valida a disponibilidade, calcula o horário final e grava o
   agendamento.
6. O profissional acompanha o atendimento no painel e no calendário.
7. Se necessário, a central ou o profissional remarcam para outro horário livre.

## Testes

```bash
poetry run python manage.py check
poetry run python manage.py test control
```

A suíte cobre models, constraints, geração de horários, autenticação, cadastro,
permissões, calendário, agendamento pela central, remarcação e histórico.

## Docker

Os arquivos `Dockerfile` e `docker-compose.yaml` estão preparados, mas o Docker
será utilizado apenas na etapa final de implantação no servidor. Antes de subir
em produção, ainda é necessário finalizar a configuração do PostgreSQL e da
variável `DATABASE_URL`, definir `ALLOWED_HOSTS`, usar `DEBUG=False`, coletar os
arquivos estáticos e executar a aplicação com um servidor WSGI adequado.

## Destaques de desenvolvimento

- Migração completa do Flask para Django, mantendo o app antigo em
  `app_antigo/` apenas como referência.
- Modelagem com `Profile` OneToOne, grupos nativos do Django e data migrations
  para criação dos grupos e padronização dos status.
- Constraints de integridade para grades e para impedir double-booking.
- Serviço centralizado de geração de horários, com suporte a grades fixas,
  semanais e intervalos personalizados.
- Fluxo de agendamento por profissional, sem escolha manual de data pela
  central.
- Calendário mensal clicável no painel do profissional, com navegação entre
  meses e agenda do dia.
- Remarcação com contador e badges `Remarcado` / `RemarcadoNx`.
- Cadastro com perfil pendente e aprovação pelo admin.
- Interface responsiva em Bootstrap 5 dark, com tema verde `#00a859`, ícones,
  mensagens, estados vazios e páginas de erro personalizadas.
- 34 testes automatizados cobrindo os fluxos principais.

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).
