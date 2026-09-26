import os
import json
import sqlite3
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-temporaria-local"
)

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "123456"
)


# =========================================================
# CAMINHOS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "database.db"
)

LOG_FILE = os.path.join(
    BASE_DIR,
    "access_logs.json"
)

CONFIG_FILE = os.path.join(
    BASE_DIR,
    "config.json"
)


# =========================================================
# CONFIGURAÇÃO PADRÃO
# =========================================================

CONFIG_PADRAO = {
    "site_name": "EXPURG",
    "admin_name": "ADMIN",
    "theme": "dark",
    "primary_color": "#e00000",

    "logo": "",

    "home_text": "THE WORLD IS YOURS",

    "register_ip": True,
    "register_browser": True,

    "max_logs": 1000,
    "auto_clean_logs": False,

    "show_access_time": True,
    "show_access_route": True,

    "session_time": 60,
    "auto_logout": True,

    "confirm_delete_logs": True,

    "show_cards": True,
    "show_ip": True,
    "show_users": True,
    "show_logs": True,
    "show_files": True,
    "show_server_status": True,

    "recent_accesses": 8,

    "admin_username": ADMIN_USERNAME,
    "admin_password": ADMIN_PASSWORD,

    "banner_enabled": True,
    "banner_image": "",
    "banner_title": "THE WORLD IS YOURS",
    "banner_text": "",
    "banner_link": "",

    "chat_enabled": True,
    "announcements_enabled": True
}


# =========================================================
# CONFIG
# =========================================================

def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        salvar_config(CONFIG_PADRAO)
        return CONFIG_PADRAO.copy()

    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:
            config = json.load(arquivo)

        alterado = False

        for chave, valor in CONFIG_PADRAO.items():
            if chave not in config:
                config[chave] = valor
                alterado = True

        if alterado:
            salvar_config(config)

        return config

    except Exception:
        salvar_config(CONFIG_PADRAO)
        return CONFIG_PADRAO.copy()


def salvar_config(config):
    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo:
        json.dump(
            config,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


# =========================================================
# BANCO
# =========================================================

def conectar_banco():
    conexao = sqlite3.connect(
        DATABASE_FILE
    )

    conexao.row_factory = sqlite3.Row

    return conexao


def inicializar_banco():

    conexao = conectar_banco()

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            status TEXT DEFAULT 'offline',
            created_at TEXT NOT NULL,
            last_login TEXT,
            theme TEXT DEFAULT 'dark'
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            image TEXT DEFAULT '',
            link TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ip TEXT,
            browser TEXT,
            route TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Compatibilidade com bancos antigos
    colunas = conexao.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    nomes_colunas = [
        coluna["name"]
        for coluna in colunas
    ]

    if "theme" not in nomes_colunas:
        conexao.execute(
            "ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'dark'"
        )

    conexao.commit()
    conexao.close()


# =========================================================
# USUÁRIOS
# =========================================================

def buscar_usuario_por_id(user_id):

    conexao = conectar_banco()

    usuario = conexao.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conexao.close()

    return usuario


def buscar_usuario_por_login(login):

    conexao = conectar_banco()

    usuario = conexao.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
           OR email = ?
        """,
        (login, login)
    ).fetchone()

    conexao.close()

    return usuario


def listar_usuarios():

    conexao = conectar_banco()

    usuarios = conexao.execute(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conexao.close()

    return usuarios


# =========================================================
# LOGS
# =========================================================

def carregar_logs():

    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(
            LOG_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:
            return json.load(arquivo)

    except Exception:
        return []


def salvar_logs(logs):

    config = carregar_config()

    limite = int(
        config.get(
            "max_logs",
            1000
        )
    )

    if limite > 0:
        logs = logs[-limite:]

    with open(
        LOG_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            logs,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


def obter_ip_cliente():

    forwarded = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get(
        "X-Real-IP"
    )

    if real_ip:
        return real_ip.strip()

    return request.remote_addr or "Desconhecido"


def registrar_log(
    username=None,
    ip=None
):

    config = carregar_config()

    if not config.get(
        "register_ip",
        True
    ):
        ip = None

    if not ip:
        ip = obter_ip_cliente()

    browser = request.headers.get(
        "User-Agent",
        "Desconhecido"
    )

    if not config.get(
        "register_browser",
        True
    ):
        browser = None

    agora = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log = {
        "username": username or "",
        "ip": ip,
        "browser": browser,
        "route": request.path,
        "created_at": agora
    }

    logs = carregar_logs()

    logs.append(log)

    salvar_logs(logs)

    # Também salva no SQLite
    try:
        conexao = conectar_banco()

        conexao.execute(
            """
            INSERT INTO access_logs
            (
                username,
                ip,
                browser,
                route,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username or "",
                ip,
                browser,
                request.path,
                agora
            )
        )

        conexao.commit()
        conexao.close()

    except Exception:
        pass


