
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

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "EXPURG_SECRET_KEY_2026_RHUAN"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

        resultado = CONFIG_PADRAO.copy()
        resultado.update(config)

        return resultado

    except Exception:
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
            indent=4,
            ensure_ascii=False
        )


def conectar_banco():
    conexao = sqlite3.connect(
        DATABASE
    )

    conexao.row_factory = sqlite3.Row

    return conexao


def coluna_existe(cursor, tabela, coluna):
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            route TEXT,
            browser TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting TEXT UNIQUE,
            value TEXT
        )
    """)

    # Corrige bancos antigos automaticamente
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

    cursor.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (
        "admin",
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
            "admin",
            "admin@expurg.local",
            "123456",
            "admin",
            0,
            "ativo",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    else:

        # Garante que o administrador continue
        # com os dados corretos.
        cursor.execute("""
            UPDATE users
            SET password = ?,
                level = ?,
                status = ?
            WHERE username = ?
        """, (
            "123456",
            "admin",
            "ativo",
            "admin"
        ))

    conexao.commit()
    conexao.close()


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

    registrar_acesso()


@app.context_processor
def dados_globais():

    return {
        "config": carregar_config()
    }


def usuario_logado():
    return session.get(
        "usuario"
    )


def admin_logado():
    return session.get(
        "admin",
        False
    ) is True


@app.route("/")
def index():

    conexao = conectar_banco()

    anuncios = conexao.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    conexao.close()

    return render_template(
        "index.html",
        usuario=usuario_logado(),
        anuncios=anuncios
    )


@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

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

        # LOGIN DO ADMIN
        if (
            username == "admin"
            and password == "123456"
        ):

            session.clear()

            session["usuario"] = "admin"
            session["admin"] = True
            session["user_id"] = 1

            session.modified = True

            return redirect(
                url_for("index")
            )

        # LOGIN DE USUÁRIO NORMAL
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

        if username.lower() == "admin":

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
                "Conta criada com sucesso!",
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

    return render_template(
        "cadastro.html"
    )


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

    return render_template(
        "perfil.html",
        usuario=usuario
    )


@app.route("/configuracoes")
def configuracoes():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    return render_template(
        "configuracoes.html"
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


@app.route("/registrar-ip")
def registrar_ip():

    if not admin_logado():

        return jsonify({
            "erro": "Acesso negado"
        }), 403

    return jsonify({
        "ipv4": obter_ip_cliente()
    })


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

        config["site_name"] = request.form.get(
            "site_name",
            config["site_name"]
        )

        config["admin_name"] = request.form.get(
            "admin_name",
            config["admin_name"]
        )

        config["primary_color"] = request.form.get(
            "primary_color",
            config["primary_color"]
        )

        config["home_text"] = request.form.get(
            "home_text",
            config["home_text"]
        )

        config["theme"] = request.form.get(
            "theme",
            config["theme"]
        )

        config["show_ip"] = (
            request.form.get(
                "show_ip"
            ) == "on"
        )

        config["register_ip"] = (
            request.form.get(
                "register_ip"
            ) == "on"
        )

        config["banner_enabled"] = (
            request.form.get(
                "banner_enabled"
            ) == "on"
        )

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

        flash(
            "Configurações salvas.",
            "success"
        )

        return redirect(
            url_for("admin_config")
        )

    return render_template(
        "admin_config.html"
    )


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

        if titulo and conteudo:

            conexao.execute("""
                INSERT INTO announcements
                (
                    title,
                    content,
                    created_at
                )
                VALUES (?, ?, ?)
            """, (
                titulo,
                conteudo,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            conexao.commit()

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


@app.route(
    "/admin/anuncios/<int:announcement_id>/excluir",
    methods=["POST"]
)
def excluir_anuncio(
    announcement_id
):

    if not admin_logado():

        return redirect(
            url_for("login")
        )

    conexao = conectar_banco()

    conexao.execute("""
        DELETE FROM announcements
        WHERE id = ?
    """, (
        announcement_id,
    ))

    conexao.commit()
    conexao.close()

    return redirect(
        url_for("admin_anuncios")
    )


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

        config["banner_enabled"] = (
            request.form.get(
                "banner_enabled"
            ) == "on"
        )

        config["banner_title"] = request.form.get(
            "banner_title",
            ""
        )

        config["banner_text"] = request.form.get(
            "banner_text",
            ""
        )

        config["banner_image"] = request.form.get(
            "banner_image",
            ""
        )

        config["banner_link"] = request.form.get(
            "banner_link",
            ""
        )

        salvar_config(config)

        flash(
            "Banner atualizado.",
            "success"
        )

        return redirect(
            url_for("admin_banner")
        )

    return render_template(
        "admin_banner.html"
    )


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

    return redirect(
        url_for("chat")
    )


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

    conexao.close()

    return render_template(
        "editar_membro.html",
        usuario=usuario
    )


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

    conexao.execute("""
        UPDATE users
        SET status = 'bloqueado'
        WHERE id = ?
    """, (
        user_id,
    ))

    conexao.commit()
    conexao.close()

    return redirect(
        url_for("admin")
    )


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

    return redirect(
        url_for("admin")
    )


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

    if (
        usuario
        and usuario["username"] != "admin"
    ):

        conexao.execute("""
            DELETE FROM users
            WHERE id = ?
        """, (
            user_id,
        ))

        conexao.commit()

    conexao.close()

    return redirect(
        url_for("admin")
    )


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
                indent=4
            )

    except Exception:
        pass

    return redirect(
        url_for("admin")
    )


if __name__ == "__main__":

    criar_banco()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

