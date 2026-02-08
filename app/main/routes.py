from __future__ import annotations

import os

from flask import Blueprint, current_app, jsonify, render_template, send_from_directory

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("main/index.html")


@bp.get("/healthz")
def healthz():
    return jsonify(ok=True)


@bp.get("/favicon.ico")
def favicon():
    # Serve an existing static image as favicon to avoid 404 noise.
    icon_dir = os.path.join(current_app.static_folder, "images", "caricatures")
    return send_from_directory(icon_dir, "genie.png")


@bp.get("/firebase-messaging-sw.js")
def firebase_messaging_sw():
    return send_from_directory(current_app.static_folder, "firebase-messaging-sw.js")
