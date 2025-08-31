# backend/models/user_model.py
from sqlalchemy import Column, Integer, Boolean
from sqlalchemy.types import Unicode, UnicodeText, String, Time
from database.session import Base

class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(Unicode(255), unique=True, nullable=False)
    email        = Column(Unicode(255), unique=True)
    password     = Column(Unicode(255), nullable=False)
    company_name = Column(Unicode(255))
    contact_name = Column(Unicode(255))
    phone        = Column(Unicode(20))
    city_id      = Column(Integer)
    street       = Column(Unicode(255))
    house_number = Column(Unicode(32))
    opening_time = Column(Time)
    closing_time = Column(Time)
    userType     = Column(Unicode(20), nullable=False)  # 'StoreOwner' / 'Supplier'
