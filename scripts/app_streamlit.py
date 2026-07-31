# ============================================
# APP STREAMLIT - PREDICCION DE REINGRESO HOSPITALARIO
# Consume datos desde modelo_datos.py (sin archivos CSV)
# Estilos centralizados en estilos.py
# ============================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import os
import re #Me permite validar en los campos los caracteres especiales

# Obtener directorio del script actual
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Importar modulos locales
from modelo_datos import cargar_datos, cargar_pesos_modelo, obtener_modelo
from estilos import (
    obtener_estilos_css, 
    Colores, 
    Componentes, 
    NOMBRES_VARIABLES,
    obtener_nombre_variable,
    configurar_matplotlib
)

# ============================================
# CONFIGURACION DE PAGINA
# ============================================
st.set_page_config(
    page_title="Prediccion de Reingreso Hospitalario",
    page_icon=os.path.join(SCRIPT_DIR, "public/logo-sumimedical.png"),
    layout="wide",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": None
    }
)

# Aplicar estilos CSS
st.markdown(obtener_estilos_css(), unsafe_allow_html=True)
# Se ocultan los obejtos visuales como, el menu de carga de datos, la configuración del estilo de la pantalla y el deploy para publicar el
# el proyecto 22-04-2026 GSCA
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
            
    [data-testid="stIconMaterial"] {
        display: none;
    }
            
    [data-testid="stToolbar"] {
        display: none;
    }
    [data-testid="stForm"]{
        border: none;
    }
            
    [data-testid = "stBaseButton-primaryFormSubmit"]{
        padding: 0.5rem 0.75rem;
    }
    
    #prediccion-de-reingreso-hospitalario{
        text-align: center;
        padding: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# Configurar matplotlib
