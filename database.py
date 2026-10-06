"""
CivicPulse AI - SQLite Database & Indore Seed Data Module
Handles persistence for infrastructure issue reports, status lifecycles, and demo seeding.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from prioritization import compute_priority_score, calculate_cluster_duplicates

DB_PATH = os.path.join(os.path.dirname(__file__), "civicpulse.db")


def get_db_connection(db_file: str = DB_PATH) -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_file: str = DB_PATH):
    """Initializes the SQLite schema if it does not exist."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        severity INTEGER NOT NULL,
        confidence REAL NOT NULL,
        priority_score INTEGER NOT NULL,
        priority_level TEXT NOT NULL,
        description TEXT NOT NULL,
        safety_risk TEXT NOT NULL,
        citizen_notes TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Reported',
        assigned_department TEXT,
        assigned_worker TEXT,
        image_path TEXT,
        reported_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        resolution_notes TEXT,
        cluster_count INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()


def insert_issue(
    title: str,
    issue_type: str,
    severity: int,
    confidence: float,
    description: str,
    safety_risk: str,
    latitude: float,
    longitude: float,
    location_name: str,
    citizen_notes: str = "",
    image_path: str = "",
    status: str = "Reported",
    assigned_department: str = "Unassigned",
    assigned_worker: str = "",
    reported_at: str = None,
    db_file: str = DB_PATH
) -> int:
    """Inserts a new issue into SQLite and auto-computes its clustered priority score."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    if not reported_at:
        reported_at = datetime.now().isoformat()
    updated_at = reported_at

    # Fetch existing active reports to calculate spatial clustering (~50m)
    cursor.execute("SELECT id, issue_type, latitude, longitude, status, severity, reported_at FROM issues")
    existing_reports = [dict(row) for row in cursor.fetchall()]

    cluster_count = calculate_cluster_duplicates(
        latitude, longitude, issue_type, existing_reports
    )

    priority_info = compute_priority_score(
        severity=severity,
        issue_type=issue_type,
        duplicate_count=cluster_count,
        reported_at_iso=reported_at,
        is_resolved=(status == "Resolved")
    )

    # Generate sequential tracking ID
    cursor.execute("SELECT COUNT(*) FROM issues")
    count = cursor.fetchone()[0] + 1
    tracking_id = f"CP-IND-{count:04d}"

    cursor.execute("""
    INSERT INTO issues (
        tracking_id, title, issue_type, severity, confidence,
        priority_score, priority_level, description, safety_risk,
        citizen_notes, latitude, longitude, location_name,
        status, assigned_department, assigned_worker, image_path,
        reported_at, updated_at, resolution_notes, cluster_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tracking_id,
        title,
        issue_type,
        severity,
        confidence,
        priority_info["priority_score"],
        priority_info["priority_level"],
        description,
        safety_risk,
        citizen_notes,
        latitude,
        longitude,
        location_name,
        status,
        assigned_department,
        assigned_worker,
        image_path,
        reported_at,
        updated_at,
        "",
        cluster_count
    ))

    issue_id = cursor.lastrowid

    # Reciprocally update any neighbors within 50m so their cluster count & score increment
    from utils import haversine_distance_meters
    target_norm_type = issue_type.lower().strip()
    for neighbor in existing_reports:
        if neighbor.get("status") == "Resolved":
            continue
        if str(neighbor.get("issue_type", "")).lower().strip() != target_norm_type:
            continue
        dist = haversine_distance_meters(latitude, longitude, float(neighbor["latitude"]), float(neighbor["longitude"]))
        if dist <= 50.0:
            # Recompute neighbor's cluster count and score
            n_id = neighbor["id"]
            cursor.execute("SELECT id, issue_type, latitude, longitude, status FROM issues WHERE id != ?", (n_id,))
            other_reps = [dict(r) for r in cursor.fetchall()]
            n_clusters = calculate_cluster_duplicates(neighbor["latitude"], neighbor["longitude"], neighbor["issue_type"], other_reps)
            n_prio = compute_priority_score(
                severity=neighbor["severity"],
                issue_type=neighbor["issue_type"],
                duplicate_count=n_clusters,
                reported_at_iso=neighbor["reported_at"],
                is_resolved=False
            )
            cursor.execute("UPDATE issues SET cluster_count = ?, priority_score = ?, priority_level = ? WHERE id = ?",
                           (n_clusters, n_prio["priority_score"], n_prio["priority_level"], n_id))

    conn.commit()
    conn.close()
    return issue_id


