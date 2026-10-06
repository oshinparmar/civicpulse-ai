# 🏙️ CivicPulse AI
> **AI-Powered Public Infrastructure Monitoring & Prioritization Engine**  
> *Developed for Indore Municipal Corporation (IMC) / Smart Cities Mission*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini%202.5%20Flash-4285F4)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Problem Statement
Public infrastructure issues like potholes, collapsed road shoulders, broken streetlights, and overflowing drains are typically reported late, get buried under bureaucratic backlogs, or go completely unnoticed until a fatal accident occurs. 

Municipalities lack an automated, intelligent system to:
1. **Instantly verify** citizen defect reports using computer vision.
2. **Weed out spam or irrelevant photos** (selfies, pets, indoor photos).
3. **Quantify civic safety risk** with an explainable, data-driven priority score.
4. **Group duplicate complaints within 50 meters** so authorities understand true public urgency.
5. **Track issues dynamically** across an interactive map and dispatch field crews.

---

## 🚀 Key Features

### 1. 📸 Citizen Report Portal
- **Camera & Image Upload**: Citizens can snap a live photo or upload an existing image.
- **EXIF GPS Auto-Extraction**: Automatically extracts decimal latitude & longitude from the photo metadata (falls back to landmark picker or manual coordinates).
- **Instant AI Vision Diagnostic**: Powered by **Google Gemini 2.5 Flash** to extract structured JSON:
  - Defect Type (`pothole`, `damaged road`, `broken streetlight`, `overflowing drain`, `other`)
  - Severity Level (1 to 5)
  - AI Confidence percentage
  - Safety Hazard Description (e.g. fatal two-wheeler skid hazard at night)
  - Automatic spam/irrelevant image rejection.

### 2. 🧠 Smart Multi-Factor Prioritization Engine (0-100 Score)
$$ \text{Priority Score} = S_{\text{severity}} + W_{\text{risk}} + C_{\text{cluster}} + A_{\text{age}} $$
- **Base Severity ($S_{\text{severity}}$)**: 10 to 45 pts from AI severity assessment.
- **Inherent Risk ($W_{\text{risk}}$)**: 12 to 25 pts based on hazard class (e.g., open drains & deep craters score highest).
- **Spatial Clustering ($C_{\text{cluster}}$)**: Uses the **Haversine Distance formula** to detect duplicate reports of the same issue within **50 meters**. Each nearby complaint adds urgency (+7 pts per duplicate, max 20 pts).
- **Aging Escalation ($A_{\text{age}}$)**: Older unresolved reports automatically escalate (+1.5 pts/day, max 15 pts) so neglected repairs don't languish.
- Categorization into **High** ($\ge 70$, Red), **Medium** ($45-69$, Orange), and **Low** ($< 45$, Green).

### 3. 🏛️ Municipal Authority Command Center
- **Executive KPIs**: Real-time counters for Total Issues, Pending Action, Critical (High) Issues, In Progress, and Resolved.
- **Interactive Triage Queue**: Sort and filter by status, defect category, priority, and locality.
- **Inspector & Workflow Control**: View full defect details, citizen notes, and update workflow status: `Reported` $\rightarrow$ `Assigned` $\rightarrow$ `In Progress` $\rightarrow$ `Resolved`.
- Assign specific civic departments (e.g., Road Works Division, Drainage & Sewerage) and field engineers.

### 4. 🗺️ Live Geospatial GIS Map
- Powered by **Folium** with high-resolution CartoDB tiles.
- Color-coded pins (Red=High, Orange=Medium, Green=Low, Slate=Resolved).
- **50-Meter Spatial Cluster Rings**: Visual dotted circles highlighting duplicate complaint hotspots.
- **Defect HeatMap Density Layer**: Toggleable heatmap displaying infrastructure defect density across the city.
- Custom interactive popups with defect thumbnails, timestamps, and safety risks.

### 5. 📊 Analytics & Operational Insights
- Visual breakdown of issues by defect category (donut chart).
- Priority distribution across city sectors.
- Top infrastructure hotspot localities.
- Resolution lifecycle funnel.
- **One-Click CSV Export**: Download the entire municipal log for reporting.

### 6. 🚔 Automated Dashcam / CCTV Patrol Simulator (Bonus)
- Simulates an automated municipal inspection car driving down the AB Road corridor.
- Periodically captures video frames, analyzes them with AI, tags GPS, and injects them directly into the dispatch queue.

