import databases
import sqlalchemy
from config import DATABASE_URL

# Database connection
database = databases.Database(DATABASE_URL)

# SQLAlchemy metadata
metadata = sqlalchemy.MetaData()

# Define tables
users_table = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()")),
    sqlalchemy.Column("name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String(255), unique=True, nullable=False),
    sqlalchemy.Column("phone", sqlalchemy.String(20), unique=True, nullable=False),
    sqlalchemy.Column("password_hash", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("role", sqlalchemy.String(50), default="user"),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True),
    sqlalchemy.Column("is_approved", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("approved_at", sqlalchemy.DateTime, nullable=True),
    sqlalchemy.Column("approved_by", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
)

temp_registrations_table = sqlalchemy.Table(
    "temp_registrations",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()")),
    sqlalchemy.Column("name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("phone", sqlalchemy.String(20), nullable=False),
    sqlalchemy.Column("password_hash", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("otp_code", sqlalchemy.String(6), nullable=False),
    sqlalchemy.Column("otp_expires_at", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
)

temp_sessions_table = sqlalchemy.Table(
    "temp_sessions",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()")),
    sqlalchemy.Column("user_id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("otp_code", sqlalchemy.String(6), nullable=False),
    sqlalchemy.Column("otp_expires_at", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
)

auth_sessions_table = sqlalchemy.Table(
    "auth_sessions",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()")),
    sqlalchemy.Column("user_id", sqlalchemy.dialects.postgresql.UUID(as_uuid=True), 
                     sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("session_token", sqlalchemy.Text, unique=True, nullable=False),
    sqlalchemy.Column("expires_at", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
)

# Create engine for table creation
engine = sqlalchemy.create_engine(DATABASE_URL)

async def connect_db():
    """Connect to database"""
    await database.connect()

async def disconnect_db():
    """Disconnect from database"""
    await database.disconnect()

def create_tables():
    """Create all tables"""
    metadata.create_all(engine)
