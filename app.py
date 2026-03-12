"""
LaunchGate — app.py  (v2 — with NeuroVerse Quiz Portal integrated)
"""

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify, flash
)
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import hashlib
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "launchgate-secret-2026-x")
app.config["DATABASE"] = os.path.join(os.path.dirname(__file__), "launchgate.db")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

ADMIN_PASSKEY = os.environ.get("ADMIN_PASSKEY", "NEURO-2026-X")


def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'Untitled Document',
                content TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS vault_snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'python',
                code TEXT NOT NULL,
                description TEXT DEFAULT '',
                is_public INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                creator_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (creator_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL DEFAULT 'MCQ',
                correct_answer TEXT NOT NULL,
                marks INTEGER DEFAULT 1,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
            );
            CREATE TABLE IF NOT EXISTS quiz_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                index_label TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
            );
            CREATE TABLE IF NOT EXISTS quiz_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total_marks INTEGER DEFAULT 0,
                submitted_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                submitted_text TEXT,
                FOREIGN KEY (response_id) REFERENCES quiz_responses(id),
                FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
            );
        """)
    print("Database ready")


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def get_unread_count(user_id):
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE receiver_id=? AND is_read=0",
            (user_id,)
        ).fetchone()
    return row["cnt"] if row else 0


@app.template_filter('index_to_char')
def index_to_char(index):
    return chr(97 + int(index))


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            # API routes get a proper JSON 403
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Admin access required."}), 403
            # Page routes get a flash + redirect
            flash("Admin access required. Please log in with the admin passkey.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        passkey  = request.form.get("passkey", "").strip()
        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hash_password(password))
            ).fetchone()
        if not user:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        session["user_id"]  = user["id"]
        session["username"] = user["username"]
        # Always start as a regular user — admin is SESSION-ONLY via passkey
        session["is_admin"] = False
        if passkey and passkey == ADMIN_PASSKEY:
            session["is_admin"] = True
            flash("Admin access granted.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error"); return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error"); return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error"); return redirect(url_for("register"))
        try:
            with get_db() as db:
                db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)",
                           (username, email, hash_password(password)))
            flash("Account created! Please sign in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already taken.", "error"); return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        docs = db.execute(
            "SELECT * FROM documents WHERE user_id=? ORDER BY updated_at DESC LIMIT 10",
            (session["user_id"],)
        ).fetchall()
        snippets = db.execute(
            "SELECT v.*, u.username FROM vault_snippets v JOIN users u ON v.user_id=u.id WHERE v.is_public=1 ORDER BY v.created_at DESC LIMIT 6"
        ).fetchall()
        users  = db.execute(
            "SELECT id, username FROM users WHERE id!=? ORDER BY username", (session["user_id"],)
        ).fetchall()
        unread = get_unread_count(session["user_id"])
        available_quizzes = db.execute("SELECT COUNT(*) AS c FROM quizzes WHERE is_active=1").fetchone()["c"]
        my_quiz_attempts  = db.execute("SELECT COUNT(*) AS c FROM quiz_responses WHERE user_id=?", (session["user_id"],)).fetchone()["c"]
        recent_quizzes    = db.execute(
            "SELECT q.*, u.username AS creator_name FROM quizzes q JOIN users u ON q.creator_id=u.id WHERE q.is_active=1 ORDER BY q.created_at DESC LIMIT 3"
        ).fetchall()
    return render_template("dashboard.html",
        docs=docs, snippets=snippets, users=users, unread=unread,
        available_quizzes=available_quizzes, my_quiz_attempts=my_quiz_attempts,
        recent_quizzes=recent_quizzes)


@app.route("/editor")
@app.route("/editor/<int:doc_id>")
@login_required
def editor(doc_id=None):
    doc = None
    if doc_id:
        with get_db() as db:
            doc = db.execute("SELECT * FROM documents WHERE id=? AND user_id=?",
                             (doc_id, session["user_id"])).fetchone()
    unread = get_unread_count(session["user_id"])
    return render_template("editor.html", doc=doc, unread=unread)


@app.route("/api/document/save", methods=["POST"])
@login_required
def save_document():
    data    = request.get_json()
    title   = data.get("title", "Untitled Document")
    content = data.get("content", "")
    doc_id  = data.get("doc_id")
    now     = datetime.now().isoformat(timespec="seconds")
    with get_db() as db:
        if doc_id:
            db.execute("UPDATE documents SET title=?,content=?,updated_at=? WHERE id=? AND user_id=?",
                       (title, content, now, doc_id, session["user_id"]))
        else:
            cur = db.execute("INSERT INTO documents (user_id,title,content,updated_at) VALUES (?,?,?,?)",
                             (session["user_id"], title, content, now))
            doc_id = cur.lastrowid
    return jsonify({"ok": True, "doc_id": doc_id})


@app.route("/api/document/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id):
    with get_db() as db:
        db.execute("DELETE FROM documents WHERE id=? AND user_id=?", (doc_id, session["user_id"]))
    return jsonify({"ok": True})


@app.route("/vault")
@login_required
def vault():
    lang = request.args.get("lang", ""); search = request.args.get("q", "")
    with get_db() as db:
        query = "SELECT v.*, u.username FROM vault_snippets v JOIN users u ON v.user_id=u.id WHERE 1=1"
        params = []
        if lang:   query += " AND v.language=?"; params.append(lang)
        if search: query += " AND (v.title LIKE ? OR v.description LIKE ? OR v.code LIKE ?)"; params += [f"%{search}%"]*3
        snippets    = db.execute(query + " AND v.is_public=1 ORDER BY v.created_at DESC", params).fetchall()
        my_snippets = db.execute("SELECT v.*, u.username FROM vault_snippets v JOIN users u ON v.user_id=u.id WHERE v.user_id=? ORDER BY v.created_at DESC", (session["user_id"],)).fetchall()
        unread = get_unread_count(session["user_id"])
    return render_template("vault.html", snippets=snippets, my_snippets=my_snippets, filter_lang=lang, search=search, unread=unread)


@app.route("/api/vault/save", methods=["POST"])
@login_required
def save_snippet():
    data = request.get_json(); sid = data.get("id")
    with get_db() as db:
        if sid:
            db.execute("UPDATE vault_snippets SET title=?,language=?,code=?,description=?,is_public=? WHERE id=? AND user_id=?",
                       (data["title"], data["language"], data["code"], data.get("description",""), int(data.get("is_public",1)), sid, session["user_id"]))
        else:
            cur = db.execute("INSERT INTO vault_snippets (user_id,title,language,code,description,is_public) VALUES (?,?,?,?,?,?)",
                             (session["user_id"], data["title"], data["language"], data["code"], data.get("description",""), int(data.get("is_public",1))))
            sid = cur.lastrowid
    return jsonify({"ok": True, "id": sid})


@app.route("/api/vault/<int:snippet_id>", methods=["DELETE"])
@login_required
def delete_snippet(snippet_id):
    with get_db() as db:
        db.execute("DELETE FROM vault_snippets WHERE id=? AND user_id=?", (snippet_id, session["user_id"]))
    return jsonify({"ok": True})


# ── QUIZ PORTAL ────────────────────────────────────────────────────────────────

@app.route("/quizzes")
@login_required
def quiz_home():
    with get_db() as db:
        quizzes = db.execute(
            "SELECT q.*, u.username AS creator_name, (SELECT COUNT(*) FROM quiz_questions WHERE quiz_id=q.id) AS q_count FROM quizzes q JOIN users u ON q.creator_id=u.id WHERE q.is_active=1 ORDER BY q.created_at DESC"
        ).fetchall()
        attempted_ids = [r["quiz_id"] for r in db.execute("SELECT quiz_id FROM quiz_responses WHERE user_id=?", (session["user_id"],)).fetchall()]
        my_responses  = db.execute(
            "SELECT qr.*, q.title AS quiz_title FROM quiz_responses qr JOIN quizzes q ON qr.quiz_id=q.id WHERE qr.user_id=? ORDER BY qr.submitted_at DESC",
            (session["user_id"],)
        ).fetchall()
        unread = get_unread_count(session["user_id"])
    return render_template("quiz_home.html", quizzes=quizzes, attempted_ids=attempted_ids, my_responses=my_responses, unread=unread)


@app.route("/quizzes/create", methods=["GET", "POST"])
@login_required
@admin_required
def quiz_create():
    if request.method == "POST":
        title = request.form.get("quiz_title", "").strip()
        if not title:
            flash("Quiz title required.", "error"); return redirect(url_for("quiz_create"))
        with get_db() as db:
            cur     = db.execute("INSERT INTO quizzes (title, creator_id) VALUES (?,?)", (title, session["user_id"]))
            quiz_id = cur.lastrowid
            q_texts = request.form.getlist("q_text[]")
            q_types = request.form.getlist("q_type[]")
            q_marks = request.form.getlist("q_marks[]")
            q_ans   = request.form.getlist("q_ans[]")
            for i, qt in enumerate(q_texts):
                if not qt.strip(): continue
                qcur = db.execute("INSERT INTO quiz_questions (quiz_id,question_text,question_type,correct_answer,marks) VALUES (?,?,?,?,?)",
                                  (quiz_id, qt, q_types[i], q_ans[i], int(q_marks[i])))
                qid = qcur.lastrowid
                if q_types[i] == "MCQ":
                    opts = request.form.getlist(f"q_options_{i+1}[]")
                    for idx, ot in enumerate(opts[:4]):
                        if ot.strip():
                            db.execute("INSERT INTO quiz_options (question_id,option_text,index_label) VALUES (?,?,?)",
                                       (qid, ot, "abcd"[idx]))
        flash(f'Quiz "{title}" published!', "success")
        return redirect(url_for("quiz_manage"))
    unread = get_unread_count(session["user_id"])
    return render_template("quiz_create.html", unread=unread)


@app.route("/quizzes/manage")
@login_required
@admin_required
def quiz_manage():
    with get_db() as db:
        quizzes = db.execute(
            "SELECT q.*, u.username AS creator_name, (SELECT COUNT(*) FROM quiz_questions WHERE quiz_id=q.id) AS q_count, (SELECT COUNT(*) FROM quiz_responses WHERE quiz_id=q.id) AS resp_count FROM quizzes q JOIN users u ON q.creator_id=u.id ORDER BY q.created_at DESC"
        ).fetchall()
        unread = get_unread_count(session["user_id"])
    return render_template("quiz_manage.html", quizzes=quizzes, unread=unread)


@app.route("/quizzes/<int:quiz_id>/attempt")
@login_required
def quiz_attempt(quiz_id):
    with get_db() as db:
        quiz = db.execute("SELECT * FROM quizzes WHERE id=? AND is_active=1", (quiz_id,)).fetchone()
        if not quiz: flash("Quiz not found.", "error"); return redirect(url_for("quiz_home"))
        questions = db.execute("SELECT * FROM quiz_questions WHERE quiz_id=?", (quiz_id,)).fetchall()
        quiz_data = []
        for q in questions:
            opts = db.execute("SELECT * FROM quiz_options WHERE question_id=?", (q["id"],)).fetchall()
            quiz_data.append({"question": q, "options": opts})
        unread = get_unread_count(session["user_id"])
    return render_template("quiz_attempt.html", quiz=quiz, quiz_data=quiz_data, unread=unread)


@app.route("/quizzes/<int:quiz_id>/submit", methods=["POST"])
@login_required
def quiz_submit(quiz_id):
    with get_db() as db:
        questions = db.execute("SELECT * FROM quiz_questions WHERE quiz_id=?", (quiz_id,)).fetchall()
        score = 0; total = sum(q["marks"] for q in questions)
        cur = db.execute("INSERT INTO quiz_responses (quiz_id,user_id,score,total_marks) VALUES (?,?,0,?)",
                         (quiz_id, session["user_id"], total))
        resp_id = cur.lastrowid
        for q in questions:
            user_ans = request.form.get(f"ans_{q['id']}", "")
            db.execute("INSERT INTO quiz_answers (response_id,question_id,submitted_text) VALUES (?,?,?)",
                       (resp_id, q["id"], user_ans))
            if user_ans and user_ans.strip().lower() == q["correct_answer"].strip().lower():
                score += q["marks"]
        db.execute("UPDATE quiz_responses SET score=? WHERE id=?", (score, resp_id))
    flash(f"Test submitted! Score: {score}/{total}", "success")
    return redirect(url_for("quiz_home"))


@app.route("/quizzes/<int:quiz_id>/responses")
@login_required
@admin_required
def quiz_responses(quiz_id):
    with get_db() as db:
        quiz = db.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
        if not quiz: flash("Quiz not found.", "error"); return redirect(url_for("quiz_manage"))
        responses = db.execute(
            "SELECT qr.*, u.username FROM quiz_responses qr JOIN users u ON qr.user_id=u.id WHERE qr.quiz_id=? ORDER BY qr.submitted_at DESC",
            (quiz_id,)
        ).fetchall()
        unread = get_unread_count(session["user_id"])
    return render_template("quiz_responses.html", quiz=quiz, responses=responses, unread=unread)


@app.route("/quizzes/response/<int:resp_id>")
@login_required
@admin_required
def quiz_review(resp_id):
    with get_db() as db:
        resp    = db.execute("SELECT * FROM quiz_responses WHERE id=?", (resp_id,)).fetchone()
        student = db.execute("SELECT * FROM users WHERE id=?", (resp["user_id"],)).fetchone()
        quiz    = db.execute("SELECT * FROM quizzes WHERE id=?", (resp["quiz_id"],)).fetchone()
        answers = db.execute("SELECT * FROM quiz_answers WHERE response_id=?", (resp_id,)).fetchall()
        full_paper = []
        for ans in answers:
            q = db.execute("SELECT * FROM quiz_questions WHERE id=?", (ans["question_id"],)).fetchone()
            full_paper.append({
                "question_text": q["question_text"], "question_type": q["question_type"],
                "answer": ans["submitted_text"], "correct": q["correct_answer"],
                "marks": q["marks"],
                "is_correct": (ans["submitted_text"] or "").strip().lower() == q["correct_answer"].strip().lower()
            })
        unread = get_unread_count(session["user_id"])
    return render_template("quiz_review.html", resp=resp, student=student, quiz=quiz, full_paper=full_paper, unread=unread)


@app.route("/quizzes/<int:quiz_id>/toggle", methods=["POST"])
@login_required
@admin_required
def quiz_toggle(quiz_id):
    with get_db() as db:
        q = db.execute("SELECT is_active FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
        nv = 0 if q["is_active"] else 1
        db.execute("UPDATE quizzes SET is_active=? WHERE id=?", (nv, quiz_id))
    return jsonify({"ok": True, "is_active": bool(nv)})


@app.route("/quizzes/<int:quiz_id>/delete", methods=["POST"])
@login_required
@admin_required
def quiz_delete(quiz_id):
    with get_db() as db:
        qs = db.execute("SELECT id FROM quiz_questions WHERE quiz_id=?", (quiz_id,)).fetchall()
        for q in qs: db.execute("DELETE FROM quiz_options WHERE question_id=?", (q["id"],))
        rs = db.execute("SELECT id FROM quiz_responses WHERE quiz_id=?", (quiz_id,)).fetchall()
        for r in rs: db.execute("DELETE FROM quiz_answers WHERE response_id=?", (r["id"],))
        db.execute("DELETE FROM quiz_questions WHERE quiz_id=?", (quiz_id,))
        db.execute("DELETE FROM quiz_responses WHERE quiz_id=?", (quiz_id,))
        db.execute("DELETE FROM quizzes WHERE id=?", (quiz_id,))
    flash("Quiz deleted.", "success"); return redirect(url_for("quiz_manage"))


# ── Social Hub ─────────────────────────────────────────────────────────────────

@app.route("/api/users")
@login_required
def api_get_users():
    with get_db() as db:
        users = db.execute("SELECT id, username FROM users WHERE id!=? ORDER BY username", (session["user_id"],)).fetchall()
    return jsonify({"users": [{"id": u["id"], "username": u["username"], "online": True} for u in users]})


@app.route("/api/messages/<int:peer_id>")
@login_required
def api_get_messages(peer_id):
    uid = session["user_id"]
    with get_db() as db:
        msgs = db.execute(
            "SELECT m.id,m.sender_id,m.receiver_id,m.content,m.created_at,u.username AS sender_username FROM messages m JOIN users u ON u.id=m.sender_id WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?) ORDER BY m.created_at ASC LIMIT 200",
            (uid, peer_id, peer_id, uid)
        ).fetchall()
        db.execute("UPDATE messages SET is_read=1 WHERE receiver_id=? AND sender_id=?", (uid, peer_id))
    return jsonify({"messages": [dict(m) for m in msgs]})


@app.route("/api/messages/send", methods=["POST"])
@login_required
def api_send_message():
    data = request.get_json(); rid = data.get("recipient_id"); content = data.get("content", "").strip()
    if not rid or not content: return jsonify({"ok": False}), 400
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as db:
        cur = db.execute("INSERT INTO messages (sender_id,receiver_id,content,created_at) VALUES (?,?,?,?)",
                         (session["user_id"], rid, content, now))
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/unread")
@login_required
def api_unread():
    return jsonify({"unread": get_unread_count(session["user_id"])})


@socketio.on("connect")
def on_connect():
    uid = session.get("user_id")
    if uid: join_room(f"user_{uid}"); emit("status", {"msg": f"Connected"})


@socketio.on("user_online")
def on_user_online(data):
    uid = session.get("user_id")
    if uid: join_room(f"user_{uid}"); emit("user_joined", {"user_id": uid, "username": session.get("username")}, broadcast=True, include_self=False)


@socketio.on("send_message")
def on_send_message(data):
    sid = session.get("user_id"); rid = data.get("recipient_id"); content = data.get("content","").strip()
    if not sid or not rid or not content: return
    emit("receive_message", {"sender_id": sid, "sender_username": session.get("username"), "receiver_id": rid, "content": content, "created_at": data.get("created_at", datetime.now().isoformat(timespec="seconds"))}, room=f"user_{rid}")


@socketio.on("disconnect")
def on_disconnect():
    uid = session.get("user_id")
    if uid: emit("user_left", {"user_id": uid}, broadcast=True, include_self=False)


# ── Settings ───────────────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old_pw = request.form.get("old_password",""); new_pw = request.form.get("new_password",""); confirm = request.form.get("confirm_password","")
            with get_db() as db:
                user = db.execute("SELECT * FROM users WHERE id=? AND password=?", (session["user_id"], hash_password(old_pw))).fetchone()
            if not user: flash("Current password is incorrect.", "error")
            elif new_pw != confirm: flash("New passwords do not match.", "error")
            elif len(new_pw) < 6: flash("Password must be at least 6 characters.", "error")
            else:
                with get_db() as db: db.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_pw), session["user_id"]))
                flash("Password updated.", "success")
        elif action == "admin_passkey":
            pk = request.form.get("passkey","").strip()
            if pk == ADMIN_PASSKEY:
                # Session-only elevation — never persisted to DB
                session["is_admin"] = True
                flash("Admin privileges activated for this session!", "success")
            else:
                flash("Invalid passkey.", "error")
        return redirect(url_for("settings"))
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        doc_count     = db.execute("SELECT COUNT(*) AS c FROM documents WHERE user_id=?", (session["user_id"],)).fetchone()["c"]
        snippet_count = db.execute("SELECT COUNT(*) AS c FROM vault_snippets WHERE user_id=?", (session["user_id"],)).fetchone()["c"]
        quiz_count    = db.execute("SELECT COUNT(*) AS c FROM quiz_responses WHERE user_id=?", (session["user_id"],)).fetchone()["c"]
        unread = get_unread_count(session["user_id"])
    return render_template("settings.html", user=user, doc_count=doc_count, snippet_count=snippet_count, quiz_count=quiz_count, unread=unread)


# ── Admin Panel ────────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    with get_db() as db:
        users    = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        snippets = db.execute("SELECT v.*, u.username FROM vault_snippets v JOIN users u ON v.user_id=u.id ORDER BY v.created_at DESC").fetchall()
        total_docs     = db.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]
        total_msgs     = db.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        total_quizzes  = db.execute("SELECT COUNT(*) AS c FROM quizzes").fetchone()["c"]
        total_attempts = db.execute("SELECT COUNT(*) AS c FROM quiz_responses").fetchone()["c"]
        unread         = get_unread_count(session["user_id"])
    return render_template("admin.html", users=users, snippets=snippets, total_docs=total_docs, total_msgs=total_msgs, total_quizzes=total_quizzes, total_attempts=total_attempts, unread=unread)


@app.route("/api/admin/delete_user/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_user(uid):
    if uid == session["user_id"]: return jsonify({"ok": False, "error": "Cannot delete yourself"}), 400
    with get_db() as db:
        for tbl in ["documents","vault_snippets","quiz_responses"]:
            db.execute(f"DELETE FROM {tbl} WHERE user_id=?", (uid,))
        db.execute("DELETE FROM messages WHERE sender_id=? OR receiver_id=?", (uid, uid))
        db.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True})


@app.route("/api/admin/toggle_admin/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_toggle_admin(uid):
    with get_db() as db:
        user = db.execute("SELECT is_admin FROM users WHERE id=?", (uid,)).fetchone()
        if not user: return jsonify({"ok": False}), 404
        nv = 0 if user["is_admin"] else 1
        db.execute("UPDATE users SET is_admin=? WHERE id=?", (nv, uid))
    return jsonify({"ok": True, "is_admin": bool(nv)})




@app.route("/code-editor")
@login_required
def code_editor():
    unread = get_unread_count(session["user_id"])
    return render_template("code_editor.html", unread=unread)

if __name__ == "__main__":
    init_db()
    print("LaunchGate ready at http://localhost:5000")
    print(f"Admin passkey: {ADMIN_PASSKEY}")
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
