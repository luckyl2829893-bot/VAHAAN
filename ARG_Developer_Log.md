# ARG Developer Log
*A living record of the Aequitas RoadGuard (ARG) system's development journey, technical decisions, and troubleshooting.*

---

## [Phase 1] Initial Build & The OCR Constraint

**The Goal:**
Create a system that can scan images of vehicles, extract their license plates, cross-reference the mock VAHAN database for the "Wealth Multiplier" (e.g. inflating fines for expensive SUVs), and generate simulated proxy databases.

**What We Did:**
We built a single-stage YOLO prediction script (`build_yolo_dataset.py`) to pseudo-annotate images from various downloaded datasets (`cars`, `2 wheeler`, etc.). The script relied heavily on `easyocr` to find text chunks in the bottom 60% of vehicles and assumed any string of numbers/letters was a license plate.

**The Problems We Faced:**
We trained a YOLO11m model (`train4`), but when predicting on test images, the bounding boxes were chaotic.

### Error 1: The "Folder Name" Fallacy (Making Bad Vehicle Boxes)
*   **What we did:** We separated images into folders (`3 wheeler`, `cars`, etc.), and then aggressively told the script that *any* vehicle found in that folder strictly belonged to that class. 
*   **The Error:** If an image in the `3 wheeler` folder contained a yellow dump truck in the background, our script blindly hard-coded that truck's bounding box as "class 1" (3-wheeler). The YOLO model was actively being taught that massive yellow trucks are 3-wheelers.

### Error 2: Single-Object Blindness (Overlapping & Missing Boxes)
*   **What we did:** The script searched the image for a vehicle using COCO, drew a box around the first vehicle it found, and then fired off a Python `break` statement to stop looking for more.
*   **The Error:** Whenever an image had multiple cars or people on bikes, only the first object was labeled. The model incorrectly learned that all other unlabelled bikes/cars in the image were "background noise".

### Error 3: The Watermark Disaster (Bad Plate Identification)
*   **What we did:** We used `easyocr` to find license plates blindly: *"Look at the bottom 60% of the vehicle. If you see text with numbers and letters, it is definitely a license plate!"*
*   **The Error:** 
    1. It read text painted on trucks (e.g. "CARRIER" or phone numbers) and labeled them as ground-truth plates. 
    2. When evaluating images of bikes with corner watermarks, it read the watermark and made it a license plate.
    3. It explicitly **ignored the top 40%** of motorcycles, meaning any license plate mounted near handlebars was erased from the training data.

---

## [Phase 2] The Great Reset & The Two-Stage Pipeline

**Why We Did It:**
"Raw OCR text detection" is an inherently flawed way to train an object detection model. We scrapped the single OCR-script architecture for a specialized **Two-Stage Detection System**.

**What We Did:**
1.  **Deep Cleaning:** Deleted the entire poisoned `yolo_dataset`, wiped all old YOLO `run` caches, and all flawed Python scripts.
2.  **Dataset Upgrade:** Swapped to professionally pre-annotated Roboflow datasets (`Indian number plate.v3i.yolov11` and `car-motorcycle-bus-truck.v1i.yolov11`).
3.  **Plate Sniper Training:** Initiated a 100-epoch training session for a specialized YOLO model trained exclusively to detect the physical contour of an Indian license plate.

**Difficulties:**
*   YOLO `data.yaml` files from Roboflow used broken relative paths. **Fix:** Manually rewrote all paths to absolute paths.
*   Initial training showed 0 GPU utilization. **Fix:** Confirmed CUDA was available, restarted in the virtual environment with proper PyTorch+CUDA installation.
*   Training metrics plateaued around mAP50 = 0.70-0.75 for epochs 13-37. **Fix:** This was expected — the model was still learning. After epoch 60+, it broke through and converged to 0.988 by epoch 100.

---

## [Phase 3] Rewriting the Core Simulation

**The Goal:**
Rebuild `generate_proxy_database.py` to use the Two-Stage pipeline instead of the old single-stage OCR approach.

