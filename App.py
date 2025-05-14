from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "ClaseSuperSecreta"

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

def get_db_connection():
    conn = sqlite3.connect("blog.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )""")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
    conn.commit()
    conn.close()

# Modelo User
class User(UserMixin):
    def __init__(self, id, username, password, name=None, email=None):
        self.id = id
        self.username = username
        self.password = password
        self.name = name
        self.email = email

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['password'], user['name'], user['email'])
        return None

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['password'], user['name'], user['email'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

@app.route("/")
def index():
    conn = get_db_connection()
    posts = conn.execute("""
        SELECT posts.*, users.username 
        FROM posts JOIN users ON posts.user_id = users.id 
        ORDER BY posts.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", posts=posts)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (name, email, username, password) VALUES (?, ?, ?, ?)",
                         (name, email, username, password))
            conn.commit()
            flash("Usuario registrado correctamente. Inicia sesión.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("El nombre de usuario o correo ya está en uso.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_by_username(username)
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Credenciales incorrectas", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión", "info")
    return redirect(url_for("login"))

@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    conn = get_db_connection()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn.execute("INSERT INTO posts (title, content, user_id) VALUES (?, ?, ?)",
                     (title, content, current_user.id))
        conn.commit()
        flash("Post publicado correctamente", "success")
        return redirect(url_for("dashboard"))

    posts = conn.execute("SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC",
                         (current_user.id,)).fetchall()
    conn.close()
    return render_template("dashboard.html", posts=posts, user=current_user)

@app.route("/editar/<int:post_id>", methods=['GET', 'POST'])
@login_required
def editar(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post or post['user_id'] != current_user.id:
        flash("No autorizado", "danger")
        return redirect(url_for("dashboard"))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn.execute("UPDATE posts SET title = ?, content = ? WHERE id = ?",
                     (title, content, post_id))
        conn.commit()
        flash("Post actualizado", "info")
        return redirect(url_for("dashboard"))
    
    conn.close()
    return render_template("editar_post.html", post=post)

@app.route("/delete/<int:post_id>")
@login_required
def delete(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post and post['user_id'] == current_user.id:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        flash("Post eliminado", "warning")
    else:
        flash("No autorizado o post no encontrado", "danger")
    conn.close()
    return redirect(url_for("dashboard"))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
