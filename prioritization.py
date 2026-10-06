"""
CivicPulse AI - Smart Prioritization Engine
Computes a 0-100 Priority Score using:
1. AI Detected Severity (1-5)
2. Issue Type Inherent Public Safety Risk Weight
3. Spatial Duplicate Clustering (within 50 meters)
4. Aging Escalation (days elapsed without resolution)
Categorizes into: High, Medium, Low with full explainability.
"""

from datetime import datetime
from typing import Dict, Any, List
from utils import haversine_distance_meters

# Inherent Risk Weight by Issue Type
ISSUE_TYPE_WEIGHTS = {
    "overflowing drain": 25,     # Biological contamination, flash flood, dengue risk
    "pothole": 22,               # High fatal risk for 2-wheelers, wheel axle damage
    "damaged road": 18,          # Structural road base deterioration
    "broken streetlight": 14,    # Crime risk, nighttime pedestrian danger
    "waterlogging": 20,          # Traffic blockage, foundation damage
    "other": 12,
    "none": 0
}


def calculate_cluster_duplicates(
    target_lat: float,
    target_lon: float,
    target_type: str,
    existing_reports: List[Dict[str, Any]],
    current_report_id: int = None,
    radius_meters: float = 50.0
) -> int:
    """
    Find active reports within ~50 meters of the same issue type.
    Returns the count of duplicates in this spatial cluster.
    """
    duplicates = 0
    target_norm_type = target_type.lower().strip()

    for report in existing_reports:
        # Don't compare with self
        if current_report_id and report.get("id") == current_report_id:
            continue

        # Only cluster active issues (not resolved)
        if report.get("status") == "Resolved":
            continue

        report_type = str(report.get("issue_type", "")).lower().strip()
        if report_type != target_norm_type:
            continue

        r_lat = float(report.get("latitude", 0.0))
        r_lon = float(report.get("longitude", 0.0))

        dist = haversine_distance_meters(target_lat, target_lon, r_lat, r_lon)
        if dist <= radius_meters:
            duplicates += 1

    return duplicates


def compute_priority_score(
    severity: int,
    issue_type: str,
    duplicate_count: int = 0,
    reported_at_iso: str = None,
    is_resolved: bool = False
) -> Dict[str, Any]:
    """
    Computes priority score (0-100) and priority level (High/Medium/Low)
    with a complete breakdown of scoring factors for transparency.
    """
    norm_type = issue_type.lower().strip()
    if norm_type not in ISSUE_TYPE_WEIGHTS:
        norm_type = "other"

    # 1. Base Severity (10 to 45 pts)
    sev_clamped = max(1, min(5, int(severity)))
    base_severity_pts = sev_clamped * 9

    # 2. Inherent Risk Weight (10 to 25 pts)
    risk_pts = ISSUE_TYPE_WEIGHTS.get(norm_type, 12)

    # 3. Spatial Duplicate Clustering (+7 pts per duplicate report, max 20 pts)
    cluster_pts = min(20, duplicate_count * 7)

    # 4. Aging Escalation (+1.5 pts per day unresolved, max 15 pts)
    age_pts = 0.0
    days_old = 0
    if not is_resolved and reported_at_iso:
        try:
            reported_dt = datetime.fromisoformat(reported_at_iso)
            now = datetime.now()
            days_old = max(0, (now - reported_dt).days)
            age_pts = min(15.0, days_old * 1.5)
        except Exception:
            age_pts = 0.0

    raw_score = base_severity_pts + risk_pts + cluster_pts + age_pts
    final_score = int(round(max(5, min(100, raw_score))))

    # Categorization Thresholds
    if final_score >= 70:
        level = "High"
        badge_color = "#EF4444"  # Red
        action_sla = "Immediate action required within 24 hours"
    elif final_score >= 45:
        level = "Medium"
        badge_color = "#F59E0B"  # Orange
        action_sla = "Inspection & repair scheduled within 48-72 hours"
    else:
        level = "Low"
        badge_color = "#10B981"  # Green
        action_sla = "Routine civic maintenance queue"

    return {
        "priority_score": final_score,
        "priority_level": level,
        "badge_color": badge_color,
        "action_sla": action_sla,
        "breakdown": {
            "severity_pts": base_severity_pts,
            "risk_pts": risk_pts,
            "cluster_pts": cluster_pts,
            "age_pts": round(age_pts, 1),
            "duplicate_count": duplicate_count,
            "days_old": days_old
        }
    }
