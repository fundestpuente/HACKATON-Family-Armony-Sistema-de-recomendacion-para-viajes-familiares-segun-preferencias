

> **Sistema Inteligente de Recomendación para Vacaciones Familiares**

Este proyecto unifica un **Backend analítico (FastAPI + XGBoost)** con un **Frontend interactivo (Streamlit)** para revolucionar la planificación de viajes grupales.

La herramienta va más allá de un simple buscador; actúa como un "Árbitro Inteligente" diseñado para resolver la complejidad de los viajes en grupo. Ofrece **tres motores de búsqueda independientes** para adaptarse a la necesidad del momento: consenso por gustos (IA), logística por cercanía (Geolocalización) o búsqueda directa por tipo de lugar. Además, integra visualización geoespacial en todas sus respuestas para facilitar la toma de decisiones.

---

##  Características Principales

El sistema opera bajo una arquitectura cliente-servidor modular.

* **Gestión Dinámica de Grupos:** Ingreso flexible de *N* cantidad de participantes con roles específicos (Padres, Hijos, Abuelos).
* **Motor de Recomendación Híbrido (3 Modos):**
    1.  **Por Preferencias (AI):** Usa **XGBoost** para cruzar los perfiles de gusto (Cultural, Recreación, etc.) y predecir el destino que maximiza la felicidad colectiva.
    2.  **Por Ubicación:** Algoritmo de proximidad para encontrar destinos cercanos al hogar del usuario.
    3.  **Por Tipo de Lugar:** Filtrado directo para búsquedas específicas (ej. "Solo Parques Nacionales").
* **Mapas Interactivos:** Implementación de **Folium** para visualizar la ubicación exacta y rutas de cada recomendación en cualquiera de los tres modos.
* **Dashboard Analítico (Modo Preferencias):** Panel avanzado con gráficos de radar y estadísticas de compatibilidad que justifican matemáticamente por qué un destino es el ideal para el grupo.

---

##  Estructura del Proyecto

```text
SIC-FAMILY-ARMONY-AI/
├── api/                          # Backend (Lógica y Modelo AI)
│   ├── app/                      # Código fuente de la API
│   └── .env                      # Configuración del servidor
├── data/                         # Datos procesados y análisis
│   ├── AnalisisExploratorio.ipynb
│   ├── datos_sintetico.csv
│   └── nuevos_viajes.csv
├── datasets_base/                # Fuentes de datos originales
│   ├── atractivos_tur.csv
│   └── google_review_ratings.csv
├── frontend/                     # Frontend (Interfaz de Usuario)
│   ├── .streamlit/               # Configuración de estilos
│   ├── pagina/                   # Módulos: Familia, Recomendaciones (3 tabs), Análisis
│   ├── utils/                    # Funciones auxiliares y renderizado de mapas
│   ├── app.py                    # Punto de entrada de Streamlit
│   └── .env                      # Configuración del cliente
├── generar_data_sintetica_...py  # Script para generación de datos de entrenamiento
├── union_y_preprocesamiento.py   # Script ETL de limpieza y unión de datos
└── .gitignore

```

---

##  Guía de Instalación y Ejecución

Para levantar el sistema completo, necesitarás dos terminales: una para el cerebro (API) y otra para la interfaz (Frontend).

### 1. Clonar el Repositorio

```bash
git clone [https://github.com/fundestpuente/HACKATON-Family-Armony-Sistema-de-recomendacion-para-viajes-familiares-segun-preferencias.git](https://github.com/fundestpuente/HACKATON-Family-Armony-Sistema-de-recomendacion-para-viajes-familiares-segun-preferencias.git)
cd HACKATON-Family-Armony...

```

### 2. Configurar el Backend (Terminal A)

```bash
# Navegar a la carpeta del servidor
cd api

# Instalar dependencias de IA y API
pip install fastapi uvicorn[standard] pandas numpy scikit-learn xgboost python-dotenv python-multipart

# Configurar variables de entorno
# Crea un archivo .env y agrega:
echo "DATA_PATH=../data/datos_sintetico.csv" > .env
echo "PORT=8000" >> .env

# Levantar el servidor
uvicorn app.main:app --reload --port 8000

```

> **Estado:** La API estará escuchando en `http://localhost:8000` y la documentación en `/docs`.

### 3. Configurar el Frontend (Terminal B)

```bash
# Navegar a la carpeta de la interfaz
cd frontend

# Instalar librerías gráficas y de mapas
pip install streamlit requests python-dotenv plotly pandas numpy streamlit-option-menu streamlit-folium folium

# Configurar conexión con el backend
# Crea un archivo .env y agrega:
echo "API_BASE_URL=http://localhost:8000" > .env

# Iniciar la aplicación
streamlit run app.py

# Personalizado (puerto específico)
streamlit run app.py --server.port 8501 --server.address localhost

```

> **Estado:** La Web App se abrirá en `http://localhost:8501`

---

##  Flujo de Uso

### 1. Configuración (Sidebar & Home)

El usuario define los parámetros del grupo familiar.

### 2. Módulo de Recomendaciones (Pestañas Independientes)

El sistema ofrece flexibilidad total mediante tres pestañas:

* **Por Preferencias:** El usuario califica 6 categorías. El modelo AI retorna el Top Destinos optimizados para el grupo, mostrados en un mapa interactivo.
* **Por Ubicación:** El usuario ingresa su ciudad. El sistema muestra los atractivos más cercanos en el mapa.
* **Por Tipo:** El usuario selecciona una categoría específica. El sistema filtra y geolocaliza las opciones.

### 3. Módulo de Análisis (Dashboard)

Exclusivo para la búsqueda por **Preferencias**. Al seleccionar un destino recomendado por la IA:

* Visualización de **Gráficos de Radar** comparando el perfil del destino vs. el perfil de la familia.
* Métricas de **Compatibilidad (%)** para transparencia en la decisión.


