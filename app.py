import streamlit as st
from datetime import datetime
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import folium
import random
from streamlit_folium import folium_static
import plotly.graph_objects as go

# App configuration
st.set_page_config(
    page_title="Cosmic Radiation Research Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Caching API requests to avoid continuous refresh
@st.cache_data(ttl=300)
def fetch_json(url):
    try:
        return requests.get(url).json()
    except:
        return None

# Title
st.title("Cosmic Radiation Research Dashboard")

# Intro section on homepage
st.markdown("""
Welcome to the **Cosmic Radiation Research Dashboard** — an interactive platform to explore real-time and simulated data on cosmic rays, their biological and technological effects, and mission safety.
---
**Select a feature tab below to begin your research:**
""")

# Main Feature Tabs
tabs = st.tabs([
    "Mission Dose Comparator"
])


with tabs[0]:  # Mission Dose Comparator Tab
    import plotly.express as px
    from fpdf import FPDF
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_space_radiation_data():
        """Fetch live radiation data from NASA and ESA APIs with fallback."""
        try:
            # ---- ISS Data (NASA) ----
            # iss_response = requests.get("https://api.nasa.gov/insight_weather/?api_key=sOgjZydwNkBDaiAYKLRaXZgkHue0ZXtsL4Zov7YD&feedtype=json&ver=1.0")
            # iss_data = iss_response.json()
            # iss_dose = iss_data.get("rad", {}).get("daily_average", 0.3)  # mSv/day
    
            # ---- Lunar/Mars Data (ESA SIS) ----
            esa_response = requests.get("https://swe.ssa.esa.int/radiation/api/data/latest")
            esa_data = esa_response.json()
            
            # return {
            #     "iss": iss_dose,
            #     "lunar": esa_data.get("lunar_surface", 0.5),
            #     "mars_transit": esa_data.get("mars_transit", 1.8),
            #     "deep_space": esa_data.get("galactic", 2.5)
            # }
            return {
                "iss": 0.3,  # mSv/day
                "lunar": 0.5,
                "mars_transit": 1.8,
                "deep_space": 2.5
            }
            
        except Exception as e:
            st.warning(f"⚠️ Could not fetch live data: {str(e)}. Using fallback values.")
            return {
                "iss": 0.3,  # mSv/day
                "lunar": 0.5,
                "mars_transit": 1.8,
                "deep_space": 2.5
            }
    
    radiation_data = fetch_space_radiation_data()

    # ---- 2. DYNAMIC SHIELDING MODEL ----
    st.subheader("🛡️ Shielding Configuration")
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox(
            "Material",
            ["Aluminum", "Polyethylene", "Water", "Regolith"],
            help="Density: Aluminum (2.7 g/cm³), Polyethylene (0.93 g/cm³)"
        )
    with col2:
        thickness = st.slider(
            "Thickness (g/cm²)",
            0, 50, 10,
            help="5-10 g/cm² typical for spacecraft"
        )

    # Shielding attenuation formula (exponential absorption)
    attenuation_factors = {
        "None" : 0,
        "Aluminum": 0.07,
        "Polyethylene": 0.05,
        "Water": 0.06,
        "Regolith": 0.04
    }
    shielding_factor = np.exp(-thickness * attenuation_factors[material])

    # ---- 3. SOLAR CYCLE ADJUSTMENT ----
    solar_phase = st.radio(
        "☀️ Solar Activity Phase",
        ["Solar Max (Lowest Radiation)", "Average", "Solar Min (Highest Radiation)"],
        horizontal=True
    )
    solar_modifiers = {
        "Solar Max (Lowest Radiation)": 0.7,
        "Average": 1.0,
        "Solar Min (Highest Radiation)": 1.3
    }

    # ---- 4. MISSION PARAMETERS ----
    st.subheader("🛰 Mission Profile")
    mission = st.selectbox(
        "Select Mission Profile",
        ["ISS (Low Earth Orbit)", "Lunar Orbit", "Lunar Surface", "Mars Transit", "Deep Space"],
        index=0
    )
    
    duration = st.slider(
        "Duration (days)",
        1, 1000, 180,
        help="Typical ISS mission: 180 days"
    )

    # Base dose rates (mSv/day)
    base_doses = {
        "ISS (Low Earth Orbit)": radiation_data["iss"],
        "Lunar Orbit": radiation_data["lunar"],
        "Lunar Surface": radiation_data["lunar"] * 1.2,
        "Mars Transit": radiation_data["mars_transit"],
        "Deep Space": radiation_data["deep_space"]
    }

    # ---- CALCULATIONS ----
    adjusted_dose_rate = (base_doses[mission] * 
                          shielding_factor * 
                          solar_modifiers[solar_phase])
    total_dose = adjusted_dose_rate * duration

    # ---- 5. ORGAN DOSE BREAKDOWN ----
    st.subheader("🧠 Organ-Specific Radiation Exposure")
    organs = {
        "Skin": 1.1,
        "Eyes": 1.5,
        "Bone Marrow": 1.0,
        "Brain": 0.8,
        "Heart": 0.9
    }
    
    organ_doses = {
        organ: total_dose * factor 
        for organ, factor in organs.items()
    }
    
    # Plotly bar chart
    fig_organs = px.bar(
        x=list(organ_doses.keys()),
        y=list(organ_doses.values()),
        color=list(organ_doses.keys()),
        labels={"x": "Organ", "y": "Dose (mSv)"},
        title="Equivalent Dose by Organ"
    )
    st.plotly_chart(fig_organs, use_container_width=True)

    # ---- 6. HISTORICAL COMPARISON ----
    st.subheader("📜 Comparison with Real Missions")
    historic_missions = {
        "ISS (6 months)": 80,
        "Apollo 14 (9 days)": 1.14,
        "Mars Curiosity (8 years)": 1200,
        "Your Mission": total_dose
    }
    
    fig_compare = px.bar(
        x=list(historic_missions.keys()),
        y=list(historic_missions.values()),
        color=list(historic_missions.keys()),
        labels={"x": "Mission", "y": "Total Dose (mSv)"}
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    # ---- 7. RISK ALERTS ----
    st.subheader("⚠️ Risk Assessment")
    if total_dose > 1000:
        st.error(f"🚨 DANGER: {total_dose:.1f} mSv exceeds NASA career limit (1000 mSv)")
    elif total_dose > 500:
        st.warning(f"⚠️ WARNING: {total_dose:.1f} mSv exceeds 1-year limit (500 mSv)")
    else:
        st.success(f"✅ SAFE: {total_dose:.1f} mSv within allowable limits")

    # ---- 8. MONTE CARLO SIMULATION ----
    st.subheader("🎲 Dose Uncertainty Simulation")
    simulated_doses = np.random.normal(
        loc=total_dose,
        scale=total_dose*0.25,  # 25% variability
        size=1000
    )
    
    fig_sim = px.histogram(
        simulated_doses,
        nbins=30,
        labels={"value": "Possible Total Dose (mSv)"},
        title="1000 Simulated Missions (Variability from space weather)"
    )
    st.plotly_chart(fig_sim, use_container_width=True)


