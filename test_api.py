import requests, json

# Test root
r = requests.get("http://127.0.0.1:8000/")
print("=== ROOT ===")
print(json.dumps(r.json(), indent=2))

# Test crops list
r = requests.get("http://127.0.0.1:8000/api/v1/crops")
data = r.json()
print(f"\n=== CROPS: {data['total']} total ===")
for c in data["crops"][:5]:
    print(f"  {c['name']}: {c['category']} | MSP: {c.get('msp', 'N/A')}")

# Test mandis list
r = requests.get("http://127.0.0.1:8000/api/v1/mandis")
data = r.json()
print(f"\n=== MANDIS: {data['total']} total ===")
for m in list(data["mandis"])[:5]:
    print(f"  {m['name']}: {m['state']} ({m['region']})")

# Test geography states
r = requests.get("http://127.0.0.1:8000/api/v1/geography/states")
data = r.json()
print(f"\n=== STATES: {data['total']} ===")
for s in data["states"][:5]:
    print(f"  {s['state']}: {s['mandi_count']} mandis")

# Test nearby mandis
r = requests.post("http://127.0.0.1:8000/api/v1/mandis/nearby",
    json={"lat": 22.7196, "lon": 75.8577, "radius_km": 150})
data = r.json()
print(f"\n=== NEARBY MANDIS (150km from Indore): {data['total_found']} ===")
for m in data["mandis"][:5]:
    print(f"  {m['mandi']}: {m['distance_km']}km | Transport: Rs.{m['transport_cost']}")

# Test transport estimate
r = requests.get("http://127.0.0.1:8000/api/v1/transport/estimate",
    params={"from_lat": 22.7196, "from_lon": 75.8577, "to_mandi": "Nashik", "quantity_qtl": 100})
data = r.json()
print(f"\n=== TRANSPORT: Indore -> {data['to_mandi']} ===")
print(f"  Distance: {data['distance_km']}km | Cost: Rs.{data['total_cost']} | Per Qtl: Rs.{data['cost_per_qtl']}")

# Test API key registration
r = requests.post("http://127.0.0.1:8000/api/v1/auth/register?company_name=TestCorp&plan=starter")
print(f"\n=== API KEY ===")
print(json.dumps(r.json(), indent=2))
