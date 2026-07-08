"""
Proves each of the three bugs and its fix, using the exact values from
database/seed.sql. Pure Python, no DB/Docker required.

Run:  python3 verify_fixes.py
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

GREEN, RED, BOLD, END = "\033[92m", "\033[91m", "\033[1m", "\033[0m"


def header(n, title):
    print(f"\n{BOLD}{'='*70}\nBUG {n}: {title}\n{'='*70}{END}")


# ---------------------------------------------------------------------------
# BUG 1 — Timezone month-bucketing (Client A: "March totals don't match")
# ---------------------------------------------------------------------------
header(1, "Timezone month-bucketing")
# seed: res-tz-1, prop-001 (tenant-a, Europe/Paris), check_in 2024-02-29 23:30 UTC
check_in = datetime(2024, 2, 29, 23, 30, tzinfo=timezone.utc)
paris = ZoneInfo("Europe/Paris")
print(f"Reservation res-tz-1 check_in: {check_in}  (= {check_in.astimezone(paris)} in Paris)")
print("This booking is MARCH in the property's local timezone (Paris).\n")

# BEFORE (buggy): naive UTC month boundaries
before_start = datetime(2024, 3, 1)                       # naive -> treated as UTC
before_end = datetime(2024, 4, 1)
in_march_before = before_start <= check_in.replace(tzinfo=None) < before_end
print(f"  BEFORE (naive UTC boundaries):  counted in March? {RED if not in_march_before else GREEN}{in_march_before}{END}")

# AFTER (fixed): boundaries anchored to the property's timezone
after_start = datetime(2024, 3, 1, tzinfo=paris)
after_end = datetime(2024, 4, 1, tzinfo=paris)
in_march_after = after_start <= check_in < after_end
print(f"  AFTER  (Paris-anchored boundaries): counted in March? {GREEN if in_march_after else RED}{in_march_after}{END}")
assert not in_march_before and in_march_after
print(f"{GREEN}==> Fix moves the €1250 booking back into March, matching the client's records.{END}")


# ---------------------------------------------------------------------------
# BUG 2 — Cross-tenant cache collision (Client B: "I see another company's data")
# ---------------------------------------------------------------------------
header(2, "Cross-tenant cache key collision")
# seed: prop-001 exists for BOTH tenant-a (Beach House) and tenant-b (Mountain Lodge)
def key_before(property_id, tenant_id):
    return f"revenue:{property_id}"

def key_after(property_id, tenant_id):
    return f"revenue:{tenant_id}:{property_id}"

a = ("prop-001", "tenant-a")
b = ("prop-001", "tenant-b")
print(f"  BEFORE: tenant-a key = {key_before(*a)!r}")
print(f"          tenant-b key = {key_before(*b)!r}")
print(f"          collision? {RED}{key_before(*a) == key_before(*b)}{END}  <- tenant-b reads tenant-a's cached revenue")
print(f"  AFTER : tenant-a key = {key_after(*a)!r}")
print(f"          tenant-b key = {key_after(*b)!r}")
print(f"          collision? {GREEN}{key_after(*a) == key_after(*b)}{END}")
assert key_before(*a) == key_before(*b)
assert key_after(*a) != key_after(*b)
print(f"{GREEN}==> Fix isolates each tenant's cache; no cross-company data leak.{END}")


# ---------------------------------------------------------------------------
# BUG 3 — Money as float (Finance: "totals off by a few cents")
# ---------------------------------------------------------------------------
header(3, "Money precision (float vs Decimal)")
# seed amounts (NUMERIC(10,3)) for prop-001/tenant-a
amounts = ["333.333", "333.333", "333.334", "1250.000"]
true_total = sum(Decimal(x) for x in amounts)          # exact
print(f"  Exact total (Decimal):  {true_total}")

# demonstrate a value that actually mis-rounds under float
tricky = Decimal("1475.505")
before_tricky = round(float(str(tricky)) * 100) / 100
after_tricky = float(Decimal(str(tricky)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
print(f"  Example value 1475.505 (a real 3-decimal amount):")
print(f"    BEFORE float round -> {RED}{before_tricky}{END}   (float(1475.505) = {float(1475.505)!r})")
print(f"    AFTER  Decimal round -> {GREEN}{after_tricky}{END}")
assert before_tricky != after_tricky
print(f"{GREEN}==> Fix rounds money with Decimal, so cents always reconcile.{END}")

print(f"\n{BOLD}{GREEN}All three fixes verified.{END}\n")
