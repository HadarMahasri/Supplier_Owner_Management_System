# backend/services/context_to_prompt.py (updated)
# ממיר Context עשיר ל-System Prompt חכם + Few-shots (בעברית)
# נשמרו שמות ה-API הציבוריים ואליהם הוספנו תמיכה בחתימת build_system_prompt עם 1 או 4 פרמטרים.
#  - supplier_context_to_text(ctx)
#  - owner_context_to_text(ctx)
#  - build_system_prompt(role: str, username: Optional[str]=None, permissions: Optional[List[str]]=None, snapshot_text: Optional[str]=None)
#  - few_shots(role: str)
#  - join_prompt(system_prompt: str, snapshot_text: str, examples: str, user_question: str)

from __future__ import annotations
from typing import Dict, Any, List, Callable, Optional
import textwrap

AGENT_NAME = "Supi"
AGENT_DESCRIPTION = "עוזר AI חכם למערכת ניהול ספקים וחנויות"

# =============================
# Helpers (משותפים)
# =============================

def _nl() -> str:
    return "\n"


def _format_money(v: Any) -> str:
    try:
        return f"₪{float(v):.2f}"
    except Exception:
        return str(v)


def _format_percent(v: Any) -> str:
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return str(v)


def _fmt_row(cols: List[str], sep: str = " | ") -> str:
    return sep.join(str(c) for c in cols)


def _limit(items: List[Any] | None, n: int) -> List[Any]:
    if not items:
        return []
    return list(items)[: max(0, n)]


def _section(title: str, body: str) -> str:
    body = body.strip()
    return f"{title}\n{('-' * max(3, len(title)))}\n{body}\n"


def _optional_list_section(title: str, items: List[Any], limit: int, row_fn: Callable[[Any, int], str]) -> str:
    items = _limit(items, limit)
    if not items:
        return _section(title, "אין נתונים להצגה")
    lines = [row_fn(it, i) for i, it in enumerate(items, start=1)]
    return _section(title + f" ({len(items)})", "\n".join(lines))


# =============================
# Context → Snapshot Text
# =============================

def _supplier_snapshot(ctx: Dict[str, Any]) -> str:
    """תרגום קונטקסט של ספק לטקסט תמציתי ואחיד."""
    k = ctx.get("kpis", {})
    s = ctx.get("samples", {})
    analytics = ctx.get("analytics", {})

    # KPIs
    kpi_lines = []
    if k:
        if "revenue_30d" in k:
            kpi_lines.append(_fmt_row(["הכנסות 30 יום", _format_money(k.get("revenue_30d", 0))]))
        if "open_orders" in k:
            kpi_lines.append(_fmt_row(["הזמנות פתוחות", str(k.get("open_orders", 0))]))
        if "avg_fulfillment_days" in k:
            kpi_lines.append(_fmt_row(["ימי אספקה ממוצעים", str(k.get("avg_fulfillment_days", "-"))]))
        if "top_product" in k:
            tp = k.get("top_product")
            if isinstance(tp, dict):
                kpi_lines.append(_fmt_row(["מוצר מוביל", f"{tp.get('name', 'N/A')} ({_format_money(tp.get('revenue', 0))})"]))
            else:
                kpi_lines.append(_fmt_row(["מוצר מוביל", str(tp)]))
    kpi_text = _section("מדדים עיקריים", "\n".join(kpi_lines) if kpi_lines else "אין מדדים זמינים")

    # הזמנות פתוחות
    open_orders = s.get("open_orders", [])
    def _order_row(o: Dict[str, Any], i: int) -> str:
        oid = o.get('id', '-')
        st = o.get('status', '-')
        qty = o.get('total_count') or o.get('count') or o.get('items_count') or '-'
        other = o.get('other_party') or o.get('owner_name') or o.get('customer') or '-'
        total = _format_money(o.get('total_amount', 0))
        return f"  #{oid} | {st} | {qty} פריטים | {other} | {total}"
    open_orders_text = _optional_list_section("הזמנות פתוחות", open_orders, 5, _order_row)

    # מלאי נמוך
    low_stock = s.get("low_stock", [])
    def _low_row(p: Dict[str, Any], i: int) -> str:
        return f"  {p.get('name','ללא שם')} - מלאי: {p.get('stock','?')}, מינימום: {p.get('min_stock','?')}"
    low_stock_text = _optional_list_section("מלאי נמוך", low_stock, 6, _low_row)

    # אנליטיקה
    anl_lines = []
    if analytics:
        if analytics.get("late_orders_rate") is not None:
            anl_lines.append(_fmt_row(["איחורים באספקה", _format_percent(analytics.get("late_orders_rate"))]))
        if analytics.get("returns_rate") is not None:
            anl_lines.append(_fmt_row(["שיעור החזרות", _format_percent(analytics.get("returns_rate"))]))
        if analytics.get("monthly_trend") is not None:
            anl_lines.append(_fmt_row(["מגמת הכנסות חודשית", str(analytics.get("monthly_trend"))]))
    analytics_text = _section("אנליטיקה", "\n".join(anl_lines) if anl_lines else "אין תובנות זמינות")

    return "\n".join([kpi_text, open_orders_text, low_stock_text, analytics_text]).strip()


