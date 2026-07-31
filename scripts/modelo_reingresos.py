# ============================================
# MODELO PREDICTIVO DE PROBABILIDAD DE REINGRESOS HOSPITALARIOS
# Compara 3 modelos: Gradient Boosting, Random Forest, Regresión Logística
# Conexión a SQL Server - Para integración con Power BI
# ============================================

import pandas as pd
import numpy as np
import pyodbc
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings
warnings.filterwarnings('ignore')

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, roc_curve, 
    precision_recall_curve, accuracy_score, precision_score, recall_score, 
    f1_score, average_precision_score
)
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer

# Configuración de estilo para gráficos
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Crear directorio de salida
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output') + os.sep
os.makedirs(output_dir, exist_ok=True)

print(f"Carpeta de salida: {output_dir}")

# ============================================
# 1. CONEXIÓN A SQL SERVER
# ============================================

print("=" * 70)
print("MODELO PREDICTIVO DE PROBABILIDAD DE REINGRESOS")
print("Comparación de 3 Modelos: Gradient Boosting, Random Forest, Regresión Logística")
print("=" * 70)

try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=192.168.0.11\\DINAMICA;"
        "DATABASE=DGEmpres01;"
        "UID=p_dinamica;"
        "PWD=Pruebas.Dinamica;"
        "TrustServerCertificate=yes;"
    )
    print("Conexión exitosa a SQL Server")
except Exception as e:
    print(f"Error de conexión: {e}")
    exit(1)

# ============================================
# 2. CONSULTA DE DATOS DESDE V_Analisis_Reingresos
# ============================================

print("\n" + "=" * 70)
print("EXTRACCIÓN DE DATOS")
print("=" * 70)

query = """
SELECT
    ar.DOCUMENTO,
    CASE
        WHEN ar.SEXO = 'MASCULINO' THEN 1
        WHEN ar.SEXO = 'FEMENINO' THEN 2
        ELSE 0
    END AS SEXO,
    ar.EDAD,
    ar.ASEGURADOR,
    ar.INGRESO_ACTUAL,
    ar.FECHA_INGRESO_ACTUAL,
    ar.FECHA_EGRESO_DEL_INGRESO_ACTUAL,
    ar.COD_DX_INGRESO,
    ar.NOM_DX_INGRESO,
    ar.COD_DX_EGRESO,
    ar.NOM_DX_EGRESO,
    CASE
        WHEN ar.ESTADO_EGRESO = 'MEJOR' THEN 1
        WHEN ar.ESTADO_EGRESO = 'IGUAL O PEOR' THEN 2
        WHEN ar.ESTADO_EGRESO = 'MUERTO DESPUES DE 48 HORAS' THEN 3
        WHEN ar.ESTADO_EGRESO = 'MUERTO ANTES DE 48 HORAS' THEN 4
        ELSE 0
    END AS ESTADO_EGRESO,
    ar.ANTECEDENTES_PERSONALES,
    ar.ANTECEDENTES_FAMILIARES,
    CASE
        WHEN ar.PESO BETWEEN 0.2 AND 250 THEN ar.PESO
        ELSE NULL
    END AS PESO,
    CASE
        WHEN ar.TALLA BETWEEN 20 AND 225 THEN ar.TALLA
        ELSE NULL
    END AS TALLA,
    ar.PRESION_ARTERIAL,
    ar.HOSPITALIZACIONES_ULTIMO_AÑO,
    ar.TIEMPO_ULTIMA_HOSPITALIZACION,
    ar.DURACION_ESTANCIA_ACTUAL,
    ar.NUMERO_MEDICAMENTOS,
    CASE
        WHEN ar.ADHERENCIA_PREVIA = 'SI' THEN 1
        WHEN ar.ADHERENCIA_PREVIA = 'NO' THEN 2
        ELSE 0
    END AS ADHERENCIA_PREVIA,
    CASE
        WHEN ar.CAUSA_INGRESO = 'DIFERENTE CAUSA' THEN 1
        WHEN ar.CAUSA_INGRESO = 'MISMA CAUSA' THEN 2
        ELSE 0
    END AS CAUSA_INGRESO
FROM V_Analisis_Reingresos AS ar
"""

try:
    df = pd.read_sql(query, conn)
    print(f"Datos extraídos exitosamente: {df['DOCUMENTO'].nunique()} pacientes únicos")
    print(f"Total de registros (hospitalizaciones): {len(df)}")
except Exception as e:
    print(f"Error al ejecutar la consulta: {e}")
    conn.close()
    exit(1)

# ============================================
# 3. PREPARACIÓN DE DATOS
# ============================================

print("\n" + "=" * 70)
print("PREPARACIÓN DE DATOS")
print("=" * 70)

# Calcular IMC solo donde hay peso y talla válidos
df['IMC'] = np.where(
    (df['PESO'].notna()) & (df['TALLA'].notna()) & (df['TALLA'] > 0),
    df['PESO'] / ((df['TALLA'] / 100) ** 2),
    np.nan
)

# Categorizar IMC
def categorizar_imc(imc):
    if pd.isna(imc):
        return 'Sin dato'
    elif imc < 18.5:
        return 'Bajo peso'
    elif imc < 25:
        return 'Normal'
    elif imc < 30:
        return 'Sobrepeso'
    else:
        return 'Obesidad'

df['CATEGORIA_IMC'] = df['IMC'].apply(categorizar_imc)

# Categorizar edad
def categorizar_edad(edad):
    if pd.isna(edad):
        return 'Sin dato'
    elif edad < 30:
        return 'Joven'
    elif edad < 50:
        return 'Adulto'
    elif edad < 65:
        return 'Adulto Mayor'
    else:
        return 'Tercera Edad'

df['GRUPO_EDAD'] = df['EDAD'].apply(categorizar_edad)

# Procesar PRESION_ARTERIAL (convertir "120/80" a valores numéricos)
def extraer_presion_sistolica(presion):
    """Extrae la presión sistólica (primer valor) de un string como '120/80'"""
    if pd.isna(presion) or presion is None:
        return np.nan
    try:
        presion_str = str(presion).strip()
        if '/' in presion_str:
            sistolica = float(presion_str.split('/')[0])
            # Validar que esté en rango razonable (60-250)
            if 60 <= sistolica <= 250:
                return sistolica
        return np.nan
    except:
        return np.nan

def extraer_presion_diastolica(presion):
    """Extrae la presión diastólica (segundo valor) de un string como '120/80'"""
    if pd.isna(presion) or presion is None:
        return np.nan
    try:
        presion_str = str(presion).strip()
        if '/' in presion_str:
            diastolica = float(presion_str.split('/')[1])
            # Validar que esté en rango razonable (30-150)
            if 30 <= diastolica <= 150:
                return diastolica
        return np.nan
    except:
        return np.nan

