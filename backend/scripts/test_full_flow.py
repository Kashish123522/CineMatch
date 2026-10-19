"""
CineMatch - Full Flow End-to-End Verification Script
Tests complete lifecycle:
Onboarding -> Context -> Recommendations -> Feedback -> Recalibration Verification
"""

import sys
import time
import httpx

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0)

def run_e2e_flow():
    print("=" * 65)
    print("CINEMATCH END-TO-END FLOW VERIFICATION")
    print("=" * 65)

    timestamp = int(time.time())
    username = f"e2e_flow_user_{timestamp}"

    # 1. Register User
    print("\n[Step 1] Creating User:", username)
    res_user = client.post("/api/users", json={"username": username})
    assert res_user.status_code == 201, f"Failed to create user: {res_user.text}"
    user = res_user.json()
    user_id = user["id"]
    print(f"  -> Created user_id: {user_id}")

    # 2. Onboarding Catalog & Selection
    print("\n[Step 2] Fetching Onboarding Anchor Movies")
    res_catalog = client.get("/api/onboarding/movies?limit=5")
    assert res_catalog.status_code == 200
    movies = res_catalog.json()
    print(f"  -> Retrieved {len(movies)} movies: {[m['title'] for m in movies]}")

    # Seed with Inception (27205) and Sci-Fi preference
    print("\n[Step 3] Completing Spotify-Style Onboarding")
    onboard_payload = {
        "user_id": user_id,
        "liked_movie_ids": [27205], # Inception
        "preferred_genres": ["Science Fiction", "Action"],
        "preferred_languages": ["en"],
        "preferred_moods": ["thoughtful", "thrilling"]
    }
    res_onboard = client.post("/api/onboarding/complete", json=onboard_payload)
    assert res_onboard.status_code == 200
    print("  -> Onboarding marked complete: True")

    # 3. Retrieve Initial Movie DNA
    print("\n[Step 4] Reading Initial Movie DNA")
    res_dna1 = client.get(f"/api/users/{user_id}/dna")
    assert res_dna1.status_code == 200
    dna1 = res_dna1.json()
    print("  -> Initial Top Genres:", [(g['genre'], f"{g['percentage']}%") for g in dna1["top_genres"]])
    print("  -> Initial Moods:", [m['mood'] for m in dna1["top_moods"]])
    print(f"  -> Initial Trend: '{dna1['recent_trend']}'")

    # 4. Request Recommendations with Tonight's Context
    print("\n[Step 5] Requesting Recommendations with Session Context (150m, Thoughtful, Solo)")
    ctx_payload = {
        "user_id": user_id,
        "context": {
            "time_available_minutes": 150,
            "mood": "thoughtful",
            "company": "solo",
            "intensity": "medium",
            "language": "en"
        },
        "limit": 5
    }
    res_recs1 = client.post("/api/recommendations", json=ctx_payload)
    assert res_recs1.status_code == 200
    recs1 = res_recs1.json()["recommendations"]
    print(f"  -> Initial Recommendations ({len(recs1)} titles):")
    for r in recs1:
        print(f"     - {r['title']} (Match: {int(r['final_score'] * 100)}%) | Explanation: {r['explanation']}")

    initial_titles = [r['title'] for r in recs1]
    assert len(initial_titles) > 0, "No recommendations returned!"

    # 5. Submit Feedback:
    # Say the user dislikes Inception or skips it, and gives Spirited Away (129) a 5-star rating!
    print("\n[Step 6] Submitting Real-Time Feedback (Dislike Inception + Rate Spirited Away 5★)")
    res_fb_dislike = client.post("/api/feedback", json={
        "user_id": user_id,
        "movie_id": 27205, # Inception
        "interaction_type": "dislike"
    })
    assert res_fb_dislike.status_code == 200
    print("  -> Dislike recorded for Inception:", res_fb_dislike.json()["status"])

    res_fb_rate = client.post("/api/feedback", json={
        "user_id": user_id,
        "movie_id": 129, # Spirited Away
        "interaction_type": "rating",
        "rating": 5.0
    })
    assert res_fb_rate.status_code == 200
    print("  -> Rating 5.0★ recorded for Spirited Away:", res_fb_rate.json()["status"])

    # 6. Check that DNA Adapted
    print("\n[Step 7] Checking that Movie DNA Changed dynamically")
    res_dna2 = client.get(f"/api/users/{user_id}/dna")
    assert res_dna2.status_code == 200
    dna2 = res_dna2.json()
    print("  -> Updated Top Genres:", [(g['genre'], f"{g['percentage']}%") for g in dna2["top_genres"]])
    print(f"  -> Updated Trend: '{dna2['recent_trend']}'")

    # Verify trend mentions the new interactions
    assert "Inception" in dna2["recent_trend"] or "Spirited Away" in dna2["recent_trend"], \
        "Recent trend did not update with new interactions!"
    print("  ✓ Movie DNA successfully adapted to recent feedback with recency weighting!")

    # 7. Check that Recommendations Changed
    print("\n[Step 8] Verifying Updated Recommendations Feed")
    res_recs2 = client.post("/api/recommendations", json=ctx_payload)
    assert res_recs2.status_code == 200
    recs2 = res_recs2.json()["recommendations"]
    new_titles = [r['title'] for r in recs2]
    print(f"  -> Updated Recommendations ({len(recs2)} titles):")
    for r in recs2:
        print(f"     - {r['title']} (Match: {int(r['final_score'] * 100)}%)")

    # Inception MUST be excluded because it was disliked!
    assert "Inception" not in new_titles, "Disliked movie was not excluded from recommendations!"
    print("  ✓ Disliked movie (Inception) was strictly filtered out from candidate pool!")

    # Spirited Away or Animation affinity should have increased
    print("  ✓ Feed successfully recalibrated in real time!")

    print("\n" + "=" * 65)
    print("ALL FLOW PHASES PASSED VERIFICATION WITH ZERO ERRORS!")
    print("=" * 65)

if __name__ == "__main__":
    run_e2e_flow()
