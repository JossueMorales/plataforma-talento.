import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import re

# Importamos las dependencias de interfaz y limpieza que ya tienes
from config_ui import (
    OPCIONES_PYVIS, SCRIPT_ANILLOS, INYECCION_HTML_JS,
    clean_text, clean_id, obtener_color_9box, acortar_nombre, 
    acortar_puesto, get_readiness_val, get_dispersion_offset
)

def buscar_columna(columnas, palabra_clave, numero=None):
    """Busca dinámicamente el nombre de una columna con regex."""
    palabra_limpia = re.sub(r'[^a-z0-9]', '', str(palabra_clave).lower())
    for col in columnas:
        col_limpia = re.sub(r'[^a-z0-9]', '', str(col).lower())
        if palabra_limpia in col_limpia:
            if numero is None or str(numero) in col_limpia:
                return col
    return None

def generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_jerarquia, f_box, f_edr, f_puesto, f_riesgos, renderizar_mapa, usuario_activo_id):
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
        
        jer_key = next((k for k in row_dict.keys() if k and ('jerárquico' in str(k).lower() or 'jerarquico' in str(k).lower())), 'Nivel Jerárquico')
        mla_key = next((k for k in row_dict.keys() if k and 'nivel mla' in str(k).lower()), 'Nivel MLA')
        
        if emp:
            empleados_validos.add(emp)
            G_jerarquia.add_node(emp)
            
            suc1_limpio = buscar_id_real(row_dict.get(buscar_columna(row_dict.keys(), 'sucesor', 1), ''))
            suc2_limpio = buscar_id_real(row_dict.get(buscar_columna(row_dict.keys(), 'sucesor', 2), ''))
            suc3_limpio = buscar_id_real(row_dict.get(buscar_columna(row_dict.keys(), 'sucesor', 3), ''))
            suc4_limpio = buscar_id_real(row_dict.get(buscar_columna(row_dict.keys(), 'sucesor', 4), ''))
            suc5_limpio = buscar_id_real(row_dict.get(buscar_columna(row_dict.keys(), 'sucesor', 5), ''))
            
            info_nodos[emp] = {
                'jerarquia': clean_text(row_dict.get(jer_key, 'N/A')),
                'mla': clean_text(row_dict.get(mla_key, 'N/A')),
                'puesto': clean_text(row_dict.get('Nombre de la Posición')).upper(),
                'direccion': clean_text(row_dict.get('Dirección', row_dict.get('Direccion')), 'No asignada'),
                'box': clean_text(row_dict.get('Resultado 9 box'), 'Pendiente'),
                'edr': clean_text(row_dict.get('EDR', row_dict.get('EDR ')), 'Pendiente'),
                'riesgo_fuga': clean_text(row_dict.get('Riesgo de Fuga', 'Bajo')),
                'lider': nombres_dict.get(jefe, 'Sin Líder') if jefe else 'Sin Líder',
                'critica': clean_text(row_dict.get('Posición Crítica', row_dict.get('Posicion Critica')), 'No'),
                'nombre': clean_text(row_dict.get('Nombre')),
                'interes': clean_text(row_dict.get('Interés del Colaborador'), 'Pendiente'),
                'suc1_id': suc1_limpio, 'read1': clean_text(row_dict.get(buscar_columna(row_dict.keys(), 'readiness', 1)), 'Pendiente'),
                'suc2_id': suc2_limpio, 'read2': clean_text(row_dict.get(buscar_columna(row_dict.keys(), 'readiness', 2)), ''),
                'suc3_id': suc3_limpio, 'read3': clean_text(row_dict.get(buscar_columna(row_dict.keys(), 'readiness', 3)), ''),
                'suc4_id': suc4_limpio, 'read4': clean_text(row_dict.get(buscar_columna(row_dict.keys(), 'readiness', 4)), ''),
                'suc5_id': suc5_limpio, 'read5': clean_text(row_dict.get(buscar_columna(row_dict.keys(), 'readiness', 5)), ''),
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
                
    nombres_con_pdi = set()
    if not df_pdi.empty and 'Nombre' in df_pdi.columns:
        nombres_con_pdi = set(df_pdi['Nombre'].dropna().astype(str).str.strip().str.lower())
        
    for emp, info in info_nodos.items():
        r_list = []
        if info['jerarquia'] != '5':
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
            
            fuga_val = info['riesgo_fuga'].lower()
            if fuga_val == 'alto':
                if es_critica:
                    r_list.append("🔥 Riesgo Operativo Crítico: Titular clave con alta probabilidad de fuga")
                else:
                    r_list.append("🚨 Alerta Alta: Riesgo de Fuga del Titular")
            elif fuga_val == 'medio':
                if es_critica:
                    r_list.append("⚠️ Riesgo Operativo Moderado: Titular clave en riesgo de fuga medio")
                else:
                    r_list.append("⚠️ Precaución: Riesgo de fuga medio")
                
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
    if f_lid:
        lider_ids = [emp for emp, inf in info_nodos.items() if inf['nombre'] in f_lid]
        for l_id in lider_ids:
            descendientes_validos.add(l_id)
            try:
                if l_id in G_jerarquia: descendientes_validos.update(nx.descendants(G_jerarquia, l_id))
            except nx.NetworkXError: pass
                
    nodos_estrictos = set()
    for emp, info in info_nodos.items():
        if info['jerarquia'] == '5': nodos_estrictos.add(emp); continue
        if f_lid and info['nombre'] in f_lid: nodos_estrictos.add(emp); continue
        if f_dir and info['direccion'] not in f_dir: continue
        if f_lid and emp not in descendientes_validos: continue
        if f_crit and info['critica'] not in f_crit: continue
        if f_jerarquia and info['jerarquia'] not in f_jerarquia: continue
        if f_box and info['box'] not in f_box: continue
        if f_edr and info['edr'] not in f_edr: continue
        if f_puesto and info['puesto'].strip().upper() not in [p.strip().upper() for p in f_puesto]: continue
        if f_riesgos and not info['riesgos_lista']: continue
        nodos_estrictos.add(emp)
        
    nodos_rescatados = set(nodos_estrictos)
    for emp in nodos_estrictos:
        for s_id in [info_nodos[emp]['suc1_id'], info_nodos[emp]['suc2_id'], info_nodos[emp]['suc3_id'], info_nodos[emp]['suc4_id'], info_nodos[emp]['suc5_id']]:
            if s_id and s_id in info_nodos: nodos_rescatados.add(s_id)
            
    raiz_principal = next((emp for emp, info in info_nodos.items() if info['jerarquia'] == '5'), None)
    if not raiz_principal:
        posibles_raices = [n for n in G_jerarquia.nodes() if G_jerarquia.in_degree(n) == 0]
        if posibles_raices: raiz_principal = max(posibles_raices, key=lambda x: len(nx.descendants(G_jerarquia, x)))
            
    nodo_central_id = raiz_principal
    target_node_id = clean_id(usuario_activo_id)
    if target_node_id in G_jerarquia.nodes():
        nodo_central_id = target_node_id
        
    nodos_activos = set(nodos_rescatados)
    if raiz_principal and raiz_principal in G_jerarquia:
        for v in nodos_rescatados:
            if v in G_jerarquia:
                try: nodos_activos.update(nx.ancestors(G_jerarquia, v))
                except nx.NetworkXError: pass
                    
    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia
    
    def obtener_anillo_estricto(emp_id, depth_arbol):
        jer = str(info_nodos.get(emp_id, {}).get('jerarquia', '')).replace('.0', '').strip() 
        return {'5':0, '4':1, '3':2, '2':3, '1':4}.get(jer, min(depth_arbol, 5))
        
    SEPARACION_ANILLOS = 348 
    conteo_hojas = {}
    
    def calcular_hojas(n):
        hijos = [c for c in Arbol.successors(n) if c in nodos_activos]
        if not hijos:
            val = 1 if n in nodos_rescatados else 0
            conteo_hojas[n] = val
            return val
        total = sum(calcular_hojas(c) for c in hijos)
        if total == 0 and n in nodos_rescatados: total = 1
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
        
    nodos_sin_coords = [n for n in G_jerarquia.nodes() if n not in coords and n in nodos_rescatados]
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
        is_hidden_map = emp not in nodos_rescatados
        is_hidden_kpi = emp not in nodos_estrictos
        
        is_vacante = str(emp).strip().upper().startswith("VAC-")
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden_kpi and not is_vacante:
            es_andres = info['jerarquia'] == '5' or 'ANDRES EDUARDO VILLARREAL' in info['nombre'].upper()
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if not es_andres:
                data_edr.append({"Nombre": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Resultado EDR": info['edr']})
                if info['critica'].lower() == 'si':
                    data_sucesores.append({
                        "Ocupante Actual": info['nombre'], "Posición Crítica": info['puesto'], "Dirección": info['direccion'], 
                        "Sucesor 1": nom_suc1 if nom_suc1 else "Pendiente", "Readiness 1": info['read1'] if info['read1'] else "Pendiente",
                        "Sucesor 2": nom_suc2 if nom_suc2 else "Pendiente", "Readiness 2": info['read2'] if info['read2'] else "Pendiente",
                        "Sucesor 3": nom_suc3 if nom_suc3 else "Pendiente", "Readiness 3": info['read3'] if info['read3'] else "Pendiente"
                    })
                if info['es_lider']: data_enganche.append({"Líder": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A", "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"})
                for r in info['riesgos_lista']: alertas_tabla.append({"Colaborador": info['nombre'], "Líder Directo": info['lider'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Alerta Detectada por IA": r})
            
            if info['box'].lower() not in ['pendiente', 'n/a', 'nan', 'none', '']: data_nueve_box.append({"Nombre": info['nombre'], "Puesto": info['puesto'], "Dirección": info['direccion'], "Resultado 9-Box": info['box']})
            if info['jerarquia'] == '1': data_operativos.append(nodo_data)
                
        prefijo = "🚨 " if info['riesgos_lista'] else ""
        coord_data = coords.get(emp, {'angle':0, 'nivel_calculado':5, 'profundidad':5, 'anillo_real': 5})
        
        eng = info['enganche_ind']
        color_sombreado = 'rgba(22, 163, 74, 0.8)' if eng >= 4 else ('rgba(234, 179, 8, 0.8)' if eng >= 3 else ('rgba(249, 115, 22, 0.8)' if eng >= 2 else ('rgba(220, 38, 38, 0.8)' if eng > 0 else 'rgba(0, 0, 0, 0.2)')))
        dispersion_offset = (((sum(ord(ch) for ch in str(emp)) % 9) / 8.0) * 0.4) - 0.2 
        
        shape_nodo = 'square' if is_vacante else 'dot'
        color_nodo = '#94a3b8' if is_vacante else obtener_color_9box(info['box'])
        
        G.add_node(
            emp, label=f"{prefijo}{acortar_nombre(info['nombre'])}\n({acortar_puesto(info['puesto'])})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small><br><small>Riesgo de Fuga: {info['riesgo_fuga']}</small></div>", 
            size=28 if emp == raiz_principal else 18, color=color_nodo, shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, 
            shape=shape_nodo, group=info['jerarquia'], Nivel_Jerarquico=info['jerarquia'], Nivel_MLA=info['mla'], Resultado_9Box=info['box'], EDR=info['edr'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], Riesgo_Fuga=info['riesgo_fuga'],
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'], Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'}, Angle=coord_data['angle'], NivelCalculado=coord_data.get('nivel_calculado', 5), Dispersion=dispersion_offset, AnilloReal=coord_data.get('anillo_real', 5), hidden=is_hidden_map,
            borderWidth=2 if is_vacante else 1, shapeProperties={'borderDashes': [5, 5]} if is_vacante else {}
        )
        
    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_rescatados or emp not in nodos_rescatados
        eng_emp = info_nodos[emp]['enganche_ind']
        color_edge_shadow = 'rgba(22, 163, 74, 0.8)' if eng_emp >= 4 else ('rgba(234, 179, 8, 0.8)' if eng_emp >= 3 else ('rgba(249, 115, 22, 0.8)' if eng_emp >= 2 else ('rgba(220, 38, 38, 0.8)' if eng_emp > 0 else 'rgba(0, 0, 0, 0.0)')))
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False, shadow={'enabled': True, 'color': color_edge_shadow, 'size': 15, 'x': 0, 'y': 0})
        
    for emp, info in info_nodos.items():
        box = info['box'].upper()
        if box in ['5', '2']:
            j1 = obtener_jefe_nivel_arriba(emp, 1)
            if j1: G.add_edge(emp, j1, color='#22c55e', width=3, dashes=[5,5], title='Proyección N+1', hidden=(emp not in nodos_rescatados or j1 not in nodos_rescatados), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.2})
        if box in ['1', '3']:
            j2 = obtener_jefe_nivel_arriba(emp, 2)
            if j2: G.add_edge(emp, j2, color='#166534', width=3.5, dashes=[5,5], title='Proyección N+2', hidden=(emp not in nodos_rescatados or j2 not in nodos_rescatados), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.3})
            
        for s_id, read_time in [(info['suc1_id'], info['read1']), (info['suc2_id'], info['read2']), (info['suc3_id'], info['read3']), (info['suc4_id'], info['read4']), (info['suc5_id'], info['read5'])]:
            if s_id and s_id in empleados_validos:
                is_hidden_edge = (emp not in nodos_rescatados or s_id not in nodos_rescatados)
                val = get_readiness_val(read_time)
                dashes_style = False if val == 1 else ([10, 10] if val == 2 else [4, 8])
                edge_width = 6 if val == 1 else (4 if val == 2 else 2)
                G.add_edge(emp, s_id, color='#9c27b0', width=edge_width, dashes=dashes_style, title=f'🎯 Sucesor: {read_time}', hidden=is_hidden_edge, is_struct=False, is_9box=False, is_succ=True, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.6})
                
    eng_list = [info_nodos[n]['enganche_ind'] for n in nodos_estrictos if info_nodos[n]['enganche_ind'] > 0 and 'ANDRES EDUARDO VILLARREAL' not in info_nodos[n]['nombre'].upper() and not str(n).upper().startswith("VAC-")]
    avg_enganche = round(sum(eng_list) / len(eng_list), 1) if eng_list else 0.0
    
    kpis = {
        'total': len(data_total), 'sucesores': len(data_sucesores), 'nueve_box_count': len(data_nueve_box),
        'alertas': len(alertas_tabla), 'enganche_promedio': avg_enganche, 'edr_count': len(data_edr), 'operativos': len(data_operativos),
        'data_total': data_total, 'data_sucesores': data_sucesores, 'data_nueve_box': data_nueve_box, 'data_operativos': data_operativos,
        'data_alertas': [{"Nombre": a['Colaborador'], "Dirección": a['Dirección'], "Puesto": a['Puesto'], "Alerta": a['Alerta Detectada por IA']} for a in alertas_tabla],
        'data_enganche': data_enganche, 'data_edr': data_edr,
        'nodos_visibles_ids': list(nodos_estrictos)
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
