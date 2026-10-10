"""Pick a seeded user and one company in their subtree, then embed the dashboard.

The guest token's rls list stays empty. The company ids go in
user.attributes.allowed_companies. Superset 6.1 keeps that field only because
guest_user_attributes.py is installed.
"""
import os
import psycopg2
import requests
from flask import Flask, jsonify, render_template, request, session

SUPERSET = os.environ.get("SUPERSET_URL", "http://superset:8088")
SUPERSET_PUBLIC = os.environ.get("SUPERSET_PUBLIC_URL", "http://localhost:8098")
COMPANY_DB = os.environ.get(
    "COMPANY_DB_URL", "postgresql://demo_reader:demo_reader@db:5432/demo")
ADMIN = "__admin__"

TREE_SQL = """
WITH RECURSIVE company_tree AS (
    SELECT id, parent_id, 0 AS level FROM company WHERE id = %(company_id)s
    UNION ALL
    SELECT c.id, c.parent_id, ct.level + 1
    FROM company c
    INNER JOIN company_tree ct ON c.parent_id = ct.id
)
SELECT ct.id, c.title, ct.level
FROM company_tree ct
JOIN company c ON c.id = ct.id
ORDER BY ct.level, c.title
"""

app = Flask(__name__, template_folder=".")
app.secret_key = "host-app-demo"
app.config["SESSION_COOKIE_NAME"] = "rls_demo_session"


def query(sql, params=None):
    with psycopg2.connect(COMPANY_DB) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def app_users():
    rows = query("""
        SELECT u.username, u.full_name, u.company_id, c.title
        FROM app_user u JOIN company c ON c.id = u.company_id
        ORDER BY c.id, u.username
    """)
    return [{"username": u, "name": n, "company_id": cid, "company": title}
            for u, n, cid, title in rows]


def company_subtree(company_id):
    if company_id is None:
        return []
    return [{"id": cid, "title": title, "level": level}
            for cid, title, level in query(TREE_SQL, {"company_id": company_id})]


def selectable_companies(username):
    if username == ADMIN:
        roots = query("SELECT id FROM company WHERE parent_id IS NULL")
        return [company for (root,) in roots for company in company_subtree(root)]
    rows = query("SELECT company_id FROM app_user WHERE username = %s", (username,))
    if not rows:
        return None
    return company_subtree(rows[0][0])


def current_selection():
    username = session.get("user", ADMIN)
    companies = selectable_companies(username)
    if companies is None:
        username, companies = ADMIN, selectable_companies(ADMIN) or []
    allowed = {c["id"] for c in companies}
    company = session.get("company")
    if company not in allowed:
        company = companies[0]["id"] if companies else None
    return username, company


def superset_session():
    s = requests.Session()
    tok = s.post(f"{SUPERSET}/api/v1/security/login",
                 json={"username": "admin", "password": "admin", "provider": "db"},
                 timeout=30).json()["access_token"]
    s.headers["Authorization"] = f"Bearer {tok}"
    s.headers["X-CSRFToken"] = s.get(f"{SUPERSET}/api/v1/security/csrf_token/", timeout=30).json()["result"]
    s.headers["Referer"] = SUPERSET
    return s


def embedded_uuid(s):
    return s.get(f"{SUPERSET}/api/v1/dashboard/checks/embedded", timeout=30).json()["result"]["uuid"]


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


@app.get("/")
def index():
    username, company = current_selection()
    return render_template(
        "index.html", users=app_users(), admin=ADMIN, current_user=username,
        companies=selectable_companies(username) or [], current_company=company,
        dashboard_uuid=embedded_uuid(superset_session()), superset_url=SUPERSET_PUBLIC,
    )


@app.get("/companies")
def companies():
    username = request.args.get("user")
    if not isinstance(username, str) or not username:
        return jsonify(error="Unknown user"), 400
    rows = selectable_companies(username)
    if rows is None:
        return jsonify(error="Unknown user"), 400
    return jsonify(companies=rows)


@app.post("/login")
def login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("user"), str) or not body["user"]:
        return jsonify(error="Unknown user"), 400
    username = body["user"]
    allowed_rows = selectable_companies(username)
    if allowed_rows is None:
        return jsonify(error="Unknown user"), 400
    allowed = {c["id"] for c in allowed_rows}
    company = body.get("company")
    session["user"] = username
    try:
        chosen = int(company) if company not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify(error="Unknown company"), 400
    session["company"] = chosen if chosen in allowed else None
    return jsonify(ok=True)


@app.get("/guest-token")
def guest_token():
    username, company = current_selection()
    allowed = [c["id"] for c in company_subtree(company)]
    s = superset_session()
    body = {
        "user": {"username": username, "first_name": username, "last_name": "",
                 "attributes": {"allowed_companies": allowed}},
        "resources": [{"type": "dashboard", "id": embedded_uuid(s)}],
        "rls": [],
    }
    r = s.post(f"{SUPERSET}/api/v1/security/guest_token/", json=body, timeout=30)
    r.raise_for_status()
    return jsonify(token=r.json()["token"], rls=[], allowed_companies=allowed)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, threaded=True)
