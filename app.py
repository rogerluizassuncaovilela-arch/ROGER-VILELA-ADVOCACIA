import os
import re
import json
import threading
import unicodedata
import urllib.request
import urllib.error
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
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    # Fallback local
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "railway"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
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
        CREATE TABLE IF NOT EXISTS artigos (
            id           SERIAL PRIMARY KEY,
            titulo       VARCHAR(300) NOT NULL,
            slug         VARCHAR(300) UNIQUE NOT NULL,
            resumo       VARCHAR(500),
            conteudo     TEXT         NOT NULL,
            imagem_url   VARCHAR(500),
            categoria    VARCHAR(100),
            publicado    BOOLEAN      DEFAULT FALSE,
            criado_em    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
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
        api_key = os.getenv("BREVO_API_KEY")
        if not api_key:
            print("[EMAIL] BREVO_API_KEY ausente - e-mail ignorado.")
            return

        corpo_html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#1C1C1C;">
          <h2 style="color:#B8965A;">Nova mensagem pelo site</h2>
          <table style="border-collapse:collapse;width:100%;border:1px solid #eee;">
            <tr><td style="padding:10px;font-weight:bold;background:#f5f0ea;">Nome</td><td style="padding:10px;">{dados['nome']}</td></tr>
            <tr><td style="padding:10px;font-weight:bold;background:#f5f0ea;">E-mail</td><td style="padding:10px;">{dados['email']}</td></tr>
            <tr><td style="padding:10px;font-weight:bold;background:#f5f0ea;">Telefone</td><td style="padding:10px;">{dados.get('telefone','—')}</td></tr>
            <tr><td style="padding:10px;font-weight:bold;background:#f5f0ea;">Área</td><td style="padding:10px;">{dados.get('area','—')}</td></tr>
            <tr><td style="padding:10px;font-weight:bold;background:#f5f0ea;vertical-align:top;">Mensagem</td><td style="padding:10px;">{dados['mensagem']}</td></tr>
          </table>
          <p style="margin-top:20px;font-size:12px;color:#888;">Recebido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </body></html>
        """

        payload = json.dumps({
            "sender":   {"name": "Roger Vilela Advocacia", "email": "rogerluizassuncaovilela@gmail.com"},
            "to":       [{"email": "rogerluizassuncaovilela@gmail.com", "name": "Dr. Roger Vilela"}],
            "subject":  f"[Site] Nova mensagem de {dados['nome']}",
            "htmlContent": corpo_html
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={
                "api-key":      api_key,
                "Content-Type": "application/json",
                "Accept":       "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[EMAIL] Enviado via Brevo. Status: {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[EMAIL ERROR] {e.code} {e.reason} — {body}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

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

    threading.Thread(target=enviar_email, args=(dados,), daemon=True).start()
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


# ── Google Search Console Verification ─────────────────────────────
@app.route("/googlee6ac8beeef971233.html")
def google_verify():
    from flask import Response
    return Response(
        "google-site-verification: googlee6ac8beeef971233.html",
        mimetype="text/html"
    )

# ── Slug ────────────────────────────────────────────────────────────
def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)

# ── Artigos (público) ────────────────────────────────────────────────
@app.route("/artigos")
def artigos():
    try:
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM artigos WHERE publicado=TRUE ORDER BY criado_em DESC")
        posts = cur.fetchall(); cur.close(); conn.close()
    except: posts = []
    return render_template("artigos.html", posts=posts)

@app.route("/artigos/<slug>")
def artigo(slug):
    try:
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM artigos WHERE slug=%s AND publicado=TRUE", (slug,))
        post = cur.fetchone(); cur.close(); conn.close()
    except: post = None
    if not post:
        return "Artigo não encontrado.", 404
    return render_template("artigo.html", post=post)

# ── Artigos (admin) ──────────────────────────────────────────────────
@app.route("/admin/artigos")
@requer_login
def admin_artigos():
    try:
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM artigos ORDER BY criado_em DESC")
        posts = cur.fetchall(); cur.close(); conn.close()
    except: posts = []
    return render_template("admin_artigos.html", posts=posts)

@app.route("/admin/artigos/novo")
@requer_login
def admin_artigo_novo():
    return render_template("admin_artigo_form.html", post=None)

@app.route("/admin/artigos/criar", methods=["POST"])
@requer_login
def admin_artigo_criar():
    titulo    = request.form.get("titulo", "").strip()
    conteudo  = request.form.get("conteudo", "").strip()
    resumo    = request.form.get("resumo", "").strip()
    imagem    = request.form.get("imagem_url", "").strip()
    categoria = request.form.get("categoria", "").strip()
    publicado = request.form.get("publicado") == "on"
    slug      = slugify(titulo)
    if not titulo or not conteudo:
        return redirect(url_for("admin_artigo_novo"))
    try:
        conn = get_db(); cur = conn.cursor()
        # ensure unique slug
        base = slug; i = 1
        while True:
            cur.execute("SELECT id FROM artigos WHERE slug=%s", (slug,))
            if not cur.fetchone(): break
            slug = f"{base}-{i}"; i += 1
        cur.execute(
            "INSERT INTO artigos (titulo,slug,resumo,conteudo,imagem_url,categoria,publicado) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (titulo, slug, resumo, conteudo, imagem, categoria, publicado)
        )
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[ARTIGO ERROR] {e}")
    return redirect(url_for("admin_artigos"))

@app.route("/admin/artigos/editar/<int:id>")
@requer_login
def admin_artigo_editar(id):
    try:
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM artigos WHERE id=%s", (id,))
        post = cur.fetchone(); cur.close(); conn.close()
    except: post = None
    return render_template("admin_artigo_form.html", post=post)

@app.route("/admin/artigos/atualizar/<int:id>", methods=["POST"])
@requer_login
def admin_artigo_atualizar(id):
    titulo    = request.form.get("titulo", "").strip()
    conteudo  = request.form.get("conteudo", "").strip()
    resumo    = request.form.get("resumo", "").strip()
    imagem    = request.form.get("imagem_url", "").strip()
    categoria = request.form.get("categoria", "").strip()
    publicado = request.form.get("publicado") == "on"
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "UPDATE artigos SET titulo=%s,resumo=%s,conteudo=%s,imagem_url=%s,categoria=%s,publicado=%s,atualizado_em=NOW() WHERE id=%s",
            (titulo, resumo, conteudo, imagem, categoria, publicado, id)
        )
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[ARTIGO ERROR] {e}")
    return redirect(url_for("admin_artigos"))

@app.route("/admin/artigos/publicar/<int:id>")
@requer_login
def admin_artigo_publicar(id):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("UPDATE artigos SET publicado = NOT publicado WHERE id=%s", (id,))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[ARTIGO ERROR] {e}")
    return redirect(url_for("admin_artigos"))

@app.route("/admin/artigos/deletar/<int:id>")
@requer_login
def admin_artigo_deletar(id):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM artigos WHERE id=%s", (id,))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[ARTIGO ERROR] {e}")
    return redirect(url_for("admin_artigos"))

# ── SEO: Sitemap e Robots ───────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap():
    from flask import Response
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://rogervilelaadvocacia.up.railway.app/</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return Response(xml, mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    from flask import Response
    txt = """User-agent: *
Allow: /
Sitemap: https://rogervilelaadvocacia.up.railway.app/sitemap.xml"""
    return Response(txt, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
