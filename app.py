import os
import json
import re
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
# APLICAÇÃO
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-temporaria-local"
)


# =========================================================
# ADMIN
# =========================================================

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "123456"
)


# =========================================================
# ARQUIVOS
# =========================================================

LOG_FILE = "access_logs.json"

CONFIG_FILE = "config.json"

DATABASE_FILE = "database.db"


# =========================================================
# CONFIGURAÇÃO PADRÃO
# =========================================================

DEFAULT_CONFIG = {

    "site_name": "DEMON",

    "admin_name": "RHUAN",

    "theme": "dark",

    "primary_color": "#8b0000",

    "logo": "",

    "home_text": "WELCOME TO THE UNDERGROUND",

    "register_ip": True,

    "register_browser": True,

    "max_logs": 500,

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

    "admin_password": ADMIN_PASSWORD
}


# =========================================================
# CONFIGURAÇÃO
# =========================================================

def carregar_config():

    if not os.path.exists(CONFIG_FILE):

        config = DEFAULT_CONFIG.copy()

        salvar_config(config)

        return config

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

            if isinstance(dados, dict):

                config = DEFAULT_CONFIG.copy()

                config.update(dados)

                return config

    except (
        json.JSONDecodeError,
        OSError
    ):

        pass

    return DEFAULT_CONFIG.copy()


def salvar_config(config):

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

            last_login TEXT

        )
        """
    )

    conexao.commit()

    conexao.close()


# =========================================================
# USUÁRIOS
# =========================================================

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
            login.lower()
        )
    ).fetchone()

    conexao.close()

    return usuario


def buscar_usuario_por_username(username):

    conexao = conectar_banco()

    usuario = conexao.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (
            username,
        )
    ).fetchone()

    conexao.close()

    return usuario


def buscar_usuario_por_email(email):

    conexao = conectar_banco()

    usuario = conexao.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (
            email.lower(),
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
# VALIDAÇÃO
# =========================================================

def email_valido(email):

    padrao = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(
        padrao,
        email
    ) is not None


def username_valido(username):

    if not 3 <= len(username) <= 30:

        return False

    return re.match(
        r"^[a-zA-Z0-9_.]+$",
        username
    ) is not None


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

            dados = json.load(arquivo)

            if isinstance(dados, list):

                return dados

    except (
        json.JSONDecodeError,
        OSError
    ):

        pass

    return []


def salvar_logs(logs):

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


def registrar_log(
    ip=None,
    navegador=None,
    rota=None
):

    config = carregar_config()

    logs = carregar_logs()

    registro = {

        "ip": ip,

        "browser": navegador,

        "navegador": navegador,

        "route": rota,

        "rota": rota,

        "time": datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        ),

        "data": datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    }

    logs.append(registro)

    max_logs = config.get(
        "max_logs",
        500
    )

    if len(logs) > max_logs:

        logs = logs[-max_logs:]

    salvar_logs(logs)


# =========================================================
# CONTEXTO GLOBAL
# =========================================================

@app.context_processor
def contexto_global():

    return {

        "usuario_logado":
            session.get(
                "member_authenticated",
                False
            ),

        "usuario_admin":
            session.get(
                "is_admin",
                False
            ),

        "usuario_nome":
            session.get(
                "member_username"
            )

    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def inicio():

    config = carregar_config()

    return render_template(
        "index.html",
        config=config
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

    # =====================================================
    # ADMIN
    # =====================================================

    admin_username = config.get(
        "admin_username",
        ADMIN_USERNAME
    )

    admin_password = config.get(
        "admin_password",
        ADMIN_PASSWORD
    )

    if (
        login_digitado == admin_username
        and password == admin_password
    ):

        session.clear()

        session["member_authenticated"] = True

        session["member_username"] = admin_username

        session["is_admin"] = True

        session["admin_authenticated"] = True

        session["member_id"] = 0

        return redirect("/")

    # =====================================================
    # USUÁRIO NORMAL
    # =====================================================

    usuario = buscar_usuario_por_login(
        login_digitado
    )

    if not usuario:

        return render_template(
            "login.html",
            config=config,
            erro="Usuário, Gmail ou senha incorretos."
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
            erro="Usuário, Gmail ou senha incorretos."
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
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    password_confirm = request.form.get(
        "password_confirm",
        ""
    )

    if not username or not email or not password:

        return render_template(
            "cadastro.html",
            config=config,
            erro="Preencha todos os campos."
        )

    if not username_valido(username):

        return render_template(
            "cadastro.html",
            config=config,
            erro="Usuário inválido."
        )

    if not email_valido(email):

        return render_template(
            "cadastro.html",
            config=config,
            erro="Digite um Gmail válido."
        )

    if len(password) < 6:

        return render_template(
            "cadastro.html",
            config=config,
            erro="A senha precisa ter pelo menos 6 caracteres."
        )

    if password != password_confirm:

        return render_template(
            "cadastro.html",
            config=config,
            erro="As senhas não são iguais."
        )

    if buscar_usuario_por_username(username):

        return render_template(
            "cadastro.html",
            config=config,
            erro="Esse usuário já existe."
        )

    if buscar_usuario_por_email(email):

        return render_template(
            "cadastro.html",
            config=config,
            erro="Esse Gmail já está cadastrado."
        )

    password_hash = generate_password_hash(
        password
    )

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    conexao = conectar_banco()

    conexao.execute(
        """
        INSERT INTO users (

            email,
            username,
            password_hash,
            level,
            xp,
            status,
            created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            username,
            password_hash,
            1,
            0,
            "offline",
            agora
        )
    )

    conexao.commit()

    conexao.close()

    return render_template(
        "login.html",
        config=config,
        cadastro_sucesso=True
    )


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

    usuario = None

    member_id = session.get(
        "member_id"
    )

    if member_id != 0:

        conexao = conectar_banco()

        usuario = conexao.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (
                member_id,
            )
        ).fetchone()

        conexao.close()

    return render_template(
        "perfil.html",
        config=carregar_config(),
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

    session.clear()

    return redirect("/")


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

    ips_unicos = set()

    for log in logs:

        ip = log.get("ip")

        if ip:

            ips_unicos.add(ip)

    ultimo_acesso = None

    if logs:

        ultimo_acesso = logs[-1]

    config = carregar_config()

    return render_template(

        "admin.html",

        logs=logs,

        ips_unicos=ips_unicos,

        total_acessos=len(logs),

        total_ips=len(ips_unicos),

        ultimo_acesso=ultimo_acesso,

        usuarios=usuarios,

        total_usuarios=len(usuarios),

        config=config

    )


# =========================================================
# LIMPAR LOGS
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
        (
            user_id,
        )
    )

    conexao.commit()

    conexao.close()

    return redirect("/admin")