**How We Did It:**
*   **Step 1 (Vehicle Finder):** Used the base `yolo11m.pt` (COCO pre-trained) to detect vehicles and crop them.
*   **Step 2 (Plate Sniper):** Passed cropped vehicle images to the custom `best.pt` model to locate the physical plate bounding box.
*   **Step 3 (OCR Extraction):** Only the tightly-cropped plate region is sent to EasyOCR — massively reducing false positives from watermarks and painted truck text.

---

## [Phase 4] Full Proxy Database Generation (COMPLETED)

**The Goal:**
Execute the Two-Stage pipeline across all 1,899 raw images and build a comprehensive proxy database simulating real Indian government APIs.

**What We Built:**
1.  **Plate Sniper Training:** 100 epochs on RTX 4060. Final: **Precision 97.9%, Recall 97.9%, mAP50 98.8%, mAP50-95 80.1%**
2.  **5 Interconnected Database Tables:**
    *   `citizens` — Aadhaar (masked UID, Virtual ID, PAN, CIBIL, KYC status)
    *   `vahan_registry` — Vehicle specs (make, model, color, fuel, chassis, engine, RTO, insurance, hypothecation/loan)
    *   `fastag_accounts` — Financial wallet (balance, issuer bank, tag status, vehicle class code)
    *   `fastag_transactions` — Movement tracking (toll plaza name, timestamp, amount deducted)
    *   `challans` — Traffic fines with the Wealth Multiplier (base fine × vehicle value ratio)
3.  **RTO Coverage:** Expanded from 15 states to **all 28 states + 8 Union Territories** (36 total).

**The Result:** 525 unique vehicle identities extracted and populated.

**Difficulties:**
*   Detection rate was 525/1899 (~27.6%). **Reason:** The pipeline is intentionally strict — requires valid Indian plate regex match. Many images had plates too blurry, angled, or small for OCR. This is a precision-over-recall design choice.
*   Vehicle make/model is randomly simulated since YOLO only detects broad classes (car/bike/truck), not specific models.

---

## [Phase 5] Real-Time Detection & Live Detect (COMPLETED)

**The Goal:**
Build a real-time script that scans any new image, detects plates, and auto-generates proxy identities for unknown vehicles on the fly.

**What We Built:**
*   `live_detect.py` — Point it at any image or folder. If a plate exists in the DB → pulls existing profile. If it's new → auto-generates Aadhaar, VAHAN, FASTag records and inserts them permanently.
*   Displays a formatted profile with owner name, vehicle specs, CIBIL score, FASTag balance, and a Wealth Multiplier preview.

