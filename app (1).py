"""
============================================================================
FORENS-IA - Agente de Auditoría Forense
Interfaz Streamlit con Chat + Dashboard de Visualizaciones
============================================================================
"""

import streamlit as st
import pandas as pd
import os
import time

from agent import SentinelAgent
from visualizations import (
    graficar_kpis,
    graficar_distribucion_montos,
    graficar_timeline,
    graficar_heatmap_horario,
    graficar_top_proveedores,
    graficar_benford,
    graficar_metodos_pago,
    graficar_gasto_departamento,
    graficar_scatter_outliers,
    graficar_autorizadores,
)

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================
st.set_page_config(
    page_title="FORENSIA | Auditoría Forense",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================
st.markdown("""
<style>
    /* ===== IMPORTAR FUENTES ===== */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* ===== FONDO GENERAL ===== */
    .stApp {
        background: linear-gradient(160deg, #f0fdf4 0%, #e0f5ec 40%, #f7fdf9 100%);
    }
    
    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #064e3b 0%, #065f46 50%, #047857 100%);
        border-right: 2px solid #10b981;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #ffffff;
    }
    
    section[data-testid="stSidebar"] .stMarkdown h5, 
    section[data-testid="stSidebar"] .stMarkdown h4,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] .stCaption {
        color: #e2e8f0 !important;
    }
    
    section[data-testid="stSidebar"] hr {
        border-color: rgba(167, 243, 208, 0.3);
    }
    
    /* ===== HEADER PRINCIPAL ===== */
    .forensia-header {
        background: linear-gradient(135deg, #c026d3 0%, #d946ef 30%, #e879f9 60%, #c026d3 100%);
        border: 1px solid #e879f9;
        border-radius: 16px;
        padding: 2.5rem 3rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(192, 38, 211, 0.35);
    }
    
    .forensia-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #f0abfc, #e879f9, #d946ef, #e879f9, #f0abfc);
    }
    
    .forensia-header h1 {
        font-family: 'DM Sans', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0 0 0.5rem 0;
        letter-spacing: -1px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .forensia-header p {
        font-family: 'DM Sans', sans-serif;
        color: #ffffff !important;
        font-size: 1.1rem;
        font-weight: 500;
        margin: 0;
        text-shadow: 0 1px 4px rgba(0,0,0,0.2);
        letter-spacing: 0.3px;
    }
    
    /* ===== TARJETAS KPI ===== */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, #ffffff, #f0fdf4);
        border: 1px solid #a7f3d0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.08);
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: #10b981;
        box-shadow: 0 6px 20px rgba(5, 150, 105, 0.15);
    }
    
    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 700;
        color: #064e3b;
        margin-bottom: 0.3rem;
    }
    
    .kpi-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.78rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .kpi-value.alert { color: #dc2626; }
    .kpi-value.warning { color: #ea580c; }
    .kpi-value.success { color: #059669; }
    .kpi-value.info { color: #0891b2; }
    
    /* ===== CHAT CONTAINER ===== */
    .chat-message-user {
        background: linear-gradient(135deg, #059669, #10b981);
        border-radius: 16px 16px 4px 16px;
        padding: 1rem 1.3rem;
        margin: 0.5rem 0;
        max-width: 85%;
        margin-left: auto;
        color: #ffffff;
        font-family: 'DM Sans', sans-serif;
        box-shadow: 0 2px 10px rgba(5, 150, 105, 0.2);
    }
    
    .chat-message-assistant {
        background: linear-gradient(135deg, #ffffff, #f0fdf4);
        border: 1px solid #a7f3d0;
        border-radius: 16px 16px 16px 4px;
        padding: 1rem 1.3rem;
        margin: 0.5rem 0;
        max-width: 90%;
        color: #1f2937;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.92rem;
        line-height: 1.65;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border: 1px solid #d1fae5;
        border-radius: 8px;
        color: #6b7280;
        font-family: 'DM Sans', sans-serif;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #059669, #10b981);
        border-color: #10b981;
        color: #ffffff;
    }
    
    /* ===== BOTONES ===== */
    .stButton > button {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        border: none;
        border-radius: 8px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        transition: all 0.2s;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #047857, #059669);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.35);
    }
    
    /* ===== TEXTO GENERAL ===== */
    .stMarkdown, .stMarkdown p {
        color: #1f2937;
    }
    
    h1, h2, h3, h4, h5 {
        color: #064e3b !important;
    }
    
    /* ===== OCULTAR ELEMENTOS DEFAULT ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #f0fdf4;
    }
    ::-webkit-scrollbar-thumb {
        background: #6ee7b7;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #34d399;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# INICIALIZACIÓN DEL ESTADO DE SESIÓN
# ============================================================================
if "agent" not in st.session_state:
    st.session_state.agent = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "datos_cargados" not in st.session_state:
    st.session_state.datos_cargados = False

if "df" not in st.session_state:
    st.session_state.df = None

if "voz_activa" not in st.session_state:
    st.session_state.voz_activa = True


# ============================================================================
# FUNCIÓN PARA INICIALIZAR EL AGENTE
# ============================================================================
def inicializar_agente(api_key, path_txn, path_prov, path_emp):
    """Inicializa el agente FORENSIA con los datos proporcionados."""
    os.environ["OPENAI_API_KEY"] = api_key
    
    agent = SentinelAgent()
    resultado = agent.cargar_dataset(path_txn, path_prov, path_emp)
    
    st.session_state.agent = agent
    st.session_state.datos_cargados = True
    st.session_state.df = pd.read_csv(path_txn)
    
    return resultado


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🤖</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">
            FORENSIA
        </div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: #e2e8f0; letter-spacing: 2px; text-transform: uppercase;">
            Auditoría Forense IA
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- Configuración API ---
    st.markdown("##### ⚙️ Configuración")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Tu clave de API de OpenAI para GPT-4o"
    )
    
    st.divider()
    
    # --- Carga de datos ---
    st.markdown("##### 📂 Datos")
    
    # Opción 1: Datos incluidos
    usar_datos_demo = st.checkbox("Usar datos de demostración", value=True)
    
    # Opción 2: Subir archivo
    if not usar_datos_demo:
        archivo_subido = st.file_uploader(
            "Subir CSV de transacciones",
            type=["csv"],
            help="Sube tu propio archivo de transacciones"
        )
    
    # Botón de carga
    if st.button("🚀 Iniciar FORENSIA", use_container_width=True):
        if not api_key:
            st.error("⚠️ Ingresa tu API Key de OpenAI")
        else:
            with st.spinner("Inicializando agente..."):
                try:
                    if usar_datos_demo:
                        # Buscar archivos en la carpeta data/
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        data_dir = os.path.join(base_dir, "data")
                        path_txn = os.path.join(data_dir, "transacciones_empresa_2024.csv")
                        path_prov = os.path.join(data_dir, "catalogo_proveedores.csv")
                        path_emp = os.path.join(data_dir, "catalogo_empleados.csv")
                    else:
                        if archivo_subido:
                            # Guardar archivo temporal
                            path_txn = os.path.join("/tmp", "transacciones_subidas.csv")
                            with open(path_txn, "wb") as f:
                                f.write(archivo_subido.getbuffer())
                            path_prov = None
                            path_emp = None
                        else:
                            st.error("⚠️ Sube un archivo CSV")
                            st.stop()
                    
                    resultado = inicializar_agente(api_key, path_txn, path_prov, path_emp)
                    st.success(resultado)
                    
                    # Mensaje de bienvenida
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": (
                                "🤖 **FORENSIA activado.**\n\n"
                                "Soy tu agente de auditoría forense. He cargado el dataset de "
                                "transacciones y la base de conocimiento normativa.\n\n"
                                "**¿Por dónde quieres empezar?** Algunas opciones:\n"
                                "- 📊 *\"Dame un resumen general del dataset\"*\n"
                                "- 🔍 *\"Busca transacciones duplicadas\"*\n"
                                "- 👻 *\"Analiza proveedores sospechosos\"*\n"
                                "- ⏰ *\"Detecta transacciones fuera de horario\"*\n"
                                "- 📈 *\"Aplica la Ley de Benford\"*\n"
                                "- 📚 *\"¿Qué dice la NIA 240 sobre el triángulo del fraude?\"*\n"
                                "- 📋 *\"Genera un reporte ejecutivo completo\"*"
                            )
                        }
                    ]
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.divider()
    
    # --- Estado del agente ---
    if st.session_state.datos_cargados:
        st.markdown("##### 📡 Estado")
        st.markdown(f"""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #ffffff; font-weight: 600;">
            ● FORENSIA ACTIVO
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.agent:
            info = st.session_state.agent.obtener_info()
            st.caption(f"Modelo: {info['modelo']}")
            st.caption(f"Herramientas: {len(info['herramientas'])}")
            st.caption(f"Mensajes en memoria: {info['mensajes_en_memoria']}")
            
            # Indicador de tipo de memoria
            if info.get('memoria_persistente', False):
                st.markdown("""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #10b981; 
                            background: rgba(16,185,129,0.1); padding: 4px 8px; border-radius: 6px; margin-top: 4px;">
                    📦 Memoria: PostgreSQL
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #f59e0b; 
                            background: rgba(245,158,11,0.1); padding: 4px 8px; border-radius: 6px; margin-top: 4px;">
                    💭 Memoria: Sesión
                </div>
                """, unsafe_allow_html=True)
            
            # Indicador RAG
            if info.get('rag_activo', False):
                docs_rag = info.get('documentos_rag', 0)
                st.markdown(f"""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #8b5cf6; 
                            background: rgba(139,92,246,0.1); padding: 4px 8px; border-radius: 6px; margin-top: 4px;">
                    📚 RAG: {docs_rag} documentos
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #6b7280; 
                            background: rgba(107,114,128,0.1); padding: 4px 8px; border-radius: 6px; margin-top: 4px;">
                    📚 RAG: No disponible
                </div>
                """, unsafe_allow_html=True)
        
        if st.button("🔄 Limpiar Memoria", use_container_width=True):
            st.session_state.agent.limpiar_memoria()
            st.session_state.messages = [st.session_state.messages[0]]
            st.success("Memoria reiniciada")
            st.rerun()
    
    st.divider()
    
    # --- Consultas sugeridas ---
    if st.session_state.datos_cargados:
        st.markdown("##### 💡 Consultas Sugeridas")
        
        sugerencias = [
            "Dame un resumen general",
            "Busca facturas duplicadas",
            "Analiza proveedores sospechosos",
            "Detecta fraccionamiento de compras",
            "Busca transacciones fuera de horario",
            "Analiza montos atípicos",
            "Revisa los autorizadores",
            "Aplica análisis de Benford",
            "Revisa notas de crédito",
            "Genera reporte ejecutivo",
        ]
        
        for sug in sugerencias:
            if st.button(f"→ {sug}", key=f"sug_{sug}", use_container_width=True):
                st.session_state.consulta_sugerida = sug
                st.rerun()


# ============================================================================
# CONTENIDO PRINCIPAL
# ============================================================================

# Header
st.markdown("""
<div class="forensia-header">
    <h1>🤖 FORENSIA</h1>
    <p>Agente de Auditoría Forense • Detección de Fraude en Transacciones • Desarrollado por GPT-4o + LangChain</p>
</div>
""", unsafe_allow_html=True)


# Si no hay datos cargados, mostrar pantalla de inicio
if not st.session_state.datos_cargados:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🔒</div>
        <h2 style="font-family: 'DM Sans', sans-serif; color: #064e3b; font-weight: 700;">
            Configura tu API Key para comenzar
        </h2>
        <p style="font-family: 'DM Sans', sans-serif; color: #6b7280; max-width: 500px; margin: 0 auto;">
            Ingresa tu clave de OpenAI en el panel lateral y presiona "Iniciar FORENSIA" 
            para activar el agente de auditoría forense.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ============================================================================
# TABS PRINCIPALES: CHAT + DASHBOARD
# ============================================================================
tab_chat, tab_dashboard = st.tabs(["💬 Chat con FORENSIA", "📊 Dashboard Analítico"])


# ============================================================================
# TAB 1: CHAT CON EL AGENTE
# ============================================================================
with tab_chat:
    
    # Mostrar historial de mensajes
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-message-user">{msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])
    
    # Verificar si hay consulta sugerida
    consulta_sugerida = st.session_state.pop("consulta_sugerida", None)
    
    # ===== COMPONENTE DE VOZ =====
    if st.session_state.datos_cargados:
        
        # Columnas para micrófono y controles
        col_mic, col_tts = st.columns([1, 1])
        
        with col_mic:
            # Componente de reconocimiento de voz embebido
            voice_html = """
            <div style="
                display: flex; align-items: center; gap: 12px;
                padding: 10px 16px;
                background: linear-gradient(135deg, #ffffff, #f0fdf4);
                border: 1px solid #a7f3d0;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(5, 150, 105, 0.08);
                font-family: 'Segoe UI', sans-serif;
            ">
                <button id="micBtn" style="
                    width: 48px; height: 48px; border-radius: 50%;
                    border: 2px solid #10b981;
                    background: linear-gradient(135deg, #059669, #10b981);
                    color: white; font-size: 1.3rem; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    transition: all 0.3s; flex-shrink: 0;
                ">🎤</button>
                <span id="status" style="color: #6b7280; font-size: 0.85rem;">
                    Pulsa para hablar
                </span>
            </div>
            
            <script>
            const btn = document.getElementById('micBtn');
            const status = document.getElementById('status');
            let rec = null;
            let recording = false;
            
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                rec = new SR();
                rec.lang = 'es-ES';
                rec.continuous = false;
                rec.interimResults = true;
                
                rec.onresult = (e) => {
                    let t = '';
                    for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
                    status.textContent = '🎯 "' + t + '"';
                    
                    if (e.results[e.results.length - 1].isFinal) {
                        stop();
                        status.textContent = '✅ Enviando: "' + t + '"';
                        
                        // Buscar el textarea del chat
                        const root = window.parent.document;
                        const ta = root.querySelector('textarea[data-testid="stChatInputTextArea"]');
                        if (ta) {
                            const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                            setter.call(ta, t);
                            ta.dispatchEvent(new Event('input', {bubbles: true}));
                            setTimeout(() => {
                                ta.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
                            }, 400);
                        }
                    }
                };
                rec.onend = () => stop();
                rec.onerror = (e) => { status.textContent = '⚠️ Error: ' + e.error; stop(); };
            }
            
            function stop() {
                recording = false;
                btn.textContent = '🎤';
                btn.style.background = 'linear-gradient(135deg, #059669, #10b981)';
                btn.style.borderColor = '#10b981';
                btn.style.animation = '';
            }
            
            btn.onclick = () => {
                if (!rec) { status.textContent = '⚠️ Usa Chrome para voz'; return; }
                if (recording) { rec.stop(); stop(); }
                else {
                    window.parent.speechSynthesis.cancel();
                    rec.start();
                    recording = true;
                    btn.textContent = '⏹️';
                    btn.style.background = 'linear-gradient(135deg, #dc2626, #ef4444)';
                    btn.style.borderColor = '#ef4444';
                    btn.style.animation = 'pulse 1.5s infinite';
                    status.textContent = '🔴 Escuchando... habla ahora';
                }
            };
            </script>
            <style>
            @keyframes pulse {
                0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
                50% { box-shadow: 0 0 0 12px rgba(239,68,68,0); }
            }
            </style>
            """
            st.components.v1.html(voice_html, height=75)
        
        with col_tts:
            # Toggle de voz de respuesta
            voz_col1, voz_col2 = st.columns([3, 1])
            with voz_col1:
                st.session_state.voz_activa = st.toggle("🔊 Respuestas con voz", value=st.session_state.voz_activa)
            with voz_col2:
                if st.session_state.messages and len(st.session_state.messages) > 0:
                    if st.button("🔁 Repetir"):
                        st.session_state.repetir_voz = True
    
    # Input del usuario
    prompt = st.chat_input("Escribe o usa el micrófono para consultar...")
    
    # Usar consulta sugerida si existe
    if consulta_sugerida:
        prompt = consulta_sugerida
    
    if prompt:
        # Mostrar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(
            f'<div class="chat-message-user">{prompt}</div>',
            unsafe_allow_html=True
        )
        
        # Generar respuesta del agente
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🔍 Analizando..."):
                respuesta = st.session_state.agent.ejecutar(prompt)
            st.markdown(respuesta)
        
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        
        # Leer respuesta en voz alta si está activado
        if st.session_state.voz_activa:
            st.session_state.leer_respuesta = respuesta
        
        st.rerun()
    
    # ===== TEXT-TO-SPEECH: Leer respuesta =====
    respuesta_a_leer = st.session_state.pop("leer_respuesta", None)
    repetir = st.session_state.pop("repetir_voz", False)
    
    if repetir and st.session_state.messages:
        # Buscar última respuesta del asistente
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant":
                respuesta_a_leer = msg["content"]
                break
    
    if respuesta_a_leer and st.session_state.voz_activa:
        # Limpiar texto para TTS
        import re
        texto_limpio = re.sub(r'[#*_~`>|]', '', respuesta_a_leer)
        texto_limpio = re.sub(r'🔴|🟡|🟢|⚠️|❌|✅|📊|📋|🔍|💡|🛡️|📡|🚀|📂|⏰|📈|👻|🔄|💬|🔒|●', '', texto_limpio)
        texto_limpio = re.sub(r'S/\.', 'soles', texto_limpio)
        texto_limpio = re.sub(r'-{3,}', '', texto_limpio)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        
        # Limitar a 500 chars para TTS (resumen)
        if len(texto_limpio) > 500:
            # Tomar las primeras oraciones hasta 500 chars
            oraciones = texto_limpio.split('. ')
            resumen = ''
            for oracion in oraciones:
                if len(resumen + oracion) > 500:
                    break
                resumen += oracion + '. '
            texto_limpio = resumen.strip() if resumen else texto_limpio[:500]
        
        texto_js = texto_limpio.replace("'", "\\'").replace("\n", " ").replace("\r", "")
        
        tts_html = f"""
        <script>
        (function() {{
            const synth = window.parent.speechSynthesis;
            synth.cancel();
            
            const text = '{texto_js}';
            
            function hablar() {{
                const chunks = text.match(/.{{1,200}}[.!?,;]|.{{1,200}}/g) || [text];
                let i = 0;
                
                function next() {{
                    if (i >= chunks.length) return;
                    const u = new SpeechSynthesisUtterance(chunks[i]);
                    u.lang = 'es-ES';
                    u.rate = 1.05;
                    const voices = synth.getVoices();
                    const esVoice = voices.find(v => v.lang.startsWith('es'));
                    if (esVoice) u.voice = esVoice;
                    u.onend = () => {{ i++; next(); }};
                    synth.speak(u);
                }}
                
                next();
            }}
            
            if (synth.getVoices().length === 0) {{
                synth.onvoiceschanged = hablar;
            }} else {{
                setTimeout(hablar, 300);
            }}
        }})();
        </script>
        """
        st.components.v1.html(tts_html, height=0)


# ============================================================================
# TAB 2: DASHBOARD DE VISUALIZACIONES
# ============================================================================
with tab_dashboard:
    
    df = st.session_state.df
    
    if df is not None:
        # --- KPIs ---
        kpis = graficar_kpis(df)
        
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-value info">{kpis['total_transacciones']}</div>
                <div class="kpi-label">Transacciones</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value success">{kpis['monto_total']}</div>
                <div class="kpi-label">Monto Total</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value info">{kpis['proveedores']}</div>
                <div class="kpi-label">Proveedores</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value info">{kpis['autorizadores']}</div>
                <div class="kpi-label">Autorizadores</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value warning">{kpis['fuera_horario']}</div>
                <div class="kpi-label">Fuera de Horario</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value alert">{kpis['duplicados']}</div>
                <div class="kpi-label">Duplicados</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # --- Fila 1: Timeline + Heatmap ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(
                graficar_timeline(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        with col2:
            st.plotly_chart(
                graficar_heatmap_horario(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        # --- Fila 2: Benford + Métodos de Pago ---
        col3, col4 = st.columns(2)
        
        with col3:
            st.plotly_chart(
                graficar_benford(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        with col4:
            st.plotly_chart(
                graficar_metodos_pago(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        # --- Fila 3: Top Proveedores ---
        st.plotly_chart(
            graficar_top_proveedores(df),
            use_container_width=True,
            config={"displayModeBar": False}
        )
        
        # --- Fila 4: Distribución de Montos + Scatter ---
        col5, col6 = st.columns(2)
        
        with col5:
            st.plotly_chart(
                graficar_distribucion_montos(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        with col6:
            st.plotly_chart(
                graficar_gasto_departamento(df),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        
        # --- Fila 5: Autorizadores + Scatter Outliers ---
        st.plotly_chart(
            graficar_autorizadores(df),
            use_container_width=True,
            config={"displayModeBar": False}
        )
        
        st.plotly_chart(
            graficar_scatter_outliers(df),
            use_container_width=True,
            config={"displayModeBar": False}
        )