# =========================================================
# LOGIN ADMIN
# =========================================================

def admin_logado():

    return bool(
        session.get(
            "is_admin",
            False
        )
    )


def membro_logado():

    return bool(
        session.get(
            "member_authenticated",
            False
        )
    )


def login_obrigatorio():

    if not membro_logado():
        return redirect("/login")

    return None


# =========================================================
# CONTEXTO GLOBAL
# =========================================================

@app.context_processor
def contexto_global():

    config = carregar_config()

    usuario_logado = bool(
        session.get(
            "member_authenticated",
            False
        )
    )

    usuario_admin = bool(
        session.get(
            "is_admin",
            False
        )
    )

    usuario = None

    if usuario_logado:

        member_id = session.get(
            "member_id"
        )

        if member_id and member_id != 0:

            usuario = buscar_usuario_por_id(
                member_id
            )

    return {
        "config": config,
        "usuario_logado": usuario_logado,
        "usuario_admin": usuario_admin,
        "usuario": usuario
    }


# =========================================================
# CONTROLE DE SESSÃO
# =========================================================

@app.before_request
def controlar_sessao():

    if not session.get(
        "member_authenticated",
        False
    ):
        return

    config = carregar_config()

    if not config.get(
        "auto_logout",
        True
    ):
        return

    ultima_atividade = session.get(
        "ultima_atividade"
    )

    agora = datetime.now()

    if ultima_atividade:

        try:

            ultima = datetime.fromisoformat(
                ultima_atividade
            )

            minutos = int(
                config.get(
                    "session_time",
                    60
                )
            )

            if agora - ultima > timedelta(
                minutes=minutos
            ):

                if (
                    session.get("member_id")
                    and session.get("member_id") != 0
                ):

                    conexao = conectar_banco()

                    conexao.execute(
                        """
                        UPDATE users
                        SET status = 'offline'
                        WHERE id = ?
                        """,
                        (
                            session.get("member_id"),
                        )
                    )

                    conexao.commit()
                    conexao.close()

                session.clear()

                return redirect("/login")

        except Exception:
            pass

    session["ultima_atividade"] = agora.isoformat()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    config = carregar_config()

    anuncios = []

    if config.get(
        "announcements_enabled",
        True
    ):

        conexao = conectar_banco()

        anuncios = conexao.execute(
            """
            SELECT *
            FROM announcements
            WHERE active = 1
            ORDER BY id DESC
            """
        ).fetchall()

        conexao.close()

    registrar_log(
        username=session.get(
            "member_username",
            ""
        )
    )

    return render_template(
        "index.html",
        anuncios=anuncios
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        login_value = request.form.get(
            "login",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        config = carregar_config()

        admin_username = config.get(
            "admin_username",
            ADMIN_USERNAME
        )

        admin_password = config.get(
            "admin_password",
            ADMIN_PASSWORD
        )

        # ADMIN
        if (
            login_value == admin_username
            and password == admin_password
        ):

            session.clear()

            session["member_authenticated"] = True
            session["member_username"] = admin_username
            session["member_id"] = 0
            session["is_admin"] = True
            session["admin_authenticated"] = True
            session["ultima_atividade"] = datetime.now().isoformat()

            registrar_log(
                username=admin_username
            )

            return redirect("/admin")

        # USUÁRIO NORMAL
        usuario = buscar_usuario_por_login(
            login_value
        )

        if not usuario:

            flash(
                "Usuário ou senha incorretos.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if usuario["status"] == "blocked":

            flash(
                "Esta conta está bloqueada.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if not check_password_hash(
            usuario["password_hash"],
            password
        ):

            flash(
                "Usuário ou senha incorretos.",
                "error"
            )

            return render_template(
                "login.html"
            )

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conexao = conectar_banco()

        conexao.execute(
            """
            UPDATE users
            SET last_login = ?,
                status = 'online'
            WHERE id = ?
            """,
            (
                agora,
                usuario["id"]
            )
        )

        conexao.commit()
        conexao.close()

        session.clear()

        session["member_authenticated"] = True
        session["member_username"] = usuario["username"]
        session["member_id"] = usuario["id"]
        session["is_admin"] = False
        session["admin_authenticated"] = False
        session["ultima_atividade"] = datetime.now().isoformat()

        registrar_log(
            username=usuario["username"]
        )

        return redirect("/")

    return render_template(
        "login.html"
    )


# =========================================================
# CADASTRO
# =========================================================

@app.route(
    "/cadastro",
    methods=["GET", "POST"]
)
def cadastro():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        password_confirm = request.form.get(
            "password_confirm",
            request.form.get(
                "confirm_password",
                ""
            )
        )

        if not username or not email or not password:

            flash(
                "Preencha todos os campos.",
                "error"
            )

            return render_template(
                "cadastro.html"
            )

        if password != password_confirm:

            flash(
                "As senhas não coincidem.",
                "error"
            )

            return render_template(
                "cadastro.html"
            )

        config = carregar_config()

        admin_username = config.get(
            "admin_username",
            ADMIN_USERNAME
        )

        if username.lower() == admin_username.lower():

            flash(
                "Esse nome de usuário não está disponível.",
                "error"
            )

            return render_template(
                "cadastro.html"
            )

        conexao = conectar_banco()

        existe = conexao.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
               OR email = ?
            """,
            (
                username,
                email
            )
        ).fetchone()

        if existe:

            conexao.close()

            flash(
                "Usuário ou e-mail já cadastrado.",
                "error"
            )

            return render_template(
                "cadastro.html"
            )

        agora = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        password_hash = generate_password_hash(
            password
        )

        conexao.execute(
            """
            INSERT INTO users
            (
                email,
                username,
                password_hash,
                level,
                xp,
                status,
                created_at,
                theme
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                username,
                password_hash,
                1,
                0,
                "offline",
                agora,
                "dark"
            )
        )

        conexao.commit()
        conexao.close()

        flash(
            "Conta criada com sucesso.",
            "success"
        )

        return redirect("/login")

    return render_template(
        "cadastro.html"
    )


# =========================================================
# PERFIL
# =========================================================

@app.route("/perfil")
def perfil():

    if not membro_logado():
        return redirect("/login")

    if admin_logado():
        return redirect("/admin")

    usuario = buscar_usuario_por_id(
        session.get("member_id")
    )

    if not usuario:
        session.clear()
        return redirect("/login")

    return render_template(
        "perfil.html",
        usuario=usuario
    )


# =========================================================
# CONFIGURAÇÕES DO MEMBRO
# =========================================================

@app.route(
    "/configuracoes",
    methods=["GET", "POST"]
)
def configuracoes():

    if not membro_logado():
        return redirect("/login")

    if admin_logado():
        return redirect("/admin/config")

    usuario = buscar_usuario_por_id(
        session.get("member_id")
    )

    if not usuario:
        return redirect("/login")

    if request.method == "POST":

        theme = request.form.get(
            "theme",
            "dark"
        )

        if theme not in [
            "dark",
            "light"
        ]:
            theme = "dark"

        conexao = conectar_banco()

        conexao.execute(
            """
            UPDATE users
            SET theme = ?
            WHERE id = ?
            """,
            (
                theme,
                usuario["id"]
            )
        )

        conexao.commit()
        conexao.close()

        flash(
            "Configurações salvas.",
            "success"
        )

        return redirect("/configuracoes")

    return render_template(
        "configuracoes.html",
        usuario=usuario
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    member_id = session.get(
        "member_id"
    )

    if member_id and member_id != 0:

        try:

            conexao = conectar_banco()

            conexao.execute(
                """
                UPDATE users
                SET status = 'offline'
                WHERE id = ?
                """,
                (
                    member_id,
                )
            )

            conexao.commit()
            conexao.close()

        except Exception:
            pass

    session.clear()

    return redirect("/")


# =========================================================
# REGISTRO DE IP
# =========================================================

@app.route(
    "/registrar-ip",
    methods=["POST"]
)
def registrar_ip():

    # O IP não vem do navegador.
    # O servidor registra o IP real da requisição.
    ip = obter_ip_cliente()

    registrar_log(
        username=session.get(
            "member_username",
            ""
        ),
        ip=ip
    )

    return jsonify({
        "ok": True
    })


# =========================================================
# PAINEL ADMINISTRATIVO
# =========================================================

@app.route("/admin")
def admin():

    if not admin_logado():
        return redirect("/")

    logs = carregar_logs()

    usuarios = listar_usuarios()

    config = carregar_config()

    ips_unicos = set()

    for log in logs:

        ip = log.get("ip")

        if ip:
            ips_unicos.add(ip)

    ultimo_acesso = None

    if logs:
        ultimo_acesso = logs[-1]

    conexao = conectar_banco()

    total_mensagens = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM chat_messages
        """
    ).fetchone()["total"]

    total_anuncios = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM announcements
        """
    ).fetchone()["total"]

    usuarios_online = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        WHERE status = 'online'
        """
    ).fetchone()["total"]

    conexao.close()

    return render_template(
        "admin_dashboard.html",
        logs=logs,
        ips_unicos=ips_unicos,
        total_acessos=len(logs),
        total_ips=len(ips_unicos),
        ultimo_acesso=ultimo_acesso,
        usuarios=usuarios,
        total_usuarios=len(usuarios),
        usuarios_online=usuarios_online,
        total_mensagens=total_mensagens,
        total_anuncios=total_anuncios,
        config=config
    )


# =========================================================
# EDITAR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/editar",
    methods=["GET", "POST"]
)
def editar_membro(user_id):

    if not admin_logado():
        return redirect("/")

    usuario = buscar_usuario_por_id(
        user_id
    )

    if not usuario:
        return redirect("/admin")

    if request.method == "POST":

        try:
            level = int(
                request.form.get(
                    "level",
                    1
                )
            )
        except Exception:
            level = 1

        try:
            xp = int(
                request.form.get(
                    "xp",
                    0
                )
            )
        except Exception:
            xp = 0

        status = request.form.get(
            "status",
            "offline"
        )

        theme = request.form.get(
            "theme",
            "dark"
        )

        if status not in [
            "online",
            "offline",
            "blocked"
        ]:
            status = "offline"

        if theme not in [
            "dark",
            "light"
        ]:
            theme = "dark"

        level = max(
            1,
            level
        )

        xp = max(
            0,
            xp
        )

        conexao = conectar_banco()

        conexao.execute(
            """
            UPDATE users
            SET level = ?,
                xp = ?,
                status = ?,
                theme = ?
            WHERE id = ?
            """,
            (
                level,
                xp,
                status,
                theme,
                user_id
            )
        )

        conexao.commit()
        conexao.close()

        return redirect("/admin")

    return render_template(
        "editar_membro.html",
        usuario=usuario
    )


# =========================================================
# BLOQUEAR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/bloquear",
    methods=["POST"]
)
def bloquear_membro(user_id):

    if not admin_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE users
        SET status = 'blocked'
        WHERE id = ?
        """,
        (
            user_id,
        )
    )

    conexao.commit()
    conexao.close()

    return redirect("/admin")


# =========================================================
# DESBLOQUEAR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/desbloquear",
    methods=["POST"]
)
def desbloquear_membro(user_id):

    if not admin_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE users
        SET status = 'offline'
        WHERE id = ?
        """,
        (
            user_id,
        )
    )

    conexao.commit()
    conexao.close()

    return redirect("/admin")


# =========================================================
# EXCLUIR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/excluir",
    methods=["POST"]
)
def excluir_membro(user_id):

    if not admin_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (
            user_id,
        )
    )

    conexao.commit()
    conexao.close()

    return redirect("/admin")


# =========================================================
# ANÚNCIOS
# =========================================================

@app.route(
    "/admin/anuncios",
    methods=["GET", "POST"]
)
def admin_anuncios():

    if not admin_logado():
        return redirect("/")

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        image = request.form.get(
            "image",
            ""
        ).strip()

        link = request.form.get(
            "link",
            ""
        ).strip()

        if title:

            agora = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            conexao = conectar_banco()

            conexao.execute(
                """
                INSERT INTO announcements
                (
                    title,
                    content,
                    image,
                    link,
                    active,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    content,
                    image,
                    link,
                    1,
                    agora
                )
            )

            conexao.commit()
            conexao.close()

        return redirect(
            "/admin/anuncios"
        )

    conexao = conectar_banco()

    anuncios = conexao.execute(
        """
        SELECT *
        FROM announcements
        ORDER BY id DESC
        """
    ).fetchall()

    conexao.close()

    return render_template(
        "admin_anuncios.html",
        anuncios=anuncios
    )


