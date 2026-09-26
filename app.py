import os
import json
import sqlite3
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify
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

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

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

    "home_text": (
        "THE WORLD IS YOURS"
    ),

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

    # Banner
    "banner_enabled": True,
    "banner_image": "",
    "banner_title": "THE WORLD IS YOURS",
    "banner_text": "",
    "banner_link": "",

    # Chat
    "chat_enabled": True,

    # Anúncios
    "announcements_enabled": True
}


# =========================================================
# CONFIG
# =========================================================

def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        salvar_config(CONFIG_PADRAO.copy())
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

    except (
        OSError,
        json.JSONDecodeError
    ):
        salvar_config(CONFIG_PADRAO.copy())
        return CONFIG_PADRAO.copy()


def salvar_config(config):
    try:
        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as arquivo:
            json.dump(
                config,
                arquivo,
                indent=4,
                ensure_ascii=False
            )
    except OSError:
        pass


# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():
    conexao = sqlite3.connect(
        DATABASE_FILE
    )

    conexao.row_factory = sqlite3.Row

    return conexao


def inicializar_banco():

    conexao = conectar_banco()

    conexao.execute(
        """
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
        """
    )

    conexao.execute(
        """
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
        """
    )

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            username TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TEXT NOT NULL
        )
        """
    )

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT,

            ip TEXT,

            browser TEXT,

            route TEXT,

            created_at TEXT NOT NULL
        )
        """
    )

    # -----------------------------------------------------
    # Compatibilidade com banco antigo
    # -----------------------------------------------------

    colunas = conexao.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    nomes_colunas = [
        coluna["name"]
        for coluna in colunas
    ]

    if "theme" not in nomes_colunas:
        conexao.execute(
            """
            ALTER TABLE users
            ADD COLUMN theme TEXT DEFAULT 'dark'
            """
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
        (
            login,
            login
        )
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

    try:

        if not os.path.exists(LOG_FILE):
            return []

        with open(
            LOG_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

        if not isinstance(
            dados,
            list
        ):
            return []

        return dados

    except (
        OSError,
        json.JSONDecodeError
    ):
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

    try:

        with open(
            LOG_FILE,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                logs,
                arquivo,
                indent=4,
                ensure_ascii=False
            )

    except OSError:
        pass


def obter_ip_cliente():

    forwarded = request.headers.get(
        "X-Forwarded-For",
        ""
    )

    if forwarded:

        primeiro_ip = (
            forwarded
            .split(",")[0]
            .strip()
        )

        if primeiro_ip:
            return primeiro_ip

    real_ip = request.headers.get(
        "X-Real-IP",
        ""
    ).strip()

    if real_ip:
        return real_ip

    return request.remote_addr or ""


def registrar_log(
    username=None,
    ip=None
):

    config = carregar_config()

    if ip is None:
        ip = obter_ip_cliente()

    navegador = request.headers.get(
        "User-Agent",
        ""
    )

    rota = request.path

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    logs = carregar_logs()

    logs.append(
        {
            "username": username or "",
            "ip": ip,
            "browser": navegador,
            "route": rota,
            "created_at": agora
        }
    )

    salvar_logs(logs)

    # Também salva no banco
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
                navegador,
                rota,
                agora
            )
        )

        conexao.commit()
        conexao.close()

    except sqlite3.Error:
        pass


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

        if member_id:
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
# HOME
# =========================================================

