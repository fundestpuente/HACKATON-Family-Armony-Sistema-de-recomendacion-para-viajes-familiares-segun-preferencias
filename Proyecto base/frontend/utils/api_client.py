import requests
import streamlit as st
from typing import List, Dict, Optional
from utils.config import ENDPOINTS

class APIClient:
    """Cliente para interactuar con la API de Family Harmony"""
    
    @staticmethod
    def get_recommendations(family_data, top_k):
        payload = {
            "family": family_data,
            "top_k": top_k
        }

        response = requests.post(
            ENDPOINTS["recommend"],
            params={"top_k": top_k},
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(
                f"Error HTTP {response.status_code}: {response.text}"
            )

        return response.json()
    
    @staticmethod
    def check_api_health() -> bool:
        """
        Verifica si la API está disponible
        
        Returns:
            True si la API responde, False en caso contrario
        """
        try:
            # Intentar conectar al endpoint raíz o de salud
            response = requests.get(
                ENDPOINTS["recommend"].replace('/api/family/recommend_destinations', ''),
                timeout=3
            )
            return response.status_code == 200
        except:
            # Intentar directamente con el endpoint
            try:
                response = requests.head(
                    ENDPOINTS["recommend"],
                    timeout=3
                )
                return True
            except:
                return False


def format_family_data(members: List[Dict]) -> Dict:
    """
    Formatea los datos de la familia para enviar a la API
    Envía SOLO preferencias con rating > 0
    """
    formatted_members = []
    
    for member in members:
        flat_preferences = {}
        
        pref_mapping = {
            "iglesias": "Calif promedio iglesias",
            "resorts": "Calif promedio resorts",
            "playas": "Calif promedio playas",
            "parques": "Calif promedio parques",
            "teatros": "Calif promedio teatros",
            "museos": "Calif promedio museos",
            "centros_comerciales": "Calif promedio centros_comerciales",
            "zoologicos": "Calif promedio zoologicos",
            "restaurantes": "Calif promedio restaurantes",
            "bares_pubs": "Calif promedio bares_pubs",
            "servicios_locales": "Calif promedio servicios_locales",
            "pizzerias_hamburgueserias": "Calif promedio pizzerias_hamburgueserias",
            "hoteles_alojamientos": "Calif promedio hoteles_alojamientos",
            "juguerias": "Calif promedio juguerias",
            "galerias_arte": "Calif promedio galerias_arte",
            "discotecas": "Calif promedio discotecas",
            "piscinas": "Calif promedio piscinas",
            "gimnasios": "Calif promedio gimnasios",
            "panaderias": "Calif promedio panaderias",
            "belleza_spas": "Calif promedio belleza_spas",
            "cafeterias": "Calif promedio cafeterias",
            "miradores": "Calif promedio miradores",
            "monumentos": "Calif promedio monumentos",
            "jardines": "Calif promedio jardines"
        }
        
        # Solo agregar preferencias con rating > 0
        for category, items in member.get('preferencias', {}).items():
            for item, rating in items.items():
                if item in pref_mapping and rating > 0:
                    col_name = pref_mapping[item]
                    flat_preferences[col_name] = float(rating)
        
        formatted_member = {
            "nombre": member['nombre'],
            "rol": member['rol'],
            "preferencias": flat_preferences
        }
        
        formatted_members.append(formatted_member)
    
    return {"miembros": formatted_members}