**Key Design Decision:**
The `generate_proxy_database.py` generators are imported as a module, keeping all data generation logic DRY (Don't Repeat Yourself).

---

## [Phase 6] Violation Detection Module (COMPLETED)

**The Goal:**
Detect traffic violations from images and video using the Two-Stage pipeline.

**What We Built:**
*   `violation_detector.py` with 3 violation detectors:
    1.  **Missing Plate Detector** — If Stage 1 finds a vehicle but Stage 2 finds 0 plates → violation. No training needed.
    2.  **Dark Window Tint Detector** — Analyzes the window-region brightness of cars/buses. Below 45 avg brightness = SEVERE, below 70 = MODERATE. No training needed.
    3.  **No Helmet Detector** — For motorcycles, uses edge-density heuristic as fallback. When a trained helmet model is available, automatically switches to it.
*   Supports images, folders, and **video files** (frame-by-frame processing).
*   Auto-generates challans in the database for detected violations.
*   Saves color-coded annotated images to `violation_results/`.

**Difficulties:**
*   `.MOV` files from the user's dashcam weren't detected as video because the extension check was case-sensitive (`.mov` vs `.MOV`). **Fix:** Changed to `source.lower().endswith(...)`.
*   Far-away vehicles were being flagged as "NO PLATE" even though their plates were simply too distant to read. **Fix:** This led directly to the ROI masking feature in Phase 7.
*   Dashcam video at 30 FPS produced choppy 2 FPS output. **Root cause:** Processing every 15th frame then writing at 2 FPS. This is addressed in Phase 7 with smoother processing.

**Test Results (on `test/` folder):** 52 vehicles scanned, 30 violations detected (26 no plate, 4 no helmet, 2 dark tint).

---

## [Phase 7] Advanced Video Engine (COMPLETED)

**The Goal:**
Build a production-grade video processing engine with intelligent detection zones, vehicle tracking, speed estimation, evidence storage, and automated legal narrative generation.

**What We Built:**
*   `arg_video_engine.py` — The flagship script integrating 5 advanced features:

### Feature 1: ROI Masking (Region of Interest)
*   Defines a trapezoid-shaped detection zone covering the center-bottom 60% of the frame.
*   Vehicles outside this zone (sky, distant objects) are drawn in grey and skipped.
*   **Why:** Eliminates false "NO PLATE" violations on vehicles too far to read.

### Feature 2: YOLO Tracking (model.track())
*   Uses Ultralytics' built-in tracking instead of per-frame prediction.
*   Each vehicle gets a persistent **Track ID** that follows it across frames.
*   **Why:** Enables speed calculation and prevents duplicate violation counting.

### Feature 3: Speed Estimation
*   Tracks pixel displacement of each vehicle ID across frames.
*   Converts pixel movement to km/h using approximate pixels-per-meter calibration.
*   Flags vehicles exceeding 50 km/h as **SPEEDING** violations.
*   **Limitation:** Speed is approximate since pixel-to-meter conversion depends on camera angle and distance.

### Feature 4: Court Evidence Storage
*   Every violation is saved as a **court-ready evidence package** in `evidence_vault/`:
    *   `full_frame.jpg` — The entire frame at the moment of violation
    *   `vehicle_crop.jpg` — Zoomed crop of the offending vehicle
    *   `metadata.json` — Timestamp, plate number, violation type, speed, track ID
*   **Why:** Creates an indisputable, timestamped record admissible as digital evidence.

### Feature 5: Legal Narrative Generator (NLP Component)
*   Auto-generates structured legal challan text from detection data.
*   Pulls owner details from the database (name, Aadhaar, vehicle specs, insurance, loan status).
*   Calculates the Wealth Multiplier and produces a formal legal notice.
*   **Example output:** *"On 31-03-2026 at 02:45 IST, vehicle bearing registration MH12AB1234, a White Mahindra XUV700 (4-Wheeler Luxury SUV), valued at ₹15,00,000, was recorded committing SPEEDING at 72 km/h..."*
*   **Why:** This is the NLP component — structured data → natural language legal document.

**HUD Overlay:**
*   Every output frame has a professional heads-up display showing "ARG ENFORCEMENT AI", frame counter, total vehicles tracked, and total violations detected.

---

## Known Limitations & Honest Assessment

1.  **Vehicle Make/Model:** Randomly simulated. The AI detects "car" or "truck" but cannot distinguish specific models. Would require a fine-grained classification dataset.
2.  **Speed Estimation:** Approximate. Accuracy depends on camera angle and calibration.
3.  **Helmet Detection:** Currently uses edge-density heuristic. Trained model slot is ready — just needs a Roboflow helmet dataset.
4.  **No Crash Detection:** Insufficient public Indian crash footage datasets.
5.  **No GPS Tagging:** Dashcam videos have timestamps but no embedded GPS coordinates.

## Hardware & Environment
*   **GPU:** NVIDIA RTX 4060 Laptop (8GB VRAM)
*   **CUDA:** 12.1
*   **Python:** 3.10.11 (virtual environment: `ARGvenv`)
*   **YOLO:** Ultralytics 8.3.0 (YOLO11m architecture)
*   **OS:** Windows

*(Log to be continued as Phase 8 begins...)*

---

## [Phase 8] Dataset Consolidation & The Scraper Challenge (COMPLETED)

**The Goal:**
Consolidate pricing and feature data from multiple car brands into a single master dataset (`cars_details_data.csv`) and acquire interactive 360-degree exterior rotations for every vehicle.

**What We Built:**
1.  **Brand Merger Script:** Consolidated fragmented CSVs from Audi, BMW, Tata, Toyota, Mahindra, and Maruti into a unified schema.
2.  **Price Magnitude Repairer:** A targeted script (`final_cleanup.py`) to fix broad-scale scaling errors in the "On-Road" price columns.
3.  **Standardized Specification Engine:** Converted verbose, pipe-separated Maruti data (e.g., *"Petrol/CNG | 25.75 kmpl | Manual/..."*) into the concise "Mercedes-Benz style" (`Petrol/CNG25.75 kmpl`).
4.  **Advanced 360 Scraper:** A Selenium-driven engine (`scrape_360.py`) that bypasses CarDekho's interactive viewer protections.

**The Problems We Faced:**

### Error 1: The "Lakh" Truncation (The Missing Zeros Issue)
*   **What we did:** Used `re.sub(r'[^\d]', '', price_str)` to clean currency strings like "₹ 5.79 Lakh".
*   **The Error:** The regex removed the decimal point and the unit "Lakh" was lost before multiplication. "5.79" became "579". Since it wasn't scaled, a 6-Lakh car appeared to cost ₹579.
*   **The Fix:** 
    1. Updated `clean_price` in the scraper to detect 'Lakh' context *before* regex cleaning.
    2. Ran a magnitude-based repair script: 
       *   `val < 100` -> `* 100,000` (e.g., 4 becomes 4,00,000)
       *   `100 <= val < 10,000` -> `* 1,000` (e.g., 579 becomes 5,79,000)

### Error 2: The 360 Viewer "Wall"
*   **What we did:** Initially tried to scrape the standard image gallery.
*   **The Problem:** The 360-degree exterior rotation is hidden behind a specialized JavaScript viewer (Object2VR) that only loads images *after* specific user interaction. Standard scraping returned 0 images.
*   **The Fix:** 
    1. **Multi-Step Interaction:** Programmed Selenium to: Scroll to Viewer -> Click "Tap to Interact 360º" -> Clear popup modals -> Click "CLICK TO INTERACT".
    2. **Network Sniffing:** Instead of scraping the DOM, the script monitors the `performance` logs to spot a single `img_0_0_X.jpg` frame.
    3. **Sequence Interpolation:** Once one frame URL is found, the script programmatically downloads all 36 frames (`img_0_0_0.jpg` to `img_0_0_35.jpg`) directly from the CDN, bypassing the browser entirely for speed.

### Error 3: Mixed Spec Schema
*   **What we did:** Merged Maruti data which uses pipe separation (`|`) with high-end brands that use concatenated strings.
*   **The Problem:** The master CSV looked structurally broken and messy.
*   **The Fix:** Developed `standardize_specs.py` to extract only the core Fuel + Mileage (or Electric Range) and join them into a clean, unified format across all 252 cars.

**The Result:** A perfectly clean, high-precision vehicle catalog with 360-degree visual assets for AI-driven enforcement and appraisal.

---

## [Phase 9] Zero-Shot Auto-Annotation & AI Prompt Engineering

**The Goal:**
Automate the annotation process for thousands of newly scraped car frames (including the 360-degree datasets and motovlogger frames) without manually drawing bounding boxes. The goal is to aggressively train the model on specific vehicle sub-components.

**What We Built:**
1.  **Autodistill Implementation:** Replaced the generic image parser with a robust `GroundedSAM` (GroundingDINO + Segment Anything) pipeline.
2.  **Dataset Consolidation:** Automatically moved fragmented OEM folders (Audi, BMW, Honda, etc.) into a unified `cars/` master directory, and updated the script to recursively crawl through image trees.
3.  **Visualization:** Added the `supervision` library to automatically generate preview thumbnails of what the AI is "seeing".

**The Problems We Faced:**

### Error 1: The HuggingFace Transformers Conflict
*   **What happened:** Upon executing the annotator, it crashed with `AttributeError: 'BertModel' object has no attribute 'get_head_mask'`.
*   **The Cause:** `GroundedSAM` (specifically the GroundingDINO backend) relies on an older version of the HuggingFace `transformers` package. The latest `transformers` update removed the `get_head_mask()` function, breaking the entire dependency tree.
*   **The Fix:** Forcibly downgraded the environment using `pip install "transformers<4.40"`.

### Error 2: Corrupted SAM Weights (PytorchStreamReader Error)
*   **What happened:** `RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory`.
*   **The Cause:** GroundedSAM requires a massive 2.4 GB `.pth` file (`sam_vit_h_4b8939.pth`). A previous crash or network drop interrupted the download, creating a corrupted/"hollow" ZIP archive in the Windows hidden cache `C:\Users\laksh\.cache\autodistill\`.
*   **The Fix:** Traced the corrupted file deep in the `.cache` folder and manually deleted it, forcing the PyTorch engine to download a clean, fresh copy of the weights.

### Error 3: "Prompt Bleed" in Zero-Shot Models
*   **What happened:** When telling the AI to find a "car logo", "front grill", or "headlight", the AI drew a massive bounding box covering the *entire car*.
*   **The Cause:** Zero-Shot models map language literally. By passing the word "car" (in "car logo") or "front" (in "front grill"), the AI's language-vision linkage triggered on the broader concept and highlighted the whole vehicle. 
*   **The Fix (Prompt Engineering):** Rewrote the `CaptionOntology` dictionary to aggressively isolate terms. 
    *   `"car logo"` -> `"emblem"`
    *   `"front grill"` -> `"grille"`
    *   `"headlight"` -> `"headlamp"`
    Removing broad nouns stopped the AI from getting confused, resulting in strict, pixel-perfect bounding boxes for the sub-components.

---

## [Phase 10] Continuous Growth Pipeline & Database Hardening (COMPLETED)

**The Goal:**
Automate the end-to-end flow where detected license plates are instantly turned into full citizen/vehicle profiles, while simultaneously accumulating high-quality training data for future model retraining.

**What We Built:**
1.  **`ARG_Auto_Growth_Pipeline.py`** — A "Watcher" script that monitors detection folders. It performs OCR, checks the registry, and auto-generates proxy identities (Aadhaar, VAHAN, FASTag) for unknown plates.
2.  **Explicit Schema Synchronization** — Hardened all SQL logic in the Pipeline, API Server, and Live Detector to use **named column insertions**.
3.  **`db_writer.py`** — A specialized verification tool that acts as the "Source of Truth" for the 21-column VAHAN registry schema.

**The Problems We Faced:**

### Error 1: The "Blind Insertion" Crash (The 12 vs 13 Column Mismatch)
*   **What happened:** The pipeline was crashing with `sqlite3.ProgrammingError: table citizens has 13 columns but 12 values were supplied`.
*   **The Cause:** Earlier scripts used "blind" insertions like `INSERT INTO citizens VALUES (?, ?, ...)`. When the `created_at` timestamp column was added to the database, every script that didn't know about it immediately broke.
*   **The Fix:** Rewrote all SQL to use **explicit column lists** (e.g., `INSERT INTO citizens (aadhar_masked, full_name, ...) VALUES (?, ?, ...)`). This makes the code immune to future schema changes.

### Error 2: The "Secret Schema" Naming Conflict
*   **What happened:** Even after fixing the column counts, the script failed with `no such column: chassis`.
*   **The Cause:** The production database used formal, long-form names (`chassis_number`, `engine_number`, `registration_date`) but the pipeline script was looking for shortened versions (`chassis`, `engine_no`, `reg_date`). 
*   **The Fix:** Used `PRAGMA table_info` and the `db_writer.py` test script to perform a full schema audit. Mapped every internal variable to the exact long-form column name in the SQLite file.

### Error 3: The "Zombie" Process Conflict
*   **What happened:** Multiple copies of the pipeline were running in the background, creating "Database is locked" errors and running old, unpatched code.
*   **The Fix:** Performed a system-wide `taskkill` on all Python processes and restarted a single, clean instance of the synchronized pipeline.

**The Result:**
*   **Database Synchronicity:** All core scripts (`Pipeline`, `API`, `Live Detect`) now share the exact same database "language."
*   **Unblocked Growth:** The pipeline now successfully recognizes new plates (like `MH12BG7237`), generates their proxy identities, and appends them to the CSV and SQLite databases without human intervention.
*   **Training Loop:** New plate crops are automatically categorized and staged for the next 200-plate retraining cycle.

---
