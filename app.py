import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps

import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave")

# ── Conexão PostgreSQL ──────────────────────────────────────────────
def get_db():
    # Railway injeta DATABASE_PRIVATE_URL automaticamente (rede privada, gratuita)
    url = os.getenv("DATABASE_PRIVATE_URL") or os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url, sslmode="require")
    # Fallback para uso local (.env com variaveis individuais)
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )

# ── Criar tabela automaticamente na inicialização ──────────────────
def init_db():
    SQL = """
        CREATE TABLE IF NOT EXISTS contatos (
            id        SERIAL PRIMARY KEY,
            nome      VARCHAR(200)  NOT NULL,
            email     VARCHAR(200)  NOT NULL,
            telefone  VARCHAR(50),
            area      VARCHAR(100),
            mensagem  TEXT          NOT NULL,
            criado_em TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
            lido      BOOLEAN       DEFAULT FALSE
        );
    """
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Tabela 'contatos' pronta.")
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")

init_db()

# ── Envio de e-mail (Gmail SMTP) ────────────────────────────────────
def enviar_email(dados):
    try:
        remetente   = os.getenv("GMAIL_USER")
        app_pass    = os.getenv("GMAIL_APP_PASSWORD")
        destinatario = os.getenv("GMAIL_USER")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Site] Nova mensagem de {dados['nome']}"
        msg["From"]    = remetente
        msg["To"]      = destinatario

        corpo = f"""
        <html><body style="font-family:Arial,sans-serif;color:#1C1C1C;">
          <h2 style="color:#B8965A;">Nova mensagem pelo site</h2>
          <table style="border-collapse:collapse;width:100%;">
            <tr><td style="padding:8px;font-weight:bold;">Nome</td><td style="padding:8px;">{dados['nome']}</td></tr>
            <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">E-mail</td><td style="padding:8px;">{dados['email']}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;">Telefone</td><td style="padding:8px;">{dados.get('telefone','—')}</td></tr>
            <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">Área</td><td style="padding:8px;">{dados.get('area','—')}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;vertical-align:top;">Mensagem</td><td style="padding:8px;">{dados['mensagem']}</td></tr>
          </table>
          <p style="margin-top:20px;font-size:12px;color:#888;">Recebido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </body></html>
        """
        msg.attach(MIMEText(corpo, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remetente, app_pass)
            smtp.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ── Decorator admin ─────────────────────────────────────────────────
def requer_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Rotas ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/contato", methods=["POST"])
def contato():
    dados = request.get_json(silent=True) or {}

    nome     = dados.get("nome", "").strip()
    email    = dados.get("email", "").strip()
    mensagem = dados.get("mensagem", "").strip()

    if not nome or not email or not mensagem:
        return jsonify({"ok": False, "erro": "Campos obrigatórios ausentes."}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO contatos (nome, email, telefone, area, mensagem)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                nome,
                email,
                dados.get("telefone", ""),
                dados.get("area", ""),
                mensagem,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"ok": False, "erro": "Erro ao salvar. Tente novamente."}), 500

    enviar_email(dados)
    return jsonify({"ok": True}), 200


# ── Painel Admin ─────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    erro = None
    if request.method == "POST":
        senha = request.form.get("senha", "")
        if senha == os.getenv("ADMIN_PASSWORD", "admin123"):
            session["admin"] = True
            return redirect(url_for("admin_painel"))
        erro = "Senha incorreta."
    return render_template("admin_login.html", erro=erro)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@requer_login
def admin_painel():
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM contatos ORDER BY criado_em DESC")
        mensagens = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        mensagens = []
    return render_template("admin.html", mensagens=mensagens)


@app.route("/admin/marcar-lido/<int:id>")
@requer_login
def marcar_lido(id):
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("UPDATE contatos SET lido = TRUE WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return redirect(url_for("admin_painel"))


@app.route("/admin/deletar/<int:id>")
@requer_login
def deletar(id):
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM contatos WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return redirect(url_for("admin_painel"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
