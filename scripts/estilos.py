# ============================================
# ESTILOS Y CONFIGURACION VISUAL - STREAMLIT
# Archivo centralizado de estilos CSS y clases
# ============================================

# ============================================
# PALETA DE COLORES
# ============================================
class Colores:
    """Paleta de colores del sistema"""
    
    # Colores principales
    PRIMARIO = "#1e3a5f"          # Azul oscuro
    SECUNDARIO = "#2ecc71"        # Verde
    TERCIARIO = "#3498db"         # Azul claro
    
    # Colores de estado/riesgo
    RIESGO_ALTO = "#e74c3c"       # Rojo
    RIESGO_MEDIO = "#f39c12"      # Naranja/Amarillo
    RIESGO_BAJO = "#2ecc71"       # Verde
    
    # Colores de fondo
    FONDO_PRINCIPAL = "#0e1117"   # Gris muy claro
    FONDO_TARJETA = "#ffffff"     # Blanco
    FONDO_HEADER = "#1e3a5f"      # Azul oscuro
    
    # Colores de texto
    TEXTO_PRINCIPAL = "#ffffff"   # Gris oscuro
    TEXTO_SECUNDARIO = "#ffffff"  # Gris medio
    TEXTO_CLARO = "#ffffff"       # Blanco
    
    # Colores de modelos
    GRADIENT_BOOSTING = "#e67e22" # Naranja
    RANDOM_FOREST = "#2ecc71"     # Verde
    REG_LOGISTICA = "#3498db"     # Azul
    
    # Bordes y sombras
    BORDE = "#e0e0e0"
    SOMBRA = "rgba(0, 0, 0, 0.1)"


# ============================================
# TIPOGRAFIA
# ============================================
class Tipografia:
    """Configuracion de tipografia"""
    
    FUENTE_PRINCIPAL = "'Segoe UI', 'Roboto', sans-serif"
    FUENTE_TITULOS = "'Segoe UI Semibold', 'Roboto', sans-serif"
    FUENTE_MONOSPACE = "'Consolas', 'Monaco', monospace"
    
    # Tamanos
    TAMANO_H1 = "2rem"
    TAMANO_H2 = "1.5rem"
    TAMANO_H3 = "1.25rem"
    TAMANO_BODY = "1rem"
    TAMANO_SMALL = "0.875rem"
    TAMANO_TINY = "0.75rem"


