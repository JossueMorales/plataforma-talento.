import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components

# ==========================================
# CONSTANTES DE PLANTILLAS (HTML / JS)
# ==========================================
OPCIONES_PYVIS = """
var options = {
  "nodes": {
      "borderWidth": 2,
      "shadow": {"enabled": true, "color": "rgba(0,0,0,0.4)", "size": 10, "x": 3, "y": 3}
  },
  "physics": {
      "enabled": false,
      "forceAtlas2Based": {"gravitationalConstant": -150, "centralGravity": 0.01, "springLength": 250, "springConstant": 0.08, "avoidOverlap": 0.5},
      "solver": "forceAtlas2Based"
  },
  "interaction": {"hover": true, "tooltipDelay": 200}
}
"""

SCRIPT_ANILLOS = """
<script>
window.onionMode = true; 
window.ringSpacing = 1800; 
network.on("beforeDrawing", function(ctx) {
    if (!window.onionMode) return; 
    ctx.save(); 
    var nodos_visibles = network.body.data.nodes.get().filter(n => n.hidden !== true);
    var max_nivel_visible = 0;
    var paso = window.ringSpacing; 
    nodos_visibles.forEach(function(n) {
        var anillo = n.AnilloReal !== undefined ? n.AnilloReal : n.anilloreal;
        if(anillo !== undefined) { if (anillo > max_nivel_visible) { max_nivel_visible = anillo; } }
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

BOTON_HTML = """
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
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">📈 Se perfila para:</div>
        <div><span style="font-size: 11px; color: #777; font-weight: bold;">INTERÉS DEL COLABORADOR</span><br><span id="fInteres" style="font-size: 14px; color: #333; font-weight:bold;">-</span></div>
        <div id="divSucesor1" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #9c27b0;">
            <span style="font-size: 11px; color: #555; font-weight: bold;">OBJETIVO 1</span><br>
            <span id="fSuc1" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
            <span id="fRead1" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
        </div>
        <div id="divSucesor2" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #9c27b0; display:none;">
            <span style="font-size: 11px; color: #555; font-weight: bold;">OBJETIVO 2</span><br>
            <span id="fSuc2" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
            <span id="fRead2" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
        </div>
        <div id="divSucesor3" style="background: #f8f9fa; padding: 8px; border-radius: 6px; border-left: 3px solid #9c27b0; display:none;">
            <span style="font-size: 11px; color: #555; font-weight: bold;">OBJETIVO 3</span><br>
            <span id="fSuc3" style="font-size: 14px; color: #333; font-weight:bold;">-</span><br>
            <span id="fRead3" style="font-size: 13px; color: #555; margin-top:3px; display:inline-block;">-</span>
        </div>
    </div>
</div>

<div style="position: absolute; bottom: 30px; right: 30px; z-index: 9999; background: white; border-radius: 8px; box-shadow: 0px 8px 20px rgba(0,0,0,0.25); border-left: 5px solid #1976d2; font-family: Arial, sans-serif; overflow: hidden; width: 280px;">
    <div style="padding: 12px 15px; background: #f8f9fa; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eaeaea;" onclick="toggleFiltrosPanel()">
        <h3 style="margin: 0; font-size: 15px; color: #333;">Opciones Visuales</h3><span id="iconoFiltro" style="font-size: 12px; color: #666;">▼ Ocultar</span>
    </div>
    <div id="cuerpoFiltros" style="padding: 15px; display: flex; flex-direction: column; gap: 8px; max-height: 70vh; overflow-y: auto;">
        <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; background: #e3f2fd; padding: 8px; border-radius: 5px; color: #1565c0;">
            <input type="checkbox" id="toggleOnion" checked onchange="toggleLayoutMode()" style="width: 18px; height: 18px;"> 🎯 Modo Cebolla (Radial)
        </label>
        <div id="sliderContainer" style="transition: 0.3s;">
            <label style="font-size: 13px; font-weight: bold; color: #555;">Amplitud Radial:</label>
            <div style="display: flex; align-items: center; gap: 10px;">
                <input type="range" id="sliderSeparacion" min="800" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">1800px</span>
            </div>
        </div>
        <hr style="margin: 10px 0; border: 0; border-top: 1px solid #ddd;">
        <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" id="toggleNormal" checked onchange="applyVisualFilters()" style="width: 16px; height: 16px;"> 🏢 Reporte Estructural
        </label>
        <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; color: #9c27b0;">
            <input type="checkbox" id="toggleSucc" onchange="applyVisualFilters()" style="width: 16px; height: 16px;"> 🔀 Rutas de Sucesión
        </label>
        <label style="font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; color: #16a34a;">
            <input type="checkbox" id="toggleJumps" onchange="applyVisualFilters()" style="width: 16px; height: 16px;"> 📈 Proyecciones 9-Box
        </label>
        <button onclick="enfocarPantalla()" style="margin-top: 10px; background: #1976d2; color: white; border: none; padding: 10px; border-radius: 5px; font-size: 14px; font-weight: bold; cursor: pointer; width: 100%;">
            🔍 Centrar Mapa
        </button>
    </div>
