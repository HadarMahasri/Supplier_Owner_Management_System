from sqlalchemy import Column, Integer, ForeignKey
from database.session import Base

class SupplierCity(Base):
    __tablename__ = "supplier_cities"

    supplier_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    city_id     = Column(Integer, ForeignKey("cities.id"), primary_key=True)
