# backend/models/order_model.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.types import Unicode
from sqlalchemy.orm import relationship
from database.session import Base

class Order(Base):
    __tablename__ = "orders"
    id           = Column(Integer, primary_key=True, index=True)
    owner_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    supplier_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    status       = Column(Unicode(20), nullable=False)  # "בתהליך" / "הושלמה" / "בוצעה"
    created_date = Column(DateTime)

    owner    = relationship("User", foreign_keys=[owner_id])
    supplier = relationship("User", foreign_keys=[supplier_id])
    items    = relationship("OrderItem", cascade="all, delete-orphan", back_populates="order")
