import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components

# ==========================================
# SISTEMA DE SEGURIDAD Y LOGIN (SIMULADO)
# ==========================================
USUARIOS_AUTORIZADOS = {
    "admin": {"nombre": "Administrador Global", "password": "admin", "direccion": "TODAS"},
    "d.comercial": {"nombre": "Director Comercial", "password": "123", "direccion": "DIRECCIÓN COMERCIAL"},
    "d.rh": {"nombre": "Director de Recursos Humanos", "password": "123", "direccion": "RECURSOS HUMANOS"}
}

def login():
    st.set_page_config(page_title="Plataforma de Talento", layout="wide")
    
    if "usuario_logueado" not in st.session_state:
        st.session_state["usuario_logueado"] = False

    if not st.session_state["usuario_logueado"]:
        st.markdown("<h1 style='text-align: center; color: #1976d2;'>🔐 Portal de Talento SaaS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Inicia sesión para acceder al mapa organizacional</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.write("")
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Iniciar Sesión", use_container_width=True):
                if usuario in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario]["password"] == password:
                    st.session_state["usuario_logueado"] = True
                    st.session_state["nombre_usuario"] = USUARIOS_AUTORIZADOS[usuario]["nombre"]
                    st.session_state["id_usuario"] = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

# ==========================================
# MOTOR DEL MAPA ORGANIZACIONAL (BACKEND)
# ==========================================
def generar_mapa_html(url_sheets, direccion_permitida):
    if "/edit" in url_sheets:
        csv_url = url_sheets.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = url_sheets
        
    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        return f"<div style='color:red;'>Error al leer el archivo: {e}</div>", None, None

    df.columns = [str(col).strip() for col in df.columns]

    if direccion_permitida != "TODAS":
        es_del_area = df['Dirección'].astype(str).str.upper().str.contains(direccion_permitida)
        es_raiz = df['Nivel MLA'].astype(str).str.strip() == '5'
        df = df[es_del_area | es_raiz]
        if df.empty:
            return f"<div style='padding:50px; text-align:center;'><h3>No hay datos para la {direccion_permitida}</h3></div>", None, None

    G = nx.MultiDiGraph()
    G_jerarquia = nx.DiGraph() 

    def clean_id(val):
        if pd.isna(val): return ''
        v = str(val).strip()
        if v.endswith('.0'): return v[:-2]
        return v

    def clean_text(val, default=''):
        if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
            return default
        return str(val).strip()

    # COLORES MÁS VIBRANTES (Alto Contraste)
    def obtener_color_9box(valor):
        v = str(valor).strip().upper()
        if v in ['9', '7A', '7B', '7']: return '#dc2626' # Rojo Intenso
        elif v == '4': return '#2563eb' # Azul Intenso
        elif v == '6': return '#ca8a04' # Mostaza Intenso
        elif v in ['5', '2']: return '#16a34a' # Verde Intenso
        elif v in ['1', '3']: return '#14532d' # Verde Oscuro
        else: return '#94a3b8' # Gris Frío

    jefes_dict = {}
    empleados_validos = set()
    info_nodos = {}
    
    direcciones_unicas = set()
    mlas_unicos = set()
    box_unicos = set()
    lideres_unicos = set()
    criticas_unicas = set()
    
    nombres_dict = {}
    for index, row in df.iterrows():
        emp = clean_id(row['id Empleado'])
        if emp:
            nombres_dict[emp] = str(row.get('Nombre', '')).strip()
            
    for index, row in df.iterrows():
        emp = clean_id(row['id Empleado'])
        jefe = clean_id(row['ID Del Jefe'])
        
        direccion = clean_text(row.get('Dirección', row.get('Direccion')), 'No asignada')
        mla = clean_text(row.get('Nivel MLA'), 'N/A')
        box = clean_text(row.get('Resultado 9 box'), 'Pendiente')
        critica = clean_text(row.get('Posición Crítica', row.get('Posicion Critica')), 'No')
        
        nombre_lider = nombres_dict.get(jefe, 'Sin Líder') if jefe not in ['', 'NAN', 'NONE'] else 'Sin Líder'
        
        if emp not in ['', 'NAN', 'NONE']:
            empleados_validos.add(emp)
            G_jerarquia.add_node(emp)
            
            info_nodos[emp] = {
                'mla': mla,
                'puesto': clean_text(row.get('Nombre de la Posición')).upper(),
                'direccion': direccion,
                'box': box,
                'lider': nombre_lider,
                'critica': critica,
                'nombre': clean_text(row.get('Nombre')),
                'interes': clean_text(row.get('Interés del Colaborador'), 'Pendiente'),
                'suc1': clean_text(row.get('Sucesor P.1'), 'Pendiente'),
                'read1': clean_text(row.get('Tiempo de Readiness 1'), 'Pendiente'),
                'suc2': clean_text(row.get('Sucesor P.2')),
                'read2': clean_text(row.get('Tiempo de Readiness 2')),
                'suc3': clean_text(row.get('Sucesor P.3')),
                'read3': clean_text(row.get('Tiempo de Readiness 3'))
            }
            
            if direccion != 'No asignada': direcciones_unicas.add(direccion)
            if mla and mla.lower() != 'nan': mlas_unicos.add(mla)
            if box and box.lower() != 'nan': box_unicos.add(box)
            lideres_unicos.add(nombre_lider)
            criticas_unicas.add(critica)
            
            if jefe not in ['', 'NAN', 'NONE']:
                jefes_dict[emp] = jefe
                G_jerarquia.add_edge(jefe, emp)

    def obtener_jefe_nivel_arriba(emp_id, niveles):
        actual = emp_id
        for _ in range(niveles):
            if actual not in jefes_dict:
                return None
            actual = jefes_dict[actual]
        return actual

    reportes_directos = {n: 0 for n in G_jerarquia.nodes()}
    for jefe, emp in G_jerarquia.edges():
        reportes_directos[jefe] += 1

    sucesores_de = {n: 0 for n in G_jerarquia.nodes()}
    for index, row in df.iterrows():
        emp = clean_id(row['id Empleado'])
        resultado_9box = str(row.get('Resultado 9 box', '')).strip().upper()
        if resultado_9box in ['5', '2']: 
            jefe1 = obtener_jefe_nivel_arriba(emp, 1)
            if jefe1: sucesores_de[jefe1] += 1
        if resultado_9box in ['1', '3']:
            jefe2 = obtener_jefe_nivel_arriba(emp, 2)
            if jefe2: sucesores_de[jefe2] += 1

    raiz_principal = None
    for emp, info in info_nodos.items():
        if info['mla'] == '5':
            raiz_principal = emp
            break 
    if not raiz_principal:
        posibles_raices = [n for n in G_jerarquia.nodes() if G_jerarquia.in_degree(n) == 0]
        if posibles_raices:
            raiz_principal = max(posibles_raices, key=lambda x: len(nx.descendants(G_jerarquia, x)))

    if raiz_principal:
        Arbol = nx.bfs_tree(G_jerarquia, raiz_principal)
    else:
        Arbol = G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        info = info_nodos.get(emp_id, {})
        mla = info.get('mla', '')
        if mla == '5': return 0
        elif mla == '4': return 1 
        elif mla == '3': return 2 
        elif mla == '2': return 3 
        elif mla == '1': return 4 
        return min(depth_arbol, 5)

    conteo_hojas = {}
    def calcular_hojas(n):
        hijos = list(Arbol.successors(n))
        if not hijos:
            conteo_hojas[n] = 1
            return 1
        total = sum(calcular_hojas(c) for c in hijos)
        conteo_hojas[n] = total
        return total

    if raiz_principal:
        calcular_hojas(raiz_principal)

    coords = {}
    SEPARACION_ANILLOS = 1000 
    def asignar_coordenada_radial(nodo, angulo_inicio, angulo_fin):
        hijos = list(Arbol.successors(nodo))
        if not hijos: return
        hojas_totales = sum(conteo_hojas.get(c, 1) for c in hijos)
        angulo_actual = angulo_inicio
        for i, c in enumerate(hijos):
            rebanada = (conteo_hojas.get(c, 1) / hojas_totales) * (angulo_fin - angulo_inicio)
            angulo_hijo = angulo_actual + (rebanada / 2)
            profundidad = nx.shortest_path_length(Arbol, raiz_principal, c) if raiz_principal and c in Arbol else 5
            anillo_real = obtener_anillo_estricto(c, profundidad)
            radio_final = (anillo_real * SEPARACION_ANILLOS) + (profundidad * 120) if anillo_real != 0 else 0
            coords[c] = {
                'x': radio_final * math.cos(angulo_hijo), 'y': radio_final * math.sin(angulo_hijo),
                'angle': angulo_hijo, 'anillo_real': anillo_real, 'profundidad': profundidad
            }
            asignar_coordenada_radial(c, angulo_actual, angulo_actual + rebanada)
            angulo_actual += rebanada

    if raiz_principal:
        coords[raiz_principal] = {'x': 0, 'y': 0, 'angle': 0, 'anillo_real': 0, 'profundidad': 0}
        asignar_coordenada_radial(raiz_principal, 0, 2 * math.pi)

    alertas_tabla = []

    for index, row in df.iterrows():
        try:
            id_empleado = clean_id(row['id Empleado'])
            if not id_empleado: continue
                
            info = info_nodos.get(id_empleado, {})
            nombre = info.get('nombre', 'Desconocido')
            puesto = info.get('puesto', '')
            nivel_mla = info.get('mla', 'N/A')
            resultado_9box = info.get('box', 'Pendiente')
            direccion = info.get('direccion', 'No asignada')
            lider = info.get('lider', 'Sin Líder')
            critica = info.get('critica', 'No')
            
            interes = info.get('interes', 'Pendiente')
            suc1 = info.get('suc1', 'Pendiente')
            read1 = info.get('read1', 'Pendiente')
            suc2 = info.get('suc2', '')
            read2 = info.get('read2', '')
            suc3 = info.get('suc3', '')
            read3 = info.get('read3', '')
            
            riesgos_lista = []
            
            es_critica = (critica.lower() == 'si')
            tiene_oficial = (suc1.lower() != 'pendiente' and suc1 != '')
            tiene_hipos_9box = (sucesores_de.get(id_empleado, 0) > 0)
            
            if es_critica:
                if not tiene_oficial and not tiene_hipos_9box:
                    riesgos_lista.append("🔥 Riesgo Crítico: Sin Sucesor ni HiPos")
                elif not tiene_oficial and tiene_hipos_9box:
                    riesgos_lista.append("⚠️ Sugerencia: HiPo disponible, falta oficializar")
                    
            reps = reportes_directos.get(id_empleado, 0)
            if reps >= 12: riesgos_lista.append(f"⚠️ Sobrecarga ({reps} reportes)")
            elif reps == 1: riesgos_lista.append("⚠️ Ineficiencia (1 reporte)")
                
            for r in riesgos_lista:
                alertas_tabla.append({
                    "Colaborador": nombre,
                    "Puesto": puesto,
                    "Dirección": direccion,
                    "Alerta Detectada por IA": r
                })

            riesgos_str = " | ".join(riesgos_lista) if riesgos_lista else "Ninguno"
            prefijo = "🚨 " if riesgos_lista else ""

            coord_data = coords.get(id_empleado, {'x':5000, 'y':5000, 'angle':0, 'anillo_real':5, 'profundidad':5})
            tamaño_nodo = 35 if id_empleado == raiz_principal else 22
            etiqueta_visible = f"{prefijo}{nombre}\n({puesto})"
            tooltip_html = f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{nombre}</b></div>"
            color_nodo = obtener_color_9box(resultado_9box)

            G.add_node(
                id_empleado, label=etiqueta_visible, title=tooltip_html, size=tamaño_nodo, color=color_nodo, 
                shape='dot', group=nivel_mla, Nivel_MLA=nivel_mla, Resultado_9Box=resultado_9box, 
                Direccion=direccion, Lider=lider, Critica=critica, Nombre=nombre, Puesto=puesto, Riesgos=riesgos_str,
                Interes=interes, Suc1=suc1, Read1=read1, Suc2=suc2, Read2=read2, Suc3=suc3, Read3=read3,
                # AQUI AGREGAMOS LA FUENTE DE ALTO CONTRASTE CON HALO BLANCO
                font={'color': '#0f172a', 'strokeWidth': 4, 'strokeColor': '#ffffff', 'size': 12, 'face': 'Arial', 'weight': 'bold'},
                x=coord_data['x'], y=coord_data['y'], 
                Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad']
            )
        except: pass

    for index, row in df.iterrows():
        try:
            id_empleado = clean_id(row['id Empleado'])
            id_jefe = clean_id(row['ID Del Jefe'])
            res_9box = str(row.get('Resultado 9 box', '')).strip().upper()
            if not id_empleado: continue
            if id_jefe in empleados_validos:
                # Líneas grises más oscuras para mayor contraste
                G.add_edge(id_jefe, id_empleado, color='#94a3b8', width=2, dashes=False, is_jump=False)
            if res_9box in ['5', '2']:
                G.add_edge(id_empleado, obtener_jefe_nivel_arriba(id_empleado, 1), color='#22c55e', width=3, dashes=True, title='Proyección N+1', is_jump=True)
            if res_9box in ['1', '3']:
                G.add_edge(id_empleado, obtener_jefe_nivel_arriba(id_empleado, 2), color='#166534', width=3.5, dashes=True, title='Proyección N+2', is_jump=True)
        except: pass

    kpis = {
        'total': len(empleados_validos),
        'criticas': sum(1 for v in info_nodos.values() if v['critica'].lower() == 'si'),
        'sucesores': sum(1 for v in info_nodos.values() if v['suc1'].lower() not in ['pendiente', '', 'nan']),
        'operativos': sum(1 for v in info_nodos.values() if v['mla'] == '1')
    }
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    
    # AQUI AGREGAMOS SOMBRAS Y BORDES A LOS NODOS
    net.set_options("""
    var options = {
      "nodes": {
          "borderWidth": 2,
          "shadow": {"enabled": true, "color": "rgba(0,0,0,0.25)", "size": 8, "x": 3, "y": 3}
      },
      "physics": {"enabled": false, "forceAtlas2Based": {"gravitationalConstant": -150, "centralGravity": 0.01, "springLength": 250, "springConstant": 0.08, "avoidOverlap": 0.5}, "solver": "forceAtlas2Based"},
      "edges": {"smooth": {"enabled": true, "type": "continuous", "roundness": 0.2}},
      "interaction": {"hover": true, "tooltipDelay": 200}
    }
    """)
    
    html = net.generate_html()
    
    script_anillos = """
    <script>
    window.onionMode = true; 
    window.ringSpacing = 1000; 
    network.on("beforeDrawing", function(ctx) {
        if (!window.onionMode) return; 
        ctx.save(); 
        var nodos_visibles = network.body.data.nodes.get().filter(n => n.hidden !== true);
        var max_nivel_visible = 0;
        var paso = window.ringSpacing; 
        nodos_visibles.forEach(function(n) {
            if(n.AnilloReal !== undefined) { if (n.AnilloReal > max_nivel_visible) { max_nivel_visible = n.AnilloReal; } }
        });
        var limite_anillos = Math.max(max_nivel_visible, 1);
        ctx.strokeStyle = '#cbd5e1'; ctx.setLineDash([8, 8]); ctx.lineWidth = 2; ctx.font = "bold 24px Arial"; ctx.fillStyle = "#64748b"; ctx.textAlign = "center";
        for (var i = 1; i <= limite_anillos; i++) {
            if (i > 5) break; 
            var r = i * paso; ctx.beginPath(); ctx.arc(0, 0, r, 0, 2 * Math.PI); ctx.stroke();
            var etiqueta = "";
            if (i === 1) etiqueta = "Gerentes (Nivel MLA 4)"; else if (i === 2) etiqueta = "Mandos Medios (Nivel MLA 3)"; else if (i === 3) etiqueta = "Analistas (Nivel MLA 2)"; else if (i === 4) etiqueta = "Operativos (Nivel MLA 1)";
            if (etiqueta !== "") { ctx.fillText(etiqueta, 0, -r - 15); }
        }
        ctx.setLineDash([]); ctx.restore(); 
    });
    </script>
    """
    
    opciones_direccion = "".join([f'<option value="{x}">{x}</option>' for x in sorted(direcciones_unicas)])
    opciones_mla = "".join([f'<option value="{x}">{x}</option>' for x in sorted(mlas_unicos)])
    opciones_box = "".join([f'<option value="{x}">{x}</option>' for x in sorted(box_unicos)])
    opciones_lider = "".join([f'<option value="{x}">{x}</option>' for x in sorted(lideres_unicos)])
    opciones_critica = "".join([f'<option value="{x}">{x}</option>' for x in sorted(criticas_unicas)])
    
    boton_html = f"""
    <div id="fichaLateral" style="position: absolute; top: 0; left: -400px; width: 340px; height: 100vh; background: white; box-shadow: 2px 0 15px rgba(0,0,0,0.15); transition: left 0.3s ease; z-index: 10000; font-family: Arial, sans-serif; display: flex; flex-direction: column;">
        <div style="background: #1976d2; padding: 20px; color: white; position: relative; flex-shrink: 0;">
            <button onclick="cerrarFicha()" style="position: absolute; top: 15px; right: 15px; background: transparent; border: none; color: white; font-size: 20px; cursor: pointer;">&times;</button>
            <h2 id="fNombre" style="margin: 0; font-size: 20px; padding-right: 20px;">Nombre</h2>
            <p id="fPuesto" style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Puesto</p>
        </div>
        <div style="padding: 20px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; flex-grow: 1; padding-bottom: 50px;">
            <div style="background: #ffebee; padding: 10px; border-radius: 5px; border-left: 4px solid #d32f2f;">
                <span style="font-size: 12px; color: #d32f2f; font-weight: bold; text-transform: uppercase;">Alertas de RH</span><br>
                <span id="fRiesgos" style="font-size: 14px; color: #b71c1c; font-weight: bold;">-</span>
            </div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">LÍDER DIRECTO</span><br><span id="fLider" style="font-size: 14px; color: #333;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">DIRECCIÓN</span><br><span id="fDireccion" style="font-size: 14px; color: #333;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">POSICIÓN CRÍTICA</span><br><span id="fCritica" style="font-size: 14px; color: #333;">-</span></div>
            <div style="display: flex; gap: 20px;">
                <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
                <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
            </div>
            
            <hr style="border: 0; border-top: 2px dashed #ddd; margin: 10px 0;">
            <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">📈 Plan de Sucesión</div>
            <div><span style="font-size: 11px; color: #777; font-weight: bold;">INTERÉS DEL COLABORADOR</span><br><span id="fInteres" style="font-size: 14px; color: #333; font-weight:bold;">-</span></div>
            
            <div id="divSucesor1" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #1976d2;">
                <span style="font-size: 11px; color: #555; font-weight: bold;">OPCIÓN DE SUCESIÓN 1</span><br>
                <span id="fSuc1" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
                <span id="fRead1" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
            </div>
            
            <div id="divSucesor2" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #81c784; display:none;">
                <span style="font-size: 11px; color: #555; font-weight: bold;">OPCIÓN DE SUCESIÓN 2</span><br>
                <span id="fSuc2" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
                <span id="fRead2" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
            </div>
            
            <div id="divSucesor3" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #fbc02d; display:none;">
                <span style="font-size: 11px; color: #555; font-weight: bold;">OPCIÓN DE SUCESIÓN 3</span><br>
                <span id="fSuc3" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
                <span id="fRead3" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
            </div>
        </div>
    </div>
    <div style="position: absolute; bottom: 30px; right: 30px; z-index: 9999; background: white; border-radius: 8px; box-shadow: 0px 8px 20px rgba(0,0,0,0.25); border-left: 5px solid #1976d2; font-family: Arial, sans-serif; overflow: hidden; width: 280px;">
        <div style="padding: 12px 15px; background: #f8f9fa; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eaeaea;" onclick="toggleFiltrosPanel()">
            <h3 style="margin: 0; font-size: 15px; color: #333;">Filtros y Controles</h3><span id="iconoFiltro" style="font-size: 12px; color: #666;">▼ Ocultar</span>
        </div>
        <div id="cuerpoFiltros" style="padding: 15px; display: flex; flex-direction: column; gap: 8px; max-height: 70vh; overflow-y: auto;">
            <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; background: #e3f2fd; padding: 8px; border-radius: 5px; color: #1565c0;">
                <input type="checkbox" id="toggleOnion" checked onchange="toggleLayoutMode()" style="width: 18px; height: 18px;"> 🎯 Modo Cebolla (Radial)
            </label>
            <div id="sliderContainer" style="transition: 0.3s;">
                <label style="font-size: 13px; font-weight: bold; color: #555;">Amplitud Radial:</label>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <input type="range" id="sliderSeparacion" min="100" max="1500" value="1000" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                    <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">1000px</span>
                </div>
            </div>
            <hr style="margin: 5px 0; border: 0; border-top: 1px dashed #ccc;">
            <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; color: #d32f2f; background: #ffebee; padding: 8px; border-radius: 5px;">
                <input type="checkbox" id="toggleRiesgos" onchange="applyFilters()" style="width: 18px; height: 18px;"> 🚨 Mostrar Solo Riesgos
            </label>
            <label style="font-size: 13px; font-weight: bold; color: #555;">Dirección:</label>
            <select id="filterDireccion" onchange="updateLiderDropdown(); applyFilters()" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 100%;">
                <option value="Todos">Todas las Direcciones</option>{opciones_direccion}
            </select>
            <label style="font-size: 13px; font-weight: bold; color: #555;">Líder:</label>
            <select id="filterLider" onchange="applyFilters()" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 100%;">
                <option value="Todos">Todos los Líderes</option>{opciones_lider}
            </select>
            <label style="font-size: 13px; font-weight: bold; color: #555;">Posición Crítica:</label>
            <select id="filterCritica" onchange="applyFilters()" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 100%;">
                <option value="Todos">Todas</option>{opciones_critica}
            </select>
            <label style="font-size: 13px; font-weight: bold; color: #555;">Nivel MLA:</label>
            <select id="filterMLA" onchange="applyFilters()" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 100%;">
                <option value="Todos">Todos los Niveles</option>{opciones_mla}
            </select>
            <label style="font-size: 13px; font-weight: bold; color: #555;">9-Box:</label>
            <select id="filter9Box" onchange="applyFilters()" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 100%;">
                <option value="Todos">Todos los Resultados</option>{opciones_box}
            </select>
            <hr style="margin: 10px 0; border: 0; border-top: 1px solid #ddd;">
            <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" id="toggleNormal" checked onchange="applyFilters()" style="width: 16px; height: 16px;"> 🏢 Mostrar Estructura
            </label>
            <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" id="toggleJumps" checked onchange="applyFilters()" style="width: 16px; height: 16px;"> 🔀 Mostrar Proyecciones
            </label>
            <button onclick="enfocarPantalla()" style="margin-top: 10px; background: #1976d2; color: white; border: none; padding: 10px; border-radius: 5px; font-size: 14px; font-weight: bold; cursor: pointer; width: 100%;">
                🔍 Enfocar Pantalla
            </button>
        </div>
    </div>
    
    <script>
    function toggleLayoutMode() {{
        var isOnion = document.getElementById('toggleOnion').checked;
        window.onionMode = isOnion;
        var slider = document.getElementById('sliderContainer');
        if (isOnion) {{ slider.style.opacity = "1"; slider.style.pointerEvents = "auto"; network.setOptions({{ physics: {{ enabled: false }} }}); updateSpacing(); 
        }} else {{ slider.style.opacity = "0.4"; slider.style.pointerEvents = "none"; network.setOptions({{ physics: {{ enabled: true }} }}); network.redraw(); }}
    }}
    function updateSpacing() {{
        if(!window.onionMode) return; 
        var val = document.getElementById('sliderSeparacion').value;
        window.ringSpacing = parseInt(val);
        document.getElementById('valorSeparacion').innerText = val + "px";
        var allNodes = network.body.data.nodes.get();
        var nodesToUpdate = [];
        for (var i = 0; i < allNodes.length; i++) {{
            var n = allNodes[i];
            if (n.AnilloReal !== undefined && n.Angle !== undefined) {{
                var nuevoRadio = (n.AnilloReal * window.ringSpacing) + (n.Profundidad * 120);
                nodesToUpdate.push({{ id: n.id, x: nuevoRadio * Math.cos(n.Angle), y: nuevoRadio * Math.sin(n.Angle) }});
            }}
        }}
        network.body.data.nodes.update(nodesToUpdate); network.redraw();
    }}
    network.on("click", function (params) {{
        if (params.nodes.length > 0) {{
            var nodeId = params.nodes[0]; var node = network.body.data.nodes.get(nodeId);
            var cleanName = node.Nombre ? node.Nombre.replace("🚨 ", "") : "Desconocido";
            document.getElementById('fNombre').innerText = cleanName;
            document.getElementById('fPuesto').innerText = node.Puesto || "Sin puesto asignado";
            document.getElementById('fLider').innerText = node.Lider || "N/A";
            document.getElementById('fDireccion').innerText = node.Direccion || "N/A";
            document.getElementById('fCritica').innerText = node.Critica || "N/A";
            document.getElementById('fMLA').innerText = node.Nivel_MLA || "N/A";
            document.getElementById('fRiesgos').innerText = node.Riesgos || "Ninguno";
            
            document.getElementById('fInteres').innerText = node.Interes || "Pendiente";
            
            document.getElementById('fSuc1').innerText = node.Suc1 || "Pendiente";
            document.getElementById('fRead1').innerText = node.Read1 && node.Read1 !== 'Pendiente' ? node.Read1 : "Sin tiempo definido";
            
            if(node.Suc2 && node.Suc2 !== "") {{
                document.getElementById('divSucesor2').style.display = "block";
                document.getElementById('fSuc2').innerText = node.Suc2;
                document.getElementById('fRead2').innerText = node.Read2 || "Sin tiempo definido";
            }} else {{
                document.getElementById('divSucesor2').style.display = "none";
            }}
            
            if(node.Suc3 && node.Suc3 !== "") {{
                document.getElementById('divSucesor3').style.display = "block";
                document.getElementById('fSuc3').innerText = node.Suc3;
                document.getElementById('fRead3').innerText = node.Read3 || "Sin tiempo definido";
            }} else {{
                document.getElementById('divSucesor3').style.display = "none";
            }}

            var boxResult = node.Resultado_9Box || "N/A";
            var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult;
            f9Box.style.backgroundColor = node.color || "#eee";
            f9Box.style.color = (boxResult === "4" || boxResult === "9" || boxResult === "7A" || boxResult === "7B") ? "white" : "#333";
            document.getElementById('fichaLateral').style.left = "0px";
        }} else {{ cerrarFicha(); }}
    }});
    function cerrarFicha() {{ document.getElementById('fichaLateral').style.left = "-400px"; }}
    function toggleFiltrosPanel() {{
        var cuerpo = document.getElementById('cuerpoFiltros'); var icono = document.getElementById('iconoFiltro');
        if (cuerpo.style.display === 'none') {{ cuerpo.style.display = 'flex'; icono.innerText = '▼ Ocultar';
        }} else {{ cuerpo.style.display = 'none'; icono.innerText = '▲ Mostrar'; }}
    }}
    function updateLiderDropdown() {{
        var selectedDireccion = document.getElementById('filterDireccion').value;
        var liderSelect = document.getElementById('filterLider'); var currentLider = liderSelect.value;
        var allNodes = network.body.data.nodes.get(); var validLideres = new Set();
        for (var i = 0; i < allNodes.length; i++) {{
            var node = allNodes[i];
            if (selectedDireccion === "Todos" || node.Direccion === selectedDireccion) {{
                if (node.Lider) {{ validLideres.add(node.Lider); }}
            }}
        }}
        liderSelect.innerHTML = '<option value="Todos">Todos los Líderes</option>';
        var sortedLideres = Array.from(validLideres).sort();
        for (var i = 0; i < sortedLideres.length; i++) {{
            var opt = document.createElement('option'); opt.value = sortedLideres[i]; opt.innerHTML = sortedLideres[i]; liderSelect.appendChild(opt);
        }}
        if (validLideres.has(currentLider)) {{ liderSelect.value = currentLider; }} else {{ liderSelect.value = "Todos"; }}
    }}
    function applyFilters() {{
        var showOnlyRiesgos = document.getElementById('toggleRiesgos').checked;
        var selectedLider = document.getElementById('filterLider').value;
        var selectedDireccion = document.getElementById('filterDireccion').value;
        var selectedCritica = document.getElementById('filterCritica').value;
        var selectedMLA = document.getElementById('filterMLA').value;
        var selected9Box = document.getElementById('filter9Box').value;
        var showNormal = document.getElementById('toggleNormal').checked;
        var showJumps = document.getElementById('toggleJumps').checked;
        var allNodes = network.body.data.nodes.get();
        var nodesToUpdate = []; var visibleNodeIds = new Set();
        for (var i = 0; i < allNodes.length; i++) {{
            var node = allNodes[i]; var isVisible = false;
            if (selectedLider !== "Todos" && node.Nombre === selectedLider) {{ isVisible = true;
            }} else {{
                var matchLider = (selectedLider === "Todos") || (node.Lider == selectedLider);
                var matchDireccion = (selectedDireccion === "Todos") || (node.Direccion == selectedDireccion) || (node.Nivel_MLA === "5");
                var matchCritica = (selectedCritica === "Todos") || (node.Critica == selectedCritica);
                var matchMLA = (selectedMLA === "Todos") || (node.Nivel_MLA == selectedMLA);
                var match9Box = (selected9Box === "Todos") || (node.Resultado_9Box == selected9Box);
                isVisible = matchLider && matchDireccion && matchCritica && matchMLA && match9Box;
            }}
            if (showOnlyRiesgos) {{ if (!node.Riesgos || node.Riesgos === "Ninguno") {{ isVisible = false; }} }}
            nodesToUpdate.push({{id: node.id, hidden: !isVisible}});
            if(isVisible) visibleNodeIds.add(node.id);
        }}
        network.body.data.nodes.update(nodesToUpdate);
        var allEdges = network.body.data.edges.get(); var edgesToUpdate = [];
        for (var i = 0; i < allEdges.length; i++) {{
            var edge = allEdges[i];
            var nodesVisible = visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to);
            var edgeVisible = false;
            if (nodesVisible) {{ if (edge.is_jump === true) {{ edgeVisible = showJumps; }} else {{ edgeVisible = showNormal; }} }}
            edgesToUpdate.push({{id: edge.id, hidden: !edgeVisible}});
        }}
        network.body.data.edges.update(edgesToUpdate);
    }}
    function enfocarPantalla() {{ network.fit({{ animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }}); }}
    
    // =========================================================
    // NUEVA MAGIA: ENFOQUE Y ZOOM-OUT PARA QUE NO SE CORTE
    // =========================================================
    setTimeout(function() {{
        network.fit({{ animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }});
        setTimeout(function() {{
            var currentScale = network.getScale();
            network.moveTo({{
                scale: currentScale * 0.75, // Esto aleja la cámara 25% para dejar margen al texto
                animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
            }});
        }}, 900); 
    }}, 1000); 
    // =========================================================
    
    </script>
    """
    
    html = html.replace('</body>', boton_html + '\n' + script_anillos + '\n</body>')
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        
        /* ESTILO PREMIUM PARA LAS TARJETAS DE KPIs */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #2563eb;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            margin-bottom: 12px;
        }
        div[data-testid="metric-container"] label {
            color: #475569 !important;
            font-weight: 600 !important;
        }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #0f172a !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"Bienvenido(a), {st.session_state['nombre_usuario']}")
    with c2:
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state["usuario_logueado"] = False
            st.rerun()
            
    st.divider()

    with st.spinner("Descargando base de datos y aplicando analítica de segmentación..."):
        link_google_sheets = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit?pli=1&gid=0#gid=0"
        
        direccion_permitida = USUARIOS_AUTORIZADOS[st.session_state["id_usuario"]]["direccion"]
        html_mapa, df_alertas, kpis = generar_mapa_html(link_google_sheets, direccion_permitida)
        
        if kpis is not None:
            col_mapa, col_datos = st.columns([7, 3])
            
            with col_mapa:
                components.html(html_mapa, height=750, scrolling=False)
                
            with col_datos:
                st.markdown("### 📊 KPIs de Talento")
                st.markdown(f"*(Basado en permisos de: {direccion_permitida})*")
                st.write("")
                st.metric("Total de Colaboradores", kpis['total'])
                st.metric("Posiciones Críticas", kpis['criticas'])
                st.metric("Sucesores Oficializados", kpis['sucesores'])
                st.metric("Personal Operativo (MLA 1)", kpis['operativos'])
            
            st.divider()
            st.markdown("### 🚨 Resumen de Alertas y Riesgos Detectados")
            
            if not df_alertas.empty:
                st.dataframe(df_alertas, use_container_width=True)
            else:
                st.success("✅ ¡Excelente! No se detectaron alertas de sucesión ni sobrecarga de reportes en esta área.")
        else:
            components.html(html_mapa, height=400)

if __name__ == "__main__":
    main()