@app.route(
    "/admin/anuncios/<int:announcement_id>/editar",
    methods=["POST"]
)
def editar_anuncio(announcement_id):

    if not admin_logado():
        return redirect("/")

    title = request.form.get(
        "title",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    image = request.form.get(
        "image",
        ""
    ).strip()

    link = request.form.get(
        "link",
        ""
    ).strip()

    active = 1 if request.form.get(
        "active"
    ) else 0

    agora = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE announcements
        SET title = ?,
            content = ?,
            image = ?,
            link = ?,
            active = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            title,
            content,
            image,
            link,
            active,
            agora,
            announcement_id
        )
    )

    conexao.commit()
    conexao.close()

    return redirect(
        "/admin/anuncios"
    )


@app.route(
    "/admin/anuncios/<int:announcement_id>/excluir",
    methods=["POST"]
)
def excluir_anuncio(announcement_id):

    if not admin_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM announcements
        WHERE id = ?
        """,
        (
            announcement_id,
        )
    )

    conexao.commit()
    conexao.close()

    return redirect(
        "/admin/anuncios"
    )


# =========================================================
# BANNER
# =========================================================

@app.route(
    "/admin/banner",
    methods=["GET", "POST"]
)
def admin_banner():

    if not admin_logado():
        return redirect("/")

    config = carregar_config()

    if request.method == "POST":

        config["banner_enabled"] = bool(
            request.form.get(
                "banner_enabled"
            )
        )

        config["banner_image"] = request.form.get(
            "banner_image",
            ""
        ).strip()

        config["banner_title"] = request.form.get(
            "banner_title",
            ""
        ).strip()

        config["banner_text"] = request.form.get(
            "banner_text",
            ""
        ).strip()

        config["banner_link"] = request.form.get(
            "banner_link",
            ""
        ).strip()

        salvar_config(config)

        return redirect(
            "/admin/banner"
        )

    return render_template(
        "admin_banner.html",
        config=config
    )


# =========================================================
# CONFIGURAÇÕES ADMIN
# =========================================================

@app.route(
    "/admin/config",
    methods=["GET", "POST"]
)
def admin_config():

    if not admin_logado():
        return redirect("/")

    config = carregar_config()

    if request.method == "POST":

        site_name = request.form.get(
            "site_name",
            "EXPURG"
        ).strip()

        admin_name = request.form.get(
            "admin_name",
            "ADMIN"
        ).strip()

        home_text = request.form.get(
            "home_text",
            ""
        ).strip()

        primary_color = request.form.get(
            "primary_color",
            "#e00000"
        ).strip()

        admin_username = request.form.get(
            "admin_username",
            ADMIN_USERNAME
        ).strip()

        admin_password = request.form.get(
            "admin_password",
            ""
        ).strip()

        chat_enabled = bool(
            request.form.get(
                "chat_enabled"
            )
        )

        announcements_enabled = bool(
            request.form.get(
                "announcements_enabled"
            )
        )

        if not site_name:
            site_name = "EXPURG"

        if not admin_name:
            admin_name = "ADMIN"

        if not home_text:
            home_text = "THE WORLD IS YOURS"

        if not primary_color:
            primary_color = "#e00000"

        if not admin_username:
            admin_username = ADMIN_USERNAME

        config["site_name"] = site_name
        config["admin_name"] = admin_name
        config["home_text"] = home_text
        config["primary_color"] = primary_color
        config["admin_username"] = admin_username

        # Só altera a senha se foi digitada
        if admin_password:
            config["admin_password"] = admin_password

        config["chat_enabled"] = chat_enabled
        config["announcements_enabled"] = announcements_enabled

        salvar_config(config)

        # Mantém a sessão com o novo nome
        session["member_username"] = admin_username

        return redirect(
            "/admin/config"
        )

    return render_template(
        "admin_config.html",
        config=config
    )


# =========================================================
# RESTAURAR CONFIGURAÇÕES
# =========================================================

@app.route(
    "/admin/config/restaurar",
    methods=["POST"]
)
def restaurar_config():

    if not admin_logado():
        return redirect("/")

    config = CONFIG_PADRAO.copy()

    salvar_config(config)

    return redirect(
        "/admin/config"
    )


# =========================================================
# LIMPAR LOGS
# =========================================================

@app.route(
    "/admin/limpar-logs",
    methods=["POST"]
)
def limpar_logs():

    if not admin_logado():
        return redirect("/")

    salvar_logs([])

    conexao = conectar_banco()

    conexao.execute(
        "DELETE FROM access_logs"
    )

    conexao.commit()
    conexao.close()

    return redirect("/admin")


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/chat",
    methods=["GET", "POST"]
)
def chat():

    if not membro_logado():
        return redirect("/login")

    config = carregar_config()

    if not config.get(
        "chat_enabled",
        True
    ):
        return redirect("/")

    if request.method == "POST":

        message = request.form.get(
            "message",
            ""
        ).strip()

        if message:

            username = session.get(
                "member_username",
                "Usuário"
            )

            user_id = session.get(
                "member_id"
            )

            agora = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            conexao = conectar_banco()

            conexao.execute(
                """
                INSERT INTO chat_messages
                (
                    user_id,
                    username,
                    message,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    message,
                    agora
                )
            )

            conexao.commit()
            conexao.close()

        return redirect("/chat")

    conexao = conectar_banco()

    mensagens = conexao.execute(
        """
        SELECT *
        FROM chat_messages
        ORDER BY id ASC
        """
    ).fetchall()

    conexao.close()

    return render_template(
        "chat.html",
        mensagens=mensagens
    )


