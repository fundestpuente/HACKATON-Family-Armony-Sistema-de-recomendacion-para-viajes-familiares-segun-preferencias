import streamlit as st
import folium
from streamlit_folium import st_folium
from folium import plugins

from utils.api_client import APIClient, format_family_data
from utils.helpers import clean_member_preferences


def search_destinations_simple(top_k):
    try:
        clean_members = []

        for member in st.session_state.family_members:
            clean_members.append({
                "nombre": str(member.get("nombre", "")).strip(),
                "rol": member.get("rol", "Otro"),
                "preferencias": clean_member_preferences(member)
            })

        st.session_state.family_members = clean_members
        family_data = format_family_data(clean_members)

        result = APIClient.get_recommendations(family_data, top_k)

        if result and "recommendations" in result:
            st.session_state.recommendations = result["recommendations"]
            return True

    except Exception as e:
        st.error(f"Error: {e}")

    return False



# MAPA DE RECOMENDACIONES

def render_mapa_recomendaciones(recommendations):
    if not recommendations:
        return None

    avg_lat = sum(r["lat"] for r in recommendations) / len(recommendations)
    avg_lon = sum(r["lon"] for r in recommendations) / len(recommendations)

    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=9,
        tiles="OpenStreetMap"
    )

    plugins.Fullscreen().add_to(m)

    for idx, rec in enumerate(recommendations, 1):
        score = rec.get("predicted_score", 0)
        distancia = rec.get("distancia_km")

        if score >= 4:
            color, icon = "green", "trophy"
        elif score >= 3:
            color, icon = "orange", "star"
        else:
            color, icon = "red", "map-marker"

        distancia_html = (
            f"<p><b><i class='fas fa-road'></i> Distancia:</b> {distancia} km</p>"
            if distancia is not None else ""
        )

        popup_html = f'''
        <div style="width: 230px">
            <h4><i class="fas fa-map-pin"></i> #{idx} {rec['nombre']}</h4>
            <p><b><i class="fas fa-map-marker-alt"></i></b> {rec['provincia']}, {rec['canton']}</p>
            <p><b><i class="fas fa-star"></i> Score:</b> {score:.2f}/5</p>
            {distancia_html}
        </div>
        '''

        folium.Marker(
            location=[rec["lat"], rec["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"#{idx} - {rec['nombre']}",
            icon=folium.Icon(color=color, icon=icon, prefix="fa")
        ).add_to(m)

        # Número ranking
        folium.Marker(
            location=[rec["lat"], rec["lon"]],
            icon=folium.DivIcon(html=f'''
                <div style="
                    background:white;
                    border:2px solid #1976d2;
                    border-radius:50%;
                    width:24px;
                    height:24px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-weight:bold;
                    font-size:12px;
                    color:#1976d2;
                ">{idx}</div>
            ''')
        ).add_to(m)

    return m



def render_recomendaciones_page():
    
    # Validar
    if not st.session_state.family_members:
        st.markdown('''
            <div class="warning-message">
                <i class="fas fa-users" style="color: #FFA726;"></i>
                Primero agrega miembros de familia para obtener recomendaciones.
            </div>
        ''', unsafe_allow_html=True)
        return
    
    total_prefs = sum(
        sum(len(cat) for cat in m.get('preferencias', {}).values())
        for m in st.session_state.family_members
    )
    
    if total_prefs < 3:
        st.markdown(f'''
            <div class="error-message">
                <i class="fas fa-exclamation-triangle" style="color: #f44336;"></i>
                <div>
                    <strong>Necesitas al menos 3 preferencias en total.</strong><br>
                    Tienes {total_prefs} preferencias. Agrega más para mejores recomendaciones.
                </div>
            </div>
        ''', unsafe_allow_html=True)
        return
    
    # Título principal
    st.markdown('''
        <h2 style="margin-bottom: 20px; color: #2c3e50; font-weight: 600;">
            <i class="fas fa-map-marked-alt" style="margin-right: 10px;"></i>Recomendaciones de Destinos
        </h2>
    ''', unsafe_allow_html=True)
    
    # Sección de configuración de búsqueda
    st.markdown('''
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h4 style="color: white; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-sliders-h"></i>Configurar Búsqueda
            </h4>
        </div>
    ''', unsafe_allow_html=True)
    
    # Configuración de búsqueda
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        progress_value = min(total_prefs / 20, 1.0)
        st.markdown(f'''
            <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-chart-line" style="color: #4361EE;"></i>
                <strong>Completitud de datos:</strong>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown(f'''
            <div style="background: #e0e0e0; border-radius: 10px; height: 12px; margin-bottom: 5px;">
                <div style="background: linear-gradient(90deg, #4CAF50, #8BC34A); 
                            width: {progress_value*100}%; height: 100%; 
                            border-radius: 10px;"></div>
            </div>
            <div style="font-size: 0.85rem; color: #666; display: flex; align-items: center; gap: 10px;">
                <span><i class="fas fa-users"></i> {len(st.session_state.family_members)} miembros</span>
                <span>•</span>
                <span><i class="fas fa-heart"></i> {total_prefs} preferencias</span>
            </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        top_k = st.selectbox(
            "Número de destinos",
            [3, 5, 10],
            format_func=lambda x: f"{x} destinos",
            help="Selecciona cuántos destinos quieres ver"
        )
    
    with col3:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        if st.button('Buscar Destinos', type="primary", use_container_width=True):
            with st.spinner('Analizando preferencias familiares...'):
                if search_destinations_simple(top_k):
                    st.markdown(f'''
                        <div class="success-message">
                            <i class="fas fa-check-circle" style="color: #4CAF50;"></i>
                            Encontrados {len(st.session_state.recommendations)} destinos
                        </div>
                    ''', unsafe_allow_html=True)
                    st.rerun()
                else:
                    st.markdown('''
                        <div class="error-message">
                            <i class="fas fa-times-circle" style="color: #f44336;"></i>
                            No se pudieron encontrar destinos. Intenta nuevamente.
                        </div>
                    ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Mostrar resultados si existen
    if st.session_state.recommendations:
        st.markdown('''
            <h3 style="margin: 25px 0 15px 0; color: #2c3e50; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-star" style="color: #FFD700;"></i>Destinos Recomendados para tu Familia
            </h3>
        ''', unsafe_allow_html=True)
        
        col_recomendaciones, col_mapa = st.columns([3, 7])
        
        with col_recomendaciones:
            st.markdown('<div class="custom-scroll">', unsafe_allow_html=True)
            
            # Mostrar destinos
            for idx, dest in enumerate(st.session_state.recommendations):
                card_colors = [
                    "linear-gradient(135deg, #667eea 10%, #764ba2 90%)",
                    "linear-gradient(135deg, #f093fb 10%, #f5576c 90%)", 
                    "linear-gradient(135deg, #4facfe 10%, #00f2fe 90%)",
                    "linear-gradient(135deg, #43e97b 10%, #38f9d7 90%)",
                    "linear-gradient(135deg, #fa709a 10%, #fee140 90%)"
                ]
                
                color_idx = idx % len(card_colors)
                score = dest.get('predicted_score', 0)
                
                stars_full = int(score)
                has_half = (score - stars_full) >= 0.5
                stars_empty = 5 - stars_full - (1 if has_half else 0)
                
                stars_html = '<i class="fas fa-star" style="color: #FFD700; font-size: 0.9rem;"></i>' * stars_full
                if has_half:
                    stars_html += '<i class="fas fa-star-half-alt" style="color: #FFD700; font-size: 0.9rem;"></i>'
                stars_html += '<i class="far fa-star" style="color: #FFD700; font-size: 0.9rem;"></i>' * stars_empty
                
                # Tarjeta 
                card_html = f'''
                <div style="
                    background: {card_colors[color_idx]};
                    border-radius: 10px;
                    padding: 12px;
                    color: white;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 5px;">
                                <span style="background: white; color: #2c3e50; font-weight: bold; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">
                                    #{idx+1}
                                </span>
                                <h4 style="margin: 0; font-size: 1rem; color: white;">
                                    <i class="fas fa-map-pin"></i> {dest.get('nombre', '')}
                                </h4>
                            </div>
                            <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 6px; font-size: 0.85rem;">
                                <i class="fas fa-map-marker-alt"></i>
                                <span>{dest.get('provincia', '')}, {dest.get('canton', '')}</span>
                            </div>
                            <div style="margin-top: 8px;">
                                {stars_html}
                            </div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.2); 
                            padding: 4px 10px; 
                            border-radius: 15px;
                            font-weight: bold;
                            font-size: 0.9rem;
                            display: flex;
                            align-items: center;
                            gap: 4px;
                            min-width: 55px;
                            justify-content: center;
                        ">
                            <i class="fas fa-chart-bar"></i>{score:.1f}
                        </div>
                    </div>
                </div>
                '''
                st.markdown(card_html, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_mapa:
            st.markdown('''
                <div style="margin-bottom: 10px; display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-map" style="color: #4361EE; font-size: 1.2rem;"></i>
                    <h4 style="margin: 0; color: #2c3e50;">Ubicación de los destinos</h4>
                </div>
                <p style="color: #666; font-size: 0.9rem; margin-bottom: 15px;">
                    <i class="fas fa-info-circle"></i> Haz clic en los marcadores para más detalles
                </p>
            ''', unsafe_allow_html=True)
            
            # Renderizar mapa
            mapa = render_mapa_recomendaciones(st.session_state.recommendations)
            if mapa:
                st_folium(mapa, height=500, use_container_width=True)
    
    else:
        # Estado cuando no hay recomendaciones
        st.markdown(f'''
            <div style="
                text-align: center;
                padding: 40px 20px;
                background: #f8f9fa;
                border-radius: 12px;
                margin-top: 20px;
            ">
                <div style="font-size: 2.5rem; margin-bottom: 15px; color: #4CAF50;">
                    <i class="fas fa-umbrella-beach"></i>
                </div>
                <h3 style="color: #2c3e50; margin-bottom: 10px;">
                    Listo para encontrar destinos perfectos
                </h3>
                <p style="color: #666; max-width: 500px; margin: 0 auto;">
                    Haz clic en "Buscar Destinos" para encontrar recomendaciones personalizadas.
                </p>
                <div style="margin-top: 20px; color: #999; font-size: 0.85rem; display: flex; align-items: center; justify-content: center; gap: 10px;">
                    <i class="fas fa-chart-pie"></i>
                    Basado en {len(st.session_state.family_members)} miembros familiares
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        if total_prefs < 10:
            st.info(f"Sugerencia: Agrega más preferencias ({10 - total_prefs} más) para obtener recomendaciones más precisas.")