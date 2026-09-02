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
        
        roles_disponibles = [""] + sorted(df_completo['Nombre de la Posición'].dropna().astype(str).unique().tolist())
        
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
                    st.success(f"✅ ¡{PESTANA_PDI_ACTUAL} Guardado Exitosamente! Tu base de datos multifila se actualizó.")
                    time.sleep(1.5)
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
                lista_nombres_buscador = sorted(nombres_s[nombres_s != ''].unique().tolist())
                colab_buscado = st.selectbox("🔍 Búsqueda rápida de colaborador:", [""] + lista_nombres_buscador)
                
            if colab_buscado:
                datos_c = df_seguro[df_seguro['Nombre'] == colab_buscado].iloc[0]
                st.success(f"👤 **{colab_buscado}** | 🏢 **Puesto:** {clean_text(datos_c.get('Nombre de la Posición', 'N/A'))} | 📍 **Dirección:** {clean_text(datos_c.get('Dirección', datos_c.get('Direccion', 'N/A')))} | 📊 **9-Box:** {clean_text(datos_c.get('Resultado 9 box', 'N/A'))} | 📈 **EDR:** {clean_text(datos_c.get('EDR', datos_c.get('EDR ', 'N/A')))} | 🥇 **Nivel MLA:** {clean_text(datos_c.get('Nivel MLA', 'N/A'))}")
            
            dirs = sorted(df_filtros['Dirección'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            mlas = sorted(df_filtros['Nivel MLA'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            boxes = sorted(df_filtros['Resultado 9 box'].dropna().astype(str).str.strip().str.upper()[lambda x: x != ''].unique().tolist())
            criticas = sorted(df_filtros['Posición Crítica'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
            edrs_col = 'EDR' if 'EDR' in df_filtros.columns else ('EDR ' if 'EDR ' in df_filtros.columns else None)
            edrs = sorted(df_filtros[edrs_col].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist()) if edrs_col else []
            
            col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
            f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
            
            if f_dir != "Todas": lideres_ids = df_filtros[df_filtros['Dirección'].astype(str).str.strip() == f_dir]['ID Del Jefe'].dropna().unique()
            else: lideres_ids = df_filtros['ID Del Jefe'].dropna().unique()
                
            lideres = sorted(list(set([dict_nom_global.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
            
            f_lid = col_f2.selectbox("Líder", ["Todos"] + lideres)
            f_crit = col_f3.selectbox("Pos. Crítica", ["Todas"] + criticas)
            f_mla = col_f4.selectbox("Nivel MLA", ["Todos"] + mlas)
            f_box = col_f5.selectbox("9-Box", ["Todos"] + boxes)
            f_edr = col_f6.selectbox("EDR (Resultados)", ["Todos"] + edrs)
            
            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                f_riesgos = st.checkbox("🚨 Mostrar Solo Colaboradores con Riesgos Detectados")
                
            renderizar_mapa = True
            if f_dir == "Todas" and f_lid == "Todos":
                renderizar_mapa = False
                
            with col_chk2:
                if not renderizar_mapa:
                    forzar_mapa = st.checkbox("⚠️ Dibujar el mapa visual de todos modos (Puede ser lento)", value=False)
                    if forzar_mapa:
                        renderizar_mapa = True
            st.write("") 
            
            html_mapa, df_alertas, kpis = generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_mla, f_box, f_edr, f_riesgos, renderizar_mapa, st.session_state["id_usuario"])
            
            if kpis is not None:
                if st.session_state["id_usuario"] == "admin":
                    tab_mapa, tab_sucesiones, tab_pdi_equipo, tab_mi_pdi, tab_admin = st.tabs([
                        "🗺️ Mapa Organizacional", "🔀 Sucesión", "📈 Seguimiento de PDI", "📝 Mi PDI", "⚙️ Panel de Administración"
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
                            titulos_kpi = {"total": "Total de Colaboradores", "sucesores": "Sucesión de Posiciones Críticas", "edr": "Evaluación de Desempeño y Resultados (EDR)", "nueve_box": "Evaluaciones 9-Box", "alertas": "Colaboradores con Riesgos / Alertas", "enganche": "Nivel de Enganche de Líderes"}
                            st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                            df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                            if not df_lista.empty:
                                if vista == "alertas": df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                                if "TODAS" not in direccion_permitida and "Dirección" in df_lista.columns: df_lista = df_lista.drop(columns=["Dirección"])
                                st.dataframe(df_lista, use_container_width=True, hide_index=True)
                            else: st.info("No hay registros en esta categoría.")
                            if st.button("❌ Cerrar Lista", use_container_width=True): st.session_state["vista_kpi"] = None; st.rerun()
                        else:
                            st.info("👆 Selecciona cualquier KPI superior para desplegar la información a detalle en esta área.")
                
                with tab_sucesiones:
                    st.markdown("### 🔀 Planificador de Sucesiones (Edición en Vivo)")
                    st.info("🔒 **Modo Presentación:** Selecciona a un líder aquí para limitar las posiciones críticas disponibles exclusivamente a su equipo. Útil para evitar fugas de información confidencial.")
                    
                    lideres_totales = sorted(list(set([dict_nom_global.get(clean_id(x), "Sin Líder") for x in df_seguro['ID Del Jefe'].dropna().unique() if clean_id(x)])))
                    f_lid_plan = st.selectbox("👤 Líder a revisar (Modo Privado):", ["Todos"] + lideres_totales, key="modo_pres_lider")
                    
                    def obtener_subordinados_ids(lider_nombre):
                        lider_id = next((i for i, n in dict_nom_global.items() if n == lider_nombre), None)
                        if not lider_id: return set()
                        subs = set(); cola = [lider_id]
                        while cola:
                            actual = cola.pop(0)
                            directos = jerarquia_global.get(actual, [])
                            for d in directos:
                                if d and d not in subs: subs.add(d); cola.append(d)
                        return subs
                    
                    df_posiciones_filtradas = df_seguro.copy()
                    df_posiciones_filtradas['id_clean'] = df_posiciones_filtradas['id Empleado'].apply(clean_id)
                    
                    subordinados_nombres_limpios = []
                    if f_lid_plan != "Todos":
                        sub_ids = obtener_subordinados_ids(f_lid_plan)
                        lider_id = next((i for i, n in dict_nom_global.items() if n == f_lid_plan), None)
                        if lider_id: sub_ids.add(lider_id)
                        df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['id_clean'].isin(sub_ids)]
                        
                        subordinados_nombres_limpios = [str(dict_nom_global.get(s)).strip().lower() for s in sub_ids if s in dict_nom_global and str(dict_nom_global.get(s)).strip() != '']
                    else:
                        nodos_visibles_ids = kpis.get('nodos_visibles_ids', [])
                        df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['id_clean'].isin(nodos_visibles_ids)]
                        
                    df_posiciones_filtradas = df_posiciones_filtradas[
                        (df_posiciones_filtradas['Posición Crítica'].astype(str).str.strip().str.lower() == 'si') &
                        (df_posiciones_filtradas['Nivel MLA'].astype(str).str.strip() != '5') &
                        (~df_posiciones_filtradas['Nombre de la Posición'].astype(str).str.upper().str.contains('DIRECTOR GENERAL'))
                    ]
                    
                    col_r1 = next((c for c in df_posiciones_filtradas.columns if 'readiness 1' in str(c).lower()), None)
                    col_r2 = next((c for c in df_posiciones_filtradas.columns if 'readiness 2' in str(c).lower()), None)
                    col_r3 = next((c for c in df_posiciones_filtradas.columns if 'readiness 3' in str(c).lower()), None)
                    col_r4 = next((c for c in df_posiciones_filtradas.columns if 'readiness 4' in str(c).lower()), None)
                    col_r5 = next((c for c in df_posiciones_filtradas.columns if 'readiness 5' in str(c).lower()), None)
                    
                    r_inm = r_1_3 = r_mas_3 = 0
                    if not df_posiciones_filtradas.empty:
                        s1 = df_posiciones_filtradas[col_r1].astype(str).str.lower().fillna('') if col_r1 else pd.Series(['']*len(df_posiciones_filtradas))
                        s2 = df_posiciones_filtradas[col_r2].astype(str).str.lower().fillna('') if col_r2 else pd.Series(['']*len(df_posiciones_filtradas))
                        s3 = df_posiciones_filtradas[col_r3].astype(str).str.lower().fillna('') if col_r3 else pd.Series(['']*len(df_posiciones_filtradas))
                        s4 = df_posiciones_filtradas[col_r4].astype(str).str.lower().fillna('') if col_r4 else pd.Series(['']*len(df_posiciones_filtradas))
                        s5 = df_posiciones_filtradas[col_r5].astype(str).str.lower().fillna('') if col_r5 else pd.Series(['']*len(df_posiciones_filtradas))
                        
                        todas_readiness = pd.concat([s1, s2, s3, s4, s5])
                        r_inm = int(todas_readiness.str.contains('inmediato').sum())
                        r_1_3 = int(todas_readiness.str.contains('1 a 3').sum())
                        r_mas_3 = int(todas_readiness.str.contains('mas de 3|más de 3').sum())
                    
                    total_sucesores_mapeados = r_inm + r_1_3 + r_mas_3
                    pct_inm = round((r_inm / total_sucesores_mapeados) * 100, 1) if total_sucesores_mapeados > 0 else 0.0
                    pct_1_3 = round((r_1_3 / total_sucesores_mapeados) * 100, 1) if total_sucesores_mapeados > 0 else 0.0
                    pct_mas_3 = round((r_mas_3 / total_sucesores_mapeados) * 100, 1) if total_sucesores_mapeados > 0 else 0.0
                    
                    st.write("")
                    st.markdown("#### 🩺 Salud de la Bancada (Readiness Global)")
                    rk1, rk2, rk3 = st.columns(3)
                    with rk1:
                        if st.button(f"🟢 Inmediato\n\n{pct_inm}% ({r_inm} colab.)", key="b_read_inm", use_container_width=True):
                            st.session_state['filtro_kpi_plan'] = 'inmediato'; st.rerun()
                    with rk2:
                        if st.button(f"🟡 1 a 3 años\n\n{pct_1_3}% ({r_1_3} colab.)", key="b_read_1_3", use_container_width=True):
                            st.session_state['filtro_kpi_plan'] = '1_3_anos'; st.rerun()
                    with rk3:
                        if st.button(f"🔵 Más de 3 años\n\n{pct_mas_3}% ({r_mas_3} colab.)", key="b_read_mas_3", use_container_width=True):
                            st.session_state['filtro_kpi_plan'] = 'mas_3_anos'; st.rerun()
                    st.write("---")
                    
                    if not df_posiciones_filtradas.empty:
                        col_suc = 'Sucesor P.1' if 'Sucesor P.1' in df_posiciones_filtradas.columns else 'Sucesor 1'
                        sucs = df_posiciones_filtradas[col_suc].fillna('').astype(str).str.strip().str.lower()
                        # Se retiró "sin sucesor identificado" de la lista de invalid_sucs
                        invalid_sucs = ['pendiente', 'nan', 'none', '', 'no definido']
                        df_posiciones_filtradas['Tiene_Sucesor'] = (~sucs.isin(invalid_sucs)).astype(int)
                        total_criticas = len(df_posiciones_filtradas)
                        sucesores_definidos = df_posiciones_filtradas['Tiene_Sucesor'].sum()
                        sucesores_pendientes = total_criticas - sucesores_definidos
                    else:
                        df_posiciones_filtradas['Tiene_Sucesor'] = 0
                        total_criticas = 0; sucesores_definidos = 0; sucesores_pendientes = 0
                    
                    col_k1, col_k2, col_k3 = st.columns(3)
                    with col_k1:
                        if st.button(f"📘 TOTAL CRÍTICAS\n\n{total_criticas}", use_container_width=True): st.session_state['filtro_kpi_plan'] = 'todas'; st.rerun()
                    with col_k2:
                        if st.button(f"✅ MAPEO DEFINIDO\n\n{sucesores_definidos}", use_container_width=True): st.session_state['filtro_kpi_plan'] = 'con_sucesor'; st.rerun()
                    with col_k3:
                        if st.button(f"🚨 PENDIENTES\n\n{sucesores_pendientes}", use_container_width=True): st.session_state['filtro_kpi_plan'] = 'pendientes'; st.rerun()
                    
                    if 'filtro_kpi_plan' in st.session_state and st.session_state['filtro_kpi_plan']:
                        modo = st.session_state['filtro_kpi_plan']
                        
                        if modo in ['inmediato', '1_3_anos', 'mas_3_anos']:
                            target_term1 = 'inmediato' if modo == 'inmediato' else ('1 a 3' if modo == '1_3_anos' else 'mas de 3')
                            target_term2 = 'más de 3' if modo == 'mas_3_anos' else target_term1
                            titulo_lista = f"Sucesores mapeados a: {target_term1.capitalize()}"
                            
                            lista_sucesores = []
                            for _, r in df_posiciones_filtradas.iterrows():
                                pos = clean_text(r.get('Nombre de la Posición', ''))
                                ocupante = clean_text(r.get('Nombre', ''))
                                
                                s1 = clean_text(r.get('Sucesor P.1', r.get('Sucesor 1', '')))
                                read1 = clean_text(r.get(col_r1, '')) if col_r1 else ''
                                s2 = clean_text(r.get('Sucesor P.2', r.get('Sucesor 2', '')))
                                read2 = clean_text(r.get(col_r2, '')) if col_r2 else ''
                                s3 = clean_text(r.get('Sucesor P.3', r.get('Sucesor 3', '')))
                                read3 = clean_text(r.get(col_r3, '')) if col_r3 else ''
                                s4 = clean_text(r.get('Sucesor P.4', r.get('Sucesor 4', '')))
                                read4 = clean_text(r.get(col_r4, '')) if col_r4 else ''
                                s5 = clean_text(r.get('Sucesor P.5', r.get('Sucesor 5', '')))
                                read5 = clean_text(r.get(col_r5, '')) if col_r5 else ''
                                
                                for suc, read in [(s1, read1), (s2, read2), (s3, read3), (s4, read4), (s5, read5)]:
                                    rl = read.lower()
                                    if target_term1 in rl or target_term2 in rl:
                                        lista_sucesores.append({
                                            "Posición Crítica": pos,
                                            "Ocupante Actual": ocupante,
                                            "Nombre del Sucesor": suc if suc else "No definido",
                                            "Readiness": read
                                        })
                            
                            df_lista_suc = pd.DataFrame(lista_sucesores)
                            with st.container():
                                st.markdown(f"#### 📋 {titulo_lista} ({len(df_lista_suc)} registros)")
                                if not df_lista_suc.empty:
                                    st.dataframe(df_lista_suc, use_container_width=True, hide_index=True)
                                else:
                                    st.info("No hay registros en esta categoría.")
                                if st.button("❌ Cerrar lista", key="cerrar_lista_kpi_read"): st.session_state['filtro_kpi_plan'] = None; st.rerun()

                        else:
                            if modo == 'todas': df_mostrar = df_posiciones_filtradas; titulo_lista = "Todas las Posiciones Críticas"
                            elif modo == 'con_sucesor': df_mostrar = df_posiciones_filtradas[df_posiciones_filtradas['Tiene_Sucesor'] == 1]; titulo_lista = "Posiciones con Mapeo Definido"
                            else: df_mostrar = df_posiciones_filtradas[df_posiciones_filtradas['Tiene_Sucesor'] == 0]; titulo_lista = "Posiciones Pendientes de Sucesor"
                            
                            with st.container():
                                st.markdown(f"#### 📋 {titulo_lista} (Haz clic para cargar)")
                                if df_mostrar.empty: st.info("No hay posiciones en esta categoría.")
                                else:
                                    cols_grid = st.columns(3)
                                    for i, row_dict in enumerate(df_mostrar.to_dict('records')):
                                        p_name = clean_text(row_dict.get('Nombre de la Posición'))
                                        if p_name and cols_grid[i % 3].button(p_name, key=f"grid_btn_{i}_{modo}", use_container_width=True):
                                            st.session_state['plan_pos'] = p_name; st.session_state['filtro_kpi_plan'] = None; st.rerun()
                                if st.button("❌ Cerrar lista", key="cerrar_lista_kpi"): st.session_state['filtro_kpi_plan'] = None; st.rerun()
                    
                    st.write("---")
                    st.markdown("#### 📥 Exportar Reporte de Sucesiones")
                    cols_reporte = [
                        'Nombre', 'Nombre de la Posición', 'Dirección', 'Nivel MLA', 'Resultado 9 box', 
                        'Sucesor de emergencia',
                        'Sucesor P.1', 'Tiempo de Readiness 1', 'Positivo 1', 'Oportunidad 1',
                        'Sucesor P.2', 'Tiempo de Readiness 2', 'Positivo 2', 'Oportunidad 2',
                        'Sucesor P.3', 'Tiempo de Readiness 3', 'Positivo 3', 'Oportunidad 3',
                        'Sucesor P.4', 'Tiempo de Readiness 4', 'Positivo 4', 'Oportunidad 4',
                        'Sucesor P.5', 'Tiempo de Readiness 5', 'Positivo 5', 'Oportunidad 5',
                        'Comentarios de Sucesión'
                    ]
                    cols_existentes = [c for c in cols_reporte if c in df_posiciones_filtradas.columns]
                    
                    if not df_posiciones_filtradas.empty:
                        csv_data = df_posiciones_filtradas[cols_existentes].to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📊 Descargar Reporte Completo (CSV para Excel)",
                            data=csv_data,
                            file_name=f'Reporte_Sucesiones_{f_lid_plan.replace(" ", "_")}.csv',
                            mime='text/csv'
                        )
                    else:
                        st.info("No hay datos para exportar con los filtros actuales.")
                    st.write("---")
                    
                    pos_series = df_posiciones_filtradas['Nombre de la Posición'].dropna().astype(str).str.strip()
                    posiciones_opciones = sorted(pos_series[pos_series != ''].unique().tolist())
                    
                    if 'plan_pos' in st.session_state and st.session_state['plan_pos'] not in [""] + posiciones_opciones: st.session_state['plan_pos'] = ""

                    pos_seleccionada = st.selectbox("🔍 Selecciona la Posición Crítica para editar (Filtrada por tu selección global):", [""] + posiciones_opciones, key="plan_pos")
                    
                    def obtener_ficha_candidato(nombre_cand):
                        if not nombre_cand or nombre_cand in ["Pendiente", "Sin sucesor identificado"]: return None
                        match_colab = df_completo[df_completo['Nombre_Cruce'] == nombre_cand.strip().lower()]
                        if match_colab.empty: return None
                        row_c = match_colab.iloc[0]
                        dir_candidato = clean_text(row_c.get('Dirección', row_c.get('Direccion')), 'No asignada')
                        
                        if "TODAS" not in direccion_permitida:
                            lista_dirs_perm = [d.strip() for d in direccion_permitida.split(",")]
                            if not any(d in dir_candidato.upper() for d in lista_dirs_perm):
                                return "RESTRINGIDO_GLOBAL"
                        
                        if st.session_state.get('lider_permitido', "TODOS") != "TODOS":
                            if nombre_cand.strip().lower() not in st.session_state['nombres_permitidos_limpios']:
                                return "RESTRINGIDO_LIDER_CUENTA"
                                
                        if f_lid_plan != "Todos":
                            if nombre_cand.strip().lower() not in subordinados_nombres_limpios: return "RESTRINGIDO_LIDER"
                                
                        puesto_actual = clean_text(row_c.get('Nombre de la Posición'), 'Puesto no asignado')
                        box_c = clean_text(row_c.get('Resultado 9 box'), 'Pendiente')
                        edr_c = clean_text(row_c.get('EDR', row_c.get('EDR ')), 'Pendiente')
                        eng_key = next((k for k in row_c.keys() if k and 'enganche' in str(k).lower()), None)
                        eng_c = clean_text(row_c.get(eng_key), 'N/A') if eng_key else 'N/A'
                        return {"puesto_actual": puesto_actual, "direccion": dir_candidato, "box": box_c, "enganche": eng_c, "edr": edr_c}
                    
                    def generar_sugerencias_ia(pos_destino, info_pos_destino):
                        if not pos_destino or df_completo.empty: return []
                        mla_destino = clean_text(info_pos_destino.get('Nivel MLA'), '')
                        ocupante_destino = clean_text(info_pos_destino.get('Nombre'), '').lower()
                        
                        contexto_destino = extraer_contexto(pos_destino)
                        
                        basura_ia = {"coordinador", "jefe", "gerente", "director", "supervisor", "analista", "especialista", "encargado", "auxiliar", "sr", "jr", "tecnicos", "conocimientos", "desarrollo", "gestión"}
                        ctx_dest_puro = {w for w in contexto_destino if w not in basura_ia}
                        if not ctx_dest_puro: ctx_dest_puro = contexto_destino
                        
                        candidatos_sugeridos = []
                        
                        for row in df_completo.to_dict('records'):
                            nombre = clean_text(row.get('Nombre'))
                            if not nombre or nombre.lower() == ocupante_destino: continue
                            puesto_act = clean_text(row.get('Nombre de la Posición'))
                            if puesto_act.lower() == pos_destino.lower(): continue
                            
                            contexto_cand_puesto = extraer_contexto(puesto_act)
                            pdi_texto = ""
                            if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                                df_c = df_pdi[df_pdi['Nombre'].astype(str).str.strip().str.lower() == nombre.strip().lower()]
                                col_obj = next((c for c in df_c.columns if 'objetivo' in clean_text(str(c)).lower()), None)
                                col_acc = next((c for c in df_c.columns if 'qué' in clean_text(str(c)).lower() or 'acci' in clean_text(str(c)).lower()), None)
                                for _, c_row in df_c.iterrows(): 
                                    obj_str = clean_text(c_row[col_obj]) if col_obj else ""
                                    acc_str = clean_text(c_row[col_acc]) if col_acc else ""
                                    pdi_texto += f" {obj_str} {acc_str}"
                            
                            contexto_cand_pdi = extraer_contexto(pdi_texto)
                            perfil_tecnico_candidato = contexto_cand_puesto.union(contexto_cand_pdi)
                            
                            if not ctx_dest_puro.intersection(perfil_tecnico_candidato): continue 
                            
                            box = clean_text(row.get('Resultado 9 box')).upper()
                            if box not in ['1', '2', '3', '4', '5', '6']: continue 
                            
                            mla_cand = clean_text(row.get('Nivel MLA'))
                            score = 0; razones = []
                            
                            if ctx_dest_puro.intersection(contexto_cand_puesto): score += 5; razones.append("Afinidad técnica actual")
                            elif ctx_dest_puro.intersection(contexto_cand_pdi): score += 4; razones.append("Desarrollando skills afines (PDI)")
                                
                            if box in ['1', '2', '3', '5']: score += 4; razones.append("Alto Potencial (9-Box)")
                            elif box in ['4', '6']: score += 2; razones.append("Desempeño Sólido")
                                
                            if mla_destino.isdigit() and mla_cand.isdigit():
                                diff = int(mla_destino) - int(mla_cand)
                                if diff == 1: score += 3; razones.append("Listo para ascenso")
                                elif diff == 0: score += 2; razones.append("Movimiento lateral orgánico")
                                    
                            if score >= 7: candidatos_sugeridos.append({'nombre': nombre, 'puesto': puesto_act, 'direccion': clean_text(row.get('Dirección')), 'box': box, 'score': score, 'razon': " | ".join(razones)})
                                
                        return sorted(candidatos_sugeridos, key=lambda x: x['score'], reverse=True)[:3]

                    def diagnosticar_pdi_ia(nombre_cand, puesto_destino, info_cand):
                        if not nombre_cand or nombre_cand in ["Pendiente", "Sin sucesor identificado"] or isinstance(info_cand, str) or not info_cand: return None
                        if df_pdi.empty: return {"estatus": "SIN_DATOS", "msg": "No hay PDI registrado."}
                        
                        match_pdi = df_pdi[df_pdi['Nombre'].astype(str).str.strip().str.lower() == nombre_cand.strip().lower()]
                        if match_pdi.empty: return {"estatus": "SIN_PDI", "puesto_origen": info_cand['puesto_actual'], "recomendacion": f"🚨 **Acción Requerida:** El colaborador no tiene acciones en su PDI hacia *{puesto_destino}*."}
                        
                        col_obj = next((c for c in match_pdi.columns if 'objetivo' in clean_text(str(c)).lower()), None)
                        col_acc = next((c for c in match_pdi.columns if 'qué' in clean_text(str(c)).lower() or 'acci' in clean_text(str(c)).lower()), None)
                        
                        obj_pdi = clean_text(match_pdi.iloc[0][col_obj]) if col_obj else 'Sin objetivo definido'
                        acciones_pdi = " ".join([clean_text(r[col_acc]) for _, r in match_pdi.iterrows()]) if col_acc else ""
                        
                        contexto_destino = extraer_contexto(puesto_destino)
                        
                        basura_ia = {"coordinador", "jefe", "gerente", "director", "supervisor", "analista", "especialista", "encargado", "auxiliar", "sr", "jr", "tecnicos", "conocimientos", "desarrollo", "gestión"}
                        ctx_dest_puro = {w for w in contexto_destino if w not in basura_ia}
                        if not ctx_dest_puro: ctx_dest_puro = contexto_destino
                        
                        contexto_pdi = extraer_contexto(obj_pdi + " " + acciones_pdi)
                        coincidencias = ctx_dest_puro.intersection(contexto_pdi)
                        puesto_origen = info_cand['puesto_actual']
                        
                        if len(coincidencias) > 0: return {"estatus": "ALINEADO", "icono": "✅", "titulo_estatus": "PDI Alineado", "color_borde": "#16a34a", "bg_color": "#f0fdf4", "puesto_origen": puesto_origen, "objetivo": obj_pdi, "avance": "Variado", "acciones": "Múltiples acciones registradas", "recomendacion": f"El PDI actual cubre competencias afines a *{puesto_destino}*."}
                        else: return {"estatus": "REQUIERE_AJUSTE", "icono": "🟡", "titulo_estatus": "Ajuste Recomendado", "color_borde": "#ca8a04", "bg_color": "#fefce8", "puesto_origen": puesto_origen, "objetivo": obj_pdi, "avance": "Variado", "acciones": "Falta especificidad técnica", "recomendacion": f"💡 **Recomendación IA:** Se requiere actualizar las Acciones (70/20/10) agregando competencias técnicas específicas hacia el nuevo puesto."}

                    if pos_seleccionada:
                        df_ocupantes = df_posiciones_filtradas[df_posiciones_filtradas['Nombre de la Posición'].apply(clean_text) == pos_seleccionada]
                        info_pos = df_ocupantes.iloc[0] 
                        nombres_ocupantes = [clean_text(n, 'Vacante / Sin asignar') for n in df_ocupantes['Nombre'].tolist()]
                        
                        st.markdown(f"#### 📌 Posición Crítica: `{pos_seleccionada}`")
                        
                        def mostrar_ficha_mini(nombre_cand, df_db):
                            if not nombre_cand or nombre_cand in ["Pendiente", "Vacante / Sin asignar", "No definido", "Sin sucesor identificado"]: st.info("Sin información de ocupante"); return
                            match = df_db[df_db['Nombre_Cruce'] == nombre_cand.strip().lower()]
                            if match.empty: st.warning("Colaborador no encontrado en la base."); return
                            row = match.iloc[0]
                            def get_nom(val): return dict_nom_global.get(clean_id(val), val)
                            
                            puesto = clean_text(row.get('Nombre de la Posición', 'N/A'))
                            lider = get_nom(row.get('ID Del Jefe', ''))
                            dir_c = clean_text(row.get('Dirección', row.get('Direccion', 'N/A')))
                            mla = clean_text(row.get('Nivel MLA', 'N/A'))
                            box = clean_text(row.get('Resultado 9 box', 'Pendiente'))
                            edr_key = next((k for k in row.keys() if k and 'edr' in str(k).lower()), None)
                            edr = clean_text(row.get(edr_key, 'Pendiente')) if edr_key else 'Pendiente'
                            eng_key = next((k for k in row.keys() if k and 'enganche' in str(k).lower()), None)
                            eng = clean_text(row.get(eng_key, 'N/A')) if eng_key else 'N/A'
                            suc1 = get_nom(row.get('Sucesor P.1', row.get('Sucesor 1', '')))
                            read1 = clean_text(row.get('Tiempo de Readiness 1', ''))
                            
                            st.markdown(f"""
                            <div style='padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px; font-family: sans-serif; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 10px;'>
                                <h4 style='margin-top: 0; color: #1e3a8a; font-size: 18px;'>{nombre_cand}</h4>
                                <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Puesto:</b> {puesto}</p>
                                <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Líder:</b> {lider}</p>
                                <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Dirección:</b> {dir_c}</p>
                                <hr style='margin: 10px 0; border: 0; border-top: 1px dashed #cbd5e1;'>
                                <div style='display: flex; gap: 8px; margin-bottom: 10px;'>
                                    <span style='background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>MLA: {mla}</span>
                                    <span style='background: #f1f5f9; color: #334155; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>9-BOX: {box}</span>
                                    <span style='background: #f1f5f9; color: #334155; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>EDR: {edr}</span>
                                </div>
                                <p style='margin: 0; font-size: 13px; color: #b91c1c;'><b>🔥 Enganche Individual:</b> {eng}</p>
                                <p style='margin: 6px 0 0 0; font-size: 13px; color: #4338ca;'><b>🥇 Sucesor 1:</b> {suc1 if suc1 else 'Pendiente'} <span style='font-size:11px; color:#64748b;'>{read1}</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            titulo_ocupantes = f"👥 Ocupantes Actuales ({len(nombres_ocupantes)})"
                            if hasattr(st, 'popover'):
                                with st.popover(titulo_ocupantes, use_container_width=True):
                                    for ocupante in nombres_ocupantes: mostrar_ficha_mini(ocupante, df_completo)
                            else:
                                with st.expander(titulo_ocupantes):
                                    for ocupante in nombres_ocupantes: mostrar_ficha_mini(ocupante, df_completo)
                                    
                        with col_info2:
                            sucesores_pasados = []
                            try:
                                columnas_historial = ["1. Sucesor 2025", "2. Sucesor 2025", "3. Sucesor 2025", "4. Sucesor 2025"]
                                for col_name in info_pos.index:
                                    if isinstance(col_name, str) and (col_name in columnas_historial or bool(re.search(r'Sucesor 20\d\d', col_name, re.IGNORECASE))):
                                        val = clean_text(info_pos.get(col_name, ''))
                                        if val and val.lower() not in ['nan', 'none', 'pendiente', '', 'n/a', 'no definido']:
                                            if val not in sucesores_pasados: sucesores_pasados.append(val)
                            except Exception: pass
                            
                            if hasattr(st, 'popover'):
                                with st.popover("⏳ Sucesores del Año Pasado", use_container_width=True):
                                    if sucesores_pasados:
                                        for s_pasado in sucesores_pasados: st.markdown(f"- {s_pasado}")
                                    else: st.info("No hay historial registrado en el Excel")
                            else:
                                with st.expander("⏳ Sucesores del Año Pasado"):
                                    if sucesores_pasados:
                                        for s_pasado in sucesores_pasados: st.markdown(f"- {s_pasado}")
                                    else: st.info("No hay historial registrado en el Excel")
                        
                        st.write("")
                        with st.expander("🤖 Mostrar Sugerencias de Sucesión (IA de Diccionario)"):
                            st.info("Haz clic en el botón para que la IA escanee la base en busca de afinidad con el puesto.")
                            if st.button("✨ Generar Sugerencias con IA", use_container_width=True):
                                with st.spinner("🧠 Buscando cruces de perfiles..."):
                                    sugerencias = generar_sugerencias_ia(pos_seleccionada, info_pos)
                                    if sugerencias:
                                        items_html = ""
                                        for s in sugerencias:
                                            if "TODAS" not in direccion_permitida and not any(d in s['direccion'].upper() for d in [d.strip() for d in direccion_permitida.split(",")]): info_vis = "🔒 <i>Detalles confidenciales (Otra Dirección)</i>"
                                            elif st.session_state.get('lider_permitido', "TODOS") != "TODOS" and s['nombre'].strip().lower() not in st.session_state['nombres_permitidos_limpios']: info_vis = "🔒 <i>Detalles confidenciales (Usuario Limitado por Cuenta)</i>"
                                            elif f_lid_plan != "Todos" and s['nombre'].strip().lower() not in subordinados_nombres_limpios: info_vis = "🔒 <i>Detalles confidenciales (Modo Presentación Activo)</i>"
                                            else: info_vis = f"📌 Puesto Actual: <b>{s['puesto']}</b> | 📊 9-Box: <b>{s['box']}</b>"
                                            items_html += f"<li>👤 <b>{s['nombre']}</b> — {info_vis}<br><span style='color:#0369a1;'>💡 {s['razon']}</span></li>"
                                        st.markdown(f"""<div style="background:#e0f2fe; border-left:5px solid #0284c7; padding:12px; border-radius:8px; margin-bottom:5px; font-size:13px; color:#0f172a;"><ul style="margin:8px 0 0 0; padding-left:20px; line-height:1.5;">{items_html}</ul></div>""", unsafe_allow_html=True)
                                    else:
                                        st.warning("⚠️ **Dictamen IA:** No se detectaron candidatos en la plantilla actual que cumplan con los criterios estrictos para esta posición crítica. **Se sugiere reclutamiento externo.**")
                        
                        nombres_empleados = sorted(df_completo['Nombre'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
                        opciones_sucesores = ["Pendiente", "Sin sucesor identificado"] + nombres_empleados
                        opciones_tiempo = ["Pendiente", "Inmediato", "1 a 3 años", "Más de 3 años"]
                        
                        ph_pos = "Ej. Menciona los logros recientes más destacados, fortalezas clave o competencias técnicas consolidadas..."
                        ph_opo = "Ej. ¿Qué brechas de liderazgo, conocimientos técnicos o experiencia necesita cubrir para estar listo?"
                        
                        def leer_campo(nombre_col):
                            col_match = next((c for c in info_pos.index if str(nombre_col).strip().lower() == str(c).strip().lower()), None)
                            val = info_pos[col_match] if col_match else ""
                            return clean_text(val) if pd.notna(val) else ""

                        c_suc_emergencia = leer_campo('Sucesor de emergencia') or "Pendiente"
                        
                        c_sucs = []
                        c_reads = []
                        c_pos = []
                        c_opos = []
                        for i in range(1, 6):
                            c_sucs.append(leer_campo(f'Sucesor P.{i}') or "Pendiente")
                            c_reads.append(leer_campo(f'Tiempo de Readiness {i}') or "Pendiente")
                            c_pos.append(leer_campo(f'Positivo {i}'))
                            c_opos.append(leer_campo(f'Oportunidad {i}'))
                            
                            if c_sucs[-1] not in opciones_sucesores: opciones_sucesores.append(c_sucs[-1])
                            if c_reads[-1] not in opciones_tiempo: opciones_tiempo.append(c_reads[-1])
                        
                        if c_suc_emergencia not in opciones_sucesores: opciones_sucesores.append(c_suc_emergencia)
                        
                        st.write("")
                        st.markdown("#### 🚨 Cobertura de Emergencia")
                        n_suc_emergencia = st.selectbox("Candidato de Emergencia", opciones_sucesores, index=opciones_sucesores.index(c_suc_emergencia), key=f"select_emergencia_{pos_seleccionada}")
                        
                        ficha_emergencia = obtener_ficha_candidato(n_suc_emergencia)
                        if ficha_emergencia == "RESTRINGIDO_GLOBAL": st.error("🔒 Datos confidenciales (Colaborador de otra Dirección)")
                        elif ficha_emergencia == "RESTRINGIDO_LIDER_CUENTA": st.error("🔒 Acceso Restringido")
                        elif ficha_emergencia == "RESTRINGIDO_LIDER": st.error("🔒 Modo Presentación Activo")
                        elif ficha_emergencia:
                            with st.expander("📊 Mostrar Métricas del Candidato"):
                                st.success(f"📊 **9-Box:** {ficha_emergencia['box']} | 🔥 **Enganche:** {ficha_emergencia['enganche']} | 📈 **EDR:** {ficha_emergencia['edr']}")
                        
                        st.write("---")
                        
                        k_state = f'num_sucs_{pos_seleccionada}'
                        if k_state not in st.session_state:
                            if c_sucs[4] not in ["Pendiente", "", "Sin sucesor identificado", "Vacante / Sin asignar"]: st.session_state[k_state] = 5
                            elif c_sucs[3] not in ["Pendiente", "", "Sin sucesor identificado", "Vacante / Sin asignar"]: st.session_state[k_state] = 4
                            else: st.session_state[k_state] = 3
                            
                        num_sucs = st.session_state[k_state]
                        
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                        with col_btn1:
                            if st.button("➕ Agregar Sucesor", disabled=(num_sucs >= 5), use_container_width=True):
                                st.session_state[k_state] += 1
                                st.rerun()
                        with col_btn2:
                            if st.button("❌ Quitar Último", disabled=(num_sucs <= 3), use_container_width=True):
                                st.session_state[k_state] -= 1
                                st.rerun()
                        with col_btn3:
                            if num_sucs >= 5: st.info("Límite máximo de banca alcanzado (5 sucesores).")
                                
                        st.write("")
                        
                        n_sucs = c_sucs.copy()
                        n_reads = c_reads.copy()
                        n_pos_inputs = c_pos.copy()
                        n_opo_inputs = c_opos.copy()

                        cols_sucs = st.columns(num_sucs)
                        
                        for i in range(num_sucs):
                            with cols_sucs[i]:
                                st.markdown(f"#### {'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '🏅'} Sucesor {i+1}")
                                
                                idx_sel = opciones_sucesores.index(c_sucs[i]) if c_sucs[i] in opciones_sucesores else 0
                                n_sucs[i] = st.selectbox(f"Candidato {i+1}", opciones_sucesores, index=idx_sel, key=f"select_suc{i+1}_{pos_seleccionada}")
                                
                                ficha_c = obtener_ficha_candidato(n_sucs[i])
                                if ficha_c == "RESTRINGIDO_GLOBAL": st.error("🔒 Datos confidenciales")
                                elif ficha_c == "RESTRINGIDO_LIDER_CUENTA": st.error("🔒 Acceso Restringido")
                                elif ficha_c == "RESTRINGIDO_LIDER": st.error("🔒 Modo Presentación")
                                elif ficha_c:
                                    with st.expander("📊 Mostrar Métricas del Candidato"):
                                        st.success(f"📊 **9-Box:** {ficha_c['box']} | 🔥 **Enganche:** {ficha_c['enganche']} | 📈 **EDR:** {ficha_c['edr']}")
                                    pdi_diag = diagnosticar_pdi_ia(n_sucs[i], pos_seleccionada, ficha_c)
                                    if pdi_diag and pdi_diag.get("estatus") == "SIN_PDI": st.warning(pdi_diag['recomendacion'])
                                    elif pdi_diag and "color_borde" in pdi_diag: st.markdown(f"<details style='background:{pdi_diag['bg_color']}; border-left:4px solid {pdi_diag['color_borde']}; padding:12px; border-radius:6px; cursor:pointer;'><summary style='font-weight:bold; font-size:15px; color:#1e293b; outline:none;'>🤖 Dictamen IA: {pdi_diag['icono']} {pdi_diag['titulo_estatus']}</summary><div style='margin-top:10px; font-size:14px; color:#334155; line-height:1.5;'>🎯 <b>Objetivo PDI:</b> {pdi_diag['objetivo']} (Avance: <b>{pdi_diag['avance']}</b>)<br><br>📌 <b>RECOMENDACIÓN:</b><br>{pdi_diag['recomendacion']}</div></details>", unsafe_allow_html=True)
                                
                                idx_read = opciones_tiempo.index(c_reads[i]) if c_reads[i] in opciones_tiempo else 0
                                n_reads[i] = st.radio(f"⏳ Readiness {i+1}", opciones_tiempo, index=idx_read, key=f"r_read{i+1}_{pos_seleccionada}", horizontal=True)
                                n_pos_inputs[i] = st.text_area(f"👍 Comentarios Positivos {i+1}", value=c_pos[i], height=80, key=f"t_pos{i+1}_{pos_seleccionada}", placeholder=ph_pos)
                                n_opo_inputs[i] = st.text_area(f"📈 Áreas de Oportunidad {i+1}", value=c_opos[i], height=80, key=f"t_opo{i+1}_{pos_seleccionada}", placeholder=ph_opo)
                        
                        st.write("---")
                        st.markdown("#### 📋 Plan de Acción / Comentarios Adicionales")
                        st.info("Utiliza este espacio para justificar si no hay sucesores o detallar el plan a seguir.")
                        
                        c_plan_accion = leer_campo('Comentarios de Sucesión') 
                        n_plan_accion = st.text_area("Comentarios del Plan de Acción:", value=c_plan_accion, height=100, key=f"t_plan_accion_{pos_seleccionada}")
                        
                        st.write("")
                        submitted = st.button("💾 Guardar Cambios en Base de Datos", type="primary", use_container_width=True)
                        
                        if submitted:
                            with st.spinner("🤖 El robot está escribiendo en tu Excel..."):
                                try:
                                    secretos = st.secrets["connections"]["gsheets"]
                                    credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                    cliente = gspread.authorize(credenciales)
                                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                    doc_id = match.group(1) if match else LINK_ARCHIVO
                                    archivo = cliente.open_by_key(doc_id)
                                    pestana = archivo.worksheet("Base de datos")
                                    
                                    headers_bd = pestana.row_values(1)
                                    
                                    def idx_col(nombre):
                                        for i, header in enumerate(headers_bd):
                                            if str(header).strip().lower() == str(nombre).strip().lower():
                                                return i + 1
                                        return None
                                    
                                    idx_emergencia = idx_col('Sucesor de emergencia')
                                    idx_plan_accion = idx_col('Comentarios de Sucesión')
                                    
                                    idxs_sucs = [idx_col(f'Sucesor P.{i}') for i in range(1, 6)]
                                    idxs_reads = [idx_col(f'Tiempo de Readiness {i}') for i in range(1, 6)]
                                    idxs_pos = [idx_col(f'Positivo {i}') for i in range(1, 6)]
                                    idxs_opos = [idx_col(f'Oportunidad {i}') for i in range(1, 6)]
                                    
                                    for idx_p in df_ocupantes.index:
                                        idx_excel = idx_p + 2 
                                        
                                        if idx_emergencia: pestana.update_cell(idx_excel, idx_emergencia, "Pendiente" if n_suc_emergencia == "Pendiente" else n_suc_emergencia)
                                        if idx_plan_accion: pestana.update_cell(idx_excel, idx_plan_accion, n_plan_accion)
                                        
                                        for i in range(5):
                                            if idxs_sucs[i]: pestana.update_cell(idx_excel, idxs_sucs[i], "Pendiente" if n_sucs[i] == "Pendiente" else n_sucs[i])
                                            if idxs_reads[i]: pestana.update_cell(idx_excel, idxs_reads[i], "Pendiente" if n_reads[i] == "Pendiente" else n_reads[i])
                                            if idxs_pos[i]: pestana.update_cell(idx_excel, idxs_pos[i], n_pos_inputs[i])
                                            if idxs_opos[i]: pestana.update_cell(idx_excel, idxs_opos[i], n_opo_inputs[i])
                                        
                                        time.sleep(0.5) 
                                    
                                    try: archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                    except Exception: pass 
                                    
                                    st.success("✅ ¡Guardado exitosamente! El mapa se está actualizando...")
                                    st.cache_data.clear(); st.rerun()
                                except Exception as e: st.error(f"❌ Error técnico al intentar escribir en el Excel: {e}")
                
                with tab_pdi_equipo:
                    st.markdown("### 📈 Seguimiento de PDI de mi Equipo")
                    st.info("Gracias a la nueva arquitectura multifila, ahora puedes ver el estatus granular de cada acción del plan 70-20-10 de tus colaboradores.")
                    if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                        nombres_visibles_limpios = [str(d['Nombre']).strip().lower() for d in kpis['data_total']]
                        df_pdi_filtrado = df_pdi.copy()
                        
                        if f_lid_plan != "Todos":
                            df_pdi_filtrado = df_pdi_filtrado[df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower().isin(subordinados_nombres_limpios)]
                        else:
                            df_pdi_filtrado = df_pdi_filtrado[df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower().isin(nombres_visibles_limpios)]
                        
                        columnas_busqueda = [
                            ("nómina", "Nómina"),
                            ("nombre", "Colaborador"),
                            ("roles", "Roles / Áreas de Interés"),
                            ("objetivo", "Objetivo PDI"),
                            ("pdi", "PDI (70/20/10)"), 
                            ("clasificacion", "Clasificación de Competencia"),
                            ("qué", "Qué? / Acciones"),
                            ("para qué", "¿Para qué? / Competencia"),
                            ("quién", "¿Quién? / Recursos"),
                            ("cuándo", "¿Cuándo? / Fechas"),
                            ("cómo", "Métricas"),
                            ("avance", "% de Avance"),
                            ("estatus", "Estatus")
                        ]
                        cols_reales = []; nombres_finales = []
                        for clave, nombre_nuevo in columnas_busqueda:
                            col_match = None
                            if clave == "pdi":
                                col_match = next((c for c in df_pdi_filtrado.columns if clean_text(str(c)).lower() == "pdi"), None)
                                if not col_match:
                                    col_match = next((c for c in df_pdi_filtrado.columns if 'pdi' in clean_text(str(c)).lower() and 'objetivo' not in clean_text(str(c)).lower()), None)
                            else:
                                col_match = next((c for c in df_pdi_filtrado.columns if clean_text(clave).lower() in clean_text(str(c)).lower() and c not in cols_reales), None)
                            
                            if col_match and col_match not in cols_reales: 
                                cols_reales.append(col_match)
                                nombres_finales.append(nombre_nuevo)
                        
                        if cols_reales:
                            df_pdi_mostrar = df_pdi_filtrado[cols_reales].copy()
                            df_pdi_mostrar.columns = nombres_finales
                            
                            col_acc_tabla = next((c for c in df_pdi_mostrar.columns if 'Acciones' in c), None)
                            if col_acc_tabla:
                                df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_acc_tabla].astype(str).str.strip() != ""]
                                
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
                                
                                prom_70 = get_avg(mask_70)
                                prom_20 = get_avg(mask_20)
                                prom_10 = get_avg(mask_10)
                                promedio_avance = get_avg(pd.Series(True, index=df_pdi_mostrar.index))
                                
                            st.markdown("#### 📊 Análisis Global del Modelo 70-20-10")
                            pk1, pk2, pk3, pk4, pk5 = st.columns(5)
                            
                            with pk1:
                                if st.button(f"📊 Total Acciones\n\n{total_acciones}", key="b_pdi_todas", use_container_width=True): 
                                    st.session_state['filtro_pdi_cat'] = 'todas'
                                    st.rerun()
                                    
                            with pk2:
                                st.button(f"📈 Avance Promedio\n\n{promedio_avance}%", key="b_pdi_prom", use_container_width=True)
                                    
                            with pk3:
                                if st.button(f"🔵 Experiencia (70%)\n\n{prom_70}%", key="b_pdi_70", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '70'
                                    st.rerun()
                                    
                            with pk4:
                                if st.button(f"🟡 Mentoring (20%)\n\n{prom_20}%", key="b_pdi_20", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '20'
                                    st.rerun()
                                    
                            with pk5:
                                if st.button(f"🔴 Formación (10%)\n\n{prom_10}%", key="b_pdi_10", use_container_width=True):
                                    st.session_state['filtro_pdi_cat'] = '10'
                                    st.rerun()
                                    
                            st.write("---")
                            
                            if 'filtro_pdi_cat' in st.session_state and st.session_state['filtro_pdi_cat'] not in ['todas', None]:
                                f_cat = st.session_state['filtro_pdi_cat']
                                if col_pdi_kpi:
                                    df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar[col_pdi_kpi].astype(str).str.contains(f_cat)]
                                    c_f1, c_f2 = st.columns([8, 2])
                                    c_f1.info(f"👆 **Filtro Activo:** Mostrando exclusivamente las acciones de la categoría **{f_cat}%**.")
                                    if c_f2.button("❌ Quitar filtro", use_container_width=True):
                                        st.session_state['filtro_pdi_cat'] = None
                                        st.rerun()
                            
                            col_p1, col_p2, col_p3 = st.columns(3)
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
                        else: st.warning("⚠️ Esperando el primer guardado para construir la tabla de seguimiento.")
                    else: st.warning("⚠️ No hay planes de desarrollo registrados en el equipo todavía.")
                
                # LA NUEVA MAGIA: PESTAÑA PERSONAL DEL LÍDER
                with tab_mi_pdi:
                    renderizar_mi_pdi(df_completo, df_pdi)
                
                if st.session_state["id_usuario"] == "admin":
                    with tab_admin:
                        st.markdown("### ⚙️ Gestión de Usuarios Directivos")
                        st.info("Administra los accesos a la plataforma. Estos se sincronizan en vivo con tu pestaña 'Usuarios' de Google Sheets.")

                        current_timestamp_u = obtener_timestamp_actualizacion(LINK_ARCHIVO)
                        df_u_admin = cargar_datos_csv(LINK_ARCHIVO, "Usuarios", current_timestamp_u)

                        sub_tab_nuevo, sub_tab_editar = st.tabs(["➕ Agregar Nuevo Perfil", "✏️ Editar / Eliminar Perfil"])

                        with sub_tab_nuevo:
                            with st.form("nuevo_usuario_form", clear_on_submit=True):
                                st.markdown("#### Crear Alta de Usuario")
                                
                                lista_empleados_busqueda = []
                                for _, r in df_completo.iterrows():
                                    nom = clean_id(r.get('id Empleado'))
                                    nombre = clean_text(r.get('Nombre'))
                                    if nom and nombre:
                                        lista_empleados_busqueda.append(f"{nom} - {nombre}")
                                lista_empleados_busqueda = sorted(list(set(lista_empleados_busqueda)))
                                
                                seleccion_empleado = st.selectbox("🔍 Buscar colaborador (Por Número de Nómina o Nombre)", [""] + lista_empleados_busqueda)
                                
                                n_pass = st.text_input(f"Contraseña temporal (Sugerencia: {PASSWORD_POR_DEFECTO})", value=PASSWORD_POR_DEFECTO)
                                n_dir_list = st.multiselect("🏢 Direcciones Permitidas (Elige 'TODAS', 'COLABORADOR' o múltiples áreas)", ["TODAS", "COLABORADOR"] + dirs)
                                
                                lideres_para_admin = sorted(df_completo['Nombre'].dropna().astype(str).str.strip()[lambda x: x != ''].unique().tolist())
                                n_lider_list = st.multiselect("👤 Líder Restringido (Filtro por jerarquía de equipo)", ["TODOS"] + lideres_para_admin, default=["TODOS"])
                                
                                submit_btn = st.form_submit_button("Crear Nuevo Usuario")
                                
                                if submit_btn:
                                    if seleccion_empleado and n_pass and n_dir_list:
                                        n_user = seleccion_empleado.split(" - ")[0].strip()
                                        n_nombre = seleccion_empleado.split(" - ")[1].strip()
                                        n_dir = ", ".join(n_dir_list)
                                        n_lider = ", ".join(n_lider_list) if n_lider_list else "TODOS"
                                        
                                        with st.spinner("🤖 Escribiendo usuario en Google Sheets..."):
                                            try:
                                                secretos = st.secrets["connections"]["gsheets"]
                                                credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                                                cliente = gspread.authorize(credenciales)
                                                match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                                                doc_id = match.group(1) if match else LINK_ARCHIVO
                                                archivo = cliente.open_by_key(doc_id)
                                                
                                                pestana_users = archivo.worksheet("Usuarios")
                                                pestana_users.append_row([n_user, n_nombre, n_pass, n_dir, n_lider])
                                                
                                                archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                
                                                st.success(f"✅ ¡Usuario '{n_nombre}' ({n_user}) creado exitosamente! Ya puede iniciar sesión.")
                                                st.cache_data.clear()
                                                time.sleep(1.5)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Error al crear el usuario. Asegúrate de que la pestaña 'Usuarios' tenga 5 columnas en la fila 1 (Usuario, Nombre, Password, Direccion, Lider Restringido). Detalles: {e}")
                                    else:
                                        st.warning("⚠️ Debes seleccionar un colaborador y al menos una Dirección Permitida para crear el usuario.")
                        
                        with sub_tab_editar:
                            if not df_u_admin.empty:
                                lista_usuarios_edit = []
                                for _, r in df_u_admin.iterrows():
                                    u_id_val = str(r.get("Usuario", "")).strip()
                                    u_nom_val = str(r.get("Nombre", "")).strip()
                                    if u_id_val: 
                                        lista_usuarios_edit.append(f"{u_id_val} - {u_nom_val}")
                                
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
                                        e_pass = st.text_input("Contraseña", value=c_pass)
                                        e_dir_list = st.multiselect("🏢 Direcciones Permitidas", opciones_dir, default=c_dir_list_valid)
                                        e_lider_list = st.multiselect("👤 Líder Restringido (Filtro por jerarquía de equipo)", opciones_lid, default=c_lid_list_valid)
                                        
                                        col_b1, col_b2 = st.columns(2)
                                        btn_actualizar = col_b1.form_submit_button("💾 Actualizar Permisos", type="primary", use_container_width=True)
                                        btn_eliminar = col_b2.form_submit_button("🗑️ Eliminar Usuario", use_container_width=True)
                                        
                                        if btn_actualizar:
                                            if e_dir_list:
                                                e_dir_str = ", ".join(e_dir_list)
                                                e_lider_str = ", ".join(e_lider_list) if e_lider_list else "TODOS"
                                                with st.spinner("🤖 Actualizando usuario en Google Sheets..."):
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
                                                            pestana_users.update_cell(fila_usuario, 3, e_pass)
                                                            pestana_users.update_cell(fila_usuario, 4, e_dir_str)
                                                            pestana_users.update_cell(fila_usuario, 5, e_lider_str)
                                                            
                                                            archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                                                            st.cache_data.clear()
                                                            st.success(f"✅ ¡Usuario actualizado exitosamente!")
                                                            time.sleep(1.5)
                                                            st.rerun()
                                                        except ValueError:
                                                            st.error("❌ El usuario no fue encontrado en la hoja de Excel.")
                                                    except Exception as e:
                                                        st.error(f"❌ Error de conexión: {e}")
                                            else:
                                                st.warning("⚠️ Debes seleccionar al menos una Dirección Permitida.")
                                                
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
                                                    except ValueError:
                                                        st.error("❌ El usuario no fue encontrado en la hoja de Excel.")
                                                except Exception as e:
                                                    st.error(f"❌ Error de conexión: {e}")
                            else:
                                st.info("No hay usuarios registrados en la base de datos.")
                                    
                        st.write("---")
                        st.markdown("#### 👥 Usuarios Actuales en Base de Datos")
                        if not df_u_admin.empty:
                            st.dataframe(df_u_admin, use_container_width=True, hide_index=True)
                        else:
                            st.info("La pestaña 'Usuarios' en Google Sheets está vacía.")
                            
if __name__ == "__main__":
    main()