# ============================================
# ESTILOS CSS PRINCIPALES
# ============================================
def obtener_estilos_css():
    """Retorna el CSS principal de la aplicacion"""
    return f"""
    <style>
        /* ============================================
           ESTILOS GLOBALES
           ============================================ */
        
        .stApp {{
            background-color: {Colores.FONDO_PRINCIPAL};
        }}
        [data-testid="dtSidedar"]{{
            display: none;
        }}
        
        /* ============================================
           HEADER PERSONALIZADO
           ============================================ */
        
        .header-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: linear-gradient(135deg, {Colores.FONDO_HEADER} 0%, #2c5282 100%);
            border-radius: 10px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px {Colores.SOMBRA};
        }}
        
        .header-logo {{
            height: 70px;
            object-fit: contain;
        }}
        
        .header-titulo {{
            color: {Colores.TEXTO_CLARO};
            font-family: {Tipografia.FUENTE_TITULOS};
            font-size: {Tipografia.TAMANO_H1};
            text-align: center;
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        
        .header-subtitulo {{
            color: rgba(255,255,255,0.8);
            font-size: {Tipografia.TAMANO_SMALL};
            text-align: center;
            margin-top: 0.25rem;
        }}
        
        /* ============================================
           TARJETAS Y CONTENEDORES
           ============================================ */
        
        .tarjeta {{
            background-color: {Colores.FONDO_TARJETA};
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px {Colores.SOMBRA};
            margin-bottom: 1rem;
            border: 1px solid {Colores.BORDE};
        }}
        
        .tarjeta-titulo {{
            font-family: {Tipografia.FUENTE_TITULOS};
            font-size: {Tipografia.TAMANO_H3};
            color: {Colores.TEXTO_PRINCIPAL};
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid {Colores.PRIMARIO};
        }}
        
        /* ============================================
           INDICADORES DE RIESGO
           ============================================ */
        
        .indicador-riesgo {{
            display: inline-block;
            padding: 0.5rem 1.5rem;
            border-radius: 25px;
            font-weight: bold;
            font-size: {Tipografia.TAMANO_BODY};
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .riesgo-alto {{
            background-color: {Colores.RIESGO_ALTO};
            color: {Colores.TEXTO_CLARO};
            animation: pulse-alto 2s infinite;
        }}
        
        .riesgo-medio {{
            background-color: {Colores.RIESGO_MEDIO};
            color: {Colores.TEXTO_PRINCIPAL};
        }}
        
        .riesgo-bajo {{
            background-color: {Colores.RIESGO_BAJO};
            color: {Colores.TEXTO_CLARO};
        }}
        
        @keyframes pulse-alto {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.8; }}
        }}
        
        /* ============================================
           METRICAS Y KPIs
           ============================================ */
        
        .metrica-container {{
            text-align: center;
            padding: 1rem;
        }}
        
        .metrica-valor {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {Colores.PRIMARIO};
            font-family: {Tipografia.FUENTE_TITULOS};
        }}
        
        .metrica-label {{
            font-size: {Tipografia.TAMANO_SMALL};
            color: {Colores.TEXTO_SECUNDARIO};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* ============================================
           TABLAS
           ============================================ */
        
        .tabla-variables {{
            width: 100%;
            border-collapse: collapse;
            font-size: {Tipografia.TAMANO_SMALL};
        }}
        
        .tabla-variables th {{
            background-color: {Colores.PRIMARIO};
            color: {Colores.TEXTO_CLARO};
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }}
        
        .tabla-variables td {{
            padding: 0.75rem;
            border-bottom: 1px solid {Colores.BORDE};
        }}
        
        .tabla-variables tr:hover {{
            background-color: rgba(30, 58, 95, 0.05);
        }}
        
        /* ============================================
           BOTONES PERSONALIZADOS
           ============================================ */
        
        .btn-primario {{
            background-color: {Colores.PRIMARIO};
            color: {Colores.TEXTO_CLARO};
            padding: 0.75rem 2rem;
            border: none;
            border-radius: 5px;
            font-size: {Tipografia.TAMANO_BODY};
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .btn-primario:hover {{
            background-color: #2c5282;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px {Colores.SOMBRA};
        }}
        
        /* ============================================
           INPUTS Y FORMULARIOS
           ============================================ */
        
        .input-busqueda {{
            border: 2px solid {Colores.BORDE};
            border-radius: 8px;
            padding: 0.75rem 1rem;
            font-size: {Tipografia.TAMANO_BODY};
            transition: border-color 0.3s ease;
        }}
        
        .input-busqueda:focus {{
            border-color: {Colores.PRIMARIO};
            outline: none;
            box-shadow: 0 0 0 3px rgba(30, 58, 95, 0.1);
        }}
        
        /* ============================================
           GAUGES Y GRAFICOS
           ============================================ */
        
        .gauge-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem;
        }}
        
        .gauge-titulo {{
            font-size: {Tipografia.TAMANO_SMALL};
            color: {Colores.TEXTO_SECUNDARIO};
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}
        
        .gauge-valor {{
            font-size: 1.5rem;
            font-weight: bold;
            margin-top: 0.5rem;
        }}
        
        /* ============================================
           MENSAJES Y ALERTAS
           ============================================ */
        
        .alerta {{
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .alerta-exito {{
            background-color: rgba(46, 204, 113, 0.1);
            border-left: 4px solid {Colores.RIESGO_BAJO};
            color: #27ae60;
        }}
        
        .alerta-advertencia {{
            background-color: rgba(243, 156, 18, 0.1);
            border-left: 4px solid {Colores.RIESGO_MEDIO};
            color: #d68910;
        }}
        
        .alerta-error {{
            background-color: rgba(231, 76, 60, 0.1);
            border-left: 4px solid {Colores.RIESGO_ALTO};
            color: #c0392b;
        }}
        
        .alerta-info {{
            background-color: rgba(52, 152, 219, 0.1);
            border-left: 4px solid {Colores.TERCIARIO};
            color: #2980b9;
        }}
        
        /* ============================================
           FOOTER
           ============================================ */
        
        .footer {{
            text-align: center;
            padding: 1.5rem;
            color: {Colores.TEXTO_SECUNDARIO};
            font-size: {Tipografia.TAMANO_TINY};
            border-top: 1px solid {Colores.BORDE};
            margin-top: 2rem;
        }}
        
        /* ============================================
           SEPARADORES
           ============================================ */
        
        .separador {{
            height: 2px;
            background: linear-gradient(90deg, transparent, {Colores.PRIMARIO}, transparent);
            margin: 1.5rem 0;
        }}
        
        /* ============================================
           ANIMACIONES
           ============================================ */
        
        .fade-in {{
            animation: fadeIn 0.5s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* ============================================
           RESPONSIVE
           ============================================ */
        
        @media (max-width: 768px) {{
            .header-container {{
                flex-direction: column;
                text-align: center;
                gap: 1rem;
            }}
            
            .header-logo {{
                height: 50px;
            }}
            
            .header-titulo {{
                font-size: 1.5rem;
            }}
        }}
    </style>
    """


