# backend/models/order_item_model.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base

class OrderItem(Base):
    __tablename__ = "order_items"
    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False)
    quantity   = Column(Integer, nullable=False)

    order   = relationship("Order", back_populates="items")
    product = relationship("Product")
