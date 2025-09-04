import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# Target page
URL = "https://www.ubuy.ke/en/search/?ref_p=ser_tp&q=makeup"
OUTPUT_FILE = "links.txt"

# Request headers to avoid blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.ubuy.ke/",
}

# Regex to pull .jpg links from attributes like onerror
jpg_in_onerror = re.compile(r"(https?://[^\s'\"<>]+?\.jpg)", re.I)

def pick_jpg(url: str) -> str | None:
    """Return the URL trimmed up to .jpg (case-insensitive), else None."""
    if not url:
        return None
    m = re.search(r"(https?://[^\s'\"<>]+?\.jpg)", url, flags=re.I)
    return m.group(1) if m else None

def extract_img_url(img, base_url: str) -> str | None:
    """
    Prefer data-src. If absent, try the jpg inside the onerror attribute.
    Finally, fall back to src or srcset. Always return .jpg links only.
    """
    # 1) data-src
    ds = img.get("data-src")
    if ds:
        ds = pick_jpg(urljoin(base_url, ds.strip()))
        if ds:
            return ds

    # 2) onerror="checkonerrorimg(..., 'https://...jpg')"
    onerr = img.get("onerror") or ""
    m = jpg_in_onerror.search(onerr)
    if m:
        return pick_jpg(urljoin(base_url, m.group(1)))

    # 3) src
    src = img.get("src")
    if src:
        src = pick_jpg(urljoin(base_url, src.strip()))
        if src:
            return src

    # 4) srcset
    ss = img.get("srcset")
    if ss:
        for part in ss.split(","):
            cand = part.strip().split()[0]
            cand = pick_jpg(urljoin(base_url, cand))
            if cand:
                return cand

    return None

def get_product_jpgs(page_url: str) -> list[str]:
    """Scrape all .jpg product image URLs from the target page."""
    r = requests.get(page_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    urls = []
    seen = set()
    for img in soup.select("figure.product-image img"):
        u = extract_img_url(img, page_url)
        if u and u.lower().endswith(".jpg") and u not in seen:
            seen.add(u)
            urls.append(u)
    return urls

if __name__ == "__main__":
    urls = get_product_jpgs(URL)

    # Print to terminal
    for u in urls:
        print(u)

    # Write results to links.txt (each line ends with a comma)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for u in urls:
            f.write(f"{u},\n")

    print(f"\nSaved {len(urls)} .jpg links to {OUTPUT_FILE}")
