import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import time

# Constantes de conexión
LINK_ARCHIVO = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit"
PESTANA_PDI_ACTUAL = "PDI 2026"
PESTANA_PDI_ANTERIOR = "PDI 2025"

@st.cache_data(ttl=300, show_spinner=False)
def obtener_metadata(url_sheets=LINK_ARCHIVO):
    """Obtiene el timestamp para el caché y el estado de los periodos de sucesión y PDI."""
    try:
        secretos = st.secrets["connections"]["gsheets"]
        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        cliente = gspread.authorize(credenciales)
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheets)
        doc_id = match.group(1) if match else url_sheets
        archivo = cliente.open_by_key(doc_id)
        
        val_a1 = archivo.worksheet("Metadata").acell('A1').value
        val_c1 = archivo.worksheet("Metadata").acell('C1').value # Estado Sucesión
        val_d1 = archivo.worksheet("Metadata").acell('D1').value # Estado PDI
        
        estado_suc = str(val_c1).strip().upper() if val_c1 else "ABIERTO"
        estado_pdi = str(val_d1).strip().upper() if val_d1 else "ABIERTO"
        
        return str(val_a1), estado_suc, estado_pdi
    except Exception: 
        return str(int(time.time() // 600)), "ABIERTO", "ABIERTO"

@st.cache_data(show_spinner=False)
def cargar_datos_csv(nombre_pestana, _timestamp, url_sheets=LINK_ARCHIVO):
    """Carga los datos de una pestaña de Google Sheets a un DataFrame de Pandas."""
    try:
        secretos = st.secrets["connections"]["gsheets"]
        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        cliente = gspread.authorize(credenciales)
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheets)
        doc_id = match.group(1) if match else url_sheets
        archivo = cliente.open_by_key(doc_id)
        datos = archivo.worksheet(nombre_pestana).get_all_values()
        if datos:
            df = pd.DataFrame(datos[1:], columns=datos[0])
            df.columns = [str(col).strip() for col in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
