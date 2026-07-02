"""
============================================================================
PIPELINE RAG - FORENSIA (AUDITORÍA FORENSE)
Proyecto: Detección de Fraude en Transacciones + Base de Conocimiento
============================================================================
Pipeline completo de RAG: ingesta, limpieza, fragmentación, metadata,
embeddings, indexación en FAISS y recuperación.
============================================================================
"""

import os
import re
import glob
from typing import List, Optional, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# ============================================================================
# CONFIGURACIÓN RAG
# ============================================================================

# Directorio de la base de conocimiento
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")

# Directorio para el índice FAISS persistido
FAISS_INDEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faiss_index")

# Configuración de fragmentación
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Modelo de embeddings
EMBEDDING_MODEL = "text-embedding-3-small"

# Variable global para el vector store
_vector_store: FAISS = None


# ============================================================================
# FASE 1: INGESTA - Carga de documentos
# ============================================================================

def cargar_documentos(directorio: str = None) -> List[Document]:
    """
    Carga todos los documentos Markdown de la base de conocimiento.
    Agrega metadata de origen a cada documento.
    
    Args:
        directorio: Ruta al directorio con los documentos.
    
    Returns:
        Lista de objetos Document con contenido y metadata.
    """
    directorio = directorio or KNOWLEDGE_BASE_DIR
    documentos = []
    
    # Buscar archivos Markdown y PDF
    archivos_md = glob.glob(os.path.join(directorio, "*.md"))
    archivos_pdf = glob.glob(os.path.join(directorio, "*.pdf"))
    
    archivos_todos = archivos_md + archivos_pdf
    
    if not archivos_todos:
        print(f"⚠️ No se encontraron documentos en {directorio}")
        return documentos
    
    # Cargar archivos Markdown
    for archivo in archivos_md:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
            
            if not contenido.strip():
                print(f"⚠️ Archivo vacío: {archivo}")
                continue
            
            nombre_archivo = os.path.basename(archivo)
            nombre_doc = nombre_archivo.replace(".md", "").replace("_", " ")
            content_type, topic = _clasificar_documento(nombre_archivo)
            
            doc = Document(
                page_content=contenido,
                metadata={
                    "source": nombre_archivo,
                    "document_name": nombre_doc,
                    "content_type": content_type,
                    "topic": topic,
                    "file_path": archivo,
                }
            )
            documentos.append(doc)
            print(f"  ✅ Cargado (MD): {nombre_doc} ({len(contenido)} caracteres)")
            
        except Exception as e:
            print(f"  ❌ Error al cargar {archivo}: {e}")
    
    # Cargar archivos PDF
    for archivo in archivos_pdf:
        try:
            from langchain_community.document_loaders import PyPDFLoader
            
            nombre_archivo = os.path.basename(archivo)
            nombre_doc = nombre_archivo.replace(".pdf", "").replace("_", " ")
            content_type, topic = _clasificar_documento(nombre_archivo)
            
            loader = PyPDFLoader(archivo)
            paginas = loader.load()
            
            for pagina in paginas:
                if pagina.page_content.strip():
                    pagina.metadata["source"] = nombre_archivo
                    pagina.metadata["document_name"] = nombre_doc
                    pagina.metadata["content_type"] = content_type
                    pagina.metadata["topic"] = topic
                    pagina.metadata["file_path"] = archivo
                    documentos.append(pagina)
            
            print(f"  ✅ Cargado (PDF): {nombre_doc} ({len(paginas)} páginas)")
            
        except ImportError:
            print(f"  ⚠️ Para cargar PDFs instala: pip install pypdf")
        except Exception as e:
            print(f"  ❌ Error al cargar {archivo}: {e}")
    
    print(f"\n📚 Total documentos cargados: {len(documentos)}")
    return documentos


