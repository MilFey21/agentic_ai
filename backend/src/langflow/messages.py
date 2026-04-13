"""
Service for fetching messages from LangFlow's PostgreSQL database.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.langflow.config import langflow_settings


logger = logging.getLogger(__name__)


@dataclass
class LangFlowMessage:
    """A message from LangFlow's message table."""

    id: str
    session_id: str
    sender: str  # 'User' or 'Machine'
    sender_name: str
    text: str
    timestamp: datetime
    flow_id: str | None = None


async def get_session_messages(session_id: str, limit: int | None = None) -> list[LangFlowMessage]:
    """
    Fetch messages for a given session from LangFlow's database.

    Args:
        session_id: The LangFlow session ID
        limit: Maximum number of messages to fetch (from the end of conversation).
               If None, fetches all messages.

    Returns:
        List of messages ordered by timestamp (chronological order)
    """
    engine = create_async_engine(
        langflow_settings.langflow_database_url,
        echo=False,
    )

    messages: list[LangFlowMessage] = []

    try:
        async with engine.connect() as conn:
            # Query messages from langflow's message table
            # If limit is set, get last N messages (ORDER BY DESC + LIMIT, then reverse)
            if limit:
                result = await conn.execute(
                    text("""
                        SELECT id, session_id, sender, sender_name, text, timestamp, flow_id
                        FROM message
                        WHERE session_id = :session_id
                        ORDER BY timestamp DESC
                        LIMIT :limit
                    """),
                    {'session_id': session_id, 'limit': limit},
                )
            else:
                result = await conn.execute(
                    text("""
                        SELECT id, session_id, sender, sender_name, text, timestamp, flow_id
                        FROM message
                        WHERE session_id = :session_id
                        ORDER BY timestamp ASC
                    """),
                    {'session_id': session_id},
                )

            rows = result.fetchall()

            for row in rows:
                messages.append(
                    LangFlowMessage(
                        id=str(row.id),
                        session_id=row.session_id,
                        sender=row.sender,
                        sender_name=row.sender_name,
                        text=row.text or '',
                        timestamp=row.timestamp,
                        flow_id=str(row.flow_id) if row.flow_id else None,
                    )
                )

            # If limit was used, messages are in DESC order - reverse to chronological
            if limit:
                messages.reverse()

            logger.info('Fetched %d messages for session %s', len(messages), session_id)

    except Exception as e:
        logger.exception('Failed to fetch messages from LangFlow database: %s', e)
        raise
    finally:
        await engine.dispose()

    return messages


def format_conversation_for_evaluation(messages: list[LangFlowMessage]) -> str:
    """
    Format messages into a conversation string for evaluation.

    Args:
        messages: List of LangFlow messages

    Returns:
        Formatted conversation string
    """
    if not messages:
        return ''

    conversation_parts = []

    # Note: LangFlow only stores AI responses in the message table
    # User messages are not stored, but we can infer the conversation flow
    for msg in messages:
        role = 'Бот' if msg.sender == 'Machine' else 'Студент'
        conversation_parts.append(f'[{role}]: {msg.text}')

    return '\n\n'.join(conversation_parts)
