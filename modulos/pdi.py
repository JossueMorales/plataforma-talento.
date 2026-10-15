import streamlit as st
import pandas as pd
import re
import time
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

from config_ui import clean_text, clean_id
from database import LINK_ARCHIVO
from modulos.mapa_org import buscar_columna

COLUMNAS_PDI = [
    "Nómina", "Nombre", "Puesto", "Dirección", "Líder", "Fecha Elaboración", "Departamento",
    "Rol Interés 1", "Motivo 1", "Rol Interés 2", "Motivo 2", "Rol Interés 3", "Motivo 3",
    "Objetivo PDI", "PDI", "Qué? / Acciones de Desarrollo", 
    "¿Para qué? / Competencia", "¿Quién? / Recursos", "¿Cómo sabremos que se logró? / Métricas", 
    "¿Cuándo? / Fechas", "% de Avance", "Estatus"
]

def renderizar_mi_pdi(df_completo, df_pdi, df_pdi_anterior=pd.DataFrame(), df_mla=pd.DataFrame(), df_comp_funcionales=pd.DataFrame(), df_comp_por_area=pd.DataFrame(), df_comp_tecnicas=pd.DataFrame(), df_evaluaciones=pd.DataFrame(), es_lider_evaluando=False, empleado_a_evaluar=None):
    pdi_planeacion_str = st.session_state.get("pdi_planeacion", "PDI 2027")
    pdi_cierre_str = st.session_state.get("pdi_cierre", "PDI 2026")
    
    estado_pdi = st.session_state.get("estado_pdi", "ABIERTO")
    
    col_tit, col_btn = st.columns([4, 1])
    with col_tit:
        st.markdown(f"### 📝 Plan de Desarrollo Individual")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True) 
        components.html(
            """
            <button onclick="window.parent.print()" style="background-color: #ffffff; border: 1px solid #cbd5e1; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-family: sans-serif; font-size: 14px; font-weight: bold; color: #1e40af; width: 100%; box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f1f5f9'" onmouseout="this.style.backgroundColor='#ffffff'">
                🖨️ Imprimir / PDF
            </button>
            """,
            height=50
        )
    
    if estado_pdi == "CERRADO" and st.session_state.get("id_usuario") != "admin":
        st.error("🔒 **Periodo de Captura de PDI Cerrado**")
        st.info("El ciclo de planeación y evaluación ha concluido. Si requieres hacer ajustes, contacta a Recursos Humanos.")
        return

    nombre_colab = empleado_a_evaluar if es_lider_evaluando and empleado_a_evaluar else st.session_state["nombre_usuario"]
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

    tab_evaluacion, tab_planeacion = st.tabs([f"📊 Evaluación ({pdi_cierre_str})", f"🚀 Planeación ({pdi_planeacion_str})"])

    opciones_avance = ["0%", "25%", "50%", "75%", "100%"]
    opciones_estatus = ["No Iniciado", "En proceso", "Completado", "Cancelado"]
    roles_disponibles = [""] + df_completo['Nombre de la Posición'].dropna().astype(str).drop_duplicates().tolist()
    
    def index_seguro(lista, valor): return lista.index(valor) if valor in lista else 0

    with tab_evaluacion:
        st.info(f"Aquí puedes evaluar el avance de los objetivos que te propusiste para el ciclo **{pdi_cierre_str}**. Solo puedes editar el % de Avance y el Estatus.")
        
        datos_pdi_cierre = pd.DataFrame()
        if not df_pdi_anterior.empty:
            col_nom_ant = buscar_columna(df_pdi_anterior.columns, 'nómina')
            if col_nom_ant and nomina_aut != "N/A":
                ids_ant_limpios = df_pdi_anterior[col_nom_ant].apply(clean_id)
                datos_pdi_cierre = df_pdi_anterior[ids_ant_limpios == nomina_aut].copy()
            elif 'Nombre' in df_pdi_anterior.columns:
                nombres_ant_limpios = df_pdi_anterior['Nombre'].astype(str).str.strip().str.lower()
                datos_pdi_cierre = df_pdi_anterior[nombres_ant_limpios == nombre_colab.strip().lower()].copy()
            
        if datos_pdi_cierre.empty:
            st.warning(f"No tienes un PDI registrado para el ciclo {pdi_cierre_str}.")
        else:
            with st.form("form_evaluacion_pdi", clear_on_submit=False):
                primer_row_c = datos_pdi_cierre.iloc[0]
                def f_c(keyword): return next((c for c in datos_pdi_cierre.columns if clean_text(keyword).lower() in clean_text(str(c)).lower()), None)
                
                fecha_elab_c = str(primer_row_c.get(f_c('fecha elab') or 'Fecha Elaboración', ''))
                depto_c = str(primer_row_c.get(f_c('departamento') or 'Departamento', ''))
                rol_1_c = str(primer_row_c.get(f_c('rol interés 1') or 'Rol Interés 1', ''))
                mot_1_c = str(primer_row_c.get(f_c('motivo 1') or 'Motivo 1', ''))
                objetivo_c = str(primer_row_c.get(f_c('objetivo') or 'Objetivo PDI', ''))
                
                st.markdown(f"**Objetivo del Ciclo:** {objetivo_c}")
                st.markdown(f"**Rol de Interés Principal:** {rol_1_c}")
                st.divider()
                
                col_cat = f_c('pdi') or f_c('clasificacion') or f_c('categoría') or 'PDI'
                col_acc = f_c('qué') or f_c('acción') or 'Qué? / Acciones de Desarrollo'
                col_comp = f_c('para qué') or f_c('competencia') or '¿Para qué? / Competencia'
                col_rec = f_c('quién') or f_c('recursos') or '¿Quién? / Recursos'
                col_met = f_c('cómo') or f_c('métricas') or '¿Cómo sabremos que se logró? / Métricas'
                col_fec = f_c('cuándo') or f_c('cuándo') or '¿Cuándo? / Fechas'
                col_av = f_c('avance') or '% de Avance'
                col_est = f_c('estatus') or 'Estatus'
                
                acciones_cierre = []
                for idx, row in datos_pdi_cierre.iterrows():
                    acc_val = str(row.get(col_acc, ''))
                    if acc_val.strip() != "":
                        acciones_cierre.append({
                            "idx": idx,
                            "cat": str(row.get(col_cat, '')),
                            "acc": acc_val, "comp": str(row.get(col_comp, '')),
                            "rec": str(row.get(col_rec, '')), "met": str(row.get(col_met, '')),
                            "fec": str(row.get(col_fec, '')), "av": str(row.get(col_av, '0%')),
                            "est": str(row.get(col_est, 'No Iniciado'))
                        })
                
                nuevas_evaluaciones = []
                
                for i, accion in enumerate(acciones_cierre):
                    st.markdown(f"**{accion['cat']}**")
                    a1, a2, a3, a4 = st.columns([4, 1.5, 1.5, 1.5])
                    a1.text_area("Acción de Desarrollo", value=accion['acc'], disabled=True, key=f"eval_acc_{i}", height=68)
                    a2.text_input("Fecha Ejecución", value=accion['fec'], disabled=True, key=f"eval_fec_{i}")
                    n_av = a3.selectbox("% Avance", opciones_avance, index=index_seguro(opciones_avance, accion['av']), key=f"eval_av_{i}")
                    n_est = a4.selectbox("Estatus", opciones_estatus, index=index_seguro(opciones_estatus, accion['est']), key=f"eval_est_{i}")
                    st.write("")
                    
                    accion_actualizada = {
                        "PDI": accion['cat'], "Qué? / Acciones de Desarrollo": accion['acc'], 
                        "¿Para qué? / Competencia": accion['comp'], "¿Quién? / Recursos": accion['rec'], 
                        "¿Cómo sabremos que se logró? / Métricas": accion['met'], "¿Cuándo? / Fechas": accion['fec'], 
                        "% de Avance": n_av, "Estatus": n_est
                    }
                    nuevas_evaluaciones.append(accion_actualizada)
                
                btn_guardar_evaluacion = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)
                
                if btn_guardar_evaluacion:
                    with st.spinner(f"☁️ Guardando evaluación en {pdi_cierre_str}..."):
                        try:
                            secretos = st.secrets["connections"]["gsheets"]
                            credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                            cliente = gspread.authorize(credenciales)
                            match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                            doc_id = match.group(1) if match else LINK_ARCHIVO
                            archivo = cliente.open_by_key(doc_id)
                            pestana_pdi_cierre_gs = archivo.worksheet(pdi_cierre_str)
                            
                            base_fila_c = {
                                "Nómina": nomina_aut, "Nombre": nombre_colab, "Puesto": puesto_aut,
                                "Dirección": dir_aut, "Líder": lider_aut, "Fecha Elaboración": fecha_elab_c,
                                "Departamento": depto_c, "Rol Interés 1": rol_1_c, "Motivo 1": str(primer_row_c.get(f_c('motivo 1') or 'Motivo 1', '')),
                                "Rol Interés 2": str(primer_row_c.get(f_c('rol interés 2') or 'Rol Interés 2', '')), "Motivo 2": str(primer_row_c.get(f_c('motivo 2') or 'Motivo 2', '')), 
                                "Rol Interés 3": str(primer_row_c.get(f_c('rol interés 3') or 'Rol Interés 3', '')), "Motivo 3": str(primer_row_c.get(f_c('motivo 3') or 'Motivo 3', '')), 
                                "Objetivo PDI": objetivo_c
                            }
                            
                            datos_a_insertar = []
                            for acc in nuevas_evaluaciones:
                                fila = base_fila_c.copy()
                                fila.update(acc)
                                datos_a_insertar.append([str(fila.get(col, "")) for col in COLUMNAS_PDI])
                                
                            registros_vivos = pestana_pdi_cierre_gs.get_all_values()
                            if len(registros_vivos) > 0:
                                encabezados = registros_vivos[0]
                                idx_identificador = buscar_columna(encabezados, 'nómina') or buscar_columna(encabezados, 'nombre')
                                if idx_identificador:
                                    idx_num = encabezados.index(idx_identificador)
                                    filas_a_borrar = []
                                    valor_buscar = str(nomina_aut).strip().lower() if 'nómina' in idx_identificador.lower() else str(nombre_colab).strip().lower()
                                    for i, row in enumerate(registros_vivos):
                                        if i > 0 and len(row) > idx_num and str(row[idx_num]).strip().lower() == valor_buscar:
                                            filas_a_borrar.append(i + 1)
                                    for num_fila in reversed(filas_a_borrar):
                                        pestana_pdi_cierre_gs.delete_rows(num_fila)

                            if datos_a_insertar:
                                pestana_pdi_cierre_gs.append_rows(datos_a_insertar)
                            
                            archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                            st.cache_data.clear()
                            st.success(f"✅ ¡Evaluación guardada exitosamente en {pdi_cierre_str}!")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar en Google Sheets: {e}")

    with tab_planeacion:
        st.info(f"Diseña tu estrategia de desarrollo para el ciclo **{pdi_planeacion_str}**.")
        
        datos_pdi_usuario = pd.DataFrame()
        if not df_pdi.empty:
            col_nom_act = buscar_columna(df_pdi.columns, 'nómina')
            if col_nom_act and nomina_aut != "N/A":
                ids_act = df_pdi[col_nom_act].apply(clean_id)
                datos_pdi_usuario = df_pdi[ids_act == nomina_aut].copy()
            elif 'Nombre' in df_pdi.columns:
                nombres_act = df_pdi['Nombre'].astype(str).str.strip().str.lower()
                datos_pdi_usuario = df_pdi[nombres_act == nombre_colab.strip().lower()].copy()
            
        if 'clonar_pdi' not in st.session_state:
            st.session_state['clonar_pdi'] = False

        historial = pd.DataFrame()
        if not df_pdi_anterior.empty:
            col_nom_ant = buscar_columna(df_pdi_anterior.columns, 'nómina')
            if col_nom_ant and nomina_aut != "N/A":
                ids_ant = df_pdi_anterior[col_nom_ant].apply(clean_id)
                historial = df_pdi_anterior[ids_ant == nomina_aut].copy()
            elif 'Nombre' in df_pdi_anterior.columns:
                nombres_ant = df_pdi_anterior['Nombre'].astype(str).str.strip().str.lower()
                historial = df_pdi_anterior[nombres_ant == nombre_colab.strip().lower()].copy()

        if not historial.empty:
            if not st.session_state['clonar_pdi']:
                if datos_pdi_usuario.empty:
                    st.warning(f"✨ Tienes un PDI del ciclo anterior ({pdi_cierre_str}).")
                    if st.button("🔄 Clonar estrategias no completadas", use_container_width=True):
                        st.session_state['clonar_pdi'] = True
                        st.rerun()
                else:
                    with st.expander(f"✨ Detectamos un historial en {pdi_cierre_str}. ¿Deseas sobreescribir este plan?"):
                        st.info("Ya tienes datos guardados en este nuevo ciclo. Si haces clic aquí, reemplazaremos lo que está abajo con tus pendientes del año pasado.")
                        if st.button("🔄 Sobreescribir trayendo mis pendientes del año pasado", use_container_width=True):
                            st.session_state['clonar_pdi'] = True
                            st.rerun()
            else:
                col_est = next((c for c in historial.columns if 'estatus' in clean_text(str(c)).lower()), None)
                if col_est:
                    historial = historial[~historial[col_est].astype(str).str.lower().isin(['completado', 'cancelado', 'terminado', 'concluido'])]
                datos_pdi_usuario = historial.copy() 
                
                num_acciones = 0
                col_acc_clon = next((c for c in historial.columns if 'qué' in clean_text(str(c)).lower() or 'acci' in clean_text(str(c)).lower()), None)
                if col_acc_clon:
                    num_acciones = len(historial[historial[col_acc_clon].astype(str).str.strip() != ""])
                
                st.markdown(f"""
                    <div style='background-color: #dcfce7; padding: 15px; border-radius: 8px; border-left: 5px solid #22c55e; margin-bottom: 15px;'>
                        <h4 style='color: #166534; margin-top: 0;'>✅ ¡Magia completada! Se clonaron {num_acciones} acciones pendientes.</h4>
                        <p style='color: #15803d; margin-bottom: 0; font-size: 14px;'><b>Siguiente paso:</b> Desplázate hacia abajo hasta la sección azul oscuro de <b>"Plan de Desarrollo"</b>. Verás que las cajas de texto de los apartados 70%, 20% y 10% <b>ya contienen tu información</b>. Solo ajusta las fechas objetivo y presiona Guardar.</p>
                    </div>
                """, unsafe_allow_html=True)

        fecha_elab, depto = "", ""
        rol_1, mot_1, rol_2, mot_2, rol_3, mot_3 = "", "", "", "", "", ""
        objetivo = ""
        acciones_70, acciones_20, acciones_10 = [], [], []

        if not datos_pdi_usuario.empty:
            primer_row = datos_pdi_usuario.iloc[0]
            def fc(keyword): return next((c for c in datos_pdi_usuario.columns if clean_text(keyword).lower() in clean_text(str(c)).lower()), None)
                
            fecha_elab = str(primer_row.get(fc('fecha elab') or 'Fecha Elaboración', ''))
            depto = str(primer_row.get(fc('departamento') or 'Departamento', ''))
            rol_1 = str(primer_row.get(fc('rol interés 1') or 'Rol Interés 1', ''))
            mot_1 = str(primer_row.get(fc('motivo 1') or 'Motivo 1', ''))
            rol_2 = str(primer_row.get(fc('rol interés 2') or 'Rol Interés 2', ''))
            mot_2 = str(primer_row.get(fc('motivo 2') or 'Motivo 2', ''))
            rol_3 = str(primer_row.get(fc('rol interés 3') or 'Rol Interés 3', ''))
            mot_3 = str(primer_row.get(fc('motivo 3') or 'Motivo 3', ''))
            objetivo = str(primer_row.get(fc('objetivo') or 'Objetivo PDI', ''))
            
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
        
        with st.expander("📚 Sugerencias de Desarrollo (Catálogo MLA)", expanded=False):
            st.markdown("¿No sabes por dónde empezar tu PDI? El sistema analizará tus áreas de oportunidad del MLA y te mostrará los comportamientos esperados y sugerencias clave para desarrollarlas.")
            
            competencias_bajas = []
            if not df_mla.empty:
                col_id_mla = buscar_columna(df_mla.columns, 'id de usuario') or buscar_columna(df_mla.columns, 'nómina')
                col_comp = buscar_columna(df_mla.columns, 'nombre de competencia') or buscar_columna(df_mla.columns, 'competencia')
                col_lid = buscar_columna(df_mla.columns, 'lider') or buscar_columna(df_mla.columns, 'líder')
                
                if col_id_mla and col_comp and col_lid:
                    datos_mla_usr = df_mla[df_mla[col_id_mla].apply(clean_id) == nomina_aut]
                    if not datos_mla_usr.empty:
                        try:
                            datos_mla_usr['_num_lid'] = pd.to_numeric(datos_mla_usr[col_lid], errors='coerce')
                            competencias_bajas = datos_mla_usr.nsmallest(2, '_num_lid')[col_comp].tolist()
                        except:
                            pass

            if st.button("📖 Consultar sugerencias para mis áreas de oportunidad", type="primary"):
                if not competencias_bajas:
                    st.warning("No encontramos calificaciones bajas en tu evaluación MLA reciente para darte una sugerencia específica.")
                else:
                    with st.spinner("Buscando en la matriz de Orientación MLA..."):
                        try:
                            secretos = st.secrets["connections"]["gsheets"]
                            credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                            cliente = gspread.authorize(credenciales)
                            match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                            doc_id = match.group(1) if match else LINK_ARCHIVO
                            archivo = cliente.open_by_key(doc_id)
                            
                            pestana_orientacion = archivo.worksheet("Orientacion MLA")
                            datos_orientacion = pestana_orientacion.get_all_records()
                            df_orientacion = pd.DataFrame(datos_orientacion)
                            
                            st.success(f"💡 **Resultados encontrados para tus áreas de oportunidad:**")
                            
                            encontro_alguna = False
                            col_o_comp = buscar_columna(df_orientacion.columns, 'competencia')
                            col_o_alineado = buscar_columna(df_orientacion.columns, 'comportamiento alineado')
                            col_o_desalineado = buscar_columna(df_orientacion.columns, 'comportamiento desalineado')
                            col_o_sug = buscar_columna(df_orientacion.columns, 'sugerencias')
                            
                            if col_o_comp and col_o_alineado and col_o_desalineado and col_o_sug:
                                for comp in competencias_bajas:
                                    comp_limpia = clean_text(comp).lower()
                                    match_fyi = df_orientacion[df_orientacion[col_o_comp].apply(lambda x: clean_text(str(x)).lower()) == comp_limpia]
                                    
                                    if not match_fyi.empty:
                                        encontro_alguna = True
                                        fila = match_fyi.iloc[0]
                                        st.markdown(f"### 🎯 Competencia a Desarrollar: **{str(fila[col_o_comp]).title()}**")
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            st.markdown("✔️ **Comportamiento Alineado (Lo esperado)**")
                                            st.info(str(fila[col_o_alineado]))
                                        with c2:
                                            st.markdown("⚠️ **Comportamiento Desalineado (A evitar)**")
                                            st.warning(str(fila[col_o_desalineado]))
                                        st.markdown("🚀 **Sugerencias para mejorar (Acciones PDI):**")
                                        st.success(str(fila[col_o_sug]))
                                        st.divider()
                                        
                            if not encontro_alguna:
                                st.info(f"Las competencias '{', '.join(competencias_bajas)}' aún no tienen sus detalles cargados en la base de datos de Orientación MLA.")
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al buscar en el archivo (Asegúrate de que la pestaña se llama 'Orientacion MLA'): {e}")

        with st.form("form_edicion_pdi_planeacion", clear_on_submit=False):
            st.markdown("<div style='background-color:#fef08a; padding:6px; color:#854d0e; font-weight:bold; text-align:center; border-radius:4px;'>Expectativas de Desarrollo (Colaborador)</div>", unsafe_allow_html=True)
            st.write("")
            
            r1, m1 = st.columns([1, 2])
            rol_int_1 = r1.selectbox("Rol / Área de Interés 1", roles_disponibles, index=index_seguro(roles_disponibles, rol_1), key="mot_r1")
            mot_int_1 = m1.text_input("Motivo 1", value=mot_1, key="mot_m1", placeholder="¿Por qué te interesa este rol?")
            
            r2, m2 = st.columns([1, 2])
            rol_int_2 = r2.selectbox("Rol / Área de Interés 2", roles_disponibles, index=index_seguro(roles_disponibles, rol_2), key="mot_r2")
            mot_int_2 = m2.text_input("Motivo 2", value=mot_2, key="mot_m2")
            
            r3, m3 = st.columns([1, 2])
            rol_int_3 = r3.selectbox("Rol / Área de Interés 3", roles_disponibles, index=index_seguro(roles_disponibles, rol_3), key="mot_r3")
            mot_int_3 = m3.text_input("Motivo 3", value=mot_3, key="mot_m3")
            
            st.write("")
            
            # --- INICIO DE SECCIÓN DE COMPETENCIAS DIVIDIDA EN 2 COLUMNAS ---
            st.markdown("<div style='background-color:#e0f2fe; padding:6px; color:#0369a1; font-weight:bold; text-align:center; border-radius:4px;'>📊 Evaluación de Competencias</div>", unsafe_allow_html=True)
            st.write("")
            
            col_izq, col_der = st.columns(2)
            
            with col_izq:
                st.markdown("##### 🧭 Modelo de Liderazgo Ayvi (MLA)")
                if not df_mla.empty:
                    col_id_mla = buscar_columna(df_mla.columns, 'id de usuario') or buscar_columna(df_mla.columns, 'nómina')
                    if col_id_mla:
                        datos_mla_usr = df_mla[df_mla[col_id_mla].apply(clean_id) == nomina_aut]
                    else:
                        col_nom_mla = buscar_columna(df_mla.columns, 'nombre')
                        datos_mla_usr = df_mla[df_mla[col_nom_mla].astype(str).str.strip().str.lower() == nombre_colab.strip().lower()] if col_nom_mla else pd.DataFrame()
                    
                    if not datos_mla_usr.empty:
                        col_comp = buscar_columna(datos_mla_usr.columns, 'nombre de competencia') or buscar_columna(datos_mla_usr.columns, 'competencia')
                        col_lid = buscar_columna(datos_mla_usr.columns, 'lider') or buscar_columna(datos_mla_usr.columns, 'líder')
                        col_colab = buscar_columna(datos_mla_usr.columns, 'colaborador')
                        
                        if col_comp and col_lid and col_colab:
                            df_tabla_mla = datos_mla_usr[[col_comp, col_colab, col_lid]].copy()
                            df_tabla_mla.columns = ['Competencia MLA', 'Colaborador', 'Líder']
                            st.dataframe(df_tabla_mla, use_container_width=True, hide_index=True)
                else:
                    st.info("Resultados MLA no disponibles.")

            with col_der:
                opciones_calif = ["", "1", "2", "3", "4", "5"]
                evaluaciones_a_guardar = []
                
                # ✨ 1. EXTRAER CONOCIMIENTOS TÉCNICOS
                tecnicas_asignadas = []
                col_puesto_tech = buscar_columna(df_comp_tecnicas.columns, 'puesto') if not df_comp_tecnicas.empty else None
                if col_puesto_tech:
                    match_tech = df_comp_tecnicas[df_comp_tecnicas[col_puesto_tech].astype(str).str.strip().str.lower() == puesto_aut.strip().lower()]
                    if not match_tech.empty:
                        tech_cols = [c for c in match_tech.columns if 'tec' in c.lower()]
                        tecnicas_asignadas = match_tech.iloc[0][tech_cols].dropna().astype(str).tolist()
                        tecnicas_asignadas = [c.strip() for c in tecnicas_asignadas if c.strip() and c.lower() != 'nan']

                # ✨ 2. EXTRAER COMPETENCIAS FUNCIONALES
                funcionales_asignadas = []
                col_puesto_func = buscar_columna(df_comp_funcionales.columns, 'puesto') if not df_comp_funcionales.empty else None
                col_base_func = buscar_columna(df_comp_funcionales.columns, 'base') if not df_comp_funcionales.empty else None
                
                if col_puesto_func and col_base_func and not df_comp_por_area.empty:
                    match_func = df_comp_funcionales[df_comp_funcionales[col_puesto_func].astype(str).str.strip().str.lower() == puesto_aut.strip().lower()]
                    if not match_func.empty:
                        base_comp = match_func.iloc[0].get(col_base_func, '')
                        if base_comp:
                            col_comp_area = buscar_columna(df_comp_por_area.columns, 'competencia')
                            if col_comp_area:
                                match_area = df_comp_por_area[df_comp_por_area[col_comp_area].astype(str).str.strip().str.lower() == str(base_comp).strip().lower()]
                                if not match_area.empty:
                                    area_cols = [c for c in match_area.columns if 'competencia ' in c.lower()]
                                    funcionales_asignadas = match_area.iloc[0][area_cols].dropna().astype(str).tolist()
                                    funcionales_asignadas = [c.strip() for c in funcionales_asignadas if c.strip() and c.lower() != 'nan']

                # ✨ 3. RENDERIZAR INTERFAZ
                def renderizar_filas_evaluacion(lista_comp, titulo, tipo_comp, is_df_empty):
                    st.markdown(f"##### 🛠️ {titulo}")
                    if is_df_empty:
                        st.error(f"🚨 Error de conexión: No se pudo cargar correctamente la pestaña de {titulo} desde Google Sheets.")
                        return
                    if not lista_comp:
                        st.info(f"No hay {titulo.lower()} configuradas para el puesto: {puesto_aut}")
                        return
                        
                    for idx, comp in enumerate(lista_comp):
                        calif_c_prev = ""
                        calif_l_prev = ""
                        if not df_evaluaciones.empty and 'Competencia' in df_evaluaciones.columns and 'Nómina' in df_evaluaciones.columns:
                            match_eval = df_evaluaciones[(df_evaluaciones['Nómina'].astype(str) == str(nomina_aut)) & (df_evaluaciones['Competencia'].astype(str).str.strip().str.lower() == str(comp).strip().lower())]
                            if not match_eval.empty:
                                calif_c_prev = str(match_eval.iloc[0].get('Calif. Colab', ''))
                                calif_l_prev = str(match_eval.iloc[0].get('Calif. Líder', ''))

                        c1, c2, c3 = st.columns([6, 2, 2])
                        c1.markdown(f"<div style='font-size: 13px; margin-top:8px;'>{comp}</div>", unsafe_allow_html=True)
                        
                        idx_c = opciones_calif.index(calif_c_prev) if calif_c_prev in opciones_calif else 0
                        idx_l = opciones_calif.index(calif_l_prev) if calif_l_prev in opciones_calif else 0
                        
                        val_c = c2.selectbox("Colab.", opciones_calif, index=idx_c, disabled=es_lider_evaluando, key=f"c_{tipo_comp}_{idx}", label_visibility="collapsed")
                        val_l = c3.selectbox("Líder", opciones_calif, index=idx_l, disabled=not es_lider_evaluando, key=f"l_{tipo_comp}_{idx}", label_visibility="collapsed")
                        
                        evaluaciones_a_guardar.append({
                            "Nómina": nomina_aut, "Nombre": nombre_colab, "Puesto": puesto_aut,
                            "Tipo de Competencia": tipo_comp, "Competencia": comp, 
                            "Calif. Colab": val_c, "Calif. Líder": val_l, "Fecha": time.strftime("%d/%m/%Y")
                        })

                renderizar_filas_evaluacion(funcionales_asignadas, "Competencias Funcionales", "Funcional", df_comp_funcionales.empty or df_comp_por_area.empty)
                renderizar_filas_evaluacion(tecnicas_asignadas, "Conocimientos Técnicos", "Técnica", df_comp_tecnicas.empty)

            st.write("")
            # --- FIN DE SECCIÓN DE COMPETENCIAS ---
            
            st.markdown("<div style='background-color:#fef08a; padding:6px; color:#854d0e; font-weight:bold; text-align:center; border-radius:4px;'>Objetivo de Desarrollo (Colaborador y Líder)</div>", unsafe_allow_html=True)
            st.write("")
            
            obj_desarrollo = st.text_area("Objetivo a Desarrollar:", value=objetivo, placeholder="Ej. Desarrollar Conocimientos Técnicos, Creación de Equipos eficientes y Valentía Gerencial...", height=68)
            
            st.write("")
            st.markdown("<div style='background-color:#1e40af; padding:8px; color:white; font-weight:bold; text-align:center; border-radius:4px;'>Plan de Desarrollo (Modelo 70-20-10)</div>", unsafe_allow_html=True)
            st.write("")

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
                        "PDI": titulo, "Qué? / Acciones de Desarrollo": acc, "¿Para qué? / Competencia": comp,
                        "¿Quién? / Recursos": rec, "¿Cómo sabremos que se logró? / Métricas": met, 
                        "¿Cuándo? / Fechas": fec, "% de Avance": av, "Estatus": est
                    })
                st.divider()
                return nuevas

            with st.expander("🔵 70% Desarrollo en el trabajo (Aprendizaje basado en experiencia directa)", expanded=True):
                acciones_70_nuevas = render_categoria("70% Desarrollo en el trabajo", "70", acciones_70)
                
            with st.expander("🟡 20% Mentoring (Feedback, coaching, trabajo colaborativo)", expanded=True):
                acciones_20_nuevas = render_categoria("20% Mentoring", "20", acciones_20)
                
            with st.expander("🔴 10% Formación Formal (Cursos, talleres, certificaciones)", expanded=True):
                acciones_10_nuevas = render_categoria("10% Formación Formal", "10", acciones_10)
                
            btn_guardar_pdi = st.form_submit_button(f"💾 Guardar y Compartir Planeación ({pdi_planeacion_str})", use_container_width=True)
            
            if btn_guardar_pdi:
                with st.spinner(f"☁️ Sincronizando con Base de Datos ({pdi_planeacion_str})..."):
                    try:
                        secretos = st.secrets["connections"]["gsheets"]
                        credenciales = Credentials.from_service_account_info(secretos, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                        cliente = gspread.authorize(credenciales)
                        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_ARCHIVO)
                        doc_id = match.group(1) if match else LINK_ARCHIVO
                        archivo = cliente.open_by_key(doc_id)
                        
                        # 1. Guardar el PDI
                        pestana_pdi_gs = archivo.worksheet(pdi_planeacion_str)
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
                            idx_identificador = buscar_columna(encabezados, 'nómina') or buscar_columna(encabezados, 'nombre')
                            if idx_identificador:
                                idx_num = encabezados.index(idx_identificador)
                                filas_a_borrar = []
                                valor_buscar = str(nomina_aut).strip().lower() if 'nómina' in idx_identificador.lower() else str(nombre_colab).strip().lower()
                                for i, row in enumerate(registros_vivos):
                                    if i > 0 and len(row) > idx_num and str(row[idx_num]).strip().lower() == valor_buscar:
                                        filas_a_borrar.append(i + 1)
                                    for num_fila in reversed(filas_a_borrar):
                                        pestana_pdi_gs.delete_rows(num_fila)

                        if datos_a_insertar:
                            pestana_pdi_gs.append_rows(datos_a_insertar)
                            
                        # 2. Guardar las Evaluaciones de Competencias
                        if evaluaciones_a_guardar:
                            try:
                                pestana_eval = archivo.worksheet("Evaluaciones Competencias")
                                registros_eval = pestana_eval.get_all_values()
                                
                                if len(registros_eval) > 0:
                                    encabezados_e = registros_eval[0]
                                    idx_id_e = buscar_columna(encabezados_e, 'nómina')
                                    if idx_id_e:
                                        idx_num_e = encabezados_e.index(idx_id_e)
                                        filas_a_borrar_e = []
                                        for i, row in enumerate(registros_eval):
                                            if i > 0 and len(row) > idx_num_e and str(row[idx_num_e]).strip().lower() == str(nomina_aut).strip().lower():
                                                filas_a_borrar_e.append(i + 1)
                                        for num_fila in reversed(filas_a_borrar_e):
                                            pestana_eval.delete_rows(num_fila)
                                            
                                datos_eval_insertar = []
                                cols_eval = ["Nómina", "Nombre", "Puesto", "Tipo de Competencia", "Competencia", "Calif. Colab", "Calif. Líder", "Fecha"]
                                
                                if len(registros_eval) == 0:
                                    pestana_eval.append_row(cols_eval)
                                    
                                for ev in evaluaciones_a_guardar:
                                    datos_eval_insertar.append([str(ev.get(col, "")) for col in cols_eval])
                                    
                                if datos_eval_insertar:
                                    pestana_eval.append_rows(datos_eval_insertar)
                                    
                            except Exception as eval_err:
                                st.warning(f"Se guardó el PDI, pero hubo un error al guardar las evaluaciones (Asegúrate que exista la pestaña 'Evaluaciones Competencias'): {eval_err}")
                        
                        archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                        st.cache_data.clear()
                        
                        st.balloons()
                        st.toast(f"¡Plan {pdi_planeacion_str} guardado exitosamente!", icon="✅")
                        time.sleep(2.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar en Google Sheets: {e}")
