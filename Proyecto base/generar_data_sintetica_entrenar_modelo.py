import pandas as pd
import numpy as np
import random

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from category_encoders import TargetEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from xgboost import XGBRegressor

# =======================================================
# Cargar Dataset
# =======================================================
print("Cargando dataset original...")
df = pd.read_csv("reseñas_con_atractivos_turisticos.csv", sep="|")
print(f"Dataset cargado: {len(df)} filas")
# =======================================================
# columnas
# =======================================================
num_cols = [c for c in df.columns if "Calif promedio" in c]
cat_cols = ["provincia", "canton", "parroquia"]

print(f"Columnas numéricas: {len(num_cols)}")
print(f"Columnas categóricas: {len(cat_cols)}")

# =======================================================
# eliminar columnas NO deseadas
# =======================================================
df = df.drop(columns=[
    "ID unico de usuario",
    "user_id",
    "desc_",
    "desc2",
    "desc3"
], errors="ignore")

# =======================================================
# Crear SCORE
# =======================================================
df["score"] = df[num_cols].mean(axis=1)
target = "score"

# =======================================================
# Eliminar filas vacías
# =======================================================
df = df.dropna(subset=num_cols + cat_cols)
print(f"Después de limpiar: {len(df)} filas")

# =======================================================
# Mapas de coordenadas por ubicación
# =======================================================
print("\nCreando mapas de coordenadas...")

# Agrupar por provincia/canton/parroquia y calcular coordenadas promedio
coord_map = df.groupby(['provincia', 'canton', 'parroquia']).agg({
    'lat': 'mean',
    'lon': 'mean',
    'nombre': lambda x: list(x.unique())
}).to_dict('index')

# Backup: coordenadas por provincia/canton (si parroquia no tiene datos)
coord_canton_map = df.groupby(['provincia', 'canton']).agg({
    'lat': 'mean',
    'lon': 'mean'
}).to_dict('index')

# Backup: coordenadas por provincia (si canton no tiene datos)
coord_prov_map = df.groupby('provincia').agg({
    'lat': 'mean',
    'lon': 'mean'
}).to_dict('index')

print(f"Mapas creados:")
print(f"   • Parroquias con coordenadas: {len(coord_map)}")
print(f"   • Cantones con coordenadas: {len(coord_canton_map)}")
print(f"   • Provincias con coordenadas: {len(coord_prov_map)}")


# =======================================================
# Generar Datos Sintéticos
# =======================================================
print(f"\nGenerando datos sintéticos...")

N = 3000
sintetico = pd.DataFrame()

# ---------- Simulación multivariada ----------
print("   • Generando calificaciones...")
cov_matrix = np.cov(df[num_cols].values.T)
mean_vector = df[num_cols].mean().values


vals = np.random.multivariate_normal(
    mean=mean_vector,
    cov=cov_matrix * 0.4,
    size=N
)

for i, col in enumerate(num_cols):
    sintetico[col] = np.clip(vals[:, i], 0, 5)

# ---------- Categóricas realistas ----------
print("   • Generando ubicaciones...")
pc_map = df.groupby("provincia")["canton"].unique().to_dict()
cp_map = df.groupby("canton")["parroquia"].unique().to_dict()
provincias = df["provincia"].unique()

def generar_registro_categ():
    prov = np.random.choice(provincias)
    canton = np.random.choice(pc_map[prov])
    parroquia = np.random.choice(cp_map[canton])
    return prov, canton, parroquia

cats = [generar_registro_categ() for _ in range(N)]
cats = pd.DataFrame(cats, columns=cat_cols)
sintetico[cat_cols] = cats

# ---------- Generar coordenadas y nombres ----------
print("   • Generando coordenadas y nombres...")

nombres_sinteticos = []
lats_sinteticas = []
lons_sinteticas = []

# Prefijos para nombres sintéticos
prefijos = [
    "Mirador", "Parque", "Plaza", "Centro", "Museo", "Iglesia",
    "Complejo", "Reserva", "Playa", "Laguna", "Cascada", "Sendero",
    "Jardín", "Monumento", "Mercado", "Terminal", "Zona", "Balneario"
]

for idx, row in sintetico.iterrows():
    prov = row['provincia']
    canton = row['canton']
    parroquia = row['parroquia']
    
    # Intentar obtener coordenadas en orden de precisión
    key_parroquia = (prov, canton, parroquia)
    key_canton = (prov, canton)
    
    if key_parroquia in coord_map:
        # Usar coordenadas de la parroquia con pequeña variación
        lat_base = coord_map[key_parroquia]['lat']
        lon_base = coord_map[key_parroquia]['lon']
        nombres_disponibles = coord_map[key_parroquia]['nombre']
    elif key_canton in coord_canton_map:
        # Usar coordenadas del cantón con variación
        lat_base = coord_canton_map[key_canton]['lat']
        lon_base = coord_canton_map[key_canton]['lon']
        nombres_disponibles = []
    elif prov in coord_prov_map:
        # Usar coordenadas de la provincia con mayor variación
        lat_base = coord_prov_map[prov]['lat']
        lon_base = coord_prov_map[prov]['lon']
        nombres_disponibles = []
    else:
        # Valores por defecto (centro de Ecuador)
        lat_base = -1.8312
        lon_base = -78.1834
        nombres_disponibles = []
    
    # Agregar pequeña variación a las coordenadas (±0.01 grados = ~1 km)
    lat = lat_base + np.random.uniform(-0.01, 0.01)
    lon = lon_base + np.random.uniform(-0.01, 0.01)
    
    # Generar nombre sintético
    if nombres_disponibles and random.random() < 0.3:
        # 30% de probabilidad de reutilizar un nombre existente
        nombre = random.choice(nombres_disponibles)
    else:
        # Generar nombre nuevo
        prefijo = random.choice(prefijos)
        numero = random.randint(1, 999)
        nombre = f"{prefijo} {canton} {numero}"
    
    nombres_sinteticos.append(nombre)
    lats_sinteticas.append(lat)
    lons_sinteticas.append(lon)

sintetico['nombre'] = nombres_sinteticos
sintetico['lat'] = lats_sinteticas
sintetico['lon'] = lons_sinteticas

# ---------- Score sintético ----------
sintetico["score"] = sintetico[num_cols].mean(axis=1)

print(f"Datos sintéticos generados: {len(sintetico)} filas")


# =======================================================
# Verificar datos sintéticos
# =======================================================
print("\nVerificando datos sintéticos:")
print(f"   • Nombres únicos: {sintetico['nombre'].nunique()}")
print(f"   • Nombres vacíos: {sintetico['nombre'].isna().sum()}")
print(f"   • Coordenadas válidas: {(sintetico['lat'].notna() & sintetico['lon'].notna()).sum()}")
print(f"   • Rango lat: {sintetico['lat'].min():.2f} a {sintetico['lat'].max():.2f}")
print(f"   • Rango lon: {sintetico['lon'].min():.2f} a {sintetico['lon'].max():.2f}")
print(f"\n   Muestra de nombres generados:")
for i, nombre in enumerate(sintetico['nombre'].head(5), 1):
    print(f"   {i}. {nombre}")

# =======================================================
# Unir datos
# =======================================================
print(f"\n Uniendo datos originales y sintéticos...")

# Asegurarse de que ambos DataFrames tengan las mismas columnas
columnas_finales = num_cols + cat_cols + ['nombre', 'lat', 'lon', 'score']
df = df[columnas_finales]
sintetico = sintetico[columnas_finales]

df_final = pd.concat([df, sintetico], ignore_index=True)

print(f"Dataset final: {len(df_final)} filas")
print(f"   • Datos originales: {len(df)}")
print(f"   • Datos sintéticos: {len(sintetico)}")

# Verificar que no haya valores nulos en campos críticos
nulos_criticos = df_final[['nombre', 'lat', 'lon', 'provincia', 'canton']].isna().sum()
if nulos_criticos.sum() > 0:
    print(f"\nAdvertencia: Se encontraron valores nulos:")
    print(nulos_criticos[nulos_criticos > 0])
else:
    print(f" Sin valores nulos en campos críticos")

# =======================================================
# Guardar dataset combinado
# =======================================================
output_file = "datos_sintetico.csv"
df_final.to_csv(output_file, sep="|", index=False)
print(f"\nDataset combinado guardado en: {output_file}")

# Mostrar muestra del dataset final
print(f"\n Muestra del dataset final:")
print(df_final[['nombre', 'provincia', 'canton', 'lat', 'lon', 'score']].head(10))

# =======================================================
# Definir X e y para entrenamiento
# =======================================================
print(f"\n Preparando datos para entrenamiento...")

X = df_final[num_cols + cat_cols]
y = df_final[target]

# =======================================================
# Preprocesamiento
# =======================================================
preprocess = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_cols),
        ("cat", TargetEncoder(), cat_cols),
    ],
    remainder="drop"
)

# =======================================================
# Modelo XGBoost
# =======================================================
model = XGBRegressor(
    n_estimators=500,
    max_depth=9,
    learning_rate=0.045,
    subsample=0.9,
    colsample_bytree=0.85,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline([
    ("prep", preprocess),
    ("xgb", model)
])

# =======================================================
# Split y Entrenamiento
# =======================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nEntrenando modelo...")
print(f"   • Datos de entrenamiento: {len(X_train)}")
print(f"   • Datos de prueba: {len(X_test)}")

pipeline.fit(X_train, y_train)

# =======================================================
# Evaluación
# =======================================================
preds = pipeline.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, preds))
mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print("\n" + "="*60)
print("           RESULTADOS DEL MODELO XGBOOST")
print("="*60)
print(f"RMSE:      {rmse:.4f}")
print(f"MAE:       {mae:.4f}")
print(f"R2 Score:  {r2:.4f}")
print("="*60)

print("\nComparación Real vs Predicho (primeras 10 predicciones):")
comparison = pd.DataFrame({
    "Real": y_test.iloc[:10].values,
    "Predicho": preds[:10],
    "Error": np.abs(y_test.iloc[:10].values - preds[:10])
})
comparison.index = range(1, 11)
print(comparison.to_string())
