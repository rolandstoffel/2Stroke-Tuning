import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math

# ==============================================================================
# 1. BERECHNUNGSLOGIK (unverändert)
# ==============================================================================
def kurbelwinkel_zu_hub_exakt(kurbelwinkel_grad, pleuelstange_mm, hub_mm):
    if hub_mm <= 0 or pleuelstange_mm <= 0:
        return 0.0
    radius_mm = hub_mm / 2.0
    if pleuelstange_mm < radius_mm:
        raise ValueError("Pleuellänge muss größer als der Kurbelradius sein.")
    kurbelwinkel_rad = math.radians(kurbelwinkel_grad)
    l_r_verhaeltnis = pleuelstange_mm / radius_mm
    
    innerhalb_der_wurzel_wert = l_r_verhaeltnis**2 - math.sin(kurbelwinkel_rad)**2
    if innerhalb_der_wurzel_wert < 0:
        innerhalb_der_wurzel_wert = 0

    kolbenweg_s = radius_mm * (
        1 + l_r_verhaeltnis - math.cos(kurbelwinkel_rad) - math.sqrt(innerhalb_der_wurzel_wert)
    )
    return kolbenweg_s

def hub_zu_kurbelwinkel(kolbenweg_mm, pleuelstange_mm, hub_mm, toleranz=0.0001):
    if hub_mm <= 0 or pleuelstange_mm <= 0 or kolbenweg_mm < 0:
        return 0.0
    if kolbenweg_mm > hub_mm:
        return 180.0
        
    winkel_unten = 0.0
    winkel_oben = 180.0
    
    for _ in range(100):
        test_winkel = (winkel_unten + winkel_oben) / 2
        berechneter_hub = kurbelwinkel_zu_hub_exakt(test_winkel, pleuelstange_mm, hub_mm)
        
        if abs(berechneter_hub - kolbenweg_mm) < toleranz:
            return test_winkel
        
        if berechneter_hub > kolbenweg_mm:
            winkel_oben = test_winkel
        else:
            winkel_unten = test_winkel
            
    return (winkel_unten + winkel_oben) / 2

def berechne_auslass_resonanz(laenge_m, oeffnungswinkel_grad, schallgeschwindigkeit_ms):
    if laenge_m <= 0 or oeffnungswinkel_grad <= 0:
        return "Eingabewerte müssen positiv sein."
    # Formel n = (c_s * φ) / (12 * l_r)
    drehzahl = (schallgeschwindigkeit_ms * oeffnungswinkel_grad) / (12 * laenge_m)
    return f"{drehzahl:.0f} U/min"

def berechne_einlass_resonanz(oeffnungswinkel_grad, hubraum_ccm, kurbel_faktor, vergaser_d_mm, ansaug_faktor, ansaug_laenge):
    kurbelhausvolumen_cm3 = hubraum_ccm*kurbel_faktor
    querschnitt_cm2 = ansaug_faktor*(vergaser_d_mm/10/2)**2*math.pi
    if kurbelhausvolumen_cm3 <= 0 or querschnitt_cm2 <= 0 or oeffnungswinkel_grad <=0:
        return "Eingabewerte müssen positiv sein."
    # Formel n = (1750 * φ) / sqrt(V_k / F_m)
    # Hinweis aus dem Buch: Der effektive Winkel ist ca. 25-30° kleiner als der gemessene.
    effektiver_winkel = oeffnungswinkel_grad - 25 
    if effektiver_winkel <= 0:
        return "Effektiver Winkel zu klein. Bitte größeren Öffnungswinkel angeben."
    
    verhaeltnis = kurbelhausvolumen_cm3 * ansaug_laenge / querschnitt_cm2
    drehzahl = (1750 * effektiver_winkel) / math.sqrt(verhaeltnis)
    return f"{drehzahl:.0f} U/min"

