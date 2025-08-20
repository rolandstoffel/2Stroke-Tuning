import gradio as gr
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
                #xycoords='polar', textcoords='polar',
                arrowprops=dict(arrowstyle="<-", color="blue", linewidth=2, connectionstyle="arc3,rad=0.2"),
                ha='center', va='center', fontsize=12, color='blue')
    
    return fig


# ==============================================================================
# 3. GRADIO APP INTERFACE
# ==============================================================================
with gr.Blocks(theme=gr.themes.Soft(), title="Zweitakt-Tuner") as app:
    gr.Markdown("# Zweitakt-Tuner")
    gr.Markdown("Ein Satz von Werkzeugen zur Berechnung und Abstimmung von Zweitaktmotoren, basierend auf den Formeln aus 'Zweitakt-Motoren Tuning' von Christian Rieck.")

    with gr.Tabs():
        with gr.TabItem("Resonanzdrehzahl Auslass"):
            gr.Markdown("### Berechnet die Drehzahl, bei der der Auspuff in Resonanz ist.")
            with gr.Row():
                with gr.Column(scale=2):
                    auslass_laenge = gr.Slider(0.5, 1.5, label="Resonanzlänge (m)", info="Länge vom Auslassschlitz bis zum Ende des Gegenkonus.", value=0.85)
                    auslass_winkel = gr.Slider(100, 200, label="Auslass-Öffnungswinkel (°KW)", info="Gesamter Öffnungswinkel des Auslassschlitzes.", value=140)
                    schall_ms = gr.Slider(450, 550, label="Schallgeschwindigkeit im Abgas (m/s)", info="Normalerweise ca. 500 m/s.", value=500)
                with gr.Column(scale=1):
                    gr.Markdown("### Ergebnis")
                    auslass_drehzahl_output = gr.Textbox(label="Resonanzdrehzahl", interactive=False)
            
            auslass_inputs = [auslass_laenge, auslass_winkel, schall_ms]
            for component in auslass_inputs:
                component.change(berechne_auslass_resonanz, inputs=auslass_inputs, outputs=auslass_drehzahl_output)
            app.load(berechne_auslass_resonanz, inputs=auslass_inputs, outputs=auslass_drehzahl_output)

        with gr.TabItem("Resonanzdrehzahl Einlass"):
            gr.Markdown("### Berechnet die Drehzahl der besten Zylinderfüllung durch die Einlass-Schwingung.")
            with gr.Row():
                with gr.Column(scale=2):
                    einlass_winkel = gr.Slider(100, 180, label="Einlass-Öffnungswinkel (°KW)", info="Gemessener Wert. Das Skript zieht intern 25° für den Anschwingvorgang ab.", value=130)
                    hubraum_ccm = gr.Number(label="Hubraum (cm³)", value=50)
                    kurbel_faktor = gr.Slider(2.0, 4.0, label="Faktor Kurbelhausvolumen", value=3.0)
                    vergaser_d_mm = gr.Number(label="Vergaserdurchmesser (mm)", value=13)
                    ansaug_faktor = gr.Slider(1.0, 1.3, label="Faktor Ansaugfläche", value=1.1)
                    ansaug_laenge = gr.Slider(1.0, 20.0, label="Länge Ansaugweg (cm)", value=16.0)
                with gr.Column(scale=1):
                    gr.Markdown("### Ergebnis")
                    einlass_drehzahl_output = gr.Textbox(label="Resonanzdrehzahl", interactive=False)

            einlass_inputs = [einlass_winkel, hubraum_ccm, kurbel_faktor, vergaser_d_mm, ansaug_faktor, ansaug_laenge]
            for component in einlass_inputs:
                component.change(berechne_einlass_resonanz, inputs=einlass_inputs, outputs=einlass_drehzahl_output)
            app.load(berechne_einlass_resonanz, inputs=einlass_inputs, outputs=einlass_drehzahl_output)

        with gr.TabItem("Werkzeuge"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Hub → Winkel (Zündung)")
                    hub_input1 = gr.Number(label="Hub (mm)", value=44.0)
                    pleuel_input1 = gr.Number(label="Pleuellänge (mm)", value=95.0)
                    kolbenweg_input = gr.Number(label="Kolbenweg vor OT (mm)", value=2.0)
                    berechnen_btn1 = gr.Button("Winkel berechnen", variant="primary")
                    winkel_output = gr.Textbox(label="Benötigter Kurbelwinkel (° vor OT)", interactive=False)
                    berechnen_btn1.click(hub_zu_kurbelwinkel, inputs=[kolbenweg_input, pleuel_input1, hub_input1], outputs=winkel_output)
                with gr.Column():
                    gr.Markdown("#### Winkel → Hub")
                    hub_input2 = gr.Number(label="Hub (mm)", value=44.0)
                    pleuel_input2 = gr.Number(label="Pleuellänge (mm)", value=95.0)
                    winkel_input2 = gr.Slider(0, 180, label="Kurbelwinkel nach OT (°)", value=90)
                    hub_output = gr.Textbox(label="Kolbenweg vom OT (mm)", interactive=False)
                    winkel_input2.change(kurbelwinkel_zu_hub_exakt, inputs=[winkel_input2, pleuel_input2, hub_input2], outputs=hub_output)
            
            gr.Markdown("--- \n ### Druckbare Gradscheibe")
            with gr.Row():
                winkel_fuer_scheibe = gr.Number(label="Zündwinkel hervorheben (°)", value=21.86)
                plot_output = gr.Plot(label="Gradscheibe")
            winkel_fuer_scheibe.change(plotte_gradscheibe, inputs=winkel_fuer_scheibe, outputs=plot_output)
            app.load(plotte_gradscheibe, inputs=winkel_fuer_scheibe, outputs=plot_output)

# App starten und einen öffentlichen Link erstellen
app.launch(share=True)