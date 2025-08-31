from database.session import Base
from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint
from database.session import Base

class SupplierCity(Base):
    __tablename__ = "supplier_cities"
    supplier_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    city_id     = Column(Integer, ForeignKey("cities.id"), primary_key=True)
    __table_args__ = (PrimaryKeyConstraint("supplier_id", "city_id"),)

class SupplierDistrict(Base):
    __tablename__ = "supplier_districts"
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    __table_args__ = (PrimaryKeyConstraint("supplier_id", "district_id"),)
