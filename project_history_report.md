# Project History & Error Post-Mortem Report

As requested, here is the official breakdown of exactly what went wrong in our initial attempts to train the single-stage YOLO model for the Aequitas RoadGuard (ARG) system, and why the outputs on the initial `predict_test` folder looked so disjointed.

---

## 🛑 The Core Problem
To create a YOLO dataset, we heavily relied on an automated script ([build_yolo_dataset.py](file:///c:/Users/laksh/Desktop/image/build_yolo_dataset.py)) to generate ground-truth labels for thousands of raw images downloaded from the internet. **The script logic had fundamental flaws that taught the YOLO model to behave completely erratically.**

### Error 1: The "Folder Name" Fallacy (Making Bad Vehicle Boxes)
*   **What we did:** We separated images into folders (`3 wheeler`, `cars`, etc.), and then aggressively told the script that *any* vehicle found in that folder strictly belonged to that class. 
*   **The Error:** If an image in the `3 wheeler` folder contained a yellow dump truck in the background, our script blindly hard-coded that truck's bounding box as "class 1" (3-wheeler). The YOLO model was actively being taught that massive yellow trucks are 3-wheelers.

### Error 2: Single-Object Blindness (Overlapping & Missing Boxes)
*   **What we did:** The script searched the image for a vehicle using COCO, drew a box around the first vehicle it found, and then fired off a Python `break` statement to stop looking for more.
*   **The Error:** Whenever an image had multiple cars or people on bikes, only the first object was labeled. The model incorrectly learned that all other unlabelled bikes/cars in the image were "background noise". This caused overlapping confusions and completely empty detections later on.

### Error 3: The Watermark Disaster (Bad Plate Identification)
*   **What we did:** We used `easyocr` to find license plates blindly. We told it: *"Look at the bottom 60% of the vehicle. If you see text with numbers and letters, it is definitely a license plate!"*
*   **The Error:** 
    1. It read text painted on trucks (e.g. "CARRIER" or phone numbers) and labeled them as ground-truth plates. 
    2. When evaluating images of bikes with corner watermarks, it read the watermark and made it a license plate.
    3. It explicitly **ignored the top 40%** of motorcycles, meaning any license plate accurately mounted near a bike's handlebars was completely erased from the training data. The model was never taught what a motorcycle plate looks like.

---

## 🛠️ The Solution (What we are doing now)
Instead of forcing raw, messy images to comply with a blind Python script, we are moving to the **"Two-Stage AI Pipeline"**. 

We have successfully dropped our flawed YOLO dataset entirely. By deleting it and moving to the manually-annotated Roboflow datasets (`Indian number plate.v3i.yolov11` and `car-motorcycle-bus-truck.v1i.yolov11`), the YOLO model will now learn from perfect, human-verified ground truth instead of OCR mistakes. 

This guarantees:
1. No more yellow trucks being called 3-wheelers.
2. No more watermarks being detected as plates.
3. Every motorcycle plate is found regardless of where it is mounted.
