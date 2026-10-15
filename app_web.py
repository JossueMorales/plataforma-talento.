import streamlit as st
import gspread.utils

# CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Portal de Talento Ayvi", layout="wide")

import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components
import re
import gspread
import unicodedata
from google.oauth2.service_account import Credentials
import time

# --- IMPORTACIONES DE NUESTROS NUEVOS MÓDULOS ---
from config_ui import (
    OPCIONES_PYVIS, SCRIPT_ANILLOS, INYECCION_HTML_JS,
    crear_tarjeta_kpi, extraer_contexto, clean_text, clean_id,
    obtener_color_9box, acortar_nombre, acortar_puesto,
    get_readiness_val, get_dispersion_offset
)

from database import LINK_ARCHIVO, obtener_metadata, cargar_datos_csv
from auth import login, hash_password, PASSWORD_POR_DEFECTO

from modulos.mapa_org import generar_mapa_html, buscar_columna
from modulos.sucesion import renderizar_tab_sucesiones
from modulos.pdi import renderizar_mi_pdi, COLUMNAS_PDI
from modulos.reportes import renderizar_reportes

# ==========================================
# FUNCIONES DE UTILIDAD Y CACHÉ
# ==========================================
@st.cache_data(show_spinner=False)
def generar_mapa_html_cacheado(*args, **kwargs):
    return generar_mapa_html(*args, **kwargs)

def ordenar_jerarquia_talento(df, col_puesto='Nombre de la Posición', col_nombre='Nombre'):
    if col_puesto not in df.columns: return df
    def asignar_peso(puesto):
        p = str(puesto).lower()
        if 'gerente' in p or 'director' in p: return 1
        if 'jefe' in p: return 2
        return 3
    df['_peso_jerarquia'] = df[col_puesto].apply(asignar_peso)
    cols_sort = ['_peso_jerarquia', col_puesto]
    if col_nombre in df.columns: cols_sort.append(col_nombre)
    df = df.sort_values(by=cols_sort)
    return df.drop(columns=['_peso_jerarquia'])

