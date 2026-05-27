import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          SERIAL PRIMARY KEY,
                session_id  VARCHAR(255) NOT NULL,
                role        VARCHAR(50)  NOT NULL,
                content     TEXT         NOT NULL,
                token_count INTEGER      DEFAULT 0,
                created_at  TIMESTAMP    DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
            ON chat_messages(session_id)
        """))
    logger.info("DB: chat_messages table ready")


async def save_message(
    session_id: str,
    role: str,
    content: str,
    token_count: int = 0,
) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO chat_messages
                    (session_id, role, content, token_count, created_at)
                VALUES
                    (:session_id, :role, :content, :token_count, :created_at)
            """),
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "token_count": token_count,
                "created_at": datetime.utcnow(),
            }
        )
        await session.commit()
        logger.debug(f"Saved message [{role}] session={session_id}")


async def load_history(
    session_id: str,
    limit: int = 50,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT role, content
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at ASC
                LIMIT :limit
            """),
            {"session_id": session_id, "limit": limit}
        )
        rows = result.fetchall()
    history = [{"role": row.role, "content": row.content} for row in rows]
    logger.debug(f"Loaded {len(history)} messages for session={session_id}")
    return history


async def clear_history(session_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM chat_messages WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        await session.commit()
        logger.info(f"Cleared history for session={session_id}")


async def get_token_usage(session_id: str) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    COUNT(*)         AS message_count,
                    SUM(token_count) AS total_tokens,
                    MIN(created_at)  AS first_message,
                    MAX(created_at)  AS last_message
                FROM chat_messages
                WHERE session_id = :session_id
            """),
            {"session_id": session_id}
        )
        row = result.fetchone()
    return {
        "session_id":    session_id,
        "message_count": row.message_count or 0,
        "total_tokens":  row.total_tokens or 0,
        "first_message": str(row.first_message) if row.first_message else None,
        "last_message":  str(row.last_message) if row.last_message else None,
    }