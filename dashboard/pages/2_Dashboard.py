import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime
from gdd import CROP_DB, get_stage, stage_progress, simulate_future, compute_gdd, compute_stress

# --- CONFIG ---
st.set_page_config(page_title="Precision Maintenance Dashboard", layout="wide")

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

WEATHER_API_KEY = "9263dfa9885ef03419fe5827ebb00de1"
SIM_DAYS = 90

default_soil = {
    "BDOD": 134, "CEC": 171, "CFVO": 78, "CLAY": 29.0,
    "SAND": 28.5, "SILT": 42.5, "NITROGEN": 183, "PHH2O": 6.8,
    "SOC": 171, "WV0010": 0.344, "WV0033": 0.321, "WV1500": 0.144
}

# Fetch SOIL_DATA from session state properly initialized from the Landing Page
SOIL_DATA = default_soil.copy()
if "raw_soil_data" in st.session_state and st.session_state["raw_soil_data"]:
    for k, v in st.session_state["raw_soil_data"].items():
        key = str(k).upper()
        # Only overwrite defaults if the API returned an actual valid float
        if v is not None:
            SOIL_DATA[key] = v

# --- STATE MANAGEMENT ---
def init_state():
    if "current_day" not in st.session_state:
        st.session_state.current_day = 0
    if "gdd_base" not in st.session_state:
        st.session_state.gdd_base = 800
    if "crop_name" not in st.session_state:
        st.session_state.crop_name = "rice"
    if "inventory_kg" not in st.session_state:
        st.session_state.inventory_kg = 100
    if "events" not in st.session_state:
        st.session_state.events = {i: {"fertilizer": False, "weed": False, "irrigate": False} for i in range(SIM_DAYS)}
    if "weather_data" not in st.session_state:
        st.session_state.weather_data = fetch_or_simulate_weather()

def fetch_or_simulate_weather():
    base_date = datetime.date.today()
    weather = []
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q=London&units=metric&appid={WEATHER_API_KEY}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if resp.status_code == 200:
            for item in data.get("list", []):
                if "12:00:00" in item.get("dt_txt", ""):
                    weather.append({
                        "temp": item["main"]["temp"],
                        "rain": item.get("rain", {}).get("3h", 0) * 8
                    })
    except Exception:
        pass
    
    final_weather = []
    for i in range(SIM_DAYS):
        date_str = (base_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        if i < len(weather):
            temp = weather[i]["temp"]
            rain = weather[i]["rain"]
        else:
            temp = np.random.normal(25, 3) 
            rain = max(0, np.random.normal(2, 5))
            
        final_weather.append({
            "date": date_str,
            "temp": temp,
            "tmax": temp + 4,
            "tmin": temp - 4,
            "rain": rain
        })
    return final_weather

def simulate_environment():
    M_base = 50.0   
    N_base = float(SOIL_DATA["NITROGEN"]) 
    W_base = 10.0   
    
    M_series = [M_base]
    N_series = [N_base]
    W_series = [W_base]
    
    weather = st.session_state.weather_data
    events = st.session_state.events
    
    for t in range(SIM_DAYS - 1):
        M_t = M_series[-1]
        N_t = N_series[-1]
        W_t = W_series[-1]
        
        rain = weather[t]["rain"]
        temp = weather[t]["temp"]
        evapo = max(1, temp * 0.1) 
        
        irrigated = events[t]["irrigate"]
        fertilized = events[t]["fertilizer"]
        weeded = events[t]["weed"]
        
        irrigation_amount = 20 if irrigated else 0
        M_next = max(0, min(100, M_t + rain + irrigation_amount - evapo))
        
        fertilizer_amount = 50 if fertilized else 0
        uptake = max(1, min(N_t * 0.02, 5))
        N_next = max(0, N_t - uptake + fertilizer_amount)
        
        growth = max(0.5, W_t * 0.05) if M_t > 20 else 0
        W_next = 10.0 if weeded else max(0, W_t + growth)
        
        M_series.append(M_next)
        N_series.append(N_next)
        W_series.append(W_next)
        
    return M_series, N_series, W_series

# --- UI STYLES ---
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

# --- MAIN APP LOGIC ---
init_state()

st.title("🌱 Precision Maintenance Dashboard")

M_series, N_series, W_series = simulate_environment()
curr_day = st.session_state.current_day
weather = st.session_state.weather_data

# --- TOP LEVEL CROP STATUS ---
crop = CROP_DB[st.session_state.crop_name]
soil_type = "loamy"

# Evolve GDD up to current day
current_gdd = st.session_state.gdd_base
for i in range(curr_day):
    day = weather[i]
    base_gdd = compute_gdd(day["tmax"], day["tmin"], crop["base_temp"])
    window = weather[max(0, i-7):i]
    stress = compute_stress(window, soil_type)
    current_gdd += base_gdd * stress

current_stage = get_stage(current_gdd, crop)
progress = stage_progress(current_gdd, crop)

st.subheader(f"🌾 Crop Status: {st.session_state.crop_name.capitalize()} - {current_stage.capitalize()} Phase")

forecast = weather[curr_day:]
predictions = simulate_future(current_gdd, forecast, crop, soil_type)

# Calculate overall lifecycle progress
harvest_gdd = crop["stages"]["harvest"]
overall_progress = min(1.0, current_gdd / harvest_gdd)

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=overall_progress * 100,
    number={'suffix': "%", 'valueformat': ".1f", 'font': {'size': 40}},
    title={'text': "🌱 Germination ➔ 🌿 Vegetative ➔ 🌼 Flowering ➔ 🌾 Harvest<br><span style='font-size:0.8em;color:gray'>Overall Lifecycle Progress</span>"},
    gauge={
        'axis': {'range': [0, 100], 'visible': False},
        'bar': {'color': "#17a2b8"},
        'bgcolor': "rgba(255,255,255,0.1)",
    }
))
fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})

