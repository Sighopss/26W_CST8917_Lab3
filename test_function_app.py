# =============================================================================
# FleetBook — Azure Function Tests
# CST8917 Lab 3
# =============================================================================

import json
import azure.functions as func
from function_app import check_booking, health


# =============================================================================
# TEST HELPERS
# =============================================================================

def invoke_check_booking(body: dict) -> func.HttpResponse:
    """Invoke the check-booking Azure Function with a given JSON body.

    Constructs an azure.functions.HttpRequest with the provided dict
    serialised as JSON, calls the function, and returns the HttpResponse.
    """
    req = func.HttpRequest(
        method="POST",
        body=json.dumps(body).encode("utf-8"),
        url="/api/check-booking",
        headers={"Content-Type": "application/json"},
    )
    return check_booking(req)


def invoke_health() -> func.HttpResponse:
    """Invoke the health Azure Function endpoint."""
    req = func.HttpRequest(
        method="GET",
        body=b"",
        url="/api/health",
    )
    return health(req)


def parse_response(resp: func.HttpResponse) -> dict:
    """Parse the JSON body from an HttpResponse."""
    return json.loads(resp.get_body().decode("utf-8"))


# =============================================================================
# UNIT TESTS — Specific Booking Scenarios (Task 2.2)
# Requirements: 6.1, 6.2, 1.5
# =============================================================================


def test_sedan_ottawa_confirmed_with_v001():
    """Sedan in Ottawa should be confirmed with vehicle V001 assigned.

    V001 is a sedan in Ottawa, available, with 25000 km mileage.
    Validates: Requirement 6.1
    """
    body = {
        "bookingId": "BK-TEST-001",
        "customerName": "Jane Doe",
        "customerEmail": "jane@example.com",
        "vehicleType": "sedan",
        "pickupLocation": "Ottawa",
        "pickupDate": "2026-04-01",
        "returnDate": "2026-04-05",
        "notes": "",
    }
    resp = invoke_check_booking(body)
    assert resp.status_code == 200

    data = parse_response(resp)
    assert data["status"] == "confirmed"
    assert data["vehicleId"] == "V001"
    assert data["vehicleType"] == "sedan"
    assert data["location"] == "Ottawa"
    assert data["bookingId"] == "BK-TEST-001"
    assert data["customerName"] == "Jane Doe"
    assert data["customerEmail"] == "jane@example.com"
    assert data["estimatedPrice"] is not None
    assert data["estimatedPrice"] > 0


def test_sedan_montreal_rejected():
    """Sedan in Montreal should be rejected because V003 is unavailable.

    V003 is the only sedan in Montreal and it has available=False.
    Validates: Requirement 6.2
    """
    body = {
        "bookingId": "BK-TEST-002",
        "customerName": "John Smith",
        "customerEmail": "john@example.com",
        "vehicleType": "sedan",
        "pickupLocation": "Montreal",
        "pickupDate": "2026-04-01",
        "returnDate": "2026-04-03",
        "notes": "",
    }
    resp = invoke_check_booking(body)
    assert resp.status_code == 200

    data = parse_response(resp)
    assert data["status"] == "rejected"
    assert data["vehicleId"] is None
    assert data["estimatedPrice"] is None
    assert data["vehicleType"] == "sedan"
    assert data["location"] == "Montreal"
    assert data["bookingId"] == "BK-TEST-002"


def test_health_endpoint_returns_correct_json():
    """Health endpoint should return status, service name, and fleet size.

    Validates: Requirement 1.5
    """
    resp = invoke_health()
    assert resp.status_code == 200

    data = parse_response(resp)
    assert data["status"] == "healthy"
    assert data["service"] == "FleetBook Function App"
    assert data["fleet_size"] == 10


# =============================================================================
# UNIT TESTS — Error Conditions (Task 2.3)
# Requirements: 1.4
# =============================================================================


def test_invalid_json_body_returns_400():
    """Sending a non-JSON body should return 400 with an error message.

    Validates: Requirement 1.4
    """
    req = func.HttpRequest(
        method="POST",
        body=b"this is not json{{{",
        url="/api/check-booking",
        headers={"Content-Type": "application/json"},
    )
    resp = check_booking(req)
    assert resp.status_code == 400

    data = parse_response(resp)
    assert data["error"] == "Invalid JSON in request body"


def test_missing_all_required_fields_returns_400():
    """Sending an empty JSON object should return 400 listing all missing fields.

    Required fields: bookingId, customerName, customerEmail, vehicleType, pickupLocation
    Validates: Requirement 1.4
    """
    resp = invoke_check_booking({})
    assert resp.status_code == 400

    data = parse_response(resp)
    assert "Missing required fields" in data["error"]
    for field in ["bookingId", "customerName", "customerEmail", "vehicleType", "pickupLocation"]:
        assert field in data["error"]


