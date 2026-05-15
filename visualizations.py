"""
============================================================================
VISUALIZACIONES - AUDITORÍA FORENSE
Proyecto: SENTINEL - Detección de Fraude en Transacciones
============================================================================
Funciones de visualización con Plotly para el dashboard de Streamlit.
============================================================================
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


# ============================================================================
# PALETA DE COLORES SENTINEL
# ============================================================================
COLORS = {
    "bg_dark": "#0a0f1a",
    "bg_card": "#111827",
    "accent_red": "#ef4444",
    "accent_orange": "#f97316",
    "accent_yellow": "#eab308",
    "accent_green": "#22c55e",
    "accent_blue": "#3b82f6",
    "accent_cyan": "#06b6d4",
    "accent_purple": "#8b5cf6",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "grid": "#1e293b",
}

FRAUD_COLORS = {
    "Fraccionamiento de compras": "#ef4444",
    "Proveedor fantasma": "#f97316",
    "Transacción duplicada": "#eab308",
    "Transacción fuera de horario": "#8b5cf6",
    "Sobrefacturación": "#ec4899",
    "Conflicto de interés": "#06b6d4",
    "Lavado de activos": "#dc2626",
    "Gastos de viaje ficticios": "#14b8a6",
    "Manipulación de notas de crédito": "#f59e0b",
    "Monto bajo umbral sospechoso": "#6366f1",
}

TEMPLATE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text_primary"], family="DM Sans, sans-serif"),
    margin=dict(l=40, r=40, t=60, b=40),
    xaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
    yaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color=COLORS["text_secondary"])
    ),
)


# ============================================================================
# GRÁFICO 1: RESUMEN KPIs (MÉTRICAS PRINCIPALES)
# ============================================================================
def graficar_kpis(df):
    """Retorna diccionario con KPIs principales para mostrar con st.metric."""
    total_txn = len(df)
    monto_total = df["monto_total"].sum()
    proveedores = df["proveedor_id"].nunique()
    autorizadores = df["autorizado_por_id"].nunique()
    monto_promedio = df["monto_total"].mean()
    
    # Transacciones fuera de horario
    df_temp = df.copy()
    df_temp["hora_num"] = pd.to_datetime(df_temp["hora"], format="%H:%M:%S").dt.hour
    fuera_horario = len(df_temp[(df_temp["hora_num"] < 8) | (df_temp["hora_num"] >= 18)])
    
    # Duplicados
    duplicados = len(df[df.duplicated(subset=["numero_factura", "proveedor_id"], keep=False)])
    
    return {
        "total_transacciones": f"{total_txn:,}",
        "monto_total": f"S/. {monto_total:,.2f}",
        "proveedores": f"{proveedores}",
        "autorizadores": f"{autorizadores}",
        "monto_promedio": f"S/. {monto_promedio:,.2f}",
        "fuera_horario": f"{fuera_horario}",
        "duplicados": f"{duplicados}",
    }


# ============================================================================
# GRÁFICO 2: DISTRIBUCIÓN DE MONTOS POR CATEGORÍA
# ============================================================================
def graficar_distribucion_montos(df):
    """Box plot de distribución de montos por categoría."""
    top_cats = df.groupby("categoria")["monto_total"].sum().nlargest(8).index
    df_filtrado = df[df["categoria"].isin(top_cats)]
    
    fig = px.box(
        df_filtrado,
        x="categoria",
        y="monto_total",
        color="categoria",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    
    fig.update_layout(
        title="Distribución de Montos por Categoría (Top 8)",
        xaxis_title="",
        yaxis_title="Monto Total (S/.)",
        showlegend=False,
        **TEMPLATE_LAYOUT,
    )
    fig.update_xaxes(tickangle=45)
    
    return fig


# ============================================================================
# GRÁFICO 3: LÍNEA DE TIEMPO DE TRANSACCIONES
# ============================================================================
def graficar_timeline(df):
    """Línea de tiempo con volumen de transacciones por semana."""
    df_temp = df.copy()
    df_temp["fecha"] = pd.to_datetime(df_temp["fecha"])
    df_temp["semana"] = df_temp["fecha"].dt.isocalendar().week.astype(int)
    df_temp["mes"] = df_temp["fecha"].dt.to_period("M").astype(str)
    
    por_mes = df_temp.groupby("mes").agg(
        cantidad=("transaction_id", "count"),
        monto=("monto_total", "sum")
    ).reset_index()
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=por_mes["mes"],
            y=por_mes["cantidad"],
            name="Cantidad",
            marker_color=COLORS["accent_blue"],
            opacity=0.7,
        ),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(
            x=por_mes["mes"],
            y=por_mes["monto"],
            name="Monto Total",
            line=dict(color=COLORS["accent_cyan"], width=3),
            mode="lines+markers",
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title="Volumen de Transacciones por Mes",
        **TEMPLATE_LAYOUT,
    )
    fig.update_yaxes(title_text="Cantidad de Transacciones", secondary_y=False)
    fig.update_yaxes(title_text="Monto Total (S/.)", secondary_y=True)
    
    return fig


# ============================================================================
# GRÁFICO 4: HEATMAP DE TRANSACCIONES POR HORA Y DÍA
# ============================================================================
def graficar_heatmap_horario(df):
    """Heatmap de actividad por hora del día y día de la semana."""
    df_temp = df.copy()
    df_temp["hora_num"] = pd.to_datetime(df_temp["hora"], format="%H:%M:%S").dt.hour
    
    orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    pivot = df_temp.groupby(["dia_semana", "hora_num"]).size().reset_index(name="cantidad")
    pivot_table = pivot.pivot(index="dia_semana", columns="hora_num", values="cantidad").fillna(0)
    pivot_table = pivot_table.reindex(orden_dias)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=[f"{h}:00" for h in pivot_table.columns],
        y=pivot_table.index,
        colorscale=[
            [0, "#0a0f1a"],
            [0.25, "#1e3a5f"],
            [0.5, "#3b82f6"],
            [0.75, "#f97316"],
            [1, "#ef4444"],
        ],
        hoverongaps=False,
        hovertemplate="Día: %{y}<br>Hora: %{x}<br>Transacciones: %{z}<extra></extra>",
    ))
    
    fig.update_layout(
        title="Mapa de Calor: Actividad por Hora y Día",
        xaxis_title="Hora del Día",
        yaxis_title="",
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 5: TOP PROVEEDORES POR MONTO
# ============================================================================
def graficar_top_proveedores(df, top_n=15):
    """Barras horizontales de los proveedores con mayor monto."""
    top = df.groupby("proveedor_nombre")["monto_total"].sum().nlargest(top_n).reset_index()
    top = top.sort_values("monto_total", ascending=True)
    
    fig = go.Figure(go.Bar(
        x=top["monto_total"],
        y=top["proveedor_nombre"],
        orientation="h",
        marker=dict(
            color=top["monto_total"],
            colorscale=[[0, COLORS["accent_blue"]], [1, COLORS["accent_red"]]],
        ),
        hovertemplate="<b>%{y}</b><br>Monto: S/. %{x:,.2f}<extra></extra>",
    ))
    
    fig.update_layout(
        title=f"Top {top_n} Proveedores por Monto Total",
        xaxis_title="Monto Total (S/.)",
        yaxis_title="",
        height=500,
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 6: ANÁLISIS DE BENFORD
# ============================================================================
def graficar_benford(df, campo="monto_total"):
    """Gráfico comparativo de distribución observada vs Ley de Benford."""
    benford_esperado = {1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7, 5: 7.9, 6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6}
    
    montos = df[campo].abs()
    montos = montos[montos > 0]
    primer_digito = montos.apply(lambda x: int(str(x).replace(".", "").replace("-", "").lstrip("0")[0]) if x != 0 else 0)
    primer_digito = primer_digito[primer_digito > 0]
    
    conteo = primer_digito.value_counts().sort_index()
    total = len(primer_digito)
    
    digitos = list(range(1, 10))
    observado = [(conteo.get(d, 0) / total) * 100 for d in digitos]
    esperado = [benford_esperado[d] for d in digitos]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=digitos,
        y=observado,
        name="Observado",
        marker_color=COLORS["accent_blue"],
        opacity=0.8,
    ))
    
    fig.add_trace(go.Scatter(
        x=digitos,
        y=esperado,
        name="Ley de Benford (esperado)",
        line=dict(color=COLORS["accent_red"], width=3, dash="dash"),
        mode="lines+markers",
        marker=dict(size=8),
    ))
    
    fig.update_layout(
        title="Análisis de Ley de Benford - Primer Dígito",
        xaxis_title="Primer Dígito",
        yaxis_title="Frecuencia (%)",
        barmode="overlay",
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 7: DISTRIBUCIÓN POR MÉTODO DE PAGO
# ============================================================================
def graficar_metodos_pago(df):
    """Gráfico de dona con la distribución de métodos de pago."""
    conteo = df["metodo_pago"].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=conteo.index,
        values=conteo.values,
        hole=0.55,
        marker=dict(colors=[
            COLORS["accent_blue"],
            COLORS["accent_cyan"],
            COLORS["accent_purple"],
            COLORS["accent_orange"],
            COLORS["accent_green"],
            COLORS["accent_yellow"],
        ]),
        textinfo="label+percent",
        textfont=dict(size=12, color=COLORS["text_primary"]),
        hovertemplate="<b>%{label}</b><br>Cantidad: %{value:,}<br>Porcentaje: %{percent}<extra></extra>",
    )])
    
    fig.update_layout(
        title="Distribución por Método de Pago",
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 8: GASTO POR DEPARTAMENTO
# ============================================================================
def graficar_gasto_departamento(df):
    """Treemap del gasto por departamento y categoría."""
    agrupado = df.groupby(["departamento", "categoria"])["monto_total"].sum().reset_index()
    
    fig = px.treemap(
        agrupado,
        path=["departamento", "categoria"],
        values="monto_total",
        color="monto_total",
        color_continuous_scale=["#1e3a5f", "#3b82f6", "#f97316", "#ef4444"],
    )
    
    fig.update_layout(
        title="Distribución de Gasto por Departamento y Categoría",
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 9: SCATTER DE MONTOS POR PROVEEDOR (OUTLIERS)
# ============================================================================
def graficar_scatter_outliers(df):
    """Scatter plot para visualizar outliers por proveedor."""
    df_temp = df.copy()
    df_temp["fecha"] = pd.to_datetime(df_temp["fecha"])
    
    fig = px.scatter(
        df_temp,
        x="fecha",
        y="monto_total",
        color="categoria",
        size=df_temp["monto_total"].abs().clip(lower=100),
        hover_data=["proveedor_nombre", "autorizado_por", "descripcion"],
        color_discrete_sequence=px.colors.qualitative.Set2,
        opacity=0.6,
    )
    
    fig.update_layout(
        title="Dispersión de Transacciones en el Tiempo (tamaño = monto)",
        xaxis_title="Fecha",
        yaxis_title="Monto Total (S/.)",
        height=500,
        **TEMPLATE_LAYOUT,
    )
    
    return fig


# ============================================================================
# GRÁFICO 10: CONCENTRACIÓN DE AUTORIZADORES
# ============================================================================
def graficar_autorizadores(df):
    """Barras con la concentración de transacciones por autorizador."""
    auth = df.groupby("autorizado_por").agg(
        cantidad=("transaction_id", "count"),
        monto=("monto_total", "sum"),
    ).reset_index().sort_values("monto", ascending=True)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Por Cantidad de Transacciones", "Por Monto Autorizado"),
        shared_yaxes=True,
    )
    
    fig.add_trace(
        go.Bar(
            x=auth["cantidad"],
            y=auth["autorizado_por"],
            orientation="h",
            marker_color=COLORS["accent_blue"],
            name="Cantidad",
            hovertemplate="<b>%{y}</b><br>Transacciones: %{x:,}<extra></extra>",
        ),
        row=1, col=1,
    )
    
    fig.add_trace(
        go.Bar(
            x=auth["monto"],
            y=auth["autorizado_por"],
            orientation="h",
            marker_color=COLORS["accent_orange"],
            name="Monto",
            hovertemplate="<b>%{y}</b><br>Monto: S/. %{x:,.2f}<extra></extra>",
        ),
        row=1, col=2,
    )
    
    fig.update_layout(
        title="Concentración por Autorizador",
        height=600,
        showlegend=False,
        **TEMPLATE_LAYOUT,
    )
    
    return fig