# Extraer valores numéricos de presión arterial
df['PRESION_SISTOLICA'] = df['PRESION_ARTERIAL'].apply(extraer_presion_sistolica)
df['PRESION_DIASTOLICA'] = df['PRESION_ARTERIAL'].apply(extraer_presion_diastolica)

# Calcular presión arterial media (PAM = (sistólica + 2*diastólica) / 3)
df['PRESION_ARTERIAL_MEDIA'] = (df['PRESION_SISTOLICA'] + 2 * df['PRESION_DIASTOLICA']) / 3

print(f"\nProcesamiento de Presión Arterial:")
print(f"   - Registros con presión arterial válida: {df['PRESION_SISTOLICA'].notna().sum()}")
print(f"   - Presión sistólica promedio: {df['PRESION_SISTOLICA'].mean():.1f} mmHg")
print(f"   - Presión diastólica promedio: {df['PRESION_DIASTOLICA'].mean():.1f} mmHg")

# ============================================
# CÁLCULO DE REINGRESO CON CRITERIO TEMPORAL
# Un reingreso es cuando:
# - CAUSA_INGRESO = 2 (MISMA CAUSA)
# - FECHA_INGRESO_ACTUAL < 15 días después de FECHA_EGRESO_DEL_INGRESO_ACTUAL anterior
# ============================================

# Convertir fechas a datetime
df['FECHA_INGRESO_ACTUAL'] = pd.to_datetime(df['FECHA_INGRESO_ACTUAL'], errors='coerce')
df['FECHA_EGRESO_DEL_INGRESO_ACTUAL'] = pd.to_datetime(df['FECHA_EGRESO_DEL_INGRESO_ACTUAL'], errors='coerce')

# Ordenar por documento y fecha de ingreso
df = df.sort_values(['DOCUMENTO', 'FECHA_INGRESO_ACTUAL']).reset_index(drop=True)

# Calcular la fecha de egreso del ingreso anterior
df['FECHA_EGRESO_ANTERIOR'] = df.groupby('DOCUMENTO')['FECHA_EGRESO_DEL_INGRESO_ACTUAL'].shift(1)

# Calcular los días transcurridos desde el egreso anterior
df['DIAS_DESDE_EGRESO_ANTERIOR'] = (df['TIEMPO_ULTIMA_HOSPITALIZACION'])

# Variable objetivo: REINGRESO (reingreso por misma causa dentro de 15 días)
df['ES_MISMA_CAUSA'] = (df['CAUSA_INGRESO'] == 2)
df['TIEMPO_ULTIMA_HOSPITALIZACION'] = pd.to_numeric(
    df['TIEMPO_ULTIMA_HOSPITALIZACION'],
    errors='coerce'  # convierte errores a NaN
)
df['DENTRO_15_DIAS'] = (df['TIEMPO_ULTIMA_HOSPITALIZACION']) <= 15
df['REINGRESO'] = ((df['ES_MISMA_CAUSA']) & (df['DENTRO_15_DIAS'])).astype(int)

# Mapeos de texto
adherencia_map = {0: 'Sin dato', 1: 'Con tratamiento', 2: 'Sin tratamiento'}
df['ADHERENCIA_TEXTO'] = df['ADHERENCIA_PREVIA'].map(adherencia_map)
sexo_map = {0: 'Sin dato', 1: 'Masculino', 2: 'Femenino'}
df['SEXO_TEXTO'] = df['SEXO'].map(sexo_map)
estado_map = {0: 'Sin dato', 1: 'Mejor', 2: 'Igual o Peor', 3: 'Muerto >48h', 4: 'Muerto <48h'}
df['ESTADO_EGRESO_TEXTO'] = df['ESTADO_EGRESO'].map(estado_map)

n_reingresos = df['REINGRESO'].sum()
n_total = len(df)
tasa_reingreso = n_reingresos / n_total * 100

print(f"\nAnálisis de criterios de reingreso:")
print(f"   - Pacientes con misma causa: {df['ES_MISMA_CAUSA'].sum()}")
print(f"   - Ingresos dentro de 15 días del egreso anterior: {df['DENTRO_15_DIAS'].sum()}")
print(f"   - REINGRESOS (misma causa + <=15 días): {n_reingresos}")
print(f"   - Tasa de reingreso: {tasa_reingreso:.2f}%")

# ============================================
# 3.5 TRATAMIENTO DE VALORES NULOS CON MEDIA/MEDIANA
# ============================================

print("\n" + "=" * 70)
print("TRATAMIENTO DE VALORES NULOS")
print("=" * 70)

# Features para el modelo (ahora incluye PRESION_ARTERIAL_MEDIA y ADHERENCIA_PREVIA)
features = ['SEXO', 'EDAD', 'HOSPITALIZACIONES_ULTIMO_AÑO', 
            'DURACION_ESTANCIA_ACTUAL', 'NUMERO_MEDICAMENTOS', 'ADHERENCIA_PREVIA',
            'ESTADO_EGRESO', 'IMC', 'PRESION_ARTERIAL_MEDIA']

# Mostrar valores nulos antes del tratamiento
print("\nValores nulos por variable (antes del tratamiento):")
for feat in features:
    nulos = df[feat].isnull().sum()
    pct = nulos / len(df) * 100
    print(f"   - {feat}: {nulos} ({pct:.2f}%)")

# Crear copia del dataframe para el modelo
df_modelo = df.copy()

# Imputar valores faltantes con la MEDIANA para variables numéricas
# (la mediana es más robusta a outliers que la media)
imputer = SimpleImputer(strategy='median')
df_modelo[features] = imputer.fit_transform(df_modelo[features])

print("\nValores nulos imputados con la MEDIANA de cada columna.")
print("Valores nulos después del tratamiento: 0")

# ============================================
# 4. MATRICES DE CORRELACIÓN
# ============================================

print("\n" + "=" * 70)
print("MATRICES DE CORRELACIÓN")
print("=" * 70)

# Variables numéricas para correlación (incluye PRESION_ARTERIAL_MEDIA)
vars_correlacion = ['SEXO', 'EDAD', 'HOSPITALIZACIONES_ULTIMO_AÑO', 
                    'DURACION_ESTANCIA_ACTUAL', 'NUMERO_MEDICAMENTOS', 
                    'ADHERENCIA_PREVIA', 'ESTADO_EGRESO', 'IMC', 
                    'PRESION_ARTERIAL_MEDIA', 'REINGRESO']

