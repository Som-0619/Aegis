"""
Streamlit Web Frontend for the Aegis Project Health Reporting Agent.
Provides interactive interfaces for:
- Uploading weekly updates (PDF, DOCX, CSV, TXT, MD) and executing the health audit.
- Visualizing health scores breakdown (Plotly), executive summaries, reasoning, and recommendations.
- Aggregating historical reports for portfolio trend analysis.
- Downloading JSON data, Markdown reports, PDF-ready text, and PPTX slide presentations.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Initialize Agent components
from agents.weekly_report_generator import WeeklyReportGenerator
from agents.portfolio_analyzer import PortfolioAnalyzer
from agents.ppt_generator import PortfolioPPTGenerator
from utils.helper_functions import get_status_color

# Page Configuration
st.set_page_config(
    page_title="Aegis - AI Project Health Auditor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Injection
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Apply modern typography */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Glassmorphic Metric Cards */
.metric-card {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease-in-out;
}

.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px 0 rgba(100, 116, 139, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Header Gradient */
.header-gradient {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.8rem;
    margin-bottom: 5px;
}

/* Status Badges */
.status-badge {
    padding: 6px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
    display: inline-block;
    text-align: center;
}
.status-green {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
}
.status-yellow {
    background-color: rgba(234, 179, 8, 0.15);
    color: #eab308;
    border: 1px solid rgba(234, 179, 8, 0.3);
}
.status-red {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# App Logo / Title
st.markdown('<h1 class="header-gradient">🛡️ Aegis Project Intelligence</h1>', unsafe_allow_html=True)
st.caption("Enterprise Health Auditor & Portfolio Trend Analytics Agent")

# Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/gradient/100/shield.png", width=60)
    st.subheader("Aegis Navigation")
    active_tab = st.radio("Navigation Menu", ["📊 Health Overview", "📝 Weekly Audit", "📈 Portfolio Trends", "📂 Document Hub"])
    
    st.divider()
    st.markdown("### Agent Configuration")
    model_name = st.selectbox("LLM Reasoner Engine", ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o"])
    
    st.caption("Security Context: **Public Sandbox** (No Auth)")
    st.caption("System Status: **Ready** 🟢")

# ----------------------------------------------------
# TAB 1: HEALTH OVERVIEW
# ----------------------------------------------------
if active_tab == "📊 Health Overview":
    st.subheader("Enterprise Health Scoreboard")
    
    # KPI metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            '<div class="metric-card">'
            '<h5>Monitored Projects</h5>'
            '<h2 style="color: #6366f1; margin: 0;">3</h2>'
            '<span style="color: #22c55e; font-size: 0.85rem;">Active Tracking</span>'
            '</div>', unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            '<div class="metric-card">'
            '<h5>Average RAG Score</h5>'
            '<h2 style="color: #eab308; margin: 0;">82.3 <span style="font-size:1.1rem;">/100</span></h2>'
            '<span class="status-badge status-yellow">Yellow Threshold</span>'
            '</div>', unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            '<div class="metric-card">'
            '<h5>Critical Risks</h5>'
            '<h2 style="color: #ef4444; margin: 0;">1</h2>'
            '<span style="color: #ef4444; font-size: 0.85rem;">Requires Attention</span>'
            '</div>', unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            '<div class="metric-card">'
            '<h5>System Confidence</h5>'
            '<h2 style="color: #22c55e; margin: 0;">96.8%</h2>'
            '<span class="status-badge status-green">High Quality Data</span>'
            '</div>', unsafe_allow_html=True
        )

    st.markdown("### Portfolio Performance Score Trend")
    
    # Plotly Trend Chart
    dates = ["Wk-22", "Wk-23", "Wk-24", "Wk-25", "Current"]
    df_trends = pd.DataFrame({
        "Week": dates * 3,
        "Project": ["Project Alpha"] * 5 + ["Project Beta"] * 5 + ["OmniChannel Launch"] * 5,
        "Health Score": [92, 90, 89, 88, 87.5, 78, 80, 81, 85, 84, 62, 60, 58, 59, 75]
    })
    
    fig = px.line(
        df_trends, 
        x="Week", 
        y="Health Score", 
        color="Project", 
        markers=True,
        color_discrete_sequence=["#6366f1", "#a855f7", "#ec4899"],
        title="Project Health Trends over Time"
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="Outfit",
        yaxis_range=[0, 105]
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed status list
    st.markdown("### Active Status Summaries")
    details_col1, details_col2 = st.columns(2)
    with details_col1:
        st.write("**Project Alpha**")
        st.markdown('Status: <span class="status-badge status-yellow">YELLOW (87.5/100)</span>', unsafe_allow_html=True)
        st.markdown("- **Schedule**: Yellow (minor delays in design updates)\n- **Financial**: Green (within bounds)\n- **Risks**: Medium")
    with details_col2:
        st.write("**Project Beta**")
        st.markdown('Status: <span class="status-badge status-green">GREEN (92.0/100)</span>', unsafe_allow_html=True)
        st.markdown("- **Schedule**: Green (milestones achieved)\n- **Financial**: Green (on track)\n- **Risks**: Low")

# ----------------------------------------------------
# TAB 2: WEEKLY AUDIT
# ----------------------------------------------------
elif active_tab == "📝 Weekly Audit":
    st.subheader("Compile Weekly Health Audit")
    st.write("Upload a project plan or status report file (PDF, DOCX, CSV, TXT, MD) to run the Aegis extraction and scoring pipelines.")
    
    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload Weekly Progress Update Document", 
        type=["txt", "md", "pdf", "docx", "csv", "xlsx", "xls"],
        help="Select a file containing raw weekly progress updates (TXT, MD, PDF, DOCX, CSV, or Excel)."
    )
    
    if st.button("🚀 Run Health Audit Pipeline", use_container_width=True):
        if uploaded_file is not None:
            # Save temporary input file
            temp_dir = "data/input"
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            with st.spinner("Extracting parameters and calculating scores..."):
                try:
                    generator = WeeklyReportGenerator(model_name=model_name)
                    result = generator.run_pipeline(temp_path)
                    
                    st.success(f"Audit completed successfully for **{result['project_name']}**.")
                    
                    # Highlight Scoreboard
                    score_col1, score_col2, score_col3, score_col4 = st.columns(4)
                    with score_col1:
                        st.metric("Overall Score", f"{result['overall_score']}/100")
                    with score_col2:
                        badge_color = "status-green" if result["overall_status"] == "GREEN" else "status-yellow" if result["overall_status"] == "YELLOW" else "status-red"
                        st.markdown(
                            f"<h5>RAG Status</h5>"
                            f'<span class="status-badge {badge_color}">{result["overall_status"]}</span>',
                            unsafe_allow_html=True
                        )
                    with score_col3:
                        st.metric("AI Confidence Score", f"{result['confidence_score']}%")
                    with score_col4:
                        st.metric("QA Faithfulness Score", f"{int(result['qa_score'] * 100)}%")
                        
                    # Category Scores Graph
                    scores_data = result["scores"]
                    df_scores = pd.DataFrame({
                        "Category": [c.capitalize() for c in scores_data.keys()],
                        "Score": list(scores_data.values())
                    })
                    
                    fig_bar = px.bar(
                        df_scores,
                        x="Category",
                        y="Score",
                        color="Category",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        title="Metric Scores Breakdown"
                    )
                    fig_bar.update_layout(yaxis_range=[0, 105], paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                    # Missing data warning check
                    if "None" not in result["missing_data"]:
                        st.warning(f"**Missing Parameters Warning:** The following fields could not be resolved from raw text: *{result['missing_data']}*")
                    
                    # Display report sections
                    res_tab1, res_tab2 = st.tabs(["📝 Compiled Executive Report", "🛡️ Saved Output Files"])
                    
                    with res_tab1:
                        md_report = generator.reader.read_file(result["saved_files"]["markdown_report"])
                        st.markdown(md_report)
                        
                    with res_tab2:
                        st.write("Download generated reports for your weekly review:")
                        
                        col_d1, col_d2, col_d3 = st.columns(3)
                        with col_d1:
                            with open(result["saved_files"]["markdown_report"], "rb") as f:
                                st.download_button(
                                    "Download Markdown Report",
                                    data=f,
                                    file_name=os.path.basename(result["saved_files"]["markdown_report"]),
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                        with col_d2:
                            with open(result["saved_files"]["pdf_ready_text"], "rb") as f:
                                st.download_button(
                                    "Download PDF-ready Text",
                                    data=f,
                                    file_name=os.path.basename(result["saved_files"]["pdf_ready_text"]),
                                    mime="text/plain",
                                    use_container_width=True
                                )
                        with col_d3:
                            with open(result["saved_files"]["pptx_slides"], "rb") as f:
                                st.download_button(
                                    "Download Slide Deck (PPTX)",
                                    data=f,
                                    file_name=os.path.basename(result["saved_files"]["pptx_slides"]),
                                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    use_container_width=True
                                )
                                
                except Exception as e:
                    st.error(f"Failed to execute pipeline: {e}")
                    st.exception(e)
        else:
            st.warning("Please upload a file before running audit.")

# ----------------------------------------------------
# TAB 3: PORTFOLIO TRENDS
# ----------------------------------------------------
elif active_tab == "📈 Portfolio Trends":
    st.subheader("Portfolio-Level Trend Analytics")
    st.write("Aggregates all weekly reports across enterprise projects to construct monthly trend analysis summaries and slides.")
    
    timeframe = st.slider("Historical Timeframe (Days)", 7, 90, 30)
    
    if st.button("🚀 Analyze Portfolio Trends", use_container_width=True):
        analyzer = PortfolioAnalyzer()
        reports = analyzer.load_weekly_reports(timeframe_days=timeframe)
        
        if not reports:
            st.warning("No weekly project report records found in the database. Run the Weekly Audit tab first to generate project history.")
        else:
            with st.spinner("Aggregating historical metrics..."):
                # Run analyzer
                trend_report = analyzer.analyze_portfolio(reports)
                
                st.success("Portfolio analysis completed.")
                
                # Financial stats
                fin = trend_report.budget_burn_trends
                st.markdown("### Portfolio Financial Burn")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Budget", f"${fin.total_portfolio_budget:,.2f}")
                c2.metric("Total Spent", f"${fin.total_portfolio_spent:,.2f}")
                c3.metric("Burn Trajectory", fin.burn_rate_trajectory)
                
                # Progress bar
                if fin.total_portfolio_budget > 0:
                    ratio = min(1.0, fin.total_portfolio_spent / fin.total_portfolio_budget)
                    st.progress(ratio, text=f"Budget spent ratio: {ratio*100:.1f}%")
                
                # Blockers and Milestones
                col_block, col_mile = st.columns(2)
                with col_block:
                    st.markdown("#### Blocker Theme Groups")
                    for b in trend_report.common_blockers:
                        st.write(f"**{b.blocker_type}**")
                        st.caption(f"Details: {b.details}")
                        st.caption(f"Affected Projects: {', '.join(b.affected_projects)}")
                        st.divider()
                        
                with col_mile:
                    st.markdown("#### Repeated Milestone Delays")
                    for m in trend_report.repeated_milestone_delays:
                        st.write(f"🚩 **{m.milestone_name}**")
                        st.caption(f"Details: {m.details}")
                        st.caption(f"Affected Projects: {', '.join(m.affected_projects)}")
                        st.divider()
                        
                # Executive insights list
                st.markdown("### PMO Executive Insights")
                for insight in trend_report.executive_insights:
                    st.markdown(f"- *{insight}*")
                    
                # Slide Generation
                st.divider()
                st.markdown("### Generate Monthly Trend Presentation")
                
                ppt_output = f"outputs/presentations/monthly_portfolio_slides_{datetime.now().strftime('%Y-%m-%d')}.pptx"
                
                ppt_generator = PortfolioPPTGenerator()
                res_path = ppt_generator.generate_portfolio_deck(trend_report, ppt_output)
                
                with open(res_path, "rb") as f:
                    st.download_button(
                        "Download Monthly Executive Slide Deck (PPTX)",
                        data=f,
                        file_name=os.path.basename(res_path),
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )

# ----------------------------------------------------
# TAB 4: DOCUMENT HUB
# ----------------------------------------------------
elif active_tab == "📂 Document Hub":
    st.subheader("Enterprise Repository Deliverables")
    st.write("Browse and download generated files directly from output directories.")
    
    reports_dir = "outputs/weekly_reports"
    presentations_dir = "outputs/presentations"
    
    col_md, col_ppt = st.columns(2)
    
    with col_md:
        st.markdown("#### Markdown Reports & Data Files")
        if os.path.exists(reports_dir) and os.listdir(reports_dir):
            for file in os.listdir(reports_dir):
                if file.startswith("."):
                    continue
                filepath = os.path.join(reports_dir, file)
                # Determine mime type
                mime = "text/markdown" if file.endswith(".md") else "text/plain" if file.endswith(".txt") else "application/json"
                
                st.write(f"📄 `{file}`")
                with open(filepath, "rb") as f:
                    st.download_button(
                        f"Download {file}",
                        data=f,
                        file_name=file,
                        mime=mime,
                        key=f"hub_md_{file}"
                    )
                st.divider()
        else:
            st.caption("No weekly reports compiled yet.")
            
    with col_ppt:
        st.markdown("#### Executive Presentations")
        if os.path.exists(presentations_dir) and os.listdir(presentations_dir):
            for file in os.listdir(presentations_dir):
                if file.startswith("."):
                    continue
                filepath = os.path.join(presentations_dir, file)
                
                st.write(f"🖥️ `{file}`")
                with open(filepath, "rb") as f:
                    st.download_button(
                        f"Download Presentation",
                        data=f,
                        file_name=file,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key=f"hub_ppt_{file}"
                    )
                st.divider()
        else:
            st.caption("No presentations compiled yet.")