def _owner_snapshot(ctx: Dict[str, Any]) -> str:
    """תרגום קונטקסט של בעל חנות לטקסט תמציתי ואחיד."""
    k = ctx.get("kpis", {})
    s = ctx.get("samples", {})
    analytics = ctx.get("analytics", {})

    # KPIs
    kpi_lines = []
    if k:
        if "spend_30d" in k:
            kpi_lines.append(_fmt_row(["הוצאות 30 יום", _format_money(k.get("spend_30d", 0))]))
        if "open_orders" in k:
            kpi_lines.append(_fmt_row(["הזמנות פתוחות", str(k.get("open_orders", 0))]))
        if "avg_delivery_days" in k:
            kpi_lines.append(_fmt_row(["ימי אספקה ממוצעים", str(k.get("avg_delivery_days", "-"))]))
        if "favorite_supplier" in k:
            fav = k.get("favorite_supplier")
            kpi_lines.append(_fmt_row(["ספק מועדף", str(fav)]))
    kpi_text = _section("מדדים עיקריים", "\n".join(kpi_lines) if kpi_lines else "אין מדדים זמינים")

    # הזמנות פתוחות
    open_orders = s.get("open_orders", [])
    def _order_row(o: Dict[str, Any], i: int) -> str:
        oid = o.get('id', '-')
        st = o.get('status', '-')
        qty = o.get('total_count') or o.get('count') or o.get('items_count') or '-'
        supp = o.get('supplier_name') or o.get('supplier') or '-'
        total = _format_money(o.get('total_amount', 0))
        return f"  #{oid} | {st} | {qty} פריטים | {supp} | {total}"
    open_orders_text = _optional_list_section("הזמנות פתוחות", open_orders, 5, _order_row)

    # פריטים חסרים / להשלים מלאי
    missing = s.get("missing_items", []) or s.get("to_restock", [])
    def _miss_row(p: Dict[str, Any], i: int) -> str:
        return f"  {p.get('name','ללא שם')} - במלאי: {p.get('stock','?')} (מינימום: {p.get('min_stock','?')})"
    missing_text = _optional_list_section("מוצרים לחידוש מלאי", missing, 6, _miss_row)

    # אנליטיקה
    anl_lines = []
    if analytics:
        if analytics.get("on_time_rate") is not None:
            anl_lines.append(_fmt_row(["אספקה בזמן", _format_percent(analytics.get("on_time_rate"))]))
        if analytics.get("avg_order_value") is not None:
            anl_lines.append(_fmt_row(["שווי הזמנה ממוצע", _format_money(analytics.get("avg_order_value"))]))
        if analytics.get("monthly_trend") is not None:
            anl_lines.append(_fmt_row(["מגמת רכישות חודשית", str(analytics.get("monthly_trend"))]))
    analytics_text = _section("אנליטיקה", "\n".join(anl_lines) if anl_lines else "אין תובנות זמינות")

    return "\n".join([kpi_text, open_orders_text, missing_text, analytics_text]).strip()


# =============================
# Public APIs (נשמרו כמקודם)
# =============================

def supplier_context_to_text(ctx: Dict[str, Any]) -> str:  # type: ignore[override]
    return _supplier_snapshot(ctx)


def owner_context_to_text(ctx: Dict[str, Any]) -> str:  # type: ignore[override]
    return _owner_snapshot(ctx)


