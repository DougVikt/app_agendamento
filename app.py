import sqlite3
import os
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect

app = Flask(__name__)
app.secret_key = 'agenda2026secret'
VERSAO = "v1.0"

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
        CREATE TABLE IF NOT EXISTS pedagogicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedagogico_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            intervalo INTEGER DEFAULT 30,
            recorrente INTEGER DEFAULT 0,
            dia_semana INTEGER DEFAULT 0,
            FOREIGN KEY (pedagogico_id) REFERENCES pedagogicos(id)
        );
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedagogico_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            aluno TEXT NOT NULL,
            matricula TEXT NOT NULL DEFAULT '',
            telefone TEXT NOT NULL DEFAULT '',
            observacoes TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Agendado',
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (pedagogico_id) REFERENCES pedagogicos(id)
        );
    """)
    for col in ['matricula', 'status', 'telefone', 'observacoes']:
        try: conn.execute(f"ALTER TABLE agendamentos ADD COLUMN {col} TEXT DEFAULT ''")
        except: pass
    for col in ['recorrente', 'dia_semana']:
        try: conn.execute(f"ALTER TABLE horarios ADD COLUMN {col} INTEGER DEFAULT 0")
        except: pass
    try:
        conn.execute("UPDATE agendamentos SET status='Agendado' WHERE status IS NULL OR status=''")
        conn.commit()
    except: pass
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

def slots_disponiveis(pedagogico_id, data):
    conn = get_db()
    dt = datetime.datetime.strptime(data, "%Y-%m-%d").date()
    horarios = conn.execute(
        "SELECT * FROM horarios WHERE pedagogico_id=? AND (data=? OR (recorrente=1 AND dia_semana=?))",
        (pedagogico_id, data, dt.weekday())
    ).fetchall()
    if not horarios:
        conn.close()
        return []
    todos = set()
    for hor in horarios:
        for s in gerar_slots(hor["hora_inicio"], hor["hora_fim"], hor["intervalo"]):
            todos.add(s)
    agendados = conn.execute(
        "SELECT hora_inicio FROM agendamentos WHERE pedagogico_id=? AND data=? AND status='Agendado'",
        (pedagogico_id, data)
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
def pagina_login():
    return render_template("index.html", versao=VERSAO)

@app.route("/login/central", methods=["GET", "POST"])
def login_central():
    if request.method == "POST":
        session["user"] = "Central"
        session["role"] = "central"
        return redirect("/central")
    return render_template("acesso_central.html", versao=VERSAO)

@app.route("/login/pedagogico", methods=["GET", "POST"])
def login_pedagogico():
    if request.method == "POST":
        n = request.form.get("nome", "").strip()
        if n:
            session["user"] = n
            session["role"] = "pedagogico"
            return redirect("/pedagogico")
        return redirect("/login/pedagogico")
    return render_template("acesso_pedagogico.html", versao=VERSAO)

@app.route("/pedagogico")
def pagina_pedagogico():
    if session.get("role") != "pedagogico": return redirect("/admin")
    return render_template("pedagogico.html", nome=session.get("user"), versao=VERSAO)

@app.route("/central")
def pagina_central():
    if session.get("role") != "central": return redirect("/admin")
    return render_template("central.html", versao=VERSAO)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")

@app.route("/historico")
def pagina_historico():
    return render_template("historico.html", versao=VERSAO)

# ---------------------------------------------------------------------------
# API - PEDAGOGICOS
# ---------------------------------------------------------------------------
@app.route("/api/pedagogicos", methods=["GET"])
def listar_pedagogicos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM pedagogicos ORDER BY nome").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/pedagogicos", methods=["POST"])
def criar_pedagogico():
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO pedagogicos (nome) VALUES (?)", (nome,))
        conn.commit()
        id_ = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"id": id_, "nome": nome}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe"}), 400

@app.route("/api/pedagogicos/<int:id_>", methods=["PATCH"])
def renomear_pedagogico(id_):
    dados = request.get_json()
    nome = dados.get("nome", "").strip()
    if not nome: return jsonify({"erro": "Nome obrigatorio"}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE pedagogicos SET nome=? WHERE id=?", (nome, id_))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "nome": nome})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "Ja existe um colaborador com esse nome"}), 400

@app.route("/api/pedagogicos/<int:id_>", methods=["DELETE"])
def remover_pedagogico(id_):
    conn = get_db()
    conn.execute("DELETE FROM horarios WHERE pedagogico_id=?", (id_,))
    conn.execute("DELETE FROM agendamentos WHERE pedagogico_id=?", (id_,))
    conn.execute("DELETE FROM pedagogicos WHERE id=?", (id_,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# API - HORARIOS
# ---------------------------------------------------------------------------
@app.route("/api/horarios/<int:pid>", methods=["GET"])
def listar_horarios(pid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM horarios WHERE pedagogico_id=? ORDER BY data, hora_inicio", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/horarios", methods=["POST"])
def criar_horario():
    d = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO horarios (pedagogico_id, data, hora_inicio, hora_fim, intervalo, recorrente, dia_semana) VALUES (?,?,?,?,?,?,?)",
        (d["pedagogico_id"], d.get("data",""), d["hora_inicio"], d["hora_fim"], d.get("intervalo", 30),
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
        "SELECT DISTINCT data FROM horarios WHERE pedagogico_id=? AND data >= date('now') AND (recorrente=0 OR recorrente IS NULL) ORDER BY data",
        (pid,)
    ).fetchall()
    datas = set(r["data"] for r in rows)
    rec = conn.execute(
        "SELECT DISTINCT dia_semana FROM horarios WHERE pedagogico_id=? AND recorrente=1",
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
    pid = request.args.get("pedagogico_id")
    data = request.args.get("data")
    if not (pid and data): return jsonify({"erro": "faltam parametros"}), 400
    return jsonify(slots_disponiveis(int(pid), data))

# ---------------------------------------------------------------------------
# API - AGENDAMENTOS
# ---------------------------------------------------------------------------
@app.route("/api/agendamentos", methods=["GET"])
def listar_agendamentos():
    pid = request.args.get("pedagogico_id")
    status = request.args.get("status")
    data = request.args.get("data")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    sql = """SELECT a.*, p.nome as pedagogico_nome FROM agendamentos a
             JOIN pedagogicos p ON a.pedagogico_id = p.id WHERE 1=1"""
    params = []
    if pid: sql += " AND a.pedagogico_id = ?"; params.append(int(pid))
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
    aluno = d.get("aluno", "").strip()
    tipo = d.get("tipo", "").strip()
    if not aluno: return jsonify({"erro": "Nome do aluno obrigatorio"}), 400
    if not tipo: return jsonify({"erro": "Tipo de atendimento obrigatorio"}), 400
    slots = slots_disponiveis(d["pedagogico_id"], d["data"])
    if d["hora_inicio"] not in slots: return jsonify({"erro": "Horario indisponivel"}), 409
    conn = get_db()
    dt_base = datetime.datetime.strptime(d["data"], "%Y-%m-%d").date()
    hor = conn.execute(
        "SELECT intervalo FROM horarios WHERE pedagogico_id=? AND (data=? OR (recorrente=1 AND dia_semana=?)) AND hora_inicio <= ? AND hora_fim > ? LIMIT 1",
        (d["pedagogico_id"], d["data"], dt_base.weekday(), d["hora_inicio"], d["hora_inicio"])
    ).fetchone()
    if not hor: conn.close(); return jsonify({"erro": "Horario base nao encontrado"}), 404
    h_fim = (datetime.datetime.strptime(d["hora_inicio"], "%H:%M") +
             datetime.timedelta(minutes=hor["intervalo"])).strftime("%H:%M")
    conn.execute(
        "INSERT INTO agendamentos (pedagogico_id, tipo, aluno, matricula, telefone, observacoes, data, hora_inicio, hora_fim) VALUES (?,?,?,?,?,?,?,?,?)",
        (d["pedagogico_id"], tipo, aluno, d.get("matricula",""), d.get("telefone",""), d.get("observacoes",""), d["data"], d["hora_inicio"], h_fim)
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
    for col in ['aluno','matricula','telefone','tipo','observacoes']:
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
# BACKUP MANUAL
# ---------------------------------------------------------------------------
import shutil
@app.route("/api/backup", methods=["POST"])
def api_backup():
    try:
        bk = DB_PATH.replace(".db", f".bak")
        shutil.copy2(DB_PATH, bk)
        return jsonify({"ok": True, "arquivo": bk})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"SERVIDOR: http://0.0.0.0:5000 | Database: {DB_PATH}")
    app.run(host="0.0.0.0", port=5000, debug=False)
