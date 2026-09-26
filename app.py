import os
import json
import sqlite3
import ipaddress
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "EXPURG_SECRET_KEY_2026_RHUAN"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False


# =========================================================
# CAMINHOS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE = os.path.join(
    BASE_DIR,
    "database.db"
)

CONFIG_FILE = os.path.join(
    BASE_DIR,
    "config.json"
)

LOG_FILE = os.path.join(
    BASE_DIR,
    "access_logs.json"
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
    "home_text": "THE BEST COMMUNITY",

    "register_ip": True,
    "register_browser": True,
    "max_logs": 1000,
    "auto_clean_logs": False,

    "show_access_time": True,
    "show_access_route": True,

    "google_login": False,
    "google_client_id": "",
    "google_client_secret": "",

    "google_show_name": True,
    "google_show_email": True,
    "google_register_time": True,

    "session_time": 60,
    "auto_logout": False,

    "confirm_delete_logs": True,

    "show_cards": True,
    "show_ip": True,
    "show_users": True,
    "show_logs": True,
    "show_files": True,
    "show_server_status": True,

    "recent_accesses": 8,

    "admin_username": "admin",
    "admin_password": "123456",

    "banner_enabled": True,
    "banner_image": "",
    "banner_title": "THE WORLD IS YOURS",
    "banner_text": "",
    "banner_link": "",

    "chat_enabled": True,
    "announcements_enabled": True
}


# =========================================================
# CONFIGURAÇÕES
# =========================================================

def carregar_config():
    """
    Carrega o config.json.
    Se alguma configuração estiver faltando,
    utiliza o valor padrão.
    """

    if not os.path.exists(CONFIG_FILE):

        config_nova = CONFIG_PADRAO.copy()

        try:
            salvar_config(config_nova)
        except Exception:
            pass

        return config_nova

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            config = json.load(arquivo)

        if not isinstance(config, dict):
            config = {}

        resultado = CONFIG_PADRAO.copy()
        resultado.update(config)

        return resultado

    except Exception:

        return CONFIG_PADRAO.copy()


def salvar_config(config):
    """
    Salva todas as configurações no config.json.
    """

    config_final = CONFIG_PADRAO.copy()

    if isinstance(config, dict):
        config_final.update(config)

    arquivo_temporario = CONFIG_FILE + ".tmp"

    with open(
        arquivo_temporario,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            config_final,
            arquivo,
            indent=4,
            ensure_ascii=False
        )

    os.replace(
        arquivo_temporario,
        CONFIG_FILE
    )


# =========================================================
# BANCO
# =========================================================

def conectar_banco():

    conexao = sqlite3.connect(
        DATABASE,
        timeout=10
    )

    conexao.row_factory = sqlite3.Row

    return conexao


def coluna_existe(
    cursor,
    tabela,
    coluna
):

    cursor.execute(
        f"PRAGMA table_info({tabela})"
    )

    colunas = cursor.fetchall()

    return any(
        coluna_atual[1] == coluna
        for coluna_atual in colunas
    )


def adicionar_coluna_se_faltar(
    cursor,
    tabela,
    coluna,
    tipo,
    padrao=None
):

    if coluna_existe(
        cursor,
        tabela,
        coluna
    ):
        return

    comando = (
        f"ALTER TABLE {tabela} "
        f"ADD COLUMN {coluna} {tipo}"
    )

    if padrao is not None:
        comando += f" DEFAULT {padrao}"

    cursor.execute(comando)


