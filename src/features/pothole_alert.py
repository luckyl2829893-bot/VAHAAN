"""
VAHAAN Pothole Alert System
============================
When a pothole is detected in an image, this module:
  1. Logs the pothole with GPS coordinates and severity
  2. Determines the responsible contractor/MCD ward
  3. Issues an instant alert (simulated email/SMS/dashboard ping)
  4. Tracks resolution status

In production, replace the alert stub with:
  - Email via SMTP / SendGrid
  - SMS via Twilio / MSG91 (India-specific)
  - REST call to Delhi MCD's e-portal API
  - WhatsApp Business API alert to contractor

Pothole Severity Levels (based on visible damage):
  - LOW:      Surface crack (<5cm depth), minor repair needed
  - MODERATE: Shallow pothole (5–10cm), schedule within 7 days
  - HIGH:     Deep pothole (>10cm), hazardous — fix within 48 hours
  - CRITICAL: Large/multiple potholes, road closure risk — fix in 24 hours
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── Delhi MCD Ward / Contractor Registry (Mock) ─────────────────────────────
# In production, this would be a database lookup via GPS coordinates → ward boundary polygon

DELHI_WARD_REGISTRY = {
    # Format: "Ward Name": {"contractor": ..., "mcd_zone": ..., "contact": ..., "email": ...}
    "Connaught Place":      {"contractor": "M/S Delhi Infra Ltd",     "mcd_zone": "Central",      "contact": "+91-9876500001", "email": "central.mcd@delhi.gov.in"},
    "Lajpat Nagar":         {"contractor": "M/S South Build Corp",    "mcd_zone": "South",        "contact": "+91-9876500002", "email": "south.mcd@delhi.gov.in"},
    "Karol Bagh":           {"contractor": "M/S North Highways Pvt",  "mcd_zone": "North",        "contact": "+91-9876500003", "email": "north.mcd@delhi.gov.in"},
    "Rohini":               {"contractor": "M/S West Metro Roads",    "mcd_zone": "North-West",   "contact": "+91-9876500004", "email": "nw.mcd@delhi.gov.in"},
    "Dwarka":               {"contractor": "M/S SW Infrastructure",   "mcd_zone": "South-West",   "contact": "+91-9876500005", "email": "sw.mcd@delhi.gov.in"},
    "Shahdara":             {"contractor": "M/S East Delhi Builders",  "mcd_zone": "East",         "contact": "+91-9876500006", "email": "east.mcd@delhi.gov.in"},
    "Mayur Vihar":          {"contractor": "M/S Trans-Yamuna Const",  "mcd_zone": "East",         "contact": "+91-9876500007", "email": "east.mcd@delhi.gov.in"},
    "Janakpuri":            {"contractor": "M/S West Zone Roads",     "mcd_zone": "West",         "contact": "+91-9876500008", "email": "west.mcd@delhi.gov.in"},
    "Unknown":              {"contractor": "MCD General Contractor",   "mcd_zone": "Central HQ",  "contact": "+91-11-23221111", "email": "complaint.mcd@delhi.gov.in"},
}

SEVERITY_RULES = {
    # confidence from YOLO → pothole severity mapping
    (0.8, 1.0):  "CRITICAL",
    (0.65, 0.8): "HIGH",
    (0.5, 0.65): "MODERATE",
    (0.0, 0.5):  "LOW",
}

SLA_HOURS = {
    "CRITICAL": 24,
    "HIGH":     48,
    "MODERATE": 168,   # 7 days
    "LOW":      336,   # 14 days
}

FINE_AMOUNT = {
    "CRITICAL": 50_000,
    "HIGH":     25_000,
    "MODERATE": 10_000,
    "LOW":       5_000,
}


# ─── GPS → Ward Lookup (Simplified) ──────────────────────────────────────────

def _gps_to_ward(lat: Optional[float], lng: Optional[float]) -> str:
    """
    In production: use Shapely + Delhi ward boundary GeoJSON to do
    an exact point-in-polygon lookup.

    For the prototype, we use a bounding-box grid of Delhi zones.
    Delhi bounding box: lat 28.40–28.88, lng 76.84–77.35
    """
    if lat is None or lng is None:
        return "Unknown"

    # Very simplified zone mapping — replace with proper GeoJSON in production
    if 28.62 <= lat <= 28.68 and 77.20 <= lng <= 77.28:
        return "Connaught Place"
    elif 28.56 <= lat <= 28.62 and 77.23 <= lng <= 77.30:
        return "Lajpat Nagar"
    elif 28.64 <= lat <= 28.70 and 77.18 <= lng <= 77.22:
        return "Karol Bagh"
    elif 28.72 <= lat <= 28.80 and 77.05 <= lng <= 77.15:
        return "Rohini"
    elif 28.55 <= lat <= 28.62 and 77.00 <= lng <= 77.10:
        return "Dwarka"
    elif 28.65 <= lat <= 28.72 and 77.28 <= lng <= 77.35:
        return "Shahdara"
    elif 28.60 <= lat <= 28.65 and 77.28 <= lng <= 77.32:
        return "Mayur Vihar"
    elif 28.62 <= lat <= 28.68 and 77.06 <= lng <= 77.12:
        return "Janakpuri"
    else:
        return "Unknown"


def _confidence_to_severity(confidence: float) -> str:
    for (low, high), severity in SEVERITY_RULES.items():
        if low <= confidence < high:
            return severity
    return "LOW"


# ─── Alert Dispatcher ─────────────────────────────────────────────────────────

def _send_alert(alert_record: dict) -> dict:
    """
    Stub alert dispatcher. Replace with real integrations:
      - email: smtplib / sendgrid
      - sms:   MSG91 / Twilio (India)
      - push:  Firebase Cloud Messaging
    """
    ward    = alert_record["ward"]
    sev     = alert_record["severity"]
    addr    = alert_record.get("address", "Unknown Location")
    ticket  = alert_record["ticket_id"]
    contractor = alert_record["contractor"]
    sla     = alert_record["sla_hours"]

    # ------- SIMULATED EMAIL --------
    email_body = f"""
    ⚠️ VAHAAN POTHOLE ALERT — {sev} SEVERITY
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Ticket ID    : {ticket}
    Reported At  : {alert_record['reported_at']}
    Location     : {addr} ({ward} Ward)
    GPS          : {alert_record.get('lat','N/A')}, {alert_record.get('lng','N/A')}
    Severity     : {sev}
    SLA          : Fix within {sla} hours
    Fine if Late : ₹{alert_record['contractor_fine']:,}
    Contractor   : {contractor}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    This is an automated alert from VAHAAN Road Safety AI.
    Acknowledge: https://vahaan.gov.in/ticket/{ticket}
    """
    print(f"[ALERT EMAIL → {alert_record['contractor_email']}]")
    print(email_body)

    # ------- SIMULATED SMS ----------
    sms_body = (
        f"VAHAAN ALERT: {sev} pothole at {addr}. "
        f"Ticket {ticket}. Fix in {sla}hrs or face ₹{alert_record['contractor_fine']:,} fine. "
        f"VAHAAN Road Safety System"
    )
    print(f"[ALERT SMS → {alert_record['contractor_phone']}]: {sms_body}")

    return {
        "email_sent": True,
        "sms_sent":   True,
        "email_to":   alert_record["contractor_email"],
        "sms_to":     alert_record["contractor_phone"],
    }


# ─── Main Public API ──────────────────────────────────────────────────────────

class PotholeAlertSystem:
    """
    VAHAAN Pothole Alert System.
    Instantiate once and reuse across requests.
    """

    def __init__(self, root_path: Path):
        self.log_file = root_path / "src" / "api_brain" / "pothole_alerts_log.json"
        if not self.log_file.exists():
            self.log_file.write_text(json.dumps([], indent=2))

    def raise_alert(
        self,
        pothole_detections: list,       # list of {confidence, bbox, class_name}
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        address: Optional[str] = None,
        reported_by: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> dict:
        """
        Process all pothole detections from a single image and
        raise the appropriate MCD/contractor alerts.

        Returns summary of alerts raised.
        """
        if not pothole_detections:
            return {"alerts_raised": 0, "message": "No potholes detected — road is clear."}

        ward = _gps_to_ward(lat, lng)
        ward_info = DELHI_WARD_REGISTRY.get(ward, DELHI_WARD_REGISTRY["Unknown"])

        alerts = []
        for det in pothole_detections:
            conf     = det.get("confidence", 0.5)
            severity = _confidence_to_severity(conf)
            ticket   = f"VH-POT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            alert_record = {
                "ticket_id":         ticket,
                "reported_at":       datetime.utcnow().isoformat(),
                "reported_by":       reported_by or "VAHAAN AI",
                "ward":              ward,
                "address":           address or f"Near {ward}, Delhi",
                "lat":               lat,
                "lng":               lng,
                "severity":          severity,
                "confidence":        round(conf, 3),
                "class_detected":    det.get("class_name", "pothole"),
                "bbox":              det.get("bbox"),
                "image_url":         image_url,
                "contractor":        ward_info["contractor"],
                "contractor_email":  ward_info["email"],
                "contractor_phone":  ward_info["contact"],
                "mcd_zone":          ward_info["mcd_zone"],
                "sla_hours":         SLA_HOURS[severity],
                "contractor_fine":   FINE_AMOUNT[severity],
                "status":            "OPEN",
                "resolution":        None,
            }

            delivery = _send_alert(alert_record)
            alert_record["delivery"] = delivery
            alerts.append(alert_record)

        # Persist to log
        self._save_alerts(alerts)

        # Return structured summary
        most_severe = max(alerts, key=lambda a: list(SLA_HOURS.keys()).index(a["severity"]) * -1 + 3)
        return {
            "alerts_raised":   len(alerts),
            "ward":            ward,
            "contractor":      ward_info["contractor"],
            "contractor_phone": ward_info["contact"],
            "mcd_zone":        ward_info["mcd_zone"],
            "highest_severity": most_severe["severity"],
            "sla_hours":       most_severe["sla_hours"],
            "fine_if_missed":  most_severe["contractor_fine"],
            "tickets":         [a["ticket_id"] for a in alerts],
            "alerts":          alerts,
        }

    def get_alerts(
        self,
        status: Optional[str] = None,
        ward: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """Retrieve pothole alerts with optional filters."""
        log = json.loads(self.log_file.read_text())

        if status:
            log = [a for a in log if a.get("status", "").upper() == status.upper()]
        if ward:
            log = [a for a in log if ward.lower() in a.get("ward", "").lower()]
        if severity:
            log = [a for a in log if a.get("severity", "").upper() == severity.upper()]

        log = list(reversed(log))[:limit]
        return {
            "total":  len(log),
            "alerts": log,
        }

    def resolve_ticket(self, ticket_id: str, resolved_by: str, notes: str) -> dict:
        """Mark a pothole ticket as resolved."""
        log = json.loads(self.log_file.read_text())
        updated = False
        for alert in log:
            if alert.get("ticket_id") == ticket_id:
                alert["status"]      = "RESOLVED"
                alert["resolved_at"] = datetime.utcnow().isoformat()
                alert["resolved_by"] = resolved_by
                alert["resolution"]  = notes
                updated = True
                break

        if not updated:
            return {"status": "error", "message": f"Ticket {ticket_id} not found"}

        self.log_file.write_text(json.dumps(log, indent=2))
        return {"status": "success", "message": f"Ticket {ticket_id} marked RESOLVED"}

    def get_stats(self) -> dict:
        """Return pothole analytics for the Sentinel dashboard."""
        log = json.loads(self.log_file.read_text())
        if not log:
            return {"total_alerts": 0}

        by_severity = {}
        by_ward = {}
        by_status = {}
        total_fines = 0

        for a in log:
            sev = a.get("severity", "LOW")
            ward = a.get("ward", "Unknown")
            stat = a.get("status", "OPEN")
            fine = a.get("contractor_fine", 0)

            by_severity[sev]  = by_severity.get(sev, 0) + 1
            by_ward[ward]     = by_ward.get(ward, 0) + 1
            by_status[stat]   = by_status.get(stat, 0) + 1
            if stat == "OPEN":
                total_fines += fine

        return {
            "total_alerts":      len(log),
            "open_tickets":      by_status.get("OPEN", 0),
            "resolved_tickets":  by_status.get("RESOLVED", 0),
            "by_severity":       by_severity,
            "by_ward":           by_ward,
            "by_status":         by_status,
            "potential_fines":   total_fines,
            "worst_ward":        max(by_ward, key=by_ward.get) if by_ward else None,
        }

    def _save_alerts(self, new_alerts: list):
        """Append new alerts to the persistent log."""
        log = json.loads(self.log_file.read_text())
        log.extend(new_alerts)
        if len(log) > 10_000:
            log = log[-10_000:]
        self.log_file.write_text(json.dumps(log, indent=2))
