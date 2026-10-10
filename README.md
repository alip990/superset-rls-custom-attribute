# Superset RLS with guest-token attributes

Apache Superset 6.1 plus a small host app. Each visitor picks a user and a company. The dashboard then shows only that company and the companies under it.

The guest token's `rls` list stays empty. The company ids travel as a real user attribute:

```json
{
  "user": {
    "username": "ali",
    "attributes": {"allowed_companies": [2]}
  },
  "rls": []
}
```

Released Superset 6.1 drops `user.attributes` (its guest-token schema excludes unknown fields) and has no Jinja macro to read them. `guest_user_attributes.py` backports both from Superset master: the API keeps the field, and dataset SQL can call `get_guest_user_attribute()`. The macro is registered on `ExtraCache` and in `ExtraCache.regex`, so the resolved company list is part of the query cache key. The data cache can stay on. Two companies do not share one cached result.

## Start

```bash
docker compose up --build -d
docker compose logs -f superset-bootstrap
```

Wait for `BOOTSTRAP_DONE`.

| | |
|---|---|
| Host app | http://localhost:8097 |
| Superset | http://localhost:8098 (`admin` / `admin`) |
| Postgres | `127.0.0.1:5443` (`postgres` / `postgres`, database `demo`) |

`docker compose down` keeps the data. `docker compose down -v` loads the seeder again on the next start.

## What you should see

The seeder is three companies and five check rows:

| Company | id | parent | amount |
|---|---|---|---|
| کل کشور | 1 | — | 5 |
| تهران | 2 | 1 | 140 |
| قم | 3 | 1 | 80 |

| User | Sees |
|---|---|
| مدیر سامانه (`__admin__`) | whichever company you pick, plus its children |
| مدیر کل (`manager`) | 1, 2, and 3 → total **225** |
| علی (`ali`) | 2 only → total **140** |
| سارا (`sara`) | 3 only → total **80** |

The header shows `allowed_companies`. The big number is `SUM(amount)` after the filter.

## How the filter is applied

The host reads `company` and `app_user`, walks the subtree, and asks Superset for a guest token. The virtual dataset `checks_scoped` is:

```sql
SELECT * FROM checks
WHERE 1=1
{% set allowed_companies = get_guest_user_attribute('allowed_companies', escape_result=False) %}
{% if allowed_companies %}
  AND company_id IN {{ allowed_companies | where_in }}
{% else %}
  AND 1=0
{% endif %}
```

`escape_result=False` because `where_in` quotes the values itself. An empty attribute matches nothing (`AND 1=0`), so a token without the attribute does not return every row.

`superset_config.py` installs the backport at startup:

```python
def FLASK_APP_MUTATOR(app):
    from guest_user_attributes import install
    install()
```

## Layout

```text
Dockerfile                  Superset 6.1.0 and psycopg2
superset_config.py          embedding, Jinja, the backport
guest_user_attributes.py    keeps user.attributes and adds the macro
bootstrap.py                dataset, chart, dashboard, EmbedGuest
db/01-init.sql              three companies, three users, five checks
embed-app/                  host that mints the guest token
```

Demo passwords are fixed on purpose. Change `SUPERSET_SECRET_KEY`, `GUEST_TOKEN_JWT_SECRET`, and the database passwords before any shared deployment.

## فارسی

<div dir="rtl" lang="fa">

<h2>محدود کردن داشبورد با ویژگی توکن مهمان</h2>

<p>فهرست <code dir="ltr">rls</code> در توکن مهمان خالی می‌ماند. شناسهٔ شرکت‌هایی که کاربر حق دیدنشان را دارد داخل خود توکن می‌رود:</p>

<pre dir="ltr"><code>{"user": {"username": "ali", "attributes": {"allowed_companies": [2]}}, "rls": []}</code></pre>

<p>سوپرست ۶.۱ این فیلد را دور می‌ریزد و تابعی برای خواندنش ندارد. فایل <code dir="ltr">guest_user_attributes.py</code> هر دو را از شاخهٔ master برمی‌گرداند: API فیلد را نگه می‌دارد، و در SQL تابع <code dir="ltr">get_guest_user_attribute</code> در دسترس است. چون این تابع در کلید کش پرس‌وجو هم ثبت می‌شود، کش داده روشن می‌ماند و نتیجهٔ یک شرکت به شرکت دیگر داده نمی‌شود.</p>

<h3>اجرا</h3>

<pre dir="ltr"><code>docker compose up --build -d</code></pre>

<p>اپ میزبان: <code dir="ltr">http://localhost:8097</code>. سوپرست: <code dir="ltr">http://localhost:8098</code> با <code dir="ltr">admin</code> / <code dir="ltr">admin</code>.</p>

<p>سه شرکت در سیدر هست. کل کشور (۱) پنج واحد، تهران (۲) صد و چهل، قم (۳) هشتاد. مدیر کل هر سه را می‌بیند و جمع ۲۲۵ است. علی فقط تهران را می‌بیند و جمع ۱۴۰ است. سارا فقط قم را می‌بیند و جمع ۸۰ است.</p>

<h3>فیلتر داخل دیتاست</h3>

<pre dir="ltr"><code>SELECT * FROM checks
WHERE 1=1
{% set allowed_companies = get_guest_user_attribute('allowed_companies', escape_result=False) %}
{% if allowed_companies %}
  AND company_id IN {{ allowed_companies | where_in }}
{% else %}
  AND 1=0
{% endif %}</code></pre>

<p><code dir="ltr">escape_result=False</code> لازم است چون <code dir="ltr">where_in</code> خودش مقدارها را نقل‌قول می‌کند. اگر ویژگی در توکن نباشد، شرط <code dir="ltr">AND 1=0</code> هیچ سطری برنمی‌گرداند.</p>

<p>شرکت و کاربر در <code dir="ltr">db/01-init.sql</code> ساخته می‌شوند. این مخزن نسخهٔ پشتیبان واقعی ندارد.</p>

</div>