def clean_and_split(s):
    s = str(s)
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    words = set(s.lower().split())
    return {w for w in words if w not in ['de', 'la', 'el', 'los', 'las', 'y', 'en', 'para']}

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login(): st.stop()
    
    if st.session_state.get("password_actual") == PASSWORD_POR_DEFECTO:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_espacio1, col_centro, col_espacio3 = st.columns([1, 2, 1])
        with col_centro:
            st.markdown("<h2 style='text-align:center; color:#1e3a8a;'>🔒 Actualización de Seguridad Requerida</h2>", unsafe_allow_html=True)
            st.info("¡Bienvenido(a) a tu Portal de Talento! Al ser tu primer ingreso, por políticas corporativas debes cambiar tu contraseña temporal antes de continuar.")
            
            with st.form("cambio_pass_form"):
                n_pass1 = st.text_input("Ingresa tu nueva contraseña", type="password")
                n_pass2 = st.text_input("Confirma tu nueva contraseña", type="password")
                
                if st.form_submit_button("💾 Guardar Contraseña y Entrar", use_container_width=True):
                    if n_pass1 != n_pass2:
                        st.error("❌ Las contraseñas no coinciden. Inténtalo de nuevo.")
                    elif len(n_pass1) < 5:
                        st.error("❌ La contraseña debe tener al menos 5 caracteres.")
                    elif n_pass1 == PASSWORD_POR_DEFECTO:
                        st.error("❌ Debes elegir una contraseña diferente a la temporal.")
                    else:
                        with st.spinner("Actualizando seguridad en la base de datos..."):
                            try:
                                secretos = st.secrets["connections"]["gsheets"]
                                credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                cliente = gspread.authorize(credenciales)
                                match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                doc_id = match.group(1) if match else LINK_ARCHIVO
                                archivo = cliente.open_by_key(doc_id)
                                pestana_users = archivo.worksheet("Usuarios")
                                
                                usuarios_col = pestana_users.col_values(1)
                                try:
                                    fila_usuario = usuarios_col.index(st.session_state["id_usuario"]) + 1 
                                    pestana_users.update_cell(fila_usuario, 3, hash_password(n_pass1))
                                    archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                    
                                    st.session_state["password_actual"] = n_pass1
                                    st.cache_data.clear()
                                    st.success("✅ ¡Contraseña actualizada exitosamente! Entrando al portal...")
                                    time.sleep(1.5)
                                    st.rerun()
                                except ValueError:
                                    st.error("❌ Ocurrió un error. Tu usuario no se encontró en la matriz de la base de datos.")
                            except Exception as e:
                                st.error(f"❌ Error técnico de conexión: {e}")
        st.stop()

    if "vista_kpi" not in st.session_state: st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        [data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
        div[data-testid="stButton"] > button { padding: 2px 10px; font-size: 12px; height: auto; min-height: 28px; }
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            padding-bottom: 10px !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 320px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    with c1: st.subheader(f"Bienvenido(a), {st.session_state['nombre_usuario']}")
    with c2:
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state["usuario_logueado"] = False; st.rerun()
            
    st.divider()
    with st.spinner("Cargando base de datos y validando seguridad dinámica..."):
        current_timestamp, estado_sucesion, estado_pdi, pdi_planeacion, pdi_cierre = obtener_metadata()
        
        def intentar_cargar_pestana(opciones_nombres, timestamp):
            for nombre in opciones_nombres:
                df = cargar_datos_csv(nombre, timestamp)
                if not df.empty:
                    return df
            return pd.DataFrame()

        df_completo_raw = cargar_datos_csv("Base de datos", current_timestamp)
        df_pdi = cargar_datos_csv(pdi_planeacion, current_timestamp)
        df_pdi_anterior = cargar_datos_csv(pdi_cierre, current_timestamp)
        df_mla = cargar_datos_csv("Resultados MLA", current_timestamp)
        
        df_matriz_competencias = intentar_cargar_pestana(["Matriz de Competencias", "Matriz de competencias"], current_timestamp)
        df_evaluaciones = intentar_cargar_pestana(["Evaluaciones Tecnicas", "Evaluaciones tecnicas", "Evaluaciones Competencias"], current_timestamp)
        
        df_usuarios_permisos = cargar_datos_csv("Usuarios", current_timestamp)
        
        if df_completo_raw.empty:
            st.error("Error al conectar con la base de datos principal.")
            st.stop()
            
        col_estatus = next((c for c in df_completo_raw.columns if 'estatus' in str(c).lower()), None)
        
        if col_estatus:
            estatus_global = {clean_id(r.get('id Empleado')): clean_text(r.get(col_estatus, 'Activo')).lower() for r in df_completo_raw.to_dict('records')}
        else:
            estatus_global = {clean_id(r.get('id Empleado')): 'activo' for r in df_completo_raw.to_dict('records')}
            
        jefe_orig_global = {clean_id(r.get('id Empleado')): clean_id(r.get('ID Del Jefe')) for r in df_completo_raw.to_dict('records')}
        
        def get_active_boss_global(emp):
            j = jefe_orig_global.get(emp)
            vis = set()
            while j and j in estatus_global:
                if j in vis: break
                vis.add(j)
                if estatus_global[j] not in ['baja', 'vacante']: 
                    return j
                j = jefe_orig_global.get(j)
            return j

        df_completo = df_completo_raw.copy()
        df_completo['ID Del Jefe'] = df_completo['id Empleado'].apply(lambda x: get_active_boss_global(clean_id(x)))
        
        if col_estatus:
            df_completo = df_completo[~df_completo[col_estatus].astype(str).str.strip().str.lower().isin(['baja'])]
        
        match_nomina = pd.DataFrame() 
        if st.session_state["id_usuario"] != "admin":
            match_nomina = df_completo[df_completo['id Empleado'].apply(clean_id) == clean_id(st.session_state["id_usuario"])]
            
        if not match_nomina.empty:
            st.session_state["nombre_usuario"] = clean_text(match_nomina.iloc[0]['Nombre'])
                
        df_completo['Nombre'] = df_completo['Nombre'].astype(str).str.strip()
        df_completo['Nombre_Cruce'] = df_completo['Nombre'].str.lower()
        if not df_pdi.empty and 'Nombre' in df_pdi.columns:
            df_pdi['Nombre'] = df_pdi['Nombre'].astype(str).str.strip()
            df_pdi['Nombre_Cruce'] = df_pdi['Nombre'].str.lower()

        df_completo = ordenar_jerarquia_talento(df_completo, 'Nombre de la Posición', 'Nombre')
            
        direccion_permitida = str(st.session_state.get("direccion_permitida", "TODAS")).strip().upper()
        es_colaborador = ("COLABORADOR" in direccion_permitida)
        lider_permitido_str = str(st.session_state.get("lider_permitido", "TODOS")).strip()
        col_jer = next((c for c in df_completo.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')
        
        modulos_permitidos_usuario = ["TODOS"]
        if not df_usuarios_permisos.empty and "Modulos" in df_usuarios_permisos.columns:
            match_u = df_usuarios_permisos[df_usuarios_permisos['Usuario'].astype(str).str.strip() == str(st.session_state["id_usuario"])]
            if not match_u.empty:
                mods_str = str(match_u.iloc[0].get("Modulos", "TODOS")).strip().upper()
                if mods_str and mods_str != "NAN":
                    modulos_permitidos_usuario = [m.strip() for m in mods_str.split(",")]

        dict_nom_global = {clean_id(r.get('id Empleado')): clean_text(r.get('Nombre')) for r in df_completo.to_dict('records')}
        jerarquia_global = {}
        for j, e in zip(df_completo['ID Del Jefe'].astype(str).str.strip(), df_completo['id Empleado'].astype(str).str.strip()):
            j = clean_id(j)
            e = clean_id(e)
            if j not in jerarquia_global: jerarquia_global[j] = []
            jerarquia_global[j].append(e)

        tiene_equipo = False
        mi_nomina = clean_id(st.session_state["id_usuario"])
        mis_subordinados_directos = jerarquia_global.get(mi_nomina, [])
        if len(mis_subordinados_directos) > 0 and st.session_state["id_usuario"] != "admin":
            tiene_equipo = True

        if es_colaborador and not tiene_equipo:
            renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior, df_mla, df_matriz_competencias, df_evaluaciones, es_lider_evaluando=False)
        else:
            if "TODAS" not in direccion_permitida:
                lista_dirs = [d.strip() for d in direccion_permitida.split(",")]
                mask_dir = df_completo['Dirección'].astype(str).str.upper().apply(lambda d_val: any(d in d_val for d in lista_dirs))
                df_seguro = df_completo[mask_dir | (df_completo[col_jer].astype(str).str.strip() == '5')]
            else:
                df_seguro = df_completo.copy()

            if lider_permitido_str.upper() != "TODOS" and lider_permitido_str != "":
                lista_lideres_perm = [l.strip().lower() for l in lider_permitido_str.split(",")]
                lideres_ids_global = []
                for idx, nom in dict_nom_global.items():
                    if str(nom).strip().lower() in lista_lideres_perm: lideres_ids_global.append(idx)
                
                if not lideres_ids_global and lider_permitido_str.lower() == st.session_state["nombre_usuario"].strip().lower():
                    lideres_ids_global.append(mi_nomina)
                
                subs_globales = set()
                for l_id in lideres_ids_global:
                    cola = [l_id]
                    while cola:
                        actual = cola.pop(0)
                        directos = jerarquia_global.get(actual, [])
                        for d in directos:
                            if d and d not in subs_globales:
                                subs_globales.add(d)
                                cola.append(d)
                    subs_globales.add(l_id)
                
                df_seguro['id_clean'] = df_seguro['id Empleado'].apply(clean_id)
                df_seguro = df_seguro[df_seguro['id_clean'].isin(subs_globales)]
                nombres_permitidos_limpios = [str(dict_nom_global.get(s)).strip().lower() for s in subs_globales if s in dict_nom_global and str(dict_nom_global.get(s)).strip() != '']
                st.session_state['nombres_permitidos_limpios'] = nombres_permitidos_limpios
            elif es_colaborador and tiene_equipo:
                subs_globales = set()
                cola = [mi_nomina]
                while cola:
                    actual = cola.pop(0)
                    directos = jerarquia_global.get(actual, [])
                    for d in directos:
                        if d and d not in subs_globales:
                            subs_globales.add(d)
                            cola.append(d)
                subs_globales.add(mi_nomina)
                df_seguro['id_clean'] = df_seguro['id Empleado'].apply(clean_id)
                df_seguro = df_seguro[df_seguro['id_clean'].isin(subs_globales)]
                nombres_permitidos_limpios = [str(dict_nom_global.get(s)).strip().lower() for s in subs_globales if s in dict_nom_global and str(dict_nom_global.get(s)).strip() != '']
                st.session_state['nombres_permitidos_limpios'] = nombres_permitidos_limpios
            else:
                st.session_state['nombres_permitidos_limpios'] = []

            df_filtros = df_seguro
            if st.session_state["id_usuario"] != "admin":
                df_filtros = df_seguro[~df_seguro[col_jer].astype(str).str.strip().isin(['5'])]

            col_head1, col_head2 = st.columns([2, 1])
            with col_head1:
                st.markdown("### 🎛️ Filtros Globales")
                if st.button("🔄 Forzar Sincronización con Excel"):
                    st.cache_data.clear(); st.rerun()
                
            with col_head2:
                nombres_s = df_filtros['Nombre'].dropna()
                lista_nombres_buscador = nombres_s[nombres_s != ''].drop_duplicates().tolist()
                colab_buscado = st.selectbox("🔍 Búsqueda rápida de colaborador:", [""] + lista_nombres_buscador)
                
            if colab_buscado:
                datos_c = df_seguro[df_seguro['Nombre'] == colab_buscado].iloc[0]
                jer_key_c = next((k for k in datos_c.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
                st.success(f"👤 **{colab_buscado}** | 🏢 **Puesto:** {clean_text(datos_c.get('Nombre de la Posición', 'N/A'))} | 📍 **Dirección:** {clean_text(datos_c.get('Dirección', datos_c.get('Direccion', 'N/A')))} | 📊 **9-Box:** {clean_text(datos_c.get('Resultado 9 box', 'N/A'))} | 📈 **EDR:** {clean_text(datos_c.get('EDR', datos_c.get('EDR ', 'N/A')))} | 🥇 **Nivel Jerárquico:** {clean_text(datos_c.get(jer_key_c, 'N/A'))}")
            
            dirs = sorted(df_filtros['Dirección'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            jerarquias = sorted(df_filtros[col_jer].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            boxes = sorted(df_filtros['Resultado 9 box'].dropna().astype(str).str.strip().str.upper()[lambda x: x != ''].unique().tolist())
            criticas = sorted(df_filtros['Posición Crítica'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            edrs_col = 'EDR' if 'EDR' in df_filtros.columns else ('EDR ' if 'EDR ' in df_filtros.columns else None)
            edrs = sorted(df_filtros[edrs_col].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist()) if edrs_col else []
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            f_dir = col_f1.multiselect("Dirección", options=dirs, placeholder="Todas")
            if f_dir: lideres_ids = df_filtros[df_filtros['Dirección'].astype(str).str.strip().isin(f_dir)]['ID Del Jefe'].dropna().unique()
            else: lideres_ids = df_filtros['ID Del Jefe'].dropna().unique()
                
            lideres = sorted(list(set([dict_nom_global.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
            f_lid = col_f2.multiselect("Líder", options=lideres, placeholder="Todos")
            f_crit = col_f3.multiselect("Pos. Crítica", options=criticas, placeholder="Todas")
            f_jerarquia = col_f4.multiselect("Nivel Jerárquico", options=jerarquias, placeholder="Todos")
            
            df_temp_puestos = df_filtros.copy()
            if f_dir: df_temp_puestos = df_temp_puestos[df_temp_puestos['Dirección'].astype(str).str.strip().isin(f_dir)]
            if f_lid: 
                lideres_ids_filt = [k for k, v in dict_nom_global.items() if v in f_lid]
                df_temp_puestos = df_temp_puestos[df_temp_puestos['ID Del Jefe'].isin(lideres_ids_filt)]
            if f_crit: df_temp_puestos = df_temp_puestos[df_temp_puestos['Posición Crítica'].astype(str).str.strip().isin(f_crit)]
            if f_jerarquia: df_temp_puestos = df_temp_puestos[df_temp_puestos[col_jer].astype(str).str.strip().isin(f_jerarquia)]
            
            col_f5, col_f6, col_f7, col_f8 = st.columns(4)
            f_box = col_f5.multiselect("9-Box", options=boxes, placeholder="Todos")
            f_edr = col_f6.multiselect("EDR (Resultados)", options=edrs, placeholder="Todos")
                
            if f_box: df_temp_puestos = df_temp_puestos[df_temp_puestos['Resultado 9 box'].astype(str).str.strip().str.upper().isin(f_box)]
            if f_edr: df_temp_puestos = df_temp_puestos[df_temp_puestos[edrs_col].astype(str).str.strip().isin(f_edr)]
            
            puestos_opciones = sorted(df_temp_puestos['Nombre de la Posición'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            
            with col_f8:
                st.markdown("<div style='margin-top: 33px;'></div>", unsafe_allow_html=True)
                auto_puestos = st.checkbox("☑️ Auto-seleccionar lista", value=False)
                
            with col_f7:
                f_puesto = st.multiselect("Posición / Puesto", options=puestos_opciones, default=puestos_opciones if auto_puestos else None, placeholder="Todos")
            
            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                f_riesgos = st.checkbox("🚨 Mostrar Solo Colaboradores con Riesgos Detectados")
                
            renderizar_mapa = True
            if not f_dir and not f_lid: renderizar_mapa = False
                
            with col_chk2:
                if not renderizar_mapa:
                    forzar_mapa = st.checkbox("⚠️ Dibujar el mapa visual de todos modos (Puede ser lento)", value=False)
                    if forzar_mapa: renderizar_mapa = True
            st.write("") 
            
            html_mapa, df_alertas, kpis = generar_mapa_html_cacheado(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_jerarquia, f_box, f_edr, f_puesto, f_riesgos, renderizar_mapa, st.session_state["id_usuario"])
            
            if kpis is not None:
                tabs_a_mostrar = []
                nombres_tabs = []
                
                if st.session_state["id_usuario"] == "admin" or ("TODOS" in modulos_permitidos_usuario) or ("MAPA" in modulos_permitidos_usuario):
                    if not es_colaborador: 
                        nombres_tabs.append("🗺️ Mapa Organizacional")
                        
                if st.session_state["id_usuario"] == "admin" or ("TODOS" in modulos_permitidos_usuario) or ("SUCESIÓN" in modulos_permitidos_usuario) or ("SUCESION" in modulos_permitidos_usuario):
                    if not es_colaborador: 
                        nombres_tabs.append("🔀 Sucesión")
                        
                if st.session_state["id_usuario"] == "admin" or ("TODOS" in modulos_permitidos_usuario) or ("PDI EQUIPO" in modulos_permitidos_usuario) or tiene_equipo:
                    nombres_tabs.append("📈 Seguimiento de PDI (Mi Equipo)")
                    
                nombres_tabs.append("📝 Mi PDI")
                
                if st.session_state["id_usuario"] == "admin" or ("TODOS" in modulos_permitidos_usuario) or ("REPORTES" in modulos_permitidos_usuario):
                    nombres_tabs.append("📊 Reportes e IA")
                    
                if st.session_state["id_usuario"] == "admin":
                    nombres_tabs.append("⚙️ Panel de Administración")
                    
                tabs_creados = st.tabs(nombres_tabs)
                
                for i, nombre_tab in enumerate(nombres_tabs):
                    
                    if nombre_tab == "🗺️ Mapa Organizacional":
                        with tabs_creados[i]:
                            st.markdown("### 📊 KPIs de Talento")
                            k1, k2, k3, k4, k5, k6 = st.columns(6)
                            
                            with k1:
                                if st.button(f"👥 Total Colab.\n\n{kpis['total']}", key="b_tot", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "total"; st.rerun()
                            with k2:
                                if st.button(f"🔀 Sucesión (Críticas)\n\n{kpis['sucesores']}", key="b_suc", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "sucesores"; st.rerun()
                            with k3:
                                if st.button(f"📈 Desempeño (EDR)\n\n{kpis['edr_count']}", key="b_edr", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "edr"; st.rerun()
                            with k4:
                                if st.button(f"📊 Resultados (9-Box)\n\n{kpis['nueve_box_count']}", key="b_9box", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "nueve_box"; st.rerun()
                            with k5:
                                if st.button(f"🚨 Alertas Detect.\n\n{kpis['alertas']}", key="b_ale", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "alertas"; st.rerun()
                            with k6:
                                if st.button(f"🔥 Prom. Enganche\n\n{kpis['enganche_promedio']}", key="b_eng", use_container_width=True): 
                                    st.session_state["vista_kpi"] = "enganche"; st.rerun()
                            
                            st.write("---")
                            
                            col_mapa, col_datos = st.columns([5, 5])
                            with col_mapa: 
                                components.html(html_mapa, height=550, scrolling=False)
                            with col_datos:
                                if st.session_state.get("vista_kpi"):
                                    vista = st.session_state["vista_kpi"]
                                    titulos_kpi = {"total": "Total de Colaboradores (Excl. Vacantes)", "sucesores": "Sucesión de Posiciones Críticas", "edr": "Evaluación de Desempeño y Resultados (EDR)", "nueve_box": "Evaluaciones 9-Box", "alertas": "Colaboradores con Riesgos / Alertas", "enganche": "Nivel de Enganche de Líderes"}
                                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                                    if not df_lista.empty:
                                        if vista == "alertas": df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                                        if f_dir and "Dirección" in df_lista.columns: df_lista = df_lista.drop(columns=["Dirección"])
                                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                                    else: st.info("No hay registros en esta categoría.")
                                    if st.button("❌ Cerrar Lista", use_container_width=True): st.session_state["vista_kpi"] = None; st.rerun()
                                else:
                                    st.info("👆 Selecciona cualquier KPI superior para desplegar la información a detalle en esta área.")
                                    
                    elif nombre_tab == "🔀 Sucesión":
                        with tabs_creados[i]:
                            f_lid_plan, subordinados_nombres_limpios = renderizar_tab_sucesiones(
                                df_seguro, df_completo, df_pdi, dict_nom_global, jerarquia_global, 
                                kpis, f_jerarquia, f_puesto, direccion_permitida, match_nomina
                            )

                    elif nombre_tab == "📈 Seguimiento de PDI (Mi Equipo)":
                        with tabs_creados[i]:
                            st.markdown("### 📈 Seguimiento de PDI de mi Equipo")
                            st.info("Gracias a la nueva arquitectura multifila, ahora puedes ver el estatus granular de cada acción del plan 70-20-10 de tus colaboradores.")
                            
                            si_es_admin = st.session_state["id_usuario"] == "admin"
                            equipo_permitido = [str(n).strip().lower() for n in st.session_state.get('nombres_permitidos_limpios', [])]
                            
                            if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                                df_pdi_filtrado = df_pdi.copy()
                                df_pdi_filtrado['Nombre_Limpio'] = df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower()
                                
                                if not si_es_admin:
                                    df_pdi_filtrado = df_pdi_filtrado[df_pdi_filtrado['Nombre_Limpio'].isin(equipo_permitido)]
                                
                                columnas_busqueda = [
                                    ("nómina", "Nómina"), ("nombre", "Colaborador"), ("roles", "Roles / Áreas de Interés"),
                                    ("objetivo", "Objetivo PDI"), ("pdi", "PDI (70/20/10)"), ("clasificacion", "Clasificación de Competencia"),
                                    ("qué", "Qué? / Acciones"), ("para qué", "¿Para qué? / Competencia"), ("quién", "¿Quién? / Recursos"),
                                    ("cuándo", "¿Cuándo? / Fechas"), ("cómo", "Métricas"), ("avance", "% de Avance"), ("estatus", "Estatus")
                                ]
                                cols_reales = []; nombres_finales = []
                                for clave, nombre_nuevo in columnas_busqueda:
                                    col_match = None
                                    if clave == "pdi":
                                        col_match = next((c for c in df_pdi_filtrado.columns if clean_text(str(c)).lower() == "pdi"), None)
                                        if not col_match: col_match = next((c for c in df_pdi_filtrado.columns if 'pdi' in clean_text(str(c)).lower() and 'objetivo' not in clean_text(str(c)).lower()), None)
                                    else:
                                        col_match = next((c for c in df_pdi_filtrado.columns if clean_text(clave).lower() in clean_text(str(c)).lower() and c not in cols_reales), None)
                                    
                                    if col_match and col_match not in cols_reales: 
                                        cols_reales.append(col_match); nombres_finales.append(nombre_nuevo)
                                
                                if cols_reales:
                                    df_pdi_mostrar = df_pdi_filtrado[cols_reales].copy()
                                    df_pdi_mostrar.columns = nombres_finales
                                    
                                    col_acc_tabla = next((c for c in df_pdi_mostrar.columns if 'Acciones' in c), None)
                                    if col_acc_tabla: df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_acc_tabla].astype(str).str.strip() != ""]
                                        
                                    total_acciones = len(df_pdi_mostrar)
                                    col_pdi_kpi = next((c for c in df_pdi_mostrar.columns if 'PDI (70/20/10)' == c), None)
                                    col_av_tabla = next((c for c in df_pdi_mostrar.columns if 'Avance' in c), None)
                                    
                                    prom_70 = prom_20 = prom_10 = promedio_avance = 0.0
                                    
                                    def get_avg(mask):
                                        if col_av_tabla and mask.sum() > 0:
                                            avances_limpios = df_pdi_mostrar.loc[mask, col_av_tabla].astype(str).str.replace('%', '', regex=False).str.extract(r'(\d+)').astype(float)
                                            return round(avances_limpios[0].mean(), 1) if not avances_limpios.isna().all().all() else 0.0
                                        return 0.0
                                    
                                    if total_acciones > 0 and col_pdi_kpi:
                                        mask_70 = df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains('70')
                                        mask_20 = df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains('20')
                                        mask_10 = df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains('10')
                                        prom_70, prom_20, prom_10 = get_avg(mask_70), get_avg(mask_20), get_avg(mask_10)
                                        promedio_avance = get_avg(pd.Series(True, index=df_pdi_mostrar.index))
                                        
                                    st.markdown("#### 📊 Análisis Global del Modelo 70-20-10")
                                    
                                    falta_evaluacion = 0
                                    lista_falta_eval = []
                                    if not df_matriz_competencias.empty:
                                        col_puesto_matriz = buscar_columna(df_matriz_competencias.columns, 'puesto')
                                        df_equipo = df_completo[df_completo['Nombre_Cruce'].isin(equipo_permitido)] if not si_es_admin else df_completo
                                        
                                        for _, colab_info in df_equipo.iterrows():
                                            c_nombre = str(colab_info.get("Nombre", "")).strip()
                                            c_nom_limpio = c_nombre.lower()
                                            c_puesto = str(colab_info.get("Nombre de la Posición", "")).strip()
                                            
                                            puesto_words = clean_and_split(c_puesto)
                                            df_matriz_competencias['_score'] = df_matriz_competencias[col_puesto_matriz].apply(
                                                lambda x: len(puesto_words.intersection(clean_and_split(x)))
                                            )
                                            max_score = df_matriz_competencias['_score'].max()
                                            comps_esperadas = 0
                                            
                                            if max_score > 0 and max_score >= (len(puesto_words) * 0.5):
                                                fila_m = df_matriz_competencias[df_matriz_competencias['_score'] == max_score].iloc[0]
                                                f_cols = [c for c in df_matriz_competencias.columns if 'comp' in str(c).lower() and 'puesto' not in str(c).lower() and str(c).strip().lower() != 'competencia']
                                                t_cols = [c for c in df_matriz_competencias.columns if 'tec' in str(c).lower() or ('con' in str(c).lower() and 'comp' not in str(c).lower())]
                                                lista_f = [c.strip() for c in fila_m[f_cols].dropna().astype(str).tolist() if c.strip() and c.lower() != 'nan']
                                                lista_t = [c.strip() for c in fila_m[t_cols].dropna().astype(str).tolist() if c.strip() and c.lower() != 'nan']
                                                comps_esperadas = len(lista_f) + len(lista_t)
                                                
                                            comps_evaluadas = 0
                                            if comps_esperadas > 0 and not df_evaluaciones.empty and "Nombre" in df_evaluaciones.columns and "Calif. Líder" in df_evaluaciones.columns:
                                                ev_colab = df_evaluaciones[df_evaluaciones["Nombre"].astype(str).str.strip().str.lower() == c_nom_limpio]
                                                ev_completas = ev_colab[ev_colab['Calif. Líder'].astype(str).str.strip() != ""]
                                                comps_evaluadas = len(ev_completas)
                                                
                                            if comps_esperadas > 0 and comps_evaluadas < comps_esperadas:
                                                falta_evaluacion += (comps_esperadas - comps_evaluadas)
                                                lista_falta_eval.append(c_nombre)

                                    # ✨ CORRECCIÓN AQUÍ: Usar 'Nombre' en lugar de 'Colaborador' en df_pdi_filtrado
                                    lista_pdi_iniciados = df_pdi_filtrado['Nombre'].dropna().astype(str).str.strip().str.lower().unique().tolist()
                                    nombres_equipo_originales = []
                                    df_equipo_raw = df_completo[df_completo['Nombre_Cruce'].isin(equipo_permitido)] if not si_es_admin else df_completo
                                    for _, r in df_equipo_raw.iterrows():
                                        nom_orig = str(r.get("Nombre", "")).strip()
                                        if nom_orig and nom_orig.lower() != st.session_state["nombre_usuario"].strip().lower(): 
                                            nombres_equipo_originales.append(nom_orig)
                                            
                                    nombres_equipo_originales = list(set(nombres_equipo_originales))
                                    lista_pdi_faltantes = [n for n in nombres_equipo_originales if n.lower() not in lista_pdi_iniciados]
                                    total_faltantes_pdi = len(lista_pdi_faltantes)

                                    pk1, pk2, pk3, pk4, pk5, pk6, pk7 = st.columns(7)
                                    
                                    with pk1:
                                        if st.button(f"📊 Total Acciones\n\n{total_acciones}", key="b_pdi_todas", use_container_width=True): 
                                            st.session_state['filtro_pdi_cat'] = 'todas'; st.rerun()
                                    with pk2:
                                        st.button(f"📈 Avance Prom.\n\n{promedio_avance}%", key="b_pdi_prom", use_container_width=True)
                                    with pk3:
                                        if st.button(f"🔵 Experiencia\n\n{prom_70}%", key="b_pdi_70", use_container_width=True):
                                            st.session_state['filtro_pdi_cat'] = '70'; st.rerun()
                                    with pk4:
                                        if st.button(f"🟡 Mentoring\n\n{prom_20}%", key="b_pdi_20", use_container_width=True):
                                            st.session_state['filtro_pdi_cat'] = '20'; st.rerun()
                                    with pk5:
                                        if st.button(f"🔴 Formación\n\n{prom_10}%", key="b_pdi_10", use_container_width=True):
                                            st.session_state['filtro_pdi_cat'] = '10'; st.rerun()
                                    with pk6:
                                        if st.button(f"⚠️ Falta Eval. Líder\n\n{falta_evaluacion} comps.", key="b_pdi_falta_eval", use_container_width=True):
                                            st.session_state['filtro_pdi_cat'] = 'falta_eval'; st.rerun()
                                    with pk7:
                                        if st.button(f"🚨 Faltan Capturar PDI\n\n{total_faltantes_pdi} colabs.", key="b_pdi_no_iniciado", use_container_width=True):
                                            st.session_state['filtro_pdi_cat'] = 'no_iniciado'; st.rerun()
                                            
                                    st.write("---")
                                    
                                    if 'filtro_pdi_cat' in st.session_state and st.session_state['filtro_pdi_cat'] not in ['todas', None]:
                                        f_cat = st.session_state['filtro_pdi_cat']
                                        c_f1, c_f2 = st.columns([8, 2])
                                        
                                        if f_cat == 'falta_eval':
                                            lista_unica_falta_eval = list(set(lista_falta_eval))
                                            if lista_unica_falta_eval:
                                                df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Colaborador'].isin(lista_unica_falta_eval)]
                                                c_f1.error(f"🚨 **Alerta de Evaluación:** Tienes competencias pendientes de calificar para estos colaboradores: {', '.join(lista_unica_falta_eval)}")
                                            else:
                                                df_pdi_mostrar = df_pdi_mostrar.iloc[0:0] 
                                                c_f1.success(f"✅ ¡Felicidades! Has evaluado todas las competencias técnicas y funcionales de tu equipo.")
                                                
                                        elif f_cat == 'no_iniciado':
                                            df_pdi_mostrar = df_pdi_mostrar.iloc[0:0]
                                            if lista_pdi_faltantes:
                                                c_f1.error(f"🚨 **Alerta de PDI no iniciado:** Los siguientes colaboradores de tu equipo aún no han subido ninguna actividad de PDI: **{', '.join(lista_pdi_faltantes)}**")
                                            else:
                                                c_f1.success(f"✅ ¡Excelente! Todo tu equipo ha capturado su PDI.")
                                                
                                        else:
                                            if col_pdi_kpi:
                                                df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains(f_cat)]
                                                c_f1.info(f"👆 **Filtro Activo:** Mostrando exclusivamente las acciones de la categoría **{f_cat}%**.")
                                        
                                        if c_f2.button("❌ Quitar filtro", use_container_width=True): 
                                            st.session_state['filtro_pdi_cat'] = None; st.rerun()
                                    
                                    col_p1, col_p2, col_p3 = st.columns(3)
                                    lista_nombres_pdi = []
                                    if "Colaborador" in df_pdi_mostrar.columns:
                                        lista_nombres_pdi = sorted(df_pdi_mostrar['Colaborador'].dropna().astype(str).unique().tolist())
                                        filtro_nombre = col_p1.multiselect("👤 Filtrar por Colaborador:", options=lista_nombres_pdi)
                                        if filtro_nombre: df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Colaborador'].isin(filtro_nombre)]
                                    
                                    col_filtro_cat = col_pdi_kpi if col_pdi_kpi else next((c for c in df_pdi_mostrar.columns if 'Clasificación' in c), None)
                                    if col_filtro_cat:
                                        lista_clasif_pdi = sorted(df_pdi_mostrar[col_filtro_cat].dropna().astype(str).unique().tolist())
                                        filtro_clasif = col_p2.multiselect("🏷️ Filtrar por Categoría / PDI:", options=lista_clasif_pdi)
                                        if filtro_clasif: df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_filtro_cat].isin(filtro_clasif)]
                                    
                                    if "Estatus" in df_pdi_mostrar.columns:
                                        lista_estatus_pdi = sorted(df_pdi_mostrar['Estatus'].dropna().astype(str).unique().tolist())
                                        filtro_estatus = col_p3.multiselect("🚦 Filtrar por Estatus:", options=lista_estatus_pdi)
                                        if filtro_estatus: df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Estatus'].isin(filtro_estatus)]
                                    
                                    st.dataframe(df_pdi_mostrar, use_container_width=True, hide_index=True)
                                    
                                    st.write("---")
                                    st.markdown("#### 📝 Evaluar Competencias de mi Equipo")
                                    st.info("Selecciona a uno de tus colaboradores para evaluar sus Conocimientos Técnicos y Competencias Funcionales.")
                                    
                                    todos_los_nombres_equipo = sorted(list(set(lista_nombres_pdi + lista_pdi_faltantes)))
                                    
                                    colab_a_evaluar = st.selectbox("Seleccionar Colaborador:", [""] + todos_los_nombres_equipo, key="sel_eval_equipo")
                                    
                                    if colab_a_evaluar:
                                        st.markdown(f"**Evaluando a:** {colab_a_evaluar}")
                                        renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior, df_mla, df_matriz_competencias, df_evaluaciones, es_lider_evaluando=True, empleado_a_evaluar=colab_a_evaluar)
                                        
                                else: st.warning("⚠️ Esperando el primer guardado para construir la tabla de seguimiento.")
                            else: st.warning("⚠️ No hay planes de desarrollo registrados en el equipo todavía.")
                            
                    elif nombre_tab == "📝 Mi PDI":
                        with tabs_creados[i]:
                            renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior, df_mla, df_matriz_competencias, df_evaluaciones, es_lider_evaluando=False)
                            
                    elif nombre_tab == "📊 Reportes e IA":
                        with tabs_creados[i]:
                            renderizar_reportes(df_seguro, df_completo, df_pdi, df_mla, kpis, f_jerarquia, f_puesto)
                            
                    elif nombre_tab == "⚙️ Panel de Administración":
                        with tabs_creados[i]:
                            st.markdown("### ⚙️ Gestión de Plataforma y Usuarios")
                            
                            st.markdown("#### 🔄 Gestión de Ciclos PDI (Nivel Enterprise)")
                            st.info(f"**Ciclo de Planeación Actual:** {st.session_state.get('pdi_planeacion')} | **Ciclo de Cierre (Evaluación):** {st.session_state.get('pdi_cierre')}")
                            
                            nuevo_anio = st.number_input("Año del próximo ciclo de PDI", min_value=2025, max_value=2050, value=2028, step=1)
                            
                            if st.button(f"✨ Abrir Nuevo Ciclo: PDI {nuevo_anio}", use_container_width=True):
                                with st.spinner(f"Creando la infraestructura para PDI {nuevo_anio}..."):
                                    try:
                                        secretos = st.secrets["connections"]["gsheets"]
                                        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                        cliente = gspread.authorize(credenciales)
                                        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                        doc_id = match.group(1) if match else LINK_ARCHIVO
                                        archivo = cliente.open_by_key(doc_id)
                                        
                                        nuevo_nombre_hoja = f"PDI {nuevo_anio}"
                                        hojas_existentes = [ws.title for ws in archivo.worksheets()]
                                        
                                        if nuevo_nombre_hoja in hojas_existentes:
                                            st.warning(f"⚠️ La pestaña '{nuevo_nombre_hoja}' ya existe en tu Google Sheets.")
                                        else:
                                            nueva_hoja = archivo.add_worksheet(title=nuevo_nombre_hoja, rows="1000", cols="26")
                                            nueva_hoja.append_row(COLUMNAS_PDI)
                                            
                                            ws_meta = archivo.worksheet("Metadata")
                                            viejo_planeacion = st.session_state.get('pdi_planeacion', 'PDI 2027')
                                            ws_meta.update_acell('E1', nuevo_nombre_hoja)
                                            ws_meta.update_acell('F1', viejo_planeacion)
                                            ws_meta.update_acell('A1', str(time.time()))
                                            
                                            st.cache_data.clear()
                                            st.success(f"✅ ¡Ciclo {nuevo_anio} creado! La plataforma entera se ha actualizado automáticamente.")
                                            time.sleep(2)
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error al crear el nuevo ciclo: {e}")
                                        
                            st.divider()

                            st.markdown("#### 🔐 Control de Periodos Operativos")
                            col_candado1, col_candado2 = st.columns(2)

                            with col_candado1:
                                estado_suc = st.session_state.get("estado_sucesion", "ABIERTO")
                                st.info("Bloquea la edición de Sucesores.")
                                n_estado_suc = st.radio("Estado del Módulo de Sucesión", ["ABIERTO", "CERRADO"], index=0 if estado_suc=="ABIERTO" else 1, horizontal=True)

                            with col_candado2:
                                estado_pdi_val = st.session_state.get("estado_pdi", "ABIERTO")
                                st.info("Bloquea la captura del PDI.")
                                n_estado_pdi = st.radio("Estado del Módulo de PDI", ["ABIERTO", "CERRADO"], index=0 if estado_pdi_val=="ABIERTO" else 1, horizontal=True)

                            if st.button("Aplicar Estados de Periodos", use_container_width=True):
                                with st.spinner("Actualizando seguridad en toda la red..."):
                                    secretos = st.secrets["connections"]["gsheets"]
                                    credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                    cliente = gspread.authorize(credenciales)
                                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                    doc_id = match.group(1) if match else LINK_ARCHIVO
                                    archivo = cliente.open_by_key(doc_id)
                                    
                                    ws_meta = archivo.worksheet("Metadata")
                                    ws_meta.update_acell('C1', n_estado_suc)
                                    ws_meta.update_acell('D1', n_estado_pdi)
                                    ws_meta.update_acell('A1', str(time.time()))
                                    
                                    st.cache_data.clear()
                                    st.success(f"✅ ¡Periodos actualizados exitosamente!")
                                    time.sleep(1.5)
                                    st.rerun()

                            st.divider()

                            st.info("Administra los accesos a la plataforma. Estos se sincronizan en vivo con tu pestaña 'Usuarios' de Google Sheets.")

                            df_u_admin = df_usuarios_permisos

                            sub_tab_nuevo, sub_tab_editar = st.tabs(["➕ Agregar Nuevo Perfil", "✏️ Editar / Eliminar Perfil"])

                            opciones_modulos = ["TODOS", "MAPA", "SUCESIÓN", "PDI EQUIPO", "REPORTES"]

                            with sub_tab_nuevo:
                                with st.form("nuevo_usuario_form", clear_on_submit=True):
                                    st.markdown("#### Crear Alta de Usuario")
                                    lista_empleados_busqueda = []
                                    for _, r in df_completo.iterrows():
                                        nom, nombre = clean_id(r.get('id Empleado')), clean_text(r.get('Nombre'))
                                        if nom and nombre: lista_empleados_busqueda.append(f"{nom} - {nombre}")
                                    lista_empleados_busqueda = sorted(list(set(lista_empleados_busqueda)))
                                    
                                    seleccion_empleado = st.selectbox("🔍 Buscar colaborador (Por Número de Nómina o Nombre)", [""] + lista_empleados_busqueda)
                                    n_pass = st.text_input(f"Contraseña temporal (Sugerencia: {PASSWORD_POR_DEFECTO})", value=PASSWORD_POR_DEFECTO)
                                    n_dir_list = st.multiselect("🏢 Direcciones Permitidas (Elige 'TODAS', 'COLABORADOR' o múltiples áreas)", ["TODAS", "COLABORADOR"] + dirs)
                                    
                                    lideres_para_admin = sorted(df_completo['Nombre'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
                                    n_lider_list = st.multiselect("👤 Líder Restringido (Filtro por jerarquía de equipo)", ["TODOS"] + lideres_para_admin, default=["TODOS"])
                                    
                                    n_mods_list = st.multiselect("🧩 Módulos Permitidos en Pantalla", opciones_modulos, default=["TODOS"])
                                    
                                    submit_btn = st.form_submit_button("Crear Nuevo Usuario")
                                    
                                    if submit_btn:
                                        if seleccion_empleado and n_pass and n_dir_list and n_mods_list:
                                            n_user, n_nombre = seleccion_empleado.split(" - ")[0].strip(), seleccion_empleado.split(" - ")[1].strip()
                                            n_dir = ", ".join(n_dir_list)
                                            n_lider = ", ".join(n_lider_list) if n_lider_list else "TODOS"
                                            n_mods = ", ".join(n_mods_list)
                                            
                                            with st.spinner("🤖 Guardando y encriptando usuario..."):
                                                try:
                                                    secretos = st.secrets["connections"]["gsheets"]
                                                    credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                                    cliente = gspread.authorize(credenciales)
                                                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                                    doc_id = match.group(1) if match else LINK_ARCHIVO
                                                    archivo = cliente.open_by_key(doc_id)
                                                    
                                                    pestana_users = archivo.worksheet("Usuarios")
                                                    
                                                    enc_u = pestana_users.row_values(1)
                                                    if "Modulos" not in enc_u:
                                                        pestana_users.update_cell(1, len(enc_u) + 1, "Modulos")
                                                    
                                                    pestana_users.append_row([n_user, n_nombre, hash_password(n_pass), n_dir, n_lider, n_mods])
                                                    archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                    
                                                    st.success(f"✅ ¡Usuario '{n_nombre}' ({n_user}) creado exitosamente! Ya puede iniciar sesión.")
                                                    st.cache_data.clear()
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                except Exception as e: st.error(f"❌ Error al crear el usuario. Detalles: {e}")
                                        else: st.warning("⚠️ Debes rellenar todos los campos para crear el usuario.")
                            
                            with sub_tab_editar:
                                if not df_u_admin.empty:
                                    lista_usuarios_edit = []
                                    for _, r in df_u_admin.iterrows():
                                        u_id_val, u_nom_val = str(r.get("Usuario", "")).strip(), str(r.get("Nombre", "")).strip()
                                        if u_id_val: lista_usuarios_edit.append(f"{u_id_val} - {u_nom_val}")
                                    
                                    usuario_a_editar = st.selectbox("🔍 Selecciona el usuario a modificar", [""] + sorted(lista_usuarios_edit))
                                    
                                    if usuario_a_editar:
                                        u_id_sel = usuario_a_editar.split(" - ")[0].strip()
                                        datos_u = df_u_admin[df_u_admin['Usuario'].astype(str).str.strip() == u_id_sel].iloc[0]
                                        
                                        c_pass = str(datos_u.get("Password", ""))
                                        c_dir = str(datos_u.get("Direccion", ""))
                                        c_lid = str(datos_u.get("Lider Restringido", "TODOS"))
                                        c_mods = str(datos_u.get("Modulos", "TODOS"))
                                        
                                        c_dir_list = [d.strip() for d in c_dir.split(",")] if c_dir else []
                                        opciones_dir = ["TODAS", "COLABORADOR"] + dirs
                                        c_dir_list_valid = [d for d in c_dir_list if d in opciones_dir]
                                        
                                        c_lid_list = [l.strip() for l in c_lid.split(",")] if c_lid else ["TODOS"]
                                        opciones_lid = ["TODOS"] + lideres_para_admin
                                        c_lid_list_valid = [l for l in c_lid_list if l in opciones_lid]
                                        if not c_lid_list_valid: c_lid_list_valid = ["TODOS"]
                                        
                                        c_mods_list = [m.strip().upper() for m in c_mods.split(",")] if c_mods and c_mods != "nan" else ["TODOS"]
                                        c_mods_list_valid = [m for m in c_mods_list if m in opciones_modulos]
                                        if not c_mods_list_valid: c_mods_list_valid = ["TODOS"]
                                        
                                        with st.form("editar_usuario_form"):
                                            st.markdown(f"#### Editando a: {usuario_a_editar.split(' - ')[1]}")
                                            e_pass = st.text_input("Contraseña (Dejar igual si no deseas cambiarla)", value=c_pass)
                                            e_dir_list = st.multiselect("🏢 Direcciones Permitidas", opciones_dir, default=c_dir_list_valid)
                                            e_lider_list = st.multiselect("👤 Líder Restringido (Filtro por jerarquía de equipo)", opciones_lid, default=c_lid_list_valid)
                                            
                                            e_mods_list = st.multiselect("🧩 Módulos Permitidos", opciones_modulos, default=c_mods_list_valid)
                                            
                                            col_b1, col_b2 = st.columns(2)
                                            btn_actualizar = col_b1.form_submit_button("💾 Actualizar Permisos", type="primary", use_container_width=True)
                                            btn_eliminar = col_b2.form_submit_button("🗑️ Eliminar Usuario", use_container_width=True)
                                            
                                            if btn_actualizar:
                                                if e_dir_list and e_mods_list:
                                                    e_dir_str = ", ".join(e_dir_list)
                                                    e_lider_str = ", ".join(e_lider_list) if e_lider_list else "TODOS"
                                                    e_mods_str = ", ".join(e_mods_list)
                                                    
                                                    pass_to_save = hash_password(e_pass) if e_pass != c_pass else c_pass

                                                    with st.spinner("🤖 Actualizando usuario por lotes (Batch Update)..."):
                                                        try:
                                                            secretos = st.secrets["connections"]["gsheets"]
                                                            credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                                            cliente = gspread.authorize(credenciales)
                                                            match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                                            doc_id = match.group(1) if match else LINK_ARCHIVO
                                                            archivo = cliente.open_by_key(doc_id)
                                                            
                                                            pestana_users = archivo.worksheet("Usuarios")
                                                            
                                                            enc_u = pestana_users.row_values(1)
                                                            col_mods_idx = buscar_columna(enc_u, "modulos")
                                                            if not col_mods_idx:
                                                                pestana_users.update_cell(1, len(enc_u) + 1, "Modulos")
                                                                col_idx_letra = gspread.utils.rowcol_to_a1(1, len(enc_u) + 1)[0]
                                                            else:
                                                                col_idx_letra = gspread.utils.rowcol_to_a1(1, enc_u.index(col_mods_idx) + 1)[0]
                                                            
                                                            usuarios_col = pestana_users.col_values(1)
                                                            
                                                            try:
                                                                fila_usuario = usuarios_col.index(u_id_sel) + 1
                                                                pestana_users.update(values=[[pass_to_save, e_dir_str, e_lider_str]], range_name=f"C{fila_usuario}:E{fila_usuario}")
                                                                pestana_users.update_cell(fila_usuario, gspread.utils.a1_to_rowcol(f"{col_idx_letra}1")[1], e_mods_str)
                                                                
                                                                archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                                st.cache_data.clear()
                                                                st.success(f"✅ ¡Usuario actualizado exitosamente!")
                                                                time.sleep(1.5)
                                                                st.rerun()
                                                            except ValueError: st.error("❌ El usuario no fue encontrado en la hoja de Excel.")
                                                        except Exception as e: st.error(f"❌ Error de conexión: {e}")
                                                else: st.warning("⚠️ Debes seleccionar al menos una Dirección Permitida y un Módulo.")
                                                    
                                            if btn_eliminar:
                                                with st.spinner("🗑️ Eliminando usuario de Google Sheets..."):
                                                    try:
                                                        secretos = st.secrets["connections"]["gsheets"]
                                                        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                                        cliente = gspread.authorize(credenciales)
                                                        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                                        doc_id = match.group(1) if match else LINK_ARCHIVO
                                                        archivo = cliente.open_by_key(doc_id)
                                                        
                                                        pestana_users = archivo.worksheet("Usuarios")
                                                        usuarios_col = pestana_users.col_values(1)
                                                        
                                                        try:
                                                            fila_usuario = usuarios_col.index(u_id_sel) + 1
                                                            pestana_users.delete_rows(fila_usuario)
                                                            archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                            st.cache_data.clear()
                                                            st.success(f"✅ ¡Usuario eliminado exitosamente!")
                                                            time.sleep(1.5)
                                                            st.rerun()
                                                        except ValueError: st.error("❌ El usuario no fue encontrado en la hoja de Excel.")
                                                    except Exception as e: st.error(f"❌ Error de conexión: {e}")
                                else: st.info("No hay usuarios registrados en la base de datos.")
                                    
if __name__ == "__main__":
    main()
