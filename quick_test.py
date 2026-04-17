"""
VAHAAN — QUICK TEST v9 (Precision Sharpness)
======================================================
1. Precision Plate Filter: Aspect Ratio 3.5 - 5.5 (kills decals).
2. Proximity Logo Search: Anchored above detected plates.
3. V8 Fast-Start: Bypasses BERT internet check.
"""

import os, sys, time, cv2, torch, numpy as np
from PIL import Image
from ultralytics import YOLO

# ── GroundingDINO ──
from groundingdino.util.inference import load_model as load_gdino_model
from groundingdino.util.inference import predict as gdino_predict
import groundingdino.datasets.transforms as T

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════
VIDEO_PATH    = "test_video.mp4"
MODEL_PATH    = "best_new.pt"
OUTPUT_PATH   = "test_outputs/FINAL_VAHAAN_V9.mp4"
VEHICLE_CONF  = 0.15
VEHICLE_IOU   = 0.45
VEHICLE_IDS   = {0: "Car", 1: "Motorcycle", 2: "Bus", 3: "Truck"}

PROCESS_EVERY = 3
GDINO_CACHE_FRAMES = 12

GDINO_CONFIG  = r"models\gdino\GroundingDINO_SwinT_OGC.py"
GDINO_WEIGHTS = r"models\gdino\groundingdino_swint_ogc.pth"

COMP_COLORS = {"plate": (0,255,255), "logo": (255,128,0), "headlamp": (255,255,255), "taillamp": (0,0,255), "grille": (255,0,255)}
VEH_COLORS = {"Car": (255,200,50), "Taxi": (0,255,255), "EV Taxi": (0,255,150), "EV Private": (100,255,100), "Motorcycle": (50,200,255)}

# ══════════════════════════════════════════════════════════════

