# תקני: אל תיצור/י Base חדש ואל תגדיר/י User מחדש
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from database.session import Base  # להשתמש ב-Base הקיים מהפרויקט

class OwnerSupplierLink(Base):
    __tablename__ = "owner_supplier_links"

    owner_id    = Column(Integer, ForeignKey("users.id"), primary_key=True)
    supplier_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    status      = Column(String(20), nullable=False, default="PENDING")
    created_at  = Column(DateTime, server_default=func.getdate())
    updated_at  = Column(DateTime)

    __table_args__ = (
        CheckConstraint("status in ('PENDING','APPROVED','REJECTED')"),
    )

    # להשתמש בשם המודל הקיים "User" מבלי להגדיר אותו שוב
    owner    = relationship("User", foreign_keys=[owner_id])
    supplier = relationship("User", foreign_keys=[supplier_id])
