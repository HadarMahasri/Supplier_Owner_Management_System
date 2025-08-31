from typing import Optional, NewType
from pydantic import BaseModel, Field, constr

CityName = NewType("CityName", constr(strip_whitespace=True, min_length=1, max_length=255))

class CityCreate(BaseModel):
    district_id: int = Field(gt=0)
    name_he: CityName
    name_en: Optional[str] = None
    external_id: Optional[str] = None
    is_active: Optional[bool] = True
    source: Optional[str] = None

class CityUpdate(BaseModel):
    name_he: Optional[CityName] = None
    name_en: Optional[str] = None
    district_id: Optional[int] = None
    is_active: Optional[bool] = None
    source: Optional[str] = None

class CityOut(BaseModel):
    id: int
    external_id: Optional[str] = None
    district_id: int
    name_he: str
    name_en: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[str] = None
    source: Optional[str] = None
