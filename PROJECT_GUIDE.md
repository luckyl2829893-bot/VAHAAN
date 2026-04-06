# 🛡️ Aequitas RoadGuard (ARG) — Complete Project Guide

> **An AI-Powered Traffic Enforcement System Built for India**
> 
> Computer Vision • NLP • MLOps • Deep Learning • Database Engineering

---

## Table of Contents
1. [What is ARG?](#what-is-arg)
2. [Why This Project Exists](#why-this-project-exists)
3. [How It Works — The Big Picture](#how-it-works)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [The AI Pipeline — Explained Simply](#the-ai-pipeline)
7. [The Database — How Everything Connects](#the-database)
8. [Scripts — What Each File Does](#scripts)
9. [How to Run Everything](#how-to-run)
10. [Results & Performance](#results)
11. [Future Roadmap](#future-roadmap)

---

## 1. What is ARG? <a name="what-is-arg"></a>

**Aequitas RoadGuard (ARG)** is an end-to-end AI system that simulates what a modern, automated traffic enforcement platform would look like for India. It uses:

- **Computer Vision** to detect vehicles and read license plates from images and dashcam video
- **A Proxy Database** that simulates real Indian government systems (Aadhaar, VAHAN, FASTag)
- **A Wealth Multiplier** that calculates fines proportional to vehicle value — making penalties fair
- **An NLP Module** that auto-generates legal challan documents from AI detections
- **Violation Detection** for missing plates, dark window tint, and no helmet on motorcycles
- **Video Processing** with real-time vehicle tracking, speed estimation, and court evidence storage

### What Makes This Different?
Most traffic enforcement projects just detect license plates. ARG goes further — it creates a **complete enforcement ecosystem** where detection connects to identity, identity connects to wealth, and wealth determines the fine. A ₹500 fine means nothing to someone driving a ₹50 Lakh SUV, but everything to someone on a ₹50,000 scooter. ARG fixes this.

---

## 2. Why This Project Exists <a name="why-this-project-exists"></a>

India loses **~1.5 lakh lives annually** to road accidents (WHO, 2023). The root causes:
- Manual enforcement is inconsistent and corruptible
- Fines are flat-rate (₹500 for a billionaire = pocket change)
- No automated system connects vehicle detection → owner identity → penalty calculation
- No evidence storage for court proceedings

**ARG proposes a fully automated solution:** Camera detects violation → AI reads plate → System looks up owner → Wealth-adjusted fine is calculated → Legal challan is auto-generated → Evidence is stored for court.

---

## 3. How It Works — The Big Picture <a name="how-it-works"></a>

```
┌──────────────────────────────────────────────────────────────┐
│                    INPUT (Image or Video)                      │
│              Dashcam, CCTV, Mobile Phone Camera                │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  STAGE 1: Vehicle Finder (yolo11m.pt — COCO Pre-trained)     │
│  Detects: Cars, Motorcycles, Buses, Trucks, Bicycles         │
│  Output: Cropped image of each vehicle                        │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  STAGE 2: Plate Sniper (best.pt — Custom Trained, 98.8% mAP) │
│  Searches ONLY inside the cropped vehicle for a license plate │
│  Output: Tightly cropped plate image                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  STAGE 3: OCR Engine (EasyOCR)                                │
│  Reads the text from the cropped plate only                   │
│  Validates against Indian plate regex: [A-Z]{2}[0-9]{1,2}... │
│  Output: Clean plate string (e.g., "MH12AB1234")             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  DATABASE LOOKUP (SQLite — arg_master_database.sqlite)        │
│  → citizens (Aadhaar)                                         │
│  → vahan_registry (Vehicle details, insurance, loan)          │
│  → fastag_accounts (Wallet, bank, tag status)                 │
│  → fastag_transactions (Toll history)                         │
│  → challans (Fines with Wealth Multiplier)                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT                                                        │
│  → Owner Profile (Name, Aadhaar, PAN, CIBIL)                 │
│  → Vehicle Details (Make, Model, Value, Insurance, Loan)      │
│  → Wealth-Adjusted Fine (Base Fine × Vehicle Value Ratio)     │
│  → Legal Challan (NLP-generated formal document)              │
│  → Court Evidence Package (Timestamped frames + metadata)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Stack <a name="technology-stack"></a>

| Category | Technology | Purpose |
|----------|------------|---------|
| **Object Detection** | YOLO11m (Ultralytics) | Vehicle detection + plate detection |
| **OCR** | EasyOCR | License plate text extraction |
| **Database** | SQLite3 | Storing all identity/vehicle/financial records |
| **Image Processing** | OpenCV (cv2) | Video processing, ROI masking, annotations |
| **Deep Learning** | PyTorch + CUDA 12.1 | GPU-accelerated model training and inference |
| **NLP** | Custom Template Engine | Auto-generating legal challan narratives |
| **Data Science** | NumPy | Speed estimation, brightness analysis |
| **GPU** | NVIDIA RTX 4060 (8GB) | Training and real-time inference |
| **Language** | Python 3.10 | Everything |

---

## 5. Project Structure <a name="project-structure"></a>

```
c:\Users\laksh\Desktop\image\
│
├── 🧠 AI MODELS
│   ├── yolo11m.pt                          # Stage 1: Pre-trained vehicle detector (COCO)
│   └── runs/detect/plate_model_train_final/
│       └── weights/best.pt                 # Stage 2: Custom Plate Sniper (98.8% mAP)
│
├── 🐍 CORE SCRIPTS
│   ├── generate_proxy_database.py          # Builds the proxy database from raw images
│   ├── live_detect.py                      # Real-time detection + auto-proxy generation
│   ├── violation_detector.py               # 3 violation detectors (plate/tint/helmet)
│   ├── arg_video_engine.py                 # Advanced: ROI + tracking + speed + NLP
│   ├── export_db.py                        # Export database tables to CSV
│   └── play_video.py                       # OpenCV video player for results
│
├── 🗄️ DATABASE & EXPORTS
│   ├── arg_master_database.sqlite          # The main database (5 tables, 525+ records)
│   ├── ARG_Proxy_Dataset_Master.csv        # Combined export
│   ├── export_citizens.csv                 # Aadhaar records
│   ├── export_vahan_registry.csv           # Vehicle registration records
│   ├── export_fastag_accounts.csv          # FASTag wallet records
│   ├── export_fastag_transactions.csv      # Toll transaction history
│   └── export_challans.csv                 # Traffic violation fines
│
├── 📸 RAW IMAGE DATASETS (for inference)
│   ├── cars/                               # ~800+ car images
│   ├── 2 wheeler/                          # Motorcycle/scooter images
│   ├── 3 wheeler/                          # Auto-rickshaw images
│   ├── heavy vehicle/                      # Trucks/buses images
│   ├── ambulance/                          # Emergency vehicle images
│   └── test/                               # Mixed test images
│
├── 📹 VIDEO DATASETS
│   └── Videos/                             # 104 dashcam videos (.MOV)
│
├── 📊 TRAINING DATASETS (for model training)
│   ├── plate_dataset/                      # Roboflow annotated plate dataset
│   └── vehicle_dataset/                    # Roboflow annotated vehicle dataset
│
├── 📁 OUTPUT DIRECTORIES
│   ├── violation_results/                  # Annotated violation images
│   ├── arg_engine_output/                  # Advanced engine annotated videos + challans
│   └── evidence_vault/                     # Court evidence packages (frame + crop + JSON)
│
├── 📝 DOCUMENTATION
│   ├── PROJECT_GUIDE.md                    # This file — complete project guide
│   ├── ARG_Master_Blueprint.md             # High-level system architecture vision
│   ├── ARG_Developer_Log.md               # Technical development journal (all phases)
│   └── project_history_report.md           # Summary of past errors and fixes
│
└── ⚙️ ENVIRONMENT
    ├── ARGvenv/                            # Python virtual environment
    └── requirements.txt                    # Python dependencies
```

---

## 6. The AI Pipeline — Explained Simply <a name="the-ai-pipeline"></a>

### Stage 1: Vehicle Finder
- **Model:** `yolo11m.pt` (Medium architecture, pre-trained on COCO dataset)
- **What it does:** Looks at an entire image and draws boxes around every vehicle it sees
- **Classes it detects:** Bicycle (1), Car (2), Motorcycle (3), Bus (5), Truck (7)
- **Why we don't train this:** The COCO pre-trained model already detects vehicles with 90%+ accuracy. Training our own would require 100,000+ images for the same result.

### Stage 2: Plate Sniper
- **Model:** `best.pt` (Custom YOLO11m trained for 100 epochs)
- **What it does:** Takes the cropped vehicle image from Stage 1 and searches ONLY inside it for a license plate
- **Training data:** 3,000+ professionally annotated Indian license plate images from Roboflow
- **Performance:** Precision 97.9% | Recall 97.9% | mAP50 98.8%
- **Why this matters:** By searching only inside a confirmed vehicle crop, we eliminate false positives from watermarks, shop signs, and painted truck text that plagued our original approach.

### Stage 3: OCR (Optical Character Recognition)
- **Engine:** EasyOCR with English language model
- **What it does:** Reads the actual text characters from the cropped plate image
- **Validation:** Only accepts strings matching Indian plate format `[STATE][DIST][SERIES][NUMBER]` (e.g., MH12AB1234)
- **Why EasyOCR:** Free, open-source, GPU-accelerated, and handles the varied fonts on Indian plates well.

### Why Two Stages?
Our first attempt used a single-stage approach (detect plates directly from full images). This failed catastrophically because:
1. OCR read watermarks as plates
2. OCR read text painted on trucks ("CARRIER", phone numbers) as plates
3. Plates on the top of motorcycles were ignored (we only checked bottom 60%)

The Two-Stage approach eliminates all these problems by isolating the search area.

---

## 7. The Database — How Everything Connects <a name="the-database"></a>

The database simulates 5 real Indian government/financial systems:

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    CITIZENS      │     │  VAHAN REGISTRY   │     │ FASTAG ACCOUNTS  │
│  (Aadhaar/UIDAI) │◄────│  (Vehicle RTO)    │────►│  (NPCI/NETC)     │
│                  │     │                   │     │                  │
│ • aadhar_masked  │     │ • plate_number PK │     │ • fastag_id PK   │
│ • virtual_id     │     │ • vehicle_class   │     │ • plate_number FK│
│ • full_name      │     │ • make, model     │     │ • wallet_balance │
│ • gender, dob    │     │ • color, fuel     │     │ • issuer_bank    │
│ • city, state    │     │ • chassis, engine │     │ • tag_status     │
│ • phone_masked   │     │ • invoice_price   │     │ • vehicle_class  │
│ • pan_number     │     │ • insurance       │     │ • low_balance    │
│ • cibil_score    │     │ • loan/hypothec.  │     └────────┬─────────┘
│ • kyc_status     │     │ • owner_aadhar FK │              │
└─────────────────┘     │ • owner_name      │              │
                         └────────┬──────────┘              │
                                  │                         │
                         ┌────────▼──────────┐     ┌────────▼─────────┐
                         │    CHALLANS        │     │ FASTAG           │
                         │  (Traffic Fines)   │     │ TRANSACTIONS     │
                         │                    │     │  (Toll History)  │
                         │ • plate_number FK  │     │                  │
                         │ • violation_type   │     │ • fastag_id FK   │
                         │ • base_fine        │     │ • toll_plaza     │
                         │ • wealth_multiplier│     │ • timestamp      │
                         │ • final_fine       │     │ • amount_deducted│
                         │ • status           │     └──────────────────┘
                         └────────────────────┘
```

### The Wealth Multiplier Formula
```
Multiplier = Vehicle Invoice Price ÷ ₹5,00,000
Clamped between 1.0x and 10.0x

Examples:
  Scooter (₹80,000)     → 1.0x  → ₹5,000 fine stays ₹5,000
  Hatchback (₹6,00,000) → 1.2x  → ₹5,000 fine becomes ₹6,000
  Luxury SUV (₹25,00,000)→ 5.0x  → ₹5,000 fine becomes ₹25,000
  Supercar (₹1,00,00,000)→ 10.0x → ₹5,000 fine becomes ₹50,000
```

---

## 8. Scripts — What Each File Does <a name="scripts"></a>

### `generate_proxy_database.py` — The Brain Builder
Runs the Two-Stage pipeline on all raw images and builds the proxy database.
```
Input:  1,899 raw images from cars/, 2 wheeler/, etc.
Output: arg_master_database.sqlite with 525 unique identities
```

### `live_detect.py` — Real-Time Scanner
Point at any image or folder. Detects plates and shows full owner profiles.
```
New plate detected? → Auto-generates proxy identity → Inserts into DB
Known plate? → Pulls existing profile and displays it
```

### `violation_detector.py` — Violation Hunter
Scans images/video for 3 types of traffic violations:
```
🔴 Missing Plate  — Vehicle found but no plate detected
🟣 Dark Tint      — Window brightness below legal threshold
🟠 No Helmet      — Motorcycle rider without helmet
```

### `arg_video_engine.py` — The Flagship Engine
The most advanced script combining everything:
```
🟢 ROI Masking      — Ignores distant vehicles, focuses on detection zone
🔵 YOLO Tracking    — Persistent vehicle IDs across frames
⚡ Speed Estimation  — Calculates km/h from pixel displacement
📦 Evidence Storage  — Saves court-ready evidence packages
📜 Legal Narratives  — Auto-generates formal challan documents (NLP)
```

### `export_db.py` — Data Exporter
Converts all 5 database tables into individual CSV files for analysis.

### `play_video.py` — Video Player
OpenCV-based video player to view annotated output videos.

---

## 9. How to Run Everything <a name="how-to-run"></a>

### Setup (First Time)
```bash
# Navigate to project
cd c:\Users\laksh\Desktop\image

# Activate virtual environment
.\ARGvenv\Scripts\activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

### Run the Database Generator
```bash
# Builds proxy database from all raw images
python generate_proxy_database.py
```

### Run Live Detection
```bash
# Single image
python live_detect.py test\photo.jpg

# Entire folder
python live_detect.py test\

# Your custom images
python live_detect.py path\to\your\images\
```

### Run Violation Detection
```bash
# On images
python violation_detector.py test\photo.jpg
python violation_detector.py test\

# On video
python violation_detector.py Videos\video84.MOV
```

### Run Advanced Video Engine
```bash
# Full pipeline on dashcam video
python arg_video_engine.py Videos\video84.MOV

# On a single image
python arg_video_engine.py test\photo.jpg
```

### View Output Video
```bash
# Edit play_video.py to change the video path, then:
python play_video.py
```

### Export Database to CSV
```bash
python export_db.py
```

---

## 10. Results & Performance <a name="results"></a>

### Plate Sniper Model (Custom Trained)
| Metric | Score |
|--------|-------|
| Precision | 97.9% |
| Recall | 97.9% |
| mAP50 | 98.8% |
| mAP50-95 | 80.1% |
| Training Epochs | 100 |
| Training Time | ~2.5 hours (RTX 4060) |

### Database Statistics
| Table | Records |
|-------|---------|
| Citizens (Aadhaar) | 525 |
| VAHAN Registry | 525 |
| FASTag Accounts | 525 |
| FASTag Transactions | 5,200+ |
| Challans | 525+ |

### Violation Detection (test folder)
| Metric | Count |
|--------|-------|
| Vehicles Scanned | 52 |
| No Plate Violations | 26 |
| No Helmet | 4 |
| Dark Tint | 2 |

### Video Engine (video84.MOV — 25 seconds)
| Metric | Count |
|--------|-------|
| Frames Processed | 750 |
| Vehicles Tracked | 555 |
| Violations Detected | 531 |
| Evidence Packages | 531 |
| Legal Challans | 18 |

---

## 11. Future Roadmap <a name="future-roadmap"></a>

### Phase 8: Dataset Training (Pending)
- [ ] Train helmet detection model (Roboflow dataset)
- [ ] Train pothole/road damage detector (YOLO segmentation)
- [ ] Rain/night image enhancement using user's weather dataset

### Phase 9: Super-Resolution
- [ ] Integrate Real-ESRGAN for blurry plate enhancement before OCR
- [ ] CLAHE preprocessing for low-light/night footage

### Phase 10: Dashboard & API
- [ ] Streamlit admin dashboard (live stats, violation map, revenue tracker)
- [ ] FastAPI backend (mobile app endpoints)

### Phase 11: MLOps & Deployment
- [ ] Docker containerization
- [ ] DVC for data/model versioning
- [ ] MLflow for experiment tracking
- [ ] AWS deployment (EC2/Lambda + RDS)

### Phase 12: Mobile App
- [ ] React Native / Flutter app
- [ ] Camera capture → API call → Profile display
- [ ] Citizen portal for reporting violations

### Vision Features (Research Phase)
- [ ] Crash/accident detection from video
- [ ] Fine-grained vehicle classification (hatchback vs sedan vs SUV)
- [ ] GPS tagging for location-based enforcement
- [ ] Pothole detection + municipal accountability chain

---

## Key Takeaways

This project demonstrates proficiency in:

| Skill | Where It's Used |
|-------|----------------|
| **Computer Vision** | YOLO detection, OpenCV processing, ROI masking |
| **Deep Learning** | Custom model training (100 epochs, RTX 4060/CUDA) |
| **NLP** | Legal narrative auto-generation from structured data |
| **Database Design** | 5-table relational schema with foreign keys |
| **Data Engineering** | ETL pipeline: images → AI → database → CSV exports |
| **Software Architecture** | Two-Stage pipeline, modular script design |
| **MLOps (Planned)** | Docker, DVC, MLflow, AWS deployment |
| **Problem Solving** | Three critical bugs found and fixed in Phase 1 |

---

*Built with ❤️ for Indian roads. — Aequitas RoadGuard*
