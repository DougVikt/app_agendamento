# Sistema de Agendamento

Sistema web completo para gerenciamento de agendamentos desenvolvido com Python/Flask. Permite que a central de atendimento agende horarios com colaboradores, que cada colaborador gerencie sua propria agenda, e que administradores tenham controle total sobre os dados.

Inclui recursos de **Progressive Web App (PWA)**, permitindo instalacao em dispositivos moveis e desktop.

## Funcionalidades

### Central de Atendimento
- Agendamento de horarios com colaboradores
- Selecao de data e horarios disponiveis em tempo real
- Cadastro de dados do cliente (nome, CPF, telefone, observacoes)
- Visualizacao e cancelamento de agendamentos

### Colaborador
- Cadastro de horarios disponiveis (data unica ou recorrencia semanal)
- Visualizacao em calendario dos dias com agendamentos
- Controle de status dos atendimentos (Atendido, Ausente, Cancelado)
- Notificacao de agendamentos pendentes

### Administracao
- **Gerenciar Colaboradores**: Cadastrar, editar e excluir colaboradores
- **Gerenciar Horarios**: Visualizar e excluir horarios de qualquer colaborador
- **Gerenciar Agendamentos**: Filtrar por periodo, status e colaborador; editar ou excluir
- **Dashboard**: Estatisticas com totais, agendamentos hoje, ultimos 7 dias, por status e por colaborador
- **Historico**: Consulta de atendimentos concluidos
- **Backup**: Exportacao manual do banco de dados
- **Autenticacao**: Login protegido com credenciais alteraveis

## Tecnologias

- **Backend**: Python 3.x, Flask
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Banco de Dados**: SQLite
- **PWA**: Service Worker, Web Manifest

## Estrutura

```
app_agendamento/
├── app.py                        # Aplicacao principal Flask
├── templates/
│   ├── index.html                # Painel administrativo
│   ├── login_admin.html          # Login do admin
│   ├── landing.html              # Pagina inicial
│   ├── acesso_atendimento.html   # Login da central de atendimento
│   ├── acesso_colaborador.html   # Login do colaborador
│   ├── atendimento.html          # Central de atendimento
│   ├── colaborador.html          # Painel do colaborador
│   └── historico.html            # Historico de atendimentos
├── static/
│   ├── icon.svg
│   ├── manifest.json
│   ├── manifest-colaborador.json
│   ├── manifest-central.json
│   └── sw.js
├── backup.ps1                    # Script de backup mensal
├── .agenda.db                    # Banco de dados (criado automaticamente)
├── .gitignore
└── README.md
```

## Instalacao

### Pre-requisitos
- Python 3.6 ou superior
- pip

### Passos

1. Clone o repositorio:
   ```bash
   git clone <url>
   cd app_agendamento
   ```

2. Crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. Instale as dependencias:
   ```bash
   pip install flask
   ```

4. Execute:
   ```bash
   python app.py
   ```

5. Acesse no navegador:
   - Pagina inicial: `http://localhost:5000`
   - Painel admin: `http://localhost:5000/admin`

> O banco de dados SQLite e criado automaticamente na primeira execucao.

## Credenciais Padrao

| Acesso | Local | Credencial |
|---|---|---|
| Admin | `/admin` | `admin` / `admin` |
| Central | `/inicio_atendimento` | Acesso livre (1 clique) |
| Colaborador | `/inicio_colaborador` | Selecao do nome |

As credenciais de admin podem ser alteradas no proprio painel em "Alterar credenciais".

## Uso

### Admin
1. Acesse `/admin` e faca login com `admin` / `admin`
2. Gerencie colaboradores, horarios e agendamentos
3. Consulte estatisticas no Dashboard
4. Faca backup do banco de dados
5. Altere as credenciais de acesso pelo link no canto superior direito

### Central de Atendimento
1. Acesse a pagina inicial e clique em "Atendimento"
2. Selecione o colaborador e a data desejada
3. Escolha o horario disponivel e preencha os dados do cliente

### Colaborador
1. Acesse a pagina inicial e clique em "Colaborador"
2. Selecione seu nome ou cadastre-se como novo
3. Adicione seus horarios disponiveis (data unica ou semanal)
4. Acompanhe os agendamentos no calendario
5. Marque atendimentos como Atendido, Ausente ou Cancelado