# ============================================
# COMPONENTES HTML REUTILIZABLES
# ============================================
class Componentes:
    """Componentes HTML reutilizables"""
    
    @staticmethod
    def header(img1_base64, img2_base64, titulo="Prediccion de Reingreso Hospitalario", subtitulo=None):
        """Genera el header con logos"""
        subtitulo_html = f'<p class="header-subtitulo">{subtitulo}</p>' if subtitulo else ''
        return f"""
        <div class="header-container">
            <div><img src="data:image/png;base64,{img1_base64}" class="header-logo" /></div>
            <div>
                <h2 class="header-titulo">{titulo}</h2>
                {subtitulo_html}
            </div>
            <div><img src="data:image/png;base64,{img2_base64}" class="header-logo" /></div>
        </div>
        """
    
    @staticmethod
    def tarjeta(titulo, contenido):
        """Genera una tarjeta con titulo y contenido"""
        return f"""
        <div class="tarjeta">
            <h3 class="tarjeta-titulo">{titulo}</h3>
            {contenido}
        </div>
        """
    
    @staticmethod
    def indicador_riesgo(nivel, probabilidad):
        """Genera un indicador de riesgo"""
        clase = f"riesgo-{nivel.lower()}"
        icono = {"alto": "🚨", "medio": "⚠️", "bajo": "✅"}.get(nivel.lower(), "")
        return f"""
        <div class="indicador-riesgo {clase}">
            {icono} RIESGO {nivel.upper()} - {probabilidad:.1f}%
        </div>
        """
    
    @staticmethod
    def metrica(valor, label):
        """Genera una metrica/KPI"""
        return f"""
        <div class="metrica-container">
            <div class="metrica-valor">{valor}</div>
            <div class="metrica-label">{label}</div>
        </div>
        """
    
    @staticmethod
    def alerta(mensaje, tipo="info"):
        """Genera una alerta (tipos: exito, advertencia, error, info)"""
        iconos = {"exito": "✅", "advertencia": "⚠️", "error": "❌", "info": "ℹ️"}
        icono = iconos.get(tipo, "ℹ️")
        return f"""
        <div class="alerta alerta-{tipo}">
            <span>{icono}</span>
            <span>{mensaje}</span>
        </div>
        """
    
    @staticmethod
    def separador():
        """Genera un separador visual"""
        return '<div class="separador"></div>'
    
    @staticmethod
    def footer(texto="Sistema de Prediccion de Reingreso Hospitalario | Desarrollado por Sumimedical"):
        """Genera el footer"""
        return f"""
        <div class="footer">
            {texto} &copy; {__import__('datetime').datetime.now().year}
        </div>
        """
    
    @staticmethod
    def texto_destacado(texto, tamano="1.25rem", peso="600"):
        """Genera texto destacado"""
        return f"""
        <div style="font-size:{tamano}; font-weight:{peso}; color:{Colores.TEXTO_PRINCIPAL};">
            {texto}
        </div>
        """


# ============================================
# CONFIGURACION DE MATPLOTLIB
# ============================================
def configurar_matplotlib():
    """Configura matplotlib con los estilos del sistema"""
    import matplotlib.pyplot as plt
    
    plt.rcParams['figure.facecolor'] = Colores.FONDO_TARJETA
    plt.rcParams['axes.facecolor'] = Colores.FONDO_TARJETA
    plt.rcParams['axes.labelcolor'] = '#333333'  # Color oscuro para labels
    plt.rcParams['text.color'] = '#333333'       # Color oscuro para texto
    plt.rcParams['xtick.color'] = '#333333'      # Color oscuro para ticks X
    plt.rcParams['ytick.color'] = '#333333'
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.size'] = 10

 
# ============================================
# NOMBRES DESCRIPTIVOS DE VARIABLES
# ============================================
NOMBRES_VARIABLES = {
    'DURACION_ESTANCIA_ACTUAL': 'Variable asociada estancia actual',
    'HOSPITALIZACIONES_ULTIMO_AÑO': 'Historico hospitalizacion',
    'NUMERO_MEDICAMENTOS': 'Suministro de medicamentos',
    'EDAD': 'Variables segun clasificacion etaria',
    'SEXO': 'Clasificacion del grupo biologico',
    'PRESION_ARTERIAL': 'Perfil hemodinámico arterial',
   # 'IMC': 'Variables derivadas de la masa corporal',
    'ESTADO_EGRESO': 'Estado de egreso actual del usuario',
    'ADHERENCIA_PREVIA': 'Formulacion de medicamentos al momento del egreso',
    'ADHERENCIA_TRATAMIENTO': 'Formulacion de medicamentos al momento del egreso',
}

def obtener_nombre_variable(variable):
    """Obtiene el nombre descriptivo de una variable"""
    return NOMBRES_VARIABLES.get(variable, variable)