configurar_matplotlib()

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def cargar_imagen_base64(ruta):
    """Carga una imagen y la convierte a base64"""
    try:
        # Construir ruta absoluta desde el directorio del script
        ruta_absoluta = os.path.join(SCRIPT_DIR, ruta)
        
        # Si no existe, intentar ruta relativa directa
        if not os.path.exists(ruta_absoluta):
            ruta_absoluta = ruta
        
        with open(ruta_absoluta, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def crear_gauge(prob, titulo, color):
    """Crea un grafico de barra horizontal para mostrar probabilidad"""
    fig, ax = plt.subplots(figsize=(4, 2))

    valor = prob * 100

    ax.barh([""], [valor], color=color, edgecolor='black', linewidth=0.5)
    ax.set_xlim(0, 100)
    ax.set_title(titulo, fontsize=10, fontweight='bold')
    ax.set_xlabel("%")
    
    # Forzar los ticks del eje X para que se muestren
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.tick_params(axis='x', which='both', bottom=True, labelbottom=True, labelsize=8)

    for i in range(0, 101, 20):
        ax.axvline(i, linestyle="--", alpha=0.3, color='gray')

    # Ajuste para que el texto NO se salga
    if valor > 90:
        pos_texto = valor - 8
    else:
        pos_texto = valor + 2

    ax.text(pos_texto, 0, f'{valor:.1f}%', va='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    return fig

def detectar_columna(df, opciones):
    """Detecta cual de las opciones de columna existe en el DataFrame"""
    for c in opciones:
        if c in df.columns:
            return c
    return None

def mejor_modelo(gb, rf, lr):
    """Determina cual modelo tiene mejor probabilidad"""
    modelos = {
        "Gradient Boosting": gb,
        "Random Forest": rf,
        "Regresion Logistica": lr
    }
    nombre = max(modelos, key=modelos.get)
    valor = modelos[nombre]
    return nombre, valor

# ============================================
# HEADER CON LOGOS (estilo original)
# ============================================
img1_base64 = cargar_imagen_base64("public/logo-horus.jpg")
img2_base64 = cargar_imagen_base64("public/logo-sumimedical.png")

if img1_base64 and img2_base64:
    # Header con el estilo original
    header_html = f"""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div><img src="data:image/png;base64,{img1_base64}" style="height:80px;" /></div>
        <div style="text-align:center;">
            <h2>Predicción de Reingreso Hospitalario</h2>
        </div>
        <div><img src="data:image/png;base64,{img2_base64}" style="height:80px;" /></div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
else:
    st.title("Predicción de Reingreso Hospitalario")

# ============================================
# CARGAR DATOS DESDE MODELO (SIN CSV)
# ============================================
# Cache de StreamLit para  mantender la misma Data, se reduce de 3600 a menos GSCA 28-04-2026
@st.cache_data(ttl=360, show_spinner=False)
def _cargar_datos_interno():
    """Carga los datos desde el modelo (base de datos)"""
    try:
        df = cargar_datos()
        return df
    except Exception as e:
        return None

# Cache de StreamLit para  mantender la misma Data, se reduce de 3600 a menos GSCA 28-04-2026
@st.cache_data(ttl=360, show_spinner=False)
def _cargar_pesos_interno():
    """Carga los pesos del modelo"""
    try:
        df_pesos = cargar_pesos_modelo()
        return df_pesos
    except Exception as e:
        return None

# Cargar datos con mensaje personalizado
with st.spinner("Cargando los datos..."):
    df = _cargar_datos_interno()
    df_pesos = _cargar_pesos_interno()

if df is None:
    st.error("No se pudieron cargar los datos desde la base de datos")
    st.stop()

# Sidebar con info
st.sidebar.markdown("### Estado del Sistema")
if df is not None:
    st.sidebar.success(f"Datos cargados: {len(df)} registros")
if df_pesos is not None:
    st.sidebar.success(f"Pesos del modelo cargados")
else:
    st.sidebar.warning("Pesos no disponibles")

# ============================================
# DETECTAR COLUMNAS CLAVE
# ============================================
col_cedula = detectar_columna(df, ['CEDULA', 'DOCUMENTO', 'id'])
prob_gb_col = detectar_columna(df, ['PROB_GB', 'PROBABILIDAD_GRADIENT_BOOSTING', 'PROB_REINGRESO_GB'])
prob_rf_col = detectar_columna(df, ['PROB_RF', 'PROBABILIDAD_RANDOM_FOREST', 'PROB_REINGRESO_RF'])
prob_lr_col = detectar_columna(df, ['PROB_LR', 'PROBABILIDAD_REG_LOGISTICA', 'PROB_REINGRESO_LR'])
col_dias_egreso = detectar_columna(df, ['DIAS_DESDE_EGRESO_ANTERIOR', 'DIAS_EGRESO', 'DIAS_DESDE_EGRESO'])
col_fecha_ingreso = detectar_columna(df, ['FECHA_INGRESO_ACTUAL', 'FECHA_INGRESO', 'FEC_INGRESO'])
col_hospitalizaciones = detectar_columna(df, ['HOSPITALIZACIONES_ULTIMO_AÑO'])
col_adherencia = detectar_columna(df, ['ADHERENCIA_TRATAMIENTO', 'ADHERENCIA_TEXTO'])

# Validacion
if not all([col_cedula, prob_gb_col, prob_rf_col, prob_lr_col]):
    st.error("Faltan columnas criticas en los datos")
    st.write("Columnas detectadas:", {
        "Cedula": col_cedula,
        "GB": prob_gb_col,
        "RF": prob_rf_col,
        "LR": prob_lr_col
    })
    st.stop()

# ============================================
# BUSQUEDA DE PACIENTE
# ============================================
st.markdown(Componentes.separador(), unsafe_allow_html=True)

with st.form("form_busqueda"):
    col1, col2 = st.columns([4, 1])

    with col1:
        cedula = st.text_input(
            "Documento de identidad",
            autocomplete="off",
            placeholder="Ingrese el numero de documento"
        )

        #Limpiar cedula de caracteres especiales
cedula_limpia = ""
error_format = False

if cedula:
    # 🔹 SOLO letras y números (puedes cambiar a solo números si quieres)
    cedula_limpia = re.sub(r'[^a-zA-Z0-9]', '', cedula)

    # 🔹 Detectar si el usuario escribió caracteres inválidos
    if cedula != cedula_limpia:
        st.warning("Solo se permiten letras y números")
        error_format = True

# Reemplazamos por la versión limpia
cedula = cedula_limpia

# ============================================
# BOTON
# ============================================

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    buscar = st.form_submit_button("Buscar", type="primary")

# ============================================
# TABLA DE ESTADISTICAS DE CAUSA DE INGRESO (SIEMPRE VISIBLE)
# ============================================
col_causa_ingreso = detectar_columna(df, ['CAUSA_INGRESO', 'CAUSA', 'MOTIVO_INGRESO'])
col_dias_egreso_stats = detectar_columna(df, ['DIAS_DESDE_EGRESO_ANTERIOR', 'DIAS_EGRESO', 'DIAS_DESDE_EGRESO'])

# if col_causa_ingreso is not None:
#     st.markdown(Componentes.separador(), unsafe_allow_html=True)
#     st.markdown(
#         Componentes.texto_destacado("Analisis de criterios de reingreso"),
#         unsafe_allow_html=True
#     )
    
#     # Detectar columna de tiempo desde ultima hospitalizacion
#     col_tiempo = detectar_columna(df, ['TIEMPO_ULTIMA_HOSPITALIZACION', 'DIAS_DESDE_EGRESO_ANTERIOR', 'DIAS_EGRESO'])
    
#     # Calcular criterios de reingreso igual que modelo_reingresos.py
#     # ES_MISMA_CAUSA = (CAUSA_INGRESO == 2)
#     df['ES_MISMA_CAUSA'] = (df[col_causa_ingreso] == 2)
    
#     # DENTRO_15_DIAS = (TIEMPO_ULTIMA_HOSPITALIZACION <= 15)
#     if col_tiempo is not None:
#         df[col_tiempo] = pd.to_numeric(df[col_tiempo], errors='coerce')
#         df['DENTRO_15_DIAS'] = (df[col_tiempo] <= 15)
#     else:
#         df['DENTRO_15_DIAS'] = False
    
#     # REINGRESO = ES_MISMA_CAUSA AND DENTRO_15_DIAS
#     df['REINGRESO_CALC'] = ((df['ES_MISMA_CAUSA']) & (df['DENTRO_15_DIAS'])).astype(int)
    
#     # Detectar columna de fecha de egreso
#     col_fecha_egreso = detectar_columna(df, ['FECHA_EGRESO_DEL_INGRESO_ACTUAL', 'FECHA_EGRESO', 'EGRESO'])
    
#     # Calcular estadisticas exactamente como modelo_reingresos.py
#     cant_misma_causa = df['ES_MISMA_CAUSA'].sum()
#     cant_dentro_15_dias = df['DENTRO_15_DIAS'].sum()
#     cant_reingresos = df['REINGRESO_CALC'].sum()
#     total_registros = len(df)
#     tasa_reingreso = (cant_reingresos / total_registros * 100) if total_registros > 0 else 0
    
#     # Calcular egresos
#     if col_fecha_egreso is not None:
#         df[col_fecha_egreso] = pd.to_datetime(df[col_fecha_egreso], errors='coerce')
#         cant_con_egreso = df[col_fecha_egreso].notna().sum()
#         cant_sin_egreso = df[col_fecha_egreso].isna().sum()
#     else:
#         cant_con_egreso = 0
#         cant_sin_egreso = total_registros
    
#     # Crear tabla de estadisticas con el mismo formato que modelo_reingresos.py
#     tabla_stats = pd.DataFrame({
#         'Criterio': [
#             'Total de registros',
#             'Pacientes con egreso registrado',
#             'Pacientes sin egreso (aun hospitalizados)',
#             'Pacientes con misma causa',
#             'Ingresos dentro de 15 dias del egreso anterior',
#             'REINGRESOS (misma causa + <=15 dias)',
#             'Tasa de reingreso'
#         ],
#         'Valor': [
#             f"{total_registros:,}",
#             f"{cant_con_egreso:,}",
#             f"{cant_sin_egreso:,}",
#             f"{cant_misma_causa:,}",
#             f"{cant_dentro_15_dias:,}",
#             f"{cant_reingresos:,}",
#             f"{tasa_reingreso:.2f}%"
#         ]
#     })
    
#     # Mostrar tabla
#     st.dataframe(tabla_stats, use_container_width=True, hide_index=True)
# else:
#     st.warning("No se encontro la columna de causa de ingreso en los datos")

# ============================================
# Se valida que lo que se ingrese en el input de Documento de identidad no sena caracteres especiales y finalice la consulta si los ecuentran 23-04-2026 GSCA
# ============================================

if buscar:
    #  Detener si hay error de formato
    if error_format:
        st.stop()

    cedula_buscar = str(cedula).strip()

    # Normalizar columna
    df[col_cedula] = df[col_cedula].astype(str).str.strip()

    # Buscar registros
    registros = df[df[col_cedula] == cedula_buscar]
    

    #  Si no encuentra resultados se devuelve mensaje en relación  que no hay datos de reingreso o el usuario no existe 23-04-2026 GSCA
    if registros.empty:
        st.markdown(
            Componentes.alerta(
                "El usuario no contiene datos clinicos para la validacion de reingreso o no registra hospitalizacion",
                "error"
            ),
            unsafe_allow_html=True
        )
    else:
        # Obtener registro mas reciente
        if len(registros) > 1 and col_fecha_ingreso is not None:
            try:
                registros_ordenados = registros.copy()
                registros_ordenados['_fecha_temp'] = pd.to_datetime(
                    registros_ordenados[col_fecha_ingreso], errors='coerce'
                )
                registros_ordenados = registros_ordenados.sort_values('_fecha_temp', ascending=False)
                p = registros_ordenados.iloc[0]
                
                if col_hospitalizaciones:
                    hospitalizaciones = p[col_hospitalizaciones]
                    st.markdown(
                        Componentes.alerta(
                            f"El usuario tiene {int(hospitalizaciones)} registro(s) de hospitalizacion en el ultimo año.",
                            "info"
                        ),
                        unsafe_allow_html=True
                    )
            except:
                p = registros.iloc[0]
        else:
            p = registros.iloc[0]
        
        # Obtener probabilidades
        prob_gb = float(p[prob_gb_col])
        prob_rf = float(p[prob_rf_col])
        prob_lr = float(p[prob_lr_col])
        promedio = (prob_gb + prob_rf + prob_lr) / 3

        
        # ============================================
        # MOSTRAR RESULTADOS POR MODELO
        # ============================================
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"*Gradient Boosting:* {prob_gb*100:.2f}%")
            st.pyplot(crear_gauge(prob_gb, "Gradient Boosting", Colores.GRADIENT_BOOSTING))
        
        with col2:
            st.write(f"*Random Forest:* {prob_rf*100:.2f}%")
            st.pyplot(crear_gauge(prob_rf, "Random Forest", Colores.RANDOM_FOREST))
        
        with col3:
            st.write(f"*Regresion Logistica:* {prob_lr*100:.2f}%")
            st.pyplot(crear_gauge(prob_lr, "Regresion Logistica", Colores.REG_LOGISTICA))
        
        # Resultado principal
        nombre_modelo, valor_modelo = mejor_modelo(prob_gb, prob_rf, prob_lr)
        
        st.markdown(Componentes.separador(), unsafe_allow_html=True)
        
        st.markdown(
            Componentes.texto_destacado(
                f"El usuario presenta una probabilidad de reingreso hospitalario de: <strong>{promedio*100:.2f}%</strong> en relacion al modelo {nombre_modelo}",
                tamano="1.25rem"
            ), 
            unsafe_allow_html=True
        )
        
        # Indicador de riesgo
        if promedio >= 0.7:
            nivel_riesgo = "alto"
            st.error("🚨ALTO RIESGO")
        elif promedio >= 0.4:
            nivel_riesgo = "medio"
            st.warning("⚠️RIESGO MEDIO")
        else:
            nivel_riesgo = "bajo"
            st.success("✅RIESGO BAJO")
        
        # ============================================
        # DIAS DESDE EGRESO
        # ============================================
        
        st.markdown(Componentes.separador(), unsafe_allow_html=True)
        
        st.markdown(
            Componentes.texto_destacado(
                "Antecedentes de reingreso hospitalario por la misma causa en menos de 15 dias"
            ),
            unsafe_allow_html=True
        )
        
        if col_dias_egreso is not None:
            try:
                valor_dias = p[col_dias_egreso]
                if pd.notna(valor_dias) and str(valor_dias).strip() != '':
                    dias_desde_egreso = int(float(valor_dias))
                    
                    if dias_desde_egreso <= 15:
                        st.success(f"Dias transcurridos desde el egreso anterior: *{dias_desde_egreso} dias*")
                        st.success(
                            f"El usuario presenta antecedentes de reingreso hospitalario en menos de 15 dias. "
                            f"Han transcurrido *{dias_desde_egreso} dias* desde el ultimo egreso."
                        )
                    else:
                        st.warning(
                            f"El usuario no tiene antecedentes de reingreso hospitalario menor a 15 dias por la misma causa."
                        )
                        st.warning(f"Dias transcurridos desde la ultima hospitalizacion: *{dias_desde_egreso} dias*")
                else:
                    st.warning("*El usuario no tiene antecedentes de reingreso hospitalario menor a 15 dias*")
            except:
                st.warning("*El usuario no tiene antecedentes de reingreso hospitalario menor a 15 dias*")
        else:
            st.warning("*No se encontro informacion de dias desde egreso anterior*")
        
        # ============================================
        # TABLA DE VARIABLES DEL MODELO
        # ============================================
        st.markdown(Componentes.separador(), unsafe_allow_html=True)
        
        st.markdown(
            Componentes.texto_destacado(
                "Criterios de validacion del usuario con relacion a los modelos evaluados"
            ),
            unsafe_allow_html=True
        )
        
        if df_pesos is not None:
            # GSCA 28-04-2026: Se excluyen IMC, PESO y TALLA del modelo
            # PRESION_ARTERIAL ahora SI se muestra en la tabla de variables
            variables_excluir = ['IMC', 'PESO', 'TALLA']
            variables_procesadas = set()

            datos_variables = []
            
            for _, row_peso in df_pesos.iterrows():
                var = row_peso['Variable']
                
                if var in variables_excluir:
                    continue
                
                # Obtener nombre descriptivo
                nombre_mostrar = obtener_nombre_variable(var)
                
                # Evitar duplicados
                if nombre_mostrar in variables_procesadas:
                    continue
                variables_procesadas.add(nombre_mostrar)
                
                peso_promedio = row_peso.get('Peso_Promedio_%', 0)
                peso_lr = row_peso.get('Peso_RegLogistica_%', 0)
                peso_rf = row_peso.get('Peso_RandomForest_%', 0)
                peso_gb = row_peso.get('Peso_GradientBoosting_%', 0)
                
                datos_variables.append({
                    "Descripcion": nombre_mostrar,
                    "Promedio modelos (%)": f"{peso_promedio:.2f}%",
                    "(%) Regresion logistica": f"{peso_lr:.2f}%",
                    "(%) Random Forest": f"{peso_rf:.2f}%",
                    "(%) Gradient Boosting": f"{peso_gb:.2f}%",
                    "PesoNum": peso_promedio
                })
            
            # Ordenar por peso
            datos_variables = sorted(datos_variables, key=lambda x: x["PesoNum"], reverse=True)
            
            df_variables = pd.DataFrame(datos_variables)
            
            st.dataframe(
                df_variables[["Descripcion", "Promedio modelos (%)", "(%) Regresion logistica", "(%) Random Forest", "(%) Gradient Boosting"]],
                use_container_width=True,
                hide_index=True,
                height=350
            )
        else:
            st.warning("No se pudieron cargar los pesos del modelo")

# ============================================
# FOOTER
# ============================================
st.markdown(Componentes.separador(), unsafe_allow_html=True)
st.markdown(Componentes.footer(), unsafe_allow_html=True)
