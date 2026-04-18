import streamlit as st

st.set_page_config(page_title="Agri-OS Navigation", layout="wide")

pages = {
    "": [
        st.Page("pages/0_Setup.py", title="Setup & Location", icon="🏠"),
        st.Page("pages/2_Dashboard.py", title="Simulation Dashboard", icon="📊"),
        st.Page("pages/1_Kisan_QA.py", title="Kisan Q&A", icon="🌾")
    ]
}

pg = st.navigation(pages, position="hidden")
pg.run()
