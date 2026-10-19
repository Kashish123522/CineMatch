"""
CineMatch - Live API Smoke Test
Verifies all 8 REST endpoints against running server.
"""

import sys
import httpx

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0)

print("\n--- 1. POST /api/users ---")
r = client.post("/api/users", json={"username": f"smoke_user_{int(sys.platform == 'win32')}"})
if r.status_code == 400:  # If exists, use user 1
    uid = 1
    print("User already exists, using user_id 1")
else:
    assert r.status_code == 201
    uid = r.json()["id"]
    print(f"Created user: id={uid}, username={r.json()['username']}")

print("\n--- 2. GET /api/onboarding/movies ---")
r = client.get("/api/onboarding/movies?limit=3")
assert r.status_code == 200
movies = r.json()
print(f"Retrieved {len(movies)} onboarding movies: {[m['title'] for m in movies]}")

print("\n--- 3. POST /api/onboarding/complete ---")
r = client.post(
    "/api/onboarding/complete",
    json={
        "user_id": uid,
        "liked_movie_ids": [27205],
        "preferred_genres": ["Science Fiction", "Action"],
        "preferred_languages": ["en"],
        "preferred_moods": ["thoughtful"],
    },
)
assert r.status_code == 200
print(f"Onboarding complete: status={r.status_code}, onboarding_completed={r.json()['onboarding_completed']}")

print("\n--- 4. GET /api/users/{id}/dna ---")
r = client.get(f"/api/users/{uid}/dna")
assert r.status_code == 200
dna = r.json()
print(f"Movie DNA: Top genres: {dna['top_genres'][:2]}, Trend: '{dna['recent_trend']}'")

print("\n--- 5. POST /api/recommendations ---")
r = client.post(
    "/api/recommendations",
    json={
        "user_id": uid,
        "context": {
            "time_available_minutes": 150,
            "mood": "thoughtful",
            "company": "solo",
            "intensity": "intense",
            "language": "en",
        },
        "limit": 3,
    },
)
assert r.status_code == 200
recs = r.json()["recommendations"]
print(f"Recommendations returned: {len(recs)}")
for idx, item in enumerate(recs, 1):
    print(f"  [{idx}] {item['title']} (Score: {item['final_score']})")
    print(f"      Explanation: {item['explanation']}")
    print(f"      Chips: {item['reason_chips']}")

print("\n--- 6. POST /api/feedback ---")
r = client.post(
    "/api/feedback",
    json={
        "user_id": uid,
        "movie_id": 157336,
        "interaction_type": "like",
    },
)
assert r.status_code == 200
print(f"Feedback submitted: {r.json()['message']}")

print("\n--- 7. GET /api/movies/{id} ---")
r = client.get("/api/movies/27205")
assert r.status_code == 200
print(f"Movie details: {r.json()['title']} | Dir: {r.json()['director']} | Runtime: {r.json()['runtime']}m")

print("\n--- 8. GET /api/users/{id}/history ---")
r = client.get(f"/api/users/{uid}/history")
assert r.status_code == 200
history = r.json()
print(f"History records: {len(history)} -> {[h['movie_title'] + ':' + h['interaction_type'] for h in history]}")

print("\n========================================================")
print("SUCCESS: ALL 8 ENDPOINTS VERIFIED AGAINST LIVE SERVER!")
print("========================================================")