</div>

<script>
function toggleLayoutMode() {
    var isOnion = document.getElementById('toggleOnion').checked;
    window.onionMode = isOnion;
    var slider = document.getElementById('sliderContainer');
    if (isOnion) { slider.style.opacity = "1"; slider.style.pointerEvents = "auto"; network.setOptions({ physics: { enabled: false } }); updateSpacing(); 
    } else { slider.style.opacity = "0.4"; slider.style.pointerEvents = "none"; network.setOptions({ physics: { enabled: true } }); network.redraw(); }
}

function updateSpacing() {
    if(!window.onionMode) return; 
    var val = document.getElementById('sliderSeparacion').value;
    window.ringSpacing = parseInt(val);
    document.getElementById('valorSeparacion').innerText = val + "px";
    
    var allNodes = network.body.data.nodes.get();
    var nodesToUpdate = [];
    
    for (var i = 0; i < allNodes.length; i++) {
        var n = allNodes[i];
        
        var anillo = n.AnilloReal !== undefined ? n.AnilloReal : n.anilloreal;
        var angle = n.Angle !== undefined ? n.Angle : n.angle;
        var prof = n.Profundidad !== undefined ? n.Profundidad : n.profundidad;
        
        if (anillo !== undefined && angle !== undefined && prof !== undefined) {
            var nuevoRadio = (anillo * window.ringSpacing) + (prof * 120);
            nodesToUpdate.push({ id: n.id, x: nuevoRadio * Math.cos(angle), y: nuevoRadio * Math.sin(angle) });
        }
    }
    
    network.body.data.nodes.update(nodesToUpdate);
    network.setOptions({ physics: { enabled: true, solver: 'repulsion' } });
    network.redraw();
    network.setOptions({ physics: { enabled: false } });
}

network.on("click", function (params) {
    if (params.nodes.length > 0) {
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
        
        document.getElementById('fSuc1').innerText = node.NomSuc1 || "Pendiente";
        document.getElementById('fRead1').innerText = node.Read1 && node.Read1 !== 'Pendiente' ? node.Read1 : "Sin tiempo definido";
        
        if(node.NomSuc2 && node.NomSuc2 !== "") {
            document.getElementById('divSucesor2').style.display = "block";
            document.getElementById('fSuc2').innerText = node.NomSuc2;
            document.getElementById('fRead2').innerText = node.Read2 || "Sin tiempo definido";
        } else { document.getElementById('divSucesor2').style.display = "none"; }
        
        if(node.NomSuc3 && node.NomSuc3 !== "") {
            document.getElementById('divSucesor3').style.display = "block";
            document.getElementById('fSuc3').innerText = node.NomSuc3;
            document.getElementById('fRead3').innerText = node.Read3 || "Sin tiempo definido";
        } else { document.getElementById('divSucesor3').style.display = "none"; }

        var boxResult = node.Resultado_9Box || "N/A";
        var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult;
        f9Box.style.backgroundColor = node.color || "#eee";
        f9Box.style.color = (boxResult === "4" || boxResult === "9" || boxResult === "7A" || boxResult === "7B") ? "white" : "#333";
        document.getElementById('fichaLateral').style.left = "0px";
    } else { cerrarFicha(); }
});

