import streamlit as streamlit_app
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageDraw
import io
import math
import numpy as np

# Configuración de la página
streamlit_app.set_page_config(
    page_title="CALCULADORA xG Y PPDA BY JM",
    page_icon="⚽",
    layout="wide"
)

# Intentar importar el componente de coordenadas de imagen
try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    HAS_IMAGE_COORDS = True
except ImportError:
    HAS_IMAGE_COORDS = False

# Inicializar estados de la sesión
if 'shots_data' not in streamlit_app.session_state:
    streamlit_app.session_state.shots_data = []

if 'match_events' not in streamlit_app.session_state:
    streamlit_app.session_state.match_events = []

if 'selected_x' not in streamlit_app.session_state:
    streamlit_app.session_state.selected_x = 94.0

if 'selected_y' not in streamlit_app.session_state:
    streamlit_app.session_state.selected_y = 34.0

# Estados acumulativos para PPDA Local
if 'total_pases_local' not in streamlit_app.session_state:
    streamlit_app.session_state.total_pases_local = 0
if 'total_acciones_local' not in streamlit_app.session_state:
    streamlit_app.session_state.total_acciones_local = 0
if 'acciones_local_detalle' not in streamlit_app.session_state:
    streamlit_app.session_state.acciones_local_detalle = {"Recuperación": 0, "Interceptación": 0, "Entrada / Duelo ganado": 0, "Falta táctica": 0}
if 'ppda_local_val' not in streamlit_app.session_state:
    streamlit_app.session_state.ppda_local_val = 0.0

# Estados acumulativos para PPDA Rival
if 'total_pases_rival' not in streamlit_app.session_state:
    streamlit_app.session_state.total_pases_rival = 0
if 'total_acciones_rival' not in streamlit_app.session_state:
    streamlit_app.session_state.total_acciones_rival = 0
if 'acciones_rival_detalle' not in streamlit_app.session_state:
    streamlit_app.session_state.acciones_rival_detalle = {"Recuperación": 0, "Interceptación": 0, "Entrada / Duelo ganado": 0, "Falta táctica": 0}
if 'ppda_rival_val' not in streamlit_app.session_state:
    streamlit_app.session_state.ppda_rival_val = 0.0

# Estilos personalizados en CSS
streamlit_app.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

streamlit_app.title("⚽Calculadora xG y PPDA")
streamlit_app.markdown("Monitoreo en tiempo real de **xG (Expected Goals)** y **PPDA** (Passes Per Defensive Action).")

# Barra lateral para configuración del partido
with streamlit_app.sidebar:
    streamlit_app.header("⚙️ Configuración del Partido")
    equipo_local = streamlit_app.text_input("Equipo Local", "Nuestro Equipo")
    equipo_visitante = streamlit_app.text_input("Equipo Visitante", "Rival")
    
    streamlit_app.divider()
    streamlit_app.subheader("📊 Controles de Sesión")
    if streamlit_app.button("🔄 Reiniciar Datos del Partido", type="primary"):
        streamlit_app.session_state.shots_data = []
        streamlit_app.session_state.total_pases_local = 0
        streamlit_app.session_state.total_acciones_local = 0
        streamlit_app.session_state.acciones_local_detalle = {k: 0 for k in streamlit_app.session_state.acciones_local_detalle}
        streamlit_app.session_state.ppda_local_val = 0.0
        
        streamlit_app.session_state.total_pases_rival = 0
        streamlit_app.session_state.total_acciones_rival = 0
        streamlit_app.session_state.acciones_rival_detalle = {k: 0 for k in streamlit_app.session_state.acciones_rival_detalle}
        streamlit_app.session_state.ppda_rival_val = 0.0
        
        streamlit_app.session_state.match_events = []
        streamlit_app.session_state.selected_x = 94.0
        streamlit_app.session_state.selected_y = 34.0
        streamlit_app.rerun()

# Pestañas principales
tab_remates, tab_ppda, tab_resumen = streamlit_app.tabs(["🎯 Mapa de Remates & xG", "🛡️ Análisis PPDA", "📋 Resumen y Eventos"])

