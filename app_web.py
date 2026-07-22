import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import math
import streamlit.components.v1 as components
import re
import gspread
from google.oauth2.service_account import Credentials

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
        <div style="display: flex; gap: 10px;">
            <div><span style="font-size: 11px; color: #777; font-weight: bold;">NIVEL MLA</span><br><span id="fMLA" style="font-size: 15px; font-weight: bold; color: #1976d2;">-</span></div>
            <div><span style="font-size: 11px; color: #777; font-weight: bold;">9-BOX</span><br><span id="f9Box" style="display: inline-block; padding: 2px 8px; border-radius: 12px; background: #eee; font-size: 13px; font-weight: bold; color: #333;">-</span></div>
            <div><span style="font-size: 11px; color: #777; font-weight: bold;">EDR</span><br><span id="fEDR" style="display: inline-block; padding: 2px 8px; border-radius: 12px; background: #e0f2fe; font-size: 12px; font-weight: bold; color: #0369a1;">-</span></div>
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
                <input type="range" id="sliderSeparacion" min="100" max="800" value="150" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
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
        
        if (anillo !== undefined && angle !== undefined) {
            var nuevoRadio = anillo * window.ringSpacing;
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
        document.getElementById('fEDR').innerText = node.EDR || "Pendiente";
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
# DESCARGA DIRECTA Y SEGURA CON GSPREAD
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def cargar_datos_csv(url_sheets, nombre_pestana):
    try:
        secretos = st.secrets["connections"]["gsheets"]
        credenciales = Credentials.from_service_account_info(
            secretos,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        cliente = gspread.authorize(credenciales)
        
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheets)
        doc_id = match.group(1) if match else url_sheets
        
        archivo = cliente.open_by_key(doc_id)
        pestana = archivo.worksheet(nombre_pestana)
        
        datos = pestana.get_all_values()
        
        if datos:
            df = pd.DataFrame(datos[1:], columns=datos[0])
        else:
            df = pd.DataFrame()
            
        df.columns = [str(col).strip() for col in df.columns]
        return df
        
    except KeyError:
        st.error("🤖 Error: No se encontraron los secretos en la nube. Revisa que el cuadro negro de 'Secrets' empiece exactamente con [connections.gsheets]")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"🤖 Error técnico del Robot: {e}")
        return pd.DataFrame()

# ==========================================
# FIX: FUNCIÓN MEJORADA PARA IGNORAR COLUMNAS REPETIDAS
# ==========================================
def clean_text(val, default=''):
    if isinstance(val, pd.Series):
        val = val.iloc[0] if not val.empty else default
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'pendiente', '']:
        return default
    return str(val).strip()

def clean_id(val):
    if isinstance(val, pd.Series):
        val = val.iloc[0] if not val.empty else ''
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

def acortar_puesto(puesto):
    """Acorta los nombres de puestos largos para la etiqueta del mapa"""
    if not puesto: return ""
    p = str(puesto).strip().upper()
    
    reemplazos = {
        "RECURSOS HUMANOS": "RH",
        "TALENTO Y CULTURA": "TYC",
        "DESARROLLO ORGANIZACIONAL": "D.O.",
        "ADMINISTRATIVO": "ADM.",
        "ADMINISTRATIVA": "ADM.",
        "ADMINISTRADOR DE ": "ADMIN. ",
        "ADMINISTRADOR ": "ADMIN. ",
        "COORDINADOR DE ": "COORD. ",
        "COORDINADORA DE ": "COORD. ",
        "COORDINADOR ": "COORD. ",
        "COORDINADORA ": "COORD. ",
        "ESPECIALISTA EN ": "ESP. ",
        "ESPECIALISTA ": "ESP. ",
        "SUPERVISOR DE ": "SUP. ",
        "SUPERVISORA DE ": "SUP. ",
        "SUPERVISOR ": "SUP. ",
        "SUPERVISORA ": "SUP. ",
        "GERENTE DE ": "GTE. ",
        "GERENTE ": "GTE. ",
        "DIRECTOR DE ": "DIR. ",
        "DIRECTORA DE ": "DIR. ",
        "DIRECTOR ": "DIR. ",
        "DIRECTORA ": "DIR. ",
        "JEFE DE ": "JEFE ",
        "ADQUISICIÓN": "ADQ.",
        "ADQUISICION": "ADQ.",
        "TRANSFORMACIÓN": "TRANSF.",
        "TRANSFORMACION": "TRANSF.",
        "SUCURSAL": "SUC.",
        "OPERACIONES": "OP.",
        "MANTENIMIENTO": "MANTTO.",
        "PRODUCCIÓN": "PROD.",
        "PRODUCCION": "PROD.",
        "TECNOLOGÍA": "TECH",
        "TECNOLOGIA": "TECH",
        "INFORMACIÓN": "INFO.",
        "INFORMACION": "INFO.",
        "COMERCIAL": "COM.",
        "DISTRIBUCIÓN": "DIST.",
        "DISTRIBUCION": "DIST.",
        "LOGÍSTICA": "LOG.",
        "LOGISTICA": "LOG.",
        "SISTEMAS": "SIST.",
        "PROYECTOS": "PROY.",
        "NACIONAL": "NAL.",
        "REGIONAL": "REG.",
        "EJECUTIVO": "EJEC.",
        "EJECUTIVA": "EJEC.",
        "REPRESENTANTE": "REP.",
        "ASISTENTE": "ASIST.",
        "AUXILIAR": "AUX."
    }
    
    for original, abrev in reemplazos.items():
        p = p.replace(original, abrev)
    
    if len(p) > 35:
        p = p[:32] + "..."
        
    return p

