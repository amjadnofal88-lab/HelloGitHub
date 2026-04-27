from fastapi import APIRouter

from api.routes.customers import router as customers_router
from api.routes.policies import router as policies_router
from api.routes.claims import router as claims_router

router = APIRouter()

router.include_router(customers_router, prefix="/customers", tags=["customers"])
router.include_router(policies_router, prefix="/policies", tags=["policies"])
router.include_router(claims_router, prefix="/claims", tags=["claims"])
