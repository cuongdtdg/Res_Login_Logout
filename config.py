import os
from decouple import config

# Database
DATABASE_URL = config("DATABASE_URL")

# JWT
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=1440, cast=int)

# Email
SMTP_SERVER = config("SMTP_SERVER")
SMTP_PORT = config("SMTP_PORT", cast=int)
SMTP_USERNAME = config("SMTP_USERNAME")
SMTP_PASSWORD = config("SMTP_PASSWORD")
FROM_EMAIL = config("FROM_EMAIL")
ADMIN_EMAIL = config("ADMIN_EMAIL", default="admin@example.com")

# OTP
OTP_EXPIRE_MINUTES = config("OTP_EXPIRE_MINUTES", default=5, cast=int)
SESSION_EXPIRE_MINUTES = config("SESSION_EXPIRE_MINUTES", default=5, cast=int)
AUTH_SESSION_EXPIRE_MINUTES = config("AUTH_SESSION_EXPIRE_MINUTES", default=1440, cast=int)

# Environment
ENVIRONMENT = config("ENVIRONMENT", default="development")

FRONTEND_ORIGINS = [
    o.strip() for o in config(
        "FRONTEND_ORIGINS",
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if o.strip()
]
# Thay 192.168.1.X bằng IP thật của máy chủ và máy client
