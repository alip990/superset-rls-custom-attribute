"""Connection, one scoped dataset, one dashboard, embedding. Re-running updates in place."""
import json
import os
import requests

URL = os.environ.get("SUPERSET_URL", "http://superset:8088")
s = requests.Session()


def login():
    tok = s.post(f"{URL}/api/v1/security/login", json={
        "username": "admin", "password": "admin", "provider": "db", "refresh": True,
    }).json()["access_token"]
    s.headers["Authorization"] = f"Bearer {tok}"
    s.headers["X-CSRFToken"] = s.get(f"{URL}/api/v1/security/csrf_token/").json()["result"]
    s.headers["Referer"] = URL


def api(method, path, **kw):
    r = s.request(method, f"{URL}/api/v1/{path}", **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:800]}")
    return r.json()


def find(resource, col, value):
    q = json.dumps({"filters": [{"col": col, "opr": "eq", "value": value}]})
    res = api("GET", f"{resource}/?q={q}")["result"]
    return res[0]["id"] if res else None


login()

db_id = find("database", "database_name", "Demo DB") or api("POST", "database/", json={
    "database_name": "Demo DB",
    "sqlalchemy_uri": "postgresql+psycopg2://demo_reader:demo_reader@db:5432/demo",
    "expose_in_sqllab": True,
})["id"]

SQL = """SELECT * FROM checks
WHERE 1=1
{% set allowed_companies = get_guest_user_attribute('allowed_companies', escape_result=False) %}
{% if allowed_companies %}
  AND company_id IN {{ allowed_companies | where_in }}
{% else %}
  AND 1=0
{% endif %}"""

ds = find("dataset", "table_name", "checks_scoped")
body = {"database": db_id, "schema": "public", "table_name": "checks_scoped", "sql": SQL}
if ds:
    api("PUT", f"dataset/{ds}", json={"sql": SQL})
    api("PUT", f"dataset/{ds}/refresh")
else:
    ds = api("POST", "dataset/", json=body)["id"]

SUM_AMOUNT = {"expressionType": "SQL", "sqlExpression": "SUM(amount)", "label": "مجموع"}


def chart(name, viz, params):
    cid = find("chart", "slice_name", name)
    params = {"viz_type": viz, "datasource": f"{ds}__table", "adhoc_filters": [], **params}
    payload = {"slice_name": name, "viz_type": viz, "datasource_id": ds, "datasource_type": "table",
               "params": json.dumps(params)}
    if cid:
        api("PUT", f"chart/{cid}", json=payload)
        return cid
    return api("POST", "chart/", json=payload)["id"]


charts = {
    "total": chart("مجموع", "big_number_total", {"metric": SUM_AMOUNT, "y_axis_format": ",d"}),
    "by_company": chart("به تفکیک شرکت", "table", {
        "query_mode": "aggregate", "groupby": ["company_id"], "metrics": [SUM_AMOUNT],
        "all_columns": [], "row_limit": 100, "order_desc": True, "server_pagination": False,
    }),
}

pos = {
    "DASHBOARD_VERSION_KEY": "v2",
    "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
    "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": ["ROW-0"], "parents": ["ROOT_ID"]},
    "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": "پایش به تفکیک شرکت"}},
    "ROW-0": {"type": "ROW", "id": "ROW-0", "children": ["CHART-total", "CHART-by_company"],
              "parents": ["ROOT_ID", "GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"}},
    "CHART-total": {"type": "CHART", "id": "CHART-total", "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", "ROW-0"],
                    "meta": {"chartId": charts["total"], "width": 4, "height": 40}},
    "CHART-by_company": {"type": "CHART", "id": "CHART-by_company", "children": [],
                         "parents": ["ROOT_ID", "GRID_ID", "ROW-0"],
                         "meta": {"chartId": charts["by_company"], "width": 8, "height": 40}},
}
dash_body = {"dashboard_title": "پایش به تفکیک شرکت", "slug": "checks", "published": True,
             "position_json": json.dumps(pos), "json_metadata": json.dumps({"refresh_frequency": 0})}
dash_id = find("dashboard", "slug", "checks")
if dash_id:
    api("PUT", f"dashboard/{dash_id}", json=dash_body)
else:
    dash_id = api("POST", "dashboard/", json=dash_body)["id"]
for cid in charts.values():
    api("PUT", f"chart/{cid}", json={"dashboards": [dash_id]})
embedded = api("POST", f"dashboard/{dash_id}/embedded", json={"allowed_domains": []})["result"]["uuid"]
print("EMBEDDED_DASHBOARD_UUID", embedded)

from superset.app import create_app  # noqa: E402

app = create_app()
with app.app_context():
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable

    guest = sm.find_role("EmbedGuest") or sm.add_role("EmbedGuest")
    for pv in sm.find_role("Gamma").permissions:
        sm.add_permission_role(guest, pv)
    table = db.session.get(SqlaTable, ds)
    pv = sm.find_permission_view_menu("datasource_access", table.get_perm())
    if pv:
        sm.add_permission_role(guest, pv)
    db.session.commit()

print("BOOTSTRAP_DONE dashboard_id=", dash_id)
