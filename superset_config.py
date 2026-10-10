import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-demo-secret-key-please-rotate")
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:postgres@db:5432/superset"

REDIS_URL = "redis://redis:6379"
CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_DEFAULT_TIMEOUT": 300,
                "CACHE_KEY_PREFIX": "superset_", "CACHE_REDIS_URL": f"{REDIS_URL}/0"}
# get_guest_user_attribute() is registered on ExtraCache and in ExtraCache.regex,
# so the company list is part of the query cache key. The data cache can stay on.
DATA_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_KEY_PREFIX": "superset_data_"}

BABEL_DEFAULT_LOCALE = "fa"
LANGUAGES = {
    "fa": {"flag": "ir", "name": "فارسی"},
    "en": {"flag": "us", "name": "English"},
}

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

GUEST_ROLE_NAME = "EmbedGuest"
GUEST_TOKEN_JWT_SECRET = os.environ.get("GUEST_TOKEN_JWT_SECRET", "demo-guest-token-secret")
GUEST_TOKEN_JWT_EXP_SECONDS = 600
ENABLE_CORS = True
CORS_OPTIONS = {"supports_credentials": True, "allow_headers": ["*"], "resources": ["*"],
                "origins": [os.environ.get("HOST_ORIGIN", "http://localhost:8097")]}
TALISMAN_ENABLED = False
HTTP_HEADERS = {"X-Frame-Options": "ALLOWALL"}
FAB_ADD_SECURITY_API = True

# 6.1.0 drops user.attributes and has no macro for them. guest_user_attributes.py
# backports both from Superset master.
def FLASK_APP_MUTATOR(app):  # noqa: N802
    from guest_user_attributes import install

    install()
