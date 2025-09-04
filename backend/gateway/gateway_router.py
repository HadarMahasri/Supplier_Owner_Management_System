# backend/gateway/gateway_router.py
from fastapi import APIRouter

# ראוטרים עסקיים – לא משנים לוגיקה, רק עוטפים תחת /gateway/*
from routers.orders_router import router as orders_router
from routers.products_router import router as products_router
from routers.users_router import router as users_router
from routers.owner_links_router import router as owner_links_router

# תת-שערים
from routers.images_gateway_router import router as images_gateway_router    # שרת התמונות
from routers.gateway_router_chat import router as chat_gateway_router        # צ'אט AI חדש

gateway_router = APIRouter(prefix="/gateway", tags=["gateway"])

# DB/business routers
gateway_router.include_router(users_router)           # /gateway/users/...
gateway_router.include_router(owner_links_router)     # /gateway/owner-links/...
gateway_router.include_router(products_router)        # /gateway/products/...
gateway_router.include_router(orders_router)          # /gateway/orders/...

# External services routers
gateway_router.include_router(images_gateway_router)  # /gateway/images/...

# AI routers
gateway_router.include_router(chat_gateway_router, prefix="/chat", tags=["chat-ai"])     # /gateway/chat/... (חדש)