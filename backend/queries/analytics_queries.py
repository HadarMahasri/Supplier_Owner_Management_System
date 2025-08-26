from sqlalchemy.orm import Session

class AnalyticsQueries:
    async def get_suppliers_by_category_stats(self, db: Session):
        return []
    
    async def get_top_rated_suppliers(self, db: Session, limit: int):
        return []
    
    async def get_suppliers_by_location(self, db: Session):
        return []