@app.route("/")
def index():

    config = carregar_config()

    usuario_logado = session.get(
        "member_authenticated",
        False
    )

    announcements = []

    if config.get(
        "announcements_enabled",
        True
    ):

        conexao = conectar_banco()

        announcements = conexao.execute(
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
        config=config,
        announcements=announcements,
        usuario_logado=usuario_logado
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    config = carregar_config()

    if request.method == "GET":

        return render_template(
            "login.html",
            config=config
        )

    login_digitado = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    admin_username = config.get(
        "admin_username",
        ADMIN_USERNAME
    )

    admin_password = config.get(
        "admin_password",
        ADMIN_PASSWORD
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if (
        login_digitado == admin_username
        and password == admin_password
    ):

        session.clear()

        session["member_authenticated"] = True
        session["member_username"] = admin_username
        session["member_id"] = 0
        session["is_admin"] = True
        session["admin_authenticated"] = True

        registrar_log(
            username=admin_username
        )

        return redirect("/")


    # -----------------------------------------------------
    # MEMBRO
    # -----------------------------------------------------

    usuario = buscar_usuario_por_login(
        login_digitado
    )

    if not usuario:

        return render_template(
            "login.html",
            config=config,
            erro=(
                "Usuário, Gmail ou senha "
                "incorretos."
            )
        )

    if usuario["status"] == "bloqueado":

        return render_template(
            "login.html",
            config=config,
            erro="Sua conta está bloqueada."
        )

    if not check_password_hash(
        usuario["password_hash"],
        password
    ):

        return render_template(
            "login.html",
            config=config,
            erro=(
                "Usuário, Gmail ou senha "
                "incorretos."
            )
        )

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE users
        SET
            last_login = ?,
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
    session["member_id"] = usuario["id"]
    session["member_username"] = usuario["username"]
    session["is_admin"] = False
    session["admin_authenticated"] = False

    registrar_log(
        username=usuario["username"]
    )

    # Depois do login o usuário volta
    # para a página inicial.
    return redirect("/")


# =========================================================
# CADASTRO
# =========================================================

@app.route(
    "/cadastro",
    methods=["GET", "POST"]
)
def cadastro():

    config = carregar_config()

    if request.method == "GET":

        return render_template(
            "cadastro.html",
            config=config
        )

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

    if not username:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Digite um username."
        )

    if not email:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Digite seu Gmail."
        )

    if not password:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Digite uma senha."
        )

    if password != password_confirm:

        return render_template(
            "cadastro.html",
            config=config,
            erro="As senhas não são iguais."
        )

    if username.lower() == (
        config.get(
            "admin_username",
            ADMIN_USERNAME
        ).lower()
    ):

        return render_template(
            "cadastro.html",
            config=config,
            erro="Esse username não está disponível."
        )

    existente = buscar_usuario_por_login(
        username
    )

    if existente:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Esse username já está em uso."
        )

    existente_email = buscar_usuario_por_login(
        email
    )

    if existente_email:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Esse Gmail já está cadastrado."
        )

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    senha_hash = generate_password_hash(
        password
    )

    try:

        conexao = conectar_banco()

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
                last_login,
                theme
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                username,
                senha_hash,
                1,
                0,
                "offline",
                agora,
                None,
                "dark"
            )
        )

        conexao.commit()
        conexao.close()

    except sqlite3.IntegrityError:

        return render_template(
            "cadastro.html",
            config=config,
            erro=(
                "Username ou Gmail "
                "já cadastrado."
            )
        )

    return redirect("/login")


# =========================================================
# PERFIL
# =========================================================

@app.route("/perfil")
def perfil():

    if not session.get(
        "member_authenticated",
        False
    ):
        return redirect("/login")

    member_id = session.get(
        "member_id"
    )

    # Admin não usa perfil de membro
    if session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    usuario = buscar_usuario_por_id(
        member_id
    )

    if not usuario:
        session.clear()
        return redirect("/login")

    return render_template(
        "perfil.html",
        usuario=usuario,
        config=carregar_config()
    )


# =========================================================
# CONFIGURAÇÕES DO MEMBRO
# =========================================================