# Crear dataframe con variables para correlación
df_corr = df_modelo[vars_correlacion].copy()

# Calcular matriz de correlación
matriz_corr = df_corr.corr()

# Mostrar correlaciones con REINGRESO
print("\nCorrelación de variables con REINGRESO:")
corr_con_reingreso = matriz_corr['REINGRESO'].drop('REINGRESO').sort_values(key=abs, ascending=False)
for var, corr in corr_con_reingreso.items():
    signo = "+" if corr > 0 else ""
    print(f"   - {var}: {signo}{corr:.4f}")

# Exportar matriz de correlación a CSV
matriz_corr.to_csv(f'{output_dir}MATRIZ_CORRELACION_COMPLETA.csv', encoding='utf-8-sig')
corr_con_reingreso.to_frame('CORRELACION_CON_REINGRESO').to_csv(
    f'{output_dir}CORRELACION_CON_REINGRESO.csv', encoding='utf-8-sig'
)
print(f"\nMatrices exportadas a CSV")

# --- GRÁFICO: Matriz de Correlación Completa ---
fig, ax = plt.subplots(figsize=(12, 10))
mask = np.triu(np.ones_like(matriz_corr, dtype=bool), k=1)
cmap = sns.diverging_palette(250, 10, as_cmap=True)
sns.heatmap(matriz_corr, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
            square=True, linewidths=0.5, cbar_kws={"shrink": 0.8},
            annot=True, fmt='.2f', annot_kws={'size': 9})
ax.set_title('Matriz de Correlación - Variables del Modelo de Reingreso', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{output_dir}00_matriz_correlacion_completa.png', dpi=150, bbox_inches='tight')
plt.close()
print("   - 00_matriz_correlacion_completa.png")

# --- GRÁFICO: Correlación con REINGRESO (barras horizontales) ---
fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#e74c3c' if c < 0 else '#2ecc71' for c in corr_con_reingreso.values]
bars = ax.barh(range(len(corr_con_reingreso)), corr_con_reingreso.values, color=colors, edgecolor='black')
ax.set_yticks(range(len(corr_con_reingreso)))
ax.set_yticklabels(corr_con_reingreso.index)
ax.set_xlabel('Coeficiente de Correlación (Pearson)')
ax.set_title('Correlación de Variables con REINGRESO\n(Verde: aumenta riesgo, Rojo: disminuye riesgo)')
ax.axvline(0, color='black', linewidth=0.5)
ax.axvline(0.1, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
ax.axvline(-0.1, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
for i, (bar, val) in enumerate(zip(bars, corr_con_reingreso.values)):
    ax.text(val + 0.01 if val >= 0 else val - 0.01, i, f'{val:.3f}', 
            va='center', ha='left' if val >= 0 else 'right', fontsize=9)
plt.tight_layout()
plt.savefig(f'{output_dir}00_correlacion_con_reingreso.png', dpi=150, bbox_inches='tight')
plt.close()
print("   - 00_correlacion_con_reingreso.png")

# ============================================
# 5. MODELO PREDICTIVO - ENTRENAMIENTO DE 3 MODELOS
# ============================================

print("\n" + "=" * 70)
print("ENTRENAMIENTO DE MODELOS PREDICTIVOS")
print("=" * 70)

# Verificar que tenemos suficientes datos
print(f"\nRegistros disponibles para el modelo: {len(df_modelo)}")
print(f"Reingresos en los datos: {df_modelo['REINGRESO'].sum()} ({df_modelo['REINGRESO'].mean()*100:.2f}%)")

if df_modelo['REINGRESO'].sum() < 10:
    print("\nADVERTENCIA: Muy pocos casos de reingreso para entrenar un modelo confiable.")
    print("Se procederá con el entrenamiento pero los resultados pueden no ser confiables.")

X = df_modelo[features].copy()
y = df_modelo['REINGRESO']

# Dividir datos (70% entrenamiento, 30% prueba)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, 
    stratify=y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
)

print(f"\nConjunto de entrenamiento: {len(X_train)} registros")
print(f"Conjunto de prueba: {len(X_test)} registros")

# Escalar datos
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
X_all_scaled = scaler.transform(X)

# ============================================
# 5.1 ENTRENAR LOS 3 MODELOS
# ============================================

print("\n" + "-" * 50)
print("ENTRENAMIENTO DE MODELOS")
print("-" * 50)

# Diccionario para almacenar resultados
resultados = {}

# Modelo 1: Regresión Logística
print("\n1. Entrenando Regresión Logística...")
modelo_lr = LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')
modelo_lr.fit(X_train_scaled, y_train)
y_pred_lr = modelo_lr.predict(X_test_scaled)
y_pred_proba_lr = modelo_lr.predict_proba(X_test_scaled)[:, 1]
try:
    auc_lr = roc_auc_score(y_test, y_pred_proba_lr)
except:
    auc_lr = 0.5
print(f"   AUC-ROC: {auc_lr:.3f}")

resultados['Regresión Logística'] = {
    'modelo': modelo_lr,
    'y_pred': y_pred_lr,
    'y_prob': y_pred_proba_lr,
    'usa_scaled': True
}

# Modelo 2: Random Forest
print("\n2. Entrenando Random Forest...")
modelo_rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5, class_weight='balanced')
modelo_rf.fit(X_train, y_train)
y_pred_rf = modelo_rf.predict(X_test)
y_pred_proba_rf = modelo_rf.predict_proba(X_test)[:, 1]
try:
    auc_rf = roc_auc_score(y_test, y_pred_proba_rf)
except:
    auc_rf = 0.5
print(f"   AUC-ROC: {auc_rf:.3f}")

resultados['Random Forest'] = {
    'modelo': modelo_rf,
    'y_pred': y_pred_rf,
    'y_prob': y_pred_proba_rf,
    'usa_scaled': False
}

# Modelo 3: Gradient Boosting
print("\n3. Entrenando Gradient Boosting...")
modelo_gb = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5, learning_rate=0.1)
modelo_gb.fit(X_train, y_train)
y_pred_gb = modelo_gb.predict(X_test)
y_pred_proba_gb = modelo_gb.predict_proba(X_test)[:, 1]
try:
    auc_gb = roc_auc_score(y_test, y_pred_proba_gb)
except:
    auc_gb = 0.5
print(f"   AUC-ROC: {auc_gb:.3f}")

resultados['Gradient Boosting'] = {
    'modelo': modelo_gb,
    'y_pred': y_pred_gb,
    'y_prob': y_pred_proba_gb,
    'usa_scaled': False
}

