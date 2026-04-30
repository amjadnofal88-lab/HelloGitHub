from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case


class CaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        tenant_id: str,
        owner_id: str,
        title: str,
        description: str | None = None,
    ) -> Case:
        case = Case(
            tenant_id=tenant_id,
            owner_id=owner_id,
            title=title,
            description=description,
        )
        self.db.add(case)
        await self.db.flush()
        return case

    async def get(self, case_id: str, tenant_id: str) -> Case | None:
        result = await self.db.execute(
            select(Case).where(Case.id == case_id, Case.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, skip: int = 0, limit: int = 50) -> list[Case]:
        result = await self.db.execute(
            select(Case)
            .where(Case.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, case_id: str, tenant_id: str, status: str) -> Case:
        case = await self.get(case_id, tenant_id)
        if case is None:
            raise ValueError(f"Case '{case_id}' not found")
        case.status = status
        await self.db.flush()
        return case

    async def delete(self, case_id: str, tenant_id: str) -> None:
        case = await self.get(case_id, tenant_id)
        if case is None:
            raise ValueError(f"Case '{case_id}' not found")
        await self.db.delete(case)
