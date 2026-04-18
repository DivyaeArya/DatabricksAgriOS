import streamlit as st
import sys
import os

# Add root directory to sys.path to resolve 'utils' module since we run from dashboard folder
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import importlib
import utils.croppred
importlib.reload(utils.croppred)
from utils.croppred import recommend_crop

st.set_page_config(page_title="Agri-OS Setup", page_icon="🏠", layout="centered")

# Top Navigation Bar (Hidden Sidebar)
st.markdown("""
<style>
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
try:
    with col1:
        st.page_link("pages/0_Setup.py", label="Setup & Location", icon="🏠")
    with col2:
        st.page_link("pages/2_Dashboard.py", label="Simulation Dashboard", icon="📊")
    with col3:
        st.page_link("pages/1_Kisan_QA.py", label="Kisan Q&A", icon="🌾")
except Exception:
    st.warning("⚠️ Navigation Disabled: Please run `streamlit run app.py` from the dashboard directory to enable multipage routing.")
st.markdown("---")

st.title("🌾 Agri-OS Farm Setup")
st.write("Enter your location and farm layout to personalize crop simulations.")

col_s, col_d = st.columns(2)
with col_s:
    state = st.text_input("Enter your State (e.g., Maharashtra, Bihar):").strip()
with col_d:
    district = st.text_input("Enter your District (e.g., Patna, Pune):").strip()
farm_size = st.number_input("Farm Size (Acres):", min_value=0.5, value=10.0, step=0.5)

if st.button("Fetch Soil Data & Crop Recommendations"):
    if district and state:
        with st.spinner("Fetching mapping data and ML inference..."):
            crops, raw_soil_data = recommend_crop(district)
            
            if crops and raw_soil_data:
                st.session_state["state_input"] = state
                st.session_state["district_input"] = district
                st.session_state["raw_soil_data"] = raw_soil_data
                st.session_state["ml_crops"] = crops
                st.session_state["farm_size_acres"] = farm_size
                st.success(f"Data successfully fetched for {district}, {state}!")
            else:
                st.error("Could not fetch data for this district. Please check the spelling.")
    else:
        st.warning("Please enter both State and District.")

st.markdown("""
<style>
.metric-card {
    background-color: #1E1E1E;
    border-radius: 12px;
    padding: 15px;
    margin: 10px 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    text-align: center;
    border: 1px solid #333;
    color: white;
}
.metric-value {
    font-size: 24px;
    font-weight: bold;
    color: #4CAF50;
}
.metric-label {
    font-size: 14px;
    color: #AAA;
}
</style>
""", unsafe_allow_html=True)

if "ml_crops" in st.session_state:
    from cost_pred import AgricultureFinancialEngine
    
    st.markdown("---")
    st.markdown("### 🌍 Auto-Fetched Regional Data")
    st.caption("Here is the live regional data extracted for your coordinates which powers the AI suggestions below.")
    
    with st.expander("📊 Native Soil Parameters Matrix", expanded=True):
        param_cols = st.columns(4)
        for i, (k, v) in enumerate(st.session_state["raw_soil_data"].items()):
            display_v = round(v, 2) if isinstance(v, float) and v is not None else v
            if display_v is None: display_v = "N/A"
            with param_cols[i % 4]:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{display_v}</div>
                    <div class="metric-label">{str(k).upper()}</div>
                </div>
                ''', unsafe_allow_html=True)
                
    st.markdown("---")
    st.markdown("### 🌾 Top Crop Recommendations")
    st.info("Based on the geographical constraints above, the ML model strongly suggests these crops in descending order of compatibility:")
    
    for idx, c in enumerate(st.session_state["ml_crops"], 1):
        st.markdown(f"**{idx}. {c.capitalize()}**")
        
    st.markdown("### 🛒 Configure Simulation Strategy")
    selected_crop = st.selectbox("Select which crop to simulate:", st.session_state["ml_crops"])
    
    state_val = st.session_state.get("state_input", "Maharashtra")
    dist_val = st.session_state.get("district_input", district if district else "Pune")
    farm_acres = st.session_state.get("farm_size_acres", 10.0)
    
    engine = AgricultureFinancialEngine(api_key="", databricks_token="")
    with st.spinner("Crunching Agmarknet Financials..."):
        fin_data = engine.calculate_metrics(selected_crop, farm_acres, state_val, dist_val)
    
    st.markdown("#### 💰 Financial & Risk Analysis")
    if "error" in fin_data:
        st.warning(fin_data["error"])
    else:
        st.caption(f"*Source: {fin_data['location']['mandi']} APMC Mandi*")
        
        colA, colB, colC = st.columns(3)
        colA.metric("Market Price", fin_data["market_data"]["price_per_quintal"])
        colB.metric("Projected Revenue", fin_data["financial_analysis"]["total_revenue"])
        colC.metric("Net Profit (ROI)", f"{fin_data['financial_analysis']['net_profit']} ({fin_data['financial_analysis']['roi']})")
        
        st.markdown("##### 🚨 Databricks AI Risk Assessment")
        risk = fin_data.get("risk_assessment", {})
        risk_level = str(risk.get("risk_level", "medium")).upper()
        if risk_level == "LOW":
            st.success(f"**Risk Profile: {risk_level}**  \n{risk.get('summary', '')}")
        elif risk_level == "HIGH":
            st.error(f"**Risk Profile: {risk_level}**  \n{risk.get('summary', '')}")
        else:
            st.warning(f"**Risk Profile: {risk_level}**  \n{risk.get('summary', '')}")
    
    st.markdown("---")
    if st.button("Initialize Dashboard Simulation 🚀", type="primary", use_container_width=True):
        st.session_state["crop_name"] = selected_crop.lower()
        try:
            st.switch_page("pages/2_Dashboard.py")
        except Exception:
            st.error("Navigation Error: `StreamlitAPIException` - You are running 0_Setup.py natively. Please launch the app using `streamlit run app.py` instead of running pages directly to enable multi-page routing!")
