
"""
Seed the database with sample GeniusBaby Cosmetics products focused on the Kenyan market,
and try to find REAL image URLs from the internet that match product names.

Image Sources (tries in order if keys present):
- Pexels API (https://www.pexels.com/api/) -> set PEXELS_API_KEY
- Unsplash API (https://unsplash.com/documentation) -> set UNSPLASH_ACCESS_KEY
- Openverse API (https://api.openverse.org/) -> no key required

If no image found:
- Rename to a real market product name (per category) and try search again.
- If still nothing, fall back to placeholder/sample images.

Environment variables:
  PEXELS_API_KEY           optional, improves hit-rate for photos
  UNSPLASH_ACCESS_KEY      optional, improves hit-rate for photos
  IMAGE_FETCH_TIMEOUT      optional, default 5 (seconds per request)
  IMAGE_SEARCH_ENABLED     optional, "1" (default) to enable, "0" to disable network calls
  IMAGE_SEARCH_SLEEP_MS    optional, sleep between API calls to be polite (default 150ms)

Usage (local):
  python seed.py
  flask --app app shell -c "import seed; seed.run()"
"""
from __future__ import annotations
from datetime import datetime
from random import choice, uniform, randint
from typing import Optional, Tuple, Dict, List
import os, time

# Optional import: if missing, we'll gracefully skip web fetches
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from app import create_app

