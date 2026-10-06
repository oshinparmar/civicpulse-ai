"""
CivicPulse AI - AI-Powered Public Infrastructure Monitoring & Action Engine
Built with Streamlit, Google Gemini Vision 2.5 Flash, SQLite, and Folium.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import io
import time
from datetime import datetime

# Local project imports
import database
import ai_engine
import prioritization
from utils import (
    INDORE_CENTER,
    INDORE_LANDMARKS,
    extract_exif_gps,
    image_to_base64_data_uri,
    haversine_distance_meters
)
from map_component import build_civic_map
from streamlit_folium import st_folium

# Page configuration
st.set_page_config(
    page_title="CivicPulse AI | Smart Infrastructure Monitoring",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Metric Cards */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        color: #0F172A;
        margin-top: 4px;
    }

    /* Priority Badges */
    .badge-high {
        background-color: #FEE2E2;
        color: #DC2626;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-block;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #D97706;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-block;
    }
    .badge-low {
        background-color: #D1FAE5;
        color: #059669;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-block;
    }
    .badge-cluster {
        background-color: #EDE9FE;
        color: #6D28D9;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 11px;
    }

    /* Streamlit button style tweak */
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database and Seed if needed
database.init_db()
database.seed_indore_demo_data()


# ---------------- SIDEBAR NAVIGATION & API KEY ----------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/smart-city.png", width=70)
    st.title("CivicPulse AI")
    st.caption("Smart City Infrastructure Action Engine\nIndore Municipal Corporation (IMC)")
    st.divider()

    # Navigation Menu
    nav_option = st.radio(
        "Navigation",
        [
            "📸 Citizen Report",
            "🏛️ Authority Command Center",
            "🗺️ Live Geospatial Map",
            "📊 Analytics & Insights",
            "🚔 Dashcam / CCTV Simulator",
            "⚙️ Settings & Demo Reset"
        ],
        index=0
    )

    st.divider()

    # Gemini API Key Status
    current_key = ai_engine.get_gemini_api_key()
    if current_key:
        st.success("🟢 **Gemini Vision Connected**", icon="✅")
        st.caption("Using Google Gemini 2.5 Flash")
    else:
        st.warning("🟡 **Demo Simulation Mode Active**")
        st.caption("No API key detected in secrets or environment. Live analysis is running in offline demo simulation mode.")
        manual_key = st.text_input(
            "Enter Gemini API Key (Optional)",
            type="password",
            placeholder="AIzaSy...",
            help="Get your free key from aistudio.google.com"
        )
        if manual_key:
            st.session_state["manual_api_key"] = manual_key
            st.rerun()

    st.divider()
    st.markdown("""
    <div style='font-size: 11px; color: #64748B; line-height: 1.4;'>
        <strong>CivicPulse AI v1.0 MVP</strong><br>
        Built for Hackathon Demo<br>
        City: Indore, Madhya Pradesh
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# TAB 1: CITIZEN REPORT
# ==============================================================================
if nav_option == "📸 Citizen Report":
    st.title("📸 Report an Infrastructure Issue")
    st.write("Upload or capture a photo of a road, streetlight, or drain problem. Our AI will automatically detect the defect, classify severity, check nearby duplicate complaints, and prioritize it for municipal repair.")

    col_img, col_form = st.columns([1.1, 1], gap="large")

    with col_img:
        st.subheader("1. Capture or Upload Defect Image")
        input_method = st.radio("Input Source", ["Upload Photo", "Use Camera"], horizontal=True)

        uploaded_file = None
        if input_method == "Upload Photo":
            uploaded_file = st.file_uploader(
                "Choose an image (JPEG, PNG)",
                type=["jpg", "jpeg", "png"],
                help="You can upload road photos, potholes, overflowing drains, broken lights, etc."
            )
        else:
            uploaded_file = st.camera_input("Take a photo of the defect")

        # Display preview if uploaded
        pil_image = None
        exif_gps = None
        if uploaded_file is not None:
            pil_image = Image.open(uploaded_file)
            st.image(pil_image, caption="Uploaded Image", use_container_width=True)
            exif_gps = extract_exif_gps(pil_image)
            if exif_gps:
                st.info(f"📍 GPS coordinates auto-extracted from photo EXIF: `{exif_gps[0]}, {exif_gps[1]}`")

    with col_form:
        st.subheader("2. Location & Details")

        # Location selector
        location_mode = st.selectbox(
            "Select Locality or Custom Coordinates",
            ["Select prominent Indore Landmark..."] + list(INDORE_LANDMARKS.keys()) + ["Custom Coordinates"]
        )

        default_lat, default_lon = INDORE_CENTER
        if exif_gps:
            default_lat, default_lon = exif_gps
        elif location_mode in INDORE_LANDMARKS:
            default_lat, default_lon = INDORE_LANDMARKS[location_mode]

        loc_cols = st.columns(2)
        with loc_cols[0]:
            lat = st.number_input("Latitude", value=float(default_lat), format="%.6f")
        with loc_cols[1]:
            lon = st.number_input("Longitude", value=float(default_lon), format="%.6f")

        location_name = st.text_input(
            "Address / Landmark Description",
            value=location_mode if location_mode in INDORE_LANDMARKS else "Indore, Madhya Pradesh",
            placeholder="e.g. Near Vijay Nagar BRTS Bus Stop, AB Road"
        )

        citizen_note = st.text_area(
            "Additional Notes (Optional)",
            placeholder="e.g. Water is leaking rapidly; vehicles are skidding at night.",
            height=70
        )

        # AI Inspection trigger
        st.subheader("3. AI Inspection & Prioritization")
        analyze_btn = st.button("🔍 Run AI Vision Analysis", type="primary", use_container_width=True)

        if analyze_btn:
            if pil_image is None:
                st.error("Please upload or capture an image first!")
            else:
                with st.spinner("AI analyzing image with Gemini Vision..."):
                    manual_k = st.session_state.get("manual_api_key", None)
                    filename = getattr(uploaded_file, "name", "capture.jpg")
                    analysis = ai_engine.analyze_infrastructure_image(
                        image=pil_image,
                        manual_api_key=manual_k,
                        image_filename=filename
                    )
                    st.session_state["last_analysis"] = analysis
                    st.session_state["last_image"] = pil_image
                    st.session_state["last_lat"] = lat
                    st.session_state["last_lon"] = lon
                    st.session_state["last_loc_name"] = location_name
                    st.session_state["last_note"] = citizen_note

    # Display AI Analysis Card if available in session
    if "last_analysis" in st.session_state:
        res = st.session_state["last_analysis"]

        st.divider()
        st.subheader("🤖 AI Diagnostic & Prioritization Card")

        if not res.get("is_valid_infrastructure_issue", True):
            st.error(f"⚠️ **Invalid Image Detected**: {res.get('rejection_reason', 'Image does not appear to show public municipal infrastructure.')}")
            st.info("CivicPulse AI filters out irrelevant uploads (selfies, food, indoor rooms) to keep municipal dispatch queues clean.")
        else:
            # Query existing reports to calculate real-time spatial clustering
            all_reps = database.get_all_issues()
            rep_lat = st.session_state["last_lat"]
            rep_lon = st.session_state["last_lon"]
            rep_type = res["issue_type"]

            cluster_count = prioritization.calculate_cluster_duplicates(
                rep_lat, rep_lon, rep_type, all_reps, radius_meters=50.0
            )

            prio = prioritization.compute_priority_score(
                severity=res["severity"],
                issue_type=rep_type,
                duplicate_count=cluster_count,
                reported_at_iso=datetime.now().isoformat()
            )

            # Analysis Display Cards
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Detected Issue</div>
                    <div style="font-size:20px; font-weight:700; color:#0284C7; margin-top:6px;">
                        {res['issue_type'].title()}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                sev_color = "#DC2626" if res['severity'] >= 4 else ("#D97706" if res['severity'] == 3 else "#059669")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Severity Rating</div>
                    <div style="font-size:22px; font-weight:800; color:{sev_color}; margin-top:6px;">
                        Level {res['severity']} / 5
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">AI Confidence</div>
                    <div style="font-size:22px; font-weight:800; color:#1E293B; margin-top:6px;">
                        {int(res['confidence'] * 100)}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c4:
                badge_class = f"badge-{prio['priority_level'].lower()}"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Priority Score</div>
                    <div style="font-size:24px; font-weight:800; color:{prio['badge_color']}; margin-top:4px;">
                        {prio['priority_score']}/100
                    </div>
                    <span class="{badge_class}">{prio['priority_level']} Priority</span>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            col_desc, col_risk = st.columns(2)
            with col_desc:
                st.markdown(f"**📝 AI Description:** {res['short_description']}")
                st.caption(f"Engine: `{res.get('mode', 'live_gemini')}`")
            with col_risk:
                st.markdown(f"**⚠️ Safety Hazard Assessment:** {res['safety_risk_reason']}")
                st.caption(f"Action SLA: {prio['action_sla']}")

            # Cluster Warning Banner
            if cluster_count > 0:
                st.warning(f"🚨 **Spatial Cluster Detected:** There are already **{cluster_count} active reports** of type `{res['issue_type']}` within 50 meters of this location. These reports have been grouped together, bumping this issue's urgency score (+{prio['breakdown']['cluster_pts']} pts)!", icon="📍")

            # Final Submission
            st.write("")
            if st.button("🚀 Confirm & Submit to Municipal Dispatch", type="primary", use_container_width=True):
                base64_img = image_to_base64_data_uri(st.session_state["last_image"])
                new_id = database.insert_issue(
                    title=f"{res['issue_type'].title()} at {st.session_state['last_loc_name'][:30]}",
                    issue_type=res["issue_type"],
                    severity=res["severity"],
                    confidence=res["confidence"],
                    description=res["short_description"],
                    safety_risk=res["safety_risk_reason"],
                    latitude=st.session_state["last_lat"],
                    longitude=st.session_state["last_lon"],
                    location_name=st.session_state["last_loc_name"],
                    citizen_notes=st.session_state["last_note"],
                    image_path=base64_img,
                    status="Reported"
                )
                st.success(f"🎉 **Report Submitted Successfully!** Tracking ID: `CP-IND-{new_id:04d}` has been routed to the Municipal Control Center.")
                st.balloons()
                del st.session_state["last_analysis"]


