"""
Vendor Search Service — OpenStreetMap Nominatim + Overpass API

Searches for nearby agricultural supply vendors using free OpenStreetMap APIs.
Uses Overpass API for POI search and Nominatim for geocoding.
Calculates distances using the Haversine formula.

Falls back to demo vendor data when DEMO_MODE is enabled or APIs fail.
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
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
HTTP_TIMEOUT = 15.0  # seconds
MAX_RETRIES = 2

# OSM tags for agricultural supply shops
SEARCH_TAGS = [
    '"shop"="agrarian"',
    '"shop"="farm"',
    '"shop"="garden"',
    '"name"~"pesticide|कीटनाशक|krishi|कृषि|fertilizer|खाद|agri|agricultural|agro|seed|बीज"',
    '"shop"="chemist"',
    '"amenity"="marketplace"',
]

# ── Punjab vendor database loader ─────────────────
_PUNJAB_VENDORS_CACHE: Optional[List[dict]] = None


def _load_punjab_vendors() -> List[dict]:
    """Load vendors from data/vendors_punjab.json (cached)."""
    global _PUNJAB_VENDORS_CACHE
    if _PUNJAB_VENDORS_CACHE is not None:
        return _PUNJAB_VENDORS_CACHE

    json_path = Path(__file__).parent.parent.parent / "data" / "vendors_punjab.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            _PUNJAB_VENDORS_CACHE = data
            logger.info("Loaded %d vendors from Punjab database", len(data))
            return data
        except Exception as e:
            logger.warning("Failed to load vendors_punjab.json: %s", str(e))

    # Fallback to a minimal hardcoded list
    _PUNJAB_VENDORS_CACHE = [
        {"name": "Sharma Krishi Kendra", "address": "Main Market, Ludhiana", "lat": 30.9010, "lng": 75.8573, "phone": "+91 98765 43210", "rating": 4.5},
        {"name": "Punjab Agro Store", "address": "GT Road, Ludhiana", "lat": 30.9110, "lng": 75.8673, "phone": "+91 98123 45678", "rating": 4.2},
        {"name": "Kisan Sewa Kendra", "address": "Gill Road, Ludhiana", "lat": 30.8810, "lng": 75.8373, "phone": "+91 94170 12345", "rating": 4.7},
    ]
    return _PUNJAB_VENDORS_CACHE


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points
    on Earth using the Haversine formula.

    Returns distance in kilometers.
    """
    R = 6371.0  # Earth's radius in km

    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)


def _build_overpass_query(lat: float, lng: float, radius_m: int) -> str:
    """
    Build an Overpass QL query to find agricultural supply shops
    within a given radius of the coordinates.
    """
    tag_filters = "".join(
        f'  node[{tag}](around:{radius_m},{lat},{lng});\n' for tag in SEARCH_TAGS
    )

    query = f"""
[out:json][timeout:10];
(
{tag_filters});
out body;
"""
    return query.strip()


