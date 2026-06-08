import sqlite3
from pathlib import Path
import os
import hashlib
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect

app = Flask(__name__)
app.secret_key = 'agenda2026secret'
VERSAO = "v2.7"

DB_PATH = os.environ.get("AGENDA_DB") or os.path.join(os.path.dirname(__file__), '.agenda.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS colaborador (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS atendimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            intervalo INTEGER DEFAULT 30,
            recorrente INTEGER DEFAULT 0,
            dia_semana INTEGER DEFAULT 0,
            FOREIGN KEY (colaborador_id) REFERENCES colaborador(id)
        );
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            cliente TEXT NOT NULL,
            cpf TEXT NOT NULL DEFAULT '',
            telefone TEXT NOT NULL DEFAULT '',
            observacoes TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Agendado',
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            atendimento_user TEXT DEFAULT '',
            FOREIGN KEY (colaborador_id) REFERENCES colaborador(id)
        );
        CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data);
        CREATE INDEX IF NOT EXISTS idx_agendamentos_colaborador ON agendamentos(colaborador_id);
        CREATE INDEX IF NOT EXISTS idx_agendamentos_status ON agendamentos(status);
        CREATE INDEX IF NOT EXISTS idx_horarios_colaborador ON horarios(colaborador_id);
    """)
    for col in ['cpf', 'status', 'telefone', 'observacoes', 'atendimento_user']:
        try: conn.execute(f"ALTER TABLE agendamentos ADD COLUMN {col} TEXT DEFAULT ''")
        except: pass
    for col in ['recorrente', 'dia_semana']:
        try: conn.execute(f"ALTER TABLE horarios ADD COLUMN {col} INTEGER DEFAULT 0")
        except: pass
    try:
        conn.execute("UPDATE agendamentos SET status='Agendado' WHERE status IS NULL OR status=''")
        conn.commit()
    except: pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    if not conn.execute("SELECT 1 FROM config WHERE key='admin_user'").fetchone():
        conn.execute("INSERT INTO config (key, value) VALUES ('admin_user', 'admin')")
        conn.execute("INSERT INTO config (key, value) VALUES ('admin_pass', ?)",
                     (hashlib.sha256('admin'.encode()).hexdigest(),))
        conn.commit()
    conn.commit()
    conn.close()

init_db()

def gerar_slots(h_inicio, h_fim, intervalo):
    slots = []
    atual = datetime.datetime.strptime(h_inicio, "%H:%M")
    fim = datetime.datetime.strptime(h_fim, "%H:%M")
    while atual < fim:
        prox = atual + datetime.timedelta(minutes=intervalo)
        if prox > fim: break
        slots.append(atual.strftime("%H:%M"))
        atual = prox
    return slots

def slots_disponiveis(colaborador_id, data):
    conn = get_db()
    dt = datetime.datetime.strptime(data, "%Y-%m-%d").date()
    horarios = conn.execute(
        "SELECT * FROM horarios WHERE colaborador_id=? AND (data=? OR (recorrente=1 AND dia_semana=?))",
        (colaborador_id, data, dt.weekday())
    ).fetchall()
    if not horarios:
        conn.close()
        return []
    todos = set()
    for hor in horarios:
        for s in gerar_slots(hor["hora_inicio"], hor["hora_fim"], hor["intervalo"]):
            todos.add(s)
    agendados = conn.execute(
        "SELECT hora_inicio FROM agendamentos WHERE colaborador_id=? AND data=? AND status='Agendado'",
        (colaborador_id, data)
    ).fetchall()
    conn.close()
    ocupados = set(r["hora_inicio"] for r in agendados)
    hoje = datetime.date.today()
    agora = datetime.datetime.now().strftime("%H:%M")
    disp = []
    for s in sorted(todos):
        dt = datetime.datetime.strptime(data, "%Y-%m-%d").date()
        if dt < hoje: continue
        if dt == hoje and s <= agora: continue
        if s not in ocupados: disp.append(s)
    return disp

# ---------------------------------------------------------------------------
# ROTAS - PAGINAS
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("landing.html", versao=VERSAO)

@app.route("/admin", methods=["GET"])
def pagina_admin():
    if not session.get("admin_logged"):
        return render_template("login_admin.html", versao=VERSAO)
    return render_template("index.html", versao=VERSAO)

@app.route("/admin/login", methods=["POST"])
def admin_login():
    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "").strip()
    conn = get_db()
    user_db = conn.execute("SELECT value FROM config WHERE key='admin_user'").fetchone()
    pass_db = conn.execute("SELECT value FROM config WHERE key='admin_pass'").fetchone()
    conn.close()
    if user_db and pass_db and usuario == user_db[0] and hashlib.sha256(senha.encode()).hexdigest() == pass_db[0]:
        session["admin_logged"] = True
        return redirect("/admin")
    return render_template("login_admin.html", versao=VERSAO, erro="Usuario ou senha incorretos")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged", None)
    return redirect("/admin")

@app.route("/inicio_atendimento", methods=["GET", "POST"])
def login_atendimento():
    if request.method == "POST":
        session["user"] = "atendimento"
        session["role"] = "atendimento"
        return redirect("/atendimento")
    return render_template("acesso_atendimento.html", versao=VERSAO)

@app.route("/inicio_colaborador", methods=["GET", "POST"])
def login_colaborador():
    if request.method == "POST":
        n = request.form.get("nome", "").strip()
        if n:
            session["user"] = n
            session["role"] = "colaborador"
            return redirect("/colaborador")
        return redirect("/inicio_colaborador")
    return render_template("acesso_colaborador.html", versao=VERSAO)

@app.route("/colaborador")
def pagina_colaborador():
    if session.get("role") != "colaborador": return redirect("/inicio_colaborador")
    return render_template("colaborador.html", nome=session.get("user"), versao=VERSAO)

@app.route("/atendimento")
def pagina_atendimento():
    if session.get("role") != "atendimento": return redirect("/inicio_atendimento")
    return render_template("atendimento.html", versao=VERSAO)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")

@app.route("/sw.js")
def service_worker():
    return app.send_static_file("sw.js")

@app.route("/historico")
def pagina_historico():
    role = session.get("role")
    if not role and session.get("admin_logged"):
        role = "admin"
    return render_template("historico.html", versao=VERSAO, role=role)

# ---------------------------------------------------------------------------
# API - colaborador
# ---------------------------------------------------------------------------
@app.route("/api/colaborador", methods=["GET"])
def listar_colaborador():
    conn = get_db()
    rows = conn.execute("SELECT * FROM colaborador ORDER BY nome").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/colaborador", methods=["POST"])
def criar_colaborador():
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO colaborador (nome) VALUES (?)", (nome,))
        conn.commit()
        id_ = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"id": id_, "nome": nome}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe"}), 400

@app.route("/api/colaborador/<int:id_>", methods=["PATCH"])
def renomear_colaborador(id_):
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE colaborador SET nome=? WHERE id=?", (nome, id_))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "nome": nome})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe um colaborador com esse nome"}), 400

@app.route("/api/colaborador/<int:id_>", methods=["DELETE"])
def remover_colaborador(id_):
    conn = get_db()
    conn.execute("DELETE FROM horarios WHERE colaborador_id=?", (id_,))
    conn.execute("DELETE FROM agendamentos WHERE colaborador_id=?", (id_,))
    conn.execute("DELETE FROM colaborador WHERE id=?", (id_,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# API - ATENDIMENTO
# ---------------------------------------------------------------------------
@app.route("/api/atendimento", methods=["GET"])
def listar_atendimento():
    conn = get_db()
    rows = conn.execute("SELECT * FROM atendimento ORDER BY nome").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/atendimento", methods=["POST"])
def criar_atendimento():
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO atendimento (nome) VALUES (?)", (nome,))
        conn.commit()
        id_ = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"id": id_, "nome": nome}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe"}), 400

@app.route("/api/atendimento/<int:id_>", methods=["PATCH"])
def renomear_atendimento(id_):
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE atendimento SET nome=? WHERE id=?", (nome, id_))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "nome": nome})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe"}), 400

@app.route("/api/atendimento/<int:id_>", methods=["DELETE"])
def remover_atendimento(id_):
    conn = get_db()
    conn.execute("DELETE FROM atendimento WHERE id=?", (id_,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# API - HORARIOS
# ---------------------------------------------------------------------------
@app.route("/api/horarios/<int:pid>", methods=["GET"])
def listar_horarios(pid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM horarios WHERE colaborador_id=? ORDER BY data, hora_inicio", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/horarios", methods=["POST"])
def criar_horario():
    d = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO horarios (colaborador_id, data, hora_inicio, hora_fim, intervalo, recorrente, dia_semana) VALUES (?,?,?,?,?,?,?)",
        (d["colaborador_id"], d.get("data",""), d["hora_inicio"], d["hora_fim"], d.get("intervalo", 30),
         d.get("recorrente", 0), d.get("dia_semana", 0))
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True}), 201

@app.route("/api/horarios/<int:id_>", methods=["DELETE"])
def remover_horario(id_):
    conn = get_db()
    conn.execute("DELETE FROM horarios WHERE id=?", (id_,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# API - SLOTS
# ---------------------------------------------------------------------------
@app.route("/api/datas/<int:pid>", methods=["GET"])
def api_datas(pid):
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT data FROM horarios WHERE colaborador_id=? AND data >= date('now') AND (recorrente=0 OR recorrente IS NULL) ORDER BY data",
        (pid,)
    ).fetchall()
    datas = set(r["data"] for r in rows)
    rec = conn.execute(
        "SELECT DISTINCT dia_semana FROM horarios WHERE colaborador_id=? AND recorrente=1",
        (pid,)
    ).fetchall()
    conn.close()
    if rec:
        hoje = datetime.date.today()
        dias = set(r["dia_semana"] for r in rec)
        for i in range(60):
            d = hoje + datetime.timedelta(days=i)
            if d.weekday() in dias:
                datas.add(d.strftime("%Y-%m-%d"))
    return jsonify(sorted(datas))

@app.route("/api/slots", methods=["GET"])
def api_slots():
    pid = request.args.get("colaborador_id")
    data = request.args.get("data")
    if not (pid and data): return jsonify({"erro": "faltam parametros"}), 400
    return jsonify(slots_disponiveis(int(pid), data))

# ---------------------------------------------------------------------------
# API - AGENDAMENTOS
# ---------------------------------------------------------------------------
@app.route("/api/agendamentos", methods=["GET"])
def listar_agendamentos():
    pid = request.args.get("colaborador_id")
    status = request.args.get("status")
    data = request.args.get("data")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    sql = """SELECT a.*, p.nome as colaborador_nome FROM agendamentos a
             JOIN colaborador p ON a.colaborador_id = p.id WHERE 1=1"""
    params = []
    if pid: sql += " AND a.colaborador_id = ?"; params.append(int(pid))
    if data: sql += " AND a.data = ?"; params.append(data)
    if data_inicio: sql += " AND a.data >= ?"; params.append(data_inicio)
    if data_fim: sql += " AND a.data <= ?"; params.append(data_fim)
    if status:
        if status == "pendentes": sql += " AND a.status='Agendado' AND a.data < date('now')"
        else: sql += " AND a.status = ?"; params.append(status)
    sql += " ORDER BY a.data DESC, a.hora_inicio DESC"
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/agendamentos", methods=["POST"])
def criar_agendamento():
    d = request.get_json()
    cliente = d.get("cliente", "").strip()
    tipo = d.get("tipo", "").strip()
    atendimento_user = d.get("atendimento_user", "").strip()
    if not cliente: return jsonify({"erro": "Nome do cliente obrigatorio"}), 400
    if not tipo: return jsonify({"erro": "Tipo de atendimento obrigatorio"}), 400
    if not atendimento_user: return jsonify({"erro": "Responsavel pelo agendamento obrigatorio"}), 400
    slots = slots_disponiveis(d["colaborador_id"], d["data"])
    if d["hora_inicio"] not in slots: return jsonify({"erro": "Horario indisponivel"}), 409
    conn = get_db()
    dt_base = datetime.datetime.strptime(d["data"], "%Y-%m-%d").date()
    hor = conn.execute(
        "SELECT intervalo FROM horarios WHERE colaborador_id=? AND (data=? OR (recorrente=1 AND dia_semana=?)) AND hora_inicio <= ? AND hora_fim > ? LIMIT 1",
        (d["colaborador_id"], d["data"], dt_base.weekday(), d["hora_inicio"], d["hora_inicio"])
    ).fetchone()
    if not hor: conn.close(); return jsonify({"erro": "Horario base nao encontrado"}), 404
    h_fim = (datetime.datetime.strptime(d["hora_inicio"], "%H:%M") +
             datetime.timedelta(minutes=hor["intervalo"])).strftime("%H:%M")
    conn.execute(
        "INSERT INTO agendamentos (colaborador_id, tipo, cliente, cpf, telefone, observacoes, data, hora_inicio, hora_fim, atendimento_user) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (d["colaborador_id"], tipo, cliente, d.get("cpf",""), d.get("telefone",""), d.get("observacoes",""), d["data"], d["hora_inicio"], h_fim, atendimento_user)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True}), 201

@app.route("/api/agendamentos/<int:id_>/status", methods=["PATCH"])
def atualizar_status(id_):
    d = request.get_json()
    ns = d.get("status","").strip()
    if ns not in ("Atendido","Ausente","Cancelado"): return jsonify({"erro":"Status invalido"}),400
    conn = get_db()
    conn.execute("UPDATE agendamentos SET status=? WHERE id=?", (ns, id_))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/agendamentos/<int:id_>", methods=["PATCH"])
def editar_agendamento(id_):
    d = request.get_json()
    campos = []
    params = []
    for col in ['cliente','cpf','telefone','tipo','observacoes']:
        if col in d:
            campos.append(f"{col}=?")
            params.append(d[col].strip() if isinstance(d[col],str) else d[col])
    if not campos: return jsonify({"erro":"Nenhum campo para alterar"}),400
    params.append(id_)
    conn = get_db()
    conn.execute(f"UPDATE agendamentos SET {', '.join(campos)} WHERE id=?", params)
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/agendamentos/<int:id_>", methods=["DELETE"])
def cancelar_agendamento(id_):
    conn = get_db()
    conn.execute("DELETE FROM agendamentos WHERE id=?", (id_,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# API - STATS / DASHBOARD
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def api_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM agendamentos").fetchone()[0]
    hoje = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE data = date('now')").fetchone()[0]
    semana = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE data >= date('now', '-7 days') AND data <= date('now')").fetchone()[0]
    por_status = conn.execute("SELECT status, COUNT(*) as qtd FROM agendamentos GROUP BY status ORDER BY qtd DESC").fetchall()
    por_colaborador = conn.execute(
        "SELECT p.nome, COUNT(*) as qtd FROM agendamentos a JOIN colaborador p ON a.colaborador_id = p.id GROUP BY a.colaborador_id ORDER BY qtd DESC"
    ).fetchall()
    conn.close()
    return jsonify({
        "total": total,
        "hoje": hoje,
        "semana": semana,
        "por_status": [dict(r) for r in por_status],
        "por_colaborador": [dict(r) for r in por_colaborador]
    })

# ---------------------------------------------------------------------------
# API - ADMIN CREDENTIALS
# ---------------------------------------------------------------------------
@app.route("/api/admin/change-credentials", methods=["POST"])
def change_credentials():
    if not session.get("admin_logged"):
        return jsonify({"erro": "Nao autorizado"}), 401
    d = request.get_json()
    usuario_atual = d.get("usuario_atual", "").strip()
    senha_atual = d.get("senha_atual", "").strip()
    novo_usuario = d.get("novo_usuario", "").strip()
    nova_senha = d.get("nova_senha", "").strip()
    if not usuario_atual or not senha_atual:
        return jsonify({"erro": "Preencha usuario e senha atual"}), 400
    if not novo_usuario or not nova_senha:
        return jsonify({"erro": "Preencha novo usuario e nova senha"}), 400
    if len(nova_senha) < 4:
        return jsonify({"erro": "Nova senha deve ter pelo menos 4 caracteres"}), 400
    conn = get_db()
    user_db = conn.execute("SELECT value FROM config WHERE key='admin_user'").fetchone()
    pass_db = conn.execute("SELECT value FROM config WHERE key='admin_pass'").fetchone()
    if not user_db or not pass_db or usuario_atual != user_db[0] or hashlib.sha256(senha_atual.encode()).hexdigest() != pass_db[0]:
        conn.close()
        return jsonify({"erro": "Credenciais atuais incorretas"}), 400
    conn.execute("UPDATE config SET value=? WHERE key='admin_user'", (novo_usuario,))
    conn.execute("UPDATE config SET value=? WHERE key='admin_pass'", (hashlib.sha256(nova_senha.encode()).hexdigest(),))
    conn.commit(); conn.close()
    session["admin_logged"] = True
    return jsonify({"ok": True, "mensagem": "Credenciais alteradas com sucesso"})

# ---------------------------------------------------------------------------
# BACKUP MANUAL
# ---------------------------------------------------------------------------
import shutil
@app.route("/api/backup", methods=["POST"])
def api_backup():
    try:
        bk_path = Path("Backup")
        bk_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M")
        bk_name = Path(DB_PATH).stem + f"_{timestamp}.db"
        bk_dest = bk_path / bk_name

        shutil.copy2(DB_PATH, bk_dest)
        return jsonify({"ok": True, "arquivo": str(bk_dest)})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"SERVIDOR: http://0.0.0.0:5000 | Database: {DB_PATH}")
    app.run(host="0.0.0.0", port=5000, debug=False)