def get_readiness_val(rt_str):
    """Función para el estilo de las flechas punteadas"""
    rt = str(rt_str).strip().lower()
    if not rt or rt == 'pendiente' or rt == 'nan' or rt == 'none': return 4
    if 'inmediato' in rt or 'listo' in rt or '0' in rt: return 1
    if '1' in rt or '2' in rt or 'medio' in rt: return 2
    if '3' in rt or '4' in rt or '5' in rt or 'más' in rt or 'mas' in rt or 'largo' in rt: return 3
    return 4

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
def generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_mla, f_box, f_edr, f_riesgos):
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
    
    puesto_a_id = {}
    for row in df_seguro.to_dict('records'):
        emp_id = clean_id(row.get('id Empleado'))
        puesto = clean_text(row.get('Nombre de la Posición')).lower()
        if emp_id and puesto and puesto not in puesto_a_id:
            puesto_a_id[puesto] = emp_id

    def buscar_id_real(valor):
        if pd.isna(valor) or str(valor).strip().lower() in ['nan', 'none', 'pendiente', '']: 
            return ''
        v = str(valor).strip()
        if v.endswith('.0'): 
            v = v[:-2]
        
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
            
            edr_val = clean_text(row_dict.get('EDR', row_dict.get('EDR ')), 'Pendiente')
            
            info_nodos[emp] = {
                'mla': clean_text(row_dict.get('Nivel MLA'), 'N/A'),
                'puesto': clean_text(row_dict.get('Nombre de la Posición')).upper(),
                'direccion': clean_text(row_dict.get('Dirección', row_dict.get('Direccion')), 'No asignada'),
                'box': clean_text(row_dict.get('Resultado 9 box'), 'Pendiente'),
                'edr': edr_val,
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

    nombres_con_pdi = set()
    if not df_pdi.empty and 'Nombre' in df_pdi.columns:
        nombres_con_pdi = set(df_pdi['Nombre'].dropna().astype(str).str.strip().str.lower())

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

            edr_txt = info['edr'].lower()
            if '1.resultado inaceptable' in edr_txt or 'inaceptable' in edr_txt:
                r_list.append("🚨 EDR Crítico: Resultado Inaceptable")
            elif '2.resultado necesita mejorar' in edr_txt or 'necesita mejorar' in edr_txt:
                r_list.append("⚠️ EDR Bajo: Necesita Mejorar")

            if info['nombre'].strip().lower() not in nombres_con_pdi:
                r_list.append("⚠️ Sin PDI: No tiene Plan de Desarrollo Individual")
                
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
        if f_edr != "Todos" and info['edr'] != f_edr: continue
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

    nodos_activos = set(nodos_visibles)
    if raiz_principal and raiz_principal in G_jerarquia:
        for v in nodos_visibles:
            if v in G_jerarquia:
                try:
                    nodos_activos.update(nx.ancestors(G_jerarquia, v))
                except nx.NetworkXError:
                    pass

    Arbol = nx.bfs_tree(G_jerarquia, raiz_principal) if raiz_principal else G_jerarquia

    def obtener_anillo_estricto(emp_id, depth_arbol):
        mla = info_nodos.get(emp_id, {}).get('mla', '')
        mla = str(mla).replace('.0', '').strip() 
        if mla == '5': return 0
        if mla == '4': return 1 
        if mla == '3': return 2 
        if mla == '2': return 3 
        if mla == '1': return 4 
        return min(depth_arbol, 5)

    SEPARACION_ANILLOS = 150 
    conteo_hojas = {}
    
    def calcular_hojas(n):
        hijos = [c for c in Arbol.successors(n) if c in nodos_activos]
        if not hijos:
            val = 1 if n in nodos_visibles else 0
            conteo_hojas[n] = val
            return val
        total = sum(calcular_hojas(c) for c in hijos)
        if total == 0 and n in nodos_visibles:
            total = 1
        conteo_hojas[n] = total
        return total

    if raiz_principal: 
        calcular_hojas(raiz_principal)

    coords = {}
    def asignar_coordenada_radial(nodo, angulo_inicio, angulo_fin):
        hijos = [c for c in Arbol.successors(nodo) if c in nodos_activos]
        if not hijos: 
            return
        hojas_totales = sum(conteo_hojas.get(c, 0) for c in hijos)
        if hojas_totales == 0: 
            return
            
        angulo_actual = angulo_inicio
        for i, c in enumerate(hijos):
            peso = conteo_hojas.get(c, 0)
            if peso == 0:
                continue
            rebanada = (peso / hojas_totales) * (angulo_fin - angulo_inicio)
            angulo_hijo = angulo_actual + (rebanada / 2)
            profundidad = nx.shortest_path_length(Arbol, raiz_principal, c) if raiz_principal and c in Arbol else 5
            anillo_real = obtener_anillo_estricto(c, profundidad)
            
            coords[c] = {
                'x': (anillo_real * SEPARACION_ANILLOS) * math.cos(angulo_hijo) if anillo_real != 0 else 0, 
                'y': (anillo_real * SEPARACION_ANILLOS) * math.sin(angulo_hijo) if anillo_real != 0 else 0, 
                'angle': angulo_hijo, 
                'anillo_real': anillo_real, 
                'profundidad': profundidad
            }
            
            asignar_coordenada_radial(c, angulo_actual, angulo_actual + rebanada)
            angulo_actual += rebanada

    if raiz_principal:
        coords[raiz_principal] = {'x': 0, 'y': 0, 'angle': 0, 'anillo_real': 0, 'profundidad': 0}
        asignar_coordenada_radial(raiz_principal, 0, 2 * math.pi)

    nodos_sin_coords = [n for n in G_jerarquia.nodes() if n not in coords and n in nodos_visibles]
    if nodos_sin_coords:
        angulo_extra = (2 * math.pi) / len(nodos_sin_coords)
        angulo_actual = 0
        for n in nodos_sin_coords:
            anillo = obtener_anillo_estricto(n, 5)
            radio = (anillo * SEPARACION_ANILLOS) if anillo != 0 else 80
            coords[n] = {'x': radio * math.cos(angulo_actual), 'y': radio * math.sin(angulo_actual), 'angle': angulo_actual, 'anillo_real': anillo, 'profundidad': 5}
            angulo_actual += angulo_extra

    alertas_tabla = []
    data_total = []
    data_sucesores = []
    data_operativos = []
    data_enganche = []
    data_edr = []
    
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
                data_edr.append({
                    "Nombre": info['nombre'],
                    "Puesto": info['puesto'],
                    "Dirección": info['direccion'],
                    "Resultado EDR": info['edr']
                })
                
                if info['critica'].lower() == 'si':
                    target_id = info['suc1_id']
                    nom_suc = nom_suc1 if nom_suc1 else "Pendiente"
                    puesto_suc = "Pendiente"
                    
                    if target_id in info_nodos:
                        puesto_suc = info_nodos[target_id]['puesto']
                    elif target_id:
                        puesto_suc = target_id
                    
                    tiempo_suc = info['read1'] if info['read1'] else "Pendiente"
                    
                    data_sucesores.append({
                        "Ocupante Actual": info['nombre'],
                        "Posición Crítica": info['puesto'],
                        "Dirección": info['direccion'],
                        "Nombre del Sucesor": nom_suc,
                        "Puesto del Sucesor": puesto_suc,
                        "Tiempo de Sucesión": tiempo_suc
                    })
                    
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

            if info['mla'] == '1':
                data_operativos.append(nodo_data)

        prefijo = "🚨 " if info['riesgos_lista'] else ""
        coord_data = coords.get(emp, {'x':5000, 'y':5000, 'angle':0, 'anillo_real':5, 'profundidad':5})
        
        nombre_corto = acortar_nombre(info['nombre'])
        puesto_corto = acortar_puesto(info['puesto'])
        
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
            
        label_texto = f"{prefijo}{nombre_corto}\n({puesto_corto})"
        
        G.add_node(
            emp, 
            label=label_texto, 
            title=f"<div style='padding: 5px; text-align: center;'><b>{prefijo}{info['nombre']}</b><br><small>{info['puesto']}</small></div>", 
            size=28 if emp == raiz_principal else 18, 
            color=obtener_color_9box(info['box']), 
            shadow={'enabled': True, 'color': color_sombreado, 'size': 25, 'x': 0, 'y': 0}, 
            shape='dot', group=info['mla'], 
            Nivel_MLA=info['mla'], Resultado_9Box=info['box'], EDR=info['edr'], Direccion=info['direccion'], Lider=info['lider'], 
            Critica=info['critica'], Nombre=info['nombre'], Puesto=info['puesto'], Riesgos=info['riesgos'], Interes=info['interes'], 
            NomSuc1=nom_suc1, Read1=info['read1'], NomSuc2=nom_suc2, Read2=info['read2'], NomSuc3=nom_suc3, Read3=info['read3'],
            Eng_Ind=info['enganche_ind'], Eng_Area=info['enganche_area'], Es_Lider=info['es_lider'],
            font={'color': '#0f172a', 'strokeWidth': 2, 'strokeColor': '#ffffff', 'size': 11, 'face': 'Arial', 'weight': 'bold'},
            x=coord_data['x'], y=coord_data['y'], Angle=coord_data['angle'], 
            AnilloReal=coord_data['anillo_real'], Profundidad=coord_data['profundidad'],
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
            
        for s_id, read_time in [(info['suc1_id'], info['read1']), (info['suc2_id'], info['read2']), (info['suc3_id'], info['read3'])]:
            if s_id and s_id in empleados_validos:
                is_hidden_edge = (emp not in nodos_visibles or s_id not in nodos_visibles)
                
                val = get_readiness_val(read_time)
                if val == 1:
                    dashes_style = False 
                    edge_width = 6
                elif val == 2:
                    dashes_style = [10, 10] 
                    edge_width = 4
                else:
                    dashes_style = [4, 8] 
                    edge_width = 2
                    
                G.add_edge(emp, s_id, color='#9c27b0', width=edge_width, dashes=dashes_style, title=f'🎯 Sucesor: {read_time}', hidden=is_hidden_edge, is_struct=False, is_9box=False, is_succ=True, smooth={'enabled': True, 'type': 'curvedCW', 'roundness': 0.6})

    data_alertas = [
        {
            "Nombre": a['Colaborador'], 
            "Dirección": a['Dirección'], 
            "Puesto": a['Puesto'],
            "Alerta": a['Alerta Detectada por IA']
        } 
        for a in alertas_tabla
    ]
    
    eng_total_sum = sum(info_nodos[n]['enganche_ind'] for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0 and 'ANDRES EDUARDO VILLARREAL' not in info_nodos[n]['nombre'].upper())
    eng_total_count = sum(1 for n in nodos_visibles if info_nodos[n]['enganche_ind'] > 0 and 'ANDRES EDUARDO VILLARREAL' not in info_nodos[n]['nombre'].upper())
    avg_enganche = round(eng_total_sum / eng_total_count, 1) if eng_total_count > 0 else 0.0
    
    kpis = {
        'total': len(data_total),
        'sucesores': len(data_sucesores),
        'operativos': len(data_operativos),
        'alertas': len(alertas_tabla),
        'enganche_promedio': avg_enganche,
        'edr_count': len(data_edr),
        'data_total': data_total,
        'data_sucesores': data_sucesores,
        'data_operativos': data_operativos,
        'data_alertas': data_alertas,
        'data_enganche': data_enganche,
        'data_edr': data_edr
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
        [data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
        div[data-testid="stButton"] > button { padding: 2px 10px; font-size: 12px; height: auto; min-height: 28px; }
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

    with st.spinner("Cargando mapa con conexiones lógicas y datos de PDI..."):
        
        link_archivo = "https://docs.google.com/spreadsheets/d/125WBSXsBceU3kDTX-ZY6OXlVr2Dgza8xnPMusw6OU7k/edit"
        
        df_completo = cargar_datos_csv(link_archivo, "Base de datos")
        df_pdi = cargar_datos_csv(link_archivo, "PDI")
        
        if df_completo.empty:
            st.error("Error al conectar con la base de datos de Google Sheets principal. Revisa el mensaje técnico arriba.")
            st.stop()

        usuarios_autorizados = obtener_usuarios_autorizados()
        direccion_permitida = usuarios_autorizados[st.session_state["id_usuario"]]["direccion"]
        
        if direccion_permitida != "TODAS":
            df_seguro = df_completo[(df_completo['Dirección'].astype(str).str.upper().str.contains(direccion_permitida)) | (df_completo['Nivel MLA'].astype(str).str.strip() == '5')]
        else:
            df_seguro = df_completo.copy()

        # --- AÑADIDO: BUSCADOR RÁPIDO DE COLABORADORES EN LA CABECERA ---
        col_head1, col_head2 = st.columns([2, 1])
        with col_head1:
            st.markdown("### 🎛️ Filtros Globales (Controlan Mapa, KPIs y Tablas)")
            
        with col_head2:
            lista_nombres_buscador = sorted([clean_text(n) for n in df_seguro['Nombre'].dropna().unique() if clean_text(n)])
            colab_buscado = st.selectbox("🔍 Búsqueda rápida de colaborador:", [""] + lista_nombres_buscador)

        if colab_buscado:
            datos_c = df_seguro[df_seguro['Nombre'].apply(lambda x: clean_text(x)) == colab_buscado].iloc[0]
            p_puesto = clean_text(datos_c.get('Nombre de la Posición', 'N/A'))
            p_dir = clean_text(datos_c.get('Dirección', datos_c.get('Direccion', 'N/A')))
            p_box = clean_text(datos_c.get('Resultado 9 box', 'N/A'))
            edr_key = 'EDR' if 'EDR' in datos_c else ('EDR ' if 'EDR ' in datos_c else None)
            p_edr = clean_text(datos_c.get(edr_key, 'N/A')) if edr_key else 'N/A'
            p_mla = clean_text(datos_c.get('Nivel MLA', 'N/A'))
            
            st.success(f"👤 **{colab_buscado}** | 🏢 **Puesto:** {p_puesto} | 📍 **Dirección:** {p_dir} | 📊 **9-Box:** {p_box} | 📈 **EDR:** {p_edr} | 🥇 **Nivel MLA:** {p_mla}")
        # -----------------------------------------------------------------
        
        dirs = sorted([clean_text(x) for x in df_seguro['Dirección'].unique() if clean_text(x)])
        mlas = sorted([clean_text(x) for x in df_seguro['Nivel MLA'].unique() if clean_text(x)])
        boxes = sorted([clean_text(x).upper() for x in df_seguro['Resultado 9 box'].unique() if clean_text(x)])
        criticas = sorted([clean_text(x) for x in df_seguro['Posición Crítica'].unique() if clean_text(x)])
        
        edrs_col = 'EDR' if 'EDR' in df_seguro.columns else ('EDR ' if 'EDR ' in df_seguro.columns else None)
        edrs = sorted([clean_text(x) for x in df_seguro[edrs_col].unique() if clean_text(x)]) if edrs_col else []
        
        col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
        
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
        f_edr = col_f6.selectbox("EDR (Resultados)", ["Todos"] + edrs)
        
        f_riesgos = st.checkbox("🚨 Mostrar Solo Colaboradores con Riesgos Detectados (Incluye riesgo PDI y EDR)")
        st.write("") 

        html_mapa, df_alertas, kpis = generar_mapa_html(df_seguro, df_pdi, f_dir, f_lid, f_crit, f_mla, f_box, f_edr, f_riesgos)
        
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
                    st.markdown(crear_tarjeta_kpi("Sucesión<br>(Pos. Críticas)", kpis['sucesores'], "#8b5cf6", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_suc", use_container_width=True):
                        st.session_state["vista_kpi"] = "sucesores"
                with k3:
                    st.markdown(crear_tarjeta_kpi("Desempeño<br>(EDR)", kpis['edr_count'], "#0284c7", "#64748b", "#f8f9fa"), unsafe_allow_html=True)
                    if st.button("🔍 Ver", key="b_edr", use_container_width=True):
                        st.session_state["vista_kpi"] = "edr"
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
                        "sucesores": "Sucesión de Posiciones Críticas",
                        "edr": "Evaluación de Desempeño y Resultados (EDR)",
                        "operativos": "Personal Operativo (MLA 1)",
                        "alertas": "Colaboradores con Riesgos / Alertas",
                        "enganche": "Nivel de Enganche de Líderes"
                    }
                    
                    st.markdown(f"#### 📋 {titulos_kpi[vista]}")
                    df_lista = pd.DataFrame(kpis[f"data_{vista}"])
                    
                    if not df_lista.empty:
                        if vista == "alertas":
                            df_lista = df_lista.drop_duplicates(subset=["Nombre", "Alerta"]).reset_index(drop=True)
                            
                        if direccion_permitida != "TODAS" and "Dirección" in df_lista.columns:
                            df_lista = df_lista.drop(columns=["Dirección"])
                            
                        st.dataframe(df_lista, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros en esta categoría.")
                        
                    if st.button("❌ Cerrar Lista", use_container_width=True):
                        st.session_state["vista_kpi"] = None
                        st.rerun()
            
            st.divider()
            
            # ==========================================
            # PLANIFICADOR DE SUCESIONES + IA SEMÁNTICA (NLP)
            # ==========================================
            st.markdown("### 🔀 Planificador de Sucesiones (Edición en Vivo)")
            st.markdown("Usa este panel para asignar o modificar los sucesores. **Los cambios se guardarán automáticamente en tu Excel** y el mapa se actualizará al instante.")
            
            df_posiciones_filtradas = df_seguro.copy()
            df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['Posición Crítica'].apply(clean_text).str.lower() == 'si']
            
            col_plan1, col_plan2, col_plan3 = st.columns(3)
            
            dirs_plan = sorted(list(set([clean_text(x) for x in df_posiciones_filtradas['Dirección'].unique() if clean_text(x)])))
            f_dir_plan = col_plan1.selectbox("🏢 Filtrar por Dirección:", ["Todas"] + dirs_plan, key="plan_dir")
            
            if f_dir_plan != "Todas":
                df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['Dirección'].apply(clean_text) == f_dir_plan]
            
            lideres_ids_plan = df_posiciones_filtradas['ID Del Jefe'].dropna().unique()
            lideres_plan = sorted(list(set([dict_nom.get(clean_id(x), "Sin Líder") for x in lideres_ids_plan if clean_id(x)])))
            
            f_lid_plan = col_plan2.selectbox("👤 Filtrar por Líder:", ["Todos"] + lideres_plan, key="plan_lid")
            
            if f_lid_plan != "Todos":
                df_posiciones_filtradas['Nombre_Lider'] = df_posiciones_filtradas['ID Del Jefe'].apply(lambda x: dict_nom.get(clean_id(x), "Sin Líder"))
                df_posiciones_filtradas = df_posiciones_filtradas[df_posiciones_filtradas['Nombre_Lider'] == f_lid_plan]
                
            posiciones_opciones = []
            mapa_indices = {}
            
            for idx, row in df_posiciones_filtradas.iterrows():
                puesto = clean_text(row.get('Nombre de la Posición'))
                if puesto:
                    posiciones_opciones.append(puesto)
                    mapa_indices[puesto] = idx 
                    
            posiciones_opciones = sorted(list(set(posiciones_opciones)))
            pos_seleccionada = col_plan3.selectbox("🔍 Selecciona la Posición Crítica:", [""] + posiciones_opciones, key="plan_pos")
            
            def obtener_ficha_candidato(nombre_cand):
                if not nombre_cand or nombre_cand == "Pendiente":
                    return None
                match_colab = df_completo[df_completo['Nombre'].astype(str).str.strip().str.lower() == nombre_cand.strip().lower()]
                if match_colab.empty: return None
                row_c = match_colab.iloc[0]
                dir_candidato = clean_text(row_c.get('Dirección', row_c.get('Direccion')), 'No asignada')
                if direccion_permitida != "TODAS" and not (direccion_permitida.upper() in dir_candidato.upper()):
                    return "RESTRINGIDO"
                puesto_actual = clean_text(row_c.get('Nombre de la Posición'), 'Puesto no asignado')
                box_c = clean_text(row_c.get('Resultado 9 box'), 'Pendiente')
                edr_c = clean_text(row_c.get('EDR', row_c.get('EDR ')), 'Pendiente')
                eng_key = next((k for k in row_c.keys() if k and 'enganche' in str(k).lower()), None)
                eng_c = clean_text(row_c.get(eng_key), 'N/A') if eng_key else 'N/A'
                return {"puesto_actual": puesto_actual, "direccion": dir_candidato, "box": box_c, "enganche": eng_c, "edr": edr_c}

            DICCIONARIO_MERCADO = {
                "sistemas_it": ["erp", "sistemas", "tecnologia", "informacion", "it", "software", "datos", "sap", "tecnico", "redes", "crm", "soporte", "programacion"],
                "abogado": ["legal", "juridico", "contratos", "litigio", "derecho", "normativa", "corporativo", "abogado"],
                "rh": ["talento", "recursos humanos", "cultura", "clima", "capacitacion", "atraccion", "beneficios", "compensaciones", "nomina", "laborales", "personal", "rh", "do"],
                "comercial": ["ventas", "clientes", "cuentas", "kam", "negocios", "mercado", "retail", "mayoreo", "comercial"],
                "operaciones": ["planta", "produccion", "mantenimiento", "calidad", "manufactura", "procesos", "industrial", "operacion"],
                "logistica": ["reparto", "distribucion", "almacen", "inventarios", "transporte", "cadena", "suministro", "logistica"],
                "finanzas": ["contabilidad", "tesoreria", "auditoria", "fiscal", "credito", "costos", "financiero", "finanzas"]
            }

            def extraer_contexto(texto):
                if not texto or pd.isna(texto): return set()
                t = str(texto).lower()
                stopwords = [' de ', ' del ', ' la ', ' las ', ' el ', ' los ', ' y ', ' en ', ' para ', ' con ', ' a ', ' al ']
                for sw in stopwords: t = t.replace(sw, ' ')
                
                palabras = set(re.findall(r'\b\w{3,}\b', t)) 
                
                jerarquias = {'gerente', 'jefe', 'coordinador', 'director', 'analista', 'auxiliar', 'especialista', 'encargado', 'asistente', 'control'}
                palabras = palabras - jerarquias
                
                contexto_ampliado = set(palabras)
                for palabra in palabras:
                    for key, valores in DICCIONARIO_MERCADO.items():
                        if key in palabra or palabra in key:
                            contexto_ampliado.update(valores)
                        if palabra in valores:
                            contexto_ampliado.update(valores)
                            
                return contexto_ampliado

            dict_pdi_textos = {}
            if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                col_obj = next((c for c in df_pdi.columns if 'objetivo' in str(c).lower()), None)
                col_acciones = next((c for c in df_pdi.columns if 'acciones' in str(c).lower() or 'qué' in str(c).lower()), None)
                for _, row_p in df_pdi.iterrows():
                    nom = clean_text(row_p.get('Nombre')).lower()
                    obj = clean_text(row_p.get(col_obj)) if col_obj else ""
                    acc = clean_text(row_p.get(col_acciones)) if col_acciones else ""
                    dict_pdi_textos[nom] = obj + " " + acc

            def generar_sugerencias_ia(pos_destino, info_pos_destino):
                if not pos_destino or df_completo.empty: return []
                
                mla_destino = clean_text(info_pos_destino.get('Nivel MLA'), '')
                ocupante_destino = clean_text(info_pos_destino.get('Nombre'), '').lower()
                
                contexto_destino = extraer_contexto(pos_destino)
                
                candidatos_sugeridos = []
                
                for _, row in df_completo.iterrows():
                    nombre = clean_text(row.get('Nombre'))
                    if not nombre or nombre.lower() == ocupante_destino: continue
                        
                    puesto_act = clean_text(row.get('Nombre de la Posición'))
                    if puesto_act.lower() == pos_destino.lower(): continue
                    
                    contexto_cand_puesto = extraer_contexto(puesto_act)
                    pdi_texto = dict_pdi_textos.get(nombre.lower(), "")
                    contexto_cand_pdi = extraer_contexto(pdi_texto)
                    
                    perfil_tecnico_candidato = contexto_cand_puesto.union(contexto_cand_pdi)
                    
                    if not contexto_destino.intersection(perfil_tecnico_candidato):
                        continue 
                    
                    box = clean_text(row.get('Resultado 9 box')).upper()
                    if box not in ['1', '2', '3', '4', '5', '6']: continue 
                    
                    mla_cand = clean_text(row.get('Nivel MLA'))
                    score = 0
                    razones = []
                    
                    if contexto_destino.intersection(contexto_cand_puesto):
                        score += 5
                        razones.append("Afinidad técnica en puesto actual")
                    elif contexto_destino.intersection(contexto_cand_pdi):
                        score += 4
                        razones.append("Desarrollando skills afines (PDI)")
                        
                    if box in ['1', '2', '3', '5']:
                        score += 4
                        razones.append("Alto Potencial (9-Box)")
                    elif box in ['4', '6']:
                        score += 2
                        razones.append("Desempeño Sólido")
                        
                    if mla_destino.isdigit() and mla_cand.isdigit():
                        diff = int(mla_destino) - int(mla_cand)
                        if diff == 1:
                            score += 3
                            razones.append("Listo para ascenso (Nivel contiguo)")
                        elif diff == 0:
                            score += 2
                            razones.append("Movimiento lateral orgánico")
                            
                    if score >= 7: 
                        candidatos_sugeridos.append({
                            'nombre': nombre,
                            'puesto': puesto_act,
                            'direccion': clean_text(row.get('Dirección')),
                            'box': box,
                            'score': score,
                            'razon': " | ".join(razones)
                        })
                        
                return sorted(candidatos_sugeridos, key=lambda x: x['score'], reverse=True)[:3]

            def diagnosticar_pdi_ia(nombre_cand, puesto_destino, info_cand):
                if not nombre_cand or nombre_cand == "Pendiente" or info_cand == "RESTRINGIDO" or not info_cand: return None
                if df_pdi.empty: return {"estatus": "SIN_DATOS", "msg": "No hay base de datos de PDI cargada."}
                
                match_pdi = df_pdi[df_pdi['Nombre'].astype(str).str.strip().str.lower() == nombre_cand.strip().lower()]
                if match_pdi.empty:
                    return {
                        "estatus": "SIN_PDI", 
                        "puesto_origen": info_cand['puesto_actual'],
                        "recomendacion": f"🚨 **Acción Requerida:** El colaborador ocupa el puesto de *{info_cand['puesto_actual']}* pero NO tiene un PDI registrado. Se requiere crear un PDI enfocado en cerrar las brechas hacia la posición de *{puesto_destino}*."
                    }
                
                col_obj = next((c for c in match_pdi.columns if 'objetivo' in str(c).lower()), None)
                col_avance = next((c for c in match_pdi.columns if 'avance' in str(c).lower()), None)
                col_acciones = next((c for c in match_pdi.columns if 'acciones' in str(c).lower() or 'qué' in str(c).lower()), None)
                
                row_p = match_pdi.iloc[0]
                obj_pdi = clean_text(row_p.get(col_obj), 'Sin objetivo definido') if col_obj else 'Sin objetivo'
                avance_pdi = clean_text(row_p.get(col_avance), '0%') if col_avance else '0%'
                acciones_pdi = clean_text(row_p.get(col_acciones), 'Sin acciones descritas') if col_acciones else 'Sin acciones'
                
                contexto_destino = extraer_contexto(puesto_destino)
                contexto_pdi = extraer_contexto(obj_pdi + " " + acciones_pdi)
                
                coincidencias = contexto_destino.intersection(contexto_pdi)
                puesto_origen = info_cand['puesto_actual']
                
                if len(coincidencias) > 0:
                    return {
                        "estatus": "ALINEADO", "icono": "✅", "titulo_estatus": "PDI Alineado a la Posición",
                        "color_borde": "#16a34a", "bg_color": "#f0fdf4", "puesto_origen": puesto_origen,
                        "objetivo": obj_pdi, "avance": avance_pdi, "acciones": acciones_pdi,
                        "recomendacion": f"El PDI actual está **correctamente enfocado** en la posición de *{puesto_destino}*. Con un avance del **{avance_pdi}**, las acciones en curso cubren las competencias requeridas. Mantenimiento del plan actual."
                    }
                else:
                    return {
                        "estatus": "REQUIERE_AJUSTE", "icono": "🟡", "titulo_estatus": "Ajuste Recomendado al PDI",
                        "color_borde": "#ca8a04", "bg_color": "#fefce8", "puesto_origen": puesto_origen,
                        "objetivo": obj_pdi, "avance": avance_pdi, "acciones": acciones_pdi,
                        "recomendacion": f"💡 **Recomendación IA:** El candidato actualmente es *{puesto_origen}*. Su PDI está orientado a '_{obj_pdi}_'. Para asegurar su éxito hacia *{puesto_destino}*, se recomienda **actualizar sus Acciones de Desarrollo** agregando competencias técnicas específicas del nuevo puesto."
                    }

            if pos_seleccionada:
                idx_pandas = mapa_indices[pos_seleccionada]
                info_pos = df_seguro.loc[idx_pandas]
                
                ocupante_actual = clean_text(info_pos.get('Nombre'), 'Vacante / Sin asignar')
                direccion_pos = clean_text(info_pos.get('Dirección'), 'No asignada')
                sucesor_actual_info = clean_text(info_pos.get('Sucesor actual', info_pos.get('Sucesor actual ')), 'No definido')
                
                if direccion_permitida != "TODAS":
                    st.info(f"📌 **Posición Crítica:** {pos_seleccionada} | 👤 **Ocupante Actual:** {ocupante_actual} | 🎯 **Sucesor Actual:** {sucesor_actual_info}")
                else:
                    st.info(f"📌 **Posición Crítica:** {pos_seleccionada} | 👤 **Ocupante Actual:** {ocupante_actual} | 🏢 **Dirección:** {direccion_pos} | 🎯 **Sucesor Actual:** {sucesor_actual_info}")

                with st.expander("🤖 Mostrar Sugerencias de Sucesión (IA)"):
                    sugerencias = generar_sugerencias_ia(pos_seleccionada, info_pos)
                    if sugerencias:
                        items_html = ""
                        for s in sugerencias:
                            if direccion_permitida != "TODAS" and not (direccion_permitida.upper() in s['direccion'].upper()):
                                info_vis = "🔒 <i>Detalles confidenciales (Otra Dirección)</i>"
                            else:
                                info_vis = f"📌 Puesto Actual: <b>{s['puesto']}</b> | 📊 9-Box: <b>{s['box']}</b>"
                                
                            items_html += f"<li>👤 <b>{s['nombre']}</b> — {info_vis}<br><span style='color:#0369a1;'>💡 {s['razon']}</span></li>"
                            
                        st.markdown(f"""
                        <div style="background:#e0f2fe; border-left:5px solid #0284c7; padding:12px; border-radius:8px; margin-bottom:5px; font-size:13px; color:#0f172a;">
                            <ul style="margin:8px 0 0 0; padding-left:20px; line-height:1.5;">
                                {items_html}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ **Dictamen IA:** No se detectaron candidatos en la plantilla actual que cumplan con los criterios estrictos de desempeño, nivel y afinidad técnica para esta posición crítica. **Se sugiere considerar reclutamiento externo o desarrollo a mediano plazo.**")
                
                nombres_empleados = sorted([clean_text(n) for n in df_completo['Nombre'].dropna().unique() if clean_text(n)])
                opciones_sucesores = ["Pendiente"] + nombres_empleados
                opciones_tiempo = ["Pendiente", "Inmediato", "1 a 3 años", "Más de 3 años"]
                
                c_suc1 = clean_text(info_pos.get('Sucesor P.1', 'Pendiente')) or "Pendiente"
                c_read1 = clean_text(info_pos.get('Tiempo de Readiness 1', 'Pendiente')) or "Pendiente"
                c_pos1 = clean_text(info_pos.get('Positivo', info_pos.get('Positivo 1', '')))
                c_opo1 = clean_text(info_pos.get('Oportunidad', info_pos.get('Oportunidad 1', '')))
                
                c_suc2 = clean_text(info_pos.get('Sucesor P.2', 'Pendiente')) or "Pendiente"
                c_read2 = clean_text(info_pos.get('Tiempo de Readiness 2', 'Pendiente')) or "Pendiente"
                c_pos2 = clean_text(info_pos.get('Positivo.1', info_pos.get('Positivo 2', '')))
                c_opo2 = clean_text(info_pos.get('Oportunidad.1', info_pos.get('Oportunidad 2', '')))
                
                c_suc3 = clean_text(info_pos.get('Sucesor P.3', 'Pendiente')) or "Pendiente"
                c_read3 = clean_text(info_pos.get('Tiempo de Readiness 3', 'Pendiente')) or "Pendiente"
                c_pos3 = clean_text(info_pos.get('Positivo.2', info_pos.get('Positivo 3', '')))
                c_opo3 = clean_text(info_pos.get('Oportunidad.2', info_pos.get('Oportunidad 3', '')))
                
                if c_suc1 not in opciones_sucesores: opciones_sucesores.append(c_suc1)
                if c_suc2 not in opciones_sucesores: opciones_sucesores.append(c_suc2)
                if c_suc3 not in opciones_sucesores: opciones_sucesores.append(c_suc3)
                if c_read1 not in opciones_tiempo: opciones_tiempo.append(c_read1)
                if c_read2 not in opciones_tiempo: opciones_tiempo.append(c_read2)
                if c_read3 not in opciones_tiempo: opciones_tiempo.append(c_read3)
                
                st.write("") 
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### 🥇 Sucesor 1")
                    n_suc1 = st.selectbox("Candidato 1", opciones_sucesores, index=opciones_sucesores.index(c_suc1), key="select_suc1")
                    
                    ficha1 = obtener_ficha_candidato(n_suc1)
                    if ficha1 == "RESTRINGIDO":
                        st.error("🔒 Datos confidenciales (Colaborador de otra Dirección)")
                    elif ficha1:
                        st.success(f"📊 **9-Box:** {ficha1['box']} | 🔥 **Enganche:** {ficha1['enganche']} | 📈 **EDR:** {ficha1['edr']}")
                        pdi_diag1 = diagnosticar_pdi_ia(n_suc1, pos_seleccionada, ficha1)
                        if pdi_diag1 and pdi_diag1.get("estatus") == "SIN_PDI":
                            st.warning(pdi_diag1['recomendacion'])
                        elif pdi_diag1 and "color_borde" in pdi_diag1:
                            st.markdown(f"<div style='background:{pdi_diag1['bg_color']}; border-left:4px solid {pdi_diag1['color_borde']}; padding:10px; border-radius:6px; font-size:12px; color:#1e293b;'><b>🤖 Dictamen IA: {pdi_diag1['icono']} {pdi_diag1['titulo_estatus']}</b><br>🎯 <b>Objetivo PDI:</b> {pdi_diag1['objetivo']} (Avance: <b>{pdi_diag1['avance']}</b>)<br>📌 <b>RECOMENDACIÓN:</b><br>{pdi_diag1['recomendacion']}</div>", unsafe_allow_html=True)
                            
                    n_read1 = st.selectbox("Readiness 1", opciones_tiempo, index=opciones_tiempo.index(c_read1), key="select_read1")
                    n_pos1 = st.text_area("👍 Comentarios Positivos 1", value=c_pos1, height=68, key="t_pos1")
                    n_opo1 = st.text_area("📈 Áreas de Oportunidad 1", value=c_opo1, height=68, key="t_opo1")
                    
                with col2:
                    st.markdown("#### 🥈 Sucesor 2")
                    n_suc2 = st.selectbox("Candidato 2", opciones_sucesores, index=opciones_sucesores.index(c_suc2), key="select_suc2")
                    
                    ficha2 = obtener_ficha_candidato(n_suc2)
                    if ficha2 == "RESTRINGIDO":
                        st.error("🔒 Datos confidenciales (Colaborador de otra Dirección)")
                    elif ficha2:
                        st.success(f"📊 **9-Box:** {ficha2['box']} | 🔥 **Enganche:** {ficha2['enganche']} | 📈 **EDR:** {ficha2['edr']}")
                        pdi_diag2 = diagnosticar_pdi_ia(n_suc2, pos_seleccionada, ficha2)
                        if pdi_diag2 and pdi_diag2.get("estatus") == "SIN_PDI":
                            st.warning(pdi_diag2['recomendacion'])
                        elif pdi_diag2 and "color_borde" in pdi_diag2:
                            st.markdown(f"<div style='background:{pdi_diag2['bg_color']}; border-left:4px solid {pdi_diag2['color_borde']}; padding:10px; border-radius:6px; font-size:12px; color:#1e293b;'><b>🤖 Dictamen IA: {pdi_diag2['icono']} {pdi_diag2['titulo_estatus']}</b><br>🎯 <b>Objetivo PDI:</b> {pdi_diag2['objetivo']} (Avance: <b>{pdi_diag2['avance']}</b>)<br>📌 <b>RECOMENDACIÓN:</b><br>{pdi_diag2['recomendacion']}</div>", unsafe_allow_html=True)
                            
                    n_read2 = st.selectbox("Readiness 2", opciones_tiempo, index=opciones_tiempo.index(c_read2), key="select_read2")
                    n_pos2 = st.text_area("👍 Comentarios Positivos 2", value=c_pos2, height=68, key="t_pos2")
                    n_opo2 = st.text_area("📈 Áreas de Oportunidad 2", value=c_opo2, height=68, key="t_opo2")
                    
                with col3:
                    st.markdown("#### 🥉 Sucesor 3")
                    n_suc3 = st.selectbox("Candidato 3", opciones_sucesores, index=opciones_sucesores.index(c_suc3), key="select_suc3")
                    
                    ficha3 = obtener_ficha_candidato(n_suc3)
                    if ficha3 == "RESTRINGIDO":
                        st.error("🔒 Datos confidenciales (Colaborador de otra Dirección)")
                    elif ficha3:
                        st.success(f"📊 **9-Box:** {ficha3['box']} | 🔥 **Enganche:** {ficha3['enganche']} | 📈 **EDR:** {ficha3['edr']}")
                        pdi_diag3 = diagnosticar_pdi_ia(n_suc3, pos_seleccionada, ficha3)
                        if pdi_diag3 and pdi_diag3.get("estatus") == "SIN_PDI":
                            st.warning(pdi_diag3['recomendacion'])
                        elif pdi_diag3 and "color_borde" in pdi_diag3:
                            st.markdown(f"<div style='background:{pdi_diag3['bg_color']}; border-left:4px solid {pdi_diag3['color_borde']}; padding:10px; border-radius:6px; font-size:12px; color:#1e293b;'><b>🤖 Dictamen IA: {pdi_diag3['icono']} {pdi_diag3['titulo_estatus']}</b><br>🎯 <b>Objetivo PDI:</b> {pdi_diag3['objetivo']} (Avance: <b>{pdi_diag3['avance']}</b>)<br>📌 <b>RECOMENDACIÓN:</b><br>{pdi_diag3['recomendacion']}</div>", unsafe_allow_html=True)
                            
                    n_read3 = st.selectbox("Readiness 3", opciones_tiempo, index=opciones_tiempo.index(c_read3), key="select_read3")
                    n_pos3 = text_area("👍 Comentarios Positivos 3", value=c_pos3, height=68, key="t_pos3")
                    n_opo3 = st.text_area("📈 Áreas de Oportunidad 3", value=c_opo3, height=68, key="t_opo3")
                
                st.write("")
                submitted = st.button("💾 Guardar Cambios en Base de Datos", type="primary", use_container_width=True)
                
                if submitted:
                    with st.spinner("🤖 El robot está escribiendo en tu Excel..."):
                        idx_excel = idx_pandas + 2 
                        match = re.search(r'/d/([a-zA-Z0-9-_]+)', link_archivo)
                        doc_id = match.group(1) if match else link_archivo
                        
                        try:
                            secretos = st.secrets["connections"]["gsheets"]
                            credenciales = Credentials.from_service_account_info(
                                secretos,
                                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                            )
                            cliente = gspread.authorize(credenciales)
                            archivo = cliente.open_by_key(doc_id)
                            pestana = archivo.worksheet("Base de datos")
                            
                            # Actualización del rango de I hasta T (12 columnas)
                            rango = f'I{idx_excel}:T{idx_excel}'
                            celdas = pestana.range(rango)
                            
                            celdas[0].value = "Pendiente" if n_suc1 == "Pendiente" else n_suc1
                            celdas[1].value = "Pendiente" if n_read1 == "Pendiente" else n_read1
                            celdas[2].value = n_pos1
                            celdas[3].value = n_opo1
                            
                            celdas[4].value = "Pendiente" if n_suc2 == "Pendiente" else n_suc2
                            celdas[5].value = "Pendiente" if n_read2 == "Pendiente" else n_read2
                            celdas[6].value = n_pos2
                            celdas[7].value = n_opo2
                            
                            celdas[8].value = "Pendiente" if n_suc3 == "Pendiente" else n_suc3
                            celdas[9].value = "Pendiente" if n_read3 == "Pendiente" else n_read3
                            celdas[10].value = n_pos3
                            celdas[11].value = n_opo3
                            
                            pestana.update_cells(celdas)
                            
                            st.success("✅ ¡Guardado exitosamente! El mapa se está actualizando...")
                            st.cache_data.clear()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error técnico al intentar escribir en el Excel: {e}")

            st.divider()
            
            # ==========================================
            # INTEGRACIÓN: TABLA AVANCE PDI
            # ==========================================
            st.markdown("### 📈 Avance de PDI (Integrado)")
            
            if not df_pdi.empty and 'Nombre' in df_pdi.columns:
                nombres_visibles_limpios = [str(d['Nombre']).strip().lower() for d in kpis['data_total']]
                df_pdi_filtrado = df_pdi.copy()
                df_pdi_filtrado['Nombre_Cruce'] = df_pdi_filtrado['Nombre'].astype(str).str.strip().str.lower()
                df_pdi_filtrado = df_pdi_filtrado[df_pdi_filtrado['Nombre_Cruce'].isin(nombres_visibles_limpios)]
                
                columnas_deseadas = {
                    "Nombre": "Nombre",
                    "Posicion": "Posicion", 
                    "Dirección actual": "Dirección", 
                    "Objetivo a Desar": "Objetivo", 
                    "PDI": "PDI", 
                    "Clasificacion de": "Clasificacion",
                    "Qué? / Acciones de Desarrollo": "Qué? / Acciones de Desarrollo", 
                    "% de Avance": "% de Avance", 
                    "Estatus": "Estatus"
                }
                
                cols_reales = []
                nombres_finales = []
                for col_orig, nombre_nuevo in columnas_deseadas.items():
                    col_match = next((c for c in df_pdi_filtrado.columns if col_orig.lower() in str(c).lower()), None)
                    if col_match:
                        cols_reales.append(col_match)
                        nombres_finales.append(nombre_nuevo)
                
                if cols_reales:
                    df_pdi_mostrar = df_pdi_filtrado[cols_reales].copy()
                    df_pdi_mostrar.columns = nombres_finales
                    
                    if direccion_permitida != "TODAS" and "Dirección" in df_pdi_mostrar.columns:
                        df_pdi_mostrar = df_pdi_mostrar.drop(columns=["Dirección"])
                    
                    col_p1, col_p2, col_p3 = st.columns(3)
                    
                    if "Nombre" in df_pdi_mostrar.columns:
                        lista_nombres_pdi = sorted(df_pdi_mostrar['Nombre'].dropna().astype(str).unique().tolist())
                        filtro_nombre = col_p1.multiselect("👤 Filtrar por Nombre:", options=lista_nombres_pdi)
                        if filtro_nombre:
                            df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Nombre'].isin(filtro_nombre)]
                            
                    if "Clasificacion" in df_pdi_mostrar.columns:
                        lista_clasif_pdi = sorted(df_pdi_mostrar['Clasificacion'].dropna().astype(str).unique().tolist())
                        filtro_clasif = col_p2.multiselect("🏷️ Filtrar por Clasificación:", options=lista_clasif_pdi)
                        if filtro_clasif:
                            df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Clasificacion'].isin(filtro_clasif)]
                            
                    if "Estatus" in df_pdi_mostrar.columns:
                        lista_estatus_pdi = sorted(df_pdi_mostrar['Estatus'].dropna().astype(str).unique().tolist())
                        filtro_estatus = col_p3.multiselect("🚦 Filtrar por Estatus:", options=lista_estatus_pdi)
                        if filtro_estatus:
                            df_pdi_mostrar = df_pdi_mostrar[df_pdi_mostrar['Estatus'].isin(filtro_estatus)]
                    
                    st.dataframe(df_pdi_mostrar, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ No se encontraron las columnas especificadas en la hoja PDI. Revisa los nombres en tu Excel.")
            else:
                st.warning("⚠️ No se pudo cargar la información de la pestaña PDI (O está vacía).")

        else:
            components.html(html_mapa, height=400)

if __name__ == "__main__":
    main()
