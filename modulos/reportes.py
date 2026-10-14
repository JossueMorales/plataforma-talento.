import streamlit as st
import pandas as pd
import google.generativeai as genai
from modulos.mapa_org import buscar_columna
from config_ui import clean_text, clean_id

def renderizar_reportes(df_seguro, df_completo, df_pdi, df_mla, kpis, f_jerarquia, f_puesto):
    st.markdown("## 📊 Reportes e Inteligencia Artificial")
    st.write("Bienvenido al módulo de análisis estratégico de talento.")
    
    # Validar si el usuario es "admin"
    if str(st.session_state.get("id_usuario")).strip().lower() == "admin":
        
        # ==========================================
        # 1. HERRAMIENTA MANUAL DE REPORTES (EXCEL)
        # ==========================================
        st.markdown("### 📥 Generador de Reportes (Filtros y Excel)")
        
        df_reportes_base = df_seguro.copy()
        df_reportes_base['id_clean'] = df_reportes_base['id Empleado'].apply(clean_id)
        nodos_estrictos_ids = kpis.get('nodos_visibles_ids', [])
        df_reportes_estricto = df_reportes_base[df_reportes_base['id_clean'].isin(nodos_estrictos_ids)].copy()
        
        is_admin = True
        wants_level_5 = is_admin and (('5' in f_jerarquia) or (f_puesto and any('DIRECTOR GENERAL' in p.upper() for p in f_puesto)))
        
        if not wants_level_5:
            col_jer_rep = next((c for c in df_reportes_estricto.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')
            if col_jer_rep in df_reportes_estricto.columns:
                df_reportes_estricto = df_reportes_estricto[
                    (df_reportes_estricto[col_jer_rep].astype(str).str.strip() != '5') &
                    (~df_reportes_estricto['Nombre de la Posición'].astype(str).str.upper().str.contains('DIRECTOR GENERAL'))
                ]
        
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
                
            if 'columnas_seleccionadas' in locals() and columnas_seleccionadas and not df_base_export.empty:
                df_export = df_base_export[columnas_seleccionadas]
                csv_data = df_export.T.to_csv(header=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Descargar Reporte a Excel (Formato Transpuesto)", 
                    data=csv_data, 
                    file_name=f'Reporte_Talento_{st.session_state["nombre_usuario"].replace(" ", "_")}.csv', 
                    mime='text/csv', 
                    use_container_width=True, 
                    type="primary"
                )
            elif 'columnas_seleccionadas' in locals() and not columnas_seleccionadas:
                st.warning("⚠️ Selecciona al menos una columna para habilitar la descarga del archivo.")
        else:
            st.warning("⚠️ No hay datos con los filtros actuales para generar el reporte.")

        st.divider()

        # ==========================================
        # 2. PANEL DE INTELIGENCIA (GEMINI)
        # ==========================================
        if "GEMINI_API_KEY" in st.secrets:
            st.markdown("### 👑 Panel de Inteligencia de RH (Analista de Datos IA)")
            
            with st.expander("🤖 Pregúntale a Gemini sobre Sucesión, PDI y Evaluaciones", expanded=True):
                st.info("El motor de Gemini procesará los Excel completos de la empresa (Mapa de talento, PDI y Evaluaciones) para darte estadísticas, cruces de datos y resúmenes directivos.")
                
                pregunta_admin = st.text_area(
                    "¿Qué quieres saber sobre los datos de la empresa?", 
                    placeholder="Ej. ¿Cuántas personas son Sucesores Inmediatos y no tienen un PDI iniciado? o ¿Cuáles son las 3 competencias más bajas de la Dirección de Manufactura?",
                    height=100
                )
                
                if st.button("📊 Analizar Base de Datos con IA", type="primary"):
                    if pregunta_admin.strip() == "":
                        st.warning("Por favor, escribe una pregunta primero.")
                    else:
                        with st.spinner("🧠 Leyendo bases de datos y calculando métricas... (Puede tomar unos segundos)"):
                            try:
                                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                                modelo_analista = genai.GenerativeModel('gemini-1.5-flash')
                                
                                csv_completo = df_completo.to_csv(index=False) if not df_completo.empty else "Sin datos"
                                csv_pdi = df_pdi.to_csv(index=False) if not df_pdi.empty else "Sin datos"
                                csv_mla = df_mla.to_csv(index=False) if not df_mla.empty else "Sin datos"
                                
                                prompt_analista = f"""
                                Eres el Director de Data Analytics de Recursos Humanos de la empresa Ayvi.
                                Se te proporcionan las bases de datos en vivo de la empresa en formato CSV.
                                
                                Tus instrucciones estrictas:
                                1. Cruza la información de Sucesión (Plantilla), Avance de PDI y Resultados MLA para responder.
                                2. Responde ÚNICAMENTE basándote en los datos adjuntos. No inventes información.
                                3. Calcula porcentajes, conteos o listas exactas si la pregunta lo requiere.
                                4. Da tu respuesta en un formato claro, directivo y profesional.
                                
                                Pregunta del Director de RH: {pregunta_admin}
                                
                                Bases de Datos:
                                === DATOS DE PLANTILLA Y SUCESIÓN ===
                                {csv_completo[:15000]}
                                
                                === ESTATUS DE PDI ===
                                {csv_pdi[:15000]}
                                
                                === RESULTADOS EVALUACIÓN MLA ===
                                {csv_mla[:15000]}
                                """
                                
                                respuesta_analista = modelo_analista.generate_content(prompt_analista)
                                
                                st.success("✅ Análisis completado:")
                                st.markdown(respuesta_analista.text)
                                
                            except Exception as e:
                                st.error(f"❌ Ocurrió un error en el análisis de datos: {e}")
        else:
            st.error("No se encontró la llave GEMINI_API_KEY en los secretos de Streamlit.")
            
    else:
        st.warning("🔒 **Acceso Restringido**")
        st.info("Esta sección contiene métricas confidenciales y herramientas de Inteligencia Artificial exclusivas para la administración de Recursos Humanos.")
