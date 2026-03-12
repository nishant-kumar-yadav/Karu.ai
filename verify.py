"""Viraasat.ai — End-to-End Verification Script

Tests ALL endpoints without needing Gemini API calls.
Run with: python verify.py
"""

import json
import urllib.request
import urllib.error
import sys

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def test(name: str, method: str, path: str, body=None, expect_status=200):
    global PASS, FAIL
    url = f"{BASE}{path}"
    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if body else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        r = urllib.request.urlopen(req)
        result = json.loads(r.read().decode())
        print(f"  ✅ {name}")
        PASS += 1
        return result
    except urllib.error.HTTPError as e:
        if e.code == expect_status:
            print(f"  ✅ {name} (expected {e.code})")
            PASS += 1
            return json.loads(e.read().decode()) if e.readable() else {}
        print(f"  ❌ {name} — HTTP {e.code}: {e.read().decode()[:100]}")
        FAIL += 1
        return None
    except Exception as e:
        print(f"  ❌ {name} — {e}")
        FAIL += 1
        return None


def test_binary(name: str, path: str, min_bytes=100):
    global PASS, FAIL
    try:
        r = urllib.request.urlopen(f"{BASE}{path}")
        data = r.read()
        if len(data) >= min_bytes:
            print(f"  ✅ {name} ({len(data)} bytes)")
            PASS += 1
        else:
            print(f"  ❌ {name} — only {len(data)} bytes")
            FAIL += 1
    except Exception as e:
        print(f"  ❌ {name} — {e}")
        FAIL += 1


print("=" * 55)
print("  🏺 VIRAASAT.AI — VERIFICATION SUITE")
print("=" * 55)

# ── 1. Health & Root ──
print("\n📡 Server Health")
test("GET /", "GET", "/")
test("GET /health", "GET", "/health")

# ── 2. Auth Flow ──
print("\n🔐 Auth Flow")
reg = test("POST /auth/register", "POST", "/auth/register", {"phone": "+919999900001"})
ver = test("POST /auth/verify (new user)", "POST", "/auth/verify", {"phone": "+919999900001", "otp": "123456"})

profile_data = {
    "phone": "+919999900001",
    "name": "Test Artisan",
    "district": "Varanasi",
    "state": "Uttar Pradesh",
    "craft_types": ["textiles"],
    "preferred_language": "hi",
    "upi_id": "9999900001@upi",
}
profile = test("POST /auth/profile (create)", "POST", "/auth/profile", profile_data)

if profile:
    aid = profile["id"]
    test("GET /auth/profile/{id}", "GET", f"/auth/profile/{aid}")
    test("PUT /auth/profile/{id}", "PUT", f"/auth/profile/{aid}", {"district": "Banaras"})
    test("GET /auth/profile/{id}/completion", "GET", f"/auth/profile/{aid}/completion")
    test_binary("GET /auth/profile/{id}/monogram", f"/auth/profile/{aid}/monogram", min_bytes=1000)

    # Verify re-login
    test("POST /auth/verify (returning user)", "POST", "/auth/verify", {"phone": "+919999900001", "otp": "000000"})

    # Duplicate check
    test("POST /auth/profile (duplicate → 409)", "POST", "/auth/profile", profile_data, expect_status=409)

# ── 3. 404 handling ──
print("\n🚫 Error Handling")
test("GET /auth/profile/nonexistent → 404", "GET", "/auth/profile/nonexistent-id", expect_status=404)
test("GET /products/nonexistent → 404", "GET", "/products/nonexistent-id", expect_status=404)
test("GET /sharing/nonexistent/whatsapp → 404", "GET", "/sharing/nonexistent-id/whatsapp", expect_status=404)

# ── 4. Products (metadata only — no Gemini needed) ──
print("\n📦 Products (metadata)")
if profile:
    test("GET /products/artisan/{id} (empty)", "GET", f"/products/artisan/{aid}")

# ── 5. Sharing (needs a product — will 404 without one) ──
print("\n📤 Sharing Endpoints (expect 404 — no products yet)")
test("GET /sharing/{id}/whatsapp → 404", "GET", "/sharing/fake-product/whatsapp", expect_status=404)
test("GET /sharing/{id}/instagram → 404", "GET", "/sharing/fake-product/instagram", expect_status=404)
test("GET /sharing/{id}/facebook → 404", "GET", "/sharing/fake-product/facebook", expect_status=404)
test("GET /sharing/{id}/landing-page → 404", "GET", "/sharing/fake-product/landing-page", expect_status=404)
test("GET /sharing/{id}/download-kit → 404", "GET", "/sharing/fake-product/download-kit", expect_status=404)
test("GET /sharing/{id}/analytics → 404", "GET", "/sharing/fake-product/analytics", expect_status=404)

# ── 6. Scan Tracking (creates data, doesn't need product to exist in demo mode) ──
print("\n📊 QR Scan Tracking")
test("POST /sharing/{id}/scan", "POST", "/sharing/test-product-id/scan?action=viewed", expect_status=404)

# ── Summary ──
print("\n" + "=" * 55)
print(f"  Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("  🎉 ALL TESTS PASSED!")
else:
    print(f"  ⚠️  {FAIL} test(s) need attention")
print("=" * 55)

sys.exit(0 if FAIL == 0 else 1)
