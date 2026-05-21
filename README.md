# Sistema de Agendamentos

## 📋 Visão Geral

Sistema web completo para gerenciamento de agendamentos desenvolvido com Python/Flask. O projeto permite agendamento de serviços/consultas com suporte a múltiplos usuários (administradores, professores/pessoal técnico e alunos/usuários finais), controle de horários, recorrência de eventos e histórico de atendimentos.

Este sistema também implementa recursos de **Progressive Web App (PWA)**, permitindo instalação em dispositivos móveis e desktop para uso offline ou como aplicativo nativo.

## 🚀 Funcionalidades Principais

- **Gestão de Usuários**: Administradores, professores/pessoal técnico
- **Cadastro de Profissionais**: Registro de pedagogicos/profissionais disponíveis
- **Gerenciamento de Horários**: Definição de disponibilidade com suporte a horários recorrentes
- **Sistema de Agendamento**: Reserva de horários com verificação de disponibilidade em tempo real
- **Controle de Status**: Agendamentos podem ser marcados como Atendido, Ausente ou Cancelado
- **Histórico Completo**: Visualização de todos os agendamentos realizados
- **Backup Automático**: Funcionalidade de backup manual do banco de dados
- **Interface Responsiva**: Templates HTML com Bootstrap para excelente experiência em dispositivos móveis e desktop
- **Progressive Web App (PWA)**: Instalável como aplicativo nativo com suporte offline
- **Tema Escuro**: Interface com tema escuro personalizável
- **Manifest e Service Worker**: Configuração completa para experiência PWA

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.x, Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Banco de Dados**: SQLite
- **PWA**: Service Worker, Web Manifest, HTTPS (para produção)
- **Outras Bibliotecas**: 
  - `sqlite3` (padrão do Python)
  - `shutil` (para funcionalidade de backup)

## 📁 Estrutura do Projeto

```
agendamento/
├── app.py                 # Aplicação principal Flask
├── templates/             # Templates HTML
│   ├── index.html         # Página de login/admin
│   ├── landing.html       # Página inicial pública
│   ├── acesso_central.html # Login da central
│   ├── acesso_pedagogico.html # Login do professor
│   ├── central.html       # Dashboard da central
│   ├── pedagogico.html    # Interface do professor
│   └── historico.html     # Página de histórico
├── static/                # Arquivos estáticos
│   ├── icon.svg           # Ícone do aplicativo
│   ├── manifest.json      # Manifest do PWA
│   ├── manifest-pedagogico.json # Manifest específico para professores
│   ├── manifest-central.json # Manifest específico para central
│   └── sw.js              # Service Worker para PWA
├── .gitignore             # Arquivos ignorados pelo Git
├── .gitattributes         # Configurações do Git
├── ci.ps1                 # Script de integração contínua PowerShell
└── README.md              # Este arquivo
```

## ⚙️ Instalação e Configuração

### Pré-requisitos

- Python 3.6 ou superior
- pip (gerenciador de pacotes do Python)

### Passo a Passo

1. **Clone o repositório** (se aplicável):
   ```bash
   git clone [URL-do-repositório]
   cd agendamento
   ```

2. **Crie um ambiente virtual** (recomendado):
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install flask
   ```

4. **Inicialize o banco de dados**:
   O banco de dados SQLite será criado automaticamente na primeira execução.

5. **Execute a aplicação**:
   ```bash
   python app.py
   ```

6. **Acesse no navegador**:
   - URL principal: `http://localhost:5000`
   - Painel administrativo: `http://localhost:5000/admin`

7. **Instale como PWA** (opcional):
   - No navegador Chrome/Edge: Clique no ícone de instalação na barra de endereços
   - No Firefox: Use o menu > Mais ferramentas > Criar atalho...
   - Em dispositivos móveis: Use o menu do navegador > "Instalar aplicativo"

## 🔧 Variáveis de Ambiente

- `AGENDA_DB`: Define o caminho personalizado para o arquivo do banco de dados SQLite
  ```bash
  set AGENDA_DB=C:\caminho\para\seu\banco.db  # Windows
  export AGENDA_DB=/caminho/para/seu/banco.db  # Linux/Mac
  ```

Se não definida, o banco será criado como `.agenda.db` no diretório do projeto.

## 📖 Uso

### Para Administradores/Central

1. Acesse `http://localhost:5000/admin`
2. Faça login usando as opções disponíveis (pode ser configurado conforme necessário)
3. Gerencie professores/pessoal técnico através da interface
4. Visualize e controle todos os agendamentos
5. Acesse o histórico de atendimentos
6. Instale como PWA para acesso rápido na área de trabalho

### Para Professores/Pessoal Técnico

1. Acesse `http://localhost:5000/login/pedagogico`
2. Faça login com seu nome cadastrado
3. Visualize seus horários disponíveis
4. Gerencie seus próprios agendamentos
5. Atualize o status dos atendimentos (Atendido, Ausente, Cancelado)
6. Use o aplicativo instalado para acesso rápido aos seus horários

### Para Usuários Finais (Alunos/Clientes)

1. Acesse a página inicial `http://localhost:5000`
2. Visualize informações gerais sobre o serviço
3. Redirecionado para o login apropriado conforme seu tipo de usuário
4. Instale como PWA para facilitar futuros acessos

## 🗄️ Banco de Dados

O sistema utiliza SQLite com as seguintes tabelas principais:

- **pedagogicos**: Armazena informações dos professores/pessoal técnico
- **horarios**: Define a disponibilidade de horários (com suporte a recorrência)
- **agendamentos**: Registra todos os agendamentos feitos

O arquivo do banco de dados é criado automaticamente como `.agenda.db` no diretório raiz do projeto (ou conforme definido pela variável de ambiente `AGENDA_DB`).

## 🔒 Segurança

- Sessões Flask com chave secreta definida
- Validação de dados nos endpoints da API
- Proteção contra inserções duplicadas (professores com mesmo nome)
- Verificação de disponibilidade de horários antes do agendamento
- Sanitização básica de entradas de texto
- Headers de segurança básicos implementados

## 📱 Responsividade e PWA

A interface é totalmente responsiva, adaptando-se a diferentes tamanhos de tela:
- Desktop: Layout completo com navegação lateral
- Tablet: Menu adaptável e otimização de espaço
- Mobile: Visualização em coluna única com menus hamburger

**Recursos PWA incluem:**
- ✅ Instalável como aplicativo nativo
- ✅ Funcionamento offline limitado (páginas básicas)
- ✅ Ícones adaptáveis para diferentes resoluções
- ✅ Tema de cor personalizado (#00a859 - verde esmeralda)
- ✅ Modo standalone (sem barra de endereços do navegador)
- ✅ Service Worker para cache de assets essenciais

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

Para questões, sugestões ou relatos de problemas, por favor abra uma issue neste repositório.

## 🙏 Agradecimentos

- Comunidade Flask por fornecer um excelente framework web
- Equipe do Bootstrap pelos componentes UI responsivos
- Comunidade PWA pelos padrões e melhores práticas
- Todos os contribuidores que ajudaram a melhorar este projeto

---

**Versão**: v1.0  
**Última atualização**: Maio 2026  
**Desenvolvido com**: Python & Flask  
**Recursos PWA**: Service Worker, Web Manifest, Design Responsivo