# NeuroVerse

> A unified collaborative workspace — write documents, run code, share snippets, chat with teammates, and take quizzes. All in one place.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-black?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-embedded-lightblue?style=flat-square&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Features

| Module | Description |
|---|---|
| **Dashboard** | Overview of all activity — documents, snippets, messages, quizzes |
| **Neuro Word** | Rich text word processor with PDF export, auto-save, recent docs sidebar |
| **Code Editor** | Online IDE supporting Python, C, C++, Java, JavaScript, HTML/CSS, TypeScript, Rust, Go, Bash — no installs needed (powered by [Piston API](https://github.com/engineer-man/piston)) |
| **Code Vault** | Community snippet library — share, browse, filter by language, fullscreen viewer |
| **Social Hub** | Real-time messaging between teammates via WebSockets (Flask-SocketIO) |
| **Quiz Portal** | Create, publish, and attempt quizzes with multiple choice questions |
| **Admin Panel** | User management, snippet moderation, quiz management — session-only passkey access |

---

## Tech Stack

- **Backend** — Flask, Flask-SocketIO, SQLite
- **Frontend** — Jinja2 templates, vanilla JS, Socket.IO
- **Real-time** — WebSockets via Flask-SocketIO (threading mode)
- **Code execution** — [Piston API](https://emkc.org/api/v2/piston) (free, no key required)
- **PDF export** — jsPDF (client-side)
- **Auth** — Session-based, SHA-256 password hashing

---

## Project Structure

```
neuroverse/
├── app.py                  # Main Flask application & all routes
├── requirements.txt        # Python dependencies
├── launchgate.db           # SQLite database (auto-created on first run)
├── static/
│   ├── style.css           # Unified design system
│   ├── logo.png            # Brand logo
│   └── js/
│       └── app.js          # Social Hub Socket.IO client
└── templates/
    ├── base.html           # HTML shell
    ├── layout.html         # App shell (sidebar, navbar, chat panel)
    ├── dashboard.html      # Main dashboard
    ├── nero_word.html      # Word processor (editor.html)
    ├── vault.html          # Code Vault
    ├── code_editor.html    # Online Code Editor
    ├── quiz_home.html      # Quiz portal
    ├── admin.html          # Admin panel
    ├── admin_dashboard.html
    ├── settings.html
    └── login.html / register.html
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/neuroverse.git
cd neuroverse
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set environment variables (optional)

```bash
# Windows
set SECRET_KEY=your-secret-key
set ADMIN_PASSKEY=your-admin-passkey

# macOS / Linux
export SECRET_KEY=your-secret-key
export ADMIN_PASSKEY=your-admin-passkey
```

If not set, defaults are used (`launchgate-secret-2026-x` and `NEURO-2026-X`). **Change these in production.**

### 5. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser. The SQLite database is created automatically on first run.

---

## Deployment (Render + UptimeRobot — Free, Always On)

### Step 1 — Add deployment files

**`Procfile`** (create in root directory):
```
web: gunicorn --worker-class eventlet -w 1 app:app
```

**Update `requirements.txt`** — add these if not present:
```
flask-socketio==5.3.6
python-socketio==5.11.2
gunicorn
eventlet
```

### Step 2 — Deploy on Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repository
4. Set the following:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --worker-class eventlet -w 1 app:app`
   - **Environment variables:** Add `SECRET_KEY` and `ADMIN_PASSKEY`
5. Click **Deploy**

### Step 3 — Prevent sleep with UptimeRobot

Render's free tier sleeps after 15 minutes of inactivity. Prevent this for free:

1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor → **HTTP(s)** → paste your Render URL
3. Set interval to **5 minutes**
4. Your app will never sleep

---

## Admin Access

Admin privileges are **session-only** — they are never stored in the database.

To activate admin access:
1. Log in to any account
2. Go to **Settings → Admin Access**
3. Enter the admin passkey (default: `NEURO-2026-X`)
4. Admin panel is accessible for the current session only
5. Logging out removes admin access

---

## Supported Languages in Code Editor

| Language | Runtime | Notes |
|---|---|---|
| Python | 3.10.0 | Full stdlib, `input()` supported |
| C | GCC 10.2 | Compile + run |
| C++ | GCC 10.2 | Compile + run |
| Java | JDK 15.0.2 | Auto-detects class name |
| JavaScript | Node.js 18.15 | Full Node runtime |
| HTML / CSS | Browser | Live preview in output panel |
| TypeScript | 5.0.3 | Compile + run |
| Rust | 1.68.2 | Full compile |
| Go | 1.20.3 | Full compile |
| Bash | 5.2.0 | Shell scripting |

Code runs on the [Piston API](https://github.com/engineer-man/piston) — no packages to install, no accounts needed.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `launchgate-secret-2026-x` | Flask session secret — **change in production** |
| `ADMIN_PASSKEY` | `NEURO-2026-X` | Passkey to activate admin session — **change in production** |

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">
  Built with Flask · Designed for collaboration
</div>