# =========================================================
# CONFIGURAÇÕES
# =========================================================

@app.route(
    "/admin/config",
    methods=["POST"]
)
def atualizar_config():

    if not session.get(
        "is_admin",
        False
    ):

        return redirect("/")

    config = carregar_config()

    site_name = request.form.get(
        "site_name"
    )

    if site_name is not None:

        config["site_name"] = site_name.strip()

    admin_name = request.form.get(
        "admin_name"
    )

    if admin_name is not None:

        config["admin_name"] = admin_name.strip()

    home_text = request.form.get(
        "home_text"
    )

    if home_text is not None:

        config["home_text"] = home_text.strip()

    primary_color = request.form.get(
        "primary_color"
    )

    if primary_color is not None:

        config["primary_color"] = primary_color.strip()

    admin_username = request.form.get(
        "admin_username"
    )

    if admin_username:

        config["admin_username"] = admin_username.strip()

    admin_password = request.form.get(
        "admin_password"
    )

    if admin_password:

        config["admin_password"] = admin_password

    salvar_config(config)

    return redirect("/admin")


# =========================================================
# RESTAURAR CONFIG
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

    salvar_config(
        DEFAULT_CONFIG.copy()
    )

    return redirect("/admin")


# =========================================================
# REGISTRAR IP
# =========================================================

@app.route(
    "/registrar-ip",
    methods=["POST"]
)
def registrar_ip():

    config = carregar_config()

    if not config.get(
        "register_ip",
        True
    ):

        return jsonify({
            "success": True
        })

    ip = request.form.get(
        "ip"
    )

    if not ip:

        ip = request.remote_addr

    navegador = request.form.get(
        "browser"
    )

    rota = request.form.get(
        "route"
    )

    registrar_log(
        ip=ip,
        navegador=navegador,
        rota=rota
    )

    return jsonify({
        "success": True
    })


# =========================================================
# INICIALIZAR
# =========================================================

inicializar_banco()


# =========================================================
# EXECUTAR
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