# backend/models/city_model.py
from sqlalchemy import Column, Integer
from database.session import Base

class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
