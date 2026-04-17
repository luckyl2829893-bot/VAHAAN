"""
VAHAAN — LIVE STREAM ENGINE
========================================
Supports: USB Webcam (0), Phone (IP Cam), Security Camera (RTSP)
Controls: Press 'q' to quit.
"""

import os, sys, time, cv2, torch, numpy as np
from PIL import Image
from ultralytics import YOLO

# ── GroundingDINO ──
from groundingdino.util.inference import load_model as load_gdino_model
from groundingdino.util.inference import predict as gdino_predict
import groundingdino.datasets.transforms as T

# ══════════════════════════════════════════════════════════════
# CONFIG — Source '0' for webcam, or "rtsp://..." for IP Cam
# ══════════════════════════════════════════════════════════════
LIVE_SOURCE   = 0             # 0 = USB Webcam
MODEL_PATH    = "best_new.pt"
VEHICLE_CONF  = 0.25          # Higher for live to reduce flicker
PROCESS_EVERY = 2             # Analyze every 2nd frame for speed

GDINO_CONFIG  = r"models\gdino\GroundingDINO_SwinT_OGC.py"
GDINO_WEIGHTS = r"models\gdino\groundingdino_swint_ogc.pth"

VEHICLE_IDS   = {0: "Car", 1: "Motorcycle", 2: "Bus", 3: "Truck"}
COMP_COLORS   = {"plate": (0,255,255), "logo": (255,128,0), "headlamp": (255,255,255), "taillamp": (0,0,255), "grille": (255,0,255)}
VEH_COLORS    = {"Car": (255,200,50), "Taxi": (0,255,255), "EV Taxi": (0,255,150), "EV Private": (100,255,100)}

# ══════════════════════════════════════════════════════════════

def is_red_dominant(roi_bgr):
    if roi_bgr.size == 0: return False
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    return (cv2.countNonZero(m1) + cv2.countNonZero(m2)) / roi_bgr.size > 0.08

def build_gdino_transform():
    return T.Compose([T.RandomResize([256], max_size=448), T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

def run_gdino_on_roi(model, transform, roi_bgr, device_str):
    h_roi, w_roi = roi_bgr.shape[:2]
    if h_roi < 30 or w_roi < 30: return []
    pil_img = Image.fromarray(cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB))
    transformed, _ = transform(pil_img, None)
    prompt = "number plate . taillamp . brake light . headlamp . logo . brand emblem"
    boxes, logits, phrases = gdino_predict(model=model, image=transformed, caption=prompt,
                                         box_threshold=0.35, text_threshold=0.30, device=device_str)
    raw = []
    for box, logit, phrase in zip(boxes, logits, phrases):
        cx, cy, w, h = box.tolist()
        p = phrase.lower(); lbl = None
        if "plate" in p: lbl = "plate"
        elif "tail" in p or "brake" in p: lbl = "taillamp"
        elif "head" in p: lbl = "headlamp"
        elif "logo" in p or "emblem" in p: lbl = "logo"
        if lbl: raw.append({"l": lbl, "c": float(logit), "b": [cx, cy, w, h]})
    
    plates = sorted([d for d in raw if d["l"] == "plate"], key=lambda x: x["c"], reverse=True)
    final = [plates[0]] if (plates and 1.5 < (plates[0]["b"][2]/plates[0]["b"][3]) < 8.0) else []
    
    for d in raw:
        if d["l"] in ["headlamp", "taillamp"]:
            cx, cy, bw, bh = d["b"]
            light_roi = roi_bgr[int((cy-bh/2)*h_roi):int((cy+bh/2)*h_roi), int((cx-bw/2)*w_roi):int((cx+bw/2)*w_roi)]
            d["l"] = "taillamp" if is_red_dominant(light_roi) else "headlamp"
            if d["c"] > 0.50: final.append(d)
        elif d["l"] == "logo" and d["c"] > 0.50 and d["b"][2] < 0.2:
            final.append(d)
    return [(d["l"], d["c"], d["b"][0], d["b"][1], d["b"][2], d["b"][3]) for d in final]

def detect_plate_color(plate_roi):
    if plate_roi.size == 0: return "white"
    hsv = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2HSV)
    total = plate_roi.size; y_m = cv2.inRange(hsv, np.array([18, 80, 80]), np.array([35, 255, 255]))
    g_m = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([90, 255, 255]))
    y_r, g_r = cv2.countNonZero(y_m)/total, cv2.countNonZero(g_m)/total
    if g_r > 0.25: return "green_yellow" if y_r > 0.04 else "green"
    return "yellow" if y_r > 0.30 else "white"