### 7. 🌱 18 Pre-Seeded Realistic Demo Issues
- Realistic reports centered around **Indore, India** (India's cleanest city), covering famous landmarks like Vijay Nagar, Rajwada Palace, 56 Dukan, Super Corridor, Palasia, and Bhawarkua.
- Includes a live 3-point duplicate cluster at Vijay Nagar Square demonstrating the 50m spatial grouping!

---

## 📂 Project Structure

```text
civicpulse-ai/
├── app.py                     # Streamlit frontend & application orchestration
├── ai_engine.py               # Google Gemini 2.5 Flash Vision & Fallback Demo Mode
├── prioritization.py          # 0-100 Multi-factor priority scoring & Haversine clustering
├── database.py                # SQLite persistence, queries, and 18 Indore seed records
├── map_component.py           # Folium interactive map, markers, and heatmap layer
├── utils.py                   # EXIF GPS parser, distance formula, base64 image encoder
├── run_app.bat                # 1-click Windows runner
├── requirements.txt           # Project dependencies
├── .gitignore                 # Excludes secrets, database, virtual environment
├── sample_images/             # 5 realistic test images for live demos
│   ├── 01_deep_pothole.jpg
│   ├── 02_overflowing_drain.jpg
│   ├── 03_broken_streetlight.jpg
│   ├── 04_damaged_road.jpg
│   └── 05_unrelated_cat_selfie.jpg
└── .streamlit/
    ├── config.toml            # Theme and UI styling
    └── secrets.toml.example   # Template for Gemini API Key
```

---

## 🔑 How to Get a Free Google Gemini API Key

1. Go to **[Google AI Studio](https://aistudio.google.com/)**.
2. Sign in with any Google account.
3. Click the blue **"Get API key"** button on the top left.
4. Click **"Create API key"** $\rightarrow$ select any existing project (or click "Create key in new project").
5. Copy your API key (it begins with `AIzaSy...`).
6. *That's it! Gemini 2.5 Flash has a generous free tier for development.*

> 💡 **Demo Resilience**: If you don't provide an API key right away, **CivicPulse AI automatically activates Demo Simulation Mode**! It will analyze the test images with realistic mock heuristics so your hackathon demo will **NEVER crash** on stage.

---

## 💻 How to Run Locally

### Windows
1. **Clone or open this folder** in your terminal or VS Code:
   ```powershell
   cd civicpulse-ai
   ```
2. **Double-click `run_app.bat`**, OR run:
   ```powershell
   # If running manually:
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Open your browser to **`http://localhost:8501`**.

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Adding your API Key Locally
Create a `.env` file in the project root:
```env
GEMINI_API_KEY="AIzaSyYourActualKeyHere"
```
Or paste it directly into the password field in the sidebar!

---

## ☁️ Step-by-Step Deployment to Streamlit Community Cloud (via GitHub)

Deploying takes under 3 minutes:

### Step 1: Create a GitHub Repository
1. Go to [github.com](https://github.com/) and click **New Repository**.
2. Name it `civicpulse-ai` and set it to **Public**.
3. Push or upload your project files:
   - Make sure `app.py`, `ai_engine.py`, `prioritization.py`, `database.py`, `map_component.py`, `utils.py`, `requirements.txt`, and the `sample_images/` folder are uploaded.
   - Do **NOT** commit any `.env` or `secrets.toml` file with your secret key.

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
2. Click **"New app"**.
3. Select your repository: `<your-username>/civicpulse-ai`.
4. Branch: `main`.
5. Main file path: `app.py`.

### Step 3: Add your Gemini API Key in Secrets
1. Before or after clicking Deploy, expand **"Advanced settings"** (or click **Settings** $\rightarrow$ **Secrets** on your deployed app).
2. In the **Secrets** text box, paste:
   ```toml
   GEMINI_API_KEY = "AIzaSyYourActualKeyHere"
   ```
3. Click **Save** and **Deploy**.
4. Within 60 seconds, your app will be live on a public URL you can share with judges!

---

## 🎤 2-Minute Hackathon Pitch & Demo Script

**[0:00 - 0:25] The Problem Hook**
> *"Judges, imagine hitting a 1-foot-deep pothole at 60 km/h or driving through a street where all lights have been dark for two weeks. Today, municipal corporations like Indore or Delhi receive thousands of unstructured phone calls and tweets. Critical hazards get buried, duplicate complaints flood phone lines, and by the time repairs happen, accidents have already occurred. We built **CivicPulse AI** to automate public infrastructure monitoring from defect capture to dispatch."*

**[0:25 - 0:55] Live Citizen Demo**
> *"Let's report an issue live. I snap or upload a photo of a severe pothole [select `01_deep_pothole.jpg`]. Notice that CivicPulse AI extracts the exact GPS coordinates automatically. When I hit **Run AI Vision Analysis**, Google Gemini 2.5 Flash inspects the image in milliseconds: it detects a Level-4 Pothole, explains the safety hazard to two-wheelers, and computes an explainable 0-100 Priority Score. Even better: notice the red alert banner—our spatial clustering algorithm noticed two other active pothole reports within 50 meters, automatically grouping them and escalating the urgency!"*

**[0:55 - 1:25] Authority Command Center & Geospatial Map**
> *"Now let's switch hats to the Municipal Commissioner's dashboard. In the **Authority Command Center**, officers see a triaged priority queue sorted by our mathematical risk score. In the **Live Geospatial Map**, you see color-coded pins across Indore. Dotted circles highlight 50m duplicate clusters, and we can toggle the Defect HeatMap to spot infrastructure decay corridors. An officer can click any issue, assign it to the Road Works Division, and update the status from Reported to In Progress to Resolved in one click."*

**[1:25 - 1:45] Dashcam Patrol Simulator (Bonus)**
> *"Finally, we don't just rely on citizens. Under the **Dashcam Simulator** tab, municipal survey vehicles or city buses scan corridors automatically. With one click, our virtual patrol scans AB Road, detects 3 defects in real time, and logs them into the system before citizens even have to complain."*

**[1:45 - 2:00] Conclusion**
> *"CivicPulse AI turns passive municipal maintenance into proactive, AI-driven urban safety. Simple Python stack, powered by Gemini Vision, ready to scale to any smart city. Thank you!"*

---

## 🧠 5 Likely Judge Questions & Winning Answers

### Q1: *"How does your system prevent fake or spam reports, like someone uploading a picture of a cat or an indoor room?"*
**Answer**:
> *"We implemented a multi-stage validation prompt inside Google Gemini 2.5 Flash. The model is specifically instructed to classify whether the image depicts public municipal infrastructure (`is_valid_infrastructure_issue`). If someone uploads a selfie, a pet, or an indoor room, the AI returns `issue_type: none` and flags a rejection reason. The application immediately blocks the submission, keeping municipal queues clean."*

### Q2: *"Why not just prioritize issues based on severity alone? Why do you need a multi-factor score?"*
**Answer**:
> *"Severity alone only tells part of the story. A small pothole in an alley is far less dangerous than an open drain near a school or a pothole on a high-speed arterial road. Our formula combines: (1) AI severity [1-5], (2) Inherent hazard weight by defect type, (3) Spatial clustering within 50 meters (which measures how many different citizens are complaining about the exact same hazard), and (4) Aging escalation (preventing older complaints from being perpetually ignored). This gives municipalities a fair, actionable 0-100 ranking."*

### Q3: *"How does the 50-meter duplicate clustering work, and how does it scale?"*
**Answer**:
> *"We use the Haversine trigonometric formula to calculate precise great-circle distance between GPS coordinates. When a report is submitted, we query active reports of the same defect category within a 50-meter bounding radius. When duplicates match, they are linked into a single spatial cluster and their cluster count increments reciprocally. In production, this can be indexed using SQLite SpatiaLite or PostgreSQL PostGIS `ST_DWithin` spatial indexes for sub-millisecond queries across millions of city coordinates."*

### Q4: *"What if the citizen uploads an image without EXIF GPS metadata?"*
**Answer**:
> *"Many social media apps strip EXIF tags. We built a graceful fallback: if EXIF GPS is present, it auto-fills; if absent, the citizen can pick from prominent city landmarks (like Vijay Nagar, Rajwada, or Palasia in Indore) or adjust the coordinates and address directly. In a production mobile app, the native GPS API from the device's geolocation sensor (`navigator.geolocation`) supplies real-time coordinates upon capture."*

### Q5: *"Can this be deployed and scaled to a full smart city without excessive cloud costs?"*
**Answer**:
> *"Yes! We purposely used Gemini 2.5 Flash, which is optimized for high-throughput, low-latency multimodal inference at a fraction of the cost of heavier models. Furthermore, by running client-side duplicate detection and caching, we only invoke vision inference once per photo. Municipal authorities can run the dashboard on lightweight cloud instances while storing incident records in standard relational databases."*
