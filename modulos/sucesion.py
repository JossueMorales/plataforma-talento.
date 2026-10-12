import streamlit as st
import pandas as pd
import re
import time
import gspread
import gspread.utils
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

from config_ui import clean_text, clean_id, extraer_contexto
from database import LINK_ARCHIVO
from modulos.mapa_org import buscar_columna

def renderizar_tab_sucesiones(df_seguro, df_completo, df_pdi, dict_nom_global, jerarquia_global, kpis, f_jerarquia, f_puesto, direccion_permitida, match_nomina):
    estado_suc = st.session_state.get("estado_sucesion", "ABIERTO")
    es_admin = st.session_state.get("id_usuario") == "admin"
    es_director = False
    
    if not match_nomina.empty:
        col_jer_usr = next((c for c in match_nomina.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')
        if str(match_nomina.iloc[0].get(col_jer_usr, '')).strip() == '5':
            es_director = True
            
    f_lid_plan = "Todos"
    subordinados_nombres_limpios = []
    
    if estado_suc == "CERRADO" and not (es_admin or es_director):
        st.error("🔒 **Periodo de Sucesión Cerrado**")
        st.info("El ejercicio de Sucesión para este ciclo ha finalizado. La edición de posiciones críticas se encuentra bloqueada temporalmente por políticas de la Dirección.")
        return f_lid_plan, subordinados_nombres_limpios

    st.markdown("### 🔀 Planificador de Sucesiones (Edición en Vivo)")
    st.info("🔒 **Modo Presentación:** Selecciona a un líder aquí para limitar las posiciones críticas disponibles exclusivamente a su equipo.")
    
    lideres_totales = sorted(list(set([dict_nom_global.get(clean_id(x), "Sin Líder") for x in df_seguro['ID Del Jefe'].dropna().unique() if clean_id(x)])))
    
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
    
    df_base_jerarquia = df_seguro.copy()
    
    col_f_lid_loc, col_espacio = st.columns([1, 2])
    with col_f_lid_loc:
        f_lid_plan = st.selectbox("👤 Líder a revisar (Modo Privado):", ["Todos"] + lideres_totales, key="modo_pres_lider")

    df_posiciones_filtradas = df_base_jerarquia.copy()
    df_posiciones_filtradas['id_clean'] = df_posiciones_filtradas['id Empleado'].apply(clean_id)
    
    nodos_estrictos_ids = kpis.get('nodos_visibles_ids', [])
    
    if f_lid_plan != "Todos":
        sub_ids = obtener_subordinados_ids(f_lid_plan)
        lider_id = next((i for i, n in dict_nom_global.items() if n == f_lid_plan), None)
        if lider_id: sub_ids.add(lider_id)
        sub_ids_filtrados = [s for s in sub_ids if s in nodos_estrictos_ids]
        df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['id_clean'].isin(sub_ids_filtrados)]
        subordinados_nombres_limpios = [str(dict_nom_global.get(s)).strip().lower() for s in sub_ids_filtrados if s in dict_nom_global and str(dict_nom_global.get(s)).strip() != '']
    else:
        df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['id_clean'].isin(nodos_estrictos_ids)]
    
    col_jer_fil = next((c for c in df_posiciones_filtradas.columns if 'jerárquico' in str(c).lower() or 'jerarquico' in str(c).lower()), 'Nivel Jerárquico')

    if not df_posiciones_filtradas.empty:
        filtro_base = (df_posiciones_filtradas['Posición Crítica'].astype(str).str.strip().str.lower() == 'si')
        df_posiciones_filtradas = df_posiciones_filtradas[filtro_base]
        
        wants_level_5 = es_admin and (('5' in f_jerarquia) or (f_puesto and any('DIRECTOR GENERAL' in p.upper() for p in f_puesto)))
        
        if not wants_level_5:
            df_posiciones_filtradas = df_posiciones_filtradas[
                (df_posiciones_filtradas[col_jer_fil].astype(str).str.strip() != '5') &
                (~df_posiciones_filtradas['Nombre de la Posición'].astype(str).str.upper().str.contains('DIRECTOR GENERAL'))
            ]
    
    def get_status_categoria(row):
        invalid_sucs = ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']
        estados_encontrados = []
        for i in range(1, 6):
            c_s = buscar_columna(row.index, 'sucesor', i)
            c_r = buscar_columna(row.index, 'readiness', i)
            if c_s and c_r:
                suc_val = clean_text(row.get(c_s, ''))
                read_val = clean_text(row.get(c_r, '')).strip().lower()
                if suc_val and suc_val.lower() not in invalid_sucs and "vacante" not in suc_val.lower():
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

    if not df_posiciones_filtradas.empty:
        df_posiciones_filtradas['Cat_Sucesion'] = df_posiciones_filtradas.apply(get_status_categoria, axis=1)
        c_inm = (df_posiciones_filtradas['Cat_Sucesion'] == 'inmediato').sum()
        c_1_3 = (df_posiciones_filtradas['Cat_Sucesion'] == '1_3_anos').sum()
        c_mas_3 = (df_posiciones_filtradas['Cat_Sucesion'] == 'mas_3_anos').sum()
        c_sin_suc = (df_posiciones_filtradas['Cat_Sucesion'] == 'sin_sucesor').sum()
        c_pend = (df_posiciones_filtradas['Cat_Sucesion'] == 'pendiente').sum()
        
        invalid_sucs_local = ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']
        sucs_inm = set(); sucs_1_3 = set(); sucs_mas_3 = set()

        for i in range(1, 6):
            c_suc = buscar_columna(df_posiciones_filtradas.columns, 'sucesor', i)
            c_read = buscar_columna(df_posiciones_filtradas.columns, 'readiness', i)
            if c_suc and c_read:
                for _, r in df_posiciones_filtradas.iterrows():
                    nombre_suc = clean_text(r.get(c_suc, '')).strip()
                    read_suc = clean_text(r.get(c_read, '')).strip().lower()
                    if nombre_suc and nombre_suc.lower() not in invalid_sucs_local and "vacante" not in nombre_suc.lower():
                        if 'inmediato' in read_suc: sucs_inm.add(nombre_suc)
                        elif '1 a 3' in read_suc: sucs_1_3.add(nombre_suc)
                        elif 'mas de 3' in read_suc or 'más de 3' in read_suc: sucs_mas_3.add(nombre_suc)
        
        p_inm, p_1_3, p_mas_3 = len(sucs_inm), len(sucs_1_3), len(sucs_mas_3)
        total_criticas = len(df_posiciones_filtradas)
        sucesores_definidos = c_inm + c_1_3 + c_mas_3 + c_sin_suc
        sucesores_pendientes = c_pend
    else:
        df_posiciones_filtradas['Cat_Sucesion'] = "" 
        c_inm = c_1_3 = c_mas_3 = c_sin_suc = c_pend = p_inm = p_1_3 = p_mas_3 = total_criticas = sucesores_definidos = sucesores_pendientes = 0

    pct_inm = round((c_inm / total_criticas) * 100, 1) if total_criticas > 0 else 0.0
    pct_1_3 = round((c_1_3 / total_criticas) * 100, 1) if total_criticas > 0 else 0.0
    pct_mas_3 = round((c_mas_3 / total_criticas) * 100, 1) if total_criticas > 0 else 0.0
    pct_sin_suc = round((c_sin_suc / total_criticas) * 100, 1) if total_criticas > 0 else 0.0

    st.write("")
    st.markdown(f"#### 🩺 Salud de la Bancada ({total_criticas} Posiciones Críticas)")
    rk1, rk2, rk3, rk4 = st.columns(4)
    with rk1:
        if st.button(f"🟢 Inmediato\n\n{pct_inm}% ({c_inm} pos. / {p_inm} pers.)", key="b_read_inm", use_container_width=True):
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'inmediato' else 'inmediato'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    with rk2:
        if st.button(f"🟡 1 a 3 años\n\n{pct_1_3}% ({c_1_3} pos. / {p_1_3} pers.)", key="b_read_1_3", use_container_width=True):
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == '1_3_anos' else '1_3_anos'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    with rk3:
        if st.button(f"🔵 Más de 3 años\n\n{pct_mas_3}% ({c_mas_3} pos. / {p_mas_3} pers.)", key="b_read_mas_3", use_container_width=True):
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'mas_3_anos' else 'mas_3_anos'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    with rk4:
        if st.button(f"🚨 Sin Sucesor\n\n{pct_sin_suc}% ({c_sin_suc} pos.)", key="b_read_sin_suc", use_container_width=True):
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'sin_sucesor' else 'sin_sucesor'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    
    st.write("---")
    
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        if st.button(f"📘 TOTAL CRÍTICAS\n\n{total_criticas}", use_container_width=True): 
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'todas' else 'todas'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    with col_k2:
        if st.button(f"✅ MAPEO DEFINIDO\n\n{sucesores_definidos}", use_container_width=True): 
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'con_sucesor' else 'con_sucesor'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    with col_k3:
        if st.button(f"🚨 PENDIENTES\n\n{sucesores_pendientes}", use_container_width=True): 
            st.session_state['filtro_kpi_plan'] = None if st.session_state.get('filtro_kpi_plan') == 'pendientes' else 'pendientes'
            st.session_state['mostrar_dictamen_ia'] = False
            st.rerun()
    
    st.write("---")
    st.markdown("#### 🧠 Análisis de IA: Índice de Riesgo Operativo")
    if not df_posiciones_filtradas.empty:
        riesgo_acumulado = 0
        alertas_criticas_ia = {}
        for _, row in df_posiciones_filtradas.iterrows():
            puesto_nombre = clean_text(row.get('Nombre de la Posición', ''))
            jefe_id = clean_id(row.get('ID Del Jefe', ''))
            lider_nombre = dict_nom_global.get(jefe_id, 'Líder Desconocido')
            
            readiness_list = [str(row.get(buscar_columna(row.keys(), 'readiness', i), '')).lower() for i in range(1, 6)]
            tiene_inmediato = any('inmediato' in r for r in readiness_list)
            tiene_1a3 = any('1 a 3' in r for r in readiness_list)
            tiene_mas3 = any('más de 3' in r or 'mas de 3' in r for r in readiness_list)
            
            if tiene_inmediato: vuln_base = 0      
            elif tiene_1a3: vuln_base = 30         
            elif tiene_mas3: vuln_base = 70        
            else: vuln_base = 100                  
            
            fuga = str(row.get(buscar_columna(row.keys(), 'riesgo de fuga'), 'Bajo')).strip().lower()
            if fuga == 'alto': vuln_final = min(100, vuln_base + 50)  
            elif fuga == 'bajo': vuln_final = max(0, vuln_base - 20)    
            else: vuln_final = vuln_base
                
            riesgo_acumulado += vuln_final
            
            if lider_nombre not in alertas_criticas_ia:
                alertas_criticas_ia[lider_nombre] = {"total_puestos": 0, "puestos_riesgo_critico": 0, "detalles": []}
            alertas_criticas_ia[lider_nombre]["total_puestos"] += 1
            
            if vuln_final >= 80:
                alertas_criticas_ia[lider_nombre]["puestos_riesgo_critico"] += 1
                motivo = "Sin sucesores" if vuln_base == 100 else "Sucesor a +3 años con Fuga Alta"
                alertas_criticas_ia[lider_nombre]["detalles"].append(f"{puesto_nombre} ({motivo})")

        indice_riesgo_global = round(riesgo_acumulado / total_criticas, 1) if total_criticas > 0 else 0
        
        if indice_riesgo_global <= 30:
            color_riesgo, estatus_riesgo, icono_riesgo = "#16a34a", "Saludable (Bajo Riesgo)", "✅"
        elif indice_riesgo_global <= 60:
            color_riesgo, estatus_riesgo, icono_riesgo = "#ca8a04", "Estable (Riesgo Moderado)", "⚠️"
        else:
            color_riesgo, estatus_riesgo, icono_riesgo = "#dc2626", "Vulnerabilidad Alta", "🚨"

        if 'mostrar_dictamen_ia' not in st.session_state: st.session_state['mostrar_dictamen_ia'] = False

        st.markdown(f"""
        <div style='background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid {color_riesgo}; padding: 15px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: space-between; height: 95px;'>
            <div><h3 style='margin: 0; color: #1e293b; font-size: 24px;'>{indice_riesgo_global}%</h3><p style='margin: 0; color: #64748b; font-size: 14px; font-weight: bold;'>ÍNDICE DE RIESGO OPERATIVO ACTUAL</p></div>
            <div style='text-align: right;'><h4 style='margin: 0; color: {color_riesgo}; font-size: 18px;'>{icono_riesgo} {estatus_riesgo}</h4><p style='margin: 0; color: #94a3b8; font-size: 12px;'>Clic para ver / ocultar Detalles IA</p></div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("BOTON_INVISIBLE_IA_RIESGO", key="btn_ia_riesgo", use_container_width=True):
            st.session_state['mostrar_dictamen_ia'] = not st.session_state.get('mostrar_dictamen_ia', False)
            st.session_state['filtro_kpi_plan'] = None 
            st.rerun()

        components.html("""
        <script>
        function fixButton() {
            const docs = window.parent.document;
            const buttons = Array.from(docs.querySelectorAll('button'));
            const targetBtn = buttons.find(b => b.innerText && b.innerText.includes('BOTON_INVISIBLE_IA_RIESGO'));
            if (targetBtn) {
                let container = targetBtn.closest('div[data-testid="stElementContainer"]');
                if(!container) container = targetBtn.closest('div.element-container');
                if(container) {
                    container.style.height = '0px'; container.style.minHeight = '0px'; container.style.padding = '0px'; container.style.margin = '0px'; container.style.overflow = 'visible';
                    targetBtn.style.opacity = '0'; targetBtn.style.position = 'absolute'; targetBtn.style.transform = 'translateY(-105px)'; targetBtn.style.left = '0'; targetBtn.style.width = '100%'; targetBtn.style.height = '95px'; targetBtn.style.zIndex = '9999'; targetBtn.style.cursor = 'pointer'; targetBtn.style.border = 'none';
                }
            }
        }
        const observer = new MutationObserver(fixButton); observer.observe(window.parent.document.body, {childList: true, subtree: true}); fixButton();
        </script>
        """, height=0, width=0)

        if st.session_state['mostrar_dictamen_ia']:
            lideres_problema = {lid: data for lid, data in alertas_criticas_ia.items() if data["puestos_riesgo_critico"] > 0}
            if not lideres_problema:
                st.success("🤖 **Dictamen IA:** La estructura evaluada presenta una resiliencia sólida. No se detectan concentraciones peligrosas de riesgo operativo.")
            else:
                st.warning("🤖 **Dictamen IA:** Se han detectado áreas con alta concentración de vulnerabilidad. Se sugiere revisión inmediata en las siguientes gerencias/jefaturas:")
                for lider, data in sorted(lideres_problema.items(), key=lambda item: item[1]['puestos_riesgo_critico'], reverse=True):
                    pct_riesgo_lider = round((data["puestos_riesgo_critico"] / data["total_puestos"]) * 100) if data["total_puestos"] > 0 else 0
                    alerta_color, alerta_txt = ("red", "Foco Rojo") if pct_riesgo_lider >= 50 else ("orange", "Precaución")
                    detalle_html = "".join([f"<li>{d}</li>" for d in data["detalles"]])
                    st.markdown(f"<details style='background:#f8fafc; border:1px solid #cbd5e1; padding:12px; border-radius:6px; cursor:pointer; margin-bottom:8px;'><summary style='font-weight:bold; font-size:14px; color:#0f172a; outline:none;'>👤 Equipo de {lider} — <span style='color:{alerta_color};'>[{alerta_txt}: {data['puestos_riesgo_critico']} de {data['total_puestos']} puestos en riesgo]</span></summary><ul style='margin-top:10px; font-size:13px; color:#334155;'>{detalle_html}</ul></details>", unsafe_allow_html=True)
    else:
        st.info("Selecciona posiciones críticas para que la IA genere el análisis de Riesgo Operativo.")
    
    st.write("---")
    
    if 'filtro_kpi_plan' in st.session_state and st.session_state['filtro_kpi_plan']:
        modo = st.session_state['filtro_kpi_plan']
        df_mostrar = pd.DataFrame()
        titulo_lista = ""
        invalid_sucs_local = ['pendiente', 'nan', 'none', '', 'no definido', 'sin sucesor identificado']
        
        if modo in ['inmediato', '1_3_anos', 'mas_3_anos', 'sin_sucesor']:
            if modo == 'inmediato': titulo_lista = "Posiciones con al menos un Sucesor Inmediato"
            elif modo == '1_3_anos': titulo_lista = "Posiciones con al menos un Sucesor a 1-3 años"
            elif modo == 'mas_3_anos': titulo_lista = "Posiciones con al menos un Sucesor a +3 años"
            elif modo == 'sin_sucesor': titulo_lista = "Posiciones Sin Sucesor Identificado"
                
            lista_sucesores = []
            for _, r in df_posiciones_filtradas.iterrows():
                pos = clean_text(r.get('Nombre de la Posición', ''))
                ocupante = clean_text(r.get('Nombre', ''))
                sucs, reads = [], []
                for i in range(1, 6):
                    c_suc = buscar_columna(df_posiciones_filtradas.columns, 'sucesor', i)
                    c_read = buscar_columna(df_posiciones_filtradas.columns, 'readiness', i)
                    sucs.append(clean_text(r.get(c_suc, '')) if c_suc else '')
                    reads.append(clean_text(r.get(c_read, '')) if c_read else '')
                
                is_sin_sucesor, has_match = True, False
                for i in range(5):
                    s, read = sucs[i].lower(), reads[i].lower()
                    if s and s not in invalid_sucs_local and "vacante" not in s:
                        is_sin_sucesor = False
                        if modo == 'inmediato' and 'inmediato' in read: has_match = True
                        elif modo == '1_3_anos' and '1 a 3' in read: has_match = True
                        elif modo == 'mas_3_anos' and ('mas de 3' in read or 'más de 3' in read): has_match = True
                if modo == 'sin_sucesor' and is_sin_sucesor: has_match = True
                    
                if has_match:
                    item = {"Posición Crítica": pos, "Ocupante Actual": ocupante}
                    for i in range(5):
                        item[f"Sucesor {i+1}"] = sucs[i] if sucs[i] and sucs[i].lower() not in invalid_sucs_local else ("No definido" if modo=='sin_sucesor' else "Pendiente")
                        item[f"Readiness {i+1}"] = reads[i] if reads[i] and sucs[i].lower() not in invalid_sucs_local else "Pendiente"
                    lista_sucesores.append(item)
            
            df_lista_suc = pd.DataFrame(lista_sucesores)
            if not df_lista_suc.empty:
                for i in [5, 4, 3]: 
                    if all(df_lista_suc[f"Sucesor {i}"] == "Pendiente"): df_lista_suc = df_lista_suc.drop(columns=[f"Sucesor {i}", f"Readiness {i}"])
                    
            with st.container():
                st.markdown(f"#### 📋 {titulo_lista} ({len(df_lista_suc)} positions)")
                if not df_lista_suc.empty: st.dataframe(df_lista_suc, use_container_width=True, hide_index=True)
                else: st.info("No hay registros en esta categoría.")
                if st.button("❌ Cerrar lista", key="cerrar_lista_kpi_read"): st.session_state['filtro_kpi_plan'] = None; st.rerun()

        elif modo in ['todas', 'con_sucesor', 'pendientes']:
            if modo == 'todas': df_mostrar, titulo_lista = df_posiciones_filtradas, "Todas las Posiciones Críticas"
            elif modo == 'con_sucesor': df_mostrar, titulo_lista = df_posiciones_filtradas[df_posiciones_filtradas['Cat_Sucesion'] != 'pendiente'], "Posiciones con Mapeo Definido"
            else: df_mostrar, titulo_lista = df_posiciones_filtradas[df_posiciones_filtradas['Cat_Sucesion'] == 'pendiente'], "Posiciones Pendientes de Sucesor"
                
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
    pos_series = df_posiciones_filtradas['Nombre de la Posición'].dropna().astype(str).str.strip()
    posiciones_opciones = pos_series[pos_series != ''].drop_duplicates().tolist()
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
            if not any(d in dir_candidato.upper() for d in lista_dirs_perm): return "RESTRINGIDO_GLOBAL"
        
        if st.session_state.get('lider_permitido', "TODOS") != "TODOS" and nombre_cand.strip().lower() not in st.session_state['nombres_permitidos_limpios']:
            return "RESTRINGIDO_LIDER_CUENTA"
            
        if f_lid_plan != "Todos" and nombre_cand.strip().lower() not in subordinados_nombres_limpios: return "RESTRINGIDO_LIDER"
            
        puesto_actual = clean_text(row_c.get('Nombre de la Posición'), 'Puesto no asignado')
        nom_cand_limpio = ' '.join(str(nombre_cand).strip().lower().split())
        nom_usr_limpio = ' '.join(str(st.session_state.get("nombre_usuario", "")).strip().lower().split())
        nom_lid_plan_limpio = ' '.join(str(f_lid_plan).strip().lower().split())
        es_admin = (st.session_state.get("id_usuario") == "admin")
        
        es_lider_presentado = (nom_lid_plan_limpio != "todos") and (nom_cand_limpio == nom_lid_plan_limpio)
        es_propia_colab = (not es_admin) and (nom_cand_limpio == nom_usr_limpio)
        ocultar_metricas = es_lider_presentado or es_propia_colab
        
        jer_key_c = next((k for k in row_c.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
        mla_key_c = next((k for k in row.keys() if k and 'nivel mla' in str(k).lower()), 'Nivel MLA')

        if ocultar_metricas: box_c = edr_c = eng_c = mla_c = jer_c = "🔒 Confidencial"
        else:
            box_c = clean_text(row_c.get('Resultado 9 box'), 'Pendiente')
            edr_c = clean_text(row_c.get('EDR', row_c.get('EDR ')), 'Pendiente')
            eng_key = next((k for k in row_c.keys() if k and 'enganche' in str(k).lower()), None)
            eng_c = clean_text(row_c.get(eng_key), 'N/A') if eng_key else 'N/A'
            mla_c = clean_text(row_c.get(mla_key_c, 'N/A'))
            jer_c = clean_text(row_c.get(jer_key_c, 'N/A'))
            
        return {"puesto_actual": puesto_actual, "direccion": dir_candidato, "box": box_c, "enganche": eng_c, "edr": edr_c, "mla": mla_c, "jerarquia": jer_c}
    
    def generar_sugerencias_ia(pos_destino, info_pos_destino):
        if not pos_destino or df_completo.empty: return []
        jer_key_dest = next((k for k in info_pos_destino.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
        mla_destino = clean_text(info_pos_destino.get(jer_key_dest, ''))
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
            
            jer_key_cand = next((k for k in row.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
            mla_cand = clean_text(row.get(jer_key_cand, ''))
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

    def mostrar_ficha_mini(nombre_cand, df_db):
        if not nombre_cand or nombre_cand in ["Pendiente", "Vacante / Sin asignar", "No definido", "Sin sucesor identificado"]: st.info("Sin información de ocupante"); return
        match = df_db[df_db['Nombre_Cruce'] == nombre_cand.strip().lower()]
        if match.empty: st.warning("Colaborador no encontrado en la base."); return
        row = match.iloc[0]
        def get_nom(val): return dict_nom_global.get(clean_id(val), val)
        
        puesto = clean_text(row.get('Nombre de la Posición', 'N/A'))
        lider = get_nom(row.get('ID Del Jefe', ''))
        dir_c = clean_text(row.get('Dirección', row.get('Direccion', 'N/A')))
        
        nom_cand_limpio = ' '.join(str(nombre_cand).strip().lower().split())
        nom_usr_limpio = ' '.join(str(st.session_state.get("nombre_usuario", "")).strip().lower().split())
        nom_lid_plan_limpio = ' '.join(str(f_lid_plan).strip().lower().split())
        es_admin = (st.session_state.get("id_usuario") == "admin")
        
        es_lider_presentado = (nom_lid_plan_limpio != "todos") and (nom_cand_limpio == nom_lid_plan_limpio)
        es_propia_colab = (not es_admin) and (nom_cand_limpio == nom_usr_limpio)
        ocultar_metricas = es_lider_presentado or es_propia_colab
        
        jer_key_c = next((k for k in row.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
        mla_key_c = next((k for k in row.keys() if k and 'nivel mla' in str(k).lower()), 'Nivel MLA')

        if ocultar_metricas: box_c = edr_c = eng_c = mla_c = jer_c = "🔒 Confidencial"
        else:
            box_c = clean_text(row.get('Resultado 9 box'), 'Pendiente')
            edr_c = clean_text(row.get('EDR', row.get('EDR ')), 'Pendiente')
            eng_key = next((k for k in row.keys() if k and 'enganche' in str(k).lower()), None)
            eng_c = clean_text(row.get(eng_key), 'N/A') if eng_key else 'N/A'
            mla_c = clean_text(row.get(mla_key_c, 'N/A'))
            jer_c = clean_text(row.get(jer_key_c, 'N/A'))
        
        c_suc_temp = buscar_columna(row.index, 'sucesor', 1)
        suc1 = get_nom(row.get(c_suc_temp, '')) if c_suc_temp else 'Pendiente'
        c_read_temp = buscar_columna(row.index, 'readiness', 1)
        read1 = clean_text(row.get(c_read_temp, '')) if c_read_temp else ''
        
        st.markdown(f"""
        <div style='padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px; font-family: sans-serif; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 10px;'>
            <h4 style='margin-top: 0; color: #1e3a8a; font-size: 18px;'>{nombre_cand}</h4>
            <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Puesto:</b> {puesto}</p>
            <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Líder:</b> {lider}</p>
            <p style='margin: 2px 0; font-size: 13px; color: #475569;'><b>Dirección:</b> {dir_c}</p>
            <hr style='margin: 10px 0; border: 0; border-top: 1px dashed #cbd5e1;'>
            <div style='display: flex; gap: 8px; margin-bottom: 10px;'>
                <span style='background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>Jerarquía: {jer_c}</span>
                <span style='background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>MLA: {mla_c}</span>
                <span style='background: #f1f5f9; color: #334155; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>9-BOX: {box_c}</span>
                <span style='background: #f1f5f9; color: #334155; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>EDR: {edr_c}</span>
            </div>
            <p style='margin: 0; font-size: 13px; color: #b91c1c;'><b>🔥 Enganche Individual:</b> {eng_c}</p>
            <p style='margin: 6px 0 0 0; font-size: 13px; color: #4338ca;'><b>🥇 Sucesor 1:</b> {suc1 if suc1 else 'Pendiente'} <span style='font-size:11px; color:#64748b;'>{read1}</span></p>
        </div>
        """, unsafe_allow_html=True)

    if pos_seleccionada:
        df_ocupantes = df_posiciones_filtradas[df_posiciones_filtradas['Nombre de la Posición'].apply(clean_text) == pos_seleccionada]
        info_pos = df_ocupantes.iloc[0] 
        nombres_ocupantes = [clean_text(n, 'Vacante / Sin asignar') for n in df_ocupantes['Nombre'].tolist()]
        
        st.markdown(f"#### 📌 Posición Crítica: `{pos_seleccionada}`")
        
        pos_upper = pos_seleccionada.upper()
        if "GERENTE" in pos_upper or "DIRECTOR" in pos_upper or "ABOGADA CORPORATIVA" in pos_upper: nivel_vulnerabilidad = "CRÍTICO 🔴"
        else: nivel_vulnerabilidad = "ALTO 🟠"
            
        st.markdown(f"**Nivel de Vulnerabilidad:** {nivel_vulnerabilidad}")
        
        def leer_campo(keyword, num=None):
            c_name = buscar_columna(info_pos.index, keyword, num)
            if c_name:
                val = info_pos[c_name]
                return clean_text(val) if pd.notna(val) else ""
            return ""
            
        c_riesgo_fuga = leer_campo('riesgo de fuga')
        if not c_riesgo_fuga: c_riesgo_fuga = "Bajo"
        
        st.markdown("##### 🏃‍♂️ Riesgo de Fuga del Ocupante Actual")
        n_riesgo_fuga = st.radio(
            "Selecciona el nivel de riesgo:", 
            ["Bajo", "Medio", "Alto"], 
            index=["Bajo", "Medio", "Alto"].index(c_riesgo_fuga.capitalize()) if c_riesgo_fuga.capitalize() in ["Bajo", "Medio", "Alto"] else 0,
            horizontal=True, key=f"r_fuga_{pos_seleccionada}"
        )
        
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
        
        id_ocupante_actual = clean_id(info_pos.get('id Empleado', ''))
        nombres_empleados_validos = []
        for _, row_emp in df_completo.iterrows():
            e_id = clean_id(row_emp.get('id Empleado', ''))
            e_nom = clean_text(row_emp.get('Nombre', ''))
            if e_id and e_nom and e_id != id_ocupante_actual and not str(e_id).upper().startswith('VAC-'):
                nombres_empleados_validos.append(e_nom)
                
        nombres_empleados_validos = sorted(list(set(nombres_empleados_validos)))
        opciones_sucesores = ["Pendiente", "Sin sucesor identificado"] + nombres_empleados_validos
        opciones_tiempo = ["Pendiente", "Inmediato", "1 a 3 años", "Más de 3 años"]
        
        ph_pos = "Ej. Menciona los logros recientes más destacados, fortalezas clave o competencias técnicas consolidadas..."
        ph_opo = "Ej. ¿Qué brechas de liderazgo, conocimientos técnicos o experiencia necesita cubrir para estar listo?"

        c_suc_emergencia = leer_campo('emergencia') or "Pendiente"
        
        c_sucs = []; c_reads = []; c_pos = []; c_opos = []
        for i in range(1, 6):
            c_sucs.append(leer_campo('sucesor', i) or "Pendiente")
            c_reads.append(leer_campo('readiness', i) or "Pendiente")
            c_pos.append(leer_campo('positivo', i))
            c_opos.append(leer_campo('oportunidad', i))
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
            st.markdown(f"<div style='font-size: 13px; color: #475569; margin-top: -10px; margin-bottom: 8px;'>💼 <b>Puesto Actual:</b> {ficha_emergencia['puesto_actual']}</div>", unsafe_allow_html=True)
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
                    st.markdown(f"<div style='font-size: 13px; color: #475569; margin-top: -10px; margin-bottom: 8px;'>💼 <b>Puesto Actual:</b> {ficha_c['puesto_actual']}</div>", unsafe_allow_html=True)
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
        
        c_plan_accion = leer_campo('comentarios de sucesión', 'comentarios de sucesion') 
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
                    
                    def idx_col_dinamico(kw, num=None):
                        c_name = buscar_columna(headers_bd, kw, num)
                        if c_name: return headers_bd.index(c_name) + 1
                        return None
                    
                    idx_id_empleado = idx_col_dinamico('id empleado')
                    if not idx_id_empleado:
                        raise ValueError("No se encontró la columna 'id Empleado' en la base de datos.")
                        
                    idx_emergencia = idx_col_dinamico('emergencia')
                    idx_plan_accion = idx_col_dinamico('comentarios de')
                    idx_riesgo_fuga = idx_col_dinamico('riesgo de fuga')
                    
                    idxs_sucs = [idx_col_dinamico('sucesor', i) for i in range(1, 6)]
                    idxs_reads = [idx_col_dinamico('readiness', i) for i in range(1, 6)]
                    idxs_pos = [idx_col_dinamico('positivo', i) for i in range(1, 6)]
                    idxs_opos = [idx_col_dinamico('oportunidad', i) for i in range(1, 6)]
                    
                    columna_ids_excel = pestana.col_values(idx_id_empleado)
                    celdas_a_actualizar = []
                    
                    for _, row_ocupante in df_ocupantes.iterrows():
                        id_buscado = clean_id(row_ocupante.get('id Empleado', ''))
                        
                        if id_buscado in columna_ids_excel:
                            fila_real = columna_ids_excel.index(id_buscado) + 1
                        else:
                            st.warning(f"⚠️ El empleado {id_buscado} ya no existe en el Excel. Se omitirá.")
                            continue
                            
                        def agregar_al_batch(col_idx, valor):
                            if col_idx:
                                letra_col = gspread.utils.rowcol_to_a1(fila_real, col_idx)
                                celdas_a_actualizar.append({'range': letra_col, 'values': [[str(valor)]]})
                
                        agregar_al_batch(idx_emergencia, "Pendiente" if n_suc_emergencia == "Pendiente" else n_suc_emergencia)
                        agregar_al_batch(idx_plan_accion, n_plan_accion)
                        agregar_al_batch(idx_riesgo_fuga, n_riesgo_fuga)
                        
                        for i in range(5):
                            agregar_al_batch(idxs_sucs[i], "Pendiente" if n_sucs[i] == "Pendiente" else n_sucs[i])
                            agregar_al_batch(idxs_reads[i], "Pendiente" if n_reads[i] == "Pendiente" else n_reads[i])
                            agregar_al_batch(idxs_pos[i], n_pos_inputs[i])
                            agregar_al_batch(idxs_opos[i], n_opo_inputs[i])
                            
                    if celdas_a_actualizar:
                        pestana.batch_update(celdas_a_actualizar)
                    
                    try: archivo.worksheet("Metadata").update_acell('A1', str(time.time()))
                    except Exception: pass 
                    
                    st.success("✅ ¡Guardado exitosamente y de forma segura! El mapa se está actualizando...")
                    st.cache_data.clear(); st.rerun()
                    
                except Exception as e: st.error(f"❌ Error técnico al intentar escribir en el Excel: {e}")
                
    return f_lid_plan, subordinados_nombres_limpios
