# routes/users.py
from flask import Blueprint, request, render_template, jsonify, flash, redirect, url_for
from utils import db
from utils.logger import logger
from zk import ZK
from config import POINTEUSE_IP, POINTEUSE_PORT

bp = Blueprint("users", __name__, url_prefix="/users")

@bp.route("/")
def list_users():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    per_page = 10
    offset = (page - 1) * per_page

    total = db.fetchone("SELECT COUNT(*) as c FROM Utilisateurs")['c'] or 0
    users = db.fetchall("""
        SELECT id, Code_Utilisateur, Nom_Prenom, Nombre_Tickets
        FROM Utilisateurs
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))

    total_pages = (total + per_page - 1) // per_page
    return render_template("Utilisateur.html", utilisateurs=users, page=page, total_pages=total_pages)

@bp.route("/add", methods=["POST"])
def add_user():
    code = request.form.get("Code_Utilisateur")
    name = request.form.get("Nom_Prenom")
    if not code or not name:
        flash("Code et nom requis", "danger")
        return redirect(url_for("users.list_users"))

    try:
        db.execute("INSERT INTO Utilisateurs (Code_Utilisateur, Nom_Prenom, Nombre_Tickets) VALUES (?, ?, 1)", (code, name))
        # Sync to pointeuse
        zk = ZK(POINTEUSE_IP, port=POINTEUSE_PORT, timeout=10)
        conn = zk.connect()
        try:
            conn.set_user(uid=int(code), name=name)
        finally:
            conn.disconnect()
        flash("Utilisateur ajouté.", "success")
    except Exception as e:
        logger.exception("Erreur ajout utilisateur: %s", e)
        flash(str(e), "danger")
    return redirect(url_for("users.list_users"))

@bp.route("/delete", methods=["POST"])
def delete_user():
    uid = request.form.get("id")
    try:
        db.execute("DELETE FROM Utilisateurs WHERE id = ?", (uid,))
        return jsonify(success=True)
    except Exception as e:
        logger.exception("Erreur delete_user: %s", e)
        return jsonify(success=False, error=str(e))