def main():
    device = "cuda"; veh_m = YOLO(MODEL_PATH).to(device)
    gd_m = load_gdino_model(GDINO_CONFIG, GDINO_WEIGHTS, device=device).to(device)
    trans = build_gdino_transform()
    cap = cv2.VideoCapture(LIVE_SOURCE)
    cv2.namedWindow("VAHAAN - LIVE", cv2.WINDOW_NORMAL)

    gd_cache = {}; last_dets = []; f_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        if f_idx % PROCESS_EVERY == 0:
            tracks = veh_m.track(frame, persist=True, conf=VEHICLE_CONF, verbose=False, agnostic_nms=True)
            curr_dets = []
            if tracks and tracks[0].boxes is not None:
                r = tracks[0]; boxes = r.boxes.xyxy.cpu().numpy(); tids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else np.arange(len(boxes)); cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                for i in range(len(boxes)):
                    x1, y1, x2, y2 = map(int, boxes[i]); tid = int(tids[i]); cls_name = VEHICLE_IDS.get(cls_ids[i], "Car")
                    det = {"vbox": (x1,y1,x2,y2), "cls": cls_name, "tid": tid, "comps": []}
                    
                    cached = gd_cache.get(tid)
                    if cached and (f_idx - cached[0] < 15): raw = cached[1]
                    else:
                        roi = frame[max(0,y1-5):y2+5, max(0,x1-5):x2+5]
                        raw = run_gdino_on_roi(gd_m, trans, roi, device)
                        gd_cache[tid] = (f_idx, raw)
                    
                    vw, vh = x2-x1, y2-y1
                    for clbl, conf, cx, cy, bw, bh in raw:
                        sx1, sy1, sx2, sy2 = int(x1+(cx-bw/2)*vw), int(y1+(cy-bh/2)*vh), int(x1+(cx+bw/2)*vw), int(y1+(cy+bh/2)*vh)
                        det["comps"].append((clbl, conf, sx1, sy1, sx2, sy2))
                        if clbl == "plate":
                            pc = detect_plate_color(frame[max(0,sy1):sy2, max(0,sx1):sx2])
                            if pc == "yellow": det["cls"] = "Taxi"
                            elif "green" in pc: det["cls"] = "EV Taxi" if "yellow" in pc else "EV Private"
                    curr_dets.append(det)
            last_dets = curr_dets
        
        # UI
        for d in last_dets:
            vx1, vy1, vx2, vy2 = d["vbox"]; color = VEH_COLORS.get(d["cls"], (255,200,50))
            cv2.rectangle(frame, (vx1,vy1), (vx2,vy2), color, 2)
            cv2.putText(frame, f"ID:{d['tid']} {d['cls']}", (vx1, vy1-10), 0, 0.6, color, 2)
            for cl, cf, sx1, sy1, sx2, sy2 in d["comps"]:
                cc = COMP_COLORS.get(cl,(200,200,200)); cv2.rectangle(frame, (sx1,sy1), (sx2,sy2), cc, 1)
        
        cv2.imshow("VAHAAN - LIVE", frame)
        f_idx += 1
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release(); cv2.destroyAllWindows()
if __name__ == "__main__": main()