# ---------- Helpers ----------
def slugify(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

def _get_env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() in ("1", "true", "yes", "on", "True", "YES", "ON")

def _http_get_json(url: str, headers: dict | None = None, timeout: float = 5.0) -> Optional[dict]:
    if requests is None:
        return None
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# ---------- Data Pools ----------
BRANDS = [
    "GeniusBaby", "LuxeLily", "VelvetBloom", "AuraGlow", "NairobiNectar",
    "NyotaBeauty", "SafariGlow", "CoastalCharm", "Malaika Cosmetics", "KenChic",
    "Umoja Organics", "Jambo Glam", "AfriSheen", "Mrembo Luxe", "Karibu Beauty"
]

CATEGORIES = [
    "Lipstick", "Foundation", "Concealer", "Mascara", "Blush", "Skincare", "Fragrance",
    "Serum", "Sunscreen", "Cleanser", "Toner", "Setting Spray", "Highlighter",
    "Eyeshadow", "Nail Polish", "Body Lotion", "Haircare", "Lip Gloss", "BB Cream"
]

SKIN_TYPES = ["All", "Dry", "Oily", "Combination", "Sensitive"]

SHADE_NAMES = [
    "Nairobi Nude", "Kilimani Caramel", "Eldoret Espresso", "Mombasa Mocha", "Kisumu Cocoa",
    "Embu Ivory", "Malindi Sand", "Thika Beige", "Meru Chestnut", "Kakamega Amber",
    "Naivasha Rose", "Diani Coral", "Maasai Red", "Lakeview Plum", "Turkana Bronze"
]

# Fallback stock images (used as last resort)
SAMPLE_IMAGES = [
    "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522335789203-9d5f4b8f96d1?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1505577072269-83d9b993f1f4?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1585386959984-a41552231653?q=80&w=1200&auto=format&fit=crop",
]

DESCRIPTIONS = [
    "Lightweight, long-wear formula designed for comfort in warm climates.",
    "Hydrating finish with buildable coverage and skin-loving botanicals.",
    "Matte yet breathable, formulated for all-day Nairobi hustle.",
    "Vitamin-enriched blend for a luminous, photo-ready glow.",
    "Dermatologist-tested, suitable for sensitive and combination skin."
]

INGREDIENTS = [
    "Aqua, Glycerin, Shea Butter, Vitamin E, Fragrance.",
    "Aqua, Hyaluronic Acid, Niacinamide, Vitamin C, Aloe Vera.",
    "Aqua, Squalane, Jojoba Oil, Shea Butter, Tocopherol.",
    "Aqua, Zinc Oxide, Titanium Dioxide, Vitamin E.",
    "Aqua, Lactic Acid, Glycerin, Green Tea Extract."
]

# Known market names to help image search; **illustrative** and commonly available globally/regionally.
# Each category maps to a list of (name, search_query) tuples.
MARKET_NAMES: Dict[str, List[Tuple[str, str]]] = {
    "Lipstick": [
        ("Maybelline SuperStay Matte Ink", "Maybelline SuperStay Matte Ink product"),
        ("MAC Retro Matte Ruby Woo", "MAC Ruby Woo lipstick"),
        ("Fenty Beauty Stunna Lip Paint", "Fenty Beauty Stunna Lip Paint"),
        ("Revlon Super Lustrous Lipstick", "Revlon Super Lustrous lipstick"),
    ],
    "Foundation": [
        ("Maybelline Fit Me Matte + Poreless", "Maybelline Fit Me foundation bottle"),
        ("L'Oréal Paris True Match", "Loreal True Match foundation"),
        ("Black Opal True Color Stick Foundation", "Black Opal foundation stick"),
        ("Fenty Beauty Pro Filt'r Soft Matte", "Fenty Pro Filt'r foundation"),
    ],
    "Concealer": [
        ("Maybelline Instant Age Rewind Concealer", "Maybelline Age Rewind concealer"),
        ("NARS Radiant Creamy Concealer", "NARS Radiant Creamy Concealer"),
        ("L.A. Girl Pro Conceal", "LA Girl Pro Conceal"),
    ],
    "Mascara": [
        ("L'Oréal Voluminous Lash Paradise", "Loreal Lash Paradise mascara"),
        ("Maybelline Lash Sensational", "Maybelline Lash Sensational mascara"),
        ("Essence Lash Princess", "Essence Lash Princess mascara"),
    ],
    "Blush": [
        ("NARS Blush Orgasm", "NARS Orgasm blush"),
        ("MAC Powder Blush", "MAC Powder Blush"),
        ("Maybelline Fit Me Blush", "Maybelline Fit Me blush"),
    ],
    "Skincare": [
        ("CeraVe Hydrating Cleanser", "CeraVe Hydrating Cleanser"),
        ("Neutrogena Hydro Boost Water Gel", "Neutrogena Hydro Boost"),
        ("Garnier Micellar Cleansing Water", "Garnier Micellar Water"),
    ],
    "Fragrance": [
        ("Carolina Herrera Good Girl", "Good Girl perfume"),
        ("Dior J'adore", "J'adore Dior perfume bottle"),
        ("YSL Black Opium", "YSL Black Opium perfume"),
    ],
    "Serum": [
        ("The Ordinary Niacinamide 10% + Zinc 1%", "The Ordinary Niacinamide"),
        ("L'Oréal Revitalift Serum", "Loreal Revitalift serum"),
        ("Garnier Vitamin C Serum", "Garnier Vitamin C Serum"),
    ],
    "Sunscreen": [
        ("NIVEA Sun Protect & Moisture", "Nivea Sun Protect Moisture sunscreen"),
        ("Neutrogena Ultra Sheer", "Neutrogena Ultra Sheer Dry-Touch"),
        ("La Roche-Posay Anthelios", "La Roche-Posay Anthelios sunscreen"),
    ],
    "Cleanser": [
        ("CeraVe Foaming Cleanser", "CeraVe Foaming Facial Cleanser"),
        ("Simple Kind To Skin Facial Wash", "Simple facial wash"),
        ("Garnier Pure Active", "Garnier Pure Active cleanser"),
    ],
    "Toner": [
        ("Thayers Witch Hazel Toner", "Thayers Witch Hazel Toner"),
        ("The Ordinary Glycolic Acid 7% Toning Solution", "Ordinary Glycolic Acid Toner"),
    ],
    "Setting Spray": [
        ("Urban Decay All Nighter", "Urban Decay All Nighter Setting Spray"),
        ("NYX Matte Finish Setting Spray", "NYX Matte Finish Setting Spray"),
    ],
    "Highlighter": [
        ("Becca Shimmering Skin Perfector", "Becca highlighter compact"),
        ("Maybelline Master Chrome", "Maybelline Master Chrome highlighter"),
    ],
    "Eyeshadow": [
        ("Huda Beauty Obsessions Palette", "Huda Beauty Obsessions eyeshadow"),
        ("NYX Ultimate Shadow Palette", "NYX Ultimate Shadow Palette"),
    ],
    "Nail Polish": [
        ("OPI Nail Lacquer", "OPI nail polish bottle"),
        ("Essie Nail Polish", "Essie nail polish bottle"),
    ],
    "Body Lotion": [
        ("NIVEA Body Lotion", "Nivea body lotion bottle"),
        ("Vaseline Intensive Care Lotion", "Vaseline Intensive Care body lotion"),
    ],
    "Haircare": [
        ("Tresemme Keratin Smooth", "Tresemme Keratin Smooth shampoo"),
        ("L'Oréal Elvive", "Loreal Elvive shampoo"),
    ],
    "Lip Gloss": [
        ("Fenty Beauty Gloss Bomb", "Fenty Beauty Gloss Bomb"),
        ("NYX Butter Gloss", "NYX Butter Gloss"),
    ],
    "BB Cream": [
        ("Garnier BB Cream", "Garnier BB cream"),
        ("Maybelline Dream Fresh BB", "Maybelline Dream Fresh BB Cream"),
    ],
}

def _random_price_ks():
    # Typical cosmetic price range in KES (approx)
    base = uniform(299, 4999)
    # Round to nearest 10 shillings
    return round(base / 10) * 10

def _random_sale(price):
    on_sale = randint(0, 1) == 1
    if not on_sale:
        return price
    return round(price * uniform(0.70, 0.95), 0)

def _random_name():
    brand = choice(BRANDS)
    style = choice(["Matte", "Silk", "Radiant", "Ultra", "Hydra", "Pro", "Velvet"])
    cat = choice(CATEGORIES)
    shade = "" if randint(0,1)==0 else f" — {choice(SHADE_NAMES)}"
    return f"{brand} {style} {cat}{shade}"

def _pick_market_name(category: str) -> Tuple[str, str]:
    options = MARKET_NAMES.get(category) or []
    if not options:
        # generic fallback
        q = f"{category} product bottle"
        return (f"{category} Classic", q)
    return choice(options)

# --- Image Lookup ---
def _find_image_url(query: str, timeout: float) -> Optional[str]:
    """Try Pexels, Unsplash, then Openverse. Return a direct image URL or None."""
    if requests is None:
        return None
    headers = {"User-Agent": "geniusbabycosmetics-seeder/1.0"}

    # Pexels
    pexels_key = os.getenv("PEXELS_API_KEY")
    if pexels_key:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": 1, "orientation": "square"},
                headers={"Authorization": pexels_key, **headers},
                timeout=timeout,
            )
            if r.status_code == 200:
                data = r.json()
                photos = data.get("photos") or []
                if photos:
                    src = photos[0].get("src") or {}
                    for k in ("large2x", "large", "medium", "original"):
                        if src.get(k):
                            return src[k]
        except Exception:
            pass

    # Unsplash
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if unsplash_key:
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": 1, "orientation": "squarish", "client_id": unsplash_key},
                headers=headers,
                timeout=timeout,
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results") or []
                if results:
                    urls = results[0].get("urls") or {}
                    for k in ("regular", "full", "small", "raw"):
                        if urls.get(k):
                            return urls[k]
        except Exception:
            pass

    # Openverse (no key)
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": 1, "license_type": "all"},
            headers=headers,
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            if results:
                # prefer url, else thumbnail
                u = results[0].get("url") or results[0].get("thumbnail")
                if u:
                    return u
    except Exception:
        pass

    return None