# ==============================================================================
# 2. PLOT-FUNKTION FÜR DIE GRADSCHEIBE
# ==============================================================================
def plotte_gradscheibe(zuendwinkel):
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': 'polar'})
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_yticklabels([])
    ax.set_rgrids([])
    ax.spines['polar'].set_visible(False)
    ax.set_ylim(0, 1.2)

    for grad in range(0, 360):
        winkel_rad = np.deg2rad(grad)
        if grad % 10 == 0:
            ax.plot([winkel_rad, winkel_rad], [0.9, 1.0], color='black', linewidth=1.5)
            ax.text(winkel_rad, 1.05, str(grad), ha='center', va='center', fontsize=12, weight='bold')
        elif grad % 5 == 0:
            ax.plot([winkel_rad, winkel_rad], [0.95, 1.0], color='black', linewidth=1)
        else:
            ax.plot([winkel_rad, winkel_rad], [0.98, 1.0], color='gray', linewidth=0.5)

    if zuendwinkel is not None and 0 < zuendwinkel < 360:
        zuendwinkel_rad = np.deg2rad(zuendwinkel)
        ax.plot([zuendwinkel_rad, zuendwinkel_rad], [0.85, 1.0], color='red', linewidth=2.5, zorder=10)
        ax.text(zuendwinkel_rad, 0.8, f'Zündung\n({zuendwinkel:.1f}°)', ha='center', va='center', fontsize=14, weight='bold', color='red', rotation=-zuendwinkel)

    ax.text(0, 0, 'Gradscheibe\nOT bei 0°', ha='center', va='center', fontsize=16, weight='bold')
    ax.annotate('Motordrehrichtung',
                xy=np.deg2rad([300, 1]),
                xytext=np.deg2rad([300, 0.6]),
                arrowprops=dict(arrowstyle="<-", color="blue", linewidth=2, connectionstyle="arc3,rad=0.2"),
                ha='center', va='center', fontsize=12, color='blue')
    
    return fig

# ==============================================================================
# 3. STREAMLIT APP INTERFACE
# ==============================================================================

