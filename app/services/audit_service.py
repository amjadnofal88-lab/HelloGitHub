from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        user_id: str | None = None,
        resource_id: str | None = None,
        detail: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list(
        self,
        tenant_id: str,
        resource_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
