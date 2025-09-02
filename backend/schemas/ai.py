# backend/schemas/ai.py
from pydantic import BaseModel

class AIAskRequest(BaseModel):
    question: str
    user_id: int

class AIAnswer(BaseModel):
    answer: str

class AIContext(BaseModel):
    user_id: int
    username: str
    role: str            # "Supplier" / "StoreOwner"
    snapshot: str        # טקסט הקשר מקוצר לתשובה