# Seitenkonfiguration
st.set_page_config(
    page_title="Zweitakt-Tuner",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Haupttitel
st.title("🏍️ Zweitakt-Tuner")
st.markdown("Ein Satz von Werkzeugen zur Berechnung und Abstimmung von Zweitaktmotoren, basierend auf den Formeln aus 'Zweitakt-Motoren Tuning' von Christian Rieck.")

# Sidebar für Navigation
st.sidebar.title("Navigation")
tab_selection = st.sidebar.radio(
    "Wählen Sie einen Bereich:",
    ["Resonanzdrehzahl Auslass", "Resonanzdrehzahl Einlass", "Werkzeuge"]
)

# ==============================================================================
# TAB 1: RESONANZDREHZAHL AUSLASS
# ==============================================================================
if tab_selection == "Resonanzdrehzahl Auslass":
    st.header("Resonanzdrehzahl Auslass")
    st.markdown("### Berechnet die Drehzahl, bei der der Auspuff in Resonanz ist.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Eingabeparameter")
        auslass_laenge = st.slider(
            "Resonanzlänge (m)", 
            min_value=0.5, 
            max_value=1.5, 
            value=0.85, 
            step=0.01,
            help="Länge vom Auslassschlitz bis zum Ende des Gegenkonus."
        )
        auslass_winkel = st.slider(
            "Auslass-Öffnungswinkel (°KW)", 
            min_value=100, 
            max_value=200, 
            value=140,
            help="Gesamter Öffnungswinkel des Auslassschlitzes."
        )
        schall_ms = st.slider(
            "Schallgeschwindigkeit im Abgas (m/s)", 
            min_value=450, 
            max_value=550, 
            value=500,
            help="Normalerweise ca. 500 m/s."
        )
    
    with col2:
        st.subheader("Ergebnis")
        auslass_result = berechne_auslass_resonanz(auslass_laenge, auslass_winkel, schall_ms)
        st.success(f"**Resonanzdrehzahl:** {auslass_result}")

# ==============================================================================
# TAB 2: RESONANZDREHZAHL EINLASS
# ==============================================================================
elif tab_selection == "Resonanzdrehzahl Einlass":
    st.header("Resonanzdrehzahl Einlass")
    st.markdown("### Berechnet die Drehzahl der besten Zylinderfüllung durch die Einlass-Schwingung.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Eingabeparameter")
        einlass_winkel = st.slider(
            "Einlass-Öffnungswinkel (°KW)", 
            min_value=100, 
            max_value=180, 
            value=130,
            help="Gemessener Wert. Das Skript zieht intern 25° für den Anschwingvorgang ab."
        )
        hubraum_ccm = st.number_input(
            "Hubraum (cm³)", 
            min_value=1.0, 
            value=50.0, 
            step=1.0
        )
        kurbel_faktor = st.slider(
            "Faktor Kurbelhausvolumen", 
            min_value=2.0, 
            max_value=4.0, 
            value=3.0, 
            step=0.1
        )
        vergaser_d_mm = st.number_input(
            "Vergaserdurchmesser (mm)", 
            min_value=1.0, 
            value=13.0, 
            step=0.1
        )
        ansaug_faktor = st.slider(
            "Faktor Ansaugfläche", 
            min_value=1.0, 
            max_value=1.3, 
            value=1.1, 
            step=0.01
        )
        ansaug_laenge = st.slider(
            "Länge Ansaugweg (cm)", 
            min_value=1.0, 
            max_value=20.0, 
            value=16.0, 
            step=0.1
        )
    
    with col2:
        st.subheader("Ergebnis")
        einlass_result = berechne_einlass_resonanz(
            einlass_winkel, hubraum_ccm, kurbel_faktor, 
            vergaser_d_mm, ansaug_faktor, ansaug_laenge
        )
        st.success(f"**Resonanzdrehzahl:** {einlass_result}")

# ==============================================================================
# TAB 3: WERKZEUGE
# ==============================================================================
elif tab_selection == "Werkzeuge":
    st.header("Werkzeuge")
    
    # Untertabs für Werkzeuge
    werkzeug_tab = st.selectbox(
        "Wählen Sie ein Werkzeug:",
        ["Hub → Winkel (Zündung)", "Winkel → Hub", "Druckbare Gradscheibe"]
    )
    
    # Hub zu Winkel
    if werkzeug_tab == "Hub → Winkel (Zündung)":
        st.subheader("Hub → Winkel (Zündung)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            hub_input1 = st.number_input("Hub (mm)", min_value=1.0, value=44.0, step=0.1, key="hub1")
            pleuel_input1 = st.number_input("Pleuellänge (mm)", min_value=1.0, value=95.0, step=0.1, key="pleuel1")
            kolbenweg_input = st.number_input("Kolbenweg vor OT (mm)", min_value=0.0, value=2.0, step=0.1)
            
            if st.button("Winkel berechnen", type="primary"):
                try:
                    winkel_result = hub_zu_kurbelwinkel(kolbenweg_input, pleuel_input1, hub_input1)
                    st.session_state.winkel_result = winkel_result
                except Exception as e:
                    st.error(f"Fehler bei der Berechnung: {e}")
        
        with col2:
            st.subheader("Ergebnis")
            if 'winkel_result' in st.session_state:
                st.success(f"**Benötigter Kurbelwinkel:** {st.session_state.winkel_result:.2f}° vor OT")
    
    # Winkel zu Hub
    elif werkzeug_tab == "Winkel → Hub":
        st.subheader("Winkel → Hub")
        
        col1, col2 = st.columns(2)
        
        with col1:
            hub_input2 = st.number_input("Hub (mm)", min_value=1.0, value=44.0, step=0.1, key="hub2")
            pleuel_input2 = st.number_input("Pleuellänge (mm)", min_value=1.0, value=95.0, step=0.1, key="pleuel2")
            winkel_input2 = st.slider("Kurbelwinkel nach OT (°)", min_value=0, max_value=180, value=90)
        
        with col2:
            st.subheader("Ergebnis")
            try:
                hub_result = kurbelwinkel_zu_hub_exakt(winkel_input2, pleuel_input2, hub_input2)
                st.success(f"**Kolbenweg vom OT:** {hub_result:.3f} mm")
            except Exception as e:
                st.error(f"Fehler bei der Berechnung: {e}")
    
    # Gradscheibe
    elif werkzeug_tab == "Druckbare Gradscheibe":
        st.subheader("Druckbare Gradscheibe")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            winkel_fuer_scheibe = st.number_input(
                "Zündwinkel hervorheben (°)", 
                min_value=0.0, 
                max_value=360.0, 
                value=21.86, 
                step=0.1
            )
        
        with col2:
            try:
                fig = plotte_gradscheibe(winkel_fuer_scheibe)
                st.pyplot(fig)
                plt.close(fig)  # Speicher freigeben
            except Exception as e:
                st.error(f"Fehler beim Erstellen der Gradscheibe: {e}")

# Footer
st.markdown("---")
st.markdown("*Basierend auf 'Zweitakt-Motoren Tuning' von Christian Rieck*")

