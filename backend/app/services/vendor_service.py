"""
Vendor Search Service — Google Places + OpenStreetMap

Searches for nearby agricultural supply vendors using:
1. Google Places API (Nearby Search) — real shops with ratings, phone, photos
2. OpenStreetMap Overpass API — free fallback with POI search
3. Nominatim — free geo-search fallback
4. Demo vendor database — final fallback

Search chain: Google Places → Overpass → Nominatim → Demo fallback
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import List, Optional

import httpx

from app.config import get_settings
from app.models.schemas import VendorResult, VendorSearchResponse
from app.utils.logger import get_logger

logger = get_logger("service.vendor")
settings = get_settings()

# ── Constants ─────────────────────────────────────
GOOGLE_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
HTTP_TIMEOUT = 15.0
MAX_RETRIES = 2

GOOGLE_SEARCH_KEYWORDS = [
    "pesticide shop", "agricultural supply store", "fertilizer shop",
    "krishi kendra", "seed store agriculture",
]

SEARCH_TAGS = [
    '"shop"="agrarian"', '"shop"="farm"', '"shop"="garden"',
    '"name"~"pesticide|कीटनाशक|krishi|कृषि|fertilizer|खाद|agri|agricultural|agro|seed|बीज"',
    '"shop"="chemist"', '"amenity"="marketplace"',
]

_PUNJAB_VENDORS_CACHE: Optional[List[dict]] = None


def _load_punjab_vendors() -> List[dict]:
    global _PUNJAB_VENDORS_CACHE
    if _PUNJAB_VENDORS_CACHE is not None:
        return _PUNJAB_VENDORS_CACHE

    json_path = Path(__file__).parent.parent.parent / "data" / "vendors_punjab.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            _PUNJAB_VENDORS_CACHE = data
            return data
        except Exception:
            pass

    _PUNJAB_VENDORS_CACHE = [
        {"name": "Sharma Krishi Kendra", "address": "Main Market, Ludhiana", "lat": 30.9010, "lng": 75.8573, "phone": "+91 98765 43210", "rating": 4.5},
        {"name": "Punjab Agro Store", "address": "GT Road, Ludhiana", "lat": 30.9110, "lng": 75.8673, "phone": "+91 98123 45678", "rating": 4.2},
        {"name": "Kisan Sewa Kendra", "address": "Gill Road, Ludhiana", "lat": 30.8810, "lng": 75.8373, "phone": "+91 94170 12345", "rating": 4.7},
    ]
    return _PUNJAB_VENDORS_CACHE


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


# ━━━ Google Places API ━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _search_google_places(
    latitude: float, longitude: float, query: str, radius_km: float, request_id: str,
) -> List[VendorResult]:
    radius_m = int(min(radius_km * 1000, 50000))
    vendors: List[VendorResult] = []
    seen_ids: set = set()

    search_terms = [query] + [kw for kw in GOOGLE_SEARCH_KEYWORDS if kw != query]

    for keyword in search_terms[:3]:
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(GOOGLE_PLACES_NEARBY_URL, params={
                    "location": f"{latitude},{longitude}", "radius": radius_m,
                    "keyword": keyword, "type": "store", "language": "en",
                    "key": settings.google_maps_api_key,
                })
                response.raise_for_status()

            data = response.json()
            if data.get("status") == "REQUEST_DENIED":
                logger.error("[%s] Google Places denied: %s", request_id, data.get("error_message", ""))
                break

            for place in data.get("results", []):
                pid = place.get("place_id", "")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                plat = place.get("geometry", {}).get("location", {}).get("lat", 0)
                plng = place.get("geometry", {}).get("location", {}).get("lng", 0)

                vendors.append(VendorResult(
                    name=place.get("name", "Unknown Shop"),
                    address=place.get("vicinity", "Address not available"),
                    distance_km=haversine_distance(latitude, longitude, plat, plng),
                    phone="", rating=place.get("rating"), lat=plat, lng=plng,
                ))

        except Exception as e:
            logger.warning("[%s] Google Places error for '%s': %s", request_id, keyword, str(e))

    vendors.sort(key=lambda v: v.distance_km)
    return vendors


# ━━━ OpenStreetMap Overpass ━━━━━━━━━━━━━━━━━━━━━

def _build_overpass_query(lat: float, lng: float, radius_m: int) -> str:
    tag_filters = "".join(f'  node[{tag}](around:{radius_m},{lat},{lng});\n' for tag in SEARCH_TAGS)
    return f"[out:json][timeout:10];\n(\n{tag_filters});\nout body;"


async def _search_overpass(latitude: float, longitude: float, radius_km: float, request_id: str) -> List[VendorResult]:
    radius_m = int(radius_km * 1000)
    query = _build_overpass_query(latitude, longitude, radius_m)
    vendors: List[VendorResult] = []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(OVERPASS_API_URL, data={"data": query},
                    headers={"User-Agent": "KrishiSarthi/1.0", "Accept": "application/json"})
                response.raise_for_status()

            for el in response.json().get("elements", []):
                if el.get("type") != "node":
                    continue
                tags = el.get("tags", {})
                el_lat, el_lng = el.get("lat", 0), el.get("lon", 0)
                name = tags.get("name") or tags.get("name:en") or tags.get("name:hi") or "Agricultural Shop"
                address_parts = [tags.get(f"addr:{k}", "") for k in ("full", "street", "city", "state")]
                address = ", ".join(p for p in address_parts if p) or tags.get("address", "Address not available")

                vendors.append(VendorResult(
                    name=name, address=address,
                    distance_km=haversine_distance(latitude, longitude, el_lat, el_lng),
                    phone=tags.get("phone", ""), rating=None, lat=el_lat, lng=el_lng,
                ))
            if vendors:
                break
        except Exception as e:
            logger.warning("[%s] Overpass error (attempt %d): %s", request_id, attempt, str(e))

    vendors.sort(key=lambda v: v.distance_km)
    return vendors


async def _search_nominatim(latitude: float, longitude: float, query: str, radius_km: float, request_id: str) -> List[VendorResult]:
    vendors: List[VendorResult] = []
    for sq in [query, "pesticide shop"][:2]:
        try:
            delta = radius_km / 111.0
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(NOMINATIM_SEARCH_URL, params={
                    "q": sq, "format": "json", "limit": 10,
                    "viewbox": f"{longitude-delta},{latitude+delta},{longitude+delta},{latitude-delta}",
                    "bounded": 1, "addressdetails": 1,
                }, headers={"User-Agent": "KrishiSarthi/1.0"})
                response.raise_for_status()

            for r in response.json():
                rlat, rlng = float(r.get("lat", 0)), float(r.get("lon", 0))
                dist = haversine_distance(latitude, longitude, rlat, rlng)
                if dist <= radius_km:
                    vendors.append(VendorResult(
                        name=r.get("display_name", "").split(",")[0],
                        address=r.get("display_name", ""), distance_km=dist,
                        phone="", rating=None, lat=rlat, lng=rlng,
                    ))
            if vendors:
                break
        except Exception as e:
            logger.warning("[%s] Nominatim error: %s", request_id, str(e))

    vendors.sort(key=lambda v: v.distance_km)
    return vendors


def _get_demo_vendors(latitude: float, longitude: float, radius_km: float) -> List[VendorResult]:
    punjab_data = _load_punjab_vendors()
    vendors = []
    for v in punjab_data:
        v_lat, v_lng = v.get("lat", 30.9), v.get("lng", 75.85)
        dist = haversine_distance(latitude, longitude, v_lat, v_lng)
        if dist <= radius_km:
            vendors.append(VendorResult(name=v["name"], address=v.get("address", "Punjab"),
                distance_km=dist, phone=v.get("phone", ""), rating=v.get("rating"), lat=v_lat, lng=v_lng))

    vendors.sort(key=lambda x: x.distance_km)
    if vendors:
        return vendors

    for v in punjab_data[:6]:
        v_lat, v_lng = latitude + random.uniform(-0.03, 0.03), longitude + random.uniform(-0.03, 0.03)
        dist = haversine_distance(latitude, longitude, v_lat, v_lng)
        vendors.append(VendorResult(name=v["name"], address=v.get("address", "Nearby"),
            distance_km=round(dist, 1), phone=v.get("phone", ""), rating=v.get("rating"),
            lat=round(v_lat, 6), lng=round(v_lng, 6)))
    vendors.sort(key=lambda x: x.distance_km)
    return vendors


# ━━━ Main Entry Point ━━━━━━━━━━━━━━━━━━━━━━━━━━

async def search_vendors(
    latitude: float, longitude: float, query: str = "pesticide shop",
    radius_km: float = 10.0, request_id: str = "",
) -> VendorSearchResponse:
    """
    Search chain: Google Places → Overpass → Nominatim → Demo fallback
    """
    logger.info("[%s] Vendor search: (%.4f, %.4f) query='%s' radius=%.1fkm", request_id, latitude, longitude, query, radius_km)

    if settings.is_demo and settings.mock_vendor_data:
        demo = _get_demo_vendors(latitude, longitude, radius_km)
        return VendorSearchResponse(vendors=demo, total=len(demo), search_radius_km=radius_km, source="demo")

    # Google Places (best quality)
    if settings.google_maps_api_key:
        vendors = await _search_google_places(latitude, longitude, query, radius_km, request_id)
        if vendors:
            return VendorSearchResponse(vendors=vendors, total=len(vendors), search_radius_km=radius_km, source="google_places")

    # Overpass (free OSM)
    vendors = await _search_overpass(latitude, longitude, radius_km, request_id)
    if vendors:
        return VendorSearchResponse(vendors=vendors, total=len(vendors), search_radius_km=radius_km, source="openstreetmap_overpass")

    # Nominatim (free geo)
    vendors = await _search_nominatim(latitude, longitude, query, radius_km, request_id)
    if vendors:
        return VendorSearchResponse(vendors=vendors, total=len(vendors), search_radius_km=radius_km, source="openstreetmap_nominatim")

    # Demo fallback
    demo = _get_demo_vendors(latitude, longitude, radius_km)
    return VendorSearchResponse(vendors=demo, total=len(demo), search_radius_km=radius_km, source="demo_fallback")
