"""
============================================================================
HERRAMIENTAS DE DETECCIÓN DE FRAUDE - AUDITORÍA FORENSE
Proyecto: Agente de Detección de Fraude en Transacciones
Framework: LangChain / LangGraph
============================================================================
Cada función es una herramienta (@tool) que el agente ReAct puede invocar
dinámicamente según la consulta del auditor.
============================================================================
"""

import pandas as pd
import numpy as np
from langchain_core.tools import tool
from typing import Optional
import json
from datetime import datetime

# Importar pipeline RAG
from rag_pipeline import buscar_normativa as _buscar_en_base, obtener_inventario

# ============================================================================
# VARIABLE GLOBAL - DataFrame de transacciones
# ============================================================================
_df_transacciones: pd.DataFrame = None
_df_proveedores: pd.DataFrame = None
_df_empleados: pd.DataFrame = None


def cargar_datos(path_transacciones: str, path_proveedores: str = None, path_empleados: str = None):
    """Carga los datasets en memoria para que las herramientas los utilicen."""
    global _df_transacciones, _df_proveedores, _df_empleados
    
    _df_transacciones = pd.read_csv(path_transacciones)
    _df_transacciones["fecha"] = pd.to_datetime(_df_transacciones["fecha"])
    _df_transacciones["hora_dt"] = pd.to_datetime(_df_transacciones["hora"], format="%H:%M:%S")
    _df_transacciones["hora_num"] = _df_transacciones["hora_dt"].dt.hour
    
    if path_proveedores:
        _df_proveedores = pd.read_csv(path_proveedores)
    if path_empleados:
        _df_empleados = pd.read_csv(path_empleados)
    
    return f"✅ Datos cargados exitosamente: {len(_df_transacciones):,} transacciones"


