from pydantic import BaseModel, Field

class SupplierCityLink(BaseModel):
    supplier_id: int = Field(gt=0)
    city_id: int = Field(gt=0)

class SupplierCityLinkOut(SupplierCityLink):
    pass