# ============================================
# 5.2 PESO/IMPORTANCIA DE LAS VARIABLES
# ============================================

print("\n" + "=" * 70)
print("PESO/IMPORTANCIA DE LAS VARIABLES EN CADA MODELO")
print("=" * 70)

# DataFrame para almacenar importancias
importancias_df = pd.DataFrame({'Variable': features})

# 1. Regresión Logística - Coeficientes (peso)
coef_lr = modelo_lr.coef_[0]
importancias_df['Coef_RegLogistica'] = coef_lr
importancias_df['Peso_RegLogistica_%'] = (np.abs(coef_lr) / np.abs(coef_lr).sum()) * 100

print("\n1. REGRESIÓN LOGÍSTICA (Coeficientes):")
print("   (Valores positivos aumentan probabilidad de reingreso, negativos la disminuyen)")
for i, feat in enumerate(features):
    signo = "+" if coef_lr[i] > 0 else ""
    print(f"   - {feat}: {signo}{coef_lr[i]:.4f} (Peso: {importancias_df['Peso_RegLogistica_%'].iloc[i]:.2f}%)")

# 2. Random Forest - Feature Importance
imp_rf = modelo_rf.feature_importances_
importancias_df['Importancia_RandomForest'] = imp_rf
importancias_df['Peso_RandomForest_%'] = imp_rf * 100

print("\n2. RANDOM FOREST (Feature Importance):")
for i, feat in enumerate(features):
    print(f"   - {feat}: {imp_rf[i]:.4f} (Peso: {imp_rf[i]*100:.2f}%)")

# 3. Gradient Boosting - Feature Importance
imp_gb = modelo_gb.feature_importances_
importancias_df['Importancia_GradientBoosting'] = imp_gb
importancias_df['Peso_GradientBoosting_%'] = imp_gb * 100

print("\n3. GRADIENT BOOSTING (Feature Importance):")
for i, feat in enumerate(features):
    print(f"   - {feat}: {imp_gb[i]:.4f} (Peso: {imp_gb[i]*100:.2f}%)")

# Calcular peso promedio de los 3 modelos
importancias_df['Peso_Promedio_%'] = (
    importancias_df['Peso_RegLogistica_%'] + 
    importancias_df['Peso_RandomForest_%'] + 
    importancias_df['Peso_GradientBoosting_%']
) / 3

# Ordenar por peso promedio
importancias_df_sorted = importancias_df.sort_values('Peso_Promedio_%', ascending=False)

print("\n" + "-" * 50)
print("RANKING DE VARIABLES POR PESO PROMEDIO (3 MODELOS):")
print("-" * 50)
for idx, row in importancias_df_sorted.iterrows():
    print(f"   {row['Variable']}: {row['Peso_Promedio_%']:.2f}%")
    print(f"      - Reg. Logística: {row['Peso_RegLogistica_%']:.2f}%")
    print(f"      - Random Forest:  {row['Peso_RandomForest_%']:.2f}%")
    print(f"      - Gradient Boost: {row['Peso_GradientBoosting_%']:.2f}%")

# Exportar importancia de variables a CSV
importancias_df_sorted.to_csv(f'{output_dir}IMPORTANCIA_PESO_VARIABLES.csv', index=False, encoding='utf-8-sig')
print(f"\nExportado: IMPORTANCIA_PESO_VARIABLES.csv")

# --- GRÁFICO: Comparación de Pesos por Modelo ---
fig, axes = plt.subplots(1, 4, figsize=(24, 6))

# Ordenar para cada gráfico
df_plot_lr = importancias_df.sort_values('Peso_RegLogistica_%', ascending=True)
colors_lr = ['#e74c3c' if c < 0 else '#2ecc71' for c in df_plot_lr['Coef_RegLogistica']]
axes[0].barh(df_plot_lr['Variable'], df_plot_lr['Peso_RegLogistica_%'], color=colors_lr, edgecolor='black')
axes[0].set_xlabel('Peso (%)')
axes[0].set_title('Regresión Logística\n(Verde: + riesgo, Rojo: - riesgo)', fontweight='bold')
for i, (v, p) in enumerate(zip(df_plot_lr['Variable'], df_plot_lr['Peso_RegLogistica_%'])):
    axes[0].text(p + 0.5, i, f'{p:.1f}%', va='center', fontsize=9)

df_plot_rf = importancias_df.sort_values('Peso_RandomForest_%', ascending=True)
axes[1].barh(df_plot_rf['Variable'], df_plot_rf['Peso_RandomForest_%'], color='#2ecc71', edgecolor='black')
axes[1].set_xlabel('Peso (%)')
axes[1].set_title('Random Forest\n(Feature Importance)', fontweight='bold')
for i, (v, p) in enumerate(zip(df_plot_rf['Variable'], df_plot_rf['Peso_RandomForest_%'])):
    axes[1].text(p + 0.5, i, f'{p:.1f}%', va='center', fontsize=9)

df_plot_gb = importancias_df.sort_values('Peso_GradientBoosting_%', ascending=True)
axes[2].barh(df_plot_gb['Variable'], df_plot_gb['Peso_GradientBoosting_%'], color='#e67e22', edgecolor='black')
axes[2].set_xlabel('Peso (%)')
axes[2].set_title('Gradient Boosting\n(Feature Importance)', fontweight='bold')
for i, (v, p) in enumerate(zip(df_plot_gb['Variable'], df_plot_gb['Peso_GradientBoosting_%'])):
    axes[2].text(p + 0.5, i, f'{p:.1f}%', va='center', fontsize=9)

# Gráfico de peso promedio
df_plot_prom = importancias_df.sort_values('Peso_Promedio_%', ascending=True)
axes[3].barh(df_plot_prom['Variable'], df_plot_prom['Peso_Promedio_%'], color='#9b59b6', edgecolor='black')
axes[3].set_xlabel('Peso Promedio (%)')
axes[3].set_title('PESO PROMEDIO\n(3 Modelos)', fontweight='bold')
for i, (v, p) in enumerate(zip(df_plot_prom['Variable'], df_plot_prom['Peso_Promedio_%'])):
    axes[3].text(p + 0.5, i, f'{p:.1f}%', va='center', fontsize=9)

