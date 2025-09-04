
### Image search in seed.py

To enable real image fetching during seeding, set one or more of:
- `PEXELS_API_KEY`
- `UNSPLASH_ACCESS_KEY`

Optional:
- `IMAGE_SEARCH_ENABLED=1` (default)
- `IMAGE_FETCH_TIMEOUT=5`
- `IMAGE_SEARCH_SLEEP_MS=150`

If no image is found, the seeder will rename the product to a real market name per category
and retry; otherwise it will fall back to built-in placeholder image URLs.
