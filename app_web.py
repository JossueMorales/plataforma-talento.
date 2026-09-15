import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components
import re
import gspread
from google.oauth2.service_account import Credentials
import time

# ==========================================
# VARIABLE GLOBAL DE CICLO (CAMBIAR AQUÍ PARA 2027)
# ==========================================
PESTANA_PDI_ACTUAL = "PDI 2026"

# IMPORTACIONES DESDE EL ARCHIVO DE CONFIGURACIÓN
from config_ui import (
    OPCIONES_PYVIS, SCRIPT_ANILLOS, INYECCION_HTML_JS,
    crear_tarjeta_kpi, extraer_contexto, clean_text, clean_id,
    obtener_color_9box, acortar_nombre, acortar_puesto,
    get_readiness_val, get_dispersion_offset
)

# VARIABLE GLOBAL DE BASE DE DATOS
LINK_ARCHIVO = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit"
PASSWORD_POR_DEFECTO = "Ayvi2026" 

# ESTRUCTURA MAESTRA DE COLUMNAS PARA EL PDI
COLUMNAS_PDI = [
    "Nómina", "Nombre", "Puesto", "Dirección", "Líder", "Fecha Elaboración", "Departamento",
    "Rol Interés 1", "Motivo 1", "Rol Interés 2", "Motivo 2", "Rol Interés 3", "Motivo 3",
    "Objetivo PDI", "PDI", "Qué? / Acciones de Desarrollo", 
    "¿Para qué? / Competencia", "¿Quién? / Recursos", "¿Cómo sabremos que se logró? / Métricas", 
    "¿Cuándo? / Fechas", "% de Avance", "Estatus"
]

# ==========================================
# MOTOR DE ORDENAMIENTO JERÁRQUICO
# ==========================================
def ordenar_jerarquia_talento(df, col_puesto='Nombre de la Posición', col_nombre='Nombre'):
    if col_puesto not in df.columns:
        return df
    
    def asignar_peso(puesto):
        p = str(puesto).lower()
        if 'gerente' in p or 'director' in p: return 1
        if 'jefe' in p: return 2
        return 3
        
    df['_peso_jerarquia'] = df[col_puesto].apply(asignar_peso)
    
    cols_sort = ['_peso_jerarquia', col_puesto]
    if col_nombre in df.columns:
        cols_sort.append(col_nombre)
        
    df = df.sort_values(by=cols_sort)
    return df.drop(columns=['_peso_jerarquia'])


