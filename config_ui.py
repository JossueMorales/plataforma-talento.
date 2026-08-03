import pandas as pd
import re

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
window.ringSpacing = 348; 
network.on("beforeDrawing", function(ctx) {
    if (!window.onionMode) return; 
    ctx.save(); 
    var nodos_visibles = network.body.data.nodes.get().filter(n => n.hidden !== true);
    var max_nivel_visible = 0;
    var paso = window.ringSpacing; 
    nodos_visibles.forEach(function(n) {
        var anillo = n.NivelCalculado !== undefined ? n.NivelCalculado : (n.AnilloReal !== undefined ? n.AnilloReal : 5);
        if(anillo > max_nivel_visible) { max_nivel_visible = anillo; }
    });
    var limite_anillos = Math.max(Math.ceil(max_nivel_visible), 1);
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

INYECCION_HTML_JS = """
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
                <input type="range" id="sliderSeparacion" min="100" max="800" value="348" oninput="updateSpacing()" style="width: 100%; cursor: pointer;">
                <span id="valorSeparacion" style="font-size: 12px; font-weight:bold; color:#1976d2; min-width: 45px;">348px</span>
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
function getDispersionOffset(nodeId, spacing) {
    var str = String(nodeId);
    var h = 0;
    for (var k = 0; k < str.length; k++) { h += str.charCodeAt(k); }
    return spacing * (((h % 9) / 8.0) * 0.5 - 0.25); 
}
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
        var angle = n.Angle !== undefined ? n.Angle : 0;
        var dispersion = n.Dispersion !== undefined ? n.Dispersion : 0;
        var nivelBase = n.NivelCalculado !== undefined ? n.NivelCalculado : (n.AnilloReal !== undefined ? n.AnilloReal : 5);
        var nuevoRadio = 0;
        if (nivelBase !== 0) { nuevoRadio = (nivelBase * window.ringSpacing) + (dispersion * window.ringSpacing); }
        nodesToUpdate.push({ id: n.id, x: nuevoRadio * Math.cos(angle), y: nuevoRadio * Math.sin(angle) });
    }
    network.body.data.nodes.update(nodesToUpdate);
}
network.on("zoom", function() {
    var currentScale = network.getScale();
    var minScale = 0.1; var maxScale = 2.5; 
    if (currentScale < minScale) { network.moveTo({ scale: minScale }); } else if (currentScale > maxScale) { network.moveTo({ scale: maxScale }); }
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
            fEngInd.innerText = engInd.toFixed(1); var colorInd = getColorEnganche(engInd);
            fEngInd.style.backgroundColor = colorInd.bg; fEngInd.style.color = colorInd.text;
        } else { fEngInd.innerText = "N/A"; fEngInd.style.backgroundColor = "#eee"; fEngInd.style.color = "#333"; }
        var isLeader = node.Es_Lider === true || node.Es_Lider === "True";
        var engArea = node.Eng_Area !== undefined ? parseFloat(node.Eng_Area) : 0;
        var fEngArea = document.getElementById('fEngArea');
        if (isLeader && engArea > 0) {
            fEngArea.innerText = engArea.toFixed(1); var colorArea = getColorEnganche(engArea);
            fEngArea.style.backgroundColor = colorArea.bg; fEngArea.style.color = colorArea.text;
        } else { fEngArea.innerText = "N/A"; fEngArea.style.backgroundColor = "#eee"; fEngArea.style.color = "#333"; }
        document.getElementById('fSuc1').innerText = node.NomSuc1 || "Pendiente";
        document.getElementById('fRead1').innerText = node.Read1 && node.Read1 !== 'Pendiente' ? node.Read1 : "Sin tiempo definido";
        if(node.NomSuc2 && node.NomSuc2 !== "") {
            document.getElementById('divSucesor2').style.display = "block"; document.getElementById('fSuc2').innerText = node.NomSuc2; document.getElementById('fRead2').innerText = node.Read2 || "Sin tiempo definido";
        } else { document.getElementById('divSucesor2').style.display = "none"; }
        if(node.NomSuc3 && node.NomSuc3 !== "") {
            document.getElementById('divSucesor3').style.display = "block"; document.getElementById('fSuc3').innerText = node.NomSuc3; document.getElementById('fRead3').innerText = node.Read3 || "Sin tiempo definido";
        } else { document.getElementById('divSucesor3').style.display = "none"; }
        var colorBg = typeof node.color === 'object' ? node.color.background : node.color;
        var boxResult = node.Resultado_9Box || "N/A";
        var f9Box = document.getElementById('f9Box'); f9Box.innerText = boxResult; f9Box.style.backgroundColor = colorBg || "#eee";
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
        var fromNode = network.body.data.nodes.get(edge.from); var toNode = network.body.data.nodes.get(edge.to);
        if (!fromNode || !toNode || fromNode.hidden === true || toNode.hidden === true) { edgesToUpdate.push({id: edge.id, hidden: true}); continue; }
        var colorValue = edge.color;
        if (typeof colorValue === 'object' && colorValue !== null) { colorValue = colorValue.color || colorValue.inherit; }
        var isSucc = (edge.is_succ === true || edge.is_succ === "True" || edge.is_succ === "true" || colorValue === '#9c27b0');
        var is9Box = (edge.is_9box === true || edge.is_9box === "True" || edge.is_9box === "true" || colorValue === '#22c55e' || colorValue === '#166534');
        if (isSucc) { edgesToUpdate.push({id: edge.id, hidden: !showSucc});
        } else if (is9Box) { edgesToUpdate.push({id: edge.id, hidden: !showJumps});
        } else { edgesToUpdate.push({id: edge.id, hidden: !showNormal}); }
    }
    network.body.data.edges.update(edgesToUpdate);
}
function enfocarPantalla() { 
    if (window.targetNodeId && network.body.data.nodes.get(window.targetNodeId) && window.targetNodeId !== "None") {
        network.focus(window.targetNodeId, { scale: 0.85, animation: { duration: 800, easingFunction: 'easeInOutQuad' } });
    } else {
        network.fit();
        setTimeout(function() { var currentScale = network.getScale(); network.moveTo({ position: {x: 0, y: -80}, scale: currentScale * 0.85, animation: { duration: 800, easingFunction: 'easeInOutQuad' } }); }, 800);
    }
}
setTimeout(function() { updateSpacing(); applyVisualFilters(); enfocarPantalla(); }, 1000); 
</script>
"""

# ==========================================
# FUNCIONES AUXILIARES Y DICCIONARIO
# ==========================================
def crear_tarjeta_kpi(titulo, valor, color_borde, color_texto, color_fondo):
    color_valor = color_texto if color_texto != "#64748b" else "#0f172a"
    return f"""
    <div style="background-color: {color_fondo}; border: 1px solid #e2e8f0; border-top: 3px solid {color_borde}; padding: 10px 5px 5px 5px; border-radius: 6px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 2px;">
        <div style="font-size: 10px; color: {color_texto}; font-weight: 600; line-height: 1.1; margin-bottom: 4px;">{titulo}</div>
        <div style="font-size: 16px; color: {color_valor}; font-weight: bold;">{valor}</div>
    </div>
    """

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
            if key in palabra or palabra in key: contexto_ampliado.update(valores)
            if palabra in valores: contexto_ampliado.update(valores)
    return contexto_ampliado

def clean_text(val, default=''):
    if isinstance(val, pd.Series): val = val.iloc[0] if not val.empty else default
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'pendiente', '']: return default
    return str(val).strip()

def clean_id(val):
    if isinstance(val, pd.Series): val = val.iloc[0] if not val.empty else ''
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'pendiente', '']: return ''
    v = str(val).strip()
    if v.endswith('.0'): return v[:-2]
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
    if len(partes) <= 2: return nombre_completo
    elif len(partes) == 3: return f"{partes[0]} {partes[1]}"
    else: return f"{partes[0]} {partes[-2]}"

