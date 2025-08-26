from sqlalchemy import Column, String, DateTime, Text, Numeric, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    name_hebrew = Column(String(100))
    description = Column(Text)
    icon = Column(String(50))
    parent_id = Column(String, ForeignKey('categories.id'))
    active = Column(Boolean, default=True)
    sort_order = Column(Numeric(5,0), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100))
    description = Column(Text)
    
    contact_info = Column(JSON)
    address = Column(JSON)
    location = Column(JSON)
    
    rating = Column(Numeric(3,2), default=0.0)
    review_count = Column(Numeric(10,0), default=0)
    price_range = Column(String(20), default='medium')
    delivery_areas = Column(JSON)
    
    status = Column(String(20), default='active')
    verified = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)