"""
Vendor Finder Router — POST /api/find-vendors

Searches for nearby pesticide/agricultural supply vendors using
Google Maps Places API. Falls back to mock vendor data in DEMO_MODE.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models.schemas import VendorResult, VendorSearchRequest, VendorSearchResponse
from app.utils.logger import get_logger

logger = get_logger("router.vendors")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Vendors"])

# ── Demo fallback data (Punjab region vendors) ────
DEMO_VENDORS = [
    VendorResult(
        name="Sharma Krishi Kendra",
        address="Main Market, Ludhiana, Punjab 141001",
        distance_km=2.3,
        phone="+91 98765 43210",
        rating=4.5,
        lat=30.9010,
        lng=75.8573,
    ),
    VendorResult(
        name="Punjab Agro Store",
        address="GT Road, Near Bus Stand, Ludhiana",
        distance_km=3.8,
        phone="+91 98123 45678",
        rating=4.2,
        lat=30.9110,
        lng=75.8673,
    ),
    VendorResult(
        name="Kisan Sewa Kendra",
        address="Gill Road, Ludhiana, Punjab 141003",
        distance_km=5.1,
        phone="+91 94170 12345",
        rating=4.7,
        lat=30.8810,
        lng=75.8373,
    ),
    VendorResult(
        name="Harpal Singh Pesticide Shop",
        address="Samrala Chowk, Ludhiana",
        distance_km=6.4,
        phone="+91 98550 67890",
        rating=4.0,
        lat=30.9210,
        lng=75.8873,
    ),
    VendorResult(
        name="Guru Nanak Agri Supplies",
        address="Pakhowal Road, Ludhiana, Punjab",
        distance_km=7.9,
        phone="+91 99880 11223",
        rating=4.3,
        lat=30.8910,
        lng=75.8173,
    ),
    VendorResult(
        name="Modern Krishi Dukaan",
        address="College Road, Near PAU Gate, Ludhiana",
        distance_km=4.2,
        phone="+91 98761 22334",
        rating=4.6,
        lat=30.9050,
        lng=75.8050,
    ),
]


@router.post(
    "/find-vendors",
    response_model=VendorSearchResponse,
    summary="Find nearby agricultural supply vendors",
    description="Searches for pesticide shops and agricultural supply vendors near the given location.",
)
async def find_vendors(request: VendorSearchRequest):
    """
    Vendor search endpoint.

    1. Validates coordinates
    2. Searches Google Maps Places API (or returns demo vendors)
    3. Returns sorted vendor list by distance
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "[%s] Vendor search: lat=%.4f, lng=%.4f, query='%s', radius=%.1fkm",
        request_id, request.latitude, request.longitude, request.query, request.radius_km,
    )

    # ── Search vendors ────────────────────────────
    try:
        from app.services.vendor_service import search_vendors
        result = await search_vendors(
            latitude=request.latitude,
            longitude=request.longitude,
            query=request.query or "pesticide shop",
            radius_km=request.radius_km,
            request_id=request_id,
        )
        logger.info("[%s] Found %d vendors", request_id, result.total)
        return result

    except ImportError:
        if settings.is_demo:
            logger.warning("[%s] Vendor service not available, using demo fallback", request_id)
            return _demo_vendors(request_id, request)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vendor search service is not available",
        )
    except Exception as e:
        logger.error("[%s] Vendor search failed: %s", request_id, str(e))
        if settings.is_demo:
            logger.warning("[%s] Falling back to demo vendors", request_id)
            return _demo_vendors(request_id, request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vendor search failed: {str(e)}",
        )


def _demo_vendors(request_id: str, request: VendorSearchRequest) -> VendorSearchResponse:
    """Return mock vendor data for demo mode."""
    import math
    import random

    vendors = []
    for v in DEMO_VENDORS:
        # Recalculate approximate distance from user's actual position
        delta_lat = abs(v.lat - request.latitude)
        delta_lng = abs(v.lng - request.longitude)
        approx_km = math.sqrt(delta_lat**2 + delta_lng**2) * 111.0  # rough km conversion
        approx_km = round(approx_km, 1) if approx_km > 0.1 else round(random.uniform(1.5, 8.0), 1)

        if approx_km <= request.radius_km:
            vendors.append(
                VendorResult(
                    name=v.name,
                    address=v.address,
                    distance_km=approx_km,
                    phone=v.phone,
                    rating=v.rating,
                    lat=v.lat,
                    lng=v.lng,
                )
            )

    # If no vendors in radius (user far from Punjab), return all with fake distances
    if not vendors:
        vendors = [
            VendorResult(
                name=v.name,
                address=v.address,
                distance_km=round(random.uniform(1.0, request.radius_km), 1),
                phone=v.phone,
                rating=v.rating,
                lat=request.latitude + random.uniform(-0.02, 0.02),
                lng=request.longitude + random.uniform(-0.02, 0.02),
            )
            for v in DEMO_VENDORS
        ]

    # Sort by distance
    vendors.sort(key=lambda x: x.distance_km)

    logger.info("[%s] DEMO vendors: returning %d vendors", request_id, len(vendors))

    return VendorSearchResponse(
        vendors=vendors,
        total=len(vendors),
        search_radius_km=request.radius_km,
        source="demo",
    )