def build_system_prompt(
    role: str,
    username: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    snapshot_text: Optional[str] = None,
) -> str:
    """System prompt אחיד לשתי הדמויות (ספק/בעל חנות), עם תמיכה גם בחתימה הישנה (פרמטר יחיד) וגם בחדשה (4 פרמטרים).

    הערה: snapshot_text *לא* מוכנס ל-system prompt כדי למנוע כפילות; הוא נצרף ב-join_prompt תחת "מידע עדכני".
    """
    role = (role or "").strip() or "Assistant"
    persona = {
        "Supplier": "את/ה מסייע/ת לספק לייעל אספקות, מעקב הזמנות ומלאי.",
        "StoreOwner": "את/ה מסייע/ת לבעל חנות לנהל הזמנות, ספקים ומלאי באופן חכם.",
    }.get(role, "את/ה עוזר/ת כללי/ת לניהול ספקים וחנויות.")

    user_line = f"משתמש: {username}" if username else None
    perms_line = None
    if permissions:
        try:
            # מצמצם לרשימה קצרה כדי לא לנפח טוקנים
            short = ", ".join(list(dict.fromkeys(permissions))[:10])
            perms_line = f"הרשאות: {short}"
        except Exception:
            pass

    extra_lines = [l for l in [user_line, perms_line] if l]
    extra = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

    return textwrap.dedent(f"""
    אתה {AGENT_NAME} – {AGENT_DESCRIPTION}.
    {persona}{extra}

    עקרונות עבודה:
    • ענה/י בעברית, תמציתי וברור, עם רשימות קצרות כשמתאים.
    • הסתמך/י קודם כל על מידע מה-DB שנשלח בסנאפשוט. אם חסר נתון – ציין/י מה דרוש ונבנה שאילתה.
    • שמור/שמרי על דיוק במספרים (₪, אחוזים, כמויות). אל תנחש/י נתונים שלא הופיעו.
    • אם יש חריגות (מלאי נמוך, איחורים), הצע/י פעולות אופרטיביות.
    • אם השאלה לא עסקית/לא רלוונטית – הסבר/י בנימוס והצע/י נושא קשור.
    """).strip()


def few_shots(role: str) -> str:
    """דוגמאות קבועות לתשובות – טון ותבנית זהים, תוכן מותאם לתפקיד."""
    role = (role or "").strip() or "Assistant"
    if role == "Supplier":
        shots = [
            "ש: מה מצב ההזמנות הפתוחות?\nת: יש 3 הזמנות פתוחות. הבולטות: #1021 (ממתינה לאישור), #1033 (בתהליך אספקה). ממליץ לאשר #1021 היום כדי לעמוד ביעד 30 הימים.",
            "ש: אילו מוצרים קרובים לסף המלאי?\nת: גבינת עיזים (מלאי 14/מינ' 20), קממבר (12/20). ממליץ להגדיל ייצור/הזמנה ל-+25 יח' מכל אחד לשבוע הקרוב.",
        ]
    elif role == "StoreOwner":
        shots = [
            "ש: מה מצב ההזמנות האחרונות?\nת: 2 הזמנות נמסרו בזמן (#2205, #2206) ואחת באיחור קל (#2208). ממליץ לבדוק מול הספק לגבי זמינות נהגים לשישי.",
            "ש: מה כדאי לחדש במלאי?\nת: טחינה אתיופית (במלאי 6/מינ' 20), פסטה ספגטי (9/מינ' 25). מציע להזמין 30 יח' טחינה ו-40 יח' ספגטי ל-10 ימים.",
        ]
    else:
        shots = [
            "ש: מה הסטטוס הכללי?\nת: אין נתונים ספציפיים. אנא ספק/י user_id כדי לטעון סנאפשוט רלוונטי.",
        ]
    return "\n\n".join(shots)


def join_prompt(system_prompt: str, snapshot_text: str, examples: str, user_question: str) -> str:
    """מרכיב את ה-Prompt הסופי בפורמט אחיד."""
    system_prompt = (system_prompt or "").strip()
    snapshot_text = (snapshot_text or "אין סנאפשוט זמין").strip()
    examples = (examples or "").strip()
    user_question = (user_question or "").strip()

    parts = [
        system_prompt,
        "\n\n=== מידע עדכני מהמערכת ===\n" + snapshot_text,
    ]
    if examples:
        parts.append("\n\n=== דוגמאות תשובות ===\n" + examples)
    parts.append("\n\n=== השאלה ===\n" + user_question)
    parts.append("\n\n=== התשובה ===\n")

    return "".join(parts)