with tab_remates:
    streamlit_app.subheader("🎯 Calculadora Profesional de Expected Goals (xG)")
    
    col_filtro1, col_filtro2 = streamlit_app.columns([1, 2])
    with col_filtro1:
        filtro_visualizacion = streamlit_app.selectbox(
            "Filtrar campograma por:",
            ["Todos los remates", f"Solo {equipo_local} (Propios)", f"Solo {equipo_visitante} (Rival)"],
            key="filtro_mapa_remates"
        )

    if 'selected_x' not in streamlit_app.session_state:
        streamlit_app.session_state.selected_x = 94.0
    if 'selected_y' not in streamlit_app.session_state:
        streamlit_app.session_state.selected_y = 34.0

    col_mapa, col_form = streamlit_app.columns([1.4, 1])

    with col_mapa:
        streamlit_app.markdown("#### 🏟️ Mitad Ofensiva (Con área pequeña, portería y espacio exterior)")

        img_width, img_height = 740, 650
        pitch_img = Image.new("RGB", (img_width, img_height), color="#1b4d2e")
        draw = ImageDraw.Draw(pitch_img)

        x_min, x_max = 50.0, 116.0
        y_min, y_max = -2.0, 73.0

        def m_to_px(mx, my):
            px = int((mx - x_min) / (x_max - x_min) * img_width)
            py = int((my - y_min) / (y_max - y_min) * img_height)
            return px, py

        def px_to_m(px, py):
            mx = x_min + (px / img_width) * (x_max - x_min)
            my = y_min + (py / img_height) * (y_max - y_min)
            return mx, my

        def draw_star(draw_obj, cx, cy, radius, fill_color, outline_color):
            points = []
            num_points = 5
            for i in range(num_points * 2):
                angle = i * math.pi / num_points - math.pi / 2
                r = radius if i % 2 == 0 else radius * 0.45
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                points.append((x, y))
            draw_obj.polygon(points, fill=fill_color, outline=outline_color)

        num_franjas = 13
        ancho_franja = img_width / num_franjas
        for i in range(num_franjas):
            color_franja = "#1b4d2e" if i % 2 == 0 else "#225d37"
            draw.rectangle([i * ancho_franja, 0, (i + 1) * ancho_franja, img_height], fill=color_franja)

        draw.rectangle([m_to_px(52.5, 0), m_to_px(105, 68)], outline="#ffffff", width=3)
        draw.line([m_to_px(52.5, 0), m_to_px(52.5, 68)], fill="#ffffff", width=3)
        
        cx_c, cy_c = m_to_px(52.5, 34)
        r_c = int(9.15 / (y_max - y_min) * img_height)
        draw.arc([cx_c - r_c, cy_c - r_c, cx_c + r_c, cy_c + r_c], start=270, end=90, fill="#ffffff", width=3)

        draw.rectangle([m_to_px(88.5, 13.84), m_to_px(105, 54.16)], outline="#ffffff", width=3)
        draw.rectangle([m_to_px(99.5, 24.84), m_to_px(105, 43.16)], outline="#ffffff", width=3)

        px_pen, py_pen = m_to_px(94, 34)
        draw.ellipse([px_pen-3, py_pen-3, px_pen+3, py_pen+3], fill="#ffffff")
        r_arc = int(9.15 / (x_max - x_min) * img_width)
        draw.arc([px_pen - r_arc, py_pen - r_arc, px_pen + r_arc, py_pen + r_arc], start=128, end=232, fill="#ffffff", width=3)

        draw.rectangle([m_to_px(105, 30.34), m_to_px(108.0, 37.66)], outline="#ffffff", fill="#143820", width=3)
        draw.line([m_to_px(105, 30.34), m_to_px(105, 37.66)], fill="#ffffff", width=5)

        remates_a_dibujar = streamlit_app.session_state.shots_data
        if filtro_visualizacion == f"Solo {equipo_local} (Propios)":
            remates_a_dibujar = [s for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_local]
        elif filtro_visualizacion == f"Solo {equipo_visitante} (Rival)":
            remates_a_dibujar = [s for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_visitante]

        if remates_a_dibujar:
            for shot in remates_a_dibujar:
                sx, sy = m_to_px(shot['x'], shot['y'])
                radio = int(shot['xg'] * 14 + 7)
                color_circulo = "#29b6f6" if shot['equipo'] == equipo_local else "#ffa726"
                is_gol = "Gol" in shot.get('resultado', '')

                if is_gol:
                    draw_star(draw, sx, sy, radius=radio + 5, fill_color=color_circulo, outline_color="#ffffff")
                else:
                    draw.ellipse([sx-radio-1, sy-radio-1, sx+radio+1, sy+radio+1], fill="#000000")
                    draw.ellipse([sx-radio, sy-radio, sx+radio, sy+radio], fill=color_circulo, outline="#ffffff", width=2)

        curr_px, curr_py = m_to_px(streamlit_app.session_state.selected_x, streamlit_app.session_state.selected_y)
        draw.ellipse([curr_px - 8, curr_py - 8, curr_px + 8, curr_py + 8], fill="#ffeb3b", outline="#000000", width=2)
        draw.ellipse([curr_px - 2, curr_py - 2, curr_px + 2, curr_py + 2], fill="#000000")

        if HAS_IMAGE_COORDS:
            value = streamlit_image_coordinates(pitch_img, key="pitch_click", width=img_width)
            if value is not None:
                click_px_x = value["x"]
                click_px_y = value["y"]
                calc_x, calc_y = px_to_m(click_px_x, click_px_y)
                calc_x = max(52.5, min(108.0, calc_x))
                calc_y = max(0.0, min(68.0, calc_y))

                rounded_x = round(calc_x, 2)
                rounded_y = round(calc_y, 2)

                if streamlit_app.session_state.selected_x != rounded_x or streamlit_app.session_state.selected_y != rounded_y:
                    streamlit_app.session_state.selected_x = rounded_x
                    streamlit_app.session_state.selected_y = rounded_y
                    streamlit_app.session_state.cx_rem = rounded_x
                    streamlit_app.session_state.cy_rem = rounded_y
                    streamlit_app.rerun()
        else:
            streamlit_app.warning("Instala `streamlit-image-coordinates`.")
            streamlit_app.image(pitch_img, use_container_width=True)

    with col_form:
        with streamlit_app.container():
            streamlit_app.markdown("#### ⚙️ Parámetros Avanzados del Remate")
            
            equipo_remate = streamlit_app.selectbox("Equipo que remata", [equipo_local, equipo_visitante], key="eq_rem")
            jugador = streamlit_app.text_input("Jugador", "Delantero #9", key="jug_rem")
            
            col_cx, col_cy = streamlit_app.columns(2)
            with col_cx:
                coord_x = streamlit_app.number_input("Coordenada X", min_value=52.5, max_value=107.5, value=float(streamlit_app.session_state.selected_x), step=0.5, key="cx_rem")
            with col_cy:
                coord_y = streamlit_app.number_input("Coordenada Y", min_value=0.0, max_value=68.0, value=float(streamlit_app.session_state.selected_y), step=0.5, key="cy_rem")
            
            streamlit_app.session_state.selected_x = coord_x
            streamlit_app.session_state.selected_y = coord_y

            tipo_remate = streamlit_app.selectbox("Superficie / Parte del Cuerpo", ["Pie Hábil (Normal)", "Pie Menos Hábil", "Cabeza", "Penal"], key="cuerpo_rem")
            tipo_asistencia = streamlit_app.selectbox("Tipo de Asistencia / Origen", ["Pase filtrado / Mano a mano", "Jugada colectiva normal", "Pase atrás (Cutback)", "Centro lateral / Aéreo", "Jugada individual / Regate"], key="asist_rem")
            presion_defensiva = streamlit_app.selectbox("Oposición Defensiva", ["Libre / Sin marca cercana", "Con oposición media", "Alta presión / Defensor en línea de tiro"], key="pres_rem")
            resultado = streamlit_app.selectbox("Resultado del Remate", ["Gol ⚽", "Atajado 🧤", "Bloqueado 🛡️️", "Fuera ❌"], key="res_rem")

            distancia = np.sqrt((105 - coord_x)**2 + (34 - coord_y)**2)
            y_post1, y_post2 = 30.34, 37.66
            v1_x, v1_y = 105 - coord_x, y_post1 - coord_y
            v2_x, v2_y = 105 - coord_x, y_post2 - coord_y
            dot_prod = v1_x * v2_x + v1_y * v2_y
            mag1 = np.sqrt(v1_x**2 + v1_y**2)
            mag2 = np.sqrt(v2_x**2 + v2_y**2)
            cos_angle = np.clip(dot_prod / (mag1 * mag2 + 1e-6), -1.0, 1.0)
            angulo_grados = np.degrees(np.arccos(cos_angle))

            base_xg = 1.0 / (1.0 + np.exp(0.14 * (distancia - 9.0)))
            factor_angulo = min(1.25, max(0.35, angulo_grados / 28.0))
            base_xg *= factor_angulo

            if tipo_asistencia == "Pase filtrado / Mano a mano":
                base_xg *= 1.25
            elif tipo_asistencia == "Pase atrás (Cutback)":
                base_xg *= 1.30
            elif tipo_asistencia == "Centro lateral / Aéreo":
                base_xg *= 0.75
            elif tipo_asistencia == "Jugada individual / Regate":
                base_xg *= 1.10

            if tipo_remate == "Pie Menos Hábil":
                base_xg *= 0.82
            elif tipo_remate == "Cabeza":
                base_xg *= 0.72
            elif tipo_remate == "Penal":
                base_xg = 0.76

            if presion_defensiva == "Con oposición media":
                base_xg *= 0.80
            elif presion_defensiva == "Alta presión / Defensor en línea de tiro":
                base_xg *= 0.40

            if tipo_remate != "Penal":
                xg_calculado = round(min(0.85, max(0.01, base_xg)), 2)
            else:
                xg_calculado = 0.76

            streamlit_app.markdown(f"""
                <div style="background-color: #ffffff; padding: 12px; border-radius: 8px; border-left: 5px solid #2e7d32; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <span style="font-size: 13px; color: #555; font-weight: 600;">ÁNGULO: {angulo_grados:.1f}° | DISTANCIA: {distancia:.1f}m</span>
                    <h3 style="color: #2e7d32; margin: 0; font-size: 26px;">xG Estimado: {xg_calculado}</h3>
                </div>
            """, unsafe_allow_html=True)

            if streamlit_app.button("📥 Registrar Remate al Partido", type="primary", use_container_width=True):
                nuevo_remate = {
                    "equipo": equipo_remate,
                    "jugador": jugador,
                    "x": coord_x,
                    "y": coord_y,
                    "xg": xg_calculado,
                    "tipo": tipo_remate,
                    "situacion": tipo_asistencia,
                    "resultado": resultado
                }
                streamlit_app.session_state.shots_data.append(nuevo_remate)
                streamlit_app.session_state.match_events.append(f"Remate de {jugador} ({equipo_remate}) - xG: {xg_calculado} [{resultado}]")
                streamlit_app.success(f"¡Remate registrado con éxito! xG: {xg_calculado}")
                streamlit_app.rerun()

