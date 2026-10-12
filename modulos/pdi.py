import streamlit as st
import pandas as pd
import re
import time
import gspread
from google.oauth2.service_account import Credentials

from config_ui import clean_text, clean_id
from database import LINK_ARCHIVO, PESTANA_PDI_ACTUAL
from modulos.mapa_org import buscar_columna

COLUMNAS_PDI = [
    "Nómina", "Nombre", "Puesto", "Dirección", "Líder", "Fecha Elaboración", "Departamento",
    "Rol Interés 1", "Motivo 1", "Rol Interés 2", "Motivo 2", "Rol Interés 3", "Motivo 3",
    "Objetivo PDI", "PDI", "Qué? / Acciones de Desarrollo", 
    "¿Para qué? / Competencia", "¿Quién? / Recursos", "¿Cómo sabremos que se logró? / Métricas", 
    "¿Cuándo? / Fechas", "% de Avance", "Estatus"
]

def renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior=pd.DataFrame()):
    st.markdown(f"### 📝 Plan de Desarrollo Individual (PDI)")
    
    estado_pdi = st.session_state.get("estado_pdi", "ABIERTO")
    if estado_pdi == "CERRADO" and st.session_state.get("id_usuario") != "admin":
        st.error("🔒 **Periodo de Captura de PDI Cerrado**")
        st.info("El ciclo de planeación de desarrollo ha concluido. Si requieres hacer ajustes a tu PDI, contacta a Recursos Humanos.")
        return

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
        nombres_pdi_limpios = df_pdi['Nombre'].astype(str).str.strip().str.lower()
        datos_pdi_usuario = df_pdi[nombres_pdi_limpios == nombre_colab.strip().lower()].copy()
        
    if 'clonar_pdi' not in st.session_state:
        st.session_state['clonar_pdi'] = False

    if datos_pdi_usuario.empty and not df_pdi_anterior.empty and 'Nombre' in df_pdi_anterior.columns:
        nombres_ant_limpios = df_pdi_anterior['Nombre'].astype(str).str.strip().str.lower()
        historial = df_pdi_anterior[nombres_ant_limpios == nombre_colab.strip().lower()].copy()
        
        if not historial.empty:
            if not st.session_state['clonar_pdi']:
                st.warning("✨ Hemos detectado que tienes un Plan de Desarrollo del ciclo anterior.")
                if st.button("🔄 Clonar estrategias del año pasado", use_container_width=True):
                    st.session_state['clonar_pdi'] = True
                    st.rerun()
            else:
                datos_pdi_usuario = historial.copy() 
                st.success("✅ ¡Datos precargados! Actualiza tus fechas y presiona 'Guardar' al final.")

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
        col_fec = fc('cuándo') or fc('cuándo') or '¿Cuándo? / Fechas'
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

                    datos_a_insertar = []
                    for f in nuevas_filas:
                        datos_a_insertar.append([str(f.get(col, "")) for col in COLUMNAS_PDI])

                    registros_vivos = pestana_pdi_gs.get_all_values()
                    
                    if len(registros_vivos) > 0:
                        encabezados = registros_vivos[0]
                        idx_identificador = buscar_columna(encabezados, 'nómina')
                        if not idx_identificador: 
                            idx_identificador = buscar_columna(encabezados, 'nombre')
                        
                        if idx_identificador:
                            idx_num = encabezados.index(idx_identificador)
                            filas_a_borrar = []
                            valor_buscar = str(nomina_aut).strip().lower() if 'nómina' in idx_identificador.lower() else str(nombre_colab).strip().lower()
                            
                            for i, row in enumerate(registros_vivos):
                                if i > 0 and len(row) > idx_num:
                                    if str(row[idx_num]).strip().lower() == valor_buscar:
                                        filas_a_borrar.append(i + 1)
                            
                            for num_fila in reversed(filas_a_borrar):
                                pestana_pdi_gs.delete_rows(num_fila)

                    if datos_a_insertar:
                        pestana_pdi_gs.append_rows(datos_a_insertar)
                    
                    archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                    st.cache_data.clear()
                    
                    st.balloons()
                    st.toast("¡Plan 70-20-10 guardado exitosamente!", icon="✅")
                    st.markdown("""
                        <div style='background-color: #22c55e; padding: 20px; border-radius: 8px; text-align: center; border: 2px solid #166534; margin-top: 15px; margin-bottom: 15px;'>
                            <h2 style='color: white; margin: 0;'>🎉 ¡Éxito! Tu PDI se guardó correctamente.</h2>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    time.sleep(2.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en Google Sheets: {e}")
