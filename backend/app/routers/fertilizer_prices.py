"""Fertilizer pricing defaults and price map builder."""
from fastapi import APIRouter
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/fertilizer-prices", tags=["fertilizer-prices"])

CURRENCY_CONVERSION = {
    "MXN": 1.0,
    "USD": 0.058,
    "EUR": 0.053
}


def _load_catalog_with_prices():
    """Load catalog and build price index."""
    from app.services.fertiirrigation_ai_optimizer import _load_hydro_fertilizers_catalog
    catalog = _load_hydro_fertilizers_catalog()
    return {f.get("id", f.get("slug")): f for f in catalog if f.get("id")}


DEFAULT_PRICES_BY_CURRENCY = {}


def get_default_price_for_currency(slug: str, currency: str = "MXN") -> dict:
    """Get default price for a fertilizer by slug and currency."""
    catalog_index = _load_catalog_with_prices()
    fert = catalog_index.get(slug, {})
    price_mxn = fert.get("default_price_mxn", 25.0) or 25.0
    
    conversion = CURRENCY_CONVERSION.get(currency, 1.0)
    price = price_mxn * conversion
    
    form = fert.get("form", "solid")
    if form == "liquid":
        return {"price_per_liter": price, "price_per_kg": None}
    return {"price_per_kg": price, "price_per_liter": None}


def load_default_fertilizers(_db=None):
    from app.services.fertiirrigation_ai_optimizer import _load_hydro_fertilizers_catalog

    catalog = _load_hydro_fertilizers_catalog()
    return [{
        "id": f["id"],
        "slug": f.get("slug", f["id"]),
        "name": f.get("name", f["id"]),
        "type": f.get("type", "salt"),
        "form": f.get("form", "solid"),
        "n_pct": f.get("n_pct", 0),
        "p2o5_pct": f.get("p2o5_pct", 0),
        "k2o_pct": f.get("k2o_pct", 0),
        "ca_pct": f.get("ca_pct", 0),
        "mg_pct": f.get("mg_pct", 0),
        "s_pct": f.get("s_pct", 0),
        "fe_pct": f.get("fe_pct", 0),
        "mn_pct": f.get("mn_pct", 0),
        "zn_pct": f.get("zn_pct", 0),
        "cu_pct": f.get("cu_pct", 0),
        "b_pct": f.get("b_pct", 0),
        "mo_pct": f.get("mo_pct", 0),
        "stock_tank": f.get("stock_tank", "B"),
        "default_price_mxn": f.get("default_price_mxn", 25.0),
        "meq_per_gram": f.get("meq_per_gram", {})
    } for f in catalog if f.get("id")]


def build_price_map(db, user_id: int, catalog_fertilizers: List[Dict], currency: str = "MXN") -> Dict[str, Dict]:
    """
    Build a price map for fertilizers.
    
    Tries to get user-specific prices first, falls back to catalog defaults.
    
    Returns:
        Dict mapping fertilizer slug/id to dict with price_per_kg/price_per_liter
    """
    price_map = {}
    catalog_index = _load_catalog_with_prices()
    conversion = CURRENCY_CONVERSION.get(currency, 1.0)
    
    try:
        from app.models.hydro_ions_models import UserFertilizerPrice
        user_prices = db.query(UserFertilizerPrice).filter(
            UserFertilizerPrice.user_id == user_id,
            UserFertilizerPrice.currency == currency
        ).all()
        
        for up in user_prices:
            price_map[up.fertilizer_id] = {
                "price_per_kg": up.price_per_kg or 0,
                "price_per_liter": up.price_per_liter or 0
            }
    except Exception:
        pass
    
    for fert in catalog_fertilizers:
        fert_id = fert.get("id") or fert.get("slug")
        if fert_id and fert_id not in price_map:
            cat_fert = catalog_index.get(fert_id, {})
            price_mxn = cat_fert.get("default_price_mxn") or fert.get("default_price_mxn") or 25.0
            form = cat_fert.get("form") or fert.get("form", "solid")
            price = price_mxn * conversion
            
            if form == "liquid":
                price_map[fert_id] = {"price_per_kg": 0, "price_per_liter": price}
            else:
                price_map[fert_id] = {"price_per_kg": price, "price_per_liter": 0}
    
    return price_map


def get_user_currency(db, user_id: int) -> Dict[str, str]:
    """Get user's preferred currency."""
    try:
        from app.models.hydro_ions_models import UserFertilizerPrice
        user_price = db.query(UserFertilizerPrice).filter(
            UserFertilizerPrice.user_id == user_id
        ).first()
        if user_price and user_price.currency:
            return {"code": user_price.currency}
    except Exception:
        pass
    return {"code": "MXN"}


@router.get("/settings")
async def get_price_settings():
    """Get user's fertilizer price settings."""
    return {"preferred_currency": "MXN", "prices": {}}
