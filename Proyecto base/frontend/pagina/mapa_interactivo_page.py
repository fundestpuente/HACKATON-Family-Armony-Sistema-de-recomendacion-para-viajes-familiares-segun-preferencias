import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from folium import plugins
from streamlit.components.v1 import html
import time
from folium.plugins import BeautifyIcon


API_URL = "http://localhost:8000"

def get_location_component():
    """obtiene y retorna la ubicación GPS"""
    timestamp = int(time.time() * 100)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 10px;
                text-align: center;
            }}
            .status {{
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .loading {{ background-color: #fff3cd; color: #856404; }}
            .success {{ background-color: #d4edda; color: #155724; }}
            .error {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div id="status" class="status loading">
            Obteniendo ubicación GPS...
        </div>
        <div id="coords"></div>
        
        <script>
            const statusDiv = document.getElementById('status');
            const coordsDiv = document.getElementById('coords');
            
            function sendToStreamlit(data) {{
                // Método 1: postMessage
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: data
                }}, '*');
                
                // Método 2: Actualizar URL con query params (fallback)
                if (data.success) {{
                    const params = new URLSearchParams(window.parent.location.search);
                    params.set('gps_lat', data.lat);
                    params.set('gps_lon', data.lon);
                    params.set('gps_acc', data.accuracy);
                    params.set('gps_time', '{timestamp}');
                    
                    const newUrl = window.parent.location.pathname + '?' + params.toString();
                    window.parent.history.replaceState(null, '', newUrl);
                }}
            }}
            
            if (!navigator.geolocation) {{
                statusDiv.className = 'status error';
                statusDiv.innerHTML = 'Geolocalización no soportada';
                sendToStreamlit({{
                    error: 'Geolocalización no soportada',
                    success: false
                }});
            }} else {{
                navigator.geolocation.getCurrentPosition(
                    function(position) {{
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        statusDiv.className = 'status success';
                        statusDiv.innerHTML = 'Ubicación obtenida exitosamente';
                        
                        
                        sendToStreamlit({{
                            lat: lat,
                            lon: lon,
                            accuracy: acc,
                            success: true,
                            timestamp: '{timestamp}'
                        }});
                    }},
                    function(error) {{
                        let errorMsg = '';
                        switch(error.code) {{
                            case error.PERMISSION_DENIED:
                                errorMsg = 'Permiso denegado por el usuario';
                                break;
                            case error.POSITION_UNAVAILABLE:
                                errorMsg = 'Ubicación no disponible';
                                break;
                            case error.TIMEOUT:
                                errorMsg = 'Tiempo de espera agotado';
                                break;
                            default:
                                errorMsg = 'Error desconocido';
                        }}
                        
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `${{errorMsg}}`;
                        
                        sendToStreamlit({{
                            error: errorMsg,
                            success: false
                        }});
                    }},
                    {{
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }}
                );
            }}
        </script>
    </body>
    </html>
    """

def render_mapa_google_page():
    """Mapa interactivo con GPS automático"""

    st.title(" Mapa interactivo de destinos")

    gps_text = "GPS" if st.session_state.get("gps_obtenido", False) else "Manual"

    if 'recomendaciones_mapa' not in st.session_state:
        st.session_state.recomendaciones_mapa = []

    if 'ubicacion_actual_mapa' not in st.session_state:
        st.session_state.ubicacion_actual_mapa = {
            "lat": -1.8312,
            "lon": -78.1834,
            "nombre": "Ecuador"
        }

    if 'destino_cercano_mapa' not in st.session_state:
        st.session_state.destino_cercano_mapa = None

    if 'gps_obtenido' not in st.session_state:
        st.session_state.gps_obtenido = False
    
    if 'mostrar_gps_widget' not in st.session_state:
        st.session_state.mostrar_gps_widget = False
    
    if 'last_gps_timestamp' not in st.session_state:
        st.session_state.last_gps_timestamp = None

    # Verificar si hay datos GPS en query params
    query_params = st.query_params
    if 'gps_lat' in query_params and 'gps_lon' in query_params:
        gps_timestamp = query_params.get('gps_time', '')
        
        # Solo actualizar si es un timestamp nuevo
        if gps_timestamp != st.session_state.last_gps_timestamp:
            try:
                lat = float(query_params['gps_lat'])
                lon = float(query_params['gps_lon'])
                acc = float(query_params.get('gps_acc', 0))
                
                st.session_state.ubicacion_actual_mapa = {
                    "lat": lat,
                    "lon": lon,
                    "nombre": "Mi ubicación GPS"
                }
                st.session_state.gps_obtenido = True
                st.session_state.mostrar_gps_widget = False
                st.session_state.last_gps_timestamp = gps_timestamp
                
                # Limpiar query params
                st.query_params.clear()
                st.success(f"Ubicación GPS actualizada (±{acc:.0f}m)")
                st.rerun()
            except (ValueError, TypeError):
                pass

    # LAYOUT PRINCIPAL: MAPA + CONFIG 
    col_mapa, col_config = st.columns([2.5, 1])

    with col_mapa:
        #  DETERMINAR CENTRO 
        if st.session_state.destino_cercano_mapa:
            center = [
                st.session_state.destino_cercano_mapa["lat"],
                st.session_state.destino_cercano_mapa["lon"]
            ]
            zoom = 11

        elif st.session_state.recomendaciones_mapa:
            avg_lat = sum(r['lat'] for r in st.session_state.recomendaciones_mapa) / len(st.session_state.recomendaciones_mapa)
            avg_lon = sum(r['lon'] for r in st.session_state.recomendaciones_mapa) / len(st.session_state.recomendaciones_mapa)
            center = [avg_lat, avg_lon]
            zoom = 9

        else:
            center = [
                st.session_state.ubicacion_actual_mapa['lat'],
                st.session_state.ubicacion_actual_mapa['lon']
            ]
            zoom = 7

        # CREAR MAPA 
        m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")
        plugins.Fullscreen().add_to(m)

        # UBICACIÓN ACTUAL
        icon_color = "green" if st.session_state.gps_obtenido else "blue"
        icon_symbol = "satellite" if st.session_state.gps_obtenido else "home"
        
        folium.Marker(
            location=[
                st.session_state.ubicacion_actual_mapa["lat"],
                st.session_state.ubicacion_actual_mapa["lon"]
            ],
            popup=f"""
            <b> {st.session_state.ubicacion_actual_mapa['nombre']}</b><br>
             {st.session_state.ubicacion_actual_mapa['lat']:.6f}, {st.session_state.ubicacion_actual_mapa['lon']:.6f}<br>
             Ubicación {gps_text}
            """,
            tooltip="Tu ubicación actual",
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
        ).add_to(m)

        # --------- DESTINO MÁS CERCANO ----------
        if st.session_state.destino_cercano_mapa:
            dest = st.session_state.destino_cercano_mapa

            folium.Marker(
                location=[dest["lat"], dest["lon"]],
                popup=f"""
                <b> {dest['nombre']}</b><br>
                 {dest['provincia']}<br>
                ⭐ {dest['score']:.2f}/5<br>
                📏 {dest['distancia_km']} km
                """,
                tooltip=f" {dest['nombre']}",
                icon=folium.Icon(color="red", icon="star", prefix="fa")
            ).add_to(m)

        # --------- RECOMENDACIONES ----------
        for idx, rec in enumerate(st.session_state.recomendaciones_mapa, 1):
            score = rec.get("predicted_score") or rec.get("score_general", 0)

            folium.Marker(
                location=[rec["lat"], rec["lon"]],
                popup=f"""
                <b>#{idx} {rec['nombre']}</b><br>
                 {rec['provincia']}<br>
                 {score:.2f}/5
                """,
                tooltip=f"#{idx} {rec['nombre']}",
                icon=folium.Icon(color="orange", icon="map-marker", prefix="fa")
            ).add_to(m)

        st_folium(m, height=650, use_container_width=True)

    # ================= PANEL DERECHO: CONFIGURACIÓN =================
    with col_config:
        st.markdown("###  Configuración")
        
        modo = st.radio(
            "Modo de búsqueda:",
            [" Mi ubicación", " Por tipo", " Más cercano"],
            key="modo_mapa"
        )

        st.markdown("---")

        # ================= MODO: UBICACIÓN =================
        if modo == " Mi ubicación":
            st.markdown("**Tu ubicación**")

            # Botón para obtener GPS
            if st.button(" Obtener GPS", type="primary", use_container_width=True):
                st.session_state.mostrar_gps_widget = True
                st.rerun()

            # Mostrar widget de GPS si fue activado
            if st.session_state.mostrar_gps_widget:
                location_data = html(get_location_component(), height=160)
                
                # Procesar datos si llegan por postMessage
                if location_data is not None and isinstance(location_data, dict):
                    if location_data.get('success'):
                        st.session_state.ubicacion_actual_mapa = {
                            "lat": location_data['lat'],
                            "lon": location_data['lon'],
                            "nombre": "Mi ubicación GPS"
                        }
                        st.session_state.gps_obtenido = True
                        st.session_state.mostrar_gps_widget = False
                        st.session_state.last_gps_timestamp = location_data.get('timestamp')
                        st.success(f"GPS actualizado (±{location_data.get('accuracy', 0):.0f}m)")
                        st.rerun()
                    elif not location_data.get('success'):
                        st.error(f"{location_data.get('error', 'Error desconocido')}")
                        st.session_state.mostrar_gps_widget = False
                
                # Botón para cerrar el widget si tarda mucho
                if st.button(" Cancelar", type="secondary", use_container_width=True):
                    st.session_state.mostrar_gps_widget = False
                    st.rerun()

            st.markdown("**O ingresa manualmente:**")

            lat_actual = st.number_input(
                "Latitud", 
                value=st.session_state.ubicacion_actual_mapa["lat"], 
                format="%.6f",
                key="lat_input"
            )
            
            lon_actual = st.number_input(
                "Longitud", 
                value=st.session_state.ubicacion_actual_mapa["lon"], 
                format="%.6f",
                key="lon_input"
            )

            nombre = st.text_input("Nombre", st.session_state.ubicacion_actual_mapa["nombre"])

            if st.button(" Actualizar", type="secondary", use_container_width=True):
                st.session_state.ubicacion_actual_mapa = {
                    "lat": lat_actual,
                    "lon": lon_actual,
                    "nombre": nombre
                }
                st.session_state.gps_obtenido = False
                st.success("Ubicación actualizada")
                st.rerun()

            # Mostrar ubicación actual
            st.markdown("---")
            st.info(f"""
            **Ubicación actual:**  
             {st.session_state.ubicacion_actual_mapa['nombre']}  
            Lat: {st.session_state.ubicacion_actual_mapa['lat']:.6f}  
            Lon: {st.session_state.ubicacion_actual_mapa['lon']:.6f}  
             {gps_text}
            """)

        # POR TIPO 
        elif modo == " Por tipo":
            st.markdown("**Buscar por tipo**")

            tipo_destino = st.selectbox(
                "Tipo de destino",
                [
                    "playas", "museos", "parques", "restaurantes",
                    "hoteles", "centros_comerciales",
                    "teatros", "iglesias", "zoologicos",
                    "bares_pubs", "monumentos"
                ]
            )

            provincia = st.selectbox(
                "Provincia",
                ["Todas", "SANTA ELENA", "PICHINCHA", "GUAYAS", "MANABÍ", "AZUAY"]
            )

            cantidad = st.slider("Cantidad", 5, 30, 10)

            if st.button("🔍 Buscar", type="primary", use_container_width=True):
                try:
                    params = {"tipo": tipo_destino, "top_k": cantidad}
                    if provincia != "Todas":
                        params["provincia"] = provincia

                    with st.spinner("Buscando..."):
                        r = requests.get(
                            f"{API_URL}/api/family/destinos_por_tipo",
                            params=params,
                            timeout=30
                        )

                    if r.status_code == 200:
                        st.session_state.recomendaciones_mapa = r.json()["resultados"]
                        st.success(f"{len(st.session_state.recomendaciones_mapa)} destinos encontrados")
                    else:
                        st.error("Error en el API")
                except Exception as e:
                    st.error(f"{str(e)}")

        # ================= MÁS CERCANO =================
        elif modo == " Más cercano":
            st.markdown("**Destino más cercano**")

            tipo = st.selectbox(
                "Tipo",
                ["Cualquiera", "playas", "museos", "parques", "restaurantes", "hoteles"]
            )

            min_score = st.slider("Score mínimo", 0.0, 5.0, 2.0, 0.1)

            if st.button(" Buscar cercano", type="primary", use_container_width=True):
                try:
                    params = {
                        "lat": st.session_state.ubicacion_actual_mapa["lat"],
                        "lon": st.session_state.ubicacion_actual_mapa["lon"],
                        "min_score": min_score
                    }
                    if tipo != "Cualquiera":
                        params["tipo"] = tipo

                    with st.spinner("Buscando..."):
                        r = requests.get(
                            f"{API_URL}/api/family/destino_mas_cercano",
                            params=params,
                            timeout=30
                        )

                    if r.status_code == 200:
                        st.session_state.destino_cercano_mapa = r.json()
                        st.success("Destino encontrado")
                    else:
                        st.error("Error en el API")
                except Exception as e:
                    st.error(f"{str(e)}")

        # ESTADÍSTICAS 
        st.markdown("---")
        st.markdown("###  Estadísticas")

        #  DESTINO MÁS CERCANO 
        if st.session_state.destino_cercano_mapa:
            dest = st.session_state.destino_cercano_mapa

            st.metric("Destino", dest["nombre"])
            st.metric("Score", f"{dest['score']:.2f}/5")
            st.metric("Distancia", f"{dest['distancia_km']} km")

            st.markdown("**Ubicación:**")
            st.markdown(f"""
             {dest.get('provincia', 'N/A')}  
             {dest.get('canton', 'N/A')}
            """)

        # RECOMENDACIONES 
        elif st.session_state.recomendaciones_mapa:
            st.metric("Destinos", len(st.session_state.recomendaciones_mapa))

            scores = [
                r.get('predicted_score') or r.get('score_general') or 0
                for r in st.session_state.recomendaciones_mapa
            ]

            if scores:
                promedio = sum(scores) / len(scores)
                st.metric("Promedio", f"{promedio:.2f}/5")
                st.metric("Mejor", f"{max(scores):.2f}/5")

        else:
            st.info("Selecciona un modo de búsqueda para comenzar.")

        st.markdown("---")


        if st.button(" Limpiar resultados", use_container_width=True):
            st.session_state.recomendaciones_mapa = []
            st.session_state.destino_cercano_mapa = None
            st.rerun()


    # TABLA DE RESULTADOS 
    if st.session_state.recomendaciones_mapa:
        st.markdown("---")
        st.subheader("📋 Tabla de resultados")
        
        df = pd.DataFrame(st.session_state.recomendaciones_mapa)
        
        # Seleccionar columnas relevantes si existen
        cols_mostrar = []
        if 'nombre' in df.columns:
            cols_mostrar.append('nombre')
        if 'provincia' in df.columns:
            cols_mostrar.append('provincia')
        if 'predicted_score' in df.columns:
            cols_mostrar.append('predicted_score')
        elif 'score_general' in df.columns:
            cols_mostrar.append('score_general')
        
        if cols_mostrar:
            st.dataframe(df[cols_mostrar], use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)