def _clasificar_documento(nombre_archivo: str) -> tuple:
    """Clasifica el documento por tipo y tema basándose en el nombre."""
    nombre = nombre_archivo.lower()
    
    if "nia" in nombre:
        return "norma_internacional", "NIA 240 - Fraude en Auditoría"
    elif "coso" in nombre:
        return "marco_referencia", "COSO - Control Interno"
    elif "acfe" in nombre:
        return "informe_referencia", "ACFE - Fraude Ocupacional"
    elif "politica" in nombre:
        return "politica_interna", "Políticas de Industria Nacional SAC"
    elif "sox" in nombre:
        return "regulacion", "SOX - Cumplimiento"
    elif "nogai" in nombre or "nagai" in nombre:
        return "norma_nacional", "NOGAI - Normas de Auditoría Gubernamental"
    else:
        return "documento_general", "General"


# ============================================================================
# FASE 2: LIMPIEZA - Normalización del texto
# ============================================================================

def limpiar_documentos(documentos: List[Document]) -> List[Document]:
    """
    Normaliza y limpia el texto de los documentos.
    
    - Elimina líneas vacías excesivas.
    - Normaliza espacios.
    - Elimina caracteres especiales innecesarios.
    """
    docs_limpios = []
    
    for doc in documentos:
        texto = doc.page_content
        
        # Normalizar saltos de línea excesivos
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        
        # Normalizar espacios múltiples
        texto = re.sub(r' {2,}', ' ', texto)
        
        # Eliminar espacios al inicio/final de líneas
        texto = '\n'.join(line.strip() for line in texto.split('\n'))
        
        # Eliminar líneas que solo contienen separadores
        texto = re.sub(r'^[=\-]{3,}$', '', texto, flags=re.MULTILINE)
        
        texto = texto.strip()
        
        if texto:
            doc_limpio = Document(
                page_content=texto,
                metadata=doc.metadata.copy()
            )
            docs_limpios.append(doc_limpio)
    
    print(f"🧹 Documentos limpiados: {len(docs_limpios)}")
    return docs_limpios


# ============================================================================
# FASE 3: FRAGMENTACIÓN - Chunks con metadata
# ============================================================================

def fragmentar_documentos(
    documentos: List[Document],
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Document]:
    """
    Fragmenta los documentos en chunks con metadata enriquecida.
    
    Usa RecursiveCharacterTextSplitter que respeta la estructura
    del documento (headers, párrafos, oraciones).
    
    Args:
        documentos: Lista de documentos a fragmentar.
        chunk_size: Tamaño máximo de cada chunk (default: 800).
        chunk_overlap: Solapamiento entre chunks (default: 150).
    
    Returns:
        Lista de chunks con metadata enriquecida.
    """
    chunk_size = chunk_size or CHUNK_SIZE
    chunk_overlap = chunk_overlap or CHUNK_OVERLAP
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
        length_function=len,
    )
    
    todos_los_chunks = []
    
    for doc in documentos:
        chunks = splitter.split_documents([doc])
        
        for i, chunk in enumerate(chunks):
            # Enriquecer metadata de cada chunk
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            
            # Detectar sección del documento
            seccion = _detectar_seccion(chunk.page_content)
            chunk.metadata["section"] = seccion
            
            # Generar un slug para la sección
            chunk.metadata["section_slug"] = re.sub(
                r'[^a-z0-9]+', '-', seccion.lower()
            ).strip('-')[:50]
            
            todos_los_chunks.append(chunk)
    
    print(f"📄 Total chunks generados: {len(todos_los_chunks)}")
    print(f"   Tamaño de chunk: {chunk_size} | Overlap: {chunk_overlap}")
    return todos_los_chunks


def _detectar_seccion(texto: str) -> str:
    """Detecta la sección del documento basándose en los headers del chunk."""
    lineas = texto.strip().split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith('## '):
            return linea.replace('## ', '').strip()
        elif linea.startswith('### '):
            return linea.replace('### ', '').strip()
        elif linea.startswith('#### '):
            return linea.replace('#### ', '').strip()
        elif linea.startswith('# '):
            return linea.replace('# ', '').strip()
    
    # Si no encuentra header, usar las primeras palabras
    primer_linea = lineas[0].strip() if lineas else "Sin sección"
    return primer_linea[:60]