def _image_for_doc_or_rename(doc: dict, timeout: float, sleep_ms: int) -> str:
    """Try to find an image for doc['name']; otherwise rename to a market name and retry.
       Returns the URL (or a fallback sample image)."""
    enabled = _get_env_bool("IMAGE_SEARCH_ENABLED", True)
    if not enabled or requests is None:
        return choice(SAMPLE_IMAGES)

    # try original name
    url = _find_image_url(doc["name"], timeout)
    if url:
        return url
    time.sleep(sleep_ms / 1000.0)

    # rename to market name and retry
    market_name, q = _pick_market_name(doc["category"])
    doc["name"] = market_name
    doc["slug"] = slugify(market_name)
    # update brand from name prefix if present
    first_word = market_name.split()[0]
    if first_word:
        doc["brand"] = first_word
    url = _find_image_url(q, timeout)
    if url:
        return url

    # final fallback
    return choice(SAMPLE_IMAGES)

def _build_doc(timeout: float, sleep_ms: int):
    price = _random_price_ks()
    sale = _random_sale(price)
    name = _random_name()
    doc = {
        "name": name,
        "slug": slugify(name),
        "brand": name.split()[0],
        "category": next((c for c in CATEGORIES if c in name), choice(CATEGORIES)),
        "price": float(price),
        "sale_price": float(sale),
        "currency": "KES",
        "market": "KE",
        "tags": ["Kenya", "Ladies", "Beauty"],
        "description": choice(DESCRIPTIONS),
        "ingredients": choice(INGREDIENTS),
        "skin_type": choice(SKIN_TYPES),
        "image_url": None,
        "rating": round(uniform(4.0, 5.0), 1),
        "stock": randint(10, 500),
        "is_featured": randint(0, 9) == 0,  # ~10% featured
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    # find image (and possibly rename)
    doc["image_url"] = _image_for_doc_or_rename(doc, timeout, sleep_ms)
    return doc

def run(additional=1000, chunk_size=250):
    """
    Insert `additional` NEW unique products (default 1000) for the Kenyan market.
    Uses slug uniqueness to avoid duplicates.
    Tries to fetch real product images online; will rename products to real market
    names if that improves image discovery.
    """
    app = create_app()
    db = app.mongo
    coll = db.products

    timeout = float(os.getenv("IMAGE_FETCH_TIMEOUT", "5"))
    sleep_ms = int(os.getenv("IMAGE_SEARCH_SLEEP_MS", "150"))

    # Cache existing slugs to avoid duplicates
    existing_slugs = set()
    try:
        for s in coll.find({}, {"slug": 1}):
            if s.get("slug"):
                existing_slugs.add(s["slug"])
    except Exception:
        pass

    docs = []
    created = 0
    attempts = 0
    target = additional

    while created < target and attempts < target * 6:
        attempts += 1
        doc = _build_doc(timeout, sleep_ms)
        if doc["slug"] in existing_slugs:
            continue
        existing_slugs.add(doc["slug"])
        docs.append(doc)
        created += 1

        # Bulk insert in chunks
        if len(docs) >= chunk_size:
            try:
                coll.insert_many(docs, ordered=False)
            except Exception:
                # on any failure, try inserting one-by-one (slow path)
                for d in docs:
                    try: coll.insert_one(d)
                    except Exception: pass
            docs.clear()

    if docs:
        try:
            coll.insert_many(docs, ordered=False)
        except Exception:
            for d in docs:
                try: coll.insert_one(d)
                except Exception: pass

    print(f"Inserted {created} new Kenyan-market products. "
          f"(image search={'enabled' if _get_env_bool('IMAGE_SEARCH_ENABLED', True) and requests else 'disabled'})")

if __name__ == "__main__":
    run(additional=1000)
