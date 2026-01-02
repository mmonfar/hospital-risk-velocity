import streamlit as st

HARM_LABELS = {
    1: "No Harm / Near Miss", 2: "Minimal Harm", 3: "Low Harm",
    4: "Moderate Harm", 5: "Significant Harm", 6: "Severe Harm",
    7: "Life-Threatening Harm", 8: "Death / Sentinel Event", 9: "Catastrophic Harm"
}

def apply_executive_css():
    st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        .dashboard-header {
            width: 100%; margin-bottom: 30px; padding: 40px;
            background: white; border: 1px solid #E9ECEF; border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }
        .exec-brief {
            margin-top: 20px; padding: 20px;
            background: #F8F9FA; border-radius: 12px; border-left: 5px solid #1D1D1F;
            font-size: 1.1rem; line-height: 1.6;
        }
        .metric-box {
            background: white; border: 1px solid #E9ECEF; border-radius: 12px;
            padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            height: 180px; display: flex; flex-direction: column;
            justify-content: space-between; margin-bottom: 25px;
        }
        .m-label { color: #86868B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .m-value { color: #1D1D1F; font-size: 2.2rem; font-weight: 700; line-height: 1; }
        .m-context { color: #86868B; font-size: 0.85rem; border-top: 1px solid #F1F3F5; padding-top: 10px; margin-top: auto; }
    </style>
    """, unsafe_allow_html=True)