@app.route(
    "/configuracoes",
    methods=["GET", "POST"]
)
def configuracoes():

    if not session.get(
        "member_authenticated",
        False
    ):
        return redirect("/login")

    if session.get(
        "is_admin",
        False
    ):
        return redirect("/admin/config")

    member_id = session.get(
        "member_id"
    )

    usuario = buscar_usuario_por_id(
        member_id
    )

    if not usuario:
        return redirect("/login")

    if request.method == "POST":

        theme = request.form.get(
            "theme",
            "dark"
        ).strip().lower()

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
                member_id
            )
        )

        conexao.commit()
        conexao.close()

        return redirect("/")

    return render_template(
        "configuracoes.html",
        usuario=usuario,
        config=carregar_config()
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    username = session.get(
        "member_username",
        ""
    )

    if username:

        conexao = conectar_banco()

        if not session.get(
            "is_admin",
            False
        ):

            conexao.execute(
                """
                UPDATE users
                SET status = 'offline'
                WHERE username = ?
                """,
                (username,)
            )

            conexao.commit()

        conexao.close()

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

    dados = request.get_json(
        silent=True
    ) or {}

    ip = dados.get(
        "ip",
        ""
    ).strip()

    if not ip:
        return jsonify({
            "ok": False
        })

    # O IP é armazenado apenas no
    # sistema administrativo.
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
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    if not session.get(
        "is_admin",
        False
    ):
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
        "admin.html",

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

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    usuario = buscar_usuario_por_id(
        user_id
    )

    if not usuario:
        return redirect("/admin")

    config = carregar_config()

    if request.method == "GET":

        return render_template(
            "editar_membro.html",
            usuario=usuario,
            config=config
        )

    level_text = request.form.get(
        "level",
        "1"
    ).strip()

    xp_text = request.form.get(
        "xp",
        "0"
    ).strip()

    status = request.form.get(
        "status",
        "offline"
    ).strip()

    theme = request.form.get(
        "theme",
        usuario["theme"] or "dark"
    ).strip().lower()

    try:

        level = int(
            level_text
        )

    except ValueError:

        return render_template(
            "editar_membro.html",
            usuario=usuario,
            config=config,
            erro=(
                "O level precisa ser "
                "um número."
            )
        )

    try:

        xp = int(
            xp_text
        )

    except ValueError:

        return render_template(
            "editar_membro.html",
            usuario=usuario,
            config=config,
            erro=(
                "O XP precisa ser "
                "um número."
            )
        )

    if level < 1:
        level = 1

    if xp < 0:
        xp = 0

    status_permitidos = [
        "online",
        "offline",
        "bloqueado"
    ]

    if status not in status_permitidos:
        status = "offline"

    if theme not in [
        "dark",
        "light"
    ]:
        theme = "dark"

    conexao = conectar_banco()

    # IMPORTANTE:
    # username, email e password_hash
    # nunca são alterados por esta rota.

    conexao.execute(
        """
        UPDATE users
        SET
            level = ?,
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


# =========================================================
# BLOQUEAR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/bloquear",
    methods=["POST"]
)
def bloquear_membro(user_id):

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE users
        SET status = 'bloqueado'
        WHERE id = ?
        """,
        (user_id,)
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

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE users
        SET status = 'offline'
        WHERE id = ?
        """,
        (user_id,)
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

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    conexao.execute(
        """
        DELETE FROM chat_messages
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect("/admin")


# =========================================================
# ADMIN: ANÚNCIOS
# =========================================================

@app.route(
    "/admin/anuncios",
    methods=["GET", "POST"]
)
def admin_anuncios():

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

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

        active = 1 if request.form.get(
            "active"
        ) else 0

        agora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        if title:

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
                    active,
                    agora
                )
            )

            conexao.commit()

        conexao.close()

        return redirect(
            "/admin/anuncios"
        )

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
        anuncios=anuncios,
        config=carregar_config()
    )


# =========================================================
# ADMIN: EDITAR ANÚNCIO
# =========================================================