# =========================================================
# EXCLUIR MENSAGEM
# =========================================================

@app.route(
    "/admin/chat/<int:message_id>/excluir",
    methods=["POST"]
)
def excluir_mensagem(message_id):

    if not admin_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM chat_messages
        WHERE id = ?
        """,
        (
            message_id,
        )
    )

    conexao.commit()
    conexao.close()

    return redirect("/chat")


# =========================================================
# API STATUS
# =========================================================

@app.route("/api/status")
def api_status():

    if not admin_logado():
        return jsonify({
            "error": "Não autorizado"
        }), 403

    conexao = conectar_banco()

    usuarios = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        """
    ).fetchone()["total"]

    online = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        WHERE status = 'online'
        """
    ).fetchone()["total"]

    mensagens = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM chat_messages
        """
    ).fetchone()["total"]

    anuncios = conexao.execute(
        """
        SELECT COUNT(*) AS total
        FROM announcements
        """
    ).fetchone()["total"]

    conexao.close()

    return jsonify({
        "usuarios": usuarios,
        "online": online,
        "mensagens": mensagens,
        "anuncios": anuncios
    })


# =========================================================
# INICIALIZAÇÃO
# =========================================================

inicializar_banco()
carregar_config()


# =========================================================
# EXECUÇÃO LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )