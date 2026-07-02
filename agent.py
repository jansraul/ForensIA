"""
============================================================================
AGENTE REACT - FORENS-IA (AUDITORÍA FORENSE)
Proyecto: Detección de Fraude en Transacciones
Framework: LangChain con create_agent
============================================================================
Agente ReAct que utiliza herramientas de detección de fraude y mantiene
memoria conversacional. Soporta dos modos:
  - Memoria en sesión (por defecto, sin configuración extra)
  - Memoria persistente con PostgreSQL (opcional, requiere DATABASE_URL)
============================================================================
"""

import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from config import SYSTEM_PROMPT, MODEL_NAME, TEMPERATURE, OPENAI_API_KEY
from config import PATH_TRANSACCIONES, PATH_PROVEEDORES, PATH_EMPLEADOS, DATABASE_URL
from tools import (
    cargar_datos,
    obtener_herramientas,
)
from rag_pipeline import ejecutar_pipeline_completo, obtener_inventario


# ============================================================================
# MEMORIA PERSISTENTE CON POSTGRESQL (OPCIONAL)
# ============================================================================

def crear_checkpointer_postgres():
    """
    Intenta crear un checkpointer con PostgreSQL.
    Si no hay DATABASE_URL o falla la conexión, retorna None.
    """
    if not DATABASE_URL:
        return None, None

    try:
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver

        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }

        pool = ConnectionPool(
            conninfo=DATABASE_URL,
            max_size=20,
            kwargs=connection_kwargs,
        )

        checkpointer = PostgresSaver(pool)

        # Crear tablas si no existen (seguro ejecutar múltiples veces)
        try:
            checkpointer.setup()
        except Exception:
            pass  # Las tablas ya existen

        return checkpointer, pool

    except ImportError:
        print("⚠️ Para memoria persistente instala: pip install langgraph-checkpoint-postgres psycopg[binary,pool]==3.2.6")
        return None, None
    except Exception as e:
        print(f"⚠️ No se pudo conectar a PostgreSQL: {e}")
        print("   FORENSIA funcionará con memoria en sesión.")
        return None, None


# ============================================================================
# CLASE DEL AGENTE CON MEMORIA
# ============================================================================

