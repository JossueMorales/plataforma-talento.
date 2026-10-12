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
from google.oauth2.service_account import Credentials
import time

# --- IMPORTACIONES DE NUESTROS NUEVOS MÓDULOS ---
from config_ui import (
    OPCIONES_PYVIS, SCRIPT_ANILLOS, INYECCION_HTML_JS,
    crear_tarjeta_kpi, extraer_contexto, clean_text, clean_id,
    obtener_color_9box, acortar_nombre, acortar_puesto,
    get_readiness_val, get_dispersion_offset
)
# Eliminamos los nombres estáticos y agregamos las columnas desde nuestro módulo
from database import LINK_ARCHIVO, obtener_metadata, cargar_datos_csv
from auth import login, hash_password, PASSWORD_POR_DEFECTO

from modulos.mapa_org import generar_mapa_html, buscar_columna
from modulos.sucesion import renderizar_tab_sucesiones
from modulos.pdi import renderizar_mi_pdi, COLUMNAS_PDI

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
        
        # Leemos las 5 variables de metadata generadas de forma dinámica
        current_timestamp, estado_sucesion, estado_pdi, pdi_planeacion, pdi_cierre = obtener_metadata()
        
        st.session_state["estado_sucesion"] = estado_sucesion
        st.session_state["estado_pdi"] = estado_pdi
        st.session_state["pdi_planeacion"] = pdi_planeacion
        st.session_state["pdi_cierre"] = pdi_cierre
        
        df_completo_raw = cargar_datos_csv("Base de datos", current_timestamp)
        df_pdi = cargar_datos_csv(pdi_planeacion, current_timestamp)
        df_pdi_anterior = cargar_datos_csv(pdi_cierre, current_timestamp)
        
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
        
        if es_colaborador:
            renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior)
        else:
            if "TODAS" not in direccion_permitida:
                lista_dirs = [d.strip() for d in direccion_permitida.split(",")]
                mask_dir = df_completo['Dirección'].astype(str).str.upper().apply(lambda d_val: any(d in d_val for d in lista_dirs))
                df_seguro = df_completo[mask_dir | (df_completo[col_jer].astype(str).str.strip() == '5')]
            else:
                df_seguro = df_completo.copy()
                
            dict_nom_global = {clean_id(r.get('id Empleado')): clean_text(r.get('Nombre')) for r in df_completo.to_dict('records')}
            jerarquia_global = {}
            for j, e in zip(df_completo['ID Del Jefe'].astype(str).str.strip(), df_completo['id Empleado'].astype(str).str.strip()):
                j = clean_id(j)
                e = clean_id(e)
                if j not in jerarquia_global: jerarquia_global[j] = []
                jerarquia_global[j].append(e)

            if lider_permitido_str.upper() != "TODOS" and lider_permitido_str != "":
                lista_lideres_perm = [l.strip().lower() for l in lider_permitido_str.split(",")]
                lideres_ids_global = []
                for idx, nom in dict_nom_global.items():
                    if str(nom).strip().lower() in lista_lideres_perm: lideres_ids_global.append(idx)
                
                if not lideres_ids_global and lider_permitido_str.lower() == st.session_state["nombre_usuario"].strip().lower():
                    lideres_ids_global.append(clean_id(st.session_state["id_usuario"]))
                
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
                if st.session_state["id_usuario"] == "admin":
                    tab_mapa, tab_sucesiones, tab_pdi_equipo, tab_mi_pdi, tab_reportes, tab_admin = st.tabs([
                        "🗺 Mapa Organizacional", "🔀 Sucesión", "📈 Seguimiento de PDI", "📝 Mi PDI", "📊 Reportes e IA", "⚙️ Panel de Administración"
                    ])
                else:
                    tab_mapa, tab_sucesiones, tab_pdi_equipo, tab_mi_pdi = st.tabs([
                        "🗺️ Mapa Organizacional", "🔀 Sucesión", "📈 Seguimiento de PDI", "📝 Mi PDI"
                    ])
                
                with tab_mapa:
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
                
                with tab_sucesiones:
                    f_lid_plan, subordinados_nombres_limpios = renderizar_tab_sucesiones(
                        df_seguro, df_completo, df_pdi, dict_nom_global, jerarquia_global, 
                        kpis, f_jerarquia, f_puesto, direccion_permitida, match_nomina
                    )

                with tab_pdi_equipo:
                    st.markdown("### 📈 Seguimiento de PDI de mi Equipo")
                    st.info("Gracias a la nueva arquitectura multifila, ahora puedes ver el estatus granular de cada acción del plan 70-20-10 de tus colaboradores.")
                    if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                        nombres_visibles_limpios = [str(d['Nombre']).strip().lower() for d in kpis['data_total']]
                        df_pdi_filtrado = df_pdi.copy()
                        
                        if f_lid_plan != "Todos":
                            nombres_cruce_lid = df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower()
                            df_pdi_filtrado = df_pdi_filtrado[nombres_cruce_lid.isin(subordinados_nombres_limpios)]
                        else:
                            nombres_cruce_vis = df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower()
                            df_pdi_filtrado = df_pdi_filtrado[nombres_cruce_vis.isin(nombres_visibles_limpios)]
                        
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
                            pk1, pk2, pk3, pk4, pk5 = st.columns(5)
                            
                            with pk1:
                                if st.button(f"📊 Total Acciones\n\n{total_acciones}", key="b_pdi_todas", use_container_width=True): 
                                    st.session_state['filtro_pdi_cat'] = 'todas'; st.rerun()
                            with pk2:
                                st.button(f"📈 Avance Promedio\n\n{promedio_avance}%", key="b_pdi_prom", use_container_width=True)
                            with pk3:
                                if st.button(f"🔵 Experiencia (70%)\n\n{prom_70}%", key="b_pdi_70", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '70'; st.rerun()
                            with pk4:
                                if st.button(f"🟡 Mentoring (20%)\n\n{prom_20}%", key="b_pdi_20", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '20'; st.rerun()
                            with pk5:
                                if st.button(f"🔴 Formación (10%)\n\n{prom_10}%", key="b_pdi_10", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '10'; st.rerun()
                                    
                            st.write("---")
                            
                            if 'filtro_pdi_cat' in st.session_state and st.session_state['filtro_pdi_cat'] not in ['todas', None]:
                                f_cat = st.session_state['filtro_pdi_cat']
                                if col_pdi_kpi:
                                    df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains(f_cat)]
                                    c_f1, c_f2 = st.columns([8, 2])
                                    c_f1.info(f"👆 **Filtro Activo:** Mostrando exclusivamente las acciones de la categoría **{f_cat}%**.")
                                    if c_f2.button("❌ Quitar filtro", use_container_width=True): st.session_state['filtro_pdi_cat'] = None; st.rerun()
                            
                            col_p1, col_p2, col_p3 = st.columns(3)
                            if "Colaborador" in df_pdi_mostrar.columns:
                                lista_nombres_pdi = sorted(df_pdi_mostrar['Colaborador'].dropna().astype(str).unique().tolist())
                                filtro_nombre = col_p1.multiselect("👤 Filtrar por Colaborador:", options=lista_nombres_pdi)
                                if filtro_nombre: df_pdi_mostrar = df_pdi_mostrar['Colaborador'].isin(filtro_nombre)
                            
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
                        else: st.warning("⚠️ Esperando el primer guardado para construir la tabla de seguimiento.")
                    else: st.warning("⚠️ No hay planes de desarrollo registrados en el equipo todavía.")
                
                with tab_mi_pdi:
                    renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior)
                
                if st.session_state["id_usuario"] == "admin":
                    with tab_reportes:
                        st.markdown("### 🧠 Inteligencia de Datos y Reportes")
                        st.info("Esta sección es exclusiva para la Dirección. Configura tu reporte, elige el enfoque del análisis y descarga la información limpia.")
                        
                        df_reportes_base = df_seguro.copy()
                        df_reportes_base['id_clean'] = df_reportes_base['id Empleado'].apply(clean_id)
                        nodos_estrictos_ids = kpis.get('nodos_visibles_ids', [])
                        df_reportes_estricto = df_reportes_base[df_reportes_base['id_clean'].isin(nodos_estrictos_ids)].copy()
                        
                        is_admin = st.session_state.get("id_usuario") == "admin"
                        wants_level_5 = is_admin and (('5' in f_jerarquia) or (f_puesto and any('DIRECTOR GENERAL' in p.upper() for p in f_puesto)))
                        
                        if not wants_level_5:
                            col_jer_rep = next((c for c in df_reportes_estricto.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')
                            df_reportes_estricto = df_reportes_estricto[
                                (df_reportes_estricto[col_jer_rep].astype(str).str.strip() != '5') &
                                (~df_reportes_estricto['Nombre de la Posición'].astype(str).str.upper().str.contains('DIRECTOR GENERAL'))
                            ]
                        
                        st.markdown("#### 1️⃣ Configuración de los Datos")
                        col_rep1, col_rep2 = st.columns([1, 2])
                        with col_rep1:
                            tipo_reporte = st.radio("¿A quiénes deseas incluir en las filas?", ["Solo Posiciones Críticas", "Todos los Colaboradores (Según filtros)"])
                            enriquecer_reporte = st.checkbox("🔄 Enriquecer reporte con datos de Sucesores (Dirección, 9-Box, EDR, etc.)", value=False)
                        
                        posiciones_criticas_filtro = df_reportes_estricto[df_reportes_estricto['Posición Crítica'].astype(str).str.strip().str.lower() == 'si'].copy()
                        df_base_export = posiciones_criticas_filtro.copy() if tipo_reporte == "Solo Posiciones Críticas" else df_reportes_estricto.copy()
                        
                        if not df_base_export.empty:
                            if enriquecer_reporte:
                                with st.spinner("Cruzando datos de talento en memoria..."):
                                    dict_empleados = {}
                                    jer_key_global = next((k for k in df_completo.columns if 'jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower()), 'Nivel Jerárquico')
                                    for _, row_emp in df_completo.iterrows():
                                        nom_key = str(row_emp.get('Nombre', '')).strip().lower()
                                        if nom_key:
                                            dict_empleados[nom_key] = {
                                                'Dirección': clean_text(row_emp.get('Dirección', row_emp.get('Direccion', ''))),
                                                'Nivel Jerárquico': clean_text(row_emp.get(jer_key_global, '')),
                                                '9-Box': clean_text(row_emp.get('Resultado 9 box', '')),
                                                'EDR': clean_text(row_emp.get('EDR', row_emp.get('EDR ', '')))
                                            }
                                    
                                    for i in range(1, 6):
                                        col_suc_name = buscar_columna(df_base_export.columns, 'sucesor', i)
                                        if col_suc_name:
                                            dir_list, jer_list, box_list, edr_list = [], [], [], []
                                            for _, r in df_base_export.iterrows():
                                                suc_val = str(r.get(col_suc_name, '')).strip().lower()
                                                if suc_val and suc_val not in ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']:
                                                    datos_suc = dict_empleados.get(suc_val, {})
                                                    dir_list.append(datos_suc.get('Dirección', 'No Encontrado'))
                                                    jer_list.append(datos_suc.get('Nivel Jerárquico', 'N/A'))
                                                    box_list.append(datos_suc.get('9-Box', 'Pendiente'))
                                                    edr_list.append(datos_suc.get('EDR', 'Pendiente'))
                                                else:
                                                    dir_list.append(''); jer_list.append(''); box_list.append(''); edr_list.append('')
                                            
                                            df_base_export[f'Sucesor {i} - Dirección'] = dir_list
                                            df_base_export[f'Sucesor {i} - Nivel Jerárquico'] = jer_list
                                            df_base_export[f'Sucesor {i} - 9 Box'] = box_list
                                            df_base_export[f'Sucesor {i} - EDR'] = edr_list

                            todas_las_columnas = df_base_export.columns.tolist()
                            columnas_limpias = [c for c in todas_las_columnas if c not in ['id_clean', 'Cat_Sucesion', 'Tiene_Sucesor', '_peso_jerarquia', 'Sucesor_Limpio']]
                            
                            col_jer_limpia = next((c for c in columnas_limpias if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')
                            col_suc1_limpia = buscar_columna(columnas_limpias, 'sucesor', 1)
                            
                            cols_default = ['Nombre', 'Nombre de la Posición', 'Dirección', 'Líder', col_jer_limpia, 'Resultado 9 box', 'EDR']
                            if col_suc1_limpia:
                                col_read1_limpia = buscar_columna(columnas_limpias, 'readiness', 1)
                                if col_read1_limpia: cols_default.append(col_read1_limpia)
                                cols_default.append(col_suc1_limpia)
                            
                            if enriquecer_reporte: cols_default.extend(['Sucesor 1 - Dirección', 'Sucesor 1 - 9 Box', 'Sucesor 1 - EDR'])
                            cols_sugeridas = [c for c in cols_default if c in columnas_limpias]
                            
                            with col_rep2:
                                columnas_seleccionadas = st.multiselect("Selecciona las columnas a exportar:", options=columnas_limpias, default=cols_sugeridas)
                        
                        st.write("---")
                        st.markdown("#### 🤖 2️⃣ Analista Interno (Resumen Automático)")
                        tipo_analisis = st.radio("Selecciona el enfoque del análisis de IA:", ["🏢 Análisis de Estructura (Demografía)", "🔀 Análisis de Sucesión (Riesgo)", "📈 Análisis de Desarrollo (PDI)"], horizontal=True)
                        
                        if df_base_export.empty: st.warning("⚠️ No hay datos con los filtros actuales para analizar.")
                        else:
                            def eval_status_rep(row):
                                invalid_sucs = ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']
                                estados_encontrados = []
                                for i in range(1, 6):
                                    c_s = buscar_columna(row.index, 'sucesor', i)
                                    c_r = buscar_columna(row.index, 'readiness', i)
                                    if c_s and c_r:
                                        suc_val, read_val = clean_text(row.get(c_s, '')).strip().lower(), clean_text(row.get(c_r, '')).strip().lower()
                                        if suc_val and suc_val not in invalid_sucs and "vacante" not in suc_val:
                                            if 'inmediato' in read_val: estados_encontrados.append(1)
                                            elif '1 a 3' in read_val: estados_encontrados.append(2)
                                            elif 'mas de 3' in read_val or 'más de 3' in read_val: estados_encontrados.append(3)
                                            else: estados_encontrados.append(4)
                                if not estados_encontrados: return 'sin_sucesor'
                                mejor_estado = min(estados_encontrados)
                                if mejor_estado == 1: return 'inmediato'
                                if mejor_estado == 2: return '1_3_anos'
                                if mejor_estado == 3: return 'mas_3_anos'
                                return 'pendiente'

                            if "Estructura" in tipo_analisis:
                                tot = len(df_base_export)
                                dirs_count = df_base_export['Dirección'].nunique() if 'Dirección' in df_base_export.columns else 0
                                jer_col = next((c for c in df_base_export.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), None)
                                if jer_col:
                                    j_counts = df_base_export[jer_col].value_counts().to_dict()
                                    j_text = ", ".join([f"Nivel {k}: {v}" for k, v in j_counts.items() if str(k).strip() != ''])
                                else: j_text = "N/A"
                                
                                texto_ia = f"**💡 Hallazgos Estructurales:**\n- Vas a exportar un total de **{tot} colaboradores** distribuidos en **{dirs_count} Direcciones/Áreas**.\n- **Desglose Jerárquico:** {j_text}.\n- **Contexto:** Esta vista te permite auditar la composición de tu plantilla y asegurar que la distribución de talento esté equilibrada."
                                st.success(texto_ia)
                                
                            elif "Sucesión" in tipo_analisis:
                                df_suc_analisis = posiciones_criticas_filtro.copy() if tipo_reporte == "Solo Posiciones Críticas" else df_reportes_estricto[df_reportes_estricto['Posición Crítica'].astype(str).str.strip().str.lower() == 'si'].copy()
                                
                                if df_suc_analisis.empty: st.info("💡 En la selección actual no hay posiciones críticas para analizar la sucesión.")
                                else:
                                    df_suc_analisis['Cat_Sucesion'] = df_suc_analisis.apply(eval_status_rep, axis=1)
                                    rep_inm, rep_1_3, rep_mas_3, rep_sin = (df_suc_analisis['Cat_Sucesion'] == 'inmediato').sum(), (df_suc_analisis['Cat_Sucesion'] == '1_3_anos').sum(), (df_suc_analisis['Cat_Sucesion'] == 'mas_3_anos').sum(), (df_suc_analisis['Cat_Sucesion'] == 'sin_sucesor').sum()
                                    sucs_inm_rep, sucs_1_3_rep, sucs_mas_3_rep, sucs_totales = set(), set(), set(), set()
                                    invalid_sucs_local = ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']
                                    
                                    for i in range(1, 6):
                                        c_suc, c_read = buscar_columna(df_suc_analisis.columns, 'sucesor', i), buscar_columna(df_suc_analisis.columns, 'readiness', i)
                                        if c_suc and c_read:
                                            for _, r in df_suc_analisis.iterrows():
                                                n_s, r_s = clean_text(r.get(c_suc, '')).strip(), clean_text(r.get(c_read, '')).strip().lower()
                                                if n_s and n_s.lower() not in invalid_sucs_local and "vacante" not in n_s.lower():
                                                    sucs_totales.add(n_s)
                                                    if 'inmediato' in r_s: sucs_inm_rep.add(n_s)
                                                    elif '1 a 3' in r_s: sucs_1_3_rep.add(n_s)
                                                    elif 'mas de 3' in r_s or 'más de 3' in r_s: sucs_mas_3_rep.add(n_s)
                                    
                                    texto_ia = f"**💡 Hallazgos de Sucesión y Riesgo:**\n- Tienes **{len(df_suc_analisis)} posiciones críticas** en esta exportación.\n- Tu 'banca de talento' total cuenta con **{len(sucs_totales)} personas únicas**.\n\n**Salud por Posición:**\n- 🟢 **{rep_inm} posiciones** con cobertura **Inmediata**.\n- 🟡 **{rep_1_3} posiciones** a **1-3 años**.\n- 🔵 **{rep_mas_3} posiciones** a **+3 años**.\n- 🚨 **{rep_sin} posiciones** **sin sucesor identificado**."
                                    st.success(texto_ia)
                                    
                            elif "PDI" in tipo_analisis:
                                nombres_export = df_base_export['Nombre'].astype(str).str.strip().str.lower().tolist() if 'Nombre' in df_base_export.columns else []
                                if df_pdi.empty or not nombres_export: st.info("💡 No hay información de PDI registrada o no seleccionaste la columna 'Nombre'.")
                                else:
                                    nombres_base_busqueda = df_pdi['Nombre'].astype(str).str.strip().str.lower()
                                    df_pdi_exp = df_pdi[nombres_base_busqueda.isin(nombres_export)].copy()
                                    if df_pdi_exp.empty: st.info("💡 Los colaboradores seleccionados no tienen un PDI registrado.")
                                    else:
                                        col_acc = next((c for c in df_pdi_exp.columns if 'Acciones' in c), None)
                                        if col_acc: df_pdi_exp = df_pdi_exp[df_pdi_exp[col_acc].astype(str).str.strip() != ""]
                                        tot_acc = len(df_pdi_exp)
                                        col_av = next((c for c in df_pdi_exp.columns if 'Avance' in c), None)
                                        promedio = 0.0
                                        if col_av and tot_acc > 0:
                                            avances = df_pdi_exp[col_av].astype(str).str.replace('%', '', regex=False).str.extract(r'(\d+)').astype(float)
                                            promedio = round(avances[0].mean(), 1) if not avances.isna().all().all() else 0.0
                                        personas_con_pdi = df_pdi_exp['Nombre'].nunique() if 'Nombre' in df_pdi_exp.columns else 0
                                        
                                        texto_ia = f"**💡 Hallazgos de Desarrollo (70-20-10):**\n- De los exportados, **{personas_con_pdi}** cuentan con PDI.\n- Total de **{tot_acc} acciones** registradas.\n- El **avance promedio general es del {promedio}%**."
                                        st.success(texto_ia)
                                        
                        st.write("---")
                        if 'columnas_seleccionadas' in locals() and columnas_seleccionadas and not df_base_export.empty:
                            df_export = df_base_export[columnas_seleccionadas]
                            
                            csv_data = df_export.T.to_csv(header=False).encode('utf-8-sig')
                            st.download_button(label="📥 3️⃣ Descargar Reporte a Excel (Formato Transpuesto)", data=csv_data, file_name=f'Reporte_Inteligente_{st.session_state["nombre_usuario"].replace(" ", "_")}.csv', mime='text/csv', use_container_width=True, type="primary")
                        elif 'columnas_seleccionadas' in locals() and not columnas_seleccionadas:
                            st.warning("⚠️ Selecciona al menos una columna en el Paso 1 para habilitar la descarga del archivo.")

                    with tab_admin:
                        st.markdown("### ⚙️ Gestión de Plataforma y Usuarios")
                        
                        # --- NUEVO: BOTÓN MÁGICO DE CICLOS PDI ---
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
                                        # Crea la hoja nueva
                                        nueva_hoja = archivo.add_worksheet(title=nuevo_nombre_hoja, rows="1000", cols="26")
                                        # Le inyecta los headers oficiales
                                        nueva_hoja.append_row(COLUMNAS_PDI)
                                        
                                        # Actualiza la metadata
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
                        # --- FIN DEL BOTÓN MÁGICO ---

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

                        st.info("Administra los accesos a la plataforma. Estos se sincronizan en vivo con tu pestaña 'Usuarios' de Google Sheets usando encriptación SHA-256.")

                        current_timestamp_u, _, _, _, _ = obtener_metadata(LINK_ARCHIVO)
                        df_u_admin = cargar_datos_csv("Usuarios", current_timestamp_u, LINK_ARCHIVO)

                        sub_tab_nuevo, sub_tab_editar = st.tabs(["➕ Agregar Nuevo Perfil", "✏️ Editar / Eliminar Perfil"])

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
                                
                                submit_btn = st.form_submit_button("Crear Nuevo Usuario")
                                
                                if submit_btn:
                                    if seleccion_empleado and n_pass and n_dir_list:
                                        n_user, n_nombre = seleccion_empleado.split(" - ")[0].strip(), seleccion_empleado.split(" - ")[1].strip()
                                        n_dir = ", ".join(n_dir_list)
                                        n_lider = ", ".join(n_lider_list) if n_lider_list else "TODOS"
                                        
                                        with st.spinner("🤖 Guardando y encriptando usuario..."):
                                            try:
                                                secretos = st.secrets["connections"]["gsheets"]
                                                credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                                cliente = gspread.authorize(credenciales)
                                                match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                                doc_id = match.group(1) if match else LINK_ARCHIVO
                                                archivo = cliente.open_by_key(doc_id)
                                                
                                                pestana_users = archivo.worksheet("Usuarios")
                                                pestana_users.append_row([n_user, n_nombre, hash_password(n_pass), n_dir, n_lider])
                                                archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                
                                                st.success(f"✅ ¡Usuario '{n_nombre}' ({n_user}) creado exitosamente! Ya puede iniciar sesión.")
                                                st.cache_data.clear()
                                                time.sleep(1.5)
                                                st.rerun()
                                            except Exception as e: st.error(f"❌ Error al crear el usuario. Detalles: {e}")
                                    else: st.warning("⚠️ Debes seleccionar un colaborador y al menos una Dirección Permitida para crear el usuario.")
                        
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
                                    
                                    c_dir_list = [d.strip() for d in c_dir.split(",")] if c_dir else []
                                    opciones_dir = ["TODAS", "COLABORADOR"] + dirs
                                    c_dir_list_valid = [d for d in c_dir_list if d in opciones_dir]
                                    
                                    c_lid_list = [l.strip() for l in c_lid.split(",")] if c_lid else ["TODOS"]
                                    lideres_para_admin = sorted(df_completo['Nombre'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
                                    opciones_lid = ["TODOS"] + lideres_para_admin
                                    c_lid_list_valid = [l for l in c_lid_list if l in opciones_lid]
                                    if not c_lid_list_valid: c_lid_list_valid = ["TODOS"]
                                    
                                    with st.form("editar_usuario_form"):
                                        st.markdown(f"#### Editando a: {usuario_a_editar.split(' - ')[1]}")
                                        e_pass = st.text_input("Contraseña (Dejar igual si no deseas cambiarla)", value=c_pass)
                                        e_dir_list = st.multiselect("🏢 Direcciones Permitidas", opciones_dir, default=c_dir_list_valid)
                                        e_lider_list = st.multiselect("👤 Líder Restringido (Filtro por jerarquía de equipo)", opciones_lid, default=c_lid_list_valid)
                                        
                                        col_b1, col_b2 = st.columns(2)
                                        btn_actualizar = col_b1.form_submit_button("💾 Actualizar Permisos", type="primary", use_container_width=True)
                                        btn_eliminar = col_b2.form_submit_button("🗑️ Eliminar Usuario", use_container_width=True)
                                        
                                        if btn_actualizar:
                                            if e_dir_list:
                                                e_dir_str = ", ".join(e_dir_list)
                                                e_lider_str = ", ".join(e_lider_list) if e_lider_list else "TODOS"
                                                
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
                                                        usuarios_col = pestana_users.col_values(1)
                                                        
                                                        try:
                                                            fila_usuario = usuarios_col.index(u_id_sel) + 1
                                                            
                                                            pestana_users.update(values=[[pass_to_save, e_dir_str, e_lider_str]], range_name=f"C{fila_usuario}:E{fila_usuario}")
                                                            
                                                            archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                            st.cache_data.clear()
                                                            st.success(f"✅ ¡Usuario actualizado exitosamente!")
                                                            time.sleep(1.5)
                                                            st.rerun()
                                                        except ValueError: st.error("❌ El usuario no fue encontrado en la hoja de Excel.")
                                                    except Exception as e: st.error(f"❌ Error de conexión: {e}")
                                            else: st.warning("⚠️ Debes seleccionar al menos una Dirección Permitida.")
                                                
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