# ==============================================================================
# TAB 2: AUTHORITY COMMAND CENTER
# ==============================================================================
elif nav_option == "🏛️ Authority Command Center":
    st.title("🏛️ Municipal Authority Command Center")
    st.write("Prioritized queue of citizen and patrol reported infrastructure defects for Indore Municipal Corporation.")

    # KPI Banner
    kpis = database.get_summary_kpis()
    kp1, kp2, kp3, kp4, kp5 = st.columns(5)
    with kp1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Total Issues</div><div class="metric-value">{kpis['total']}</div></div>""", unsafe_allow_html=True)
    with kp2:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Pending Action</div><div class="metric-value" style="color:#D97706;">{kpis['reported']}</div></div>""", unsafe_allow_html=True)
    with kp3:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Critical (High)</div><div class="metric-value" style="color:#DC2626;">{kpis['high_critical']}</div></div>""", unsafe_allow_html=True)
    with kp4:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">In Progress</div><div class="metric-value" style="color:#2563EB;">{kpis['in_progress']}</div></div>""", unsafe_allow_html=True)
    with kp5:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Resolved</div><div class="metric-value" style="color:#059669;">{kpis['resolved']}</div></div>""", unsafe_allow_html=True)

    st.write("")

    # Filter Controls
    with st.expander("🔍 Filter & Search Options", expanded=True):
        f_cols = st.columns([1, 1, 1, 1.5])
        with f_cols[0]:
            f_status = st.selectbox("Status", ["All", "Reported", "Assigned", "In Progress", "Resolved"])
        with f_cols[1]:
            f_type = st.selectbox("Issue Type", ["All", "pothole", "damaged road", "broken streetlight", "overflowing drain", "other"])
        with f_cols[2]:
            f_prio = st.selectbox("Priority Level", ["All", "High", "Medium", "Low"])
        with f_cols[3]:
            f_search = st.text_input("Search", placeholder="Search by Landmark, ID, or Title...")

    issues = database.get_all_issues(
        status_filter=f_status,
        type_filter=f_type,
        priority_filter=f_prio,
        search_query=f_search
    )

    if not issues:
        st.info("No issues found matching the selected filter criteria.")
    else:
        # Split Layout: Left Table / Right Issue Details Inspector
        col_list, col_detail = st.columns([1.2, 1], gap="medium")

        with col_list:
            st.subheader(f"Priority Dispatch Queue ({len(issues)} issues)")
            
            # Format dataframe for display
            df_rows = []
            for item in issues:
                cluster_label = f"🚨 {item['cluster_count']} nearby" if item['cluster_count'] > 0 else "-"
                df_rows.append({
                    "ID": item["id"],
                    "Tracking ID": item["tracking_id"],
                    "Score": item["priority_score"],
                    "Priority": item["priority_level"],
                    "Type": item["issue_type"].title(),
                    "Location": item["location_name"][:25] + "...",
                    "Status": item["status"],
                    "Clusters": cluster_label
                })
            df = pd.DataFrame(df_rows)

            # Interactive Issue Selector
            selected_tracking = st.selectbox(
                "Select Issue to Inspect & Update Status:",
                options=[i["tracking_id"] for i in issues],
                format_func=lambda x: f"{x} - {next((i['title'] for i in issues if i['tracking_id'] == x), '')} (Score: {next((i['priority_score'] for i in issues if i['tracking_id'] == x), '')})"
            )

            # Display table
            st.dataframe(
                df[["Tracking ID", "Score", "Priority", "Type", "Location", "Status", "Clusters"]],
                use_container_width=True,
                height=420,
                hide_index=True
            )

        # Selected Issue Details & Action Inspector
        with col_detail:
            selected_issue = next((i for i in issues if i["tracking_id"] == selected_tracking), issues[0])
            st.subheader(f"📋 Inspection: {selected_issue['tracking_id']}")

            # Priority & Status Header
            b_class = f"badge-{selected_issue['priority_level'].lower()}"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="{b_class}">Priority: {selected_issue['priority_level']} (Score: {selected_issue['priority_score']}/100)</span>
                <span style="font-weight:700; color:#475569;">Status: <strong>{selected_issue['status']}</strong></span>
            </div>
            """, unsafe_allow_html=True)

            # Issue image
            if selected_issue.get("image_path"):
                st.image(selected_issue["image_path"], use_container_width=True)

            st.markdown(f"**Title:** {selected_issue['title']}")
            st.markdown(f"**📍 Location:** {selected_issue['location_name']}")
            st.markdown(f"**Description:** {selected_issue['description']}")
            st.markdown(f"**⚠️ Safety Risk:** {selected_issue['safety_risk']}")
            
            if selected_issue.get("citizen_notes"):
                st.markdown(f"**🗣️ Citizen Note:** *\"{selected_issue['citizen_notes']}\"*")

            if selected_issue.get("cluster_count", 0) > 0:
                st.info(f"🚨 **Spatial Cluster:** {selected_issue['cluster_count']} duplicate reports of `{selected_issue['issue_type']}` found within 50m radius.")

            # Status Update Workflow
            st.divider()
            st.markdown("#### 🛠️ Update Status & Assign Crew")
            with st.form(f"update_form_{selected_issue['id']}"):
                new_status = st.selectbox(
                    "Workflow Stage",
                    ["Reported", "Assigned", "In Progress", "Resolved"],
                    index=["Reported", "Assigned", "In Progress", "Resolved"].index(selected_issue["status"])
                )
                
                dept_options = [
                    "IMC Road Works Division",
                    "IMC Drainage & Sewerage Dept",
                    "IMC Electrical Engineering Wing",
                    "Smart City Heritage Infrastructure Cell",
                    "NHAI / IMC Joint PWD Division",
                    "IDA (Indore Development Authority)"
                ]
                default_dept_idx = 0
                if selected_issue["assigned_department"] in dept_options:
                    default_dept_idx = dept_options.index(selected_issue["assigned_department"])

                dept = st.selectbox("Assigned Department", dept_options, index=default_dept_idx)
                worker = st.text_input("Assigned Field Officer / Contractor", value=selected_issue["assigned_worker"] or "Er. Rajesh Sharma")
                res_notes = st.text_area("Resolution / Action Notes", value=selected_issue["resolution_notes"] or "", placeholder="Details on patching material, crew dispatched, or completion date.")

                submitted = st.form_submit_button("💾 Save & Update Workflow", type="primary", use_container_width=True)
                if submitted:
                    success = database.update_issue_status(
                        issue_id=selected_issue["id"],
                        new_status=new_status,
                        assigned_department=dept,
                        assigned_worker=worker,
                        resolution_notes=res_notes
                    )
                    if success:
                        st.success(f"Issue {selected_issue['tracking_id']} updated to **{new_status}**!")
                        time.sleep(0.5)
                        st.rerun()