class SentinelAgent:
    """
    Agente de Auditoría Forense con memoria conversacional.
    Usa el patrón create_agent de LangChain con ciclo ReAct.
    
    Modos de memoria:
    - Sin DATABASE_URL: memoria en lista (se pierde al cerrar)
    - Con DATABASE_URL: memoria persistente en PostgreSQL
    """

    def __init__(self, thread_id: str = "auditor_default"):
        """Inicializa el agente con modelo, herramientas y memoria."""

        # 1. Configurar API Key
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

        # 2. Configurar el modelo LLM
        self.model = ChatOpenAI(
            model=MODEL_NAME,
            temperature=TEMPERATURE
        )

        # 3. Obtener las herramientas de detección
        self.tools = obtener_herramientas()

        # 4. Intentar configurar memoria persistente
        self.checkpointer, self._pool = crear_checkpointer_postgres()
        self.memoria_persistente = self.checkpointer is not None
        self.thread_id = thread_id

        # 5. Crear el agente ReAct con create_agent
        if self.memoria_persistente:
            # Con checkpointer de PostgreSQL
            self.agent = create_agent(
                model=self.model,
                tools=self.tools,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=self.checkpointer
            )
        else:
            # Sin checkpointer (memoria en lista)
            self.agent = create_agent(
                model=self.model,
                tools=self.tools,
                system_prompt=SYSTEM_PROMPT
            )

        # 6. Memoria conversacional en lista (respaldo si no hay PostgreSQL)
        self.historial_mensajes = []

        # 7. Estado de datos cargados
        self.datos_cargados = False

        # 8. Inicializar RAG (base de conocimiento)
        self.rag_activo = False
        try:
            resultado_rag = ejecutar_pipeline_completo(api_key=OPENAI_API_KEY)
            self.rag_activo = "✅" in resultado_rag
            if self.rag_activo:
                print(f"  📚 RAG: Base de conocimiento cargada")
            else:
                print(f"  ⚠️ RAG: {resultado_rag}")
        except Exception as e:
            print(f"  ⚠️ RAG no disponible: {e}")
            self.rag_activo = False

    def cargar_dataset(self, path_transacciones=None, path_proveedores=None, path_empleados=None):
        """
        Carga el dataset de transacciones para que las herramientas
        puedan analizarlo.
        """
        path_txn = path_transacciones or PATH_TRANSACCIONES
        path_prov = path_proveedores or PATH_PROVEEDORES
        path_emp = path_empleados or PATH_EMPLEADOS

        resultado = cargar_datos(path_txn, path_prov, path_emp)
        self.datos_cargados = True
        return resultado

    def ejecutar(self, pregunta: str, verbose: bool = False) -> str:
        """
        Ejecuta el agente con una pregunta del auditor.
        Mantiene la memoria conversacional entre llamadas.

        Args:
            pregunta: Consulta del auditor.
            verbose: Si True, muestra la traza completa del agente.

        Returns:
            Respuesta del agente como string.
        """

        # Validación de entrada
        if not pregunta or not pregunta.strip():
            return "⚠️ Por favor, ingresa una consulta válida."

        if not self.datos_cargados:
            return (
                "⚠️ No se han cargado datos aún. "
                "Primero carga el dataset de transacciones usando el botón "
                "'Cargar Datos' o escribe 'cargar datos'."
            )

        try:
            if self.memoria_persistente:
                # === MODO POSTGRESQL ===
                # El checkpointer se encarga de la memoria automáticamente
                config = {
                    "configurable": {"thread_id": self.thread_id},
                    "recursion_limit": 25,
                }

                resultado = self.agent.invoke(
                    {"messages": [{"role": "user", "content": pregunta}]},
                    config
                )

                # Extraer la respuesta final
                mensajes_resultado = resultado["messages"]
                mensaje_final = mensajes_resultado[-1]
                respuesta = mensaje_final.content

                # También actualizar historial local (para conteo en UI)
                self.historial_mensajes.append(
                    {"role": "user", "content": pregunta}
                )
                self.historial_mensajes.append(
                    {"role": "assistant", "content": respuesta}
                )

            else:
                # === MODO SESIÓN (comportamiento original) ===
                mensajes_completos = self.historial_mensajes + [
                    {"role": "user", "content": pregunta}
                ]

                resultado = self.agent.invoke(
                    {"messages": mensajes_completos}
                )

                # Extraer la respuesta final
                mensajes_resultado = resultado["messages"]
                mensaje_final = mensajes_resultado[-1]
                respuesta = mensaje_final.content

                # Actualizar la memoria conversacional
                self.historial_mensajes.append(
                    {"role": "user", "content": pregunta}
                )
                self.historial_mensajes.append(
                    {"role": "assistant", "content": respuesta}
                )

            # Mostrar traza si verbose está activado
            if verbose:
                self._mostrar_traza(mensajes_resultado)

            return respuesta

        except Exception as e:
            error_msg = f"❌ Error al procesar la consulta: {str(e)}"
            return error_msg

    def _mostrar_traza(self, mensajes):
        """Muestra la traza completa del agente (para depuración)."""

        print("\n" + "=" * 80)
        print("TRAZA DEL AGENTE FORENSIA")
        print("=" * 80)

        for i, mensaje in enumerate(mensajes, start=1):
            tipo = mensaje.__class__.__name__

            print(f"\n--- Mensaje {i}: {tipo} ---")

            if hasattr(mensaje, "content") and mensaje.content:
                print("Contenido:")
                contenido = mensaje.content
                if len(str(contenido)) > 500:
                    print(str(contenido)[:500] + "... [truncado]")
                else:
                    print(contenido)

            if hasattr(mensaje, "tool_calls") and mensaje.tool_calls:
                print("\nHerramientas invocadas:")
                for tool_call in mensaje.tool_calls:
                    print(f"  → {tool_call['name']}({tool_call['args']})")

            if hasattr(mensaje, "name") and mensaje.name:
                print(f"Herramienta: {mensaje.name}")

        print("\n" + "=" * 80)

    def limpiar_memoria(self):
        """Limpia el historial de conversación (reinicia la memoria)."""
        self.historial_mensajes = []
        return "🔄 Memoria conversacional reiniciada."

    def obtener_historial(self):
        """Retorna el historial de conversación actual."""
        return self.historial_mensajes

    def obtener_info(self):
        """Retorna información del agente."""
        info = {
            "nombre": "FORENSIA",
            "version": "3.0",
            "modelo": MODEL_NAME,
            "herramientas": [t.name for t in self.tools],
            "datos_cargados": self.datos_cargados,
            "mensajes_en_memoria": len(self.historial_mensajes),
            "memoria_persistente": self.memoria_persistente,
            "rag_activo": self.rag_activo,
        }
        
        if self.rag_activo:
            try:
                inventario = obtener_inventario()
                info["documentos_rag"] = len(inventario)
            except Exception:
                info["documentos_rag"] = 0
        
        return info


# ============================================================================
# FUNCIÓN PARA EJECUTAR DESDE CONSOLA (testing rápido)
# ============================================================================

def ejecutar_consola():
    """
    Modo consola interactivo para probar el agente.
    Útil para testing rápido sin Streamlit.
    """

    print("=" * 70)
    print("  FORENSIA - Agente de Auditoría Forense")
    print("  Detección de Fraude en Transacciones")
    print("=" * 70)

    # Inicializar agente
    agent = SentinelAgent()

    # Mostrar modo de memoria
    if agent.memoria_persistente:
        print("  📦 Memoria: PostgreSQL (persistente)")
    else:
        print("  💭 Memoria: Sesión (temporal)")

    # Cargar datos
    print("\n📂 Cargando dataset de transacciones...")
    resultado = agent.cargar_dataset()
    print(resultado)

    print("\n💡 Comandos especiales:")
    print("   'salir'   → Terminar sesión")
    print("   'limpiar' → Reiniciar memoria")
    print("   'info'    → Ver estado del agente")
    print("   'traza'   → Activar/desactivar traza")
    print("-" * 70)

    verbose = False

    while True:
        try:
            pregunta = input("\n🔍 Auditor: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Sesión finalizada.")
            break

        if not pregunta:
            continue

        if pregunta.lower() == "salir":
            print("\n👋 Sesión finalizada. ¡Hasta pronto!")
            break
        elif pregunta.lower() == "limpiar":
            print(agent.limpiar_memoria())
            continue
        elif pregunta.lower() == "info":
            info = agent.obtener_info()
            for k, v in info.items():
                print(f"  {k}: {v}")
            continue
        elif pregunta.lower() == "traza":
            verbose = not verbose
            print(f"  Traza {'activada ✅' if verbose else 'desactivada ❌'}")
            continue

        print("\n⏳ Analizando...")
        respuesta = agent.ejecutar(pregunta, verbose=verbose)
        print(f"\n🤖 FORENSIA:\n{respuesta}")


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    ejecutar_consola()
