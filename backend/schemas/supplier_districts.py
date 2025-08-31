from pydantic import BaseModel, Field

class SupplierDistrictLink(BaseModel):
    supplier_id: int = Field(gt=0)
    district_id: int = Field(gt=0)

class SupplierDistrictLinkOut(SupplierDistrictLink):
    pass