col_gauge, col_info = st.columns([1, 1])
with col_gauge:
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_info:
    st.markdown("#### 🗓️ Expected Phase Timelines & Harvest")
    for stage in crop["stages"].keys():
        if current_gdd >= crop["stages"][stage]:
            st.success(f"**{stage.capitalize()}**: Completed")
        elif stage in predictions:
            st.info(f"**{stage.capitalize()}**: ETA: {predictions[stage]}")
        else:
            st.warning(f"**{stage.capitalize()}**: ETA: >90 days")

st.markdown("---")

M_THRESH = 30
N_THRESH = 100
W_THRESH = 20

# Sidebar Actions
st.sidebar.subheader("🚀 Manual Actions (Applied to Current Day)")

def apply_event(evt_type):
    if evt_type == "fertilizer":
        if st.session_state.inventory_kg >= 10:
            st.session_state.inventory_kg -= 10
            st.session_state.events[curr_day][evt_type] = True
            st.toast("Fertilizer Applied (-10 kg)", icon="✅")
        else:
            st.sidebar.error("Not enough fertilizer!")
            return False
    else:
        st.session_state.events[curr_day][evt_type] = True
        st.toast(f"{evt_type.capitalize()} Applied!", icon="✅")
    return True

col1, col2, col3 = st.sidebar.columns(3)
if col1.button("💧 Water", help="Apply Irrigation"):
    if apply_event("irrigate"): st.rerun()
if col2.button("🧪 NPK", help="Apply Fertilizer"):
    if apply_event("fertilizer"): st.rerun()
if col3.button("🌿 Weed", help="Remove Weeds"):
    if apply_event("weed"): st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Inventory Tracking")
inv = st.session_state.inventory_kg
st.sidebar.metric("Fertilizer Remaining", f"{inv} kg")
if inv <= 20:
    st.sidebar.warning("⚠️ Low Fertilizer Inventory!")

st.sidebar.markdown("---")
st.sidebar.header("🎮 Demo Controller")
curr_day_slider = st.sidebar.slider("Shift Time (Current Day)", 0, SIM_DAYS-1, st.session_state.current_day)
gdd_slider = st.sidebar.slider("Base GDD (Starting Amount)", 0, 2500, st.session_state.gdd_base)

