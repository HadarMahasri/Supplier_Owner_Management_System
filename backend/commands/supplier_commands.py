from sqlalchemy.orm import Session

class SupplierCommands:
    def __init__(self):
        pass
    
    async def create_supplier(self, db: Session, supplier_data: dict):
        # TODO: implement
        return {"id": "dummy", "message": "Not implemented yet"}
    
    async def update_supplier(self, db: Session, supplier_id: str, supplier_data: dict):
        # TODO: implement
        pass
    
    async def delete_supplier(self, db: Session, supplier_id: str):
        # TODO: implement
        pass