async def _search_overpass(
    latitude: float,
    longitude: float,
    radius_km: float,
    request_id: str,
) -> List[VendorResult]:
    """
    Search for vendors using the Overpass API (OpenStreetMap POI search).

    Returns a list of VendorResult sorted by distance.
    """
    radius_m = int(radius_km * 1000)
    query = _build_overpass_query(latitude, longitude, radius_m)

    logger.info("[%s] Overpass query: radius=%dm around (%.4f, %.4f)", request_id, radius_m, latitude, longitude)

    vendors: List[VendorResult] = []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    OVERPASS_API_URL,
                    data={"data": query},
                    headers={
                        "User-Agent": "KrishiSarthi/1.0 (agricultural-assistant)",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])
            logger.info("[%s] Overpass returned %d elements (attempt %d)", request_id, len(elements), attempt)

            for el in elements:
                if el.get("type") != "node":
                    continue

                tags = el.get("tags", {})
                el_lat = el.get("lat", 0)
                el_lng = el.get("lon", 0)

                name = (
                    tags.get("name")
                    or tags.get("name:en")
                    or tags.get("name:hi")
                    or tags.get("shop", "Agricultural Shop").title()
                )

                address_parts = [
                    tags.get("addr:full", ""),
                    tags.get("addr:street", ""),
                    tags.get("addr:city", ""),
                    tags.get("addr:state", ""),
                    tags.get("addr:postcode", ""),
                ]
                address = ", ".join(p for p in address_parts if p).strip(", ")
                if not address:
                    address = tags.get("address", "Address not available")

                phone = tags.get("phone") or tags.get("contact:phone", "")
                distance = haversine_distance(latitude, longitude, el_lat, el_lng)

                vendors.append(
                    VendorResult(
                        name=name,
                        address=address,
                        distance_km=distance,
                        phone=phone,
                        rating=None,
                        lat=el_lat,
                        lng=el_lng,
                    )
                )

            # If we got results, break the retry loop
            if vendors:
                break

        except httpx.TimeoutException:
            logger.warning("[%s] Overpass timeout (attempt %d/%d)", request_id, attempt, MAX_RETRIES)
        except httpx.HTTPStatusError as e:
            logger.warning("[%s] Overpass HTTP error %d (attempt %d/%d)", request_id, e.response.status_code, attempt, MAX_RETRIES)
        except Exception as e:
            logger.error("[%s] Overpass error: %s (attempt %d/%d)", request_id, str(e), attempt, MAX_RETRIES)

    # Sort by distance
    vendors.sort(key=lambda v: v.distance_km)
    return vendors


