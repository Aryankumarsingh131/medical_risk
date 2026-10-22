# Hyperframes Composition Brief: Medical Risk XAI

## Objective
Create a short, premium launch-style brag video for Medical Risk XAI.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 18.0 seconds

## Source Material
- Project root: `C:\Users\Aryan Kumar Singh\OneDrive\Desktop\medical_risk`
- Primary files read: `frontend/src/LandingPage.jsx`, `frontend/src/LandingPage.css`, `frontend/src/DoctorDashboard.jsx`
- Product name: Medical Risk XAI
- Tagline / strongest claim: "Predict Risk with Transparent, Explainable AI"
- Key UI or visual moment to recreate: Real-time cardiovascular risk scoring dashboard with live SHAP feature attribution bars and multi-tenant isolation indicators.
- Copy that must appear verbatim:
  - "Predict Risk with Transparent, Explainable AI"
  - "XGBoost & SHAP Pipeline Active"
  - "15+ Curated Datasets · 21 Clinical Features"
  - "100% Explainable Outputs"

## Creative Direction
- Tone preset: polished
- Creative direction: sleek clinical healthcare intelligence film
- Interpretation: Precise typographic motion, crisp dark UI glassmorphism, luminescent teal and lime accents, steady rhythmic pacing.
- Angle: Medical Risk XAI transforms cardiovascular risk prediction by replacing black-box models with clinically validated, fully explainable AI that keeps hospital data completely isolated.
- Hook: "Predict Risk with Transparent, Explainable AI" over deep navy glow.
- Outro / punchline: "Medical Risk XAI — Transparent. Auditable. Clinically Validated."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unreadable micro-text

## Visual Identity
- Background: `#060D17` / `#0B111A`
- Primary Accent: `#1AAB9B` (Medical Teal)
- Secondary Accent: `#C6F135` (High-Voltage Lime)
- Text: `#FFFFFF` (Primary), `#94A3B8` (Secondary), `#3FB950` (Success Green)
- Display font: `Inter, system-ui, sans-serif`
- Body font: `Inter, system-ui, sans-serif`
- Visual references from the project: Medical cross emblem, glowing pills, glass cards with gradient borders, SHAP attribution meters.

## Storyboard
Scene summary:
1. **The Hook & Vision** — 4.0s (0.0s – 4.0s) — Glowing badge + "Predict Risk with Transparent, Explainable AI"
2. **Live Risk Engine & SHAP Attribution** — 5.0s (4.0s – 9.0s) — Interactive patient risk score (78% High Risk) with 3 SHAP bars sliding in
3. **Benchmarked Multi-Tenant Scale** — 5.0s (9.0s – 14.0s) — 4 staggered stat tiles showing 15+ datasets, 21 clinical features, 3 models, 100% explainability
4. **Final Outro & Call to Action** — 4.0s (14.0s – 18.0s) — Medical cross logo slam, "Medical Risk XAI", and launch badge

## Audio
- Audio role: steady, modern electronic bed with crisp clinical interface accents
- Audio arc: Ambient intro builds into snappy interactive UI clicks and beat-synced stat tiles, closing with a resonant bell.
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: volume 0.32, smooth intro, ducking slightly during dense UI sound moments, fading under the final logo.
- Music cue guidance: Strong cues at 8.74s, 13.11s, 17.47s; beat-grid snapping for sequential metrics (5.34s, 6.00s, 6.56s, 9.83s, 10.93s, 12.02s).
- Audio-reactive treatment: Subtle card border glow and background radial illumination responding to audio energy.
- Audio-coupled moments:
  - Scene 1 at 0.3s — Soft UI drop on badge
  - Scene 2 at 5.34s, 6.00s, 6.56s — SHAP bar slide-ins
  - Scene 2 at 8.74s — Major risk score reveal sound
  - Scene 3 at 9.83s, 10.93s, 12.02s, 13.11s — Metric tile clicks
  - Scene 4 at 17.47s — Logo impact bell
- SFX selection guidance: Use `interface/drop_001.ogg`, `interface/select_008.ogg`, `interface/click_001.ogg`, `impact/impactSoft_medium_001.ogg`, and `impact/impactBell_heavy_000.ogg`.
- Audio files: All copied into `brag-output/composition/assets/`

## Hyperframes Instructions
- Composition root: `1920x1080`
- Duration: `18.0`s
- Use GSAP timelines paused and registered under `window.__timelines["root"]`
- Run `npx hyperframes check` to validate before rendering.