def acortar_puesto(puesto):
    if not puesto: return ""
    p = str(puesto).strip().upper()
    reemplazos = {
        "RECURSOS HUMANOS": "RH", "TALENTO Y CULTURA": "TYC", "DESARROLLO ORGANIZACIONAL": "D.O.",
        "ADMINISTRATIVO": "ADM.", "ADMINISTRADORA": "ADM.", "ADMINISTRADOR DE ": "ADMIN. ", "COORDINADOR DE ": "COORD. ",
        "COORDINADORA DE ": "COORD. ", "COORDINADOR ": "COORD. ", "ESPECIALISTA EN ": "ESP. ", "SUPERVISOR DE ": "SUP. ",
        "GERENTE DE ": "GTE. ", "DIRECTOR DE ": "DIR. ", "JEFE DE ": "JEFE ", "ADQUISICIÓN": "ADQ.",
        "TRANSFORMACIÓN": "TRANSF.", "SUCURSAL": "SUC.", "OPERACIONES": "OP.", "MANTENIMIENTO": "MANTTO.",
        "PRODUCCIÓN": "PROD.", "TECNOLOGÍA": "TECH", "INFORMACIÓN": "INFO.", "COMERCIAL": "COM.",
        "DISTRIBUCIÓN": "DIST.", "LOGÍSTICA": "LOG.", "SISTEMAS": "SIST.", "PROYECTOS": "PROY.", "NACIONAL": "NAL.",
        "REGIONAL": "REG.", "EJECUTIVO": "EJEC.", "REPRESENTANTE": "REP.", "ASISTENTE": "ASIST.", "AUXILIAR": "AUX."
    }
    for original, abrev in reemplazos.items(): p = p.replace(original, abrev)
    return p[:32] + "..." if len(p) > 35 else p

def get_readiness_val(rt_str):
    rt = str(rt_str).strip().lower()
    if not rt or rt in ['pendiente', 'nan', 'none']: return 4
    if 'inmediato' in rt or 'listo' in rt or '0' in rt: return 1
    if '1' in rt or '2' in rt or 'medio' in rt: return 2
    if '3' in rt or '4' in rt or '5' in rt or 'más' in rt or 'mas' in rt: return 3
    return 4

def get_dispersion_offset(node_id):
    return (((sum(ord(c) for c in str(node_id)) % 9) / 8.0) * 0.5) - 0.25