plt.suptitle('PESO/IMPORTANCIA DE CADA VARIABLE POR MODELO', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{output_dir}00_peso_variables_comparacion.png', dpi=150, bbox_inches='tight')
plt.close()
print("   - 00_peso_variables_comparacion.png")

# ============================================
# 6. CÁLCULO DE MÉTRICAS PARA CADA MODELO
# ============================================

print("\n" + "=" * 70)
print("MÉTRICAS DE EVALUACIÓN DE CADA MODELO")
print("=" * 70)

metricas_df = []

for nombre, data in resultados.items():
    y_pred = data['y_pred']
    y_prob = data['y_prob']
    
    # Calcular métricas
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    try:
        roc_auc = roc_auc_score(y_test, y_prob)
    except:
        roc_auc = 0.5
    
    # Guardar métricas
    resultados[nombre]['metricas'] = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc
    }
    
    metricas_df.append({
        'Modelo': nombre,
        'Accuracy (%)': accuracy * 100,
        'Precisión (%)': precision * 100,
        'Recall (%)': recall * 100,
        'F1-Score (%)': f1 * 100,
        'ROC-AUC (%)': roc_auc * 100
    })
    
    print(f"\n{nombre}:")
    print(f"   - Accuracy:   {accuracy*100:.2f}%")
    print(f"   - Precisión:  {precision*100:.2f}%")
    print(f"   - Recall:     {recall*100:.2f}%")
    print(f"   - F1-Score:   {f1*100:.2f}%")
    print(f"   - ROC-AUC:    {roc_auc*100:.2f}%")

metricas_df = pd.DataFrame(metricas_df)

# Seleccionar mejor modelo basado en AUC-ROC
aucs = {'Regresión Logística': auc_lr, 'Random Forest': auc_rf, 'Gradient Boosting': auc_gb}
mejor_nombre = max(aucs, key=aucs.get)
mejor_auc = aucs[mejor_nombre]

print(f"\n{'='*50}")
print(f"MEJOR MODELO: {mejor_nombre}")
print(f"AUC-ROC: {mejor_auc:.3f}")
print(f"{'='*50}")

# ============================================
# 7. CALCULAR PROBABILIDAD DE REINGRESO PARA TODOS LOS PACIENTES
# ============================================

print("\n" + "=" * 70)
print("CALCULANDO PROBABILIDAD DE REINGRESO PARA CADA PACIENTE")
print("=" * 70)

# Calcular probabilidad con cada modelo
df_modelo['PROB_REINGRESO_LR'] = modelo_lr.predict_proba(X_all_scaled)[:, 1]
df_modelo['PROB_REINGRESO_RF'] = modelo_rf.predict_proba(X)[:, 1]
df_modelo['PROB_REINGRESO_GB'] = modelo_gb.predict_proba(X)[:, 1]

# Probabilidad del mejor modelo
if mejor_nombre == 'Regresión Logística':
    df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_LR']
elif mejor_nombre == 'Random Forest':
    df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_RF']
else:
    df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_GB']

# Promedio de los 3 modelos (ensemble)
df_modelo['PROB_REINGRESO_ENSEMBLE'] = (
    df_modelo['PROB_REINGRESO_LR'] + 
    df_modelo['PROB_REINGRESO_RF'] + 
    df_modelo['PROB_REINGRESO_GB']
) / 3

# Categorizar el riesgo de reingreso
def categorizar_riesgo(prob):
    if prob >= 0.7:
        return 'ALTO'
    elif prob >= 0.4:
        return 'MEDIO'
    else:
        return 'BAJO'

df_modelo['NIVEL_RIESGO_REINGRESO'] = df_modelo['PROBABILIDAD_REINGRESO'].apply(categorizar_riesgo)

# Estadísticas de probabilidad
print(f"\nEstadísticas de Probabilidad de Reingreso:")
print(f"   - Mínima: {df_modelo['PROBABILIDAD_REINGRESO'].min()*100:.2f}%")
print(f"   - Máxima: {df_modelo['PROBABILIDAD_REINGRESO'].max()*100:.2f}%")
print(f"   - Promedio: {df_modelo['PROBABILIDAD_REINGRESO'].mean()*100:.2f}%")
print(f"   - Mediana: {df_modelo['PROBABILIDAD_REINGRESO'].median()*100:.2f}%")

# Distribución por nivel de riesgo
print(f"\nDistribución por Nivel de Riesgo:")
riesgo_counts = df_modelo['NIVEL_RIESGO_REINGRESO'].value_counts()
for nivel in ['ALTO', 'MEDIO', 'BAJO']:
    if nivel in riesgo_counts.index:
        count = riesgo_counts[nivel]
        pct = count / len(df_modelo) * 100
        print(f"   - {nivel}: {count} pacientes ({pct:.1f}%)")

# ============================================
# 8. VISUALIZACIONES - COMPARACIÓN DE MODELOS
# ============================================

print("\n" + "=" * 70)
print("GENERANDO VISUALIZACIONES")
print("=" * 70)

# --- GRÁFICO 1: Comparación de Métricas entre Modelos ---
print("   Generando: 01_comparacion_metricas.png")
fig, ax = plt.subplots(figsize=(14, 6))

metricas_plot = metricas_df.set_index('Modelo')[['Accuracy (%)', 'Precisión (%)', 'Recall (%)', 'F1-Score (%)', 'ROC-AUC (%)']]
x = np.arange(len(metricas_plot.columns))
width = 0.25

colors = ['#3498db', '#2ecc71', '#e67e22']
modelos_orden = ['Regresión Logística', 'Random Forest', 'Gradient Boosting']

for i, modelo in enumerate(modelos_orden):
    if modelo in metricas_plot.index:
        row = metricas_plot.loc[modelo]
        bars = ax.bar(x + i*width, row.values, width, label=modelo, color=colors[i], edgecolor='black', linewidth=0.5)
        for bar, val in zip(bars, row.values):
            ax.annotate(f'{val:.1f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                       xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=8)

ax.set_ylabel('Porcentaje (%)', fontsize=12)
ax.set_title('COMPARACIÓN DE MÉTRICAS ENTRE MODELOS\n(Para Predicción de Reingreso Hospitalario)', fontsize=14, fontweight='bold')
ax.set_xticks(x + width)
ax.set_xticklabels(metricas_plot.columns, rotation=15, ha='right')
ax.legend(loc='upper right')
ax.set_ylim(0, 110)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{output_dir}01_comparacion_metricas.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 01_comparacion_metricas.png")

# --- GRÁFICO 2: Matrices de Confusión ---
print("   Generando: 02_matrices_confusion.png")
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

for idx, (nombre, data) in enumerate(resultados.items()):
    cm = confusion_matrix(y_test, data['y_pred'])
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                xticklabels=['No Reingreso', 'Reingreso'],
                yticklabels=['No Reingreso', 'Reingreso'])
    acc = data['metricas']['accuracy']
    axes[idx].set_title(f'{nombre}\nAccuracy: {acc*100:.2f}%', fontsize=11, fontweight='bold')
    axes[idx].set_ylabel('Real')
    axes[idx].set_xlabel('Predicho')