with tab_ppda:
    streamlit_app.markdown("### 🛡️ Análisis de Presión y PPDA (Acumulativo por Jugada)")
    streamlit_app.markdown("Indica cuántos pases se dieron en la jugada actual antes de la intervención o desenlace, y regístrala para mantener el PPDA exacto.")

    col_ppda_local, col_ppda_rival = streamlit_app.columns(2)

    with col_ppda_local:
        streamlit_app.markdown(f"#### Presión de: {equipo_local}")
        
        pases_jugada_local = streamlit_app.number_input("Pases permitidos al rival en su campo", min_value=0, value=3, key="pases_j_loc")
        
        accion_sel_local = streamlit_app.selectbox(
            "Tipo de acción defensiva o desenlace",
            ["Recuperación", "Interceptación", "Entrada / Duelo ganado", "Falta táctica", "sin recuperación"],
            key="select_accion_local"
        )
        
        col_btn_l1, col_btn_l2 = streamlit_app.columns(2)
        with col_btn_l1:
            if streamlit_app.button("🛡️ Registrar Acción y Sumar Pases", key="reg_acc_loc"):
                streamlit_app.session_state.total_pases_local += pases_jugada_local
                
                if accion_sel_local != "Fin de posesión sin recuperación (Rival superó / remató)":
                    streamlit_app.session_state.total_acciones_local += 1
                    streamlit_app.session_state.acciones_local_detalle[accion_sel_local] += 1
                    msg_local = f"+1 {accion_sel_local}"
                else:
                    if "Fin de posesión sin recuperación" not in streamlit_app.session_state.acciones_local_detalle:
                        streamlit_app.session_state.acciones_local_detalle["Fin de posesión sin recuperación"] = 0
                    streamlit_app.session_state.acciones_local_detalle["Fin de posesión sin recuperación"] += 1
                    msg_local = "Fin de posesión (Sin acción defensiva)"
                
                if streamlit_app.session_state.total_acciones_local > 0:
                    streamlit_app.session_state.ppda_local_val = streamlit_app.session_state.total_pases_local / streamlit_app.session_state.total_acciones_local
                
                streamlit_app.success(f"¡Registrado! +{pases_jugada_local} pases | {msg_local}")
                streamlit_app.rerun()
                
        with col_btn_l2:
            if streamlit_app.button("🔄 Reiniciar Local", key="reset_loc"):
                streamlit_app.session_state.total_pases_local = 0
                streamlit_app.session_state.total_acciones_local = 0
                streamlit_app.session_state.acciones_local_detalle = {k: 0 for k in streamlit_app.session_state.acciones_local_detalle}
                streamlit_app.session_state.ppda_local_val = 0.0
                streamlit_app.rerun()

        streamlit_app.markdown("---")
        streamlit_app.markdown("**Estadísticas Acumuladas:**")
        streamlit_app.text(f"• Total Pases Rival Permitidos: {streamlit_app.session_state.total_pases_local}")
        streamlit_app.text(f"• Total Acciones Defensivas: {streamlit_app.session_state.total_acciones_local}")
        for k, v in streamlit_app.session_state.acciones_local_detalle.items():
            streamlit_app.text(f"  - {k}: {v}")

    with col_ppda_rival:
        streamlit_app.markdown(f"#### Presión de: {equipo_visitante}")
        
        pases_jugada_rival = streamlit_app.number_input("Pases nuestros permitidos en nuestro campo", min_value=0, value=3, key="pases_j_riv")
        
        accion_sel_rival = streamlit_app.selectbox(
            "Tipo de acción defensiva o desenlace del rival",
            ["Recuperación", "Interceptación", "Entrada / Duelo ganado", "Falta táctica", "sin recuperación"],
            key="select_accion_rival"
        )
        
        col_btn_r1, col_btn_r2 = streamlit_app.columns(2)
        with col_btn_r1:
            if streamlit_app.button("🛡️ Registrar Acción Rival y Sumar Pases", key="reg_acc_riv"):
                streamlit_app.session_state.total_pases_rival += pases_jugada_rival
                
                if accion_sel_rival != "sin recuperación":
                    streamlit_app.session_state.total_acciones_rival += 1
                    streamlit_app.session_state.acciones_rival_detalle[accion_sel_rival] += 1
                    msg_rival = f"+1 {accion_sel_rival}"
                else:
                    if "Fin de posesión sin recuperación" not in streamlit_app.session_state.acciones_rival_detalle:
                        streamlit_app.session_state.acciones_rival_detalle["Fin de posesión sin recuperación"] = 0
                    streamlit_app.session_state.acciones_rival_detalle["Fin de posesión sin recuperación"] += 1
                    msg_rival = "Fin de posesión (Sin acción defensiva)"
                
                if streamlit_app.session_state.total_acciones_rival > 0:
                    streamlit_app.session_state.ppda_rival_val = streamlit_app.session_state.total_pases_rival / streamlit_app.session_state.total_acciones_rival
                
                streamlit_app.success(f"¡Registrado rival! +{pases_jugada_rival} pases | {msg_rival}")
                streamlit_app.rerun()
                
        with col_btn_r2:
            if streamlit_app.button("🔄 Reiniciar Rival", key="reset_riv"):
                streamlit_app.session_state.total_pases_rival = 0
                streamlit_app.session_state.total_acciones_rival = 0
                streamlit_app.session_state.acciones_rival_detalle = {k: 0 for k in streamlit_app.session_state.acciones_rival_detalle}
                streamlit_app.session_state.ppda_rival_val = 0.0
                streamlit_app.rerun()

        streamlit_app.markdown("---")
        streamlit_app.markdown("**Estadísticas Acumuladas:**")
        streamlit_app.text(f"• Total Pases Nuestros Permitidos: {streamlit_app.session_state.total_pases_rival}")
        streamlit_app.text(f"• Total Acciones Defensivas Rival: {streamlit_app.session_state.total_acciones_rival}")
        for k, v in streamlit_app.session_state.acciones_rival_detalle.items():
            streamlit_app.text(f"  - {k}: {v}")

    streamlit_app.markdown("---")
    streamlit_app.markdown("### 📊 Indicadores Globales de Intensidad de Presión (PPDA)")
    col_metric_1, col_metric_2 = streamlit_app.columns(2)
    with col_metric_1:
        streamlit_app.metric(f"PPDA {equipo_local}", f"{streamlit_app.session_state.ppda_local_val:.2f}", help="Menor número = Presión más intensa y alta.")
    with col_metric_2:
        streamlit_app.metric(f"PPDA {equipo_visitante}", f"{streamlit_app.session_state.ppda_rival_val:.2f}", help="Menor número = Presión más intensa y alta.")

