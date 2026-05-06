from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.billing.model.usage_record import UsageRecord
from backend.app.llm.model.llm_provider import LLMProvider
from backend.app.project.model.project import Project


class CRUDUsage:

    async def get_records(
        self, db: AsyncSession, user_id: int, start: datetime, end: datetime,
        *, page: int = 1, size: int = 20, call_type: str | None = None,
        status: str | None = None, provider_type: str | None = None,
    ) -> dict:
        """分页获取详细调用记录。"""
        conditions = [
            UsageRecord.user_id == user_id,
            UsageRecord.created_time >= start,
            UsageRecord.created_time <= end,
        ]
        if call_type:
            conditions.append(UsageRecord.call_type == call_type)
        if status:
            conditions.append(UsageRecord.status == status)
        if provider_type:
            conditions.append(UsageRecord.provider_type == provider_type)

        count_stmt = sa.select(sa.func.count()).select_from(UsageRecord).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            sa.select(
                UsageRecord.id,
                UsageRecord.provider_type,
                UsageRecord.model_name,
                UsageRecord.prompt_tokens,
                UsageRecord.completion_tokens,
                UsageRecord.total_tokens,
                UsageRecord.cached_tokens,
                UsageRecord.reasoning_tokens,
                UsageRecord.estimated_cost,
                UsageRecord.call_type,
                UsageRecord.status,
                UsageRecord.error_message,
                UsageRecord.duration_ms,
                UsageRecord.project_id,
                UsageRecord.agent_id,
                UsageRecord.created_time,
                UsageRecord.metadata_.label('metadata'),
                Project.name.label('project_name'),
                LLMProvider.name.label('provider_name'),
            )
            .outerjoin(Project, UsageRecord.project_id == Project.id)
            .outerjoin(LLMProvider, UsageRecord.llm_provider_id == LLMProvider.id)
            .where(*conditions)
            .order_by(sa.desc(UsageRecord.created_time))
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await db.execute(stmt)).all()
        return {
            'total': total,
            'page': page,
            'size': size,
            'items': [
                {
                    'id': str(r.id),
                    'provider_type': r.provider_type,
                    'provider_name': r.provider_name or r.provider_type,
                    'model_name': r.model_name,
                    'prompt_tokens': r.prompt_tokens,
                    'completion_tokens': r.completion_tokens,
                    'total_tokens': r.total_tokens,
                    'cached_tokens': r.cached_tokens or 0,
                    'reasoning_tokens': r.reasoning_tokens or 0,
                    'estimated_cost': float(r.estimated_cost),
                    'currency': (r.metadata or {}).get('currency', 'USD'),
                    'call_type': r.call_type,
                    'status': r.status,
                    'error_message': r.error_message,
                    'duration_ms': r.duration_ms,
                    'project_name': r.project_name or '-',
                    'agent_name': (r.metadata or {}).get('agent_name', '-'),
                    'created_time': str(r.created_time),
                }
                for r in rows
            ],
        }

    async def get_summary(
        self, db: AsyncSession, user_id: int, start: datetime, end: datetime,
    ) -> dict:
        stmt = (
            sa.select(
                sa.func.count().label('total_calls'),
                sa.func.coalesce(sa.func.sum(UsageRecord.prompt_tokens), 0).label('total_prompt_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.completion_tokens), 0).label('total_completion_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.total_tokens), 0).label('total_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.cached_tokens), 0).label('total_cached_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.reasoning_tokens), 0).label('total_reasoning_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.estimated_cost), 0.0).label('estimated_cost'),
            )
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.created_time >= start,
                UsageRecord.created_time <= end,
            )
        )
        row = (await db.execute(stmt)).one()
        return {
            'total_calls': row.total_calls,
            'total_prompt_tokens': row.total_prompt_tokens,
            'total_completion_tokens': row.total_completion_tokens,
            'total_tokens': row.total_tokens,
            'total_cached_tokens': row.total_cached_tokens,
            'total_reasoning_tokens': row.total_reasoning_tokens,
            'estimated_cost': float(row.estimated_cost),
        }

    async def get_by_provider(
        self, db: AsyncSession, user_id: int, start: datetime, end: datetime,
    ) -> list[dict]:
        stmt = (
            sa.select(
                UsageRecord.provider_type,
                UsageRecord.model_name,
                UsageRecord.llm_provider_id,
                LLMProvider.name.label('provider_name'),
                sa.func.count().label('calls'),
                sa.func.coalesce(sa.func.sum(UsageRecord.prompt_tokens), 0).label('prompt_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.completion_tokens), 0).label('completion_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.total_tokens), 0).label('total_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.cached_tokens), 0).label('cached_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.reasoning_tokens), 0).label('reasoning_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.estimated_cost), 0.0).label('cost'),
            )
            .outerjoin(LLMProvider, UsageRecord.llm_provider_id == LLMProvider.id)
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.created_time >= start,
                UsageRecord.created_time <= end,
            )
            .group_by(UsageRecord.provider_type, UsageRecord.model_name, UsageRecord.llm_provider_id, LLMProvider.name)
            .order_by(sa.desc('total_tokens'))
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                'provider_type': r.provider_type,
                'provider_name': r.provider_name or r.provider_type,
                'model_name': r.model_name,
                'calls': r.calls,
                'prompt_tokens': r.prompt_tokens,
                'completion_tokens': r.completion_tokens,
                'total_tokens': r.total_tokens,
                'cached_tokens': r.cached_tokens,
                'reasoning_tokens': r.reasoning_tokens,
                'cost': float(r.cost),
            }
            for r in rows
        ]

    async def get_by_project(
        self, db: AsyncSession, user_id: int, start: datetime, end: datetime,
    ) -> list[dict]:
        stmt = (
            sa.select(
                UsageRecord.project_id,
                Project.name.label('project_name'),
                sa.func.count().label('calls'),
                sa.func.coalesce(sa.func.sum(UsageRecord.prompt_tokens), 0).label('prompt_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.completion_tokens), 0).label('completion_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.total_tokens), 0).label('total_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.estimated_cost), 0.0).label('cost'),
            )
            .outerjoin(Project, UsageRecord.project_id == Project.id)
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.created_time >= start,
                UsageRecord.created_time <= end,
            )
            .group_by(UsageRecord.project_id, Project.name)
            .order_by(sa.desc('total_tokens'))
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                'project_id': r.project_id,
                'project_name': r.project_name or '(未关联项目)',
                'calls': r.calls,
                'prompt_tokens': r.prompt_tokens,
                'completion_tokens': r.completion_tokens,
                'total_tokens': r.total_tokens,
                'cost': float(r.cost),
            }
            for r in rows
        ]

    async def get_daily(
        self, db: AsyncSession, user_id: int, start: datetime, end: datetime,
    ) -> list[dict]:
        date_col = sa.func.date(UsageRecord.created_time).label('date')
        stmt = (
            sa.select(
                date_col,
                sa.func.count().label('calls'),
                sa.func.coalesce(sa.func.sum(UsageRecord.total_tokens), 0).label('total_tokens'),
                sa.func.coalesce(sa.func.sum(UsageRecord.estimated_cost), 0.0).label('cost'),
            )
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.created_time >= start,
                UsageRecord.created_time <= end,
            )
            .group_by(date_col)
            .order_by(date_col)
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                'date': str(r.date),
                'calls': r.calls,
                'total_tokens': r.total_tokens,
                'cost': float(r.cost),
            }
            for r in rows
        ]


usage_dao: CRUDUsage = CRUDUsage()