async def _search_nominatim(
    latitude: float,
    longitude: float,
    query: str,
    radius_km: float,
    request_id: str,
) -> List[VendorResult]:
    """
    Fallback search using Nominatim free-text search near a location.
    Less precise than Overpass but more forgiving with queries.
    """
    vendors: List[VendorResult] = []
    search_queries = [
        f"{query} near {latitude},{longitude}",
        f"pesticide shop",
        f"agricultural supply",
        f"fertilizer shop",
    ]

    for sq in search_queries[:2]:  # Only try first 2 to respect rate limits
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(
                    NOMINATIM_SEARCH_URL,
                    params={
                        "q": sq,
                        "format": "json",
                        "limit": 10,
                        "viewbox": _viewbox(latitude, longitude, radius_km),
                        "bounded": 1,
                        "addressdetails": 1,
                    },
                    headers={
                        "User-Agent": "KrishiSarthi/1.0 (agricultural-assistant)",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

            results = response.json()
            logger.info("[%s] Nominatim '%s' returned %d results", request_id, sq, len(results))

            for r in results:
                r_lat = float(r.get("lat", 0))
                r_lng = float(r.get("lon", 0))
                distance = haversine_distance(latitude, longitude, r_lat, r_lng)

                if distance > radius_km:
                    continue

                vendors.append(
                    VendorResult(
                        name=r.get("display_name", "").split(",")[0],
                        address=r.get("display_name", "Address not available"),
                        distance_km=distance,
                        phone="",
                        rating=None,
                        lat=r_lat,
                        lng=r_lng,
                    )
                )

            if vendors:
                break

        except Exception as e:
            logger.warning("[%s] Nominatim search failed for '%s': %s", request_id, sq, str(e))

    vendors.sort(key=lambda v: v.distance_km)
    return vendors


def _viewbox(lat: float, lng: float, radius_km: float) -> str:
    """Create a viewbox string for Nominatim bounded search."""
    delta = radius_km / 111.0  # rough degrees per km
    return f"{lng - delta},{lat + delta},{lng + delta},{lat - delta}"


def _get_demo_vendors(latitude: float, longitude: float, radius_km: float) -> List[VendorResult]:
    """
    Return demo vendors from Punjab database with distances calculated
    from user's position. Prioritizes nearest vendors.
    """
    punjab_data = _load_punjab_vendors()

    vendors = []
    for v in punjab_data:
        v_lat = v.get("lat", 30.9)
        v_lng = v.get("lng", 75.85)
        dist = haversine_distance(latitude, longitude, v_lat, v_lng)

        if dist <= radius_km:
            vendors.append(
                VendorResult(
                    name=v["name"],
                    address=v.get("address", "Punjab"),
                    distance_km=dist,
                    phone=v.get("phone", ""),
                    rating=v.get("rating"),
                    lat=v_lat,
                    lng=v_lng,
                )
            )

    # Sort by distance — nearest first
    vendors.sort(key=lambda x: x.distance_km)

    if vendors:
        return vendors

    # If no vendors within radius (user far from Punjab), generate nearby ones
    for v in punjab_data[:6]:
        offset_lat = random.uniform(-0.03, 0.03)
        offset_lng = random.uniform(-0.03, 0.03)
        v_lat = latitude + offset_lat
        v_lng = longitude + offset_lng
        dist = haversine_distance(latitude, longitude, v_lat, v_lng)

        vendors.append(
            VendorResult(
                name=v["name"],
                address=v.get("address", "Nearby"),
                distance_km=round(dist, 1),
                phone=v.get("phone", ""),
                rating=v.get("rating"),
                lat=round(v_lat, 6),
                lng=round(v_lng, 6),
            )
        )

    vendors.sort(key=lambda x: x.distance_km)
    return vendors


async def search_vendors(
    latitude: float,
    longitude: float,
    query: str = "pesticide shop",
    radius_km: float = 10.0,
    request_id: str = "",
) -> VendorSearchResponse:
    """
    Main entry point for vendor search.

    Strategy:
    1. If DEMO_MODE → return demo vendors immediately
    2. Try Overpass API (OSM POI search)
    3. Fallback to Nominatim (free-text geocoding)
    4. If all fail and DEMO_MODE → return demo vendors
    5. If all fail and not DEMO_MODE → raise exception
    """
    logger.info(
        "[%s] Vendor search: (%.4f, %.4f) | query='%s' | radius=%.1fkm | demo=%s",
        request_id, latitude, longitude, query, radius_km, settings.is_demo,
    )

    # ── Demo mode shortcut ────────────────────────
    if settings.is_demo and settings.mock_vendor_data:
        logger.info("[%s] DEMO_MODE active, returning mock vendors", request_id)
        demo = _get_demo_vendors(latitude, longitude, radius_km)
        return VendorSearchResponse(
            vendors=demo,
            total=len(demo),
            search_radius_km=radius_km,
            source="demo",
        )

    # ── Try Overpass API ──────────────────────────
    vendors = await _search_overpass(latitude, longitude, radius_km, request_id)

    if vendors:
        logger.info("[%s] Overpass found %d vendors", request_id, len(vendors))
        return VendorSearchResponse(
            vendors=vendors,
            total=len(vendors),
            search_radius_km=radius_km,
            source="openstreetmap_overpass",
        )

    # ── Fallback: Nominatim ───────────────────────
    logger.info("[%s] Overpass returned 0, trying Nominatim", request_id)
    vendors = await _search_nominatim(latitude, longitude, query, radius_km, request_id)

    if vendors:
        logger.info("[%s] Nominatim found %d vendors", request_id, len(vendors))
        return VendorSearchResponse(
            vendors=vendors,
            total=len(vendors),
            search_radius_km=radius_km,
            source="openstreetmap_nominatim",
        )

    # ── All APIs failed — demo fallback ───────────
    if settings.is_demo:
        logger.warning("[%s] All APIs returned 0 results, using demo fallback", request_id)
        demo = _get_demo_vendors(latitude, longitude, radius_km)
        return VendorSearchResponse(
            vendors=demo,
            total=len(demo),
            search_radius_km=radius_km,
            source="demo_fallback",
        )

    # ── No results and not demo mode ──────────────
    logger.warning("[%s] No vendors found and DEMO_MODE is off", request_id)
    return VendorSearchResponse(
        vendors=[],
        total=0,
        search_radius_km=radius_km,
        source="openstreetmap",
    )