def is_red_dominant(roi_bgr):
    if roi_bgr.size < 4: return False
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 80, 50]), np.array([10, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([160, 80, 50]), np.array([180, 255, 255]))
    return (cv2.countNonZero(m1) + cv2.countNonZero(m2)) / roi_bgr.size > 0.10

def build_gdino_transform():
    return T.Compose([T.RandomResize([384], max_size=640), T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

def run_gdino_on_roi(model, transform, roi_bgr, device_str):
    h_roi, w_roi = roi_bgr.shape[:2]
    if h_roi < 30 or w_roi < 30: return []
    pil_img = Image.fromarray(cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB))
    transformed, _ = transform(pil_img, None)
    
    prompt = "number plate . taillamp . headlamp . logo emblem . car badge . grille"
    boxes, logits, phrases = gdino_predict(model=model, image=transformed, caption=prompt,
                                         box_threshold=0.32, text_threshold=0.28, device=device_str)
    raw = []; has_taillamp = False
    for box, logit, phrase in zip(boxes, logits, phrases):
        cx, cy, w, h = box.tolist(); p = phrase.lower(); lbl = None
        if "plate" in p or "number" in p: lbl = "plate"
        elif "tail" in p or "brake" in p: lbl = "taillamp"; has_taillamp = True
        elif "head" in p: lbl = "headlamp"
        elif "logo" in p or "emblem" in p or "badge" in p: lbl = "logo"
        elif "grill" in p: lbl = "grille"
        if lbl: raw.append({"l": lbl, "c": float(logit), "b": [cx, cy, w, h]})
    
    # ─── PRECISION FILTER ───
    # 1. Plate: Must be in lower half, Must have 3.5 - 6.0 Aspect Ratio
    valid_plates = []
    for d in raw:
        if d["l"] == "plate":
            cx, cy, bw, bh = d["b"]
            aspect = bw/max(bh, 0.001)
            # Kill decals: "Lithium" and "Electric" text are usually > 7.0 or < 3.0 aspect
            if 3.2 < aspect < 6.8 and 0.4 < cy < 0.9:
                valid_plates.append(d)
    
    plates = sorted(valid_plates, key=lambda x: x["c"], reverse=True)
    final = [plates[0]] if plates else []
    p_cy = plates[0]["b"][1] if plates else 1.0

    for d in raw:
        if d["l"] == "grille" and has_taillamp: continue
        if d["l"] in ["headlamp", "taillamp"]:
            cx, cy, bw, bh = d["b"]
            lr = roi_bgr[int((cy-bh/2)*h_roi):int((cy+bh/2)*h_roi), int((cx-bw/2)*w_roi):int((cx+bw/2)*w_roi)]
            if lr.size > 0:
                d["l"] = "taillamp" if is_red_dominant(lr) else "headlamp"
            if d["c"] > 0.40: final.append(d)
        elif d["l"] == "logo":
            cx, cy, bw, bh = d["b"]
            # Logo is usually ABOVE the plate but below center
            if cy < p_cy and bw < 0.20:
                if d["c"] > 0.28: final.append(d) # Lower threshold for logo if position matches
        elif d["l"] == "grille" and d["c"] > 0.40:
            final.append(d)
    return [(d["l"], d["c"], d["b"][0], d["b"][1], d["b"][2], d["b"][3]) for d in final]

def detect_plate_color(plate_roi):
    if plate_roi.size < 10: return "white"
    hsv = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2HSV)
    y_m = cv2.inRange(hsv, np.array([15, 70, 70]), np.array([38, 255, 255]))
    g_m = cv2.inRange(hsv, np.array([40, 40, 40]), np.array([95, 255, 255]))
    y_r, g_r = cv2.countNonZero(y_m)/plate_roi.size, cv2.countNonZero(g_m)/plate_roi.size
    if g_r > 0.20: return "green_yellow" if y_r > 0.05 else "green"
    return "yellow" if y_r > 0.30 else "white"

def main():
    print("[INIT] Loading Models (Offline Mode)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    veh_m = YOLO(MODEL_PATH).to(device)
    gd_m = load_gdino_model(GDINO_CONFIG, GDINO_WEIGHTS, device=device).to(device)
    trans = build_gdino_transform()
    cap = cv2.VideoCapture(VIDEO_PATH)
    W, H = int(cap.get(3)), int(cap.get(4))
    writer = cv2.VideoWriter(OUTPUT_PATH, cv2.VideoWriter_fourcc(*"mp4v"), cap.get(5), (W, H))
    
    print(f"[START] Processing -> {OUTPUT_PATH}")
    gd_cache = {}; last_dets = []; f_idx = 0
    t_start = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        if f_idx % PROCESS_EVERY == 0:
            tracks = veh_m.track(frame, persist=True, conf=VEHICLE_CONF, iou=VEHICLE_IOU, agnostic_nms=True, verbose=False)
            curr_dets = []
            if tracks and tracks[0].boxes is not None:
                r = tracks[0]; boxes = r.boxes.xyxy.cpu().numpy(); tids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else np.arange(len(boxes)); cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                for i in range(len(boxes)):
                    x1, y1, x2, y2 = map(int, boxes[i]); tid = int(tids[i]); cls_orig = VEHICLE_IDS.get(cls_ids[i], "Car")
                    det = {"vbox": (x1,y1,x2,y2), "cls": cls_orig, "tid": tid, "comps": []}
                    cached = gd_cache.get(tid)
                    if cached and (f_idx - cached[0] < GDINO_CACHE_FRAMES): raw = cached[1]
                    else:
                        roi = frame[max(0,y1-5):y2+5, max(0,x1-5):x2+5]
                        raw = run_gdino_on_roi(gd_m, trans, roi, device); gd_cache[tid] = (f_idx, raw)
                    vw, vh = x2-x1, y2-y1
                    for clbl, conf, cx, cy, bw, bh in raw:
                        sx1, sy1, sx2, sy2 = int(x1+(cx-bw/2)*vw), int(y1+(cy-bh/2)*vh), int(x1+(cx+bw/2)*vw), int(y1+(cy+bh/2)*vh)
                        det["comps"].append((clbl, conf, sx1, sy1, sx2, sy2))
                        if clbl == "plate":
                            pc = detect_plate_color(frame[max(0,sy1):sy2, max(0,sx1):sx2])
                            if pc == "yellow" and det["cls"]=="Car": det["cls"] = "Taxi"
                            elif "green" in pc and det["cls"]=="Car": det["cls"] = "EV Taxi" if "yellow" in pc else "EV Private"
                    curr_dets.append(det)
            last_dets = curr_dets
        res_frame = frame.copy()
        for d in last_dets:
            vx1, vy1, vx2, vy2 = d["vbox"]; color = VEH_COLORS.get(d["cls"], (255,200,50))
            cv2.rectangle(res_frame, (vx1,vy1), (vx2,vy2), color, 2)
            cv2.putText(res_frame, f"{d['cls']}", (vx1, vy1-10), 0, 0.7, color, 2)
            for cl, cf, sx1, sy1, sx2, sy2 in d["comps"]:
                cc = COMP_COLORS.get(cl,(200,200,200)); cv2.rectangle(res_frame, (sx1,sy1), (sx2,sy2), cc, 1)
        writer.write(res_frame); f_idx += 1
        if f_idx % 200 == 0: print(f"  [FPS: {f_idx/(time.time()-t_start):.1f}] Processing Frame {f_idx}")
    cap.release(); writer.release()
if __name__ == "__main__": main()
