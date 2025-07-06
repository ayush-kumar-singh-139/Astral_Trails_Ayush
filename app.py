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
    "Radiation Risk Calculator",
    "Live Cosmic Ray Shower Map",
    "Biological Effects Visualizer",
    "Effects on Electronics",
    "Cosmic Ray Data Explorer",
    "Mission Dose Comparator"
])


with tabs[5]:  # Mission Dose Comparator Tab
    import plotly.express as px
    from fpdf import FPDF
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_space_radiation_data():
        """Fetch live radiation data from NASA and ESA APIs with fallback."""
        try:
            # ---- ISS Data (NASA) ----
            iss_response = requests.get("https://api.nasa.gov/insight_weather/?api_key=sOgjZydwNkBDaiAYKLRaXZgkHue0ZXtsL4Zov7YD&feedtype=json&ver=1.0")
            iss_data = iss_response.json()
            iss_dose = iss_data.get("rad", {}).get("daily_average", 0.3)  # mSv/day
    
            # ---- Lunar/Mars Data (ESA SIS) ----
            esa_response = requests.get("https://swe.ssa.esa.int/radiation/api/data/latest")
            esa_data = esa_response.json()
            
            return {
                "iss": iss_dose,
                "lunar": esa_data.get("lunar_surface", 0.5),
                "mars_transit": esa_data.get("mars_transit", 1.8),
                "deep_space": esa_data.get("galactic", 2.5)
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

    # ---- 9. 3D TRAJECTORY VISUALIZATION ----
    st.subheader("🌌 Mission Trajectory (Simulated)")
    # Mock trajectory data (replace with real ephemeris data)
    trajectory_data = {
        "x": np.random.normal(0, 1, 100),
        "y": np.random.normal(0, 1, 100),
        "z": np.random.normal(0, 0.5, 100),
        "radiation": np.random.uniform(0.1, 2.0, 100)
    }
    
    fig_3d = px.scatter_3d(
        trajectory_data,
        x="x", y="y", z="z",
        color="radiation",
        color_continuous_scale="Hot",
        title="Radiation Exposure Along Trajectory (Relative)"
    )
    st.plotly_chart(fig_3d, use_container_width=True)

    # ---- 10. EXPORT REPORT ----
    st.subheader("📤 Generate Mission Report")
    if st.button("📄 Generate PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Report content
        pdf.cell(200, 10, txt="COSMIC RADIATION MISSION REPORT", ln=1, align="C")
        pdf.ln(10)
        pdf.multi_cell(0, 10, txt=f"""
        Mission Profile: {mission}
        Duration: {duration} days
        Shielding: {material} ({thickness} g/cm²)
        Solar Activity: {solar_phase}
        ------------------------------
        Total Estimated Dose: {total_dose:.1f} mSv
        Highest Organ Dose: {max(organ_doses.values()):.1f} mSv (to {max(organ_doses, key=organ_doses.get)})
        """)
        
        # Save and offer download
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f:
                st.download_button(
                    "⬇️ Download Full Report",
                    f.read(),
                    "radiation_mission_report.pdf",
                    mime="application/pdf"
                )
# Tab 7: Space Weather
with tabs[6]:
    import requests
    import datetime
    import matplotlib.pyplot as plt
    import pandas as pd
    import folium
    from streamlit_folium import folium_static

    st.subheader("🌞 Real-Time Space Weather Monitor")

    # --- Solar Flare Map (Mocked Locations) ---
    st.markdown("### ☀️ Solar Flare Activity Map")
    st.info("Note: Solar flare positions shown are mock data for visualization purposes only. Real solar flare coordinates are not provided in GOES public feeds.")

    flare_map = folium.Map(location=[0, 0], zoom_start=2, tiles="CartoDB positron")
    mock_flares = [
        {"lat": 10.5, "lon": 75.3, "class": "M"},
        {"lat": -8.2, "lon": -60.1, "class": "C"},
        {"lat": 23.7, "lon": 140.9, "class": "X"},
        {"lat": -15.1, "lon": 30.4, "class": "C"},
        {"lat": 5.4, "lon": -120.3, "class": "M"}
    ]
    flare_colors = {"C": "green", "M": "orange", "X": "red"}

    for flare in mock_flares:
        folium.CircleMarker(
            location=[flare["lat"], flare["lon"]],
            radius=7,
            popup=f"Class {flare['class']} Flare",
            color=flare_colors[flare["class"]],
            fill=True,
            fill_opacity=0.8
        ).add_to(flare_map)

    folium_static(flare_map)

    # --- Proton Flux ---
    st.markdown("### ☢️ Proton Flux (≥10 MeV)")
    try:
        url_proton = "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-3-day.json"
        proton_data = requests.get(url_proton).json()
        times = [datetime.datetime.strptime(p["time_tag"], "%Y-%m-%dT%H:%M:%SZ") for p in proton_data if p["energy"] == ">=10 MeV"]
        fluxes = [float(p["flux"]) for p in proton_data if p["energy"] == ">=10 MeV"]

        fig, ax = plt.subplots()
        ax.plot(times, fluxes, color='red')
        ax.set_title("Proton Flux (GOES - ≥10 MeV)")
        ax.set_ylabel("Flux (protons/cm²·s·sr)")
        ax.set_xlabel("UTC Time")
        ax.grid(True)
        st.pyplot(fig)

        if fluxes[-1] > 100:
            st.warning("⚠️ Elevated proton flux — possible solar event in progress.")
        else:
            st.success("✅ Proton flux is at normal background levels.")
    except:
        st.error("Could not load proton flux data.")

    # --- X-Ray Flux ---
    st.markdown("### ⚡ X-Ray Flux (Solar Flares)")
    try:
        url_xray = "https://services.swpc.noaa.gov/json/goes/primary/xrays-3-day.json"
        xray_data = requests.get(url_xray).json()
        x_times = [datetime.datetime.strptime(x["time_tag"], "%Y-%m-%dT%H:%M:%SZ") for x in xray_data]
        short = [float(x["flux"]) for x in xray_data]

        fig, ax = plt.subplots()
        ax.plot(x_times, short, color='orange')
        ax.set_title("X-Ray Short Flux (GOES)")
        ax.set_ylabel("Flux (W/m²)")
        ax.set_xlabel("UTC Time")
        ax.set_yscale("log")
        ax.grid(True)
        st.pyplot(fig)

        if short[-1] > 1e-5:
            st.warning("⚠️ Possible solar flare detected!")
        else:
            st.success("✅ No flare activity at the moment.")
    except:
        st.error("Could not load X-ray data.")

    # --- Kp Index ---
    st.markdown("### 🧭 Kp Index (Geomagnetic Storms)")
    try:
        url_kp = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        raw_data = requests.get(url_kp).json()
        header = raw_data[0]
        rows = raw_data[1:]

        df_kp = pd.DataFrame(rows, columns=header)
        df_kp["time_tag"] = pd.to_datetime(df_kp["time_tag"])
        df_kp["Kp"] = pd.to_numeric(df_kp["Kp"], errors='coerce')

        fig, ax = plt.subplots()
        ax.plot(df_kp["time_tag"], df_kp["Kp"], color='blue')
        ax.set_title("NOAA Kp Index (Last 3 Days)")
        ax.set_ylabel("Kp Value")
        ax.set_xlabel("UTC Time")
        ax.grid(True)
        st.pyplot(fig)

        latest_kp = df_kp["Kp"].iloc[-1]
        if latest_kp >= 5:
            st.warning(f"🌐 Geomagnetic storm conditions likely (Kp = {latest_kp})")
        else:
            st.success(f"✅ Geomagnetic field is quiet (Kp = {latest_kp})")
    except Exception as e:
        st.error(f"Could not load Kp index data: {e}")

# Tab 8: Research Library
with tabs[7]:
    st.subheader("📚 Research Paper Library")

    st.markdown("""
    Browse handpicked research papers on cosmic rays, radiation health, and space missions.
    """)

    import pandas as pd

    papers = pd.DataFrame({
        "Title": [
            "Comparative study of effects of cosmic rays on the earth’s atmospheric processes",
            "Beyond Earthly Limits: Protection against Cosmic Radiation through Biological Response Pathways",
            "The effect of cosmic rays on biological systems",
            "Microprocessor technology and single event upset susceptibility",
            "Impact Of Cosmic Rays On Satellite Communications"
        ],
        "Authors": [
            "Arshad Rasheed Ganai and Dr. Suryansh Choudhary",
            "Zahida Sultanova and Saleh Sultansoy",
            "N. K. Belisheva, H. Lammer, H. K. Biernat and E. V. Vashenuyk",
            "L.D. Akers",
            "Dr. Premlal P.D"
        ],
        "Link": [
            "https://www.physicsjournal.in/archives/2020.v2.i1.A.27/comparative-study-of-effects-of-cosmic-rays-on-the-earthrsquos-atmospheric-processes",
            "https://arxiv.org/pdf/2405.12151",
            "https://www.researchgate.net/publication/235958260_The_effect_of_cosmic_rays_on_biological_systems_-_An_investigation_during_GLE_events",
            "https://klabs.org/DEI/References/avionics/small_sat_conference/1996/ldakers.pdf",
            "https://www.iosrjournals.org/iosr-jece/papers/Vol.%2019%20Issue%202/Ser-1/D1902013337.pdf"
        ],
        "Year": [2020, 2024, 2012, 1996, 2024],
        "Tags": ["Atmosphere", "Biology", "Biology", "Electronics", "Electronics"],
        "Summary": [
            "This paper analyzes how cosmic rays interact with the Earth’s atmosphere, influencing weather patterns and climate variability. It compares different models to understand the impact of cosmic ray flux on atmospheric ionization and cloud formation.",
            
            "This paper explores biological pathways and protective measures against harmful cosmic radiation exposure. It reviews cellular responses, genetic impacts, and adaptive mechanisms found in various organisms. The study emphasizes the importance of biological shielding for deep-space missions and human health.",
            
            "Examines biological impacts of cosmic ray exposure.",
            
            "The study investigates how microprocessor circuits are vulnerable to single event upsets (SEUs) caused by cosmic rays. It presents test results and real-case observations from satellite missions. Recommendations for radiation-hardening techniques and fault-tolerant designs are provided.",
             
            "This paper discusses the adverse effects of cosmic rays on satellite communication systems. It explains how high-energy particles can induce bit errors and signal loss in satellite electronics. Mitigation strategies and design considerations are also highlighted to enhance system reliability."
        ]
    })

    tag = st.selectbox("Filter by Tag", ["All", "Atmosphere", "Biology", "Electronics"])
    if tag != "All":
        filtered = papers[papers["Tags"] == tag]
    else:
        filtered = papers

    st.dataframe(filtered)

    st.markdown("### Paper Summaries")
    for _, row in filtered.iterrows():
        st.write(f"**{row['Title']}**")
        st.write(f"*Authors:* {row['Authors']}")
        st.write(f"*Year:* {row['Year']}")
        st.write(f"*Summary:* {row['Summary']}")
        st.write(f"[Read Paper]({row['Link']})")
        st.write("---")

    st.markdown("### Example Paper Download")
    st.download_button(
        "Download Example Paper (PDF)",
        data=b"%PDF-1.4 ... (fake content)",
        file_name="example_paper.pdf",
        mime="application/pdf"
    )

# Tab 9: cosmic ray data explorerwith tabs[8]:
with tabs[8]:
    st.subheader("📤 Upload & Analyze Your Own Cosmic Ray Dataset")
    uploaded_file = st.file_uploader("Upload your CSV file (must include 'Energy' and 'Flux' columns, max 2MB)", type=["csv"])
    if uploaded_file is not None:
        if uploaded_file.size > 2 * 1024 * 1024:
            st.error("File too large. Please upload a file smaller than 2MB.")
        else:
            try:
                df = pd.read_csv(uploaded_file)
                if 'Energy' in df.columns and 'Flux' in df.columns:
                    st.success("File uploaded and read successfully!")
                    st.markdown("### Preview of Uploaded Data")
                    st.dataframe(df.head())
                    log_scale = st.checkbox("Log scale", value=True)
                    fig, ax = plt.subplots()
                    ax.plot(df['Energy'], df['Flux'], marker='o', linestyle='-', color='blue')
                    ax.set_xlabel("Energy")
                    ax.set_ylabel("Flux")
                    ax.set_title("Uploaded Cosmic Ray Spectrum")
                    if log_scale:
                        ax.set_yscale("log")
                        ax.set_xscale("log")
                    ax.grid(True, which='both', linestyle='--', alpha=0.5)
                    st.pyplot(fig)
                else:
                    st.error("CSV must contain 'Energy' and 'Flux' columns.")
            except Exception as e:
                st.error(f"Error reading file: {e}")


# FOOTER
st.markdown(f"""
---
<p style='text-align: center; color: gray'>
Built by Ayush Kumar Singh | Last updated: {datetime.datetime.now().strftime('%B %d, %Y')}
</p>
""", unsafe_allow_html=True)
