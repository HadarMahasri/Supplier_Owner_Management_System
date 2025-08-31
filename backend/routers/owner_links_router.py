from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from database.session import get_db
from models.supplier_city_model import SupplierCity, SupplierDistrict
from models.owner_supplier_link import OwnerSupplierLink
from schemas.owner_supplier_link import LinkOut, ActionResult, OwnerMini
from models.user_model import User  # Update the import path to the correct location of your User model
from sqlalchemy.orm import joinedload


router = APIRouter(prefix="/owner-links", tags=["owner-links"])

def _query_links(db: Session, supplier_id: int, status: str | None):
    q = (db.query(OwnerSupplierLink)
           .options(joinedload(OwnerSupplierLink.owner))  # טען owner בלי join מסנן
           .filter(OwnerSupplierLink.supplier_id == supplier_id))
    if status:
        q = q.filter(OwnerSupplierLink.status == status)
    return q.all()

@router.get("/active", response_model=List[LinkOut])
def get_active(supplier_id: int = Query(...), db: Session = Depends(get_db)):
    links = _query_links(db, supplier_id, "APPROVED")
    out = []
    for l in links:
        owner = l.owner or db.get(User, l.owner_id)  # גיבוי אם לא נטען
        if not owner:
            # אם אין רשומת owner – עדיף לא להחזיר אותה (יתכן orphan ב-DB)
            continue
        out.append(LinkOut(
            owner=OwnerMini.model_validate(owner),
            supplier_id=l.supplier_id,
            status=l.status,
            created_at=l.created_at,
            updated_at=l.updated_at,
        ))
    return out

@router.get("/pending", response_model=List[LinkOut])
def get_pending(supplier_id: int, db: Session = Depends(get_db)):
    links = _query_links(db, supplier_id, "PENDING")
    return [
        LinkOut(
            owner=OwnerMini.model_validate(l.owner),
            supplier_id=l.supplier_id,
            status=l.status,
            created_at=l.created_at,
            updated_at=l.updated_at,
        ) for l in links
    ]

def _set_status(db: Session, supplier_id: int, owner_id: int, new_status: str) -> OwnerSupplierLink:
    link = db.get(OwnerSupplierLink,((owner_id, supplier_id)))
    if not link:
        raise HTTPException(404, "link not found")
    link.status = new_status
    link.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link

@router.post("/{owner_id}/approve", response_model=ActionResult)
def approve(owner_id: int, supplier_id: int, db: Session = Depends(get_db)):
    l = _set_status(db, supplier_id, owner_id, "APPROVED")
    return ActionResult(ok=True, status=l.status)

@router.post("/{owner_id}/reject", response_model=ActionResult)
def reject(owner_id: int, supplier_id: int, db: Session = Depends(get_db)):
    l = _set_status(db, supplier_id, owner_id, "REJECTED")
    return ActionResult(ok=True, status=l.status)

# ---------- חיבורים פעילים/ממתינים לפי בעל חנות ----------
def _query_links_by_owner(db: Session, owner_id: int, status: str | None):
    q = (db.query(OwnerSupplierLink)
           .options(joinedload(OwnerSupplierLink.supplier))  # נרצה את פרטי הספק
           .filter(OwnerSupplierLink.owner_id == owner_id))
    if status:
        q = q.filter(OwnerSupplierLink.status == status)
    return q.all()

@router.get("/active-by-owner", response_model=List[LinkOut])
def active_by_owner(owner_id: int = Query(...), db: Session = Depends(get_db)):
    links = _query_links_by_owner(db, owner_id, "APPROVED")
    out = []
    for l in links:
        sup = l.supplier or db.get(User, l.supplier_id)
        if not sup:  # הגנה מרשומות יתומות
            continue
        out.append(LinkOut(
            owner=OwnerMini.model_validate(sup),  # משתמשים באותו OwnerMini גם עבור ספק
            supplier_id=l.supplier_id,
            status=l.status,
            created_at=l.created_at,
            updated_at=l.updated_at,
        ))
    return out

@router.get("/pending-by-owner", response_model=List[LinkOut])
def pending_by_owner(owner_id: int = Query(...), db: Session = Depends(get_db)):
    links = _query_links_by_owner(db, owner_id, "PENDING")
    out = []
    for l in links:
        sup = l.supplier or db.get(User, l.supplier_id)
        if not sup:
            continue
        out.append(LinkOut(
            owner=OwnerMini.model_validate(sup),
            supplier_id=l.supplier_id,
            status=l.status,
            created_at=l.created_at,
            updated_at=l.updated_at,
        ))
    return out

# ---------- שליחת בקשה (בעל חנות -> ספק) ----------
@router.post("/request", response_model=ActionResult)
def request_link(owner_id: int = Query(...), supplier_id: int = Query(...), db: Session = Depends(get_db)):
    link = db.get(OwnerSupplierLink, (owner_id, supplier_id))
    if link:
        # אם כבר יש – לא ניצור כפילות; נשאיר כפי שהוא
        return ActionResult(ok=True, status=link.status)
    link = OwnerSupplierLink(owner_id=owner_id, supplier_id=supplier_id, status="PENDING")
    db.add(link)
    db.commit()
    return ActionResult(ok=True, status=link.status)

# ---------- חיפוש ספקים אפשריים לפי אזור ----------
@router.get("/find-suppliers", response_model=List[OwnerMini])
def find_suppliers(owner_id: int = Query(...), db: Session = Depends(get_db)):
    """
    מחזיר רשימת ספקים שיכולים לתת שירות לבעל החנות:
    1) אם יש לעיר של בעל החנות התאמה ב-supplier_cities.
    2) או התאמה למחוז ב-supplier_districts.
    מסנן רק משתמשים מסוג 'Supplier'.
    """
    owner = db.get(User, owner_id)
    if not owner:
        raise HTTPException(404, "owner not found")

    q = db.query(User).filter(User.userType == "Supplier")

    # התאמה לפי עיר
    if owner.city_id:
        q = q.join(SupplierCity, SupplierCity.supplier_id == User.id, isouter=True) \
             .filter((SupplierCity.city_id == owner.city_id) | (SupplierCity.city_id == None))
    # התאמה לפי מחוז (אם יש לעיר מחוז)
    # ניתן להרחיב עם join לטבלת cities כדי להביא district_id של העיר של בעל החנות

    # הוצאת ספקים שכבר יש איתם לינק (כל מצב) – כדי לא להציג כפילות
    existing = db.query(OwnerSupplierLink.supplier_id)\
                 .filter(OwnerSupplierLink.owner_id == owner_id).all()
    existing_ids = {sid for (sid,) in existing}
    suppliers = [s for s in q.all() if s.id not in existing_ids]

    return [OwnerMini.model_validate(s) for s in suppliers]