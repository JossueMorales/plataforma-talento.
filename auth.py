import streamlit as st
import hashlib
from database import cargar_datos_csv, obtener_metadata, LINK_ARCHIVO

PASSWORD_POR_DEFECTO = "Ayvi2026"

def hash_password(password):
    """Encripta la contraseña usando SHA-256."""
    return hashlib.sha256(str(password).encode('utf-8')).hexdigest()

def login():
    """Maneja la interfaz y validación de inicio de sesión."""
    if "usuario_logueado" not in st.session_state: 
        st.session_state["usuario_logueado"] = False
        
    if not st.session_state["usuario_logueado"]:
        usuarios_autorizados = {
            "admin": {"nombre": "Administrador Global", "password": hash_password("admin"), "direccion": "TODAS", "lider": "TODOS"}
        }
        
        current_timestamp, estado_sucesion, estado_pdi = obtener_metadata()
        st.session_state["estado_sucesion"] = estado_sucesion
        st.session_state["estado_pdi"] = estado_pdi
        
        df_usuarios = cargar_datos_csv("Usuarios", current_timestamp)
        
        if not df_usuarios.empty:
            for _, row in df_usuarios.iterrows():
                u = str(row.get("Usuario", "")).strip()
                if u:
                    usuarios_autorizados[u] = {
                        "nombre": str(row.get("Nombre", "")).strip(),
                        "password": str(row.get("Password", "")).strip(),
                        "direccion": str(row.get("Direccion", "")).strip(),
                        "lider": str(row.get("Lider Restringido", "TODOS")).strip()
                    }
        
        st.markdown("<h1 style='text-align: center; color: #1976d2;'>🔐 Portal de Talento Ayvi</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.write("")
            usuario = st.text_input("Usuario (Número de Nómina)")
            password = st.text_input("Contraseña", type="password")
            if st.button("Iniciar Sesión", use_container_width=True):
                if usuario in usuarios_autorizados:
                    db_pass = usuarios_autorizados[usuario]["password"]
                    if db_pass == hash_password(password) or db_pass == password:
                        st.session_state["usuario_logueado"] = True
                        st.session_state["nombre_usuario"] = usuarios_autorizados[usuario]["nombre"]
                        st.session_state["id_usuario"] = usuario
                        st.session_state["direccion_permitida"] = usuarios_autorizados[usuario]["direccion"]
                        st.session_state["lider_permitido"] = usuarios_autorizados[usuario].get("lider", "TODOS")
                        st.session_state["password_actual"] = password 
                        
                        if st.session_state["lider_permitido"] == "": st.session_state["lider_permitido"] = "TODOS"
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                else: 
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True
