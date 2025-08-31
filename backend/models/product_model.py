# backend/models/product_model.py
from sqlalchemy import Column, Integer, Float, Boolean
from sqlalchemy.types import Unicode

from database.session import Base

class Product(Base):
    __tablename__ = "products"

    id           = Column(Integer, primary_key=True, index=True)
    supplier_id  = Column(Integer, nullable=False, index=True)
    product_name = Column(Unicode(255), nullable=False)   # ← Unicode = NVARCHAR
    unit_price   = Column(Float, nullable=False)
    min_quantity = Column(Integer, nullable=False, default=0)
    stock        = Column(Integer, nullable=False, default=0)
    image_url    = Column(Unicode(255), nullable=True)    # ← גם כאן מומלץ Unicode
    is_active    = Column(Boolean, nullable=False, default=True)