if curr_day_slider != st.session_state.current_day or gdd_slider != st.session_state.gdd_base:
    st.session_state.current_day = curr_day_slider
    st.session_state.gdd_base = gdd_slider
    st.rerun()

# Top Level Stats / Alerts
st.header("📋 Today's Assessment & Actions")
alert_idx = min(curr_day + 1, len(M_series) - 1)
alert_cols = st.columns(3)
with alert_cols[0]:
    if M_series[alert_idx] < M_THRESH:
        st.error("💧 Moisture Critical. Irrigation strongly recommended!")
    else:
        st.success("💧 Soil Moisture is optimal.")
with alert_cols[1]:
    if N_series[alert_idx] < N_THRESH:
        st.error("🧪 Nitrogen Low. Apply Fertilizer soon!")
    else:
        st.success("🧪 Nitrogen levels are optimal.")
with alert_cols[2]:
    if W_series[alert_idx] > W_THRESH:
        st.warning("🌿 Weed Index High. Weeding recommended.")
    else:
        st.success("🌿 Weed Index is safe.")

# Soil Data Cards
with st.expander("📊 Soil Parameters Matrix"):
    param_cols = st.columns(4)
    for i, (k, v) in enumerate(SOIL_DATA.items()):
        with param_cols[i % 4]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{v}</div>
                <div class="metric-label">{k}</div>
            </div>
            """, unsafe_allow_html=True)

# Charts Section
st.markdown("---")
st.header("📈 Past & Live Data")

# Slice up to curr_day + 2 to immediately show the effect of today's applied actions
display_idx = min(curr_day + 2, len(M_series))
past_days = list(range(display_idx))
m_past = M_series[:display_idx]
n_past = N_series[:display_idx]
w_past = W_series[:display_idx]

chart_cols = st.columns(3)

with chart_cols[0]:
    st.markdown("#### Soil Moisture tracking")
    df_m = pd.DataFrame({"Moisture": m_past}, index=past_days)
    st.line_chart(df_m, color=["#00d1ff"], height=250)

with chart_cols[1]:
    st.markdown("#### Nitrogen Level tracking")
    df_n = pd.DataFrame({"Nitrogen": n_past}, index=past_days)
    st.line_chart(df_n, color=["#ff0000"], height=250)

with chart_cols[2]:
    st.markdown("#### Weed Index tracking")
    df_w = pd.DataFrame({"Weed Index": w_past}, index=past_days)
    st.line_chart(df_w, color=["#ffa500"], height=250)

# Schedule Section
col_schedule, col_export = st.columns([2, 1])

with col_schedule:
    st.subheader("📅 Weekly Operations Schedule")
    schedule_data = []
    for d in sorted(list(st.session_state.events.keys())):
        ev = st.session_state.events[d]
        if any(ev.values()):
            week = (d // 7) + 1
            actions = []
            if ev["irrigate"]: actions.append("Irrigate")
            if ev["fertilizer"]: actions.append("NPK Fertilizer")
            if ev["weed"]: actions.append("Weed Removal")
            schedule_data.append({"Week": f"Week {week}", "Day": d, "Actions Logged": ", ".join(actions)})
            
    if schedule_data:
        st.dataframe(pd.DataFrame(schedule_data), use_container_width=True, hide_index=True)
    else:
        st.info("No actions have been executed yet.")

with col_export:
    st.subheader("📥 Data Export")
    st.write("Extract the full 90-day simulation including the results of applied actions.")
    df_sim = pd.DataFrame({
        "Day": list(range(SIM_DAYS)),
        "Moisture_%": M_series,
        "Nitrogen_Level": N_series,
        "Weed_Index": W_series
    })
    csv_bytes = df_sim.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Simulation CSV",
        data=csv_bytes,
        file_name='precision_simulation_90day.csv',
        mime='text/csv',
        use_container_width=True
    )
