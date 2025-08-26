# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from models.supplier_model import Base
from gateway.gateway_router import gateway_router
from config.database import get_database_url

load_dotenv()

# Database setup
DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Supplier Management System...")
    yield
    # Shutdown
    print("🛑 Shutting down...")

# FastAPI app
app = FastAPI(
    title="Supplier Management System API",
    description="מערכת ניהול ספקים עם יכולות AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בסביבת פיתוח - בייצור להגביל לדומיינים ספציפיים
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include routers
app.include_router(gateway_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Supplier Management System API", 
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

