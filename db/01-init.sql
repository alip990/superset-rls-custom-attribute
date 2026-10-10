-- Superset metadata, plus a tiny company tree and a few check rows.
CREATE DATABASE superset;
CREATE DATABASE demo;
\connect demo

CREATE TABLE company (
  id int PRIMARY KEY,
  parent_id int REFERENCES company (id),
  title text NOT NULL
);

INSERT INTO company (id, parent_id, title) VALUES
  (1, NULL, 'کل کشور'),
  (2, 1, 'تهران'),
  (3, 1, 'قم');

CREATE TABLE app_user (
  username text PRIMARY KEY,
  full_name text NOT NULL,
  company_id int NOT NULL REFERENCES company (id)
);

INSERT INTO app_user (username, full_name, company_id) VALUES
  ('manager', 'مدیر کل', 1),
  ('ali', 'علی', 2),
  ('sara', 'سارا', 3);

CREATE TABLE checks (
  id serial PRIMARY KEY,
  company_id int NOT NULL REFERENCES company (id),
  amount int NOT NULL
);

INSERT INTO checks (company_id, amount) VALUES
  (2, 100), (2, 40),
  (3, 70), (3, 10),
  (1, 5);

CREATE ROLE demo_reader LOGIN PASSWORD 'demo_reader';
GRANT CONNECT ON DATABASE demo TO demo_reader;
GRANT USAGE ON SCHEMA public TO demo_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO demo_reader;