plt.suptitle('MATRICES DE CONFUSIÓN POR MODELO', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{output_dir}02_matrices_confusion.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 02_matrices_confusion.png")

# --- GRÁFICO 3: Curvas ROC ---
print("   Generando: 03_curvas_roc.png")
fig, ax = plt.subplots(figsize=(10, 8))

colors_roc = {'Regresión Logística': '#3498db', 'Random Forest': '#2ecc71', 'Gradient Boosting': '#e67e22'}

for nombre, data in resultados.items():
    fpr, tpr, _ = roc_curve(y_test, data['y_prob'])
    auc = data['metricas']['roc_auc']
    ax.plot(fpr, tpr, label=f'{nombre} (AUC = {auc:.3f})', color=colors_roc[nombre], linewidth=2)

ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Clasificador aleatorio (AUC = 0.5)')
ax.set_xlabel('Tasa de Falsos Positivos (1 - Especificidad)', fontsize=11)
ax.set_ylabel('Tasa de Verdaderos Positivos (Sensibilidad)', fontsize=11)
ax.set_title('CURVAS ROC - COMPARACIÓN DE MODELOS\nPara Predicción de Reingreso Hospitalario', fontsize=14, fontweight='bold')
ax.legend(loc='lower right')
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{output_dir}03_curvas_roc.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 03_curvas_roc.png")

# --- GRÁFICO 4: Curvas Precision-Recall ---
print("   Generando: 04_curvas_precision_recall.png")
fig, ax = plt.subplots(figsize=(10, 8))

for nombre, data in resultados.items():
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, data['y_prob'])
    ap = average_precision_score(y_test, data['y_prob'])
    ax.plot(recall_curve, precision_curve, label=f'{nombre} (AP = {ap:.3f})', color=colors_roc[nombre], linewidth=2)

ax.set_xlabel('Recall', fontsize=11)
ax.set_ylabel('Precision', fontsize=11)
ax.set_title('CURVAS PRECISION-RECALL - COMPARACIÓN DE MODELOS', fontsize=14, fontweight='bold')
ax.legend(loc='upper right')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{output_dir}04_curvas_precision_recall.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 04_curvas_precision_recall.png")

# --- GRÁFICO 5: Importancia de Variables ---
print("   Generando: 05_importancia_variables.png")
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('IMPORTANCIA DE VARIABLES PARA PREDECIR REINGRESO', fontsize=14, fontweight='bold')

# Regresión Logística (coeficientes)
coef_df = pd.DataFrame({
    'Variable': features,
    'Coeficiente': modelo_lr.coef_[0],
    'Importancia_Abs': np.abs(modelo_lr.coef_[0])
}).sort_values('Importancia_Abs', ascending=True)

colors_coef = ['#e74c3c' if c < 0 else '#2ecc71' for c in coef_df['Coeficiente']]
axes[0].barh(coef_df['Variable'], coef_df['Importancia_Abs'], color=colors_coef, edgecolor='black')
axes[0].set_xlabel('|Coeficiente|')
axes[0].set_title('Regresión Logística\n(Rojo: disminuye riesgo, Verde: aumenta)')

# Random Forest
importancia_rf = pd.DataFrame({
    'Variable': features,
    'Importancia': modelo_rf.feature_importances_
}).sort_values('Importancia', ascending=True)
axes[1].barh(importancia_rf['Variable'], importancia_rf['Importancia'], color='#2ecc71', edgecolor='black')
axes[1].set_xlabel('Importancia')
axes[1].set_title('Random Forest')

# Gradient Boosting
importancia_gb = pd.DataFrame({
    'Variable': features,
    'Importancia': modelo_gb.feature_importances_
}).sort_values('Importancia', ascending=True)
axes[2].barh(importancia_gb['Variable'], importancia_gb['Importancia'], color='#e67e22', edgecolor='black')
axes[2].set_xlabel('Importancia')
axes[2].set_title('Gradient Boosting')

