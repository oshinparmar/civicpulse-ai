"""
CivicPulse AI - Geospatial Map Component
Renders interactive Folium maps with:
- Color-coded priority pins (Red=High, Orange=Medium, Green=Low, Slate=Resolved)
- Custom HTML Popups with defect previews, safety risks, and cluster metrics
- 50-meter spatial cluster circle indicators
- Heatmap density layer toggle
"""

from typing import List, Dict, Any, Optional
import folium
from folium.plugins import HeatMap, MarkerCluster
from utils import INDORE_CENTER

# Priority color mapping
PRIORITY_COLORS = {
    "High": "#EF4444",      # Red
    "Medium": "#F59E0B",    # Orange
    "Low": "#10B981",       # Green
    "Resolved": "#64748B"   # Slate Blue
}

TYPE_ICONS = {
    "pothole": "road",
    "damaged road": "exclamation-triangle",
    "broken streetlight": "lightbulb-o",
    "overflowing drain": "tint",
    "other": "info-circle"
}


def build_civic_map(
    issues: List[Dict[str, Any]],
    center_coords: tuple = INDORE_CENTER,
    zoom_start: int = 13,
    show_heatmap: bool = False,
    show_cluster_radii: bool = True,
    selected_issue_id: Optional[int] = None
) -> folium.Map:
    """
    Constructs a Folium map loaded with municipal infrastructure issue pins.
    """
    m = folium.Map(
        location=list(center_coords),
        zoom_start=zoom_start,
        tiles="CartoDB positron",
        control_scale=True
    )

    # HeatMap Layer (if enabled)
    if show_heatmap and issues:
        heat_data = [
            [float(i["latitude"]), float(i["longitude"]), float(i["priority_score"]) / 100.0]
            for i in issues
        ]
        HeatMap(
            heat_data,
            radius=28,
            blur=18,
            min_opacity=0.35,
            gradient={0.2: "#3B82F6", 0.5: "#F59E0B", 0.8: "#EF4444", 1.0: "#991B1B"}
        ).add_to(m)

    # Add markers for each issue
    for item in issues:
        lat = float(item["latitude"])
        lon = float(item["longitude"])
        status = item.get("status", "Reported")
        priority_level = item.get("priority_level", "Medium")

        # Color logic
        if status == "Resolved":
            marker_color = "#64748B"
            pin_icon = "check"
        else:
            marker_color = PRIORITY_COLORS.get(priority_level, "#F59E0B")
            pin_icon = TYPE_ICONS.get(item.get("issue_type", "other"), "info-circle")

        is_selected = (selected_issue_id and item["id"] == selected_issue_id)

        # Highlight selected issue with a pulsating ring or outer circle
        if is_selected:
            folium.CircleMarker(
                location=[lat, lon],
                radius=18,
                color="#0284C7",
                weight=3,
                fill=True,
                fill_color="#0284C7",
                fill_opacity=0.25
            ).add_to(m)

        # Draw 50m cluster circle if duplicates exist
        cluster_count = item.get("cluster_count", 0)
        if show_cluster_radii and cluster_count > 0 and status != "Resolved":
            folium.Circle(
                location=[lat, lon],
                radius=50,
                color="#EF4444",
                weight=1,
                dash_array="4, 4",
                fill=True,
                fill_color="#EF4444",
                fill_opacity=0.10,
                tooltip=f"Spatial Cluster: {cluster_count} duplicate reports within 50m"
            ).add_to(m)

        # HTML popup card
        cluster_badge = ""
        if cluster_count > 0 and status != "Resolved":
            cluster_badge = f"""
            <div style="background:#FEE2E2; color:#B91C1C; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:600; margin-top:4px; display:inline-block;">
                🚨 {cluster_count} Nearby Reports Grouped
            </div>
            """

        status_badge_bg = {
            "Reported": "#FEF3C7; color:#92400E;",
            "Assigned": "#DBEAFE; color:#1E40AF;",
            "In Progress": "#E0E7FF; color:#3730A3;",
            "Resolved": "#D1FAE5; color:#065F46;"
        }.get(status, "#F3F4F6; color:#374151;")

        popup_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width:260px; padding:4px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-weight:700; color:#0F172A; font-size:13px;">{item['tracking_id']}</span>
                <span style="background:{status_badge_bg} padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700;">
                    {status}
                </span>
            </div>
            <div style="font-weight:700; font-size:14px; color:#1E293B; margin-bottom:4px;">
                {item['title']}
            </div>
            <div style="font-size:12px; color:#64748B; margin-bottom:6px;">
                📍 {item['location_name']}
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:6px; margin-bottom:6px; font-size:11px;">
                <div><strong>Type:</strong> {item['issue_type'].title()} | <strong>Severity:</strong> {item['severity']}/5</div>
                <div><strong>Priority Score:</strong> <span style="color:{marker_color}; font-weight:800;">{item['priority_score']} ({priority_level})</span></div>
            </div>
            <div style="font-size:11px; color:#475569; line-height:1.3; margin-bottom:4px;">
                <strong>Safety Risk:</strong> {item['safety_risk'][:110]}...
            </div>
            {cluster_badge}
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{item['tracking_id']} - {item['title']} (Score: {item['priority_score']})",
            icon=folium.Icon(color="red" if priority_level == "High" and status != "Resolved" else ("orange" if priority_level == "Medium" and status != "Resolved" else ("green" if priority_level == "Low" and status != "Resolved" else "gray")), icon=pin_icon, prefix="fa")
        ).add_to(m)

    return m