with tab_resumen:
    streamlit_app.markdown("### 📋 Resumen del Partido y Estadísticas Acumuladas")

    col_res_xg1, col_res_xg2 = streamlit_app.columns(2)
    
    xg_local_tot = sum([s['xg'] for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_local]) if streamlit_app.session_state.shots_data else 0.0
    xg_rival_tot = sum([s['xg'] for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_visitante]) if streamlit_app.session_state.shots_data else 0.0

    with col_res_xg1:
        streamlit_app.metric(f"xG Total - {equipo_local}", f"{xg_local_tot:.2f}")
    with col_res_xg2:
        streamlit_app.metric(f"xG Total - {equipo_visitante}", f"{xg_rival_tot:.2f}")

    streamlit_app.markdown("---")
    streamlit_app.markdown("#### 🎯 Desglose de Remates y Resultados")
    
    if streamlit_app.session_state.shots_data:
        remates_local = [s for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_local]
        remates_rival = [s for s in streamlit_app.session_state.shots_data if s['equipo'] == equipo_visitante]

        def contar_resultados(lista_remates):
            # CORREGIDO: Se alinean exactamente los textos y emojis del diccionario con los del selectbox del formulario
            res = {"Gol ⚽": 0, "Fuera ❌": 0, "Atajado 🧤": 0, "Bloqueado 🛡️": 0}
            for r in lista_remates:
                resultado = r.get('resultado', 'Fuera ❌')
                if resultado in res:
                    res[resultado] += 1
                else:
                    # Coincidencia flexible por si hay pequeñas variaciones de emojis en sesiones pasadas
                    found = False
                    for key in res.keys():
                        if key.split()[0] in resultado:
                            res[key] += 1
                            found = True
                            break
                    if not found and "Fuera" in resultado:
                        res["Fuera ❌"] += 1
            return len(lista_remates), res

        total_loc, desglose_loc = contar_resultados(remates_local)
        total_riv, desglose_riv = contar_resultados(remates_rival)

        col_rem_1, col_rem_2 = streamlit_app.columns(2)
        with col_rem_1:
            streamlit_app.markdown(f"**{equipo_local} (Total Remates: {total_loc})**")
            streamlit_app.text(f"⚽ Goles: {desglose_loc['Gol ⚽']}")
            streamlit_app.text(f"❌ Fuera: {desglose_loc['Fuera ❌']}")
            streamlit_app.text(f"🧤 Atajados: {desglose_loc['Atajado 🧤']}")
            streamlit_app.text(f"🛡️️ Bloqueados: {desglose_loc['Bloqueado 🛡️']}")

        with col_rem_2:
            streamlit_app.markdown(f"**{equipo_visitante} (Total Remates: {total_riv})**")
            streamlit_app.text(f"⚽ Goles: {desglose_riv['Gol ⚽']}")
            streamlit_app.text(f"❌ Fuera: {desglose_riv['Fuera ❌']}")
            streamlit_app.text(f"🧤 Atajados: {desglose_riv['Atajado 🧤']}")
            streamlit_app.text(f"🛡️ Bloqueados: {desglose_riv['Bloqueado 🛡️']}")
    else:
        streamlit_app.info("Aún no hay remates registrados en la sesión actual para mostrar el desglose.")

    streamlit_app.markdown("---")
    streamlit_app.markdown("#### 🛡️ Resumen de Intensidad de Presión (PPDA) y Acciones Defensivas")
    
    col_ppda_res1, col_ppda_res2 = streamlit_app.columns(2)

    with col_ppda_res1:
        ppda_l = streamlit_app.session_state.get('ppda_local_val', 0.0)
        streamlit_app.metric(f"PPDA - {equipo_local}", f"{ppda_l:.2f}")
        streamlit_app.text(f"Pases Totales Rival Permitidos: {streamlit_app.session_state.total_pases_local}")
        streamlit_app.text(f"Acciones Defensivas Totales: {streamlit_app.session_state.total_acciones_local}")

    with col_ppda_res2:
        ppda_r = streamlit_app.session_state.get('ppda_rival_val', 0.0)
        streamlit_app.metric(f"PPDA - {equipo_visitante}", f"{ppda_r:.2f}")
        streamlit_app.text(f"Pases Totales Nuestros Permitidos: {streamlit_app.session_state.total_pases_rival}")
        streamlit_app.text(f"Acciones Defensivas Rival: {streamlit_app.session_state.total_acciones_rival}")

    streamlit_app.markdown("---")
    streamlit_app.markdown("#### ⏱️ Historial de Eventos del Partido")
    if streamlit_app.session_state.shots_data:
        for idx, shot in enumerate(streamlit_app.session_state.shots_data, 1):
            streamlit_app.text(f"{idx}. Remate de {shot.get('jugador', 'Jugador')} ({shot.get('equipo', 'Equipo')}) - xG: {shot.get('xg', 0):.2f} [{shot.get('resultado', 'Acción')}]")
    else:
        streamlit_app.text("No hay eventos registrados todavía.")

    streamlit_app.markdown("---")
    streamlit_app.markdown("#### 📥 Exportar Datos del Partido")
    streamlit_app.markdown("Descarga los registros de remates y métricas del encuentro para tus informes analíticos.")

    if streamlit_app.session_state.shots_data:
        df_remates = pd.DataFrame(streamlit_app.session_state.shots_data)

        col_down_1, col_down_2 = streamlit_app.columns(2)

        csv_data = df_remates.to_csv(index=False).encode('utf-8')
        with col_down_1:
            streamlit_app.download_button(
                label="📄 Descargar Datos en CSV",
                data=csv_data,
                file_name="remates_partido.csv",
                mime="text/csv",
                use_container_width=True
            )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_remates.to_excel(writer, index=False, sheet_name='Remates y xG')
        excel_data = output.getvalue()

        with col_down_2:
            streamlit_app.download_button(
                label="📊 Descargar Datos en Excel (.xlsx)",
                data=excel_data,
                file_name="remates_partido.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        streamlit_app.info("Registra al menos un remate en la pestaña de mapa para habilitar las opciones de descarga.")