# ============================================================================
# FASE 4 y 5: EMBEDDINGS + INDEXACIÓN en FAISS
# ============================================================================

def crear_indice(
    chunks: List[Document],
    api_key: str = None,
    persistir: bool = True
) -> FAISS:
    """
    Genera embeddings y crea el índice FAISS.
    
    Args:
        chunks: Lista de chunks con metadata.
        api_key: OpenAI API key.
        persistir: Si True, guarda el índice en disco.
    
    Returns:
        Vector store FAISS listo para consultas.
    """
    global _vector_store
    
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    
    if not api_key:
        raise ValueError("Se requiere OPENAI_API_KEY para generar embeddings")
    
    print(f"\n🔄 Generando embeddings con {EMBEDDING_MODEL}...")
    
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=api_key,
    )
    
    _vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )
    
    print(f"✅ Índice FAISS creado con {len(chunks)} vectores")
    
    # Persistir en disco
    if persistir:
        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        _vector_store.save_local(FAISS_INDEX_DIR)
        print(f"💾 Índice guardado en: {FAISS_INDEX_DIR}")
    
    return _vector_store


def cargar_indice(api_key: str = None) -> Optional[FAISS]:
    """
    Carga un índice FAISS previamente guardado en disco.
    
    Returns:
        Vector store FAISS o None si no existe.
    """
    global _vector_store
    
    if not os.path.exists(FAISS_INDEX_DIR):
        return None
    
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    
    try:
        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=api_key,
        )
        
        _vector_store = FAISS.load_local(
            FAISS_INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        print(f"✅ Índice FAISS cargado desde disco")
        return _vector_store
    
    except Exception as e:
        print(f"⚠️ Error al cargar índice: {e}")
        return None


# ============================================================================
# FASE 6: RECUPERACIÓN - Retriever con filtros
# ============================================================================

def buscar_normativa(
    query: str,
    k: int = 4,
    filtro_topic: str = None,
    filtro_content_type: str = None,
) -> List[Dict]:
    """
    Busca fragmentos relevantes en la base de conocimiento.
    
    Args:
        query: Consulta del auditor.
        k: Número de fragmentos a recuperar.
        filtro_topic: Filtrar por tema específico.
        filtro_content_type: Filtrar por tipo de contenido.
    
    Returns:
        Lista de diccionarios con contenido, fuente y metadata.
    """
    global _vector_store
    
    if _vector_store is None:
        return [{
            "contenido": "⚠️ La base de conocimiento no está cargada.",
            "fuente": "Sistema",
            "seccion": "",
            "topic": "",
            "relevancia": 0,
        }]
    
    # Construir filtros de metadata si se especifican
    filter_dict = {}
    if filtro_topic:
        filter_dict["topic"] = filtro_topic
    if filtro_content_type:
        filter_dict["content_type"] = filtro_content_type
    
    try:
        # Búsqueda por similitud con scores
        if filter_dict:
            resultados = _vector_store.similarity_search_with_score(
                query, k=k, filter=filter_dict
            )
        else:
            resultados = _vector_store.similarity_search_with_score(
                query, k=k
            )
        
        fragmentos = []
        for doc, score in resultados:
            fragmentos.append({
                "contenido": doc.page_content,
                "fuente": doc.metadata.get("document_name", "Desconocido"),
                "source_file": doc.metadata.get("source", ""),
                "seccion": doc.metadata.get("section", ""),
                "topic": doc.metadata.get("topic", ""),
                "content_type": doc.metadata.get("content_type", ""),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "relevancia": round(1 / (1 + score), 4),  # Convertir distancia a score
            })
        
        return fragmentos
    
    except Exception as e:
        return [{
            "contenido": f"❌ Error en la búsqueda: {str(e)}",
            "fuente": "Sistema",
            "seccion": "",
            "topic": "",
            "relevancia": 0,
        }]


def obtener_vector_store() -> Optional[FAISS]:
    """Retorna el vector store global."""
    return _vector_store


def obtener_inventario() -> List[Dict]:
    """
    Retorna el inventario de fuentes de la base de conocimiento.
    Útil para mostrar al auditor qué documentos están disponibles.
    """
    archivos = glob.glob(os.path.join(KNOWLEDGE_BASE_DIR, "*.md")) + glob.glob(os.path.join(KNOWLEDGE_BASE_DIR, "*.pdf"))
    inventario = []
    
    for archivo in archivos:
        nombre = os.path.basename(archivo)
        content_type, topic = _clasificar_documento(nombre)
        
        try:
            tamaño = os.path.getsize(archivo)
        except Exception:
            tamaño = 0
        
        inventario.append({
            "archivo": nombre,
            "nombre": nombre.replace(".md", "").replace(".pdf", "").replace("_", " "),
            "tipo": content_type,
            "tema": topic,
            "caracteres": tamaño,
        })
    
    return inventario


# ============================================================================
# PIPELINE COMPLETO - Ejecutar todo el proceso
# ============================================================================

def ejecutar_pipeline_completo(api_key: str = None, force: bool = False) -> str:
    """
    Ejecuta el pipeline RAG completo:
    1. Ingesta → 2. Limpieza → 3. Fragmentación → 4. Embeddings → 5. Indexación
    
    Args:
        api_key: OpenAI API key.
        force: Si True, recrea el índice aunque ya exista.
    
    Returns:
        Mensaje de resultado.
    """
    # Verificar si ya existe un índice
    if not force and os.path.exists(FAISS_INDEX_DIR):
        vs = cargar_indice(api_key)
        if vs is not None:
            return "✅ Índice RAG cargado desde disco (ya existía)"
    
    print("\n" + "=" * 60)
    print("  PIPELINE RAG - FORENSIA")
    print("=" * 60)
    
    # Fase 1: Ingesta
    print("\n📂 FASE 1: Ingesta de documentos...")
    documentos = cargar_documentos()
    
    if not documentos:
        return "❌ No se encontraron documentos en la base de conocimiento"
    
    # Fase 2: Limpieza
    print("\n🧹 FASE 2: Limpieza y normalización...")
    docs_limpios = limpiar_documentos(documentos)
    
    # Fase 3: Fragmentación
    print("\n✂️ FASE 3: Fragmentación con metadata...")
    chunks = fragmentar_documentos(docs_limpios)
    
    # Fases 4 y 5: Embeddings + Indexación
    print("\n🔢 FASES 4-5: Embeddings + Indexación FAISS...")
    crear_indice(chunks, api_key)
    
    resumen = (
        f"✅ Pipeline RAG completado:\n"
        f"   📚 Documentos cargados: {len(documentos)}\n"
        f"   📄 Chunks generados: {len(chunks)}\n"
        f"   🔢 Modelo de embeddings: {EMBEDDING_MODEL}\n"
        f"   💾 Vector store: FAISS (local)\n"
        f"   📏 Chunk size: {CHUNK_SIZE} | Overlap: {CHUNK_OVERLAP}"
    )
    
    print(f"\n{resumen}")
    return resumen


# ============================================================================
# EJECUCIÓN DIRECTA (para testing)
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    resultado = ejecutar_pipeline_completo(force=True)
    print(f"\n{resultado}")
    
    # Test de búsqueda
    print("\n" + "=" * 60)
    print("  TEST DE BÚSQUEDA")
    print("=" * 60)
    
    queries_test = [
        "¿Qué es el triángulo del fraude?",
        "¿Cuáles son los niveles de autorización de compras?",
        "¿Qué dice la Ley de Benford?",
        "¿Qué es la segregación de funciones?",
    ]
    
    for q in queries_test:
        print(f"\n🔍 Query: {q}")
        resultados = buscar_normativa(q, k=2)
        for r in resultados:
            print(f"   📄 [{r['fuente']}] Sección: {r['seccion']}")
            print(f"   📊 Relevancia: {r['relevancia']}")
            print(f"   📝 {r['contenido'][:150]}...")
            print()
