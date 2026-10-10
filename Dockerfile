FROM apache/superset:6.1.0
USER root
RUN uv pip install --python /app/.venv/bin/python --no-cache psycopg2-binary==2.9.13
COPY superset_config.py guest_user_attributes.py /app/pythonpath/
ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py
USER superset