function cerrarFicha() { document.getElementById('fichaLateral').style.left = "-400px"; }
function toggleFiltrosPanel() {
    var cuerpo = document.getElementById('cuerpoFiltros'); var icono = document.getElementById('iconoFiltro');
    if (cuerpo.style.display === 'none') { cuerpo.style.display = 'flex'; icono.innerText = '▼ Ocultar';
    } else { cuerpo.style.display = 'none'; icono.innerText = '▲ Mostrar'; }
}

function applyVisualFilters() {
    var showNormal = document.getElementById('toggleNormal').checked;
    var showJumps = document.getElementById('toggleJumps').checked;
    var showSucc = document.getElementById('toggleSucc').checked;
    
    var allEdges = network.body.data.edges.get();
    var edgesToUpdate = [];
    
    for (var i = 0; i < allEdges.length; i++) {
        var edge = allEdges[i];
        
        var fromNode = network.body.data.nodes.get(edge.from);
        var toNode = network.body.data.nodes.get(edge.to);
        if (!fromNode || !toNode || fromNode.hidden === true || toNode.hidden === true) {
            edgesToUpdate.push({id: edge.id, hidden: true});
            continue;
        }
        
        var colorValue = edge.color;
        if (typeof colorValue === 'object' && colorValue !== null) {
            colorValue = colorValue.color || colorValue.inherit;
        }
        
        var isSucc = (edge.is_succ === true || edge.is_succ === "True" || edge.is_succ === "true" || colorValue === '#9c27b0');
        var is9Box = (edge.is_9box === true || edge.is_9box === "True" || edge.is_9box === "true" || colorValue === '#22c55e' || colorValue === '#166534');
        
        if (isSucc) {
            edgesToUpdate.push({id: edge.id, hidden: !showSucc});
        } else if (is9Box) {
            edgesToUpdate.push({id: edge.id, hidden: !showJumps});
        } else {
            edgesToUpdate.push({id: edge.id, hidden: !showNormal});
        }
    }
    network.body.data.edges.update(edgesToUpdate);
}