# ==========================================
# SISTEMA DE CACHÉ INTELIGENTE Y DESCARGA
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def obtener_timestamp_actualizacion(url_sheets):
    try:
        secretos = st.secrets["connections"]["gsheets"]
        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        cliente = gspread.authorize(credenciales)
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheets)
        doc_id = match.group(1) if match else url_sheets
        archivo = cliente.open_by_key(doc_id)
        return archivo.worksheet("Metadata").acell('A1').value
    except Exception: 
        return str(int(time.time() // 600))

@st.cache_data(show_spinner=False)
def cargar_datos_csv(url_sheets, nombre_pestana, _timestamp):
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

# ==========================================
# SISTEMA DE SEGURIDAD Y LOGIN DINÁMICO
# ==========================================
def login():
    st.set_page_config(page_title="Portal de Talento Ayvi", layout="wide")
    
    if "usuario_logueado" not in st.session_state: 
        st.session_state["usuario_logueado"] = False
        
    if not st.session_state["usuario_logueado"]:
        usuarios_autorizados = {
            "admin": {"nombre": "Administrador Global", "password": "admin", "direccion": "TODAS", "lider": "TODOS"}
        }
        
        current_timestamp = obtener_timestamp_actualizacion(LINK_ARCHIVO)
        df_usuarios = cargar_datos_csv(LINK_ARCHIVO, "Usuarios", current_timestamp)
        
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
                if usuario in usuarios_autorizados and usuarios_autorizados[usuario]["password"] == password:
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
        return False
    return True

# ==========================================
# MOTOR PRINCIPAL (GRAFO CON CACHÉ Y LAZY LOADING)
# ==========================================
@st.cache_data(show_spinner=False)
def generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_mla, f_box, f_edr, f_riesgos, renderizar_mapa, usuario_activo_id):
    G = nx.MultiDiGraph()
    G_jerarquia = nx.DiGraph() 
    jefes_dict = {}
    empleados_validos = set()
    info_nodos = {}
    
    nombres_dict = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records') if clean_id(row.get('id Empleado'))}
    nombre_a_id = {nombre.strip().lower(): emp_id for emp_id, nombre in nombres_dict.items()}
    puesto_a_id = {clean_text(r.get('Nombre de la Posición')).lower(): clean_id(r.get('id Empleado')) for r in df_seguro.to_dict('records') if clean_id(r.get('id Empleado')) and clean_text(r.get('Nombre de la Posición'))}

    def buscar_id_real(valor):
        v = str(valor).strip()
        if pd.isna(valor) or v.lower() in ['nan', 'none', 'pendiente', '']: return ''
        if v.endswith('.0'): v = v[:-2]
        if v in nombres_dict: return v  
        v_lower = v.lower()
        if v_lower in nombre_a_id: return nombre_a_id[v_lower] 
        if v_lower in puesto_a_id: return puesto_a_id[v_lower]
        return v 
            
    for row_dict in df_seguro.to_dict('records'):
        emp = clean_id(row_dict.get('id Empleado'))
        jefe = clean_id(row_dict.get('ID Del Jefe'))
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try: eng_val = float(row_dict[enganche_key])
            except ValueError: eng_val = 0.0
        else: eng_val = 0.0
        
        if emp:
            empleados_validos.add(emp)
            G_jerarquia.add_node(emp)
            
            suc1_limpio = buscar_id_real(row_dict.get('Sucesor P.1', row_dict.get('Sucesor 1', '')))
            suc2_limpio = buscar_id_real(row_dict.get('Sucesor P.2', row_dict.get('Sucesor 2', '')))
            suc3_limpio = buscar_id_real(row_dict.get('Sucesor P.3', row_dict.get('Sucesor 3', '')))
            suc4_limpio = buscar_id_real(row_dict.get('Sucesor P.4', row_dict.get('Sucesor 4', '')))
            suc5_limpio = buscar_id_real(row_dict.get('Sucesor P.5', row_dict.get('Sucesor 5', '')))
            
            info_nodos[emp] = {
                'mla': clean_text(row_dict.get('Nivel MLA'), 'N/A'),
                'puesto': clean_text(row_dict.get('Nombre de la Posición')).upper(),
                'direccion': clean_text(row_dict.get('Dirección', row_dict.get('Direccion')), 'No asignada'),
                'box': clean_text(row_dict.get('Resultado 9 box'), 'Pendiente'),
                'edr': clean_text(row_dict.get('EDR', row_dict.get('EDR ')), 'Pendiente'),
                'lider': nombres_dict.get(jefe, 'Sin Líder') if jefe else 'Sin Líder',
                'critica': clean_text(row_dict.get('Posición Crítica', row_dict.get('Posicion Critica')), 'No'),
                'nombre': clean_text(row_dict.get('Nombre')),
                'interes': clean_text(row_dict.get('Interés del Colaborador'), 'Pendiente'),
                'suc1_id': suc1_limpio, 'read1': clean_text(row_dict.get('Tiempo de Readiness 1'), 'Pendiente'),
                'suc2_id': suc2_limpio, 'read2': clean_text(row_dict.get('Tiempo de Readiness 2'), ''),
                'suc3_id': suc3_limpio, 'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'suc4_id': suc4_limpio, 'read4': clean_text(row_dict.get('Tiempo de Readiness 4'), ''),
                'suc5_id': suc5_limpio, 'read5': clean_text(row_dict.get('Tiempo de Readiness 5'), ''),
                'enganche_ind': eng_val, 'enganche_area': 0.0, 'es_lider': False
            }
            if jefe:
                jefes_dict[emp] = jefe
                G_jerarquia.add_edge(jefe, emp)
                
    def obtener_jefe_nivel_arriba(emp_id, niveles):
        actual = emp_id
        for _ in range(niveles):
            if actual not in jefes_dict: return None
            actual = jefes_dict[actual]
        return actual
        
    reportes_directos = {n: 0 for n in G_jerarquia.nodes()}
    for jefe, emp in G_jerarquia.edges(): 
        reportes_directos[jefe] += 1
        if jefe in info_nodos: info_nodos[jefe]['es_lider'] = True
            
    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
        suma = 0.0; count = 0
        for d in descendientes:
            if d in info_nodos and info_nodos[d]['enganche_ind'] > 0:
                suma += info_nodos[d]['enganche_ind']
                count += 1
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos: info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)
        
    sucesores_de_9box = {n: 0 for n in G_jerarquia.nodes()}
    sucesores_oficiales_de = {n: 0 for n in G_jerarquia.nodes()} 
    for emp, info in info_nodos.items():
        box = info['box'].upper()
        if box in ['5', '2']: 
            j1 = obtener_jefe_nivel_arriba(emp, 1)
            if j1: sucesores_de_9box[j1] += 1
        if box in ['1', '3']:
            j2 = obtener_jefe_nivel_arriba(emp, 2)
            if j2: sucesores_de_9box[j2] += 1
        for s_id in [info['suc1_id'], info['suc2_id'], info['suc3_id'], info['suc4_id'], info['suc5_id']]:
            if s_id in sucesores_oficiales_de: sucesores_oficiales_de[s_id] += 1
                
    nombres_con_pdi = set(df_pdi['Nombre'].dropna().astype(str).str.strip().str.lower()) if not df_pdi.empty and 'Nombre' in df_pdi.columns else set()
        
    for emp, info in info_nodos.items():
        r_list = []
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
            if es_critica:
                if not tiene_oficial and not tiene_hipos_9box: r_list.append("🔥 Riesgo Crítico: Sin Sucesor ni HiPos")
                elif not tiene_oficial and tiene_hipos_9box: r_list.append("⚠️ Sugerencia: HiPo disponible, falta oficializar")
                    
            reps = reportes_directos.get(emp, 0)
            if reps >= 12: r_list.append(f"⚠️ Sobrecarga ({reps} reportes)")
            elif reps == 1: r_list.append("⚠️ Ineficiencia (1 reporte)")
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0: r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0: r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0: r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0: r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
            edr_txt = info['edr'].lower()
            if '1.resultado inaceptable' in edr_txt or 'inaceptable' in edr_txt: r_list.append("🚨 EDR Crítico: Resultado Inaceptable")
            elif '2.resultado necesita mejorar' in edr_txt or 'necesita mejorar' in edr_txt: r_list.append("⚠️ EDR Bajo: Necesita Mejorar")
            if info['nombre'].strip().lower() not in nombres_con_pdi: r_list.append("⚠️ Sin PDI: No tiene Plan de Desarrollo Individual")
                
        info_nodos[emp]['riesgos_lista'] = r_list
        info_nodos[emp]['riesgos'] = " | ".join(r_list) if r_list else "Ninguno"
        
    descendientes_validos = set()
    if f_lid != "Todos":
        lider_ids = [emp for emp, inf in info_nodos.items() if inf['nombre'] == f_lid]
        for l_id in lider_ids:
            descendientes_validos.add(l_id)
            try:
                if l_id in G_jerarquia: descendientes_validos.update(nx.descendants(G_jerarquia, l_id))
            except nx.NetworkXError: pass
                
    nodos_visibles = set()
    for emp, info in info_nodos.items():
        if info['mla'] == '5': nodos_visibles.add(emp); continue
        if f_lid != "Todos" and info['nombre'] == f_lid: nodos_visibles.add(emp); continue
        if f_dir != "Todas" and info['direccion'] != f_dir: continue
        if f_lid != "Todos" and emp not in descendientes_validos: continue
        if f_crit != "Todas" and info['critica'] != f_crit: continue
        if f_mla != "Todos" and info['mla'] != f_mla: continue
        if f_box != "Todos" and info['box'] != f_box: continue
        if f_edr != "Todos" and info['edr'] != f_edr: continue
        if f_riesgos and not info['riesgos_lista']: continue
        nodos_visibles.add(emp)
        
    nodos_rescatados = set(nodos_visibles)
    for emp in nodos_visibles:
        for s_id in [info_nodos[emp]['suc1_id'], info_nodos[emp]['suc2_id'], info_nodos[emp]['suc3_id'], info_nodos[emp]['suc4_id'], info_nodos[emp]['suc5_id']]:
            if s_id and s_id in info_nodos: nodos_rescatados.add(s_id)
    nodos_visibles = nodos_rescatados
    
    raiz_principal = next((emp for emp, info in info_nodos.items() if info['mla'] == '5'), None)
    if not raiz_principal:
        posibles_raices = [n for n in G_jerarquia.nodes() if G_jerarquia.in_degree(n) == 0]
        if posibles_raices: raiz_principal = max(posibles_raices, key=lambda x: len(nx.descendants(G_jerarquia, x)))
            
    # --- AUTO-ENFOQUE PYVIS DE USUARIO ---
    nodo_central_id = raiz_principal
    target_node_id = clean_id(usuario_activo_id)
    if target_node_id in G_jerarquia.nodes():
        nodo_central_id = target_node_id
        
    nodos_activos = set(nodos_visibles)
    if raiz_principal and raiz_principal in G_jerarquia:
        for v in nodos_visibles:
            if v in G_jerarquia:
                try: nodos_activos.update(nx.ancestors(G_jerarquia, v))
                except nx.NetworkXError: pass
                    
    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia
    
    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = str(info_nodos.get(emp_id, {}).get('mla', '')).replace('.0', '').strip() 
        return {'5':0, '4':1, '3':2, '2':3, '1':4}.get(mla, min(depth_arbol, 5))
        
    SEPARACION_ANILLOS = 348 
    conteo_hojas = {}
    
    def calcular_hojas(n):
        hijos = [c for c in Arbol.successors(n) if c in nodos_activos]
        if not hijos:
            val = 1 if n in nodos_visibles else 0
            conteo_hojas[n] = val
            return val
        total = sum(calcular_hojas(c) for c in hijos)
        if total == 0 and n in nodos_visibles: total = 1
        conteo_hojas[n] = total
        return total
        
    if raiz_principal: calcular_hojas(raiz_principal)
        
    coords = {}
    def asignar_coordenada_radial(nodo, angulo_inicio, angulo_fin, nivel_padre=0):
        hijos = [c for c in Arbol.successors(nodo) if c in nodos_activos]
        if not hijos: return
        hojas_totales = sum(conteo_hojas.get(c, 0) for c in hijos)
        if hojas_totales == 0: return
            
        angulo_actual = angulo_inicio
        for c in hijos:
            peso = conteo_hojas.get(c, 0)
            if peso == 0: continue
            rebanada = (peso / hojas_totales) * (angulo_fin - angulo_inicio)
            angulo_hijo = angulo_actual + (rebanada / 2)
            profundidad = nx.shortest_path_length(Arbol, raiz_principal, c) if raiz_principal and c in Arbol else 5
            anillo_real = obtener_anillo_estricto(c, profundidad)
            nivel_calculado = max(float(anillo_real), float(nivel_padre) + 0.6)
            dispersion = get_dispersion_offset(c) if nivel_calculado != 0 else 0
            radio_final = (nivel_calculado + dispersion) * SEPARACION_ANILLOS if nivel_calculado != 0 else 0
            coords[c] = {'x': radio_final * math.cos(angulo_hijo), 'y': radio_final * math.sin(angulo_hijo), 'angle': angulo_hijo, 'anillo_real': anillo_real, 'nivel_calculado': nivel_calculado, 'dispersion': dispersion, 'profundidad': profundidad}
            asignar_coordenada_radial(c, angulo_actual, angulo_actual + rebanada, nivel_calculado)
            angulo_actual += rebanada
            
    if raiz_principal:
        coords[raiz_principal] = {'x': 0, 'y': 0, 'angle': 0, 'anillo_real': 0, 'nivel_calculado': 0, 'dispersion': 0, 'profundidad': 0}
        asignar_coordenada_radial(raiz_principal, 0, 2 * math.pi, 0)
        
    nodos_sin_coords = [n for n in G_jerarquia.nodes() if n not in coords and n in nodos_visibles]
    if nodos_sin_coords:
        angulo_extra = (2 * math.pi) / len(nodos_sin_coords)
        angulo_actual = 0
        for n in nodos_sin_coords:
            anillo = obtener_anillo_estricto(n, 5)
            nivel_calculado = float(anillo) if anillo != 0 else 1.0
            dispersion = get_dispersion_offset(n)
            radio = (nivel_calculado + dispersion) * SEPARACION_ANILLOS if nivel_calculado != 0 else 80
            coords[n] = {'x': radio * math.cos(angulo_actual), 'y': radio * math.sin(angulo_actual), 'angle': angulo_actual, 'anillo_real': anillo, 'nivel_calculado': nivel_calculado, 'dispersion': dispersion, 'profundidad': 5}
            angulo_actual += angulo_extra
            
    alertas_tabla, data_total, data_sucesores, data_nueve_box, data_enganche, data_edr, data_operativos = [], [], [], [], [], [], []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            es_andres = info['mla'] == '5' or 'ANDRES EDUARDO VILLARREAL' in info['nombre'].upper()
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if not es_andres:
                data_edr.append({"Nombre": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Resultado EDR": info['edr']})
                if info['critica'].lower() == 'si':
                    data_sucesores.append({
                        "Ocupante Actual": info['nombre'], 
                        "Posición Crítica": info['puesto'], 
                        "Dirección": info['direccion'], 
                        "Sucesor 1": nom_suc1 if nom_suc1 else "Pendiente", 
                        "Readiness 1": info['read1'] if info['read1'] else "Pendiente",
                        "Sucesor 2": nom_suc2 if nom_suc2 else "Pendiente", 
                        "Readiness 2": info['read2'] if info['read2'] else "Pendiente",
                        "Sucesor 3": nom_suc3 if nom_suc3 else "Pendiente", 
                        "Readiness 3": info['read3'] if info['read3'] else "Pendiente"
                    })
                if info['es_lider']: data_enganche.append({"Líder": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A", "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"})
                for r in info['riesgos_lista']: alertas_tabla.append({"Colaborador": info['nombre'], "Líder Directo": info['lider'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Alerta Detectada por IA": r})
            
            if info['box'].lower() not in ['pendiente', 'n/a', 'nan', 'none', '']: data_nueve_box.append({"Nombre": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Resultado 9-Box": info['box']})
            if info['mla'] == '1': data_operativos.append(nodo_data)
                
        prefijo = "🚨 " if info['riesgos_lista'] else ""
        coord_data = coords.get(emp, {'angle':0, 'nivel_calculado':5, 'profundidad':5, 'anillo_real': 5})
        
        eng = info['enganche_ind']
        color_sombreado = 'rgba(22, 163, 74, 0.8)' if eng >= 4 else ('rgba(234, 179, 8, 0.8)' if eng >= 3 else ('rgba(249, 115, 22, 0.8)' if eng >= 2 else ('rgba(220, 38, 38, 0.8)' if eng > 0 else 'rgba(0, 0, 0, 0.2)')))
        dispersion_offset = (((sum(ord(ch) for ch in str(emp)) % 9) / 8.0) * 0.4) - 0.2 
        
        G.add_node(
            emp, label=f"{prefijo}{acortar_nombre(info['nombre'])}\n({acortar_puesto(info['puesto'])})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, color=obtener_color_9box(info['box']), shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, 
            shape='dot', group=info['mla'], Nivel_MLA=info['mla'], Resultado_9Box=info['box'], EDR=info['edr'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'], Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'}, Angle=coord_data['angle'], NivelCalculado=coord_data.get('nivel_calculado', 5), Dispersion=dispersion_offset, AnilloReal=coord_data.get('anillo_real', 5), hidden=is_hidden
        )
        
    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        eng_emp = info_nodos[emp]['enganche_ind']
        color_edge_shadow = 'rgba(22, 163, 74, 0.8)' if eng_emp >= 4 else ('rgba(234, 179, 8, 0.8)' if eng_emp >= 3 else ('rgba(249, 115, 22, 0.8)' if eng_emp >= 2 else ('rgba(220, 38, 38, 0.8)' if eng_emp > 0 else 'rgba(0, 0, 0, 0.0)')))
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False, shadow={'enabled': True, 'color': color_edge_shadow, 'size': 15, 'x': 0, 'y': 0})
        
    for emp, info in info_nodos.items():
        box = info['box'].upper()
        if box in ['5', '2']:
            j1 = obtener_jefe_nivel_arriba(emp, 1)
            if j1: G.add_edge(emp, j1, color='#22c55e', width=3, dashes=[5,5], title='Proyección N+1', hidden=(emp not in nodos_visibles or j1 not in nodos_visibles), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.2})
        if box in ['1', '3']:
            j2 = obtener_jefe_nivel_arriba(emp, 2)
            if j2: G.add_edge(emp, j2, color='#166534', width=3.5, dashes=[5,5], title='Proyección N+2', hidden=(emp not in nodos_visibles or j2 not in nodos_visibles), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.3})
            
        for s_id, read_time in [(info['suc1_id'], info['read1']), (info['suc2_id'], info['read2']), (info['suc3_id'], info['read3']), (info['suc4_id'], info['read4']), (info['suc5_id'], info['read5'])]:
            if s_id and s_id in empleados_validos:
                is_hidden_edge = (emp not in nodos_visibles or s_id not in nodos_visibles)
                val = get_readiness_val(read_time)
                dashes_style = False if val == 1 else ([10, 10] if val == 2 else [4, 8])
                edge_width = 6 if val == 1 else (4 if val == 2 else 2)
                G.add_edge(emp, s_id, color='#9c27b0', width=edge_width, dashes=dashes_style, title=f'🎯 Sucesor: {read_time}', hidden=is_hidden_edge, is_struct=False, is_9box=False, is_succ=True, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.6})
                
    eng_list = [info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0 and 'ANDRES EDUARDO VILLARREAL' not in info_nodos[n]['nombre'].upper()]
    avg_enganche = round(sum(eng_list) / len(eng_list), 1) if eng_list else 0.0
    
    kpis = {
        'total': len(data_total), 'sucesores': len(data_sucesores), 'nueve_box_count': len(data_nueve_box),
        'alertas': len(alertas_tabla), 'enganche_promedio': avg_enganche, 'edr_count': len(data_edr), 'operativos': len(data_operativos),
        'data_total': data_total, 'data_sucesores': data_sucesores, 'data_nueve_box': data_nueve_box, 'data_operativos': data_operativos,
        'data_alertas': [{"Nombre": a['Colaborador'], "Dirección": a['Dirección'], "Puesto": a['Puesto'], "Alerta": a['Alerta Detectada por IA']} for a in alertas_tabla],
        'data_enganche': data_enganche, 'data_edr': data_edr,
        'nodos_visibles_ids': list(nodos_visibles)
    }
    
    if not renderizar_mapa:
        html_placeholder = """
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 550px; background-color: #f8f9fa; border-radius: 12px; border: 3px dashed #cbd5e1; font-family: Arial, sans-serif;">
            <div style="font-size: 50px; margin-bottom: 15px;">⚡</div>
            <h2 style="color: #3b82f6; margin: 0 0 10px 0;">Modo Rápido Activado</h2>
            <p style="color: #64748b; font-size: 15px; text-align: center; max-width: 450px;">El cálculo de los <b>KPIs</b> se ha realizado instantáneamente con éxito.<br><br>Para evitar sobrecargar tu navegador, selecciona una <b>Dirección</b> o un <b>Líder</b> en los filtros de arriba para generar el grafo visual.</p>
        </div>
        """
        return html_placeholder, pd.DataFrame(alertas_tabla), kpis
    
    net = Network(height='550px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    html = net.generate_html().replace('</body>', INYECCION_HTML_JS + '\n' + SCRIPT_ANILLOS + f'\n<script>\nwindow.targetNodeId = "{nodo_central_id}";\n</script>\n</body>')
    
    return html, pd.DataFrame(alertas_tabla), kpis

# ==========================================
# FUNCIONES ENCAPSULADAS DE AUTOGESTIÓN (MI PDI - 70/20/10)
# ==========================================
def renderizar_mi_pdi(df_completo, df_pdi):
    st.markdown(f"### 📝 Plan de Desarrollo Individual (PDI)")
    st.info("Estructura tu aprendizaje equilibrando experiencias prácticas (70%), interacciones sociales (20%) y formación formal (10%).")
    
    nombre_colab = st.session_state["nombre_usuario"]
    datos_bd = df_completo[df_completo['Nombre_Cruce'] == nombre_colab.strip().lower()]
    
    if not datos_bd.empty:
        row_bd = datos_bd.iloc[0]
        nomina_aut = clean_id(row_bd.get('id Empleado', ''))
        puesto_aut = clean_text(row_bd.get('Nombre de la Posición', ''))
        dir_aut = clean_text(row_bd.get('Dirección', row_bd.get('Direccion', '')))
        jefe_id = clean_id(row_bd.get('ID Del Jefe', ''))
        dict_nom_global = {clean_id(r.get('id Empleado')): clean_text(r.get('Nombre')) for r in df_completo.to_dict('records')}
        lider_aut = dict_nom_global.get(jefe_id, 'No asignado')
    else:
        nomina_aut, puesto_aut, dir_aut, lider_aut = "N/A", "N/A", "N/A", "N/A"
        st.warning("⚠️ No pudimos encontrar tus datos exactos en la base principal. Habla con RH.")

    datos_pdi_usuario = pd.DataFrame()
    if not df_pdi.empty and 'Nombre' in df_pdi.columns:
        df_pdi['Nombre_Cruce'] = df_pdi['Nombre'].astype(str).str.strip().str.lower()
        datos_pdi_usuario = df_pdi[df_pdi['Nombre_Cruce'] == nombre_colab.strip().lower()]
        
    fecha_elab, depto = "", ""
    rol_1, mot_1, rol_2, mot_2, rol_3, mot_3 = "", "", "", "", "", ""
    objetivo = ""
    
    acciones_70, acciones_20, acciones_10 = [], [], []

    if not datos_pdi_usuario.empty:
        primer_row = datos_pdi_usuario.iloc[0]
        
        def fc(keyword):
            return next((c for c in datos_pdi_usuario.columns if clean_text(keyword).lower() in clean_text(str(c)).lower()), None)
            
        col_fecha = fc('fecha elab') or 'Fecha Elaboración'
        col_depto = fc('departamento') or 'Departamento'
        col_rol1 = fc('rol interés 1') or fc('roles / áreas de interés 1') or 'Rol Interés 1'
        col_mot1 = fc('motivo 1') or 'Motivo 1'
        col_rol2 = fc('rol interés 2') or fc('roles / áreas de interés 2') or 'Rol Interés 2'
        col_mot2 = fc('motivo 2') or 'Motivo 2'
        col_rol3 = fc('rol interés 3') or fc('roles / áreas de interés 3') or 'Rol Interés 3'
        col_mot3 = fc('motivo 3') or 'Motivo 3'
        col_obj = fc('objetivo') or 'Objetivo PDI'
        
        fecha_elab = str(primer_row.get(col_fecha, ''))
        depto = str(primer_row.get(col_depto, ''))
        rol_1 = str(primer_row.get(col_rol1, ''))
        mot_1 = str(primer_row.get(col_mot1, ''))
        rol_2 = str(primer_row.get(col_rol2, ''))
        mot_2 = str(primer_row.get(col_mot2, ''))
        rol_3 = str(primer_row.get(col_rol3, ''))
        mot_3 = str(primer_row.get(col_mot3, ''))
        objetivo = str(primer_row.get(col_obj, ''))
        
        col_cat = fc('pdi') or fc('clasificacion') or fc('categoría') or 'PDI'
        col_acc = fc('qué') or fc('acción') or 'Qué? / Acciones de Desarrollo'
        col_comp = fc('para qué') or fc('competencia') or '¿Para qué? / Competencia'
        col_rec = fc('quién') or fc('recursos') or '¿Quién? / Recursos'
        col_met = fc('cómo') or fc('métricas') or '¿Cómo sabremos que se logró? / Métricas'
        col_fec = fc('cuándo') or fc('cumplimiento') or '¿Cuándo? / Fechas'
        col_av = fc('avance') or '% de Avance'
        col_est = fc('estatus') or 'Estatus'
        
        for _, row in datos_pdi_usuario.iterrows():
            cat = str(row.get(col_cat, ''))
            acc_data = {
                "acc": str(row.get(col_acc, '')), "comp": str(row.get(col_comp, '')),
                "rec": str(row.get(col_rec, '')), "met": str(row.get(col_met, '')),
                "fec": str(row.get(col_fec, '')), "av": str(row.get(col_av, '0%')),
                "est": str(row.get(col_est, 'No Iniciado'))
            }
            if '70' in cat and acc_data["acc"]: acciones_70.append(acc_data)
            elif '20' in cat and acc_data["acc"]: acciones_20.append(acc_data)
            elif '10' in cat and acc_data["acc"]: acciones_10.append(acc_data)

    molde_vacio = {"acc": "", "comp": "", "rec": "", "met": "", "fec": "", "av": "0%", "est": "No Iniciado"}
    while len(acciones_70) < 3: acciones_70.append(molde_vacio.copy())
    while len(acciones_20) < 3: acciones_20.append(molde_vacio.copy())
    while len(acciones_10) < 3: acciones_10.append(molde_vacio.copy())

    with st.container():
        st.markdown("<div style='background-color:#1e40af; padding:8px; color:white; font-weight:bold; text-align:center; border-radius:4px;'>Información General</div>", unsafe_allow_html=True)
        st.write("")
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Nombre del colaborador:", value=nombre_colab, disabled=True)
        c2.text_input("Número de nómina:", value=nomina_aut, disabled=True)
        c3.text_input("Puesto actual:", value=puesto_aut, disabled=True)
        depto_input = c4.text_input("Departamento:", value=depto, placeholder="Escribe tu depto...")
        
        c5, c6, c7, c8 = st.columns(4)
        c5.text_input("Dirección Organizacional:", value=dir_aut, disabled=True)
        c6.text_input("Líder Directo:", value=lider_aut, disabled=True)
        fecha_input = c7.text_input("Fecha de elaboración:", value=fecha_elab, placeholder="Ej. 9/9/2026")
        
    st.write("")
    
    with st.form("form_edicion_pdi", clear_on_submit=False):
        st.markdown("<div style='background-color:#fef08a; padding:6px; color:#854d0e; font-weight:bold; text-align:center; border-radius:4px;'>Expectativas de Desarrollo (Colaborador)</div>", unsafe_allow_html=True)
        st.write("")
        
        # --- APLICACIÓN EN LA LISTA DESPLEGABLE DE ROLES ---
        roles_disponibles = [""] + df_completo['Nombre de la Posición'].dropna().astype(str).drop_duplicates().tolist()
        
        def index_seguro(lista, valor): return lista.index(valor) if valor in lista else 0
            
        r1, m1 = st.columns([1, 2])
        rol_int_1 = r1.selectbox("Rol / Área de Interés 1", roles_disponibles, index=index_seguro(roles_disponibles, rol_1))
        mot_int_1 = m1.text_input("Motivo 1", value=mot_1, key="mot1", placeholder="¿Por qué te interesa este rol?")
        
        r2, m2 = st.columns([1, 2])
        rol_int_2 = r2.selectbox("Rol / Área de Interés 2", roles_disponibles, index=index_seguro(roles_disponibles, rol_2))
        mot_int_2 = m2.text_input("Motivo 2", value=mot_2, key="mot2")
        
        r3, m3 = st.columns([1, 2])
        rol_int_3 = r3.selectbox("Rol / Área de Interés 3", roles_disponibles, index=index_seguro(roles_disponibles, rol_3))
        mot_int_3 = m3.text_input("Motivo 3", value=mot_3, key="mot3")
        
        st.write("")
        st.markdown("<div style='background-color:#fef08a; padding:6px; color:#854d0e; font-weight:bold; text-align:center; border-radius:4px;'>Objetivo de Desarrollo (Colaborador y Líder)</div>", unsafe_allow_html=True)
        st.write("")
        
        opciones_obj = ["Definir objetivo (Pendiente de catálogo MLA)...", "Desarrollo de Competencias Técnicas", "Desarrollo de Liderazgo", "Preparación para Siguiente Nivel", "Gestión de Proyectos", "Otro"]
        if objetivo and objetivo not in opciones_obj: opciones_obj.append(objetivo)
        obj_desarrollo = st.selectbox("Objetivo a Desarrollar:", opciones_obj, index=index_seguro(opciones_obj, objetivo))
        
        st.write("")
        st.markdown("<div style='background-color:#1e40af; padding:8px; color:white; font-weight:bold; text-align:center; border-radius:4px;'>Plan de Desarrollo (Modelo 70-20-10)</div>", unsafe_allow_html=True)
        st.write("")
        
        opciones_avance = ["0%", "25%", "50%", "75%", "100%"]
        opciones_estatus = ["No Iniciado", "En proceso", "Completado", "Cancelado"]

        def render_categoria(titulo, prefijo, lista_acciones):
            st.markdown(f"**{titulo}**")
            nuevas = []
            for i in range(3):
                a1, a2, a3, a4, a5, a6, a7 = st.columns([2, 1.5, 1.5, 1.5, 1, 1, 1])
                acc = a1.text_area("Qué? / Acciones" if i==0 else "", value=lista_acciones[i]['acc'], key=f"{prefijo}_acc_{i}", height=68, label_visibility="visible" if i==0 else "collapsed")
                comp = a2.text_input("Para qué? / Competencia" if i==0 else "", value=lista_acciones[i]['comp'], key=f"{prefijo}_comp_{i}", label_visibility="visible" if i==0 else "collapsed")
                rec = a3.text_input("Quién? / Recursos" if i==0 else "", value=lista_acciones[i]['rec'], key=f"{prefijo}_rec_{i}", label_visibility="visible" if i==0 else "collapsed")
                met = a4.text_input("Métricas" if i==0 else "", value=lista_acciones[i]['met'], key=f"{prefijo}_met_{i}", label_visibility="visible" if i==0 else "collapsed")
                fec = a5.text_input("Fecha Ejecución" if i==0 else "", value=lista_acciones[i]['fec'], key=f"{prefijo}_fec_{i}", label_visibility="visible" if i==0 else "collapsed")
                av = a6.selectbox("% Avance" if i==0 else "", opciones_avance, index=index_seguro(opciones_avance, lista_acciones[i]['av']), key=f"{prefijo}_av_{i}", label_visibility="visible" if i==0 else "collapsed")
                est = a7.selectbox("Estatus" if i==0 else "", opciones_estatus, index=index_seguro(opciones_estatus, lista_acciones[i]['est']), key=f"{prefijo}_est_{i}", label_visibility="visible" if i==0 else "collapsed")
                
                nuevas.append({
                    "PDI": titulo, 
                    "Qué? / Acciones de Desarrollo": acc, 
                    "¿Para qué? / Competencia": comp,
                    "¿Quién? / Recursos": rec, 
                    "¿Cómo sabremos que se logró? / Métricas": met, 
                    "¿Cuándo? / Fechas": fec, 
                    "% de Avance": av, 
                    "Estatus": est
                })
            st.divider()
            return nuevas

        with st.expander("🔵 70% Desarrollo en el trabajo (Aprendizaje basado en experiencia directa)", expanded=True):
            acciones_70_nuevas = render_categoria("70% Desarrollo en el trabajo", "70", acciones_70)
            
        with st.expander("🟡 20% Mentoring (Feedback, coaching, trabajo colaborativo)", expanded=True):
            acciones_20_nuevas = render_categoria("20% Mentoring", "20", acciones_20)
            
        with st.expander("🔴 10% Formación Formal (Cursos, talleres, certificaciones)", expanded=True):
            acciones_10_nuevas = render_categoria("10% Formación Formal", "10", acciones_10)
            
        btn_guardar_pdi = st.form_submit_button("💾 Guardar y Compartir mi PDI con mi Líder", use_container_width=True)
        
        if btn_guardar_pdi:
            with st.spinner("☁️ Sincronizando con Base de Datos (Múltiples Filas)..."):
                try:
                    secretos = st.secrets["connections"]["gsheets"]
                    credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                    cliente = gspread.authorize(credenciales)
                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                    doc_id = match.group(1) if match else LINK_ARCHIVO
                    archivo = cliente.open_by_key(doc_id)
                    pestana_pdi_gs = archivo.worksheet(PESTANA_PDI_ACTUAL)
                    
                    if df_pdi.empty: df_actual = pd.DataFrame(columns=COLUMNAS_PDI)
                    else:
                        df_actual = df_pdi.copy()
                        for c in COLUMNAS_PDI:
                            if c not in df_actual.columns: df_actual[c] = ""
                            
                    if not df_actual.empty and 'Nombre' in df_actual.columns:
                        df_actual['Nombre_Cruce'] = df_actual['Nombre'].astype(str).str.strip().str.lower()
                        df_resto = df_actual[df_actual['Nombre_Cruce'] != nombre_colab.strip().lower()].copy()
                        if 'Nombre_Cruce' in df_resto.columns: df_resto = df_resto.drop(columns=['Nombre_Cruce'])
                    else:
                        df_resto = pd.DataFrame(columns=COLUMNAS_PDI)
                        
                    todas_las_acciones = acciones_70_nuevas + acciones_20_nuevas + acciones_10_nuevas
                    nuevas_filas = []
                    
                    base_fila = {
                        "Nómina": nomina_aut, "Nombre": nombre_colab, "Puesto": puesto_aut,
                        "Dirección": dir_aut, "Líder": lider_aut, "Fecha Elaboración": fecha_input,
                        "Departamento": depto_input, "Rol Interés 1": rol_int_1, "Motivo 1": mot_int_1,
                        "Rol Interés 2": rol_int_2, "Motivo 2": mot_int_2, "Rol Interés 3": rol_int_3,
                        "Motivo 3": mot_int_3, "Objetivo PDI": obj_desarrollo
                    }
                    
                    for acc in todas_las_acciones:
                        if acc['Qué? / Acciones de Desarrollo'].strip() != "":
                            fila = base_fila.copy()
                            fila.update(acc)
                            nuevas_filas.append(fila)
                            
                    if not nuevas_filas:
                        fila = base_fila.copy()
                        fila.update({"PDI": "", "Qué? / Acciones de Desarrollo": "", "¿Para qué? / Competencia": "", "¿Quién? / Recursos": "", "¿Cómo sabremos que se logró? / Métricas": "", "¿Cuándo? / Fechas": "", "% de Avance": "", "Estatus": ""})
                        nuevas_filas.append(fila)
                        
                    df_nuevas = pd.DataFrame(nuevas_filas)
                    df_final = pd.concat([df_resto, df_nuevas], ignore_index=True)[COLUMNAS_PDI]
                    
                    datos_a_escribir = [df_final.columns.values.tolist()] + df_final.fillna("").values.tolist()
                    pestana_pdi_gs.clear()
                    pestana_pdi_gs.update(values=datos_a_escribir, range_name="A1")
                    
                    archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                    st.cache_data.clear()
                    
                    st.balloons()
                    st.toast("¡Plan 70-20-10 guardado exitosamente!", icon="✅")
                    st.markdown("""
                        <div style='background-color: #22c55e; padding: 20px; border-radius: 8px; text-align: center; border: 2px solid #166534; margin-top: 15px; margin-bottom: 15px;'>
                            <h2 style='color: white; margin: 0;'>🎉 ¡Éxito! Tu PDI se guardó correctamente.</h2>
                            <p style='font-size: 16px; color: white; margin-top: 8px; margin-bottom: 0;'>
                                Tu base de datos multifila se ha sincronizado en la nube y ya es visible para tu líder.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    time.sleep(3.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en Google Sheets: {e}")

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
                                    pestana_users.update_cell(fila_usuario, 3, n_pass1)
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
        /* Carrusel de Columnas Horizontal Sucesores */
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
        current_timestamp = obtener_timestamp_actualizacion(LINK_ARCHIVO)
        
        df_completo_raw = cargar_datos_csv(LINK_ARCHIVO, "Base de datos", current_timestamp)
        df_pdi = cargar_datos_csv(LINK_ARCHIVO, PESTANA_PDI_ACTUAL, current_timestamp)
        
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

        # --- APLICACIÓN DE ORDENAMIENTO JERÁRQUICO SOLICITADO ---
        # Todo df_completo se reordena aquí, asegurando que df_seguro, df_filtros y exportaciones
        # hereden la prioridad de Gerentes -> Jefes -> Resto.
        df_completo = ordenar_jerarquia_talento(df_completo, 'Nombre de la Posición', 'Nombre')
            
        # --- LÓGICA DE PERMISOS MULTISELECCIONABLES ---
        direccion_permitida = str(st.session_state.get("direccion_permitida", "TODAS")).strip().upper()
        es_colaborador = ("COLABORADOR" in direccion_permitida)
        
        lider_permitido_str = str(st.session_state.get("lider_permitido", "TODOS")).strip()
        
        if es_colaborador:
            renderizar_mi_pdi(df_completo, df_pdi)
                                
        else:
            if "TODAS" not in direccion_permitida:
                lista_dirs = [d.strip() for d in direccion_permitida.split(",")]
                mask_dir = df_completo['Dirección'].astype(str).str.upper().apply(lambda d_val: any(d in d_val for d in lista_dirs))
                df_seguro = df_completo[mask_dir | (df_completo['Nivel MLA'].astype(str).str.strip() == '5')]
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
                    if str(nom).strip().lower() in lista_lideres_perm:
                        lideres_ids_global.append(idx)
                
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
                df_filtros = df_seguro[~df_seguro['Nivel MLA'].astype(str).str.strip().isin(['5'])]

            col_head1, col_head2 = st.columns([2, 1])
            with col_head1:
                st.markdown("### 🎛️ Filtros Globales")
                if st.button("🔄 Forzar Sincronización con Excel", help="Usa este botón si hiciste cambios manuales directamente en el archivo de Google Sheets"):
                    st.cache_data.clear(); st.rerun()
                
            with col_head2:
                nombres_s = df_filtros['Nombre'].dropna()
                # --- APLICACIÓN EN LA LISTA DESPLEGABLE DE BÚSQUEDA ---
                lista_nombres_buscador = nombres_s[nombres_s != ''].drop_duplicates().tolist()
                colab_buscado = st.selectbox("🔍 Búsqueda rápida de colaborador:", [""] + lista_nombres_buscador)
                
            if colab_buscado:
                datos_c = df_seguro[df_seguro['¡Hola, Jefe! Analizando la imagen "image_318f52.png", noto exactamente el detalle que menciona. En la sección del **Sucesor 1**, el dropdown del "Candidato 1" está preseleccionando o mostrando a "RUBÉN RAMÍREZ TAMEZ", quien es precisamente el ocupante actual de la posición crítica (Director de Administración y Finanzas). 

Esto está provocando que al desplegar las métricas en el `st.expander` (9-Box, Enganche, etc.), el sistema renderice los datos del líder sobre sí mismo, en lugar de un sucesor real.

### 🔍 Análisis del Problema y su Impacto
*   **Causa Raíz:** En la lógica de Streamlit (Pandas), la lista que alimenta el `st.selectbox` de los candidatos no está filtrando/excluyendo al ocupante actual de la posición que se está evaluando.
*   **Impacto Arquitectónico:** Es un problema puramente de interfaz y manipulación de datos en memoria (Frontend/Pandas). **No afecta nuestra regla de oro** porque no estamos tocando ni sobreescribiendo las columnas de la A a la G en Google Sheets. 
*   **Alineación con Reglas de Negocio:** Aprovecharemos la corrección para asegurar que el filtro de exclusión se haga mediante el **Número de Nómina (ID)** y no por nombre, evitando así errores por espacios o coincidencias, tal como dicta nuestra arquitectura.

---

### 🛠️ Solución Propuesta (Código)

Para corregir esto, debemos crear un *dataframe* filtrado justo antes de pintar las tarjetas de sucesores, excluyendo el ID del líder actual. Ubique el bloque de código donde construimos el `st.selectbox` de los sucesores y ajústelo de la siguiente manera:

```python
# Asumiendo que 'df_base' es tu DataFrame maestro cargado de Sheets
# y 'id_lider_actual' es la variable que guarda el ID de Nómina del Director que estamos evaluando.

# 1. Filtramos el DataFrame excluyendo el ID del líder actual para evitar que sea su propio sucesor
df_candidatos_validos = df_base[df_base['ID'] != id_lider_actual]

# 2. Excluimos también los IDs inventados de Vacantes para que no aparezcan como personas elegibles
df_candidatos_validos = df_candidatos_validos[~df_candidatos_validos['ID'].str.startswith('VAC-', na=False)]

# 3. Creamos el diccionario o lista para el selectbox
# Recordatorio: Operamos internamente con el ID, pero mostramos el Nombre al usuario
opciones_candidatos = df_candidatos_validos['Nombre'].tolist()

# 4. Renderizamos la UI del Sucesor (Ejemplo para Sucesor 1)
# Si Streamlit intenta recuperar un index anterior desde session_state, el filtro evitará que encuentre al líder.
sucesor_1 = st.selectbox(
    "Candidato 1", 
    options=["Seleccione un candidato..."] + opciones_candidatos,
    index=0
)

# Renderizado de métricas en el expander (oculto por defecto según la regla UI)
with st.expander("Mostrar Métricas del Candidato"):
    if sucesor_1 != "Seleccione un candidato...":
        # Extraer ID del candidato seleccionado para buscar sus métricas
        # Lógica para mostrar 9-Box, Enganche y EDR...
        pass