def get_all_issues(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    db_file: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Retrieves issues sorted by priority score descending."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if type_filter and type_filter != "All":
        query += " AND issue_type = ?"
        params.append(type_filter)

    if priority_filter and priority_filter != "All":
        query += " AND priority_level = ?"
        params.append(priority_filter)

    if search_query and search_query.strip():
        query += " AND (title LIKE ? OR location_name LIKE ? OR tracking_id LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term, term])

    query += " ORDER BY priority_score DESC, reported_at DESC"

    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_issue_by_id(issue_id: int, db_file: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Fetch single issue by primary key."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_issue_status(
    issue_id: int,
    new_status: str,
    assigned_department: str = None,
    assigned_worker: str = None,
    resolution_notes: str = None,
    db_file: str = DB_PATH
) -> bool:
    """Updates the workflow status and recomputes priority if resolved."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    now_iso = datetime.now().isoformat()
    issue = get_issue_by_id(issue_id, db_file)
    if not issue:
        conn.close()
        return False

    # If marked resolved, recalculate score without age penalty
    if new_status == "Resolved":
        cursor.execute("SELECT id, issue_type, latitude, longitude, status FROM issues")
        existing_reports = [dict(r) for r in cursor.fetchall()]
        cluster_cnt = calculate_cluster_duplicates(
            issue["latitude"], issue["longitude"], issue["issue_type"],
            existing_reports, current_report_id=issue_id
        )
        new_priority = compute_priority_score(
            severity=issue["severity"],
            issue_type=issue["issue_type"],
            duplicate_count=cluster_cnt,
            reported_at_iso=issue["reported_at"],
            is_resolved=True
        )
        p_score = new_priority["priority_score"]
        p_level = new_priority["priority_level"]
    else:
        p_score = issue["priority_score"]
        p_level = issue["priority_level"]

    dept = assigned_department if assigned_department is not None else issue["assigned_department"]
    worker = assigned_worker if assigned_worker is not None else issue["assigned_worker"]
    notes = resolution_notes if resolution_notes is not None else issue["resolution_notes"]

    cursor.execute("""
    UPDATE issues
    SET status = ?, assigned_department = ?, assigned_worker = ?,
        resolution_notes = ?, updated_at = ?, priority_score = ?, priority_level = ?
    WHERE id = ?
    """, (new_status, dept, worker, notes, now_iso, p_score, p_level, issue_id))

    conn.commit()
    conn.close()
    return True


def get_summary_kpis(db_file: str = DB_PATH) -> Dict[str, Any]:
    """Computes overall statistics for the municipal leadership dashboard."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM issues")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Reported'")
    reported = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'In Progress' OR status = 'Assigned'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE priority_level = 'High' AND status != 'Resolved'")
    high_critical = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "reported": reported,
        "in_progress": in_progress,
        "resolved": resolved,
        "high_critical": high_critical
    }