function enfocarPantalla() { 
    network.fit();
    setTimeout(function() {
        var currentScale = network.getScale();
        network.moveTo({
            position: {x: 0, y: -80}, 
            scale: currentScale * 0.85, 
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    }, 800);
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# SISTEMA DE SEGURIDAD Y LOGIN
# ==========================================
def obtener_usuarios_autorizados():
    try:
        return st.secrets["usuarios"]
    except KeyError:
        return {
            "admin": {"nombre": "Administrador Global", "password": "admin", "direccion": "TODAS"},
            "d.comercial": {"nombre": "Director Comercial", "password": "123", "direccion": "DIRECCIÓN COMERCIAL"},
            "d.rh": {"nombre": "Director de Recursos Humanos", "password": "123", "direccion": "RECURSOS HUMANOS"}
        }

def login():
    st.set_page_config(page_title="Plataforma de Talento", layout="wide")
    
    if "usuario_logueado" not in st.session_state:
        st.session_state["usuario_logueado"] = False

    if not st.session_state["usuario_logueado"]:
        usuarios_autorizados = obtener_usuarios_autorizados()
        
        st.markdown("<h1 style='text-align: center; color: #1976d2;'>🔐 Portal de Talento SaaS v8.1</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Inicia sesión para acceder al mapa organizacional</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.write("")
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Iniciar Sesión", use_container_width=True):
                if usuario in usuarios_autorizados and usuarios_autorizados[usuario]["password"] == password:
                    st.session_state["usuario_logueado"] = True
                    st.session_state["nombre_usuario"] = usuarios_autorizados[usuario]["nombre"]
                    st.session_state["id_usuario"] = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

# ==========================================
# DESCARGA DE DATOS OPTIMIZADA CON CACHÉ
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def cargar_datos_csv(url_sheets):
    if "/edit" in url_sheets:
        csv_url = url_sheets.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = url_sheets
    try:
        df = pd.read_csv(csv_url)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

def clean_text(val, default=''):
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'pendiente', '']:
        return default
    return str(val).strip()

def clean_id(val):
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'pendiente', '']: 
        return ''
    v = str(val).strip()
    if v.endswith('.0'): 
        return v[:-2]
    return v

def obtener_color_9box(valor):
    v = str(valor).strip().upper()
    if v in ['9', '7A', '7B', '7']: return '#dc2626' 
    if v == '4': return '#2563eb' 
    if v == '6': return '#ca8a04' 
    if v in ['5', '2']: return '#16a34a' 
    if v in ['1', '3']: return '#14532d' 
    return '#94a3b8' 

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
def generar_mapa_html(df_seguro, f_dir, f_lid, f_crit, f_mla, f_box, f_riesgos):
    G = nx.MultiDiGraph()
    G_jerarquia = nx.DiGraph() 

    jefes_dict = {}
    empleados_validos = set()
    info_nodos = {}
    
    nombres_dict = {
        clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) 
        for row in df_seguro.to_dict('records') if clean_id(row.get('id Empleado'))
    }
    
    nombre_a_id = {nombre.strip().lower(): emp_id for emp_id, nombre in nombres_dict.items()}

    def buscar_id_real(valor):
        if pd.isna(valor) or str(valor).strip().lower() in ['nan', 'none', 'pendiente', '']: 
            return ''
        v = str(valor).strip()
        if v.endswith('.0'): 
            v = v[:-2]
        if v in nombres_dict: 
            return v  
        v_lower = v.lower()
        if v_lower in nombre_a_id: 
            return nombre_a_id[v_lower] 
        return v 
            
    for row_dict in df_seguro.to_dict('records'):
        emp = clean_id(row_dict.get('id Empleado'))
        jefe = clean_id(row_dict.get('ID Del Jefe'))
        
        if emp:
            empleados_validos.add(emp)
            G_jerarquia.add_node(emp)
            
            suc1_limpio = buscar_id_real(row_dict.get('Sucesor P.1', row_dict.get('Sucesor 1', '')))
            suc2_limpio = buscar_id_real(row_dict.get('Sucesor P.2', row_dict.get('Sucesor 2', '')))
            suc3_limpio = buscar_id_real(row_dict.get('Sucesor P.3', row_dict.get('Sucesor 3', '')))
            
            info_nodos[emp] = {
                'mla': clean_text(row_dict.get('Nivel MLA'), 'N/A'),
                'puesto': clean_text(row_dict.get('Nombre de la Posición')).upper(),
                'direccion': clean_text(row_dict.get('Dirección', row_dict.get('Direccion')), 'No asignada'),
                'box': clean_text(row_dict.get('Resultado 9 box'), 'Pendiente'),
                'lider': nombres_dict.get(jefe, 'Sin Líder') if jefe else 'Sin Líder',
                'critica': clean_text(row_dict.get('Posición Crítica', row_dict.get('Posicion Critica')), 'No'),
                'nombre': clean_text(row_dict.get('Nombre')),
                'interes': clean_text(row_dict.get('Interés del Colaborador'), 'Pendiente'),
                'suc1_id': suc1_limpio,
                'read1': clean_text(row_dict.get('Tiempo de Readiness 1'), 'Pendiente'),
                'suc2_id': suc2_limpio,
                'read2': clean_text(row_dict.get('Tiempo de Readiness 2'), ''),
                'suc3_id': suc3_limpio,
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), '')
            }
            if jefe:
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

    sucesores_de_9box = {n: 0 for n in G_jerarquia.nodes()}
    sucesores_oficiales_de = {n: 0 for n in G_jerarquia.nodes()} 

    for emp, info in info_nodos.items():
        box = info['box'].upper()
        if box in ['5', '2']: 
            j1 = obtener_jefe_nivel_arriba(emp, 1)
            if j1: 
                sucesores_de_9box[j1] += 1
        if box in ['1', '3']:
            j2 = obtener_jefe_nivel_arriba(emp, 2)
            if j2: 
                sucesores_de_9box[j2] += 1
            
        for s_id in [info['suc1_id'], info['suc2_id'], info['suc3_id']]:
            if s_id in sucesores_oficiales_de:
                sucesores_oficiales_de[s_id] += 1

    for emp, info in info_nodos.items():
        es_critica = (info['critica'].lower() == 'si')
        tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
        tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
        
        r_list = []
        if es_critica:
            if not tiene_oficial and not tiene_hipos_9box: 
                r_list.append("🔥 Riesgo Crítico: Sin Sucesor ni HiPos")
            elif not tiene_oficial and tiene_hipos_9box: 
                r_list.append("⚠️ Sugerencia: HiPo disponible, falta oficializar")
                
        reps = reportes_directos.get(emp, 0)
        if reps >= 12: 
            r_list.append(f"⚠️ Sobrecarga ({reps} reportes)")
        elif reps == 1: 
            r_list.append("⚠️ Ineficiencia (1 reporte)")
            
        info_nodos[emp]['riesgos_lista'] = r_list
        info_nodos[emp]['riesgos'] = " | ".join(r_list) if r_list else "Ninguno"

    descendientes_validos = set()
    if f_lid != "Todos":
        lider_ids = [emp for emp, inf in info_nodos.items() if inf['nombre'] == f_lid]
        for l_id in lider_ids:
            descendientes_validos.add(l_id)
            try:
                if l_id in G_jerarquia:
                    descendientes_validos.update(nx.descendants(G_jerarquia, l_id))
            except nx.NetworkXError: 
                pass

    nodos_visibles = set()
    for emp, info in info_nodos.items():
        if info['mla'] == '5':
            nodos_visibles.add(emp)
            continue
            
        if f_lid != "Todos" and info['nombre'] == f_lid:
            nodos_visibles.add(emp)
            continue
            
        if f_dir != "Todas" and info['direccion'] != f_dir: continue
        if f_lid != "Todos" and emp not in descendientes_validos: continue
        if f_crit != "Todas" and info['critica'] != f_crit: continue
        if f_mla != "Todos" and info['mla'] != f_mla: continue
        if f_box != "Todos" and info['box'] != f_box: continue
        if f_riesgos and not info['riesgos_lista']: continue
        
        nodos_visibles.add(emp)

    nodos_rescatados = set(nodos_visibles)
    for emp in nodos_visibles:
        info = info_nodos[emp]
        for s_id in [info['suc1_id'], info['suc2_id'], info['suc3_id']]:
            if s_id and s_id in info_nodos:
                nodos_rescatados.add(s_id)
    nodos_visibles = nodos_rescatados

    raiz_principal = None
    for emp, info in info_nodos.items():
        if info['mla'] == '5':
            raiz_principal = emp
            break 
            
    if not raiz_principal:
        posibles_raices = [n for n in G_jerarquia.nodes() if G_jerarquia.in_degree(n) == 0]
        if posibles_raices: 
            raiz_principal = max(posibles_raices, key=lambda x: len(nx.descendants(G_jerarquia, x)))

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 1800 
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
    def asignar_coordenada_radial(nodo, angulo_inicio, angulo_fin):
        hijos = list(Arbol.successors(nodo))
        if not hijos: 
            return
        hojas_totales = sum(conteo_hojas.get(c, 1) for c in hijos)
        angulo_actual = angulo_inicio
        for i, c in enumerate(hijos):
            rebanada = (conteo_hojas.get(c, 1) / hojas_totales) * (angulo_fin - angulo_inicio)
            angulo_hijo = angulo_actual + (rebanada / 2)
            profundidad = nx.shortest_path_length(Arbol, raiz_principal, c) if raiz_principal and c in Arbol else 5
            anillo_real = obtener_anillo_estricto(c, profundidad)
            radio_final = (anillo_real * SEPARACION_ANILLOS) + (profundidad * 120) if anillo_real != 0 else 0
            
            coords[c] = {
                'x': radio_final * math.cos(angulo_hijo), 
                'y': radio_final * math.sin(angulo_hijo), 
                'angle': angulo_hijo, 
                'anillo_real': anillo_real, 
                'profundidad': profundidad
            }
            
            asignar_coordenada_radial(c, angulo_actual, angulo_actual + rebanada)
            angulo_actual += rebanada

    if raiz_principal:
        coords[raiz_principal] = {'x': 0, 'y': 0, 'angle': 0, 'anillo_real': 0, 'profundidad': 0}
        asignar_coordenada_radial(raiz_principal, 0, 2 * math.pi)

    nodos_sin_coords = [n for n in G_jerarquia.nodes() if n not in coords]
    if nodos_sin_coords:
        angulo_extra = (2 * math.pi) / len(nodos_sin_coords)
        angulo_actual = 0
        for n in nodos_sin_coords:
            anillo = obtener_anillo_estricto(n, 5)
            radio = (anillo * SEPARACION_ANILLOS) + 200 if anillo != 0 else 500
            coords[n] = {'x': radio * math.cos(angulo_actual), 'y': radio * math.sin(angulo_actual), 'angle': angulo_actual, 'anillo_real': anillo, 'profundidad': 5}
            angulo_actual += angulo_extra

    alertas_tabla = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        if not is_hidden:
            for r in info['riesgos_lista']:
                alertas_tabla.append({
                    "Colaborador": info['nombre'],
                    "Líder Directo": info['lider'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Alerta Detectada por IA": r
                })

        prefijo = "🚨 " if info['riesgos_lista'] else ""
        coord_data = coords.get(emp, {'x':5000, 'y':5000, 'angle':0, 'anillo_real':5, 'profundidad':5})
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        G.add_node(
            emp, label=f"{prefijo}{info['nombre']}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 10, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    # =========================================================
    # CONEXIONES ESTRUCTURALES Y PREDICTIVAS
    # =========================================================
    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False)

    for emp, info in info_nodos.items():
        box = info['box'].upper()
        if box in ['5', '2']:
            j1 = obtener_jefe_nivel_arriba(emp, 1)
            if j1: 
                G.add_edge(emp, j1, color='#22c55e', width=3, dashes=[5,5], title='Proyección N+1', hidden=(emp not in nodos_visibles or j1 not in nodos_visibles), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.2})
        
        if box in ['1', '3']:
            j2 = obtener_jefe_nivel_arriba(emp, 2)
            if j2: 
                G.add_edge(emp, j2, color='#166534', width=3.5, dashes=[5,5], title='Proyección N+2', hidden=(emp not in nodos_visibles or j2 not in nodos_visibles), is_struct=False, is_9box=True, is_succ=False, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.3})
            
        for s_id in [info['suc1_id'], info['suc2_id'], info['suc3_id']]:
            if s_id and s_id in empleados_validos:
                is_hidden_edge = (emp not in nodos_visibles or s_id not in nodos_visibles)
                G.add_edge(emp, s_id, color='#9c27b0', width=5, dashes=False, title='🎯 Objetivo de Sucesión', hidden=is_hidden_edge, is_struct=False, is_9box=False, is_succ=True, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.6})

    kpis = {
        'total': len(nodos_visibles),
        'criticas': sum(1 for emp in nodos_visibles if info_nodos[emp]['critica'].lower() == 'si'),
        'sucesores': sum(1 for emp in nodos_visibles if info_nodos[emp]['suc1_id']),
        'operativos': sum(1 for emp in nodos_visibles if info_nodos[emp]['mla'] == '1'),
        'alertas': len(alertas_tabla)
    }
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n</body>')
    
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

    with st.spinner("Cargando mapa con conexiones lógicas..."):
        link_google_sheets = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit?pli=1&gid=0#gid=0"
        df_completo = cargar_datos_csv(link_google_sheets)
        
        if df_completo.empty:
            st.error("Error al conectar con la base de datos de Google Sheets.")
            st.stop()

        usuarios_autorizados = obtener_usuarios_autorizados()
        direccion_permitida = usuarios_autorizados[st.session_state["id_usuario"]]["direccion"]
        
        if direccion_permitida != "TODAS":
            df_seguro = df_completo[(df_completo['Dirección'].astype(str).str.upper().str.contains(direccion_permitida)) | (df_completo['Nivel MLA'].astype(str).str.strip() == '5')]
        else:
            df_seguro = df_completo.copy()

        st.markdown("### 🎛️ Filtros Globales (Controlan Mapa, KPIs y Tabla)")
        
        dirs = sorted([clean_text(x) for x in df_seguro['Dirección'].unique() if clean_text(x)])
        mlas = sorted([clean_text(x) for x in df_seguro['Nivel MLA'].unique() if clean_text(x)])
        boxes = sorted([clean_text(x).upper() for x in df_seguro['Resultado 9 box'].unique() if clean_text(x)])
        criticas = sorted([clean_text(x) for x in df_seguro['Posición Crítica'].unique() if clean_text(x)])
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))

        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        f_lid = col_f2.selectbox("Líder", ["Todos"] + lideres)
        f_crit = col_f3.selectbox("Pos. Crítica", ["Todas"] + criticas)
        f_mla = col_f4.selectbox("Nivel MLA", ["Todos"] + mlas)
        f_box = col_f5.selectbox("9-Box", ["Todos"] + boxes)
        
        f_riesgos = st.checkbox("🚨 Mostrar Solo Colaboradores con Riesgos Detectados")
        st.write("") 

        html_mapa, df_alertas, kpis = generar_mapa_html(df_seguro, f_dir, f_lid, f_crit, f_mla, f_box, f_riesgos)
        
        if kpis is not None:
            col_mapa, col_datos = st.columns([7, 3])
            with col_mapa:
                components.html(html_mapa, height=750, scrolling=False)
                
            with col_datos:
                st.markdown("### 📊 KPIs de Talento")
                st.write("")
                st.metric("Total de Colaboradores", kpis['total'])
                st.metric("Posiciones Críticas", kpis['criticas'])
                st.metric("Colaboradores Perfilados", kpis['sucesores'])
                st.metric("Personal Operativo (MLA 1)", kpis['operativos'])
                st.metric("🚨 Alertas Detectadas", kpis['alertas'])
            
            st.divider()
            st.markdown("### 🚨 Resumen de Tareas y Alertas (Filtrable)")
            
            if not df_alertas.empty:
                col_t1, col_t2, col_t3 = st.columns(3)
                
                lista_areas = df_alertas['Dirección'].unique().tolist()
                filtro_area = col_t1.multiselect("📌 Filtrar Tabla por Área:", options=lista_areas)
                
                lista_lideres_tabla = df_alertas['Líder Directo'].unique().tolist()
                filtro_lider_tabla = col_t2.multiselect("👥 Filtrar Tabla por Líder:", options=lista_lideres_tabla)
                
                lista_riesgos = df_alertas['Alerta Detectada por IA'].unique().tolist()
                filtro_riesgo_tabla = col_t3.multiselect("⚠️ Filtrar por Tipo de Alerta:", options=lista_riesgos)
                
                df_filtrado = df_alertas.copy()
                if filtro_area: 
                    df_filtrado = df_filtrado[df_filtrado['Dirección'].isin(filtro_area)]
                if filtro_lider_tabla: 
                    df_filtrado = df_filtrado[df_filtrado['Líder Directo'].isin(filtro_lider_tabla)]
                if filtro_riesgo_tabla: 
                    df_filtrado = df_filtrado[df_filtrado['Alerta Detectada por IA'].isin(filtro_riesgo_tabla)]
                
                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            else:
                st.success("✅ ¡Excelente! No se detectaron alertas de sucesión ni sobrecarga de reportes con estos filtros.")
        else:
            components.html(html_mapa, height=400)

if __name__ == "__main__":
    main()
