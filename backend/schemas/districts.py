from typing import Optional, NewType
from pydantic import BaseModel, Field, constr

DistrictName = NewType("DistrictName", constr(strip_whitespace=True, min_length=1, max_length=255))

class DistrictCreate(BaseModel):
    name_he: DistrictName
    name_en: Optional[str] = None
    is_active: Optional[bool] = True

class DistrictUpdate(BaseModel):
    name_he: Optional[DistrictName] = None
    name_en: Optional[str] = None
    is_active: Optional[bool] = None

class DistrictOut(BaseModel):
    id: int
    name_he: str
    name_en: Optional[str] = None
    is_active: bool = True