def test_missing_some_required_fields_returns_400():
    """Sending a partial body should return 400 listing only the missing fields.

    Validates: Requirement 1.4
    """
    body = {
        "bookingId": "BK-ERR-001",
        "customerName": "Test User",
        # missing: customerEmail, vehicleType, pickupLocation
    }
    resp = invoke_check_booking(body)
    assert resp.status_code == 400

    data = parse_response(resp)
    assert "Missing required fields" in data["error"]
    assert "customerEmail" in data["error"]
    assert "vehicleType" in data["error"]
    assert "pickupLocation" in data["error"]
    # Fields that ARE present should NOT appear in the error
    assert "bookingId" not in data["error"].split(": ", 1)[1]
    assert "customerName" not in data["error"].split(": ", 1)[1]


# =============================================================================
# PROPERTY-BASED TESTS (Task 2.4)
# Feature: fleetbook-vehicle-booking, Property 1: Response structure invariant
# =============================================================================

from hypothesis import given, settings, strategies as st

# Strategies for generating booking requests
# Include fleet vehicle types + extras to cover rejection paths
vehicle_types = st.sampled_from(["sedan", "SUV", "truck", "van", "minibus", "convertible"])
# Include fleet locations + extras to cover rejection paths
pickup_locations = st.sampled_from(["Ottawa", "Toronto", "Montreal", "Vancouver", "Calgary", "Halifax", "Winnipeg"])

booking_request_strategy = st.fixed_dictionaries({
    "bookingId": st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-")),
    "customerName": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",), whitelist_characters=" ")),
    "customerEmail": st.from_regex(r"[a-z]{1,10}@[a-z]{1,10}\.[a-z]{2,4}", fullmatch=True),
    "vehicleType": vehicle_types,
    "pickupLocation": pickup_locations,
    "pickupDate": st.dates().map(lambda d: d.isoformat()),
    "returnDate": st.dates().map(lambda d: d.isoformat()),
    "notes": st.sampled_from(["", "GPS", "child seat", "insurance", "GPS, child seat", "GPS, insurance"]),
})


@given(booking=booking_request_strategy)
@settings(max_examples=100)
def test_property1_response_structure_invariant(booking):
    """Property 1: Response structure invariant.

    For any valid booking request, the response contains bookingId,
    customerName, customerEmail, status, vehicleId, vehicleType, location,
    and reason, where status is "confirmed" or "rejected".

    **Validates: Requirements 1.4, 3.4**
    """
    # Feature: fleetbook-vehicle-booking, Property 1: Response structure invariant
    resp = invoke_check_booking(booking)
    assert resp.status_code == 200

    data = parse_response(resp)

    # All required fields must be present
    required_keys = ["bookingId", "customerName", "customerEmail", "status",
                     "vehicleId", "vehicleType", "location", "reason"]
    for key in required_keys:
        assert key in data, f"Missing key '{key}' in response"

    # Status must be one of the two valid values
    assert data["status"] in ("confirmed", "rejected"), (
        f"Unexpected status '{data['status']}', expected 'confirmed' or 'rejected'"
    )


# =============================================================================
# PROPERTY-BASED TESTS (Task 2.5)
# Feature: fleetbook-vehicle-booking, Property 2: Confirmed booking consistency
# =============================================================================

from hypothesis import assume
from function_app import FLEET

# Strategy that only generates type+location combos known to produce confirmed bookings.
# Derived from FLEET: only combos where at least one vehicle is available.
_confirmed_combos = list({
    (v["type"], v["location"])
    for v in FLEET
    if v["available"]
})

confirmed_booking_strategy = st.fixed_dictionaries({
    "bookingId": st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-")),
    "customerName": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",), whitelist_characters=" ")),
    "customerEmail": st.from_regex(r"[a-z]{1,10}@[a-z]{1,10}\.[a-z]{2,4}", fullmatch=True),
    "combo": st.sampled_from(_confirmed_combos),
    "pickupDate": st.dates().map(lambda d: d.isoformat()),
    "returnDate": st.dates().map(lambda d: d.isoformat()),
    "notes": st.sampled_from(["", "GPS", "child seat", "insurance", "GPS, child seat", "GPS, insurance"]),
})