def seed_indore_demo_data(db_file: str = DB_PATH, force: bool = False):
    """
    Seeds the SQLite database with 18 realistic, rich municipal issues across Indore, India.
    Demonstrates:
    - Indore landmarks (Vijay Nagar, Rajwada, Chappan Dukan, Palasia, Bhawarkua, Super Corridor, etc.)
    - Multi-factor priority ranking
    - Spatial clustering (Vijay Nagar has 3 duplicate reports within 40m!)
    - Escalated older reports (up to 12 days old)
    - Realistic status progressions (Reported, Assigned, In Progress, Resolved)
    """
    init_db(db_file)
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM issues")
    count = cursor.fetchone()[0]

    if count > 0 and not force:
        conn.close()
        return

    # Clear if force
    if force:
        cursor.execute("DELETE FROM issues")
        conn.commit()

    conn.close()

    now = datetime.now()

    # Pre-defined realistic Indore civic issues
    seed_records = [
        # Cluster at Vijay Nagar Square (Point 1 - Pothole)
        {
            "title": "Severe Pothole on BRTS Corridor",
            "issue_type": "pothole",
            "severity": 5,
            "confidence": 0.97,
            "description": "Deep circular crater (approx 2 feet diameter, 6 inches deep) on the main AB Road lane adjacent to Vijay Nagar BRTS bus stop.",
            "safety_risk": "Imminent fatal collision hazard for two-wheeler commuters; vehicles swerving abruptly into incoming traffic.",
            "citizen_notes": "Multiple two-wheelers skidded last night during rain. Please barricade immediately!",
            "latitude": 22.7533,
            "longitude": 75.8937,
            "location_name": "Vijay Nagar Square (AB Road BRTS Lane)",
            "status": "Reported",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Unassigned",
            "days_ago": 4,
            "image_type": "pothole_crater"
        },
        # Cluster at Vijay Nagar Square (Point 2 - Pothole duplicate, 32m away!)
        {
            "title": "Road Cavity Near C21 Mall Entrance",
            "issue_type": "pothole",
            "severity": 4,
            "confidence": 0.94,
            "description": "Secondary asphalt pothole with fractured sub-base near Vijay Nagar intersection service lane.",
            "safety_risk": "Vehicular tire blowout risk and severe bottleneck causing 1.5km peak-hour traffic jams.",
            "citizen_notes": "Third time reported by shopkeepers association.",
            "latitude": 22.7535,
            "longitude": 75.8939,
            "location_name": "Vijay Nagar Square (Service Lane near C21 Mall)",
            "status": "Reported",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Unassigned",
            "days_ago": 3,
            "image_type": "pothole_crater"
        },
        # Cluster at Vijay Nagar Square (Point 3 - Pothole duplicate, 25m away!)
        {
            "title": "Broken Tarmac Surface at Vijay Nagar Turn",
            "issue_type": "pothole",
            "severity": 4,
            "confidence": 0.92,
            "description": "Asphalt depression accumulating gravel and sharp stones on turn towards Scheme 54.",
            "safety_risk": "Loose gravel causing braking failures for city buses and auto-rickshaws.",
            "citizen_notes": "Urgent attention needed before weekend rush.",
            "latitude": 22.7532,
            "longitude": 75.8935,
            "location_name": "Vijay Nagar Square (Scheme 54 Turn)",
            "status": "Assigned",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Er. Rajesh Sharma (Zonal Officer)",
            "days_ago": 2,
            "image_type": "pothole_crater"
        },
        # Chappan Dukan (56 Dukan) - Overflowing Drain
        {
            "title": "Overflowing Commercial Kitchen Drain at 56 Dukan",
            "issue_type": "overflowing drain",
            "severity": 5,
            "confidence": 0.98,
            "description": "Storm drain backflow spilling untreated oily greywater across the pedestrian food plaza walkway.",
            "safety_risk": "Acute public health hazard, foul odor, pedestrian slip hazard, and dengue mosquito vector infestation.",
            "citizen_notes": "Affecting thousands of visitors daily at Indore's prime tourist culinary hub.",
            "latitude": 22.7244,
            "longitude": 75.8839,
            "location_name": "56 Dukan (Chappan Food Street)",
            "status": "In Progress",
            "assigned_department": "IMC Drainage & Sewerage Dept",
            "assigned_worker": "Er. Manoj Verma (Sanitation Supt.)",
            "days_ago": 1,
            "image_type": "overflowing_drain"
        },
        # Bhawarkua Square - Broken Streetlight
        {
            "title": "Unlit High-Mast Lamp & Exposed Wires",
            "issue_type": "broken streetlight",
            "severity": 4,
            "confidence": 0.93,
            "description": "Dual sodium vapor streetlight fixtures dead; bottom inspection cover missing with hanging electrical cables.",
            "safety_risk": "Electrocution danger for school/college students walking in rain; pitch-dark intersection raises street crime risk.",
            "citizen_notes": "Dark stretch of 300m where 50,000 coaching students commute every evening.",
            "latitude": 22.6926,
            "longitude": 75.8672,
            "location_name": "Bhawarkua Square (Coaching Hub)",
            "status": "Reported",
            "assigned_department": "IMC Electrical Engineering Wing",
            "assigned_worker": "Unassigned",
            "days_ago": 6,
            "image_type": "broken_streetlight"
        },
        # Rajwada Palace - Damaged Historic Road
        {
            "title": "Sunken Paver Blocks & Cracked Tarmac at Rajwada",
            "issue_type": "damaged road",
            "severity": 3,
            "confidence": 0.89,
            "description": "Extensive subsidence of stone sett pavement causing uneven 4-inch ridges near the Holkar royal monument.",
            "safety_risk": "Pedestrian trip accidents among elderly tourists; slow traffic causing severe gridlock in Sarafa market.",
            "citizen_notes": "Tourists tripping on loose granite slabs daily.",
            "latitude": 22.7186,
            "longitude": 75.8554,
            "location_name": "Rajwada Palace Chowk (Heritage Zone)",
            "status": "In Progress",
            "assigned_department": "Smart City Heritage Infrastructure Cell",
            "assigned_worker": "Er. Priya Sen (Conservation Officer)",
            "days_ago": 7,
            "image_type": "damaged_road"
        },
        # Super Corridor - TCS Gate - High Speed Pothole
        {
            "title": "Submerged Expressway Pothole on Super Corridor",
            "issue_type": "pothole",
            "severity": 5,
            "confidence": 0.96,
            "description": "High-speed lane cavity hidden under water sheet near TCS Campus Gate 2 on 6-lane Super Corridor.",
            "safety_risk": "Extreme high-speed rollover risk for cars traveling at 80-100 km/h.",
            "citizen_notes": "Car hit this at 70 km/h this morning and lost suspension.",
            "latitude": 22.7820,
            "longitude": 75.8280,
            "location_name": "Super Corridor (Opposite TCS Campus)",
            "status": "Reported",
            "assigned_department": "IDA (Indore Development Authority)",
            "assigned_worker": "Unassigned",
            "days_ago": 1,
            "image_type": "pothole_crater"
        },
        # Palasia Square - Damaged Storm Drain Grate
        {
            "title": "Broken Cast Iron Manhole Grate",
            "issue_type": "overflowing drain",
            "severity": 4,
            "confidence": 0.95,
            "description": "Cast iron stormwater grating fractured in half, leaving an open 18-inch gap on pedestrian zebra crossing.",
            "safety_risk": "Citizens or children falling straight into 8-foot storm drain chamber; bicycle tire entrapment.",
            "citizen_notes": "A cyclist was rescued by locals yesterday.",
            "latitude": 22.7258,
            "longitude": 75.8893,
            "location_name": "Palasia Square (Near Industry House)",
            "status": "Assigned",
            "assigned_department": "IMC Drainage & Sewerage Dept",
            "assigned_worker": "Er. Arvind Joshi",
            "days_ago": 5,
            "image_type": "overflowing_drain"
        },
        # Khajrana Temple Road - Overflowing Sewer
        {
            "title": "Sewer Line Overflow Near Khajrana Ring Road",
            "issue_type": "overflowing drain",
            "severity": 4,
            "confidence": 0.91,
            "description": "Clogged underground main causing black sewage water to bubble up through roadway inspection manhole.",
            "safety_risk": "Severe airborne pathogens, stench, contamination of nearby commercial sweet shops.",
            "citizen_notes": "Needs jetting vacuum suction machine immediately.",
            "latitude": 22.7302,
            "longitude": 75.9085,
            "location_name": "Khajrana Ganesh Mandir Road",
            "status": "Reported",
            "assigned_department": "IMC Drainage & Sewerage Dept",
            "assigned_worker": "Unassigned",
            "days_ago": 8,
            "image_type": "overflowing_drain"
        },
        # Annapurna Road - Leaning Streetlight Pole
        {
            "title": "Structurally Compromised Leaning Lamp Post",
            "issue_type": "broken streetlight",
            "severity": 4,
            "confidence": 0.92,
            "description": "10-meter steel utility pole tilted at 25-degree angle following minor vehicular collision; base bolts severed.",
            "safety_risk": "Imminent collapse hazard onto sidewalk or passing city bus.",
            "citizen_notes": "Pole is swaying whenever heavy trucks pass.",
            "latitude": 22.6985,
            "longitude": 75.8361,
            "location_name": "Annapurna Road (Near Mandir Gate)",
            "status": "Assigned",
            "assigned_department": "IMC Electrical Engineering Wing",
            "assigned_worker": "Er. Dinesh Rathore",
            "days_ago": 4,
            "image_type": "broken_streetlight"
        },
        # Bengali Square - Damaged Road Asphalt Rupture
        {
            "title": "Severe Asphalt Rutting on Heavy Freight Corridor",
            "issue_type": "damaged road",
            "severity": 4,
            "confidence": 0.90,
            "description": "Bituminous surface shearing with 5-inch deep longitudinal wheel depressions caused by overloaded bypass trucks.",
            "safety_risk": "Two-wheelers losing balance across ruts; emergency vehicles struggling to pass.",
            "citizen_notes": "Heavy vibration shaking roadside residences.",
            "latitude": 22.7135,
            "longitude": 75.9110,
            "location_name": "Bengali Square (Ring Road Junction)",
            "status": "In Progress",
            "assigned_department": "NHAI / IMC Joint PWD Division",
            "assigned_worker": "Er. Vikram Singh",
            "days_ago": 9,
            "image_type": "damaged_road"
        },
        # Geeta Bhawan Square - Streetlight Cable Issue
        {
            "title": "Dead Streetlights on Hospital Access Lane",
            "issue_type": "broken streetlight",
            "severity": 3,
            "confidence": 0.88,
            "description": "Three consecutive street lamps malfunctioning along hospital emergency ambulance entry route.",
            "safety_risk": "Poor nighttime visibility for incoming emergency ambulances and visiting patients.",
            "citizen_notes": "Hospital administration raised formal complaint.",
            "latitude": 22.7169,
            "longitude": 75.8856,
            "location_name": "Geeta Bhawan Square (Hospital Road)",
            "status": "Reported",
            "assigned_department": "IMC Electrical Engineering Wing",
            "assigned_worker": "Unassigned",
            "days_ago": 11,
            "image_type": "broken_streetlight"
        },
        # LIG Colony - Road Crack
        {
            "title": "Longitudinal Road Surface Fracture",
            "issue_type": "damaged road",
            "severity": 2,
            "confidence": 0.87,
            "description": "Early stage thermal cracking along concrete slab joint in residential sector.",
            "safety_risk": "Water ingress will cause severe winter sub-base erosion if not sealed.",
            "citizen_notes": "Noticed after recent utility cable trenching.",
            "latitude": 22.7380,
            "longitude": 75.8920,
            "location_name": "LIG Colony (Sector B Main Road)",
            "status": "Reported",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Unassigned",
            "days_ago": 12,
            "image_type": "damaged_road"
        },
        # Airport Road (Devi Ahilya Airport) - Pothole (Resolved)
        {
            "title": "VIP Transit Corridor Asphalt Repair",
            "issue_type": "pothole",
            "severity": 3,
            "confidence": 0.95,
            "description": "Surface crater on airport approach flyover successfully resurfaced using hot-mix asphalt patching.",
            "safety_risk": "Resolved: Was causing VIP convoy slowdowns and tourist transit delay.",
            "citizen_notes": "Fixed within 24h by IMC rapid action team. Excellent work!",
            "latitude": 22.7275,
            "longitude": 75.8080,
            "location_name": "Airport Road (Kalani Nagar Flyover)",
            "status": "Resolved",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Er. Rajesh Sharma",
            "days_ago": 10,
            "image_type": "pothole_crater"
        },
        # Rau Circle - Damaged Highway Shoulder (Resolved)
        {
            "title": "Highway Shoulder Re-stabilization at Rau",
            "issue_type": "damaged road",
            "severity": 3,
            "confidence": 0.93,
            "description": "Collapsed shoulder edge compacted and stabilized with wet-mix macadam.",
            "safety_risk": "Resolved: Trucks no longer risk overturning when pulling over.",
            "citizen_notes": "Completed and painted with reflective yellow curb line.",
            "latitude": 22.6394,
            "longitude": 75.8038,
            "location_name": "Rau Circle (Mumbai-Agra Bypass)",
            "status": "Resolved",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Er. Vikram Singh",
            "days_ago": 13,
            "image_type": "damaged_road"
        },
        # Malwa Mill Square - Clogged Sump
        {
            "title": "Water Accumulation at Malwa Mill Underpass",
            "issue_type": "overflowing drain",
            "severity": 3,
            "confidence": 0.86,
            "description": "Debris and plastic bags choking rainwater catchment inlets, resulting in 4-inch waterlogging.",
            "safety_risk": "Traffic blockage and small car engine hydro-lock risk.",
            "citizen_notes": "Happens every time it rains even lightly.",
            "latitude": 22.7305,
            "longitude": 75.8715,
            "location_name": "Malwa Mill Square (Underpass)",
            "status": "Reported",
            "assigned_department": "IMC Drainage & Sewerage Dept",
            "assigned_worker": "Unassigned",
            "days_ago": 2,
            "image_type": "overflowing_drain"
        },
        # IT Park Bhanwarkuan - Minor Pothole
        {
            "title": "Software Technology Park Entrance Pothole",
            "issue_type": "pothole",
            "severity": 2,
            "confidence": 0.90,
            "description": "Minor depression formed around water meter chamber cover at tech park gate.",
            "safety_risk": "Bicycle and electric scooter wheel destabilization.",
            "citizen_notes": "Commuters getting splashed during rainy days.",
            "latitude": 22.6830,
            "longitude": 75.8690,
            "location_name": "IT Park Road (Crystal IT Park)",
            "status": "Reported",
            "assigned_department": "IMC Road Works Division",
            "assigned_worker": "Unassigned",
            "days_ago": 5,
            "image_type": "pothole_crater"
        },
        # Sapna Sangeeta Road - Broken Footpath Grating
        {
            "title": "Damaged Storm Drain Siphon at Commercial Complex",
            "issue_type": "overflowing drain",
            "severity": 4,
            "confidence": 0.92,
            "description": "Collapsed pedestrian footpath slab over drainage channel near Sapna Sangeeta multiplex.",
            "safety_risk": "Immediate hazard of pedestrians dropping 5 feet into drainage canal in shopping district.",
            "citizen_notes": "Children and shoppers walk here continuously.",
            "latitude": 22.7050,
            "longitude": 75.8720,
            "location_name": "Sapna Sangeeta Road (Commercial District)",
            "status": "Reported",
            "assigned_department": "IMC Drainage & Sewerage Dept",
            "assigned_worker": "Unassigned",
            "days_ago": 3,
            "image_type": "overflowing_drain"
        }
    ]

    for item in seed_records:
        rep_time = (now - timedelta(days=item["days_ago"], hours=2, minutes=15)).isoformat()
        img_placeholder = _generate_sample_image_uri(item["issue_type"], item["severity"], item["location_name"])

        insert_issue(
            title=item["title"],
            issue_type=item["issue_type"],
            severity=item["severity"],
            confidence=item["confidence"],
            description=item["description"],
            safety_risk=item["safety_risk"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            location_name=item["location_name"],
            citizen_notes=item["citizen_notes"],
            image_path=img_placeholder,
            status=item["status"],
            assigned_department=item["assigned_department"],
            assigned_worker=item["assigned_worker"],
            reported_at=rep_time,
            db_file=db_file
        )


def _generate_sample_image_uri(issue_type: str, severity: int, location: str) -> str:
    """
    Creates an inline SVG Data URI for realistic, high-contrast visual display of defect cards.
    Works 100% offline, requires zero external CDN dependencies, and never breaks.
    """
    colors = {
        "pothole": ("#3B82F6", "#1E3A8A", "🕳️ POTHOLE DEFECT"),
        "damaged road": ("#8B5CF6", "#4C1D95", "🛣️ ROAD DAMAGE"),
        "broken streetlight": ("#F59E0B", "#78350F", "💡 BROKEN STREETLIGHT"),
        "overflowing drain": ("#EC4899", "#831843", "🌊 OVERFLOWING DRAIN"),
        "other": ("#6B7280", "#111827", "⚠️ CIVIC DEFECT")
    }

    accent, bg, label = colors.get(issue_type, colors["other"])

    svg_content = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="600" height="340" viewBox="0 0 600 340">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:{bg};stop-opacity:1" />
                <stop offset="100%" style="stop-color:#0F172A;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="600" height="340" rx="16" fill="url(#grad)" />
        <rect x="20" y="20" width="560" height="40" rx="8" fill="{accent}" opacity="0.25" />
        <text x="35" y="46" font-family="system-ui, sans-serif" font-weight="700" font-size="16" fill="#F8FAFC">
            CIVICPULSE AI INSPECTION CAPTURE
        </text>
        <circle cx="550" cy="40" r="8" fill="#10B981" />
        
        <!-- Defect Graphic Representation -->
        <rect x="50" y="85" width="500" height="150" rx="12" fill="#1E293B" stroke="{accent}" stroke-width="2" />
        <text x="75" y="140" font-family="system-ui, sans-serif" font-size="32" font-weight="800" fill="#F8FAFC">
            {label}
        </text>
        <text x="75" y="175" font-family="system-ui, sans-serif" font-size="18" fill="#94A3B8">
            Location: {location}
        </text>
        <text x="75" y="205" font-family="system-ui, sans-serif" font-size="16" fill="#CBD5E1">
            Severity Level: {severity}/5 | AI Confidence: 94%
        </text>

        <!-- Footer Tag -->
        <rect x="50" y="260" width="140" height="34" rx="17" fill="{accent}" />
        <text x="70" y="282" font-family="system-ui, sans-serif" font-size="13" font-weight="700" fill="#FFFFFF">
            SEV {severity} CRITICAL
        </text>
        
        <text x="210" y="282" font-family="system-ui, sans-serif" font-size="13" fill="#64748B">
            Indore Municipal Smart City Vision Feed
        </text>
    </svg>
    """
    import base64
    b64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"
