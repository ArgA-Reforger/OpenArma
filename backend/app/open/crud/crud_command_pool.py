from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.open.model.command_pool import CommandPool
from backend.utils.timezone import timezone


async def get_pending_orders(db: AsyncSession, conversation_id: str) -> CommandPool | None:
    """Get the latest pending orders for a conversation."""
    stmt = (
        select(CommandPool)
        .where(
            CommandPool.conversation_id == conversation_id,
            CommandPool.status == 'pending',
        )
        .order_by(CommandPool.created_time.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_all_pending_orders_by_project(db: AsyncSession, project_id: int) -> list[CommandPool]:
    """Get all pending orders across all conversations for a project."""
    stmt = (
        select(CommandPool)
        .where(
            CommandPool.project_id == project_id,
            CommandPool.status == 'pending',
        )
        .order_by(CommandPool.created_time.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_delivered(db: AsyncSession, pool_entry: CommandPool) -> None:
    """Mark a command pool entry as delivered."""
    pool_entry.status = 'delivered'
    pool_entry.delivered_at = timezone.now()


async def create_command(
    db: AsyncSession,
    conversation_id: str,
    request_id: int,
    orders_json: dict,
    project_id: int | None = None,
) -> CommandPool:
    """Store new orders in the command pool."""
    entry = CommandPool(
        project_id=project_id,
        conversation_id=conversation_id,
        request_id=request_id,
        orders_json=orders_json,
    )
    db.add(entry)
    return entry