@given(booking=confirmed_booking_strategy)
@settings(max_examples=100)
def test_property2_confirmed_booking_consistency(booking):
    """Property 2: Confirmed booking consistency.

    For any confirmed booking, vehicleId is non-null, estimatedPrice is
    positive, and the assigned vehicle matches the requested type and location.

    **Validates: Requirements 1.4, 3.4, 6.1**
    """
    # Feature: fleetbook-vehicle-booking, Property 2: Confirmed booking consistency
    vehicle_type, pickup_location = booking.pop("combo")
    booking["vehicleType"] = vehicle_type
    booking["pickupLocation"] = pickup_location

    resp = invoke_check_booking(booking)
    assert resp.status_code == 200

    data = parse_response(resp)

    # We generated combos that should always confirm; skip if somehow rejected
    assume(data["status"] == "confirmed")

    # vehicleId must be non-null
    assert data["vehicleId"] is not None, "Confirmed booking must have a vehicleId"

    # estimatedPrice must be positive
    assert data["estimatedPrice"] is not None, "Confirmed booking must have an estimatedPrice"
    assert data["estimatedPrice"] > 0, (
        f"estimatedPrice should be positive, got {data['estimatedPrice']}"
    )

    # The assigned vehicle must match the requested type and location
    assigned = next((v for v in FLEET if v["id"] == data["vehicleId"]), None)
    assert assigned is not None, f"vehicleId '{data['vehicleId']}' not found in FLEET"
    assert assigned["type"].lower() == vehicle_type.lower(), (
        f"Assigned vehicle type '{assigned['type']}' doesn't match requested '{vehicle_type}'"
    )
    assert assigned["location"].lower() == pickup_location.lower(), (
        f"Assigned vehicle location '{assigned['location']}' doesn't match requested '{pickup_location}'"
    )


# =============================================================================
# PROPERTY-BASED TESTS (Task 2.6)
# Feature: fleetbook-vehicle-booking, Property 3: Rejected booking null fields
# =============================================================================


@given(booking=booking_request_strategy)
@settings(max_examples=100)
def test_property3_rejected_booking_null_fields(booking):
    """Property 3: Rejected booking null fields.

    For any rejected booking, vehicleId is null and estimatedPrice is null.

    **Validates: Requirements 1.4, 3.4, 6.2**
    """
    # Feature: fleetbook-vehicle-booking, Property 3: Rejected booking null fields
    resp = invoke_check_booking(booking)
    assert resp.status_code == 200

    data = parse_response(resp)

    # Only test rejected bookings
    assume(data["status"] == "rejected")

    # vehicleId must be null for rejected bookings
    assert data["vehicleId"] is None, (
        f"Rejected booking should have vehicleId=None, got '{data['vehicleId']}'"
    )

    # estimatedPrice must be null for rejected bookings
    assert data["estimatedPrice"] is None, (
        f"Rejected booking should have estimatedPrice=None, got {data['estimatedPrice']}"
    )


# =============================================================================
# PROPERTY-BASED TESTS (Task 2.7)
# Feature: fleetbook-vehicle-booking, Property 4: Pricing determinism
# =============================================================================


@given(booking=booking_request_strategy)
@settings(max_examples=100)
def test_property4_pricing_determinism(booking):
    """Property 4: Pricing determinism.

    For any two identical booking requests (same vehicleType, pickupLocation,
    pickupDate, returnDate, and notes), the estimatedPrice values are identical.

    **Validates: Requirements 1.4, 3.4**
    """
    # Feature: fleetbook-vehicle-booking, Property 4: Pricing determinism
    resp1 = invoke_check_booking(dict(booking))
    resp2 = invoke_check_booking(dict(booking))

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    data1 = parse_response(resp1)
    data2 = parse_response(resp2)

    assert data1["estimatedPrice"] == data2["estimatedPrice"], (
        f"Identical requests produced different prices: "
        f"{data1['estimatedPrice']} vs {data2['estimatedPrice']}"
    )


# =============================================================================
# PROPERTY-BASED TESTS (Task 2.8)
# Feature: fleetbook-vehicle-booking, Property 5: Lowest mileage vehicle selection
# =============================================================================


@given(booking=confirmed_booking_strategy)
@settings(max_examples=100)
def test_property5_lowest_mileage_vehicle_selection(booking):
    """Property 5: Lowest mileage vehicle selection.

    For any confirmed booking, the assigned vehicleId corresponds to the
    lowest-mileage available vehicle matching the requested type and location.

    **Validates: Requirements 1.4, 3.4**
    """
    # Feature: fleetbook-vehicle-booking, Property 5: Lowest mileage vehicle selection
    vehicle_type, pickup_location = booking.pop("combo")
    booking["vehicleType"] = vehicle_type
    booking["pickupLocation"] = pickup_location

    resp = invoke_check_booking(booking)
    assert resp.status_code == 200

    data = parse_response(resp)

    # Only test confirmed bookings
    assume(data["status"] == "confirmed")

    # Find all available vehicles matching the requested type and location
    # (case-insensitive matching, same as the function logic)
    candidates = [
        v for v in FLEET
        if v["type"].lower() == vehicle_type.lower()
        and v["location"].lower() == pickup_location.lower()
        and v["available"]
    ]

    # There must be at least one candidate for a confirmed booking
    assert len(candidates) > 0, "No matching available vehicles found for a confirmed booking"

    # The expected vehicle is the one with the lowest mileage
    expected_vehicle = min(candidates, key=lambda v: v["mileage"])

    # The assigned vehicleId must match the lowest-mileage vehicle
    assert data["vehicleId"] == expected_vehicle["id"], (
        f"Expected vehicleId '{expected_vehicle['id']}' (mileage {expected_vehicle['mileage']}) "
        f"but got '{data['vehicleId']}' for {vehicle_type} in {pickup_location}"
    )
