import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import re

# Importamos las dependencias de interfaz y limpieza que ya tienes
from config_ui import (
    OPCIONES_PYVIS, SCRIPT_ANILLOS, INYECCION_HTML_JS,
    clean_text, clean_id, obtener_color_9box, acortar_nombre, 
    acortar_puesto, get_readiness_val, get_dispersion_offset
)

def buscar_columna(columnas, palabra_clave, numero=None):
    """Busca dinámicamente el nombre de una columna con regex."""
    palabra_limpia = re.sub(r'[^a-z0-9]', '', str(palabra_clave).lower())
    for col in columnas:
        col_limpia = re.sub(r'[^a-z0-9]', '', str(col).lower())
        if palabra_limpia in col_limpia:
            if numero is None or str(numero) in col_limpia:
                return col
    return None

# ==========================================
# MOTOR PRINCIPAL (GRAFO CON CACHÉ Y LAZY LOADING)
# ==========================================
# Nota: Streamlit maneja el caché en el archivo principal, por lo que 
# aquí solo definimos la lógica pura. El decorador @st.cache_data 
# lo mantendremos en una función envoltorio en app_web.py o lo pasaremos directamente.

def generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_jerarquia, f_box, f_edr, f_puesto, f_riesgos, renderizar_mapa, usuario_activo_id):
    G = nx.MultiDiGraph()
    G_jerarquia = nx.DiGraph() 
    jefes_dict = {}
    empleados_validos = set()
    info_nodos = {}
    
    # ... [CORTA Y PEGA AQUÍ TODO EL CONTENIDO INTERNO DE TU FUNCIÓN ORIGINAL generar_mapa_html] ...
    # (Desde: nombres_dict = {...} hasta el final del return html, pd.DataFrame(alertas_tabla), kpis)
    
    return html, pd.DataFrame(alertas_tabla), kpis