# ============================================================================
# HERRAMIENTA 1: RESUMEN GENERAL DEL DATASET
# ============================================================================
@tool
def resumen_general() -> str:
    """
    Genera un resumen ejecutivo del dataset de transacciones.
    Úsala cuando el auditor pida una visión general, un overview,
    o quiera conocer las cifras principales del periodo analizado.
    No requiere parámetros.
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos. Solicita al usuario cargar el archivo CSV primero."
    
    df = _df_transacciones
    
    resumen = {
        "periodo": f"{df['fecha'].min().strftime('%Y-%m-%d')} a {df['fecha'].max().strftime('%Y-%m-%d')}",
        "total_transacciones": int(len(df)),
        "transacciones_aprobadas": int(len(df[df["estado"] == "Aprobada"])),
        "transacciones_pendientes": int(len(df[df["estado"] == "Pendiente"])),
        "transacciones_rechazadas": int(len(df[df["estado"] == "Rechazada"])),
        "monto_total_transaccionado": f"S/. {df['monto_total'].sum():,.2f}",
        "monto_promedio": f"S/. {df['monto_total'].mean():,.2f}",
        "monto_mediana": f"S/. {df['monto_total'].median():,.2f}",
        "monto_maximo": f"S/. {df['monto_total'].max():,.2f}",
        "monto_minimo": f"S/. {df['monto_total'].min():,.2f}",
        "total_proveedores_unicos": int(df["proveedor_id"].nunique()),
        "total_empleados_autorizadores": int(df["autorizado_por_id"].nunique()),
        "categorias_de_gasto": int(df["categoria"].nunique()),
        "metodos_de_pago": df["metodo_pago"].value_counts().to_dict(),
        "distribucion_por_moneda": df["moneda"].value_counts().to_dict(),
        "top_5_proveedores_por_monto": df.groupby("proveedor_nombre")["monto_total"].sum().nlargest(5).to_dict(),
        "top_5_categorias_por_monto": df.groupby("categoria")["monto_total"].sum().nlargest(5).to_dict(),
        "top_5_departamentos_por_gasto": df.groupby("departamento")["monto_total"].sum().nlargest(5).to_dict(),
    }
    
    return json.dumps(resumen, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 2: DETECCIÓN DE TRANSACCIONES DUPLICADAS
# ============================================================================
@tool
def detectar_duplicados(criterio: str = "factura") -> str:
    """
    Detecta transacciones duplicadas sospechosas.
    Úsala cuando el auditor pregunte por pagos dobles, duplicados,
    facturas repetidas o pagos redundantes.
    
    Args:
        criterio: Tipo de búsqueda de duplicados.
                  'factura' = misma factura pagada más de una vez.
                  'monto_proveedor' = mismo monto al mismo proveedor en periodo corto.
                  'todos' = ejecuta ambos criterios.
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    resultados = []
    
    # Criterio 1: Misma factura duplicada
    if criterio in ["factura", "todos"]:
        facturas_dup = df[df.duplicated(subset=["numero_factura", "proveedor_id"], keep=False)]
        facturas_dup = facturas_dup.sort_values(["numero_factura", "fecha"])
        
        if len(facturas_dup) > 0:
            grupos = facturas_dup.groupby("numero_factura")
            for factura, grupo in grupos:
                if len(grupo) > 1:
                    monto_duplicado = grupo["monto_total"].sum() - grupo["monto_total"].iloc[0]
                    resultados.append({
                        "tipo_alerta": "FACTURA DUPLICADA",
                        "severidad": "ALTA",
                        "factura": factura,
                        "proveedor": grupo["proveedor_nombre"].iloc[0],
                        "cantidad_pagos": int(len(grupo)),
                        "monto_por_pago": f"S/. {grupo['monto_total'].iloc[0]:,.2f}",
                        "monto_duplicado_estimado": f"S/. {monto_duplicado:,.2f}",
                        "fechas": grupo["fecha"].dt.strftime("%Y-%m-%d").tolist(),
                        "autorizadores": grupo["autorizado_por"].tolist(),
                        "transacciones_ids": grupo["transaction_id"].tolist(),
                    })
    
    # Criterio 2: Mismo monto y proveedor en ventana de 7 días
    if criterio in ["monto_proveedor", "todos"]:
        df_sorted = df.sort_values(["proveedor_id", "fecha"])
        for prov_id, grupo in df_sorted.groupby("proveedor_id"):
            if len(grupo) < 2:
                continue
            for i in range(len(grupo)):
                for j in range(i + 1, min(i + 5, len(grupo))):
                    row_i = grupo.iloc[i]
                    row_j = grupo.iloc[j]
                    diff_dias = (row_j["fecha"] - row_i["fecha"]).days
                    if diff_dias <= 7 and abs(row_i["monto_total"] - row_j["monto_total"]) < 0.01:
                        if row_i["numero_factura"] != row_j["numero_factura"]:
                            resultados.append({
                                "tipo_alerta": "MISMO MONTO Y PROVEEDOR EN 7 DÍAS",
                                "severidad": "MEDIA",
                                "proveedor": row_i["proveedor_nombre"],
                                "monto": f"S/. {row_i['monto_total']:,.2f}",
                                "fecha_1": row_i["fecha"].strftime("%Y-%m-%d"),
                                "fecha_2": row_j["fecha"].strftime("%Y-%m-%d"),
                                "facturas": [row_i["numero_factura"], row_j["numero_factura"]],
                                "transacciones_ids": [row_i["transaction_id"], row_j["transaction_id"]],
                            })
    
    # Limitar resultados para no saturar al LLM
    total_alertas = len(resultados)
    resultados_limitados = resultados[:30]
    
    resumen = {
        "total_alertas_duplicados": total_alertas,
        "mostrando": min(30, total_alertas),
        "monto_total_en_riesgo": f"S/. {sum(float(r.get('monto_duplicado_estimado', '0').replace('S/. ', '').replace(',', '')) for r in resultados if 'monto_duplicado_estimado' in r):,.2f}",
        "alertas": resultados_limitados
    }
    
    return json.dumps(resumen, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 3: DETECCIÓN DE TRANSACCIONES FUERA DE HORARIO
# ============================================================================
@tool
def detectar_fuera_de_horario(hora_inicio: int = 8, hora_fin: int = 18, incluir_fines_semana: bool = True) -> str:
    """
    Detecta transacciones realizadas fuera del horario laboral normal.
    Úsala cuando el auditor pregunte por transacciones en madrugada,
    fines de semana, horarios inusuales o actividad sospechosa por horario.
    
    Args:
        hora_inicio: Hora de inicio del horario laboral (default: 8).
        hora_fin: Hora de fin del horario laboral (default: 18).
        incluir_fines_semana: Si True, también marca fines de semana como sospechosos.
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    # Filtrar fuera de horario
    mask_horario = (df["hora_num"] < hora_inicio) | (df["hora_num"] >= hora_fin)
    
    if incluir_fines_semana:
        mask_fds = df["dia_semana"].isin(["Sábado", "Domingo"])
        mask_total = mask_horario | mask_fds
    else:
        mask_total = mask_horario
    
    sospechosas = df[mask_total].copy()
    
    # Análisis por empleado
    analisis_empleado = sospechosas.groupby("autorizado_por").agg(
        cantidad=("transaction_id", "count"),
        monto_total=("monto_total", "sum"),
        horario_mas_frecuente=("hora_num", lambda x: f"{x.mode().iloc[0]}:00" if len(x.mode()) > 0 else "N/A"),
    ).sort_values("cantidad", ascending=False).head(10)
    
    # Detalle de las más sospechosas (madrugada)
    madrugada = sospechosas[sospechosas["hora_num"].between(0, 5)]
    
    resultado = {
        "total_transacciones_fuera_horario": int(len(sospechosas)),
        "porcentaje_del_total": f"{len(sospechosas)/len(df)*100:.2f}%",
        "monto_total_involucrado": f"S/. {sospechosas['monto_total'].sum():,.2f}",
        "transacciones_en_madrugada_00_05": int(len(madrugada)),
        "transacciones_fines_semana": int(len(sospechosas[sospechosas['dia_semana'].isin(['Sábado', 'Domingo'])])),
        "top_10_empleados_con_mas_actividad_fuera_horario": [
            {
                "empleado": emp,
                "cantidad": int(row["cantidad"]),
                "monto_total": f"S/. {row['monto_total']:,.2f}",
                "horario_frecuente": row["horario_mas_frecuente"]
            }
            for emp, row in analisis_empleado.iterrows()
        ],
        "detalle_transacciones_madrugada": [
            {
                "id": row["transaction_id"],
                "fecha": row["fecha"].strftime("%Y-%m-%d"),
                "hora": row["hora"],
                "monto": f"S/. {row['monto_total']:,.2f}",
                "proveedor": row["proveedor_nombre"],
                "autorizado_por": row["autorizado_por"],
                "categoria": row["categoria"],
            }
            for _, row in madrugada.head(20).iterrows()
        ]
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 4: ANÁLISIS DE PROVEEDORES SOSPECHOSOS
# ============================================================================
@tool
def analizar_proveedores(nombre_proveedor: Optional[str] = None, top_n: int = 10) -> str:
    """
    Analiza proveedores buscando patrones sospechosos como proveedores
    con pocas transacciones pero montos altos, proveedores nuevos con
    actividad inusual, concentración excesiva de pagos, o proveedores
    sin patrón regular de facturación.
    Úsala cuando el auditor pregunte por proveedores fantasma, sospechosos,
    concentración de pagos, o quiera investigar un proveedor específico.
    
    Args:
        nombre_proveedor: Nombre parcial del proveedor a investigar (opcional).
                          Si se omite, analiza todos los proveedores.
        top_n: Cantidad de proveedores sospechosos a mostrar (default: 10).
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    # Si se busca un proveedor específico
    if nombre_proveedor:
        df_filtrado = df[df["proveedor_nombre"].str.contains(nombre_proveedor, case=False, na=False)]
        if len(df_filtrado) == 0:
            return f"⚠️ No se encontró ningún proveedor con el nombre '{nombre_proveedor}'. Verifica el nombre e intenta de nuevo."
        
        prov = df_filtrado.iloc[0]
        detalle = df_filtrado.sort_values("fecha")
        
        resultado_especifico = {
            "proveedor": prov["proveedor_nombre"],
            "id": prov["proveedor_id"],
            "ruc": prov["proveedor_ruc"],
            "total_transacciones": int(len(detalle)),
            "monto_total": f"S/. {detalle['monto_total'].sum():,.2f}",
            "monto_promedio": f"S/. {detalle['monto_total'].mean():,.2f}",
            "monto_maximo": f"S/. {detalle['monto_total'].max():,.2f}",
            "primera_transaccion": detalle["fecha"].min().strftime("%Y-%m-%d"),
            "ultima_transaccion": detalle["fecha"].max().strftime("%Y-%m-%d"),
            "categorias_usadas": detalle["categoria"].unique().tolist(),
            "metodos_pago": detalle["metodo_pago"].value_counts().to_dict(),
            "autorizadores": detalle["autorizado_por"].value_counts().to_dict(),
            "departamentos": detalle["departamento"].value_counts().to_dict(),
            "alertas": [],
            "ultimas_10_transacciones": [
                {
                    "id": row["transaction_id"],
                    "fecha": row["fecha"].strftime("%Y-%m-%d"),
                    "monto": f"S/. {row['monto_total']:,.2f}",
                    "descripcion": row["descripcion"],
                    "autorizado_por": row["autorizado_por"],
                }
                for _, row in detalle.tail(10).iterrows()
            ]
        }
        
        # Generar alertas específicas
        if detalle["autorizado_por"].nunique() == 1:
            resultado_especifico["alertas"].append("⚠️ ALERTA: Todas las transacciones autorizadas por la misma persona")
        if detalle["monto_total"].std() < detalle["monto_total"].mean() * 0.1:
            resultado_especifico["alertas"].append("⚠️ ALERTA: Montos sospechosamente uniformes")
        if len(detalle) > 5 and detalle["categoria"].nunique() > 3:
            resultado_especifico["alertas"].append("⚠️ ALERTA: Proveedor opera en múltiples categorías no relacionadas")
        
        return json.dumps(resultado_especifico, ensure_ascii=False, indent=2, default=str)
    
    # Análisis general de proveedores
    analisis = df.groupby(["proveedor_id", "proveedor_nombre", "proveedor_ruc"]).agg(
        total_transacciones=("transaction_id", "count"),
        monto_total=("monto_total", "sum"),
        monto_promedio=("monto_total", "mean"),
        monto_max=("monto_total", "max"),
        primera_fecha=("fecha", "min"),
        ultima_fecha=("fecha", "max"),
        num_autorizadores=("autorizado_por_id", "nunique"),
        num_categorias=("categoria", "nunique"),
    ).reset_index()
    
    # Scoring de sospecha
    analisis["score_sospecha"] = 0
    
    # Proveedor con un solo autorizador y muchas transacciones
    analisis.loc[(analisis["num_autorizadores"] == 1) & (analisis["total_transacciones"] > 3), "score_sospecha"] += 30
    
    # Monto promedio alto con pocas transacciones
    monto_p75 = analisis["monto_promedio"].quantile(0.75)
    analisis.loc[(analisis["monto_promedio"] > monto_p75) & (analisis["total_transacciones"] < 5), "score_sospecha"] += 25
    
    # Proveedor en múltiples categorías
    analisis.loc[analisis["num_categorias"] > 3, "score_sospecha"] += 20
    
    # Concentración alta de monto
    monto_total_empresa = df["monto_total"].sum()
    analisis["pct_monto"] = analisis["monto_total"] / monto_total_empresa * 100
    analisis.loc[analisis["pct_monto"] > 5, "score_sospecha"] += 15
    
    # RUC que empieza con 206 (patrón de fantasmas en nuestro dataset)
    analisis.loc[analisis["proveedor_ruc"].astype(str).str.startswith("206"), "score_sospecha"] += 25
    
    # Top sospechosos
    top_sospechosos = analisis.nlargest(top_n, "score_sospecha")
    
    resultado = {
        "total_proveedores_analizados": int(len(analisis)),
        "proveedores_con_alerta": int(len(analisis[analisis["score_sospecha"] > 30])),
        "top_proveedores_sospechosos": [
            {
                "proveedor": row["proveedor_nombre"],
                "id": row["proveedor_id"],
                "ruc": row["proveedor_ruc"],
                "score_sospecha": int(row["score_sospecha"]),
                "total_transacciones": int(row["total_transacciones"]),
                "monto_total": f"S/. {row['monto_total']:,.2f}",
                "num_autorizadores": int(row["num_autorizadores"]),
                "num_categorias": int(row["num_categorias"]),
                "pct_del_gasto_total": f"{row['pct_monto']:.2f}%",
            }
            for _, row in top_sospechosos.iterrows()
        ]
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 5: DETECCIÓN DE FRACCIONAMIENTO DE COMPRAS
# ============================================================================
@tool
def detectar_fraccionamiento(umbral_monto: float = 10000, ventana_dias: int = 5, min_transacciones: int = 3) -> str:
    """
    Detecta posible fraccionamiento de compras (structuring/smurfing).
    Busca múltiples transacciones pequeñas al mismo proveedor en un periodo
    corto que sumadas superan el umbral de aprobación.
    Úsala cuando el auditor pregunte por fraccionamiento, splitting,
    compras divididas, o evasión de límites de aprobación.
    
    Args:
        umbral_monto: Monto umbral de aprobación a verificar (default: 10000).
        ventana_dias: Ventana de días para agrupar transacciones (default: 5).
        min_transacciones: Mínimo de transacciones para considerar fraccionamiento (default: 3).
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    df_bajo_umbral = df[df["monto_total"] < umbral_monto].sort_values(["proveedor_id", "autorizado_por_id", "fecha"])
    
    alertas = []
    
    for (prov_id, emp_id), grupo in df_bajo_umbral.groupby(["proveedor_id", "autorizado_por_id"]):
        if len(grupo) < min_transacciones:
            continue
        
        grupo = grupo.sort_values("fecha").reset_index(drop=True)
        
        for i in range(len(grupo)):
            ventana = grupo[
                (grupo["fecha"] >= grupo.iloc[i]["fecha"]) & 
                (grupo["fecha"] <= grupo.iloc[i]["fecha"] + pd.Timedelta(days=ventana_dias))
            ]
            
            if len(ventana) >= min_transacciones:
                monto_acumulado = ventana["monto_total"].sum()
                if monto_acumulado > umbral_monto:
                    alerta_key = f"{prov_id}_{emp_id}_{ventana.iloc[0]['fecha'].strftime('%Y%m%d')}"
                    if not any(a.get("_key") == alerta_key for a in alertas):
                        alertas.append({
                            "_key": alerta_key,
                            "tipo_alerta": "FRACCIONAMIENTO DE COMPRAS",
                            "severidad": "ALTA",
                            "proveedor": ventana.iloc[0]["proveedor_nombre"],
                            "autorizado_por": ventana.iloc[0]["autorizado_por"],
                            "cargo": ventana.iloc[0]["cargo_autorizador"],
                            "nivel_aprobacion_empleado": f"S/. {ventana.iloc[0]['nivel_aprobacion']:,.2f}",
                            "periodo": f"{ventana.iloc[0]['fecha'].strftime('%Y-%m-%d')} a {ventana.iloc[-1]['fecha'].strftime('%Y-%m-%d')}",
                            "num_transacciones": int(len(ventana)),
                            "monto_individual_promedio": f"S/. {ventana['monto_total'].mean():,.2f}",
                            "monto_acumulado": f"S/. {monto_acumulado:,.2f}",
                            "supera_umbral_en": f"S/. {monto_acumulado - umbral_monto:,.2f}",
                            "transacciones": [
                                {"id": row["transaction_id"], "fecha": row["fecha"].strftime("%Y-%m-%d"), "monto": f"S/. {row['monto_total']:,.2f}"}
                                for _, row in ventana.iterrows()
                            ]
                        })
    
    # Limpiar key interno
    for a in alertas:
        a.pop("_key", None)
    
    resultado = {
        "parametros_busqueda": {
            "umbral_monto": f"S/. {umbral_monto:,.2f}",
            "ventana_dias": ventana_dias,
            "min_transacciones": min_transacciones,
        },
        "total_alertas_fraccionamiento": len(alertas),
        "monto_total_en_riesgo": f"S/. {sum(float(a['monto_acumulado'].replace('S/. ', '').replace(',', '')) for a in alertas):,.2f}",
        "alertas": alertas[:20]
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 6: ANÁLISIS DE MONTOS ATÍPICOS (OUTLIERS)
# ============================================================================
@tool
def detectar_montos_atipicos(metodo: str = "iqr", categoria: Optional[str] = None) -> str:
    """
    Detecta transacciones con montos atípicos (outliers) que se desvían
    significativamente del patrón normal.
    Úsala cuando el auditor pregunte por montos inusuales, outliers,
    transacciones anormales, sobrefacturación o montos sospechosos.
    
    Args:
        metodo: 'iqr' para rango intercuartílico o 'zscore' para desviación estándar.
        categoria: Categoría específica a analizar (opcional, analiza todas si se omite).
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    if categoria:
        df_filtrado = df[df["categoria"].str.contains(categoria, case=False, na=False)]
        if len(df_filtrado) == 0:
            categorias_disponibles = df["categoria"].unique().tolist()
            return f"⚠️ Categoría '{categoria}' no encontrada. Categorías disponibles: {categorias_disponibles}"
        df = df_filtrado
    
    outliers_todos = []
    
    # Analizar por categoría
    for cat, grupo in df.groupby("categoria"):
        if len(grupo) < 5:
            continue
        
        montos = grupo["monto_total"].abs()
        
        if metodo == "iqr":
            Q1 = montos.quantile(0.25)
            Q3 = montos.quantile(0.75)
            IQR = Q3 - Q1
            limite_superior = Q3 + 2.5 * IQR
            limite_inferior = Q1 - 2.5 * IQR
            outliers = grupo[(montos > limite_superior) | (montos < limite_inferior)]
        else:  # zscore
            mean = montos.mean()
            std = montos.std()
            if std == 0:
                continue
            z_scores = (montos - mean) / std
            outliers = grupo[z_scores.abs() > 2.5]
        
        for _, row in outliers.iterrows():
            outliers_todos.append({
                "id": row["transaction_id"],
                "fecha": row["fecha"].strftime("%Y-%m-%d"),
                "categoria": cat,
                "proveedor": row["proveedor_nombre"],
                "descripcion": row["descripcion"],
                "monto": f"S/. {row['monto_total']:,.2f}",
                "monto_promedio_categoria": f"S/. {montos.mean():,.2f}",
                "desviacion_vs_promedio": f"{((abs(row['monto_total']) / montos.mean()) - 1) * 100:.1f}%",
                "autorizado_por": row["autorizado_por"],
                "metodo_pago": row["metodo_pago"],
            })
    
    outliers_todos.sort(key=lambda x: float(x["desviacion_vs_promedio"].replace("%", "")), reverse=True)
    
    resultado = {
        "metodo_utilizado": metodo.upper(),
        "categoria_filtrada": categoria or "Todas",
        "total_outliers_detectados": len(outliers_todos),
        "monto_total_outliers": f"S/. {sum(float(o['monto'].replace('S/. ', '').replace(',', '')) for o in outliers_todos):,.2f}",
        "outliers_mas_significativos": outliers_todos[:25]
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 7: ANÁLISIS DE AUTORIZADORES
# ============================================================================
@tool
def analizar_autorizadores(nombre_empleado: Optional[str] = None) -> str:
    """
    Analiza patrones de autorización de empleados para detectar
    conflictos de interés, auto-aprobaciones, concentración de poder
    o autorizaciones que exceden el nivel permitido.
    Úsala cuando el auditor pregunte por segregación de funciones,
    conflicto de interés, auto-aprobación, o quiera investigar
    un empleado específico.
    
    Args:
        nombre_empleado: Nombre del empleado a investigar (opcional).
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    if nombre_empleado:
        df_emp = df[df["autorizado_por"].str.contains(nombre_empleado, case=False, na=False)]
        if len(df_emp) == 0:
            empleados_disponibles = df["autorizado_por"].unique().tolist()
            return f"⚠️ Empleado '{nombre_empleado}' no encontrado. Empleados disponibles: {empleados_disponibles}"
        
        emp = df_emp.iloc[0]
        
        # Análisis temporal
        txn_por_mes = df_emp.groupby(df_emp["fecha"].dt.month).agg(
            cantidad=("transaction_id", "count"),
            monto=("monto_total", "sum")
        ).to_dict("index")
        
        # Transacciones sin OC
        sin_oc = df_emp[df_emp["numero_oc"].isna() | (df_emp["numero_oc"] == "")]
        
        # Transacciones cerca del límite
        nivel = emp["nivel_aprobacion"]
        cerca_limite = df_emp[df_emp["monto_total"].between(nivel * 0.85, nivel * 1.0)]
        
        resultado_emp = {
            "empleado": emp["autorizado_por"],
            "cargo": emp["cargo_autorizador"],
            "departamento": emp["departamento"],
            "nivel_aprobacion": f"S/. {nivel:,.2f}",
            "total_transacciones_autorizadas": int(len(df_emp)),
            "monto_total_autorizado": f"S/. {df_emp['monto_total'].sum():,.2f}",
            "monto_promedio": f"S/. {df_emp['monto_total'].mean():,.2f}",
            "proveedores_frecuentes": df_emp["proveedor_nombre"].value_counts().head(5).to_dict(),
            "transacciones_sin_orden_compra": int(len(sin_oc)),
            "transacciones_cerca_del_limite_aprobacion": int(len(cerca_limite)),
            "transacciones_fuera_horario": int(len(df_emp[(df_emp["hora_num"] < 8) | (df_emp["hora_num"] >= 18)])),
            "transacciones_fin_semana": int(len(df_emp[df_emp["dia_semana"].isin(["Sábado", "Domingo"])])),
            "alertas": [],
        }
        
        # Generar alertas
        if len(sin_oc) > len(df_emp) * 0.3:
            resultado_emp["alertas"].append(f"⚠️ {len(sin_oc)} transacciones sin orden de compra ({len(sin_oc)/len(df_emp)*100:.0f}%)")
        if len(cerca_limite) > 5:
            resultado_emp["alertas"].append(f"🔴 {len(cerca_limite)} transacciones cercanas al límite de aprobación")
        if df_emp["proveedor_id"].nunique() < 5 and len(df_emp) > 20:
            resultado_emp["alertas"].append("⚠️ Concentración sospechosa: muchas transacciones a pocos proveedores")
        
        return json.dumps(resultado_emp, ensure_ascii=False, indent=2, default=str)
    
    # Análisis general de autorizadores
    analisis = df.groupby(["autorizado_por_id", "autorizado_por", "cargo_autorizador", "nivel_aprobacion"]).agg(
        total_txn=("transaction_id", "count"),
        monto_total=("monto_total", "sum"),
        proveedores_unicos=("proveedor_id", "nunique"),
        txn_sin_oc=("numero_oc", lambda x: (x.isna() | (x == "")).sum()),
        txn_fds=("dia_semana", lambda x: x.isin(["Sábado", "Domingo"]).sum()),
    ).reset_index()
    
    # Score de riesgo por empleado
    analisis["score_riesgo"] = 0
    analisis.loc[analisis["txn_sin_oc"] > 10, "score_riesgo"] += 25
    analisis.loc[analisis["txn_fds"] > 5, "score_riesgo"] += 20
    analisis.loc[analisis["proveedores_unicos"] < 3, "score_riesgo"] += 20
    mediana_monto = analisis["monto_total"].median()
    analisis.loc[analisis["monto_total"] > mediana_monto * 2, "score_riesgo"] += 15
    
    top_riesgo = analisis.nlargest(10, "score_riesgo")
    
    resultado = {
        "total_autorizadores_analizados": int(len(analisis)),
        "autorizadores_con_alerta": int(len(analisis[analisis["score_riesgo"] > 30])),
        "ranking_por_riesgo": [
            {
                "empleado": row["autorizado_por"],
                "cargo": row["cargo_autorizador"],
                "score_riesgo": int(row["score_riesgo"]),
                "total_transacciones": int(row["total_txn"]),
                "monto_total": f"S/. {row['monto_total']:,.2f}",
                "proveedores_unicos": int(row["proveedores_unicos"]),
                "sin_orden_compra": int(row["txn_sin_oc"]),
                "fin_de_semana": int(row["txn_fds"]),
            }
            for _, row in top_riesgo.iterrows()
        ]
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 8: ANÁLISIS DE BENFORD (LEY DEL PRIMER DÍGITO)
# ============================================================================
@tool
def analisis_benford(campo: str = "monto_total") -> str:
    """
    Aplica la Ley de Benford para detectar posible manipulación de cifras.
    La Ley de Benford dice que en datos financieros naturales, el dígito 1
    aparece como primer dígito ~30% de las veces. Desviaciones significativas
    pueden indicar fraude o manipulación.
    Úsala cuando el auditor pregunte por análisis de Benford, manipulación
    de cifras, distribución de dígitos o análisis estadístico forense.
    
    Args:
        campo: Campo numérico a analizar ('monto_total', 'monto_base', 'igv').
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    # Distribución esperada de Benford
    benford_esperado = {
        1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7,
        5: 7.9, 6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6
    }
    
    # Extraer primer dígito
    montos = df[campo].abs()
    montos = montos[montos > 0]
    primer_digito = montos.apply(lambda x: int(str(x).replace(".", "").replace("-", "").lstrip("0")[0]) if x != 0 else 0)
    primer_digito = primer_digito[primer_digito > 0]
    
    # Distribución observada
    conteo = primer_digito.value_counts().sort_index()
    total = len(primer_digito)
    
    comparacion = []
    desviacion_total = 0
    digitos_sospechosos = []
    
    for digito in range(1, 10):
        observado_pct = (conteo.get(digito, 0) / total) * 100
        esperado_pct = benford_esperado[digito]
        desviacion = observado_pct - esperado_pct
        desviacion_total += abs(desviacion)
        
        estado = "✅ Normal"
        if abs(desviacion) > 3:
            estado = "⚠️ Desviación moderada"
        if abs(desviacion) > 5:
            estado = "🔴 Desviación significativa"
            digitos_sospechosos.append(digito)
        
        comparacion.append({
            "digito": digito,
            "esperado_benford": f"{esperado_pct:.1f}%",
            "observado": f"{observado_pct:.1f}%",
            "desviacion": f"{desviacion:+.1f}%",
            "estado": estado
        })
    
    # Evaluación general
    if desviacion_total < 10:
        evaluacion = "✅ La distribución es consistente con la Ley de Benford. No hay indicios de manipulación generalizada."
    elif desviacion_total < 20:
        evaluacion = "⚠️ Se detectan desviaciones moderadas. Se recomienda investigar los dígitos señalados."
    else:
        evaluacion = "🔴 Desviaciones significativas detectadas. Alta probabilidad de manipulación de cifras."
    
    resultado = {
        "campo_analizado": campo,
        "total_registros_analizados": int(total),
        "evaluacion_general": evaluacion,
        "desviacion_total_acumulada": f"{desviacion_total:.1f}%",
        "digitos_con_desviacion_significativa": digitos_sospechosos,
        "comparacion_benford": comparacion,
    }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 9: ANÁLISIS DE NOTAS DE CRÉDITO
# ============================================================================
@tool
def analizar_notas_credito() -> str:
    """
    Analiza las notas de crédito buscando patrones sospechosos como
    notas sin documentación, montos inusuales o concentración en
    determinados proveedores o empleados.
    Úsala cuando el auditor pregunte por notas de crédito, devoluciones,
    ajustes, o anulaciones sospechosas.
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    # Identificar notas de crédito (montos negativos o método = Nota de Crédito)
    nc = df[(df["monto_total"] < 0) | (df["metodo_pago"] == "Nota de Crédito") | 
            (df["numero_factura"].astype(str).str.startswith("NC", na=False))]
    
    if len(nc) == 0:
        return json.dumps({"mensaje": "No se encontraron notas de crédito en el dataset."})
    
    # Análisis por proveedor
    nc_por_proveedor = nc.groupby("proveedor_nombre").agg(
        cantidad=("transaction_id", "count"),
        monto_total=("monto_total", "sum"),
    ).sort_values("monto_total")
    
    # NC sin orden de compra
    nc_sin_oc = nc[nc["numero_oc"].isna() | (nc["numero_oc"] == "")]
    
    resultado = {
        "total_notas_credito": int(len(nc)),
        "monto_total_notas_credito": f"S/. {nc['monto_total'].sum():,.2f}",
        "porcentaje_del_total_transacciones": f"{len(nc)/len(df)*100:.2f}%",
        "notas_sin_orden_compra": int(len(nc_sin_oc)),
        "por_proveedor": [
            {"proveedor": prov, "cantidad": int(row["cantidad"]), "monto": f"S/. {row['monto_total']:,.2f}"}
            for prov, row in nc_por_proveedor.head(10).iterrows()
        ],
        "por_autorizador": nc["autorizado_por"].value_counts().head(5).to_dict(),
        "detalle_notas_credito": [
            {
                "id": row["transaction_id"],
                "fecha": row["fecha"].strftime("%Y-%m-%d"),
                "proveedor": row["proveedor_nombre"],
                "monto": f"S/. {row['monto_total']:,.2f}",
                "descripcion": row["descripcion"],
                "autorizado_por": row["autorizado_por"],
                "tiene_oc": "Sí" if row["numero_oc"] and row["numero_oc"] != "" else "No",
            }
            for _, row in nc.head(20).iterrows()
        ],
        "alertas": []
    }
    
    if len(nc_sin_oc) > len(nc) * 0.5:
        resultado["alertas"].append(f"🔴 {len(nc_sin_oc)} notas de crédito sin orden de compra ({len(nc_sin_oc)/len(nc)*100:.0f}%)")
    if nc["autorizado_por"].nunique() < 3:
        resultado["alertas"].append("⚠️ Notas de crédito concentradas en pocos autorizadores")
    
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 10: GENERACIÓN DE REPORTE DE HALLAZGOS
# ============================================================================
@tool
def generar_reporte_ejecutivo() -> str:
    """
    Genera un reporte ejecutivo consolidado con todos los hallazgos
    de auditoría forense del análisis realizado.
    Úsala cuando el auditor pida un reporte, resumen de hallazgos,
    informe ejecutivo, o quiera consolidar los resultados del análisis.
    """
    if _df_transacciones is None:
        return "❌ Error: No se han cargado datos."
    
    df = _df_transacciones.copy()
    
    # Ejecutar análisis rápidos
    # 1. Duplicados
    facturas_dup = df[df.duplicated(subset=["numero_factura", "proveedor_id"], keep=False)]
    n_dup = len(facturas_dup) // 2
    
    # 2. Fuera de horario
    fuera_horario = df[(df["hora_num"] < 8) | (df["hora_num"] >= 18) | df["dia_semana"].isin(["Sábado", "Domingo"])]
    
    # 3. Sin OC
    sin_oc = df[df["numero_oc"].isna() | (df["numero_oc"] == "")]
    
    # 4. Notas de crédito
    nc = df[(df["monto_total"] < 0) | (df["metodo_pago"] == "Nota de Crédito")]
    
    # 5. Concentración de proveedores
    top_prov = df.groupby("proveedor_nombre")["monto_total"].sum().nlargest(5)
    concentracion = top_prov.sum() / df["monto_total"].sum() * 100
    
    reporte = {
        "titulo": "REPORTE EJECUTIVO DE AUDITORÍA FORENSE",
        "periodo_analizado": f"{df['fecha'].min().strftime('%Y-%m-%d')} a {df['fecha'].max().strftime('%Y-%m-%d')}",
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alcance": f"{len(df):,} transacciones por S/. {df['monto_total'].sum():,.2f}",
        "resumen_hallazgos": {
            "facturas_duplicadas": {
                "cantidad": int(n_dup),
                "monto_estimado": f"S/. {facturas_dup['monto_total'].sum()/2:,.2f}",
                "severidad": "ALTA"
            },
            "transacciones_fuera_horario": {
                "cantidad": int(len(fuera_horario)),
                "monto_involucrado": f"S/. {fuera_horario['monto_total'].sum():,.2f}",
                "severidad": "MEDIA-ALTA"
            },
            "transacciones_sin_orden_compra": {
                "cantidad": int(len(sin_oc)),
                "porcentaje": f"{len(sin_oc)/len(df)*100:.1f}%",
                "severidad": "MEDIA"
            },
            "notas_credito_sospechosas": {
                "cantidad": int(len(nc)),
                "monto": f"S/. {nc['monto_total'].sum():,.2f}",
                "severidad": "ALTA"
            },
            "concentracion_proveedores": {
                "top_5_representan": f"{concentracion:.1f}% del gasto total",
                "severidad": "MEDIA"
            }
        },
        "recomendaciones": [
            "1. Investigar las facturas duplicadas identificadas y recuperar los montos pagados en exceso.",
            "2. Implementar controles de acceso por horario en el sistema de aprobación de pagos.",
            "3. Reforzar la política de orden de compra obligatoria para toda transacción.",
            "4. Auditar los proveedores con alta concentración de pagos y un solo autorizador.",
            "5. Revisar las notas de crédito sin documentación de soporte.",
            "6. Implementar alertas automáticas para transacciones que superen umbrales.",
            "7. Establecer rotación de autorizadores para evitar conflictos de interés.",
        ],
        "clasificacion_riesgo_general": "ALTO - Se requiere acción inmediata en los hallazgos de severidad alta.",
    }
    
    return json.dumps(reporte, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# HERRAMIENTA 11: CONSULTAR NORMATIVA (RAG)
# ============================================================================

@tool
def consultar_normativa(consulta: str, tema: Optional[str] = None) -> str:
    """
    Busca información en la base de conocimiento de normativa de auditoría.
    Consulta documentos como NIA 240, COSO, ACFE, SOX y políticas internas
    para respaldar hallazgos con evidencia normativa verificable.
    
    Args:
        consulta: Pregunta sobre normativa, controles, procedimientos o políticas.
        tema: Filtro opcional por tema (ej: "NIA 240", "COSO", "ACFE", "SOX", "Políticas").
    
    Returns:
        Fragmentos relevantes con fuente, sección y contenido.
    """
    # Mapear tema a topic del metadata
    filtro_topic = None
    if tema:
        tema_lower = tema.lower()
        if "nia" in tema_lower or "240" in tema_lower:
            filtro_topic = "NIA 240 - Fraude en Auditoría"
        elif "coso" in tema_lower:
            filtro_topic = "COSO - Control Interno"
        elif "acfe" in tema_lower:
            filtro_topic = "ACFE - Fraude Ocupacional"
        elif "sox" in tema_lower:
            filtro_topic = "SOX - Cumplimiento"
        elif "politic" in tema_lower or "interna" in tema_lower:
            filtro_topic = "Políticas de Industria Nacional SAC"
    
    resultados = _buscar_en_base(
        query=consulta,
        k=4,
        filtro_topic=filtro_topic,
    )
    
    if not resultados or (len(resultados) == 1 and "⚠️" in resultados[0].get("contenido", "")):
        return json.dumps({
            "estado": "sin_resultados",
            "mensaje": "No se encontró información relevante en la base de conocimiento para esta consulta.",
            "sugerencia": "Intenta reformular la pregunta o consulta sobre: NIA 240, COSO, ACFE, SOX o Políticas internas."
        }, ensure_ascii=False)
    
    # Formatear resultados con fuentes
    fragmentos_formateados = []
    for r in resultados:
        fragmentos_formateados.append({
            "fuente": r["fuente"],
            "seccion": r["seccion"],
            "topic": r["topic"],
            "relevancia": r["relevancia"],
            "contenido": r["contenido"][:600],  # Limitar para no saturar contexto
        })
    
    respuesta = {
        "estado": "encontrado",
        "total_fragmentos": len(fragmentos_formateados),
        "fragmentos": fragmentos_formateados,
        "nota": "Cita siempre la fuente y sección al usar esta información en tu respuesta."
    }
    
    return json.dumps(respuesta, ensure_ascii=False, indent=2, default=str)


# ============================================================================
# LISTA DE TODAS LAS HERRAMIENTAS (para el agente)
# ============================================================================

def obtener_herramientas():
    """Retorna la lista de herramientas disponibles para el agente."""
    return [
        resumen_general,
        detectar_duplicados,
        detectar_fuera_de_horario,
        analizar_proveedores,
        detectar_fraccionamiento,
        detectar_montos_atipicos,
        analizar_autorizadores,
        analisis_benford,
        analizar_notas_credito,
        generar_reporte_ejecutivo,
        consultar_normativa,
    ]