@app.route(
    "/admin/anuncios/<int:announcement_id>/editar",
    methods=["POST"]
)
def editar_anuncio(announcement_id):

    if not session.get(
        "is_admin",
        False
    ):
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
        "%d/%m/%Y %H:%M:%S"
    )

    conexao = conectar_banco()

    conexao.execute(
        """
        UPDATE announcements
        SET
            title = ?,
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


# =========================================================
# ADMIN: EXCLUIR ANÚNCIO
# =========================================================

@app.route(
    "/admin/anuncios/<int:announcement_id>/excluir",
    methods=["POST"]
)
def excluir_anuncio(
    announcement_id
):

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM announcements
        WHERE id = ?
        """,
        (announcement_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect(
        "/admin/anuncios"
    )


# =========================================================
# ADMIN: BANNER
# =========================================================

@app.route(
    "/admin/banner",
    methods=["GET", "POST"]
)
def admin_banner():

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    config = carregar_config()

    if request.method == "POST":

        config["banner_enabled"] = (
            request.form.get(
                "banner_enabled"
            ) == "on"
        )

        config["banner_image"] = (
            request.form.get(
                "banner_image",
                ""
            ).strip()
        )

        config["banner_title"] = (
            request.form.get(
                "banner_title",
                ""
            ).strip()
        )

        config["banner_text"] = (
            request.form.get(
                "banner_text",
                ""
            ).strip()
        )

        config["banner_link"] = (
            request.form.get(
                "banner_link",
                ""
            ).strip()
        )

        salvar_config(config)

        return redirect(
            "/admin/banner"
        )

    return render_template(
        "admin_banner.html",
        config=config
    )


# =========================================================
# ADMIN: CONFIGURAÇÕES
# =========================================================

@app.route(
    "/admin/config",
    methods=["GET", "POST"]
)
def admin_config():

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    config = carregar_config()

    if request.method == "POST":

        config["site_name"] = request.form.get(
            "site_name",
            "EXPURG"
        ).strip()

        config["primary_color"] = request.form.get(
            "primary_color",
            "#e00000"
        ).strip()

        config["home_text"] = request.form.get(
            "home_text",
            ""
        ).strip()

        config["chat_enabled"] = (
            request.form.get(
                "chat_enabled"
            ) == "on"
        )

        config["announcements_enabled"] = (
            request.form.get(
                "announcements_enabled"
            ) == "on"
        )

        salvar_config(config)

        return redirect(
            "/admin/config"
        )

    return render_template(
        "admin_config.html",
        config=config
    )


# =========================================================
# ADMIN: RESTAURAR CONFIGURAÇÕES
# =========================================================

@app.route(
    "/admin/config/restaurar",
    methods=["POST"]
)
def restaurar_config():

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    config = CONFIG_PADRAO.copy()

    salvar_config(config)

    return redirect(
        "/admin/config"
    )


# =========================================================
# ADMIN: LIMPAR LOGS
# =========================================================

@app.route(
    "/admin/limpar-logs",
    methods=["POST"]
)
def limpar_logs():

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    try:

        with open(
            LOG_FILE,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                [],
                arquivo,
                indent=4,
                ensure_ascii=False
            )

    except OSError:
        pass

    try:

        conexao = conectar_banco()

        conexao.execute(
            "DELETE FROM access_logs"
        )

        conexao.commit()
        conexao.close()

    except sqlite3.Error:
        pass

    return redirect("/admin")


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/chat",
    methods=["GET", "POST"]
)
def chat():

    if not session.get(
        "member_authenticated",
        False
    ):
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
                "%d/%m/%Y %H:%M:%S"
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
        LIMIT 200
        """
    ).fetchall()

    conexao.close()

    return render_template(
        "chat.html",
        mensagens=mensagens,
        config=config
    )


# =========================================================
# ADMIN: EXCLUIR MENSAGEM
# =========================================================

@app.route(
    "/admin/chat/<int:message_id>/excluir",
    methods=["POST"]
)
def excluir_mensagem(message_id):

    if not session.get(
        "is_admin",
        False
    ):
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute(
        """
        DELETE FROM chat_messages
        WHERE id = ?
        """,
        (message_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect("/chat")


# =========================================================
# STATUS
# =========================================================

@app.route("/api/status")
def api_status():

    if not session.get(
        "is_admin",
        False
    ):
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