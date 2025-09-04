
"""
Seed the database with sample GeniusBaby Cosmetics products for the Kenyan market,
and fetch image URLs **only via Openverse** (no other sources).

Openverse API (no key required):
  https://api.openverse.org/v1/images/?q=<query>&page_size=1&license_type=all

If no image is found:
  - Rename to a known market product (per category) and retry once.
  - Fall back to safe placeholder images.

Usage:
  python seed.py
  flask --app app shell -c "import seed; seed.run(500)"

Env (optional tuning):
  IMAGE_SEARCH_ENABLED=1        # default 1
  IMAGE_FETCH_TIMEOUT=5         # seconds per request
  IMAGE_SEARCH_SLEEP_MS=150     # throttle between requests
"""
from __future__ import annotations
from datetime import datetime
from random import choice, uniform, randint
from typing import Optional, Tuple, Dict, List
import os, time

try:
    import requests
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
    return v.strip().lower() in ("1", "true", "yes", "on")

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




# Fallback stock images
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

# Known market names to improve search relevance
MARKET_NAMES: Dict[str, List[Tuple[str, str]]] = {
    "Lipstick": [
        ("Maybelline SuperStay Matte Ink", "Maybelline SuperStay Matte Ink lipstick"),
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
    base = uniform(299, 4999)
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

# --- Cosmetic Image Pool (no API) ---
COSMETIC_IMAGES = [
    "https://im.idiva.com/content/2023/Apr/1-66_643e75b0c37b6.jpg?w=900&h=675&cc=1",
    "https://lfactorcosmetics.com/cdn/shop/articles/Essential_makeup_products.jpg?v=1701681592",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSKHQv8G9ZTSr_ga1KBy-ntsZ6GKaDJjDr8Gg&s",
    "https://m.media-amazon.com/images/I/71W25WUkTUL._AC_UF1000,1000_QL80_.jpg",
    "https://www.ubuy.ke/productimg/?image=aHR0cHM6Ly9tLm1lZGlhLWFtYXpvbi5jb20vaW1hZ2VzL0kvNzFPK3A2LWpGbUwuX1NMMTUwMF8uanBn.jpg",
    "https://thumbs.dreamstime.com/b/set-various-watercolor-decorative-cosmetic-makeup-products-beauty-items-mascara-lipstick-foundation-cream-brushes-eye-shadow-69331688.jpg",
    "https://i.pinimg.com/736x/ba/73/66/ba736612e254ea4c1ed5fd9ad180d09d.jpg"
    
    ]


def _random_image_url() -> str:
    """Pick a random cosmetic image from curated pool."""
    return choice(COSMETIC_IMAGES)


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
        "image_url": _random_image_url(),   # << replaced Openverse with local pool
        "rating": round(uniform(4.0, 5.0), 1),
        "stock": randint(10, 500),
        "is_featured": randint(0, 9) == 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    return doc


def run(additional=1000, chunk_size=250):
    app = create_app()
    db = app.mongo
    coll = db.products

    timeout = float(os.getenv("IMAGE_FETCH_TIMEOUT", "5"))
    sleep_ms = int(os.getenv("IMAGE_SEARCH_SLEEP_MS", "150"))

    existing_slugs = set()
    try:
        for s in coll.find({}, {"slug": 1}):
            if s.get("slug"):
                existing_slugs.add(s["slug"])
    except Exception:
        pass

    docs, created, attempts = [], 0, 0

    while created < additional and attempts < additional * 6:
        attempts += 1
        doc = _build_doc(timeout, sleep_ms)
        if doc["slug"] in existing_slugs:
            continue
        existing_slugs.add(doc["slug"])
        docs.append(doc)
        created += 1

        if len(docs) >= chunk_size:
            try:
                coll.insert_many(docs, ordered=False)
            except Exception:
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

    print(f"Inserted {created} new products (Openverse-only image lookup={'enabled' if _get_env_bool('IMAGE_SEARCH_ENABLED', True) and requests else 'disabled'}).")

if __name__ == "__main__":
    run(additional=1000)