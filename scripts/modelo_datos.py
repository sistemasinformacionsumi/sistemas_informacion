# ============================================
# MODELO DE DATOS - PREDICCION DE REINGRESOS HOSPITALARIOS
# Este modulo carga datos desde SQL Server y entrena los modelos
# Expone DataFrames en memoria para ser consumidos por la app Streamlit
# ============================================

import pandas as pd
import numpy as np
import pyodbc
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Scikit-learn imports
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import KNNImputer


class ModeloReingresos:
    """
    Clase principal que maneja la carga de datos y entrenamiento de modelos.
    Expone DataFrames en memoria sin necesidad de archivos CSV.
    """
    
    def __init__(self):
        self.df_predicciones = None
        self.df_importancia_variables = None
        self.df_metricas = None
        self.modelo_lr = None
        self.modelo_rf = None
        self.modelo_gb = None
        self.scaler = None
        self.features = None
        self.mejor_modelo = None
        self._datos_cargados = False
        
    def conectar_db(self):
        """Establece conexion con SQL Server"""
        try:
            conn = pyodbc.connect(
                "DRIVER={ODBC Driver 18 for SQL Server};"
                "SERVER=192.168.0.11\DINAMICA;"
                "DATABASE=DGEmpres01;"
                "UID=p_dinamica;"
                "PWD=Pruebas.Dinamica;"
                "TrustServerCertificate=yes;"
            )
            print(f"Conexión establecida con la base de datos{conn}")
            return conn
        except Exception as e:
            print(f"Error de conexión con la base de datos SQL Server: {e}")
            raise ConnectionError(f"Error de conexion a SQL Server: {e}")
    
    def cargar_datos_db(self):
        """Carga datos desde la base de datos"""
        conn = self.conectar_db()
        
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
        WHERE ar.TIPO_INGRESO = 'HOSPITALARIO'
        """
        df = pd.read_sql(query, conn)
        conn.close()
        print(f"Se cargaron los datos correctamente{df}")
        return df
    
    def preparar_datos(self, df):
        """Prepara y transforma los datos"""

        """Prepara y transforma los datos"""
        # Se combierte la presioón arterial que viene como formato texto a formato numerico Ej: 120/70 para que sea numerico
        # GSCA 28-04-2026
        df['PRESION_ARTERIAL'] = df['PRESION_ARTERIAL'].astype(str).str.split('/').str[0]
        df['PRESION_ARTERIAL'] = pd.to_numeric(df['PRESION_ARTERIAL'], errors='coerce')

        #   IMC se calcula solo para análisis, NO se usa en el modelo
        df['IMC'] = np.where(
            (df['PESO'].notna()) & (df['TALLA'].notna()) & (df['TALLA'] > 0),
            df['PESO'] / ((df['TALLA'] / 100) ** 2),
            np.nan
        )

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

        # Edad
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

        # Fechas
        df['FECHA_INGRESO_ACTUAL'] = pd.to_datetime(df['FECHA_INGRESO_ACTUAL'], errors='coerce')
        df['FECHA_EGRESO_DEL_INGRESO_ACTUAL'] = pd.to_datetime(df['FECHA_EGRESO_DEL_INGRESO_ACTUAL'], errors='coerce')

        df = df.sort_values(['DOCUMENTO', 'FECHA_INGRESO_ACTUAL']).reset_index(drop=True)

        df['DIAS_DESDE_EGRESO_ANTERIOR'] = df['TIEMPO_ULTIMA_HOSPITALIZACION']

        # Target
        df['ES_MISMA_CAUSA'] = (df['CAUSA_INGRESO'] == 2)
        df['TIEMPO_ULTIMA_HOSPITALIZACION'] = pd.to_numeric(df['TIEMPO_ULTIMA_HOSPITALIZACION'], errors='coerce')
        df['DENTRO_15_DIAS'] = df['TIEMPO_ULTIMA_HOSPITALIZACION'] <= 15
        df['REINGRESO'] = ((df['ES_MISMA_CAUSA']) & (df['DENTRO_15_DIAS'])).astype(int)

        # Mapas
        df['ADHERENCIA_TEXTO'] = df['ADHERENCIA_PREVIA'].map({0: 'Sin dato', 1: 'Con tratamiento', 2: 'Sin tratamiento'})
        df['SEXO_TEXTO'] = df['SEXO'].map({0: 'Sin dato', 1: 'Masculino', 2: 'Femenino'})
        df['ESTADO_EGRESO_TEXTO'] = df['ESTADO_EGRESO'].map({
            0: 'Sin dato', 1: 'Mejor', 2: 'Igual o Peor', 3: 'Muerto >48h', 4: 'Muerto <48h'
        })

        return df
        
    # Funcion que me permite entrenar los modelos de predicción de probabilidad de reingreso de un paciente a hospitalización
    # 28-04-2026 GSCA, se cambio este bloque de codigo de def entrenaar_modelos  para que no me tome el IMC y me tome la presión Artertial
    # ya que es un dato con un 96% de diligencimiento en la base  que pacientes hospitalizados que es 32.856 pacientes para esa condición
    def entrenar_modelos(self, df):
        """Entrena los modelos"""

        # 🔥 AJUSTE IA: Features limpias (sin IMC, con presión)
        self.features = [
            'SEXO', 'EDAD', 'HOSPITALIZACIONES_ULTIMO_AÑO',
            'DURACION_ESTANCIA_ACTUAL', 'NUMERO_MEDICAMENTOS',
            'ADHERENCIA_PREVIA', 'ESTADO_EGRESO',
            'PRESION_ARTERIAL'
        ]

        print("Variables usadas en el modelo:")
        print(self.features)

        df_modelo = df.copy()

        # GSCA 28-04-2026: PESO y TALLA no se usan en el modelo, pero se mantienen 
        # en el DataFrame para calculos de IMC (solo para análisis, no para predicción)

        # ============================================
        # 🔥 KNN IMPUTER CON ESCALADO
        # ============================================

        valores_faltantes_antes = df_modelo[self.features].isnull().sum()

        print("Faltantes por variable:")
        print(valores_faltantes_antes)

        # 🔥 AJUSTE IA: escalar antes de KNN
        scaler_knn = StandardScaler()
        df_scaled = scaler_knn.fit_transform(df_modelo[self.features])

        self.knn_imputer = KNNImputer(n_neighbors=5, weights='distance')
        df_imputado = self.knn_imputer.fit_transform(df_scaled)

        # 🔥 AJUSTE IA: volver a escala original
        df_modelo[self.features] = scaler_knn.inverse_transform(df_imputado)

        print("✅ Imputación KNN completada")

        X = df_modelo[self.features].copy()
        y = df_modelo['REINGRESO']

        # Balanceo
        total = len(y)
        positivos = y.sum()
        negativos = total - positivos

        class_weight = {
            0: total / (2 * negativos),
            1: total / (2 * positivos)
        }

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=0.3,
            random_state=42,
            stratify=y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
        )

        # Escalado para LR
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        X_all_scaled = self.scaler.transform(X)

        # Modelos
        self.modelo_lr = LogisticRegression(max_iter=1000, class_weight=class_weight)
        self.modelo_lr.fit(X_train_scaled, y_train)

        self.modelo_rf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight=class_weight)
        self.modelo_rf.fit(X_train, y_train)

        sample_weights = np.where(y_train == 1, class_weight[1], class_weight[0])

        self.modelo_gb = GradientBoostingClassifier(n_estimators=100, max_depth=5)
        self.modelo_gb.fit(X_train, y_train, sample_weight=sample_weights)

        # Evaluación
        auc_lr = roc_auc_score(y_test, self.modelo_lr.predict_proba(X_test_scaled)[:, 1])
        auc_rf = roc_auc_score(y_test, self.modelo_rf.predict_proba(X_test)[:, 1])
        auc_gb = roc_auc_score(y_test, self.modelo_gb.predict_proba(X_test)[:, 1])

        aucs = {
            'Regresion Logistica': auc_lr,
            'Random Forest': auc_rf,
            'Gradient Boosting': auc_gb
        }

        self.mejor_modelo = max(aucs, key=aucs.get)

        print("AUC:", aucs)
        print("Mejor modelo:", self.mejor_modelo)

        # Predicciones
        df_modelo['PROB_REINGRESO_LR'] = self.modelo_lr.predict_proba(X_all_scaled)[:, 1]
        df_modelo['PROB_REINGRESO_RF'] = self.modelo_rf.predict_proba(X)[:, 1]
        df_modelo['PROB_REINGRESO_GB'] = self.modelo_gb.predict_proba(X)[:, 1]

        if self.mejor_modelo == 'Regresion Logistica':
            df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_LR']
        elif self.mejor_modelo == 'Random Forest':
            df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_RF']
        else:
            df_modelo['PROBABILIDAD_REINGRESO'] = df_modelo['PROB_REINGRESO_GB']
            
        # Ensemble
        df_modelo['PROB_REINGRESO_ENSEMBLE'] = (
            df_modelo['PROB_REINGRESO_LR'] +
            df_modelo['PROB_REINGRESO_RF'] +
            df_modelo['PROB_REINGRESO_GB']
        ) / 3
        
        # Nivel de riesgo
        def categorizar_riesgo(prob):
            if prob >= 0.7:
                return 'ALTO'
            elif prob >= 0.4:
                return 'MEDIO'
            else:
                return 'BAJO'
        
        df_modelo['NIVEL_RIESGO_REINGRESO'] = df_modelo['PROBABILIDAD_REINGRESO'].apply(categorizar_riesgo)
        
        return df_modelo
    def calcular_importancia_variables(self):
        """Calcula la importancia de cada variable en los modelos"""
        
        importancias_df = pd.DataFrame({'Variable': self.features})
        
        # Regresion Logistica
        coef_lr = self.modelo_lr.coef_[0]
        importancias_df['Coef_RegLogistica'] = coef_lr
        importancias_df['Peso_RegLogistica_%'] = (np.abs(coef_lr) / np.abs(coef_lr).sum()) * 100
        
        # Random Forest
        imp_rf = self.modelo_rf.feature_importances_
        importancias_df['Importancia_RandomForest'] = imp_rf
        importancias_df['Peso_RandomForest_%'] = imp_rf * 100
        
        # Gradient Boosting
        imp_gb = self.modelo_gb.feature_importances_
        importancias_df['Importancia_GradientBoosting'] = imp_gb
        importancias_df['Peso_GradientBoosting_%'] = imp_gb * 100
        
        # Peso promedio
        importancias_df['Peso_Promedio_%'] = (
            importancias_df['Peso_RegLogistica_%'] + 
            importancias_df['Peso_RandomForest_%'] + 
            importancias_df['Peso_GradientBoosting_%']
        ) / 3
        
        return importancias_df.sort_values('Peso_Promedio_%', ascending=False)
    
    def cargar_y_entrenar(self):
        """Metodo principal: carga datos, prepara y entrena modelos"""
        if self._datos_cargados:
            return
        
        # Cargar datos
        df = self.cargar_datos_db()
        
        # Preparar datos
        df = self.preparar_datos(df)
        
        # Entrenar modelos
        df_modelo = self.entrenar_modelos(df)
        
        # Preparar DataFrame de predicciones (equivalente al CSV anterior)
        # GSCA 28-04-2026: Se omiten PESO y TALLA, se agrega PRESION_ARTERIAL
        columnas_exportar = [
            'DOCUMENTO', 'SEXO_TEXTO', 'EDAD', 'GRUPO_EDAD', 'ASEGURADOR',
            'INGRESO_ACTUAL', 'FECHA_INGRESO_ACTUAL', 'FECHA_EGRESO_DEL_INGRESO_ACTUAL',
            'COD_DX_INGRESO', 'NOM_DX_INGRESO', 'COD_DX_EGRESO', 'NOM_DX_EGRESO',
            'ESTADO_EGRESO_TEXTO', 'PRESION_ARTERIAL', 'IMC', 'CATEGORIA_IMC',
            'HOSPITALIZACIONES_ULTIMO_AÑO', 'DURACION_ESTANCIA_ACTUAL',
            'NUMERO_MEDICAMENTOS', 'ADHERENCIA_TEXTO', 'DIAS_DESDE_EGRESO_ANTERIOR',
            'REINGRESO', 'PROBABILIDAD_REINGRESO', 'PROB_REINGRESO_LR',
            'PROB_REINGRESO_RF', 'PROB_REINGRESO_GB', 'PROB_REINGRESO_ENSEMBLE',
            'NIVEL_RIESGO_REINGRESO', 'CAUSA_INGRESO'
        ]
        
        self.df_predicciones = df_modelo[columnas_exportar].copy()
        self.df_predicciones = self.df_predicciones.rename(columns={
            'SEXO_TEXTO': 'SEXO',
            'ESTADO_EGRESO_TEXTO': 'ESTADO_EGRESO',
            'ADHERENCIA_TEXTO': 'ADHERENCIA_TRATAMIENTO',
            'PROB_REINGRESO_LR': 'PROB_LR',
            'PROB_REINGRESO_RF': 'PROB_RF',
            'PROB_REINGRESO_GB': 'PROB_GB'
        })
        
        # Calcular importancia de variables
        self.df_importancia_variables = self.calcular_importancia_variables()
        
        self._datos_cargados = True
    
    def obtener_predicciones(self):
        """Retorna el DataFrame de predicciones"""
        if not self._datos_cargados:
            self.cargar_y_entrenar()
        return self.df_predicciones
    
    def obtener_importancia_variables(self):
        """Retorna el DataFrame de importancia de variables"""
        if not self._datos_cargados:
            self.cargar_y_entrenar()
        return self.df_importancia_variables
    
    def obtener_mejor_modelo(self):
        """Retorna el nombre del mejor modelo"""
        if not self._datos_cargados:
            self.cargar_y_entrenar()
        return self.mejor_modelo


# Instancia global del modelo (singleton)
_modelo_instance = None

def obtener_modelo():
    """Obtiene la instancia singleton del modelo"""
    global _modelo_instance
    if _modelo_instance is None:
        _modelo_instance = ModeloReingresos()
    return _modelo_instance

def cargar_datos():
    """Funcion de conveniencia para cargar datos"""
    modelo = obtener_modelo()
    modelo.cargar_y_entrenar()
    return modelo.obtener_predicciones()

def cargar_pesos_modelo():
    """Funcion de conveniencia para cargar pesos del modelo"""
    modelo = obtener_modelo()
    modelo.cargar_y_entrenar()
    return modelo.obtener_importancia_variables()