plt.tight_layout()
plt.savefig(f'{output_dir}05_importancia_variables.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 05_importancia_variables.png")

# --- GRÁFICO 6: Distribución de Probabilidades Predichas ---
print("   Generando: 06_distribucion_probabilidades.png")
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

probs = {
    'Regresión Logística': y_pred_proba_lr,
    'Random Forest': y_pred_proba_rf,
    'Gradient Boosting': y_pred_proba_gb
}

for idx, (nombre, prob) in enumerate(probs.items()):
    axes[idx].hist(prob[y_test == 0], bins=30, alpha=0.7, label='No Reingreso', color='#3498db')
    axes[idx].hist(prob[y_test == 1], bins=30, alpha=0.7, label='Reingreso', color='#e74c3c')
    axes[idx].set_xlabel('Probabilidad Predicha')
    axes[idx].set_ylabel('Frecuencia')
    axes[idx].set_title(f'{nombre}', fontsize=11)
    axes[idx].legend()

plt.suptitle('DISTRIBUCIÓN DE PROBABILIDADES PREDICHAS POR CLASE', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{output_dir}06_distribucion_probabilidades.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 06_distribucion_probabilidades.png")

# --- GRÁFICO 7: Distribución por Nivel de Riesgo ---
print("   Generando: 07_distribucion_nivel_riesgo.png")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

colores_riesgo = {'ALTO': '#e74c3c', 'MEDIO': '#f39c12', 'BAJO': '#2ecc71'}
riesgo_order = ['BAJO', 'MEDIO', 'ALTO']
riesgo_data = df_modelo['NIVEL_RIESGO_REINGRESO'].value_counts().reindex(riesgo_order).dropna()
colors = [colores_riesgo[r] for r in riesgo_data.index]

# Pie chart
axes[0].pie(riesgo_data, labels=riesgo_data.index, autopct='%1.1f%%', colors=colors, startangle=90)
axes[0].set_title('Distribución por Nivel de Riesgo', fontsize=12, fontweight='bold')

# Bar chart
bars = axes[1].bar(riesgo_data.index, riesgo_data.values, color=colors, edgecolor='black')
axes[1].set_xlabel('Nivel de Riesgo')
axes[1].set_ylabel('Cantidad de Pacientes')
axes[1].set_title('Cantidad de Pacientes por Nivel de Riesgo', fontsize=12, fontweight='bold')
for bar in bars:
    height = bar.get_height()
    axes[1].annotate(f'{int(height)}\n({height/len(df_modelo)*100:.1f}%)', 
                     xy=(bar.get_x() + bar.get_width()/2, height), ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig(f'{output_dir}07_distribucion_nivel_riesgo.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 07_distribucion_nivel_riesgo.png")

# --- GRÁFICO 8: Dashboard Resumen ---
print("   Generando: 08_dashboard_resumen_modelos.png")
fig = plt.figure(figsize=(20, 14))
fig.suptitle(f'DASHBOARD - COMPARACIÓN DE MODELOS PREDICTIVOS DE REINGRESO HOSPITALARIO\n(Total: {len(df_modelo)} registros | Tasa Reingreso Real: {tasa_reingreso:.1f}%)', 
             fontsize=14, fontweight='bold', y=0.98)

# Subplot 1: KPIs
ax1 = fig.add_subplot(2, 3, 1)
ax1.axis('off')
kpi_text = f"""
COMPARACIÓN DE MODELOS
---------------------------
Regresión Logística: AUC = {auc_lr:.3f}
Random Forest:       AUC = {auc_rf:.3f}
Gradient Boosting:   AUC = {auc_gb:.3f}

MEJOR MODELO: {mejor_nombre}
AUC-ROC: {mejor_auc:.3f}

DISTRIBUCIÓN DE RIESGO
---------------------------
Alto (>=70%): {len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='ALTO'])} ({len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='ALTO'])/len(df_modelo)*100:.1f}%)
Medio (40-70%): {len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='MEDIO'])} ({len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='MEDIO'])/len(df_modelo)*100:.1f}%)
Bajo (<40%): {len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='BAJO'])} ({len(df_modelo[df_modelo['NIVEL_RIESGO_REINGRESO']=='BAJO'])/len(df_modelo)*100:.1f}%)
"""
ax1.text(0.1, 0.5, kpi_text, fontsize=11, family='monospace', va='center', 
         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

# Subplot 2: Distribución de probabilidad
ax2 = fig.add_subplot(2, 3, 2)
ax2.hist(df_modelo['PROBABILIDAD_REINGRESO'], bins=30, edgecolor='black', alpha=0.7, color='#3498db')
ax2.axvline(0.4, color='orange', linestyle='--', linewidth=2, label='Umbral Medio (40%)')
ax2.axvline(0.7, color='red', linestyle='--', linewidth=2, label='Umbral Alto (70%)')
ax2.set_xlabel('Probabilidad')
ax2.set_ylabel('Frecuencia')
ax2.set_title('Distribución de Probabilidad de Reingreso')
ax2.legend(fontsize=8)

# Subplot 3: Nivel de riesgo (pie)
ax3 = fig.add_subplot(2, 3, 3)
riesgo_data = df_modelo['NIVEL_RIESGO_REINGRESO'].value_counts().reindex(['BAJO', 'MEDIO', 'ALTO']).dropna()
colors = [colores_riesgo[r] for r in riesgo_data.index]
ax3.pie(riesgo_data, labels=riesgo_data.index, autopct='%1.1f%%', colors=colors, startangle=90)
ax3.set_title('Distribución por Nivel de Riesgo')

# Subplot 4: Comparación de AUC
ax4 = fig.add_subplot(2, 3, 4)
modelos_nombres = ['Regresión\nLogística', 'Random\nForest', 'Gradient\nBoosting']
aucs_vals = [auc_lr, auc_rf, auc_gb]
colors_bars = ['#3498db', '#2ecc71', '#e67e22']
bars = ax4.bar(modelos_nombres, aucs_vals, color=colors_bars, edgecolor='black')
ax4.set_ylabel('AUC-ROC')
ax4.set_title('Comparación de AUC-ROC por Modelo')
ax4.set_ylim(0, 1)
for bar, val in zip(bars, aucs_vals):
    ax4.annotate(f'{val:.3f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10, fontweight='bold')

# Subplot 5: Curva ROC
ax5 = fig.add_subplot(2, 3, 5)
for nombre, data in resultados.items():
    fpr, tpr, _ = roc_curve(y_test, data['y_prob'])
    auc = data['metricas']['roc_auc']
    ax5.plot(fpr, tpr, label=f'{nombre[:3]} ({auc:.2f})', color=colors_roc[nombre], linewidth=2)
ax5.plot([0, 1], [0, 1], 'k--', linewidth=1)
ax5.set_xlabel('FPR')
ax5.set_ylabel('TPR')
ax5.set_title('Curvas ROC')
ax5.legend(loc='lower right', fontsize=9)
ax5.grid(True, alpha=0.3)

# Subplot 6: Comparación de métricas
ax6 = fig.add_subplot(2, 3, 6)
metricas_nombres = ['Accuracy', 'Precisión', 'Recall', 'F1']
metricas_lr_vals = [resultados['Regresión Logística']['metricas'][m] for m in ['accuracy', 'precision', 'recall', 'f1']]
metricas_rf_vals = [resultados['Random Forest']['metricas'][m] for m in ['accuracy', 'precision', 'recall', 'f1']]
metricas_gb_vals = [resultados['Gradient Boosting']['metricas'][m] for m in ['accuracy', 'precision', 'recall', 'f1']]

x = np.arange(len(metricas_nombres))
width = 0.25
ax6.bar(x - width, metricas_lr_vals, width, label='LR', color='#3498db', edgecolor='black')
ax6.bar(x, metricas_rf_vals, width, label='RF', color='#2ecc71', edgecolor='black')
ax6.bar(x + width, metricas_gb_vals, width, label='GB', color='#e67e22', edgecolor='black')
ax6.set_xticks(x)
ax6.set_xticklabels(metricas_nombres)
ax6.set_ylim(0, 1)
ax6.set_title('Comparación de Métricas')
ax6.legend(fontsize=9)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(f'{output_dir}08_dashboard_resumen_modelos.png', dpi=150, bbox_inches='tight')
plt.close()
print("      Guardado: 08_dashboard_resumen_modelos.png")

# ============================================
# 9. EXPORTAR RESULTADOS PARA POWER BI
# ============================================

print("\n" + "=" * 70)
print("EXPORTANDO RESULTADOS PARA POWER BI")
print("=" * 70)

# Seleccionar columnas para exportar (ahora incluye presión arterial procesada)
columnas_exportar = [
    'DOCUMENTO',
    'SEXO_TEXTO',
    'EDAD',
    'GRUPO_EDAD',
    'ASEGURADOR',
    'INGRESO_ACTUAL',
    'FECHA_INGRESO_ACTUAL',
    'FECHA_EGRESO_DEL_INGRESO_ACTUAL',
    'COD_DX_INGRESO',
    'NOM_DX_INGRESO',
    'COD_DX_EGRESO',
    'NOM_DX_EGRESO',
    'ESTADO_EGRESO_TEXTO',
    'PESO',
    'TALLA',
    'IMC',
    'CATEGORIA_IMC',
    'HOSPITALIZACIONES_ULTIMO_AÑO',
    'PRESION_ARTERIAL',
    'PRESION_SISTOLICA',
    'PRESION_DIASTOLICA',
    'PRESION_ARTERIAL_MEDIA',
    'DURACION_ESTANCIA_ACTUAL',
    'NUMERO_MEDICAMENTOS',
    'ADHERENCIA_TEXTO',
    'DIAS_DESDE_EGRESO_ANTERIOR',
    'REINGRESO',
    'PROBABILIDAD_REINGRESO',
    'PROB_REINGRESO_LR',
    'PROB_REINGRESO_RF',
    'PROB_REINGRESO_GB',
    'PROB_REINGRESO_ENSEMBLE',
    'NIVEL_RIESGO_REINGRESO'
]

# Crear dataframe de exportación
df_export = df_modelo[columnas_exportar].copy()

# Renombrar columnas para mayor claridad
df_export = df_export.rename(columns={
    'SEXO_TEXTO': 'SEXO',
    'ESTADO_EGRESO_TEXTO': 'ESTADO_EGRESO',
    'ADHERENCIA_TEXTO': 'ADHERENCIA_TRATAMIENTO',
    'PROBABILIDAD_REINGRESO': 'PROBABILIDAD_REINGRESO_MEJOR_MODELO',
    'PROB_REINGRESO_LR': 'PROBABILIDAD_REG_LOGISTICA',
    'PROB_REINGRESO_RF': 'PROBABILIDAD_RANDOM_FOREST',
    'PROB_REINGRESO_GB': 'PROBABILIDAD_GRADIENT_BOOSTING',
    'PROB_REINGRESO_ENSEMBLE': 'PROBABILIDAD_PROMEDIO_3_MODELOS'
})

# Agregar columna con el nombre del mejor modelo usado
df_export['MODELO_USADO'] = mejor_nombre

# Exportar a CSV
csv_path = f'{output_dir}PREDICCION_REINGRESOS_POWER_BI.csv'
df_export.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\n1. CSV principal exportado: {csv_path}")
print(f"   - Total registros: {len(df_export)}")

# Exportar métricas de los modelos
metricas_df.to_csv(f'{output_dir}METRICAS_COMPARACION_MODELOS.csv', index=False, encoding='utf-8-sig')
print(f"\n2. Métricas de modelos exportadas: METRICAS_COMPARACION_MODELOS.csv")

# Exportar importancia de variables
importancia_rf.to_csv(f'{output_dir}importancia_variables_rf.csv', index=False, encoding='utf-8-sig')
importancia_gb.to_csv(f'{output_dir}importancia_variables_gb.csv', index=False, encoding='utf-8-sig')
coef_df.to_csv(f'{output_dir}coeficientes_regresion_logistica.csv', index=False, encoding='utf-8-sig')
print(f"\n3. Importancia de variables exportada")

# ============================================
# 10. RESUMEN FINAL
# ============================================

print("\n" + "=" * 70)
print("RESUMEN FINAL - COMPARACIÓN DE MODELOS")
print("=" * 70)

print("\n" + "-" * 70)
print("TABLA COMPARATIVA DE MÉTRICAS")
print("-" * 70)
print(metricas_df.to_string(index=False))

print("\n" + "-" * 70)
print("MEJOR MODELO POR MÉTRICA")
print("-" * 70)
mejor_accuracy = metricas_df.loc[metricas_df['Accuracy (%)'].idxmax()]
mejor_f1 = metricas_df.loc[metricas_df['F1-Score (%)'].idxmax()]
mejor_auc_df = metricas_df.loc[metricas_df['ROC-AUC (%)'].idxmax()]

print(f"   - Mejor Accuracy:    {mejor_accuracy['Modelo']} ({mejor_accuracy['Accuracy (%)']:.2f}%)")
print(f"   - Mejor F1-Score:    {mejor_f1['Modelo']} ({mejor_f1['F1-Score (%)']:.2f}%)")
print(f"   - Mejor ROC-AUC:     {mejor_auc_df['Modelo']} ({mejor_auc_df['ROC-AUC (%)']:.2f}%)")

print("\n" + "-" * 70)
print("RECOMENDACIÓN FINAL")
print("-" * 70)
print(f"""
   El modelo recomendado es: **{mejor_nombre}**
   
   Métricas del modelo seleccionado:
   - Accuracy:        {resultados[mejor_nombre]['metricas']['accuracy']*100:.2f}%
   - Precisión:       {resultados[mejor_nombre]['metricas']['precision']*100:.2f}%
   - Recall:          {resultados[mejor_nombre]['metricas']['recall']*100:.2f}%
   - F1-Score:        {resultados[mejor_nombre]['metricas']['f1']*100:.2f}%
   - ROC-AUC:         {resultados[mejor_nombre]['metricas']['roc_auc']*100:.2f}%
""")

# ============================================
# 11. CERRAR CONEXIÓN
# ============================================

conn.close()
print("\nConexión a SQL Server cerrada")

print("\n" + "=" * 70)
print("MODELO PREDICTIVO DE REINGRESOS COMPLETADO")
print("=" * 70)
print(f"\nArchivos generados en: {output_dir}")
print("\nARCHIVOS CSV PARA POWER BI:")
print("   1. PREDICCION_REINGRESOS_POWER_BI.csv - Todos los registros con probabilidades de los 3 modelos")
print("   2. METRICAS_COMPARACION_MODELOS.csv - Comparación de métricas entre modelos")
print("   3. MATRIZ_CORRELACION_COMPLETA.csv")
print("   4. CORRELACION_CON_REINGRESO.csv")
print("   5. IMPORTANCIA_PESO_VARIABLES.csv - NUEVO: Peso de cada variable en cada modelo")
print("   6. importancia_variables_rf.csv")
print("   7. importancia_variables_gb.csv")
print("   8. coeficientes_regresion_logistica.csv")
print("\nGRÁFICOS (9 imágenes PNG):")
print("   00. Peso/Importancia de variables (comparación 3 modelos) - NUEVO")
print("   00. Matriz de correlación completa")
print("   01. Comparación de métricas entre modelos")
print("   02. Matrices de confusión")
print("   03. Curvas ROC")
print("   04. Curvas Precision-Recall")
print("   05. Importancia de variables")
print("   06. Distribución de probabilidades predichas")
print("   07. Distribución por nivel de riesgo")
print("   08. Dashboard resumen de modelos")