## Banco de Dados

Tabelas principais:

- **config** — Armazena credenciais do admin (usuario e senha com hash SHA-256)
- **colaborador** — Dados dos colaboradores
- **horarios** — Disponibilidade de horarios (com suporte a recorrencia semanal)
- **agendamentos** — Registro de todos os agendamentos realizados

Variavel de ambiente `AGENDA_DB` permite definir caminho personalizado para o arquivo `.db`.

## API

### Endpoints principais

| Metodo | Rota | Descricao |
|---|---|---|
| GET | `/api/colaborador` | Lista colaboradores |
| POST | `/api/colaborador` | Cria colaborador |
| PATCH | `/api/colaborador/<id>` | Renomeia colaborador |
| DELETE | `/api/colaborador/<id>` | Exclui colaborador e dados relacionados |
| GET | `/api/atendimento` | Lista usuarios da central |
| POST | `/api/atendimento` | Cria usuario da central |
| PATCH | `/api/atendimento/<id>` | Renomeia usuario |
| DELETE | `/api/atendimento/<id>` | Remove usuario da central |
| GET | `/api/horarios/<id>` | Lista horarios de um colaborador |
| POST | `/api/horarios` | Cria horario |
| DELETE | `/api/horarios/<id>` | Exclui horario |
| GET | `/api/slots` | Retorna horarios disponiveis |
| GET | `/api/agendamentos` | Lista agendamentos (com filtros) |
| POST | `/api/agendamentos` | Cria agendamento |
| PATCH | `/api/agendamentos/<id>` | Edita agendamento |
| PATCH | `/api/agendamentos/<id>/status` | Atualiza status |
| DELETE | `/api/agendamentos/<id>` | Exclui agendamento |
| GET | `/api/stats` | Estatisticas do sistema |
| POST | `/api/backup` | Gera backup do banco |
| POST | `/api/admin/change-credentials` | Altera credenciais do admin |

## PWA

O sistema e instalavel como aplicativo nativo em dispositivos moveis e desktop:
- Chrome/Edge: clique no icone de instalacao na barra de enderecos
- Dispositivos moveis: menu do navegador > "Instalar aplicativo"

## Changelog

### [v2.5] - Mai 2026
**Tabela Atendimento e Rastreamento de Usuario**
- Adicionada tabela `atendimento` no banco de dados
- Coluna `atendimento_user` em agendamentos para registrar quem fez o agendamento
- Indices de performance (`idx_agendamentos_data`, `idx_agendamentos_colaborador`, `idx_agendamentos_status`, `idx_horarios_colaborador`)
- Endpoints CRUD `/api/atendimento` (GET, POST, PATCH, DELETE)
- Modal "Gerenciar Atendimento" no painel admin para cadastro/remocao de usuarios
- Select obrigatorio de responsavel no formulario de agendamento
- Exibicao do responsavel nos detalhes do colaborador
- Coluna Telefone com formatacao e filtro no historico
- Script `backup.ps1` para backup mensal

### [v2.1] - Mai 2026
**Autenticacao e Painel Administrativo**
- Login administrativo com credenciais armazenadas no banco (padrao: admin/admin)
- Pagina `login_admin.html` para autenticacao
- Dashboard com estatisticas (total, hoje, semana, por status, por colaborador)
- Modal "Gerenciar Horarios" para visualizar/excluir horarios de qualquer colaborador
- Filtros no modal de agendamentos (periodo, status, colaborador)
- Modal "Alterar Credenciais" no admin
- Botao de backup manual integrado ao painel
- Corrigido botao "Voltar" do historico para admin
- Rodape com versao padronizado em todas as paginas
- Testes CI para as novas funcionalidades

### [v2.0] - Mai 2026
**PWA e Refatoramento de Telas**
- Renomeacao de templates: `central` -> `atendimento`, `pedagogico` -> `colaborador`
- Progressive Web App (instalavel como aplicativo nativo)
- Manifests separados por perfil
- Tema escuro padrao
- Historico por perfil de acesso
- CI/CD basico com `ci.ps1`

## Licenca

MIT — veja o arquivo [LICENSE](LICENSE).
