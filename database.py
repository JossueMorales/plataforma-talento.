import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import time

# Constante de conexión principal
LINK_ARCHIVO = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit"

# NOTA: Se eliminaron las variables estáticas PESTANA_PDI. Ahora se leen dinámicamente.

@st.cache_data(ttl=300, show_spinner=False)
def obtener_metadata(url_sheets=LINK_ARCHIVO):
    """Obtiene el timestamp para caché, estados de periodos y los nombres de las pestañas PDI activas."""
    try:
        secretos = st.secrets["connections"]["gsheets"]
        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        cliente = gspread.authorize(credenciales)
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheets)
        doc_id = match.group(1) if match else url_sheets
        archivo = cliente.open_by_key(doc_id)
        
        ws = archivo.worksheet("Metadata")
        
        val_a1 = ws.acell('A1').value # Timestamp de actualización
        val_c1 = ws.acell('C1').value # Estado Sucesión
        val_d1 = ws.acell('D1').value # Estado PDI
        val_e1 = ws.acell('E1').value # PDI Planeación (Ej. PDI 2027)
        val_f1 = ws.acell('F1').value # PDI Cierre (Ej. PDI 2026)
        
        estado_suc = str(val_c1).strip().upper() if val_c1 else "ABIERTO"
        estado_pdi = str(val_d1).strip().upper() if val_d1 else "ABIERTO"
        pdi_planeacion = str(val_e1).strip() if val_e1 else "PDI 2027"
        pdi_cierre = str(val_f1).strip() if val_f1 else "PDI 2026"
        
        return str(val_a1), estado_suc, estado_pdi, pdi_planeacion, pdi_cierre
    except Exception: 
        return str(int(time.time() // 600)), "ABIERTO", "ABIERTO", "PDI 2027", "PDI 2026"

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
