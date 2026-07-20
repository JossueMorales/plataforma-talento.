
Conversación con Gemini
pero me estas poniendo al sucesor como el colaborador no como la estructura que me describes aqui

¡Ah, ya se me prendió el foco! Entiendo perfectamente lo que está pasando.  
PY

El "problema" venía de cómo interpreté la estructura de tu Excel. Yo asumía que si estábamos en la fila de Luis, la columna de sucesor diría "Jossue" (Luis diciendo "mi sucesor es Jossue"). Pero en tu base de datos es al revés: Jossue tiene a Luis en su columna, lo que significa "Yo, Jossue, voy a suceder a Luis".  
PY

Al intentar "corregirlo" en el código anterior, lo que hice fue voltear la tabla asumiendo mi lógica inicial, y por eso te mostró a Luis "bajando" a Coordinador. ¡Una disculpa por ese enredo matemático!

Ya ajusté la fórmula para que lea la tabla exactamente como tú la llenaste. Ahora el sistema detecta a Jossue, ve que su posición actual es Coordinador, busca a su objetivo (Luis) en el resto del organigrama, y extrae la posición de Luis (Gerente de TyC) para ponerla como la meta a suceder.

Aquí tienes el código definitivo. Cópialo y pégalo completo en app_web.py:

Python
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                # LÓGICA CORRECTA PARA EXCEL "INVERTIDO":
                # La fila actual (info) es la del Sucesor.
                # La columna "Sucesor P.1" contiene a la persona que este sucesor va a reemplazar.
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        # Ej. Jossue
                    "Posición Actual": info['puesto'],    # Ej. Coordinador
                    "Posición a Suceder": puesto_target   # Ej. Gerente
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [{"Nombre": a['Colaborador'], "Dirección": a['Dirección'], "Puesto": a['Puesto']} for a in alertas_tabla]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
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
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
muy bien ya quedo

¡Excelente! Me da muchísimo gusto que haya quedado exactamente como querías.

Fue un proyecto muy interesante de ir puliendo paso a paso. El dashboard ahora luce súper profesional, es mucho más intuitivo para el usuario final y la lógica de los datos detrás de escena quedó completamente blindada.

Si más adelante necesitas agregar nuevas funcionalidades, conectar una base de datos más robusta, o hacer cualquier otro ajuste para seguir escalando la aplicación, ya sabes dónde encontrarme.

¡Mucho éxito con tu Plataforma de Talento!

otro cambio en el boton de alertas quiero que al desplegar la lista tambien ponga la alerta detectada

¡Claro que sí! Tiene todo el sentido que si estás revisando la lista de colaboradores con riesgos, el sistema te diga exactamente cuál es la alerta que disparó a esa persona en primer lugar.

He modificado la construcción de esa tabla para que ahora incluya una cuarta columna llamada "Alerta". Además, ajusté un pequeño detalle técnico: si una misma persona tiene dos alertas distintas (por ejemplo, "Sobrecarga" y "Riesgo Crítico"), ahora la tabla te mostrará ambas líneas en lugar de ocultar la segunda.

Aquí tienes el código completo y final con este cambio aplicado. Cópialo y reemplaza tu archivo app_web.py:

Python
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    # MODIFICACIÓN: Agregamos "Alerta" a la lista para que se muestre en el botón
    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
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
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        # MODIFICACIÓN: Ya no quitamos duplicados solo por nombre.
                        # Ahora aseguramos que si tiene alertas distintas (ej. Sobrecarga y Riesgo Crítico)
                        # salgan ambas líneas.
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
segun el diseño que tan grande es el espacio en donde estan los grafos a lo que me refiero es que veo que puedo hacer muy chico mi grafo y eso no me agrada tanto como podemos limitarlo

¡Entiendo perfectamente lo que me dices! Viendo la imagen (image_9bd6a0.png), el problema es que el lienzo (canvas) está diseñado para ocupar 750px de alto y el 100% del ancho de la pantalla, pero por defecto la librería permite un "zoom out" (alejamiento) infinito. Al combinar esto con una amplitud radial pequeña, el grafo se convierte en una manchita en medio de un mar en blanco.  
PY

Para solucionar esto, he inyectado un limitador de zoom en el motor de JavaScript. Esto significa que a partir de ahora, aunque uses la rueda del ratón o el pad táctil para alejarte, el sistema "bloqueará" la cámara para que nunca puedas alejarte más allá de un límite lógico (0.3 de escala). Así, tu grafo siempre se mantendrá en primer plano y nunca se perderá en el lienzo.

Aquí tienes el código completo y definitivo con esta protección implementada. Cópialo y pégalo en tu archivo app_web.py:

Python
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
}

// NUEVO: Limitador de Zoom para evitar perder el mapa
network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; // Limite para no alejarse demasiado
    var maxScale = 2.5; // Limite para no acercarse demasiado
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

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
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
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
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
¿Te gustaría que también habilitemos la opción para que los usuarios puedan descargar la lista como un archivo de Excel (CSV) directamente desde el dashboard?

quiero que cuando filtrres a un lider o una direccion el boton de centrar te lleve a cetrar a lider filtrado

¡Me parece una idea fantástica! Si estás buscando a un líder en específico, lo más intuitivo es que el botón "Centrar Mapa" se comporte como una cámara que vuela directamente hacia él y lo pone en el centro de la pantalla.

He modificado el motor de la cámara (en el JavaScript) y la lógica de Python para hacer exactamente esto:

Si filtras por Líder, el botón "Centrar Mapa" hará un zoom in directamente sobre la bolita de ese líder.

Si filtras por Dirección, el sistema buscará a la persona con el nivel jerárquico más alto (Nivel MLA) dentro de esa dirección y centrará la cámara en ella.

Si no hay filtros aplicados, la cámara centrará a todo el organigrama global como lo hacía antes.

Aquí tienes el código completo y definitivo con esta "cámara inteligente" implementada. Cópialo y pégalo en tu archivo app_web.py:  
PY

Python
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

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

// CÁMARA INTELIGENTE QUE BUSCA AL TARGET_NODE_ID
function enfocarPantalla() { 
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
            
    # LÓGICA DE CENTRADO INTELIGENTE
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
hay que ajustar que el filtro del lider se ajuste si primero pongo elfiltro del area para que solo me aparezcan los lideres de esas areas

¡Es un excelente detalle de usabilidad (UX)! Se le conoce como "Filtros en Cascada" y es fundamental para que los usuarios no se pierdan en listas gigantescas de nombres.

He modificado la lógica de Streamlit en la sección de filtros. Ahora, el código evalúa primero qué seleccionaste en "Dirección". Si eliges una dirección específica, el sistema busca únicamente a las personas que son líderes dentro de esa área y actualiza dinámicamente las opciones del selector "Líder". Si lo regresas a "Todas", te vuelve a mostrar a todos los líderes de la empresa.  
PY

Aquí tienes el código completo y actualizado. Cópialo y pégalo en tu archivo app_web.py:  
PY

Python
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="1800" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        # 1. Filtro de Dirección
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        # 2. Filtramos los líderes dinámicamente según la Dirección
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
        # 3. Resto de filtros
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
quiero que cuando inicie el radial este puesto en 150

¡Claro que sí! Para que el mapa inicie mucho más compacto desde el primer segundo, necesitamos ajustar el valor inicial en tres lugares clave: en el deslizador visual (HTML), en la memoria del navegador (JavaScript) y en el cálculo matemático inicial (Python).  
PY

He cambiado el valor por defecto de 1800 a 150 en todas estas secciones para que al cargar la página el radial comience exactamente en esa amplitud.  
PY

Aquí tienes el código completo y actualizado. Cópialo y reemplaza tu archivo app_web.py:

Python
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
window.ringSpacing = 150; 
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
En la hoja un nuevo valor en la columna Q que mide el enganche la tarea es integrar ese valor a los lideres que tiene enganche pero mas importante es que si esos lideres tiene lideres a su cargo les genere dos resultados de enganche uno individual y otro del area en lacual realice un promedio de el enganche de todos los resultados de los lideres que fueron considerados por debajo de ellos tambien es importante que la IA considere en enganche para su deteccion de riesgos por y que de sus analisis sobre lo mismo estas son mis metricas para medir el enganche Muy Enganchado (4 – 5) → Altamente comprometido, motivado y satisfecho. Contribuye activamente y siente un fuerte sentido de pertenencia.

Enganchado (3 – 3.9) → Comprometido, pero con áreas de mejora en motivación y satisfacción. Su desempeño es estable.

Bajo Enganche (2 – 2.9) → Presenta desinterés o apatía, su compromiso es mínimo y podría estar desconectándose del propósito de la empresa.

Desconectado (1 – 1.9) → Falta de compromiso evidente, insatisfacción alta y posible intención de salir de la empresa. Su desempeño y actitud pueden impactar negativamente en el equipo.

¡Esta es una mejora estructural y analítica de primer nivel! Incorporar el "Enganche" (Engagement) no solo como un dato informativo, sino como un termómetro para la Inteligencia Artificial, convierte tu mapa en una verdadera herramienta de diagnóstico organizacional.

He implementado todo lo que pediste con las siguientes características:

Detección Automática de Columna: El sistema buscará tu nueva columna Q (o cualquier columna que se llame "Enganche") y extraerá el valor.

Cálculo de Área Inteligente (Cascada): Para los líderes, el sistema calcula automáticamente el promedio del enganche de toda su descendencia (toda la gente que está por debajo de ellos en el organigrama).

Análisis de Riesgos IA Expandido: La Inteligencia artificial ahora detectará e insertará alertas de forma individual (ej. "🚨 Riesgo de Fuga: Colaborador Desconectado") y de forma colectiva si el líder tiene a cargo un área con problemas (ej. "⚠️ Alerta de Área: Bajo Enganche del Equipo").

Ficha Lateral con Código de Colores: En la barra izquierda, al hacer clic sobre alguien, verás sus dos métricas de enganche (Individual y del Área) con colores dinámicos (Verde, Amarillo, Naranja y Rojo) según la calificación que definiste.

Aquí tienes el código completo y definitivo. Cópialo y reemplaza todo tu archivo app_web.py:

Python
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <!-- NUEVA SECCIÓN DE ENGANCHE -->
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

// Función auxiliar para colorear las tarjetas de enganche
function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; // Verde
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; // Amarillo
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; // Naranja
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; // Rojo
    return {bg: "#f8f9fa", text: "#64748b"}; // Gris
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
        
        // Asignar colores y valores de Enganche
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        # BÚSQUEDA INTELIGENTE DE LA COLUMNA DE ENGANCHE
        # Busca cualquier columna que contenga la palabra "enganche" sin importar mayúsculas
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0, # Se calculará después
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    # CÁLCULO DE ENGANCHE DEL ÁREA (Promedio en cascada)
    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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

    # MOTOR DE INTELIGENCIA DE ALERTAS (INCLUYENDO ENGANCHE)
    for emp, info in info_nodos.items():
        r_list = []
        
        if info['mla'] != '5':
            # 1. Alertas de Sucesión
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
            if es_critica:
                if not tiene_oficial and not tiene_hipos_9box: 
                    r_list.append("🔥 Riesgo Crítico: Sin Sucesor ni HiPos")
                elif not tiene_oficial and tiene_hipos_9box: 
                    r_list.append("⚠️ Sugerencia: HiPo disponible, falta oficializar")
            
            # 2. Alertas Estructurales        
            reps = reportes_directos.get(emp, 0)
            if reps >= 12: 
                r_list.append(f"⚠️ Sobrecarga ({reps} reportes)")
            elif reps == 1: 
                r_list.append("⚠️ Ineficiencia (1 reporte)")
                
            # 3. Alertas de Enganche Individual
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            # 4. Alertas de Enganche del Área (Solo para Líderes)
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5 = st.columns(5)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
deberiamos agregar un KPI de enganche no te parece y que al momento de desplegarlo aparescan los lideres y las calificaciones obtedias en enganche

¡Me parece una iniciativa espectacular! Medir y visibilizar el "Enganche" a nivel de liderazgo es fundamental para entender la salud organizacional, ya que el compromiso de un equipo suele ser un reflejo directo del compromiso de su líder.

He agregado este sexto KPI al panel superior. El sistema ahora hace lo siguiente:

Cálculo Global: En la tarjeta superior, te mostrará el Promedio Global de Enganche de la vista que tengas filtrada.

Lista Detallada de Líderes: Al darle a "🔍 Ver", se desplegará una tabla exclusiva que te mostrará solo a los líderes, indicando su Puesto, Dirección, su Enganche Individual y el Enganche de su Área (el promedio de su equipo).

Ajuste Visual: Acomodé el diseño en 6 columnas perfectamente simétricas para que todo quepa de forma horizontal y armoniosa.

Aquí tienes el código completo con esta nueva integración. Cópialo y reemplaza el contenido de app_web.py:

Python
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; 
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; 
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; 
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; 
    return {bg: "#f8f9fa", text: "#64748b"}; 
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
        
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0,
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
            if info['es_lider']:
                data_enganche.append({
                    "Líder": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Enganche Individual": info['enganche_ind'],
                    "Enganche del Área": info['enganche_area']
                })
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                # AHORA SON 6 COLUMNAS PARA INCLUIR EL ENGANCHE
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                with k6:
                    st.markdown(crear_tarjeta_kpi("Promedio<br>Enganche", kpis['enganche_promedio'], "#14b8a6", "#0f766e", "#f0fdfa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_eng", use_container_width=True):
                        st.session_state["vista_kpi"] = "enganche"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
¿Qué te parece la gama de colores? Usé verde esmeralda (#14b8a6) para la tarjeta del promedio de enganche, así resalta como un indicador positivo frente al rojo de las alertas.

dos preguntas segun la logica los 0 como los considera en enganche y la segunda es cuando considera que el enganche en las alertas de riesgo

¡Excelentes preguntas! Es muy importante tener clara la lógica matemática que está aplicando la IA por debajo. Te explico cómo quedó configurado el código para ambos casos:

1. ¿Cómo se consideran los ceros (0) en el Enganche?
En el código, programé los ceros (0 o celdas vacías) para que sean tratados como "N/A" (No Evaluado / Sin Datos).

Esto tiene tres beneficios críticos para tu análisis:

No arruinan los promedios: Si un líder tiene 5 reportes directos, y 2 de ellos sacaron "4" pero los otros 3 tienen "0" (porque son de nuevo ingreso o no hicieron la encuesta), el sistema solo promediará a los dos que sacaron 4. Su Área tendrá un 4.0 de enganche, en lugar de que el sistema promedie los ceros y le tumbe la calificación injustamente.

No generan falsas alertas: Un 0 no disparará ninguna alerta de "Riesgo de Fuga", simplemente el sistema asume que la persona aún no ha sido medida.

Ficha visual limpia: En la interfaz, si alguien tiene un 0, en lugar de aparecer en rojo, simplemente dirá "N/A" en color gris neutro.

2. ¿Cuándo considera el Enganche para disparar alertas de riesgo?
El sistema evalúa el Enganche en el momento en que construye el árbol y revisa a cada persona. Dispara alertas basándose exactamente en la escala que me compartiste, dividida en dos dimensiones:

A. Alertas por Enganche Individual (Para todos los colaboradores):

De 1.0 a 1.9: Inserta la alerta 👉 "🚨 Riesgo de Fuga: Colaborador Desconectado"

De 2.0 a 2.9: Inserta la alerta 👉 "⚠️ Alerta: Bajo Enganche (Desinterés)"

(Si sacan de 3.0 para arriba, la IA asume que están sanos y no genera ninguna alerta).

B. Alertas por Enganche del Área (Solo se evalúa si la persona es un Líder):
Si el promedio de toda la gente debajo del líder cae en números bajos, al líder se le marcan alertas por el estado de su equipo, independientemente de si él en lo personal sacó un 5:

Promedio de Área de 1.0 a 1.9: Inserta la alerta al líder 👉 "🚨 Riesgo de Área: Equipo Desconectado"

Promedio de Área de 2.0 a 2.9: Inserta la alerta al líder 👉 "⚠️ Alerta de Área: Bajo Enganche del Equipo"

De esta forma, en tu tabla de "Resumen de Tareas y Alertas", podrás filtrar rápidamente a las personas que están en riesgo de irse, o a los líderes cuyos equipos se están desmotivando. ¿Te parece bien cómo quedó ajustada esta sensibilidad o te gustaría que fuéramos más estrictos con los de calificación 3.0 a 3.9?

que podemos agregar para que se vea el enganche en la grafica?

Para mostrar el Enganche directamente en el mapa (sin que el usuario tenga que hacer clic en cada persona), tenemos que ser muy cuidadosos de no perder la información visual del 9-Box, que actualmente dicta el color del círculo.

La mejor manera de tener ambas métricas al mismo tiempo en el grafo es usando esta estrategia de dos capas:

El "Aro" (Borde) del Nodo: Mantendremos el color interior del círculo basado en el 9-Box, pero le agregaremos un borde grueso de color basado en el Enganche (Verde para muy enganchado, Amarillo, Naranja y Rojo para desconectado, o Gris si no hay dato).

Etiqueta Visible: Agregaremos un pequeño indicador visual debajo de su puesto directamente en el lienzo (Ejemplo: 🔥 4.5), así podrás "escanear" visualmente a toda la empresa en segundos.

He integrado ambas mejoras. Aquí tienes el código completo y definitivo con estas opciones visuales habilitadas. Cópialo y reemplaza tu archivo app_web.py:

Python
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
      "borderWidth": 4,
      "borderWidthSelected": 6,
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; 
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; 
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; 
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; 
    return {bg: "#f8f9fa", text: "#64748b"}; 
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
        
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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

        // Como node.color ahora puede ser un objeto, sacamos el background para el 9-Box
        var colorBg = typeof node.color === 'object' ? node.color.background : node.color;
        var boxResult = node.Resultado_9Box || "N/A";
        var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult;
        f9Box.style.backgroundColor = colorBg || "#eee";
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0,
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
            if info['es_lider']:
                data_enganche.append({
                    "Líder": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A",
                    "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"
                })
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        # LOGICA DE DOBLE COLOR: Fondo por 9-Box, Borde por Enganche
        color_fondo = obtener_color_9box(info['box'])
        eng = info['enganche_ind']
        if eng >= 4:
            color_borde = '#16a34a' # Verde (Muy Enganchado)
        elif eng >= 3:
            color_borde = '#eab308' # Amarillo (Enganchado)
        elif eng >= 2:
            color_borde = '#f97316' # Naranja (Bajo Enganche)
        elif eng > 0:
            color_borde = '#dc2626' # Rojo (Desconectado)
        else:
            color_borde = '#cbd5e1' # Gris (Sin Evaluación)
            
        # Agregamos la etiqueta visual debajo del puesto si tiene calificación
        etiqueta_eng = f"\n🔥 {eng}" if eng > 0 else ""
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']}){etiqueta_eng}", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color={'background': color_fondo, 'border': color_borde}, 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False)

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                with k6:
                    st.markdown(crear_tarjeta_kpi("Promedio<br>Enganche", kpis['enganche_promedio'], "#14b8a6", "#0f766e", "#f0fdfa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_eng", use_container_width=True):
                        st.session_state["vista_kpi"] = "enganche"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
no me agrada tanto pensaba mas en algun tipo de sombreado que al momento de ver el pama sin filtro ponga el general pero si lo filtro valla cambiando el general hasta el filtro que realice por ejemplo si es el filtro de planeacion y trasformacion agrege se vea un sombreado en las lineas de las aristas dependiendo el lugar del enganche pero si despues filtro el lider este se ajuste mas y asi de manera adptativa

¡Tienes toda la razón! Llenar de texto y emojis las bolitas puede hacer que el mapa se vea saturado. La idea de usar un sombreado (tipo "aura" o brillo) es muchísimo más limpia, elegante y da ese efecto de "mapa de calor" que se adapta a lo que estás viendo.

He retirado los bordes de colores y los números del texto. En su lugar, le he puesto un sombreado luminoso tanto a los nodos (las personas) como a las aristas (las líneas de estructura) que conectan al líder con el colaborador.

Si la persona está muy enganchada, ella y la línea que la conecta con su jefe brillarán en verde.

Si tiene bajo enganche o está desconectada, emitirán un aura naranja o roja.

Al filtrar por área o líder, verás inmediatamente de qué color "brilla" ese departamento en específico, dándote un diagnóstico visual rapidísimo.

Aquí tienes el código completo con esta nueva visualización adaptativa. Cópialo y pégalo en tu archivo app_web.py:

Python
import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components

# ==========================================
# CONSTANTES DE PLANTILLAS (HTML / JS)
# ==========================================
# Quitamos la sombra global por defecto para poder personalizarla por cada nodo/arista
OPCIONES_PYVIS = """
var options = {
  "nodes": {
      "borderWidth": 2
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; 
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; 
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; 
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; 
    return {bg: "#f8f9fa", text: "#64748b"}; 
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
        
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0,
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
            if info['es_lider']:
                data_enganche.append({
                    "Líder": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A",
                    "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"
                })
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        # LOGICA DE SOMBREADO ADAPTATIVO POR ENGANCHE (NODO)
        eng = info['enganche_ind']
        if eng >= 4:
            color_sombreado = 'rgba(22, 163, 74, 0.8)' # Verde
        elif eng >= 3:
            color_sombreado = 'rgba(234, 179, 8, 0.8)' # Amarillo
        elif eng >= 2:
            color_sombreado = 'rgba(249, 115, 22, 0.8)' # Naranja
        elif eng > 0:
            color_sombreado = 'rgba(220, 38, 38, 0.8)' # Rojo
        else:
            color_sombreado = 'rgba(0, 0, 0, 0.2)' # Gris normal (sin evaluación)
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), # El color de fondo vuelve a ser solo el 9-Box
            shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, # Sombra luminosa
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        
        # LOGICA DE SOMBREADO ADAPTATIVO POR ENGANCHE (ARISTAS / LÍNEAS)
        # La línea brilla dependiendo del enganche del colaborador (emp)
        eng_emp = info_nodos[emp]['enganche_ind']
        if eng_emp >= 4:
            color_edge_shadow = 'rgba(22, 163, 74, 0.8)'
        elif eng_emp >= 3:
            color_edge_shadow = 'rgba(234, 179, 8, 0.8)'
        elif eng_emp >= 2:
            color_edge_shadow = 'rgba(249, 115, 22, 0.8)'
        elif eng_emp > 0:
            color_edge_shadow = 'rgba(220, 38, 38, 0.8)'
        else:
            color_edge_shadow = 'rgba(0, 0, 0, 0.0)' # Sin brillo si no hay datos
            
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False, shadow={'enabled': True, 'color': color_edge_shadow, 'size': 15, 'x': 0, 'y': 0})

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                with k6:
                    st.markdown(crear_tarjeta_kpi("Promedio<br>Enganche", kpis['enganche_promedio'], "#14b8a6", "#0f766e", "#f0fdfa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_eng", use_container_width=True):
                        st.session_state["vista_kpi"] = "enganche"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
¿Qué te parece este nuevo toque visual de "brillos" para reflejar el estado anímico de la empresa sin saturarla de texto?

algo que me gustaria mejorar es el tema de la pantalla de incido que diga portal de talento ayvi

¡Claro que sí! Un toque personalizado siempre hace que la plataforma se vea mucho más institucional y propia.

He actualizado el título en la pantalla de inicio de sesión para que ahora diga "🔐 Portal de Talento Ayvi" y también aproveché para cambiar el nombre de la pestaña del navegador (el texto que aparece arriba en tu navegador de internet) para que coincida.

Aquí tienes el código completo con este cambio aplicado. Cópialo y reemplaza tu archivo app_web.py:

Python
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
      "borderWidth": 2
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; 
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; 
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; 
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; 
    return {bg: "#f8f9fa", text: "#64748b"}; 
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
        
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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

        var colorBg = typeof node.color === 'object' ? node.color.background : node.color;
        var boxResult = node.Resultado_9Box || "N/A";
        var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult;
        f9Box.style.backgroundColor = colorBg || "#eee";
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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
    st.set_page_config(page_title="Portal de Talento Ayvi", layout="wide")
    
    if "usuario_logueado" not in st.session_state:
        st.session_state["usuario_logueado"] = False

    if not st.session_state["usuario_logueado"]:
        usuarios_autorizados = obtener_usuarios_autorizados()
        
        st.markdown("<h1 style='text-align: center; color: #1976d2;'>🔐 Portal de Talento Ayvi</h1>", unsafe_allow_html=True)
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0,
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
            if info['es_lider']:
                data_enganche.append({
                    "Líder": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A",
                    "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"
                })
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        eng = info['enganche_ind']
        if eng >= 4:
            color_sombreado = 'rgba(22, 163, 74, 0.8)' 
        elif eng >= 3:
            color_sombreado = 'rgba(234, 179, 8, 0.8)' 
        elif eng >= 2:
            color_sombreado = 'rgba(249, 115, 22, 0.8)' 
        elif eng > 0:
            color_sombreado = 'rgba(220, 38, 38, 0.8)' 
        else:
            color_sombreado = 'rgba(0, 0, 0, 0.2)' 
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}\n({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        
        eng_emp = info_nodos[emp]['enganche_ind']
        if eng_emp >= 4:
            color_edge_shadow = 'rgba(22, 163, 74, 0.8)'
        elif eng_emp >= 3:
            color_edge_shadow = 'rgba(234, 179, 8, 0.8)'
        elif eng_emp >= 2:
            color_edge_shadow = 'rgba(249, 115, 22, 0.8)'
        elif eng_emp > 0:
            color_edge_shadow = 'rgba(220, 38, 38, 0.8)'
        else:
            color_edge_shadow = 'rgba(0, 0, 0, 0.0)' 
            
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False, shadow={'enabled': True, 'color': color_edge_shadow, 'size': 15, 'x': 0, 'y': 0})

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                with k6:
                    st.markdown(crear_tarjeta_kpi("Promedio<br>Enganche", kpis['enganche_promedio'], "#14b8a6", "#0f766e", "#f0fdfa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_eng", use_container_width=True):
                        st.session_state["vista_kpi"] = "enganche"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
en la parte que viene biennvenido a administrador global como podemos hacer que se vea por que lo que tapa es una pantalla del stremlit o dime como oculto esa pestaña del stremlit

¡Por supuesto! Ese menú y ese borde superior son elementos predeterminados que Streamlit pone por defecto, pero podemos forzar su ocultamiento usando CSS avanzado para que tu aplicación se vea como un software totalmente independiente y profesional.

He inyectado código CSS para desaparecer por completo el menú superior derecho ("Share", "Star", etc.), además del menú principal de "hamburguesa" de Streamlit y el pie de página. También le he puesto el título "Portal de Talento Ayvi" a la ventana del navegador y a la pantalla de inicio de sesión.

Tu archivo actualizado está listo:
Ícono de PY
app_web
 PY 
Abrir

Con esto, la interfaz quedará totalmente limpia y el título "Bienvenido(a)..." se verá perfectamente en la parte superior izquierda sin ningún elemento que lo tape. ¡Descarga el archivo y pruébalo!




Los chats de ayvi sa de cv no se usan para mejorar nuestros modelos. Gemini es una IA y puede cometer errores. Tu privacidad y GeminiSe abrirá en una ventana nueva

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
      "borderWidth": 2
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
window.ringSpacing = 150; 
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
        <div style="display: flex; gap: 15px;">
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 16px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 12px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 10px; border-radius: 12px; background: #eee; font-size: 14px; font-weight: bold; color: #333; margin-top: 2px;">-</span></div>
        </div>
        
        <hr style="border: 0; border-top: 2px dashed #ddd; margin: 5px 0;">
        <div style="font-size: 14px; color: #1565c0; font-weight: bold; text-transform: uppercase; margin-bottom: -5px;">🔥 Nivel de Enganche:</div>
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">INDIVIDUAL</span><br><span id="fEngInd" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
            <div style="flex: 1;"><span style="font-size: 11px; color: #777; font-weight: bold;">DEL ÁREA (EQUIPO)</span><br><span id="fEngArea" style="display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eee; font-size: 16px; font-weight: bold; color: #333; margin-top: 2px; width: 100%; text-align: center;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="3500" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">150px</span>
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
}

network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.3; 
    var maxScale = 2.5; 
    
    if (currentScale < minScale) {
        network.moveTo({ scale: minScale });
    } else if (currentScale > maxScale) {
        network.moveTo({ scale: maxScale });
    }
});

function getColorEnganche(val) {
    if (val >= 4) return {bg: "#dcfce7", text: "#166534"}; 
    if (val >= 3) return {bg: "#fef08a", text: "#854d0e"}; 
    if (val >= 2) return {bg: "#ffedd5", text: "#9f1239"}; 
    if (val >= 1) return {bg: "#fee2e2", text: "#991b1b"}; 
    return {bg: "#f8f9fa", text: "#64748b"}; 
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
        
        var engInd = node.Eng_Ind !== undefined ? parseFloat(node.Eng_Ind) : 0;
        var fEngInd = document.getElementById('fEngInd');
        if (engInd > 0) {
            fEngInd.innerText = engInd.toFixed(1);
            var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg;
            fEngInd.style.color = colorInd.text;
        } else {
            fEngInd.innerText = "N/A";
            fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333";
        }
        
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1);
            var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg;
            fEngArea.style.color = colorArea.text;
        } else {
            fEngArea.innerText = "N/A";
            fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333";
        }
        
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

        var colorBg = typeof node.color === 'object' ? node.color.background : node.color;
        var boxResult = node.Resultado_9Box || "N/A";
        var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult;
        f9Box.style.backgroundColor = colorBg || "#eee";
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
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, {
            scale: 0.85,
            animation: { duration: 800, easingFunction: 'easeInOutQuad' }
        });
    } else {
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
}

setTimeout(function() {
    applyVisualFilters();
    enfocarPantalla();
}, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES DE DISEÑO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
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
    st.set_page_config(page_title="Portal de Talento Ayvi", layout="wide")
    
    if "usuario_logueado" not in st.session_state:
        st.session_state["usuario_logueado"] = False

    if not st.session_state["usuario_logueado"]:
        usuarios_autorizados = obtener_usuarios_autorizados()
        
        st.markdown("<h1 style='text-align: center; color: #1976d2;'>🔐 Portal de Talento Ayvi</h1>", unsafe_allow_html=True)
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

def acortar_nombre(nombre_completo):
    if not nombre_completo: return ""
    partes = str(nombre_completo).strip().split()
    
    if len(partes) <= 2:
        return nombre_completo
    elif len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    else:
        return f"{partes[0]} {partes[-2]}"

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
        
        enganche_key = next((k for k in row_dict.keys() if k and 'enganche' in str(k).lower()), None)
        if enganche_key:
            try:
                eng_val = float(row_dict[enganche_key])
            except:
                eng_val = 0.0
        else:
            eng_val = 0.0
        
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
                'read3': clean_text(row_dict.get('Tiempo de Readiness 3'), ''),
                'enganche_ind': eng_val,
                'enganche_area': 0.0,
                'es_lider': False
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
        if jefe in info_nodos:
            info_nodos[jefe]['es_lider'] = True

    enganche_area_dict = {}
    for nodo in G_jerarquia.nodes():
        descendientes = nx.descendants(G_jerarquia, nodo)
        if not descendientes:
            enganche_area_dict[nodo] = 0.0
            continue
            
        suma = 0.0
        count = 0
        for d in descendientes:
            if d in info_nodos:
                val = info_nodos[d]['enganche_ind']
                if val > 0:
                    suma += val
                    count += 1
        
        enganche_area_dict[nodo] = round(suma / count, 1) if count > 0 else 0.0
    
    for emp in info_nodos:
        info_nodos[emp]['enganche_area'] = enganche_area_dict.get(emp, 0.0)

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
        r_list = []
        
        if info['mla'] != '5':
            es_critica = (info['critica'].lower() == 'si')
            tiene_oficial = (sucesores_oficiales_de.get(emp, 0) > 0)
            tiene_hipos_9box = (sucesores_de_9box.get(emp, 0) > 0)
            
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
                
            eng_ind = info['enganche_ind']
            if 1.0 <= eng_ind < 2.0:
                r_list.append("🚨 Riesgo de Fuga: Colaborador Desconectado")
            elif 2.0 <= eng_ind < 3.0:
                r_list.append("⚠️ Alerta: Bajo Enganche (Desinterés)")
                
            if info['es_lider']:
                eng_area = info['enganche_area']
                if 1.0 <= eng_area < 2.0:
                    r_list.append("🚨 Riesgo de Área: Equipo Desconectado")
                elif 2.0 <= eng_area < 3.0:
                    r_list.append("⚠️ Alerta de Área: Bajo Enganche del Equipo")
                
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
            
    nodo_central_id = raiz_principal
    if f_lid != "Todos":
        for emp, inf in info_nodos.items():
            if inf['nombre'] == f_lid:
                nodo_central_id = emp
                break
    elif f_dir != "Todas":
        candidatos = [emp for emp in nodos_visibles if info_nodos[emp]['direccion'] == f_dir]
        if candidatos:
            def mla_val(x):
                val = info_nodos[x]['mla']
                return int(val) if val.isdigit() else 0
            nodo_central_id = max(candidatos, key=mla_val)

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
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
    data_total = []
    data_criticas = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    
    for emp, info in info_nodos.items():
        is_hidden = emp not in nodos_visibles
        
        nom_suc1 = nombres_dict.get(info['suc1_id'], info['suc1_id']) if info['suc1_id'] else ""
        nom_suc2 = nombres_dict.get(info['suc2_id'], info['suc2_id']) if info['suc2_id'] else ""
        nom_suc3 = nombres_dict.get(info['suc3_id'], info['suc3_id']) if info['suc3_id'] else ""
        
        if not is_hidden:
            nodo_data = {"Nombre": info['nombre'], "Dirección": info['direccion'], "Puesto": info['puesto']}
            data_total.append(nodo_data)
            
            if info['critica'].lower() == 'si':
                data_criticas.append(nodo_data)
                
            if info['suc1_id']:
                target_id = info['suc1_id']
                puesto_target = "Posición no encontrada"
                if target_id in info_nodos:
                    puesto_target = info_nodos[target_id]['puesto']
                
                data_sucesores.append({
                    "Colaborador": info['nombre'],        
                    "Posición Actual": info['puesto'],    
                    "Posición a Suceder": puesto_target   
                })
                
            if info['mla'] == '1':
                data_operativos.append(nodo_data)
                
            if info['es_lider']:
                data_enganche.append({
                    "Líder": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Enganche Individual": info['enganche_ind'] if info['enganche_ind'] > 0 else "N/A",
                    "Enganche del Área": info['enganche_area'] if info['enganche_area'] > 0 else "N/A"
                })
                
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
        
        nombre_corto = acortar_nombre(info['nombre'])
        
        eng = info['enganche_ind']
        if eng >= 4:
            color_sombreado = 'rgba(22, 163, 74, 0.8)' 
        elif eng >= 3:
            color_sombreado = 'rgba(234, 179, 8, 0.8)' 
        elif eng >= 2:
            color_sombreado = 'rgba(249, 115, 22, 0.8)' 
        elif eng > 0:
            color_sombreado = 'rgba(220, 38, 38, 0.8)' 
        else:
            color_sombreado = 'rgba(0, 0, 0, 0.2)' 
        
        G.add_node(
            emp, 
            label=f"{prefijo}{nombre_corto}
({info['puesto']})", 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
            hidden=is_hidden
        )

    for jefe, emp in G_jerarquia.edges():
        is_hidden_edge = jefe not in nodos_visibles or emp not in nodos_visibles
        
        eng_emp = info_nodos[emp]['enganche_ind']
        if eng_emp >= 4:
            color_edge_shadow = 'rgba(22, 163, 74, 0.8)'
        elif eng_emp >= 3:
            color_edge_shadow = 'rgba(234, 179, 8, 0.8)'
        elif eng_emp >= 2:
            color_edge_shadow = 'rgba(249, 115, 22, 0.8)'
        elif eng_emp > 0:
            color_edge_shadow = 'rgba(220, 38, 38, 0.8)'
        else:
            color_edge_shadow = 'rgba(0, 0, 0, 0.0)' 
            
        G.add_edge(jefe, emp, color='#94a3b8', width=2, dashes=False, title='Estructura', hidden=is_hidden_edge, is_struct=True, is_9box=False, is_succ=False, smooth=False, shadow={'enabled': True, 'color': color_edge_shadow, 'size': 15, 'x': 0, 'y': 0})

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

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0)
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'criticas': len(data_criticas),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'data_total': data_total,
        'data_criticas': data_criticas,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche
    }
    
    df_alertas = pd.DataFrame(alertas_tabla)
    
    net = Network(height='750px', width='100%', bgcolor='#ffffff', font_color='#333333', directed=True, cdn_resources='remote')
    net.from_nx(G)
    net.set_options(OPCIONES_PYVIS)
    
    html = net.generate_html()
    
    script_foco = f"""
    <script>
    window.targetNodeId = "{nodo_central_id}";
    </script>
    """
    
    html = html.replace('</body>', BOTON_HTML + '\n' + SCRIPT_ANILLOS + '\n' + script_foco + '\n</body>')
    
    return html, df_alertas, kpis

# ==========================================
# INTERFAZ PRINCIPAL DE LA PLATAFORMA WEB
# ==========================================
def main():
    if not login():
        st.stop()
        
    if "vista_kpi" not in st.session_state:
        st.session_state["vista_kpi"] = None
        
    st.markdown("""
        <style>
        /* OCULTAR EL HEADER (BARRA SUPERIOR) DE STREAMLIT */
        [data-testid="stHeader"] {
            display: none !important;
        }
        /* OCULTAR MENÚ DE HAMBURGUESA */
        #MainMenu {
            visibility: hidden !important;
        }
        /* OCULTAR EL FOOTER */
        footer {
            visibility: hidden !important;
        }
        
        /* AJUSTAR MÁRGENES PARA QUE NO QUEDE PEGADO ARRIBA AL QUITAR EL HEADER */
        .block-container { 
            padding-top: 2rem !important; 
            padding-bottom: 0rem !important; 
        }
        
        div[data-testid="stButton"] > button {
            padding: 2px 10px;
            font-size: 12px;
            height: auto;
            min-height: 28px;
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
        
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        
        f_dir = col_f1.selectbox("Dirección", ["Todas"] + dirs)
        
        dict_nom = {clean_id(row.get('id Empleado')): clean_text(row.get('Nombre')) for row in df_seguro.to_dict('records')}
        if f_dir != "Todas":
            df_filtrado_dir = df_seguro[df_seguro['Dirección'].apply(clean_text) == f_dir]
            lideres_ids = df_filtrado_dir['ID Del Jefe'].dropna().unique()
        else:
            lideres_ids = df_seguro['ID Del Jefe'].dropna().unique()
            
        lideres = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids if clean_id(x)])))
        
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
                
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                
                with k1:
                    st.markdown(crear_tarjeta_kpi("Total<br>Colab.", kpis['total'], "#3b82f6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_tot", use_container_width=True):
                        st.session_state["vista_kpi"] = "total"
                with k2:
                    st.markdown(crear_tarjeta_kpi("Pos.<br>Críticas", kpis['criticas'], "#ef4444", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_cri", use_container_width=True):
                        st.session_state["vista_kpi"] = "criticas"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Colab.<br>Sucesión", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k4:
                    st.markdown(crear_tarjeta_kpi("Operat.<br>(MLA 1)", kpis['operativos'], "#10b981", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ope", use_container_width=True):
                        st.session_state["vista_kpi"] = "operativos"
                with k5:
                    st.markdown(crear_tarjeta_kpi("Alertas<br>Detect.", kpis['alertas'], "#e11d48", "#9f1239", "#fff1f2"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_ale", use_container_width=True):
                        st.session_state["vista_kpi"] = "alertas"
                with k6:
                    st.markdown(crear_tarjeta_kpi("Promedio<br>Enganche", kpis['enganche_promedio'], "#14b8a6", "#0f766e", "#f0fdfa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_eng", use_container_width=True):
                        st.session_state["vista_kpi"] = "enganche"
                
                if st.session_state["vista_kpi"]:
                    vista = st.session_state["vista_kpi"]
                    titulos_kpi = {
                        "total": "Total de Colaboradores",
                        "criticas": "Posiciones Críticas",
                        "sucesores": "Colaboradores en Sucesión",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
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
app_web.py
Mostrando app_web.py.
