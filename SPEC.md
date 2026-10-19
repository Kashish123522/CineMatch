# CineMatch — Project Specification

## Core Value Proposition
**CineMatch** answers the core question: **"What should THIS user watch RIGHT NOW?"**

Unlike static catalog browsers or naive recommendation lists, CineMatch couples a long-term user taste profile ("Movie DNA") with real-time situational session context, dynamic recency-weighted feedback, and diversity-conscious ranking.

---

## 1. High-Level Architecture & Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database & ORM**: SQLAlchemy with SQLite (async/sync support)
- **Data & ML**: pandas, NumPy, scikit-learn, SciPy
- **Configuration**: `backend/config.yaml`
- **Data Source**: TMDB 5000 Movies & TMDB 5000 Credits (`backend/data/tmdb_5000_movies.csv` and `tmdb_5000_credits.csv`).
  - Self-contained sample data is provided out-of-the-box so the app runs immediately without external downloads.
- **External APIs**: TMDB API key is **optional** (`TMDB_API_KEY`). When absent or invalid, the app gracefully falls back to dynamic gradient placeholders.

### Frontend
- **Framework**: React + Vite
- **Styling**: Tailwind CSS
- **Animations & Transitions**: Framer Motion
- **Interactions**: Spotify-style onboarding, quick session context picker, interactive swiping/card feedback, reason chips.

---

## 2. Recommendation Flow & Engine Logic

The CineMatch recommendation loop consists of 5 core phases:

### (1) Spotify-Style Onboarding ("Movie DNA")
- **Initial Profile Construction**: Users undergo a visual onboarding flow to seed their "Movie DNA" preference vector.
- **Signals Collected**:
  - Liked seed movies (selected from popular/diverse anchors).
  - Favorite & disliked genres.
  - Preferred languages.
  - Desired base moods/tones (e.g., Uplifting, Cerebral, Thrilling, Chill, Melancholic).
- **Representation**: A multi-dimensional feature vector combining genre distribution, TF-IDF/embeddings of keywords & overviews, director/actor preferences, and mood mappings.

### (2) Continuous Feedback Loop with Exponential Recency Decay
- **Interactions Captured**:
  - `like` (+1.0)
  - `dislike` (-1.0)
  - `rating` (1–5 / 1–10 stars scaled relative to baseline)
  - `watched` (+0.6)
  - `skip` (-0.4)
- **Recency Decay**:
  - Profile preferences dynamically adjust on every interaction.
  - Decayed weight formula: \( w(t) = w_0 \cdot \left(\frac{1}{2}\right)^{\frac{\Delta t}{t_{1/2}}} \)
  - Configurable half-life \( t_{1/2} \) (defined in `config.yaml`, default: 14 days).
  - Recent likes and skips have immediate impact without permanently wiping out foundational taste.

### (3) Session Context Collection
Before serving recommendations for a watching session, CineMatch captures immediate circumstantial filters & preferences:
- **Time Available**: Remaining minutes (e.g., 90 min, 120 min, no limit) matching movie runtime.
- **Current Mood**: Energetic, Cozy, Thought-Provoking, Dark, Escapist, Fun.
- **Company**: Solo, Date Night, Family with Kids, Friends.
- **Complexity / Intensity**: Light & Breezy, Medium Drama, Intense / Mind-bending.
- **Language**: Specific languages or any.

### (4) Multi-Objective Scoring & Diversity Re-ranking
Every candidate movie is scored using a normalized weighted sum (all weights configured in `backend/config.yaml`, normalized \( 0.0 - 1.0 \), sum = 1.0):

$$\text{FinalScore}(m) = w_1 \cdot S_{\text{profile}}(m) + w_2 \cdot S_{\text{recent}}(m) + w_3 \cdot S_{\text{context}}(m) + w_4 \cdot S_{\text{collab}}(m) + w_5 \cdot S_{\text{quality}}(m)$$

- **Profile Similarity (\(S_{\text{profile}}\))**: Cosine similarity between candidate movie features and user's base Movie DNA vector.
- **Recent Behaviour (\(S_{\text{recent}}\))**: Similarity with high-weight recently interacted items, penalizing patterns seen in recent skips/dislikes.
- **Context Match (\(S_{\text{context}}\))**: Strict and soft penalty/bonus matching runtime constraints, target mood, company suitability, and intensity.
- **Collaborative Score (\(S_{\text{collab}}\))**: Simplified user-user or item-item collaborative filtering. **Only applied when sufficient interaction data exists** (controlled by `min_system_interactions` in `config.yaml`). If threshold is not met, the engine smoothly defaults to content & context weights.
- **Quality Prior (\(S_{\text{quality}}\))**: Bayesian smoothed TMDB rating (vote average weighted by vote count) preventing obscure low-sample outliers.
- **Diversity via MMR**:
  - Top candidate pool is re-ranked using **Maximal Marginal Relevance (MMR)**:
    $$\text{MMR} = \operatorname{argmax}_{d_i \in R \setminus S} \left[ \lambda \cdot \text{Score}(d_i) - (1 - \lambda) \max_{d_j \in S} \operatorname{Sim}(d_i, d_j) \right]$$
  - Prevents recommending 10 identical movies in a row.

### (5) Explainability & Reason Chips
- Every recommendation displays human-readable, plain-language explanations.
- **Reason Chips**:
  - *"Fits your 90 min window"*
  - *"Because you loved Inception"*
  - *"Matches your 'Cerebral' mood"*
  - *"High Sci-Fi + Mystery synergy"*
  - *"Great for Date Night"*
- **Truth in Metrics**: Never fabricate accuracy numbers or fake confidence percentages. Explanations reflect actual feature attribution.

---

## 3. Directory Layout

```
CineMatch_Project/
├── SPEC.md                      # This specification file
├── backend/
│   ├── config.yaml              # Central configuration (weights, decay, thresholds)
│   ├── requirements.txt         # Python dependencies
│   ├── app/                     # FastAPI endpoints, routers, DB models, schemas
│   ├── ml/                      # DNA vector builder, context matcher, MMR, CF
│   ├── data/                    # TMDB CSV datasets (movies & credits)
│   ├── scripts/                 # Ingestion, vector pre-computation, seed tools
│   └── tests/                   # Pytest test cases (engine, context, API)
└── frontend/                    # Vite + React + Tailwind + Framer Motion app
```

---

## 4. Current Setup Status
- [x] Base directory tree created (`backend/app`, `backend/ml`, `backend/data`, `backend/scripts`, `backend/tests`, `frontend`).
- [x] Python dependencies defined in `backend/requirements.txt`.
- [x] Central configuration created in `backend/config.yaml`.
- [x] Sample datasets created in `backend/data/` for zero-setup execution.
- [x] System specification saved in `SPEC.md`.