def criar_banco():

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # -----------------------------------------------------
    # USUÁRIOS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT,
            level TEXT DEFAULT 'user',
            xp INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ativo',
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # LOGS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            route TEXT,
            browser TEXT,
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # ANÚNCIOS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            image TEXT,
            link TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # CONFIGURAÇÕES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting TEXT UNIQUE,
            value TEXT
        )
    """)

    # =====================================================
    # MIGRAÇÃO
    # =====================================================

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "password",
        "TEXT"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "email",
        "TEXT"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "level",
        "TEXT",
        "'user'"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "xp",
        "INTEGER",
        "0"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "status",
        "TEXT",
        "'ativo'"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "users",
        "created_at",
        "TEXT"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "announcements",
        "image",
        "TEXT"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "announcements",
        "link",
        "TEXT"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "announcements",
        "active",
        "INTEGER",
        "1"
    )

    adicionar_coluna_se_faltar(
        cursor,
        "announcements",
        "created_at",
        "TEXT"
    )

    # =====================================================
    # ADMIN PRINCIPAL
    # =====================================================

    config = carregar_config()

    admin_username = str(
        config.get(
            "admin_username",
            "admin"
        )
    ).strip()

    admin_password = str(
        config.get(
            "admin_password",
            "123456"
        )
    )

    if not admin_username:
        admin_username = "admin"

    if not admin_password:
        admin_password = "123456"

    cursor.execute("""
        SELECT *
        FROM users
        WHERE username = ?
        LIMIT 1
    """, (
        admin_username,
    ))

    admin = cursor.fetchone()

    if not admin:

        cursor.execute("""
            INSERT INTO users
            (
                username,
                email,
                password,
                level,
                xp,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            admin_username,
            "admin@expurg.local",
            admin_password,
            "admin",
            0,
            "ativo",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    else:

        cursor.execute("""
            UPDATE users
            SET password = ?,
                level = 'admin',
                status = 'ativo'
            WHERE username = ?
        """, (
            admin_password,
            admin_username
        ))

    conexao.commit()
    conexao.close()


# =========================================================
# IP DO CLIENTE
# =========================================================

def obter_ip_cliente():

    forwarded_for = request.headers.get(
        "X-Forwarded-For",
        ""
    ).strip()

    if forwarded_for:

        ips = [
            ip.strip()
            for ip in forwarded_for.split(",")
            if ip.strip()
        ]

        for ip in ips:

            try:

                endereco = ipaddress.ip_address(ip)

                if endereco.version == 4:
                    return str(endereco)

            except ValueError:
                continue

    real_ip = request.headers.get(
        "X-Real-IP",
        ""
    ).strip()

    if real_ip:

        try:

            endereco = ipaddress.ip_address(real_ip)

            if endereco.version == 4:
                return str(endereco)

        except ValueError:
            pass

    ip_local = (
        request.remote_addr or ""
    ).strip()

    if ip_local:

        try:

            endereco = ipaddress.ip_address(ip_local)

            if endereco.version == 4:
                return str(endereco)

        except ValueError:
            pass

    return "Desconhecido"


# =========================================================
# LOG DE ACESSO
# =========================================================

def registrar_acesso():

    config = carregar_config()

    if not config.get(
        "register_ip",
        True
    ):
        return

    ip = obter_ip_cliente()

    browser = request.headers.get(
        "User-Agent",
        "Desconhecido"
    )

    if not config.get(
        "register_browser",
        True
    ):
        browser = "Oculto"


    rota = request.path

    data = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO access_logs
            (
                ip,
                route,
                browser,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            ip,
            rota,
            browser,
            data
        ))

        max_logs = int(
            config.get(
                "max_logs",
                1000
            ) or 1000
        )

        if max_logs > 0:

            conexao.execute("""
                DELETE FROM access_logs
                WHERE id NOT IN (
                    SELECT id
                    FROM access_logs
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (
                max_logs,
            ))

        conexao.commit()
        conexao.close()

    except Exception:
        pass


@app.before_request
def antes_da_requisicao():

    if request.path.startswith(
        "/static"
    ):
        return

    if request.method == "OPTIONS":
        return

    registrar_acesso()


# =========================================================
# VARIÁVEIS GLOBAIS
# =========================================================

@app.context_processor
def dados_globais():

    return {
        "config": carregar_config()
    }


# =========================================================
# SESSÃO
# =========================================================

def usuario_logado():

    return session.get(
        "usuario"
    )


def admin_logado():

    return session.get(
        "admin",
        False
    ) is True


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
def index():

    conexao = conectar_banco()

    config = carregar_config()

    anuncios = []

    if config.get(
        "announcements_enabled",
        True
    ):

        anuncios = conexao.execute("""
            SELECT *
            FROM announcements
            WHERE active = 1
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

    conexao.close()

    return render_template(
        "index.html",
        usuario=usuario_logado(),
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

    config = carregar_config()

    admin_username = str(
        config.get(
            "admin_username",
            "admin"
        )
    ).strip()

    admin_password = str(
        config.get(
            "admin_password",
            "123456"
        )
    )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Preencha usuário e senha.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        if (
            username == admin_username
            and password == admin_password
        ):

            conexao = conectar_banco()

            usuario_admin = conexao.execute("""
                SELECT *
                FROM users
                WHERE username = ?
                LIMIT 1
            """, (
                admin_username,
            )).fetchone()

            conexao.close()

            session.clear()

            session["usuario"] = admin_username
            session["admin"] = True

            if usuario_admin:
                session["user_id"] = usuario_admin["id"]
            else:
                session["user_id"] = 1

            session.modified = True

            return redirect(
                url_for("index")
            )

        # -------------------------------------------------
        # USUÁRIO NORMAL
        # -------------------------------------------------

        conexao = conectar_banco()

        usuario = conexao.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            LIMIT 1
        """, (
            username,
            password
        )).fetchone()

        conexao.close()

        if usuario is None:

            flash(
                "Usuário ou senha incorretos.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if usuario["status"] != "ativo":

            flash(
                "Sua conta está bloqueada.",
                "error"
            )

            return render_template(
                "login.html"
            )

        session.clear()

        session["usuario"] = usuario["username"]
        session["user_id"] = usuario["id"]
        session["admin"] = (
            usuario["level"] == "admin"
        )

        session.modified = True

        return redirect(
            url_for("index")
        )

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

        if (
            not username
            or not password
        ):

            flash(
                "Preencha os campos obrigatórios.",
                "error"
            )

            return redirect(
                url_for("cadastro")
            )

        config = carregar_config()

        admin_username = str(
            config.get(
                "admin_username",
                "admin"
            )
        ).strip().lower()

        if username.lower() == admin_username:

            flash(
                "Esse nome de usuário não está disponível.",
                "error"
            )

            return redirect(
                url_for("cadastro")
            )

        conexao = conectar_banco()

        try:

            conexao.execute("""
                INSERT INTO users
                (
                    username,
                    email,
                    password,
                    level,
                    xp,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                email,
                password,
                "user",
                0,
                "ativo",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            conexao.commit()
            conexao.close()

            flash(
                "SEJA BEM VINDO !",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            conexao.close()

            flash(
                "Esse usuário já existe.",
                "error"
            )

            return redirect(
                url_for("cadastro")
            )

        except Exception:

            conexao.close()

            flash(
                "Não foi possível criar a conta.",
                "error"
            )

            return redirect(
                url_for("cadastro")
            )

    return render_template(
        "cadastro.html"
    )


# =========================================================
# PERFIL
# =========================================================

@app.route("/perfil")
def perfil():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session.get("user_id"),
    )).fetchone()

    conexao.close()

    if not usuario:

        session.clear()

        return redirect(
            url_for("login")
        )

    return render_template(
        "perfil.html",
        usuario=usuario
    )


# =========================================================
# CONFIGURAÇÕES DO USUÁRIO
# =========================================================

@app.route("/configuracoes")
def configuracoes():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    return render_template(
        "configuracoes.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# =========================================================
# IPV4
# =========================================================

@app.route("/registrar-ip")
def registrar_ip():

    if not admin_logado():

        return jsonify({
            "erro": "Acesso negado"
        }), 403

    return jsonify({
        "ipv4": obter_ip_cliente()
    })


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    usuarios = conexao.execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
    """).fetchall()

    logs = conexao.execute("""
        SELECT *
        FROM access_logs
        ORDER BY id DESC
        LIMIT 100
    """).fetchall()

    total_usuarios = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM users
    """).fetchone()["total"]

    total_acessos = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM access_logs
    """).fetchone()["total"]

    ips_unicos = conexao.execute("""
        SELECT COUNT(DISTINCT ip) AS total
        FROM access_logs
        WHERE ip IS NOT NULL
        AND ip != ''
    """).fetchone()["total"]

    ultimo_acesso = conexao.execute("""
        SELECT *
        FROM access_logs
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    conexao.close()

    return render_template(
        "admin_dashboard.html",
        usuarios=usuarios,
        logs=logs,
        total_usuarios=total_usuarios,
        total_acessos=total_acessos,
        ips_unicos=ips_unicos,
        ultimo_acesso=ultimo_acesso
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

        return redirect(
            url_for("login")
        )

    config = carregar_config()

    if request.method == "POST":

        # -------------------------------------------------
        # TEXTOS
        # -------------------------------------------------

        config["site_name"] = request.form.get(
            "site_name",
            config.get("site_name", "EXPURG")
        ).strip()

        config["admin_name"] = request.form.get(
            "admin_name",
            config.get("admin_name", "ADMIN")
        ).strip()

        config["home_text"] = request.form.get(
            "home_text",
            config.get(
                "home_text",
                "THE BEST COMMUNITY"
            )
        ).strip()

        config["logo"] = request.form.get(
            "logo",
            config.get("logo", "")
        ).strip()

        # -------------------------------------------------
        # COR
        # -------------------------------------------------

        primary_color = request.form.get(
            "primary_color",
            config.get(
                "primary_color",
                "#e00000"
            )
        ).strip()

        if not primary_color:
            primary_color = "#e00000"

        config["primary_color"] = primary_color

        # -------------------------------------------------
        # TEMA
        # -------------------------------------------------

        config["theme"] = request.form.get(
            "theme",
            config.get("theme", "dark")
        ).strip()

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        novo_admin_username = request.form.get(
            "admin_username",
            config.get(
                "admin_username",
                "admin"
            )
        ).strip()

        novo_admin_password = request.form.get(
            "admin_password",
            config.get(
                "admin_password",
                "123456"
            )
        )

        if not novo_admin_username:
            novo_admin_username = "admin"

        if not novo_admin_password:
            flash(
                "A senha do administrador não pode ficar vazia.",
                "error"
            )

            return redirect(
                url_for("admin_config")
            )

        antigo_admin_username = str(
            config.get(
                "admin_username",
                "admin"
            )
        )

        config["admin_username"] = novo_admin_username
        config["admin_password"] = novo_admin_password

        # -------------------------------------------------
        # TOGGLES
        # -------------------------------------------------

        config["show_ip"] = (
            request.form.get("show_ip")
            in ("on", "1", "true")
        )

        config["register_ip"] = (
            request.form.get("register_ip")
            in ("on", "1", "true")
        )

        config["register_browser"] = (
            request.form.get("register_browser")
            in ("on", "1", "true")
        )

        config["auto_clean_logs"] = (
            request.form.get("auto_clean_logs")
            in ("on", "1", "true")
        )

        config["show_access_time"] = (
            request.form.get("show_access_time")
            in ("on", "1", "true")
        )

        config["show_access_route"] = (
            request.form.get("show_access_route")
            in ("on", "1", "true")
        )

        config["google_login"] = (
            request.form.get("google_login")
            in ("on", "1", "true")
        )

        config["google_show_name"] = (
            request.form.get("google_show_name")
            in ("on", "1", "true")
        )

        config["google_show_email"] = (
            request.form.get("google_show_email")
            in ("on", "1", "true")
        )

        config["google_register_time"] = (
            request.form.get("google_register_time")
            in ("on", "1", "true")
        )

        config["auto_logout"] = (
            request.form.get("auto_logout")
            in ("on", "1", "true")
        )

        config["confirm_delete_logs"] = (
            request.form.get("confirm_delete_logs")
            in ("on", "1", "true")
        )

        config["show_cards"] = (
            request.form.get("show_cards")
            in ("on", "1", "true")
        )

        config["show_users"] = (
            request.form.get("show_users")
            in ("on", "1", "true")
        )

        config["show_logs"] = (
            request.form.get("show_logs")
            in ("on", "1", "true")
        )

        config["show_files"] = (
            request.form.get("show_files")
            in ("on", "1", "true")
        )

        config["show_server_status"] = (
            request.form.get("show_server_status")
            in ("on", "1", "true")
        )

        config["banner_enabled"] = (
            request.form.get("banner_enabled")
            in ("on", "1", "true")
        )

        config["chat_enabled"] = (
            request.form.get("chat_enabled")
            in ("on", "1", "true")
        )

        config["announcements_enabled"] = (
            request.form.get("announcements_enabled")
            in ("on", "1", "true")
        )

        # -------------------------------------------------
        # GOOGLE
        # -------------------------------------------------

        config["google_client_id"] = request.form.get(
            "google_client_id",
            config.get(
                "google_client_id",
                ""
            )
        ).strip()

        config["google_client_secret"] = request.form.get(
            "google_client_secret",
            config.get(
                "google_client_secret",
                ""
            )
        ).strip()

        # -------------------------------------------------
        # NÚMEROS
        # -------------------------------------------------

        try:

            max_logs = int(
                request.form.get(
                    "max_logs",
                    config.get(
                        "max_logs",
                        1000
                    )
                )
            )

            if max_logs < 0:
                max_logs = 0

        except (
            TypeError,
            ValueError
        ):

            max_logs = 1000

        config["max_logs"] = max_logs

        try:

            recent_accesses = int(
                request.form.get(
                    "recent_accesses",
                    config.get(
                        "recent_accesses",
                        8
                    )
                )
            )

            if recent_accesses < 1:
                recent_accesses = 1

        except (
            TypeError,
            ValueError
        ):

            recent_accesses = 8

        config["recent_accesses"] = recent_accesses

        try:

            session_time = int(
                request.form.get(
                    "session_time",
                    config.get(
                        "session_time",
                        60
                    )
                )
            )

            if session_time < 1:
                session_time = 60

        except (
            TypeError,
            ValueError
        ):

            session_time = 60

        config["session_time"] = session_time

        # -------------------------------------------------
        # SALVAR
        # -------------------------------------------------

        try:

            salvar_config(config)

            # ---------------------------------------------
            # Atualiza o administrador no banco
            # ---------------------------------------------

            conexao = conectar_banco()

            admin_existente = conexao.execute("""
                SELECT *
                FROM users
                WHERE username = ?
                LIMIT 1
            """, (
                antigo_admin_username,
            )).fetchone()

            if admin_existente:

                conflito = conexao.execute("""
                    SELECT id
                    FROM users
                    WHERE username = ?
                    AND id != ?
                    LIMIT 1
                """, (
                    novo_admin_username,
                    admin_existente["id"]
                )).fetchone()

                if conflito:

                    conexao.rollback()
                    conexao.close()

                    config["admin_username"] = antigo_admin_username
                    salvar_config(config)

                    flash(
                        "Esse nome de administrador já está sendo usado por outro membro.",
                        "error"
                    )

                    return redirect(
                        url_for("admin_config")
                    )

                conexao.execute("""
                    UPDATE users
                    SET username = ?,
                        password = ?,
                        level = 'admin',
                        status = 'ativo'
                    WHERE id = ?
                """, (
                    novo_admin_username,
                    novo_admin_password,
                    admin_existente["id"]
                ))

            else:

                conflito = conexao.execute("""
                    SELECT id
                    FROM users
                    WHERE username = ?
                    LIMIT 1
                """, (
                    novo_admin_username,
                )).fetchone()

                if conflito:

                    conexao.rollback()
                    conexao.close()

                    config["admin_username"] = antigo_admin_username
                    salvar_config(config)

                    flash(
                        "Esse nome de administrador já está sendo usado.",
                        "error"
                    )

                    return redirect(
                        url_for("admin_config")
                    )

                conexao.execute("""
                    INSERT INTO users
                    (
                        username,
                        email,
                        password,
                        level,
                        xp,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    novo_admin_username,
                    "admin@expurg.local",
                    novo_admin_password,
                    "admin",
                    0,
                    "ativo",
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

            conexao.commit()
            conexao.close()

            # Atualiza a sessão para não deslogar o admin
            session["usuario"] = novo_admin_username
            session["admin"] = True
            session.modified = True

            flash(
                "Todas as configurações foram salvas com sucesso.",
                "success"
            )

        except Exception as erro:

            flash(
                f"Erro ao salvar configurações: {erro}",
                "error"
            )

        return redirect(
            url_for("admin_config")
        )

    return render_template(
        "admin_config.html"
    )


# =========================================================
# ANÚNCIOS
# =========================================================

@app.route(
    "/admin/anuncios",
    methods=["GET", "POST"]
)
def admin_anuncios():

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    if request.method == "POST":

        titulo = request.form.get(
            "title",
            ""
        ).strip()

        conteudo = request.form.get(
            "content",
            ""
        ).strip()

        imagem = request.form.get(
            "image",
            ""
        ).strip()

        link = request.form.get(
            "link",
            ""
        ).strip()

        ativo = (
            1
            if request.form.get("active")
            in ("1", "on", "true")
            else 0
        )

        if not titulo:

            conexao.close()

            flash(
                "Digite um título para o anúncio.",
                "error"
            )

            return redirect(
                url_for("admin_anuncios")
            )

        if not conteudo:

            conexao.close()

            flash(
                "Digite o conteúdo do anúncio.",
                "error"
            )

            return redirect(
                url_for("admin_anuncios")
            )

        try:

            conexao.execute("""
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
            """, (
                titulo,
                conteudo,
                imagem,
                link,
                ativo,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            conexao.commit()

            flash(
                "Anúncio criado com sucesso.",
                "success"
            )

        except Exception as erro:

            conexao.rollback()

            flash(
                f"Erro ao criar anúncio: {erro}",
                "error"
            )

    anuncios = conexao.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
    """).fetchall()

    conexao.close()

    return render_template(
        "admin_anuncios.html",
        anuncios=anuncios
    )


# =========================================================
# EDITAR ANÚNCIO
# =========================================================

@app.route(
    "/admin/anuncios/<int:announcement_id>/editar",
    methods=["GET", "POST"]
)
def editar_anuncio(announcement_id):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    anuncio = conexao.execute("""
        SELECT *
        FROM announcements
        WHERE id = ?
        LIMIT 1
    """, (
        announcement_id,
    )).fetchone()

    if not anuncio:

        conexao.close()

        flash(
            "Anúncio não encontrado.",
            "error"
        )

        return redirect(
            url_for("admin_anuncios")
        )

    if request.method == "POST":

        titulo = request.form.get(
            "title",
            ""
        ).strip()

        conteudo = request.form.get(
            "content",
            ""
        ).strip()

        imagem = request.form.get(
            "image",
            ""
        ).strip()

        link = request.form.get(
            "link",
            ""
        ).strip()

        ativo = (
            1
            if request.form.get("active")
            in ("1", "on", "true")
            else 0
        )

        if not titulo or not conteudo:

            conexao.close()

            flash(
                "Título e conteúdo são obrigatórios.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_anuncio",
                    announcement_id=announcement_id
                )
            )

        try:

            conexao.execute("""
                UPDATE announcements
                SET title = ?,
                    content = ?,
                    image = ?,
                    link = ?,
                    active = ?
                WHERE id = ?
            """, (
                titulo,
                conteudo,
                imagem,
                link,
                ativo,
                announcement_id
            ))

            conexao.commit()
            conexao.close()

            flash(
                "Anúncio atualizado com sucesso.",
                "success"
            )

            return redirect(
                url_for("admin_anuncios")
            )

        except Exception as erro:

            conexao.rollback()
            conexao.close()

            flash(
                f"Erro ao atualizar anúncio: {erro}",
                "error"
            )

            return redirect(
                url_for("admin_anuncios")
            )

    conexao.close()

    return render_template(
        "editar_anuncio.html",
        anuncio=anuncio
    )


# =========================================================
# EXCLUIR ANÚNCIO
# =========================================================

@app.route(
    "/admin/anuncios/<int:announcement_id>/excluir",
    methods=["POST"]
)
def excluir_anuncio(announcement_id):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    try:

        conexao.execute("""
            DELETE FROM announcements
            WHERE id = ?
        """, (
            announcement_id,
        ))

        conexao.commit()

        flash(
            "Anúncio excluído.",
            "success"
        )

    except Exception as erro:

        conexao.rollback()

        flash(
            f"Erro ao excluir anúncio: {erro}",
            "error"
        )

    conexao.close()

    return redirect(
        url_for("admin_anuncios")
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

        return redirect(
            url_for("login")
        )

    config = carregar_config()

    if request.method == "POST":

        banner_enabled = request.form.get(
            "banner_enabled",
            "0"
        )

        config["banner_enabled"] = (
            banner_enabled in (
                "1",
                "on",
                "true"
            )
        )

        config["banner_title"] = request.form.get(
            "banner_title",
            ""
        ).strip()

        config["banner_text"] = request.form.get(
            "banner_text",
            ""
        ).strip()

        config["banner_image"] = request.form.get(
            "banner_image",
            ""
        ).strip()

        config["banner_link"] = request.form.get(
            "banner_link",
            ""
        ).strip()

        try:

            salvar_config(config)

            flash(
                "Banner atualizado com sucesso.",
                "success"
            )

        except Exception as erro:

            flash(
                f"Erro ao salvar o banner: {erro}",
                "error"
            )

        return redirect(
            url_for("admin_banner")
        )

    return render_template(
        "admin_banner.html"
    )


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/chat",
    methods=["GET", "POST"]
)
def chat():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    config = carregar_config()

    if not config.get(
        "chat_enabled",
        True
    ):

        return redirect(
            url_for("index")
        )

    conexao = conectar_banco()

    if request.method == "POST":

        mensagem = request.form.get(
            "message",
            ""
        ).strip()

        if mensagem:

            mensagem = mensagem[:2000]

            conexao.execute("""
                INSERT INTO chat_messages
                (
                    username,
                    message,
                    created_at
                )
                VALUES (?, ?, ?)
            """, (
                usuario_logado(),
                mensagem,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            conexao.commit()

    mensagens = conexao.execute("""
        SELECT *
        FROM chat_messages
        ORDER BY id ASC
        LIMIT 200
    """).fetchall()

    conexao.close()

    return render_template(
        "chat.html",
        mensagens=mensagens
    )


# =========================================================
# EXCLUIR MENSAGEM DO CHAT
# =========================================================

@app.route(
    "/admin/chat/<int:message_id>/excluir",
    methods=["POST"]
)
def excluir_mensagem(message_id):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    conexao.execute("""
        DELETE FROM chat_messages
        WHERE id = ?
    """, (
        message_id,
    ))

    conexao.commit()
    conexao.close()

    flash(
        "Mensagem excluída.",
        "success"
    )

    return redirect(
        url_for("chat")
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

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    if not usuario:

        conexao.close()

        flash(
            "Usuário não encontrado.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            usuario["username"]
        ).strip()

        email = request.form.get(
            "email",
            usuario["email"] or ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        level = request.form.get(
            "level",
            usuario["level"]
        )

        xp = request.form.get(
            "xp",
            usuario["xp"]
        )

        status = request.form.get(
            "status",
            usuario["status"]
        )

        try:
            xp = int(xp)
        except (
            TypeError,
            ValueError
        ):
            xp = 0

        if not username:

            conexao.close()

            flash(
                "O nome de usuário não pode ficar vazio.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_membro",
                    user_id=user_id
                )
            )

        if usuario["username"] == "admin":

            username = "admin"
            level = "admin"
            status = "ativo"

        try:

            if password:

                conexao.execute("""
                    UPDATE users
                    SET username = ?,
                        email = ?,
                        password = ?,
                        level = ?,
                        xp = ?,
                        status = ?
                    WHERE id = ?
                """, (
                    username,
                    email,
                    password,
                    level,
                    xp,
                    status,
                    user_id
                ))

            else:

                conexao.execute("""
                    UPDATE users
                    SET username = ?,
                        email = ?,
                        level = ?,
                        xp = ?,
                        status = ?
                    WHERE id = ?
                """, (
                    username,
                    email,
                    level,
                    xp,
                    status,
                    user_id
                ))

            conexao.commit()
            conexao.close()

            flash(
                "Membro atualizado.",
                "success"
            )

            return redirect(
                url_for("admin")
            )

        except sqlite3.IntegrityError:

            conexao.rollback()
            conexao.close()

            flash(
                "Esse nome de usuário já está em uso.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_membro",
                    user_id=user_id
                )
            )

        except Exception as erro:

            conexao.rollback()
            conexao.close()

            flash(
                f"Erro ao atualizar membro: {erro}",
                "error"
            )

            return redirect(
                url_for(
                    "editar_membro",
                    user_id=user_id
                )
            )

    conexao.close()

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

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT username
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    config = carregar_config()

    admin_username = config.get(
        "admin_username",
        "admin"
    )

    if usuario and usuario["username"] == admin_username:

        conexao.close()

        flash(
            "O administrador principal não pode ser bloqueado.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    conexao.execute("""
        UPDATE users
        SET status = 'bloqueado'
        WHERE id = ?
    """, (
        user_id,
    ))

    conexao.commit()
    conexao.close()

    flash(
        "Membro bloqueado.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# DESBLOQUEAR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/desbloquear",
    methods=["POST"]
)
def desbloquear_membro(user_id):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    conexao.execute("""
        UPDATE users
        SET status = 'ativo'
        WHERE id = ?
    """, (
        user_id,
    ))

    conexao.commit()
    conexao.close()

    flash(
        "Membro desbloqueado.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# EXCLUIR MEMBRO
# =========================================================

@app.route(
    "/admin/membro/<int:user_id>/excluir",
    methods=["POST"]
)
def excluir_membro(user_id):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT username
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    if usuario is None:

        conexao.close()

        flash(
            "Usuário não encontrado.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    config = carregar_config()

    admin_username = config.get(
        "admin_username",
        "admin"
    )

    if usuario["username"] == admin_username:

        conexao.close()

        flash(
            "O administrador principal não pode ser excluído.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    conexao.execute("""
        DELETE FROM users
        WHERE id = ?
    """, (
        user_id,
    ))

    conexao.commit()
    conexao.close()

    flash(
        "Membro excluído.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# LIMPAR LOGS
# =========================================================

@app.route(
    "/admin/logs/limpar",
    methods=["POST"]
)
def limpar_logs():

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    conexao.execute(
        "DELETE FROM access_logs"
    )

    conexao.commit()
    conexao.close()

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

    except Exception:
        pass

    flash(
        "Logs limpos.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# CRIAR BANCO
# =========================================================

criar_banco()


# =========================================================
# EXECUÇÃO LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )