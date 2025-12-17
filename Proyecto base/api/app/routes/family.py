from fastapi import APIRouter, HTTPException
from ..schemas import FamilyBase
from ..core.model_manager import ModelManager
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from typing import Optional, List

# Cargar variables de entorno desde .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path)

# Rutas a los archivos de datos (definidas en .env)
DATA_PATH = os.getenv("DATA_PATH")
NEW_DATA_PATH = os.getenv("NEW_DATA_PATH")

router = APIRouter()

# Inicializar y entrenar el modelo al arrancar la app
model_manager = ModelManager(DATA_PATH, NEW_DATA_PATH)
model_manager.train_model() # Entrenar con los datos historicos

# Utilidades
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def normalizar_texto(texto: str) -> str:
    return texto.lower().strip().replace("_", " ").replace("-", " ")


def buscar_columnas_por_tipo(df: pd.DataFrame, tipo: str) -> List[str]:
    tipo_norm = normalizar_texto(tipo)
    return [
        col for col in df.columns
        if tipo_norm in normalizar_texto(col)
    ]


def limpiar_coordenadas(df: pd.DataFrame) -> pd.DataFrame:
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.dropna(subset=["lat", "lon"]).copy()


def calcular_distancias_seguras(df, lat, lon):
    def safe(row):
        try:
            return calcular_distancia(lat, lon, row["lat"], row["lon"])
        except:
            return np.nan

    df["distancia_km"] = df.apply(safe, axis=1)
    return df.dropna(subset=["distancia_km"])

# Endpoints a exponer

@router.post("/recommend_destinations")
def recommend_destinations(
        family: FamilyBase,
        top_k: int = 10,
        ubicacion_actual_lat: Optional[float] = None,
        ubicacion_actual_lon: Optional[float] = None,
        max_distancia_km: Optional[float] = None,
        provincia_preferida: Optional[str] = None,
        tipos_interes: Optional[List[str]] = None
    ):
    miembros = family.miembros
    if not miembros:
        raise HTTPException(status_code=400, detail="No se proporcionaron miembros de la familia.")

    aggregated_preferences, counts = {}, {}

    # Agregar preferencias de cada miembro
    for member in miembros:
        for key, value in member.preferencias.items():
            key_norm = normalizar_texto(key)
            for col in model_manager.feature_columns:
                if key_norm in normalizar_texto(col):
                    aggregated_preferences[col] = aggregated_preferences.get(col, 0.0) + value
                    counts[col] = counts.get(col, 0) + 1

    # Promediar
    for col in aggregated_preferences:
        aggregated_preferences[col] /= counts[col]

    # Cargar destinos históricos
    df = pd.read_csv(DATA_PATH, sep="|")
    df.columns = df.columns.str.strip()
    df = limpiar_coordenadas(df)

    if provincia_preferida:
        df = df[df["provincia"].str.upper() == provincia_preferida.upper()]

    if tipos_interes:
        mask = pd.Series(False, index=df.index)
        for tipo in tipos_interes:
            for col in buscar_columnas_por_tipo(df, tipo):
                if pd.api.types.is_numeric_dtype(df[col]):
                    mask |= df[col] > 2
        df = df[mask]

    if df.empty:
        raise HTTPException(404, "No hay destinos tras aplicar filtros")

    if ubicacion_actual_lat is not None and ubicacion_actual_lon is not None:
        df = calcular_distancias_seguras(df, ubicacion_actual_lat, ubicacion_actual_lon)
        if max_distancia_km:
            df = df[df["distancia_km"] <= max_distancia_km]

    # Repetir agregadas para todos los destinos
    X = df[model_manager.feature_columns].copy()
    for col, val in aggregated_preferences.items():
        X[col] = val

    df["predicted_score"] = model_manager.model.predict(X)

    top = df.sort_values("predicted_score", ascending=False).head(top_k)
    # recommendations = top_destinos[["nombre", "provincia", "canton", "predicted_score"]].to_dict(orient="records")

    return {
        "recommendations": [
            {
                "nombre": r["nombre"],
                "provincia": r["provincia"],
                "canton": r["canton"],
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "predicted_score": round(float(r["predicted_score"]), 3),
                "distancia_km": round(float(r["distancia_km"]), 2) if "distancia_km" in r else None
            }
            for _, r in top.iterrows()
        ]
    }

@router.post("/save_family_record")
def save_family_record(record: dict):
    """
    Guarda un nuevo registro en CSV para futuros reentrenamientos.
    Se espera que el record contenga todas las columnas necesarias.
    """
    if not record:
        raise HTTPException(status_code=400, detail="No se proporcionó información del registro")
    
    model_manager.save_new_record(record)
    return {"status": "ok", "message": "Registro guardado"}

# Nuevos endpoints para manejar mapa interactivo

@router.get("/destino_mas_cercano")
def obtener_destino_mas_cercano(
    lat: float,
    lon: float,
    tipo: Optional[str] = None,
    min_score: float = 0.0
):
    df = pd.read_csv(DATA_PATH, sep="|")
    df.columns = df.columns.str.strip()
    df = limpiar_coordenadas(df)

    if "score" in df.columns:
        df = df[df["score"] >= min_score]

    if tipo:
        cols = buscar_columnas_por_tipo(df, tipo)
        if cols:
            mask = pd.Series(False, index=df.index)
            for col in cols:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mask |= df[col] > 0
            df = df[mask]

    if df.empty:
        raise HTTPException(404, "No hay destinos válidos")

    df = calcular_distancias_seguras(df, lat, lon)

    if df.empty:
        raise HTTPException(404, "No se pudo calcular distancia")

    d = df.sort_values("distancia_km").iloc[0]

    return {
        "nombre": d["nombre"],
        "provincia": d["provincia"],
        "canton": d["canton"],
        "lat": float(d["lat"]),
        "lon": float(d["lon"]),
        "score": float(d.get("score", 0)),
        "distancia_km": round(float(d["distancia_km"]), 2)
    }

@router.get("/destinos_por_tipo")
def destinos_por_tipo(
    tipo: str,
    top_k: int = 10,
    provincia: Optional[str] = None
):
    df = pd.read_csv(DATA_PATH, sep="|")
    df.columns = df.columns.str.strip()
    df = limpiar_coordenadas(df)

    # ---- Filtrar por provincia ----
    if provincia:
        df = df[df["provincia"].str.upper() == provincia.upper()]

    # ---- Buscar columnas del tipo ----
    cols = buscar_columnas_por_tipo(df, tipo)

    if not cols:
        raise HTTPException(404, f"No hay columnas para el tipo: {tipo}")

    # ---- Score promedio del tipo ----
    df["score_tipo"] = df[cols].mean(axis=1)

    # ---- Filtrar destinos válidos ----
    df = df[df["score_tipo"] > 0]

    if df.empty:
        raise HTTPException(404, "No hay destinos válidos")

    # ---- Top K ----
    top = df.sort_values("score_tipo", ascending=False).head(top_k)

    return {
        "resultados": [
            {
                "nombre": r["nombre"],
                "provincia": r["provincia"],
                "canton": r["canton"],
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "score_general": round(float(r["score_tipo"]), 3)
            }
            for _, r in top.iterrows()
        ]
    }
