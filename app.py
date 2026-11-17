import os
import sqlite3
from flask import Flask, g, redirect, render_template, request, url_for, flash, abort

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "links.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#4f6bed',
    position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    position INTEGER NOT NULL DEFAULT 0
);
"""


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    try:
        with app.app_context():
            get_db().executescript(SCHEMA)
            get_db().commit()
    except sqlite3.OperationalError as exc:
        d = os.path.dirname(DB_PATH) or "."
        try:
            st = os.stat(d)
            info = f"propriétaire {st.st_uid}:{st.st_gid}, droits {oct(st.st_mode & 0o777)}"
        except OSError as e:
            info = f"inaccessible ({e})"
        raise SystemExit(
            f"[linkboard] Impossible d'ouvrir la base {DB_PATH} : {exc}\n"
            f"[linkboard] Processus uid={os.getuid()} gid={os.getgid()} ; dossier {d} : {info}"
        )


def normalize_url(url):
    url = url.strip()
    if url and "://" not in url:
        url = "http://" + url
    return url


# ---------- Tableau de bord ----------

@app.route("/")
def index():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY position, name").fetchall()
    links = db.execute("SELECT * FROM links ORDER BY position, title COLLATE NOCASE").fetchall()
    grouped = {c["id"]: [] for c in categories}
    uncategorized = []
    for l in links:
        if l["category_id"] in grouped:
            grouped[l["category_id"]].append(l)
        else:
            uncategorized.append(l)
    return render_template("index.html", categories=categories, grouped=grouped,
                           uncategorized=uncategorized, total=len(links))


# ---------- Liens ----------

@app.route("/links/new", methods=["GET", "POST"])
@app.route("/links/<int:link_id>/edit", methods=["GET", "POST"])
def link_form(link_id=None):
    db = get_db()
    link = None
    if link_id is not None:
        link = db.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()
        if link is None:
            abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = normalize_url(request.form.get("url", ""))
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id") or None
        position = int(request.form.get("position") or 0)
        if not title or not url:
            flash("Le titre et l'URL sont obligatoires.", "error")
        else:
            if link:
                db.execute("UPDATE links SET title=?, url=?, description=?, category_id=?, position=? WHERE id=?",
                           (title, url, description, category_id, position, link_id))
                flash(f"Lien « {title} » modifié.", "ok")
            else:
                db.execute("INSERT INTO links (title, url, description, category_id, position) VALUES (?,?,?,?,?)",
                           (title, url, description, category_id, position))
                flash(f"Lien « {title} » ajouté.", "ok")
            db.commit()
            return redirect(url_for("index"))

    categories = db.execute("SELECT * FROM categories ORDER BY position, name").fetchall()
    preselect = request.args.get("category", type=int)
    return render_template("link_form.html", link=link, categories=categories, preselect=preselect)


@app.post("/links/<int:link_id>/delete")
def link_delete(link_id):
    db = get_db()
    db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    db.commit()
    flash("Lien supprimé.", "ok")
    return redirect(request.referrer or url_for("index"))


# ---------- Catégories ----------

@app.route("/categories", methods=["GET", "POST"])
@app.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
def categories(cat_id=None):
    db = get_db()
    edit = None
    if cat_id is not None:
        edit = db.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
        if edit is None:
            abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        color = request.form.get("color", "#4f6bed")
        position = int(request.form.get("position") or 0)
        if not name:
            flash("Le nom est obligatoire.", "error")
        else:
            try:
                if edit:
                    db.execute("UPDATE categories SET name=?, color=?, position=? WHERE id=?",
                               (name, color, position, cat_id))
                    flash(f"Catégorie « {name} » modifiée.", "ok")
                else:
                    db.execute("INSERT INTO categories (name, color, position) VALUES (?,?,?)",
                               (name, color, position))
                    flash(f"Catégorie « {name} » créée.", "ok")
                db.commit()
                return redirect(url_for("categories"))
            except sqlite3.IntegrityError:
                flash(f"La catégorie « {name} » existe déjà.", "error")

    cats = db.execute("""
        SELECT c.*, COUNT(l.id) AS link_count
        FROM categories c LEFT JOIN links l ON l.category_id = c.id
        GROUP BY c.id ORDER BY c.position, c.name
    """).fetchall()
    return render_template("categories.html", categories=cats, edit=edit)


@app.post("/categories/<int:cat_id>/delete")
def category_delete(cat_id):
    db = get_db()
    db.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    db.commit()
    flash("Catégorie supprimée (ses liens sont passés dans « Sans catégorie »).", "ok")
    return redirect(url_for("categories"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