# ==============================================================================
# TAB 3: GEOSPATIAL MAP VIEW
# ==============================================================================
elif nav_option == "🗺️ Live Geospatial Map":
    st.title("🗺️ Live Geospatial Infrastructure Map")
    st.write("Real-time GIS map of infrastructure defects across Indore with spatial clustering and heat density layers.")

    issues = database.get_all_issues()

    # Map Controls
    m_col1, m_col2, m_col3 = st.columns([1, 1, 2])
    with m_col1:
        enable_heatmap = st.checkbox("🔥 Show Defect HeatMap Density", value=False)
    with m_col2:
        enable_cluster_circles = st.checkbox("⭕ Show 50m Spatial Cluster Radii", value=True)
    with m_col3:
        status_filter_map = st.multiselect(
            "Filter Status on Map",
            ["Reported", "Assigned", "In Progress", "Resolved"],
            default=["Reported", "Assigned", "In Progress"]
        )

    filtered_for_map = [i for i in issues if i["status"] in status_filter_map] if status_filter_map else issues

    # Map Legend Banner
    st.markdown("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; padding:10px 16px; border-radius:8px; margin-bottom:12px; font-size:12px; display:flex; gap:20px; align-items:center;">
        <strong>Map Legend:</strong>
        <span>🔴 <span style="font-weight:700; color:#EF4444;">High Priority (Score ≥ 70)</span></span>
        <span>🟠 <span style="font-weight:700; color:#F59E0B;">Medium Priority (45-69)</span></span>
        <span>🟢 <span style="font-weight:700; color:#10B981;">Low Priority (< 45)</span></span>
        <span>🔘 <span style="font-weight:700; color:#64748B;">Resolved Issue</span></span>
        <span>⭕ <span style="font-weight:600; color:#DC2626;">50m Duplicate Cluster Zone</span></span>
    </div>
    """, unsafe_allow_html=True)

    # Render Map
    folium_map = build_civic_map(
        issues=filtered_for_map,
        center_coords=INDORE_CENTER,
        zoom_start=13,
        show_heatmap=enable_heatmap,
        show_cluster_radii=enable_cluster_circles
    )

    st_folium(folium_map, width="100%", height=560, returned_objects=[])


# ==============================================================================
# TAB 4: ANALYTICS & INSIGHTS
# ==============================================================================
elif nav_option == "📊 Analytics & Insights":
    st.title("📊 Municipal Analytics & Operational Insights")
    st.write("Actionable analytics for municipal commissioners, zonal officers, and urban planners.")

    issues = database.get_all_issues()
    if not issues:
        st.warning("No data available to generate analytics.")
    else:
        df = pd.DataFrame(issues)

        # Downloadable CSV report (core requirement / bonus)
        csv_data = df.drop(columns=["image_path"], errors="ignore").to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Municipal Infrastructure Incident Report (CSV)",
            data=csv_data,
            file_name=f"civicpulse_indore_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )
        st.write("")

        # Visual Charts
        c_row1_1, c_row1_2 = st.columns(2)

        with c_row1_1:
            st.subheader("📌 Issues by Defect Category")
            type_counts = df["issue_type"].value_counts().reset_index()
            type_counts.columns = ["Issue Type", "Count"]
            type_counts["Issue Type"] = type_counts["Issue Type"].str.title()
            fig_type = px.pie(
                type_counts,
                values="Count",
                names="Issue Type",
                hole=0.45,
                color_discrete_sequence=["#0284C7", "#F59E0B", "#EF4444", "#10B981", "#8B5CF6"]
            )
            fig_type.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_type, use_container_width=True)

        with c_row1_2:
            st.subheader("⚡ Priority Distribution")
            prio_counts = df["priority_level"].value_counts().reset_index()
            prio_counts.columns = ["Priority Level", "Count"]
            color_map = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"}
            fig_prio = px.bar(
                prio_counts,
                x="Priority Level",
                y="Count",
                color="Priority Level",
                color_discrete_map=color_map,
                text="Count"
            )
            fig_prio.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig_prio, use_container_width=True)

        c_row2_1, c_row2_2 = st.columns(2)

        with c_row2_1:
            st.subheader("📍 Top Hotspot Localities")
            loc_counts = df["location_name"].apply(lambda x: x.split("(")[0].strip()).value_counts().head(8).reset_index()
            loc_counts.columns = ["Locality", "Issues Reported"]
            fig_loc = px.bar(
                loc_counts,
                x="Issues Reported",
                y="Locality",
                orientation="h",
                color_discrete_sequence=["#0284C7"],
                text="Issues Reported"
            )
            fig_loc.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_loc, use_container_width=True)

        with c_row2_2:
            st.subheader("🔄 Workflow Resolution Funnel")
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            status_order = ["Reported", "Assigned", "In Progress", "Resolved"]
            status_counts["Status"] = pd.Categorical(status_counts["Status"], categories=status_order, ordered=True)
            status_counts = status_counts.sort_values("Status")
            fig_status = px.bar(
                status_counts,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_map={
                    "Reported": "#D97706",
                    "Assigned": "#2563EB",
                    "In Progress": "#6366F1",
                    "Resolved": "#059669"
                },
                text="Count"
            )
            fig_status.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)


# ==============================================================================
# TAB 5: PATROL / DASHCAM SIMULATOR (BONUS)
# ==============================================================================
elif nav_option == "🚔 Dashcam / CCTV Simulator":
    st.title("🚔 Automated CCTV & Dashcam Patrol Simulator")
    st.write("Simulate municipal inspection vehicles equipped with road-facing cameras or fixed CCTV feeds that automatically scan city streets and log defects.")

    st.info("💡 **Hackathon Feature**: Demonstrates how CivicPulse AI transitions from reactive citizen complaints to proactive, automated municipal surveillance.")

    col_sim_btn, col_bulk = st.columns([1, 1], gap="large")

    with col_sim_btn:
        st.subheader("1. Run Virtual Patrol Inspection")
        st.write("Simulate a municipal patrol vehicle driving along the **Vijay Nagar - AB Road Corridor** in Indore.")
        
        corridor = st.selectbox(
            "Select Patrol Route",
            ["AB Road - Vijay Nagar to Palasia Corridor", "Super Corridor Expressway", "Bypass Ring Road"]
        )

        if st.button("🚀 Start Automated Vehicle Patrol", type="primary", use_container_width=True):
            patrol_progress = st.progress(0, text="Initializing vehicle onboard camera stream...")
            
            # Simulated frames captured during patrol
            simulated_frames = [
                {
                    "frame_id": "FRAME-01",
                    "km": "KM 2.4",
                    "issue_type": "pothole",
                    "title": "AB Road Median Pothole",
                    "severity": 4,
                    "confidence": 0.95,
                    "desc": "Autonomous detection: 20-inch asphalt cavity in fast lane.",
                    "risk": "Vehicular tire blowout risk at 60 km/h.",
                    "lat": 22.7540,
                    "lon": 75.8942,
                    "loc": "AB Road near Vijay Nagar (Patrol KM 2.4)"
                },
                {
                    "frame_id": "FRAME-02",
                    "km": "KM 3.8",
                    "issue_type": "broken streetlight",
                    "title": "Malfunctioning Streetlight Post #42",
                    "severity": 3,
                    "confidence": 0.91,
                    "desc": "Camera detected dark zone and damaged luminaire fixture.",
                    "risk": "Low visibility for pedestrian zebra crossing at night.",
                    "lat": 22.7410,
                    "lon": 75.8925,
                    "loc": "AB Road LIG Intersection (Patrol KM 3.8)"
                },
                {
                    "frame_id": "FRAME-03",
                    "km": "KM 5.1",
                    "issue_type": "overflowing drain",
                    "title": "Roadside Storm Drain Overflow",
                    "severity": 4,
                    "confidence": 0.94,
                    "desc": "Greywater flooding 1.5m of left curb carriageway.",
                    "risk": "Hydroplaning danger and sub-base softening.",
                    "lat": 22.7290,
                    "lon": 75.8900,
                    "loc": "Palasia Approach Road (Patrol KM 5.1)"
                }
            ]

            results_container = st.container()

            for idx, frame in enumerate(simulated_frames):
                time.sleep(0.6)
                patrol_progress.progress((idx + 1) * 33, text=f"Scanning Route... Analyzing {frame['frame_id']} at {frame['km']}")

                # Insert into DB
                img_uri = database._generate_sample_image_uri(frame["issue_type"], frame["severity"], frame["loc"])
                new_id = database.insert_issue(
                    title=f"[PATROL] {frame['title']}",
                    issue_type=frame["issue_type"],
                    severity=frame["severity"],
                    confidence=frame["confidence"],
                    description=frame["desc"],
                    safety_risk=frame["risk"],
                    latitude=frame["lat"],
                    longitude=frame["lon"],
                    location_name=frame["loc"],
                    citizen_notes="Automated Dashcam Patrol Detection",
                    image_path=img_uri,
                    status="Reported",
                    assigned_department="IMC Road Works Division"
                )

            patrol_progress.progress(100, text="Patrol Route Completed! 3 defects detected and logged.")
            st.success("✅ **Patrol Finished:** 3 new defects detected, scored, and added to the municipal queue!")
            st.balloons()

    with col_bulk:
        st.subheader("2. Bulk CCTV Frame Ingestion")
        st.write("Upload a batch of dashcam or CCTV frames for bulk classification.")
        bulk_files = st.file_uploader(
            "Drop multiple road inspection images",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )

        if bulk_files:
            st.write(f"📁 **{len(bulk_files)} images staged for ingestion**")
            if st.button("⚡ Process All Frames with Gemini AI", type="secondary", use_container_width=True):
                prog = st.progress(0)
                for b_idx, b_file in enumerate(bulk_files):
                    img = Image.open(b_file)
                    b_uri = image_to_base64_data_uri(img)
                    analysis = ai_engine.analyze_infrastructure_image(
                        img,
                        manual_api_key=st.session_state.get("manual_api_key"),
                        image_filename=b_file.name
                    )
                    if analysis.get("is_valid_infrastructure_issue", True):
                        database.insert_issue(
                            title=f"[Bulk] {analysis['issue_type'].title()} - {b_file.name[:15]}",
                            issue_type=analysis["issue_type"],
                            severity=analysis["severity"],
                            confidence=analysis["confidence"],
                            description=analysis["short_description"],
                            safety_risk=analysis["safety_risk_reason"],
                            latitude=INDORE_CENTER[0] + (b_idx * 0.003),
                            longitude=INDORE_CENTER[1] + (b_idx * 0.003),
                            location_name="Indore Road Network",
                            citizen_notes="Bulk CCTV Upload",
                            image_path=b_uri
                        )
                    prog.progress((b_idx + 1) / len(bulk_files))
                st.success(f"Processed {len(bulk_files)} images successfully!")


# ==============================================================================
# TAB 6: SETTINGS & DEMO RESET
# ==============================================================================
elif nav_option == "⚙️ Settings & Demo Reset":
    st.title("⚙️ System Settings & Demo Reset")
    st.write("Manage application state, re-seed demo data, and inspect API configuration.")

    c_s1, c_s2 = st.columns(2, gap="large")

    with c_s1:
        st.subheader("🔄 Re-seed Indore Demo Data")
        st.write("Reset the SQLite database back to the pristine 18 realistic Indore infrastructure issues.")
        st.caption("Includes famous Indore landmarks (Vijay Nagar, Rajwada, 56 Dukan, Super Corridor), 50m spatial clusters, and various workflow statuses.")
        
        if st.button("🌱 Reset to Default 18 Demo Reports", type="primary"):
            database.seed_indore_demo_data(force=True)
            st.success("✅ Database re-seeded with 18 realistic Indore reports!")
            time.sleep(0.5)
            st.rerun()

        st.divider()
        st.subheader("🗑️ Wipe Database")
        if st.button("⚠️ Clear All Reports", type="secondary"):
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM issues")
            conn.commit()
            conn.close()
            st.warning("All records wiped. Click 'Reset to Default 18 Demo Reports' above to reload demo data.")
            time.sleep(0.5)
            st.rerun()

    with c_s2:
        st.subheader("🔑 Gemini Vision API Configuration")
        active_key = ai_engine.get_gemini_api_key(st.session_state.get("manual_api_key"))
        
        if active_key:
            masked = active_key[:6] + "..." + active_key[-4:]
            st.success(f"**API Key Configured:** `{masked}`")
            st.write("Model: `Google Gemini 2.5 Flash` (Multimodal Vision)")
        else:
            st.warning("**No API Key Configured (Running in Demo Fallback Mode)**")
            st.write("In Demo Fallback Mode, the AI analyzer uses simulated municipal heuristics so you can pitch your project without worrying about API errors.")

        st.markdown("""
        #### How to set your Gemini API Key:
        1. Visit **[Google AI Studio](https://aistudio.google.com/)** and click **Get API key**.
        2. Create a free API key (takes 10 seconds).
        3. Option A (Local): Create a `.env` file with `GEMINI_API_KEY=your_key` or paste it in the sidebar.
        4. Option B (Streamlit Cloud): In your app settings on share.streamlit.io, open **Secrets** and add:
           ```toml
           GEMINI_API_KEY = "your_actual_api_key_here"
           ```
        """)
