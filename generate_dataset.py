"""
============================================================================
GENERADOR DE DATASET SINTÉTICO - AUDITORÍA FORENSE
Proyecto: Agente de Detección de Fraude en Transacciones
============================================================================
Este script genera un dataset realista de transacciones empresariales
con múltiples tipos de fraude sembrados para demostración.

Tipos de fraude incluidos:
1. Fraccionamiento de compras (structuring/smurfing)
2. Proveedores fantasma (shell companies)
3. Transacciones duplicadas
4. Transacciones fuera de horario laboral
5. Sobrefacturación
6. Conflicto de interés (auto-aprobación)
7. Pagos a proveedores no autorizados
8. Lavado de activos (layering)
9. Gastos ficticios de viaje
10. Manipulación de notas de crédito
============================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import string
import os

# Semilla para reproducibilidad
np.random.seed(42)
random.seed(42)

# ============================================================================
# CONFIGURACIÓN GENERAL
# ============================================================================

NUM_TRANSACCIONES_NORMALES = 8500
NUM_FRAUDES = 1500  # ~15% del total, realista para un dataset de auditoría
FECHA_INICIO = datetime(2024, 1, 1)
FECHA_FIN = datetime(2024, 12, 31)

# ============================================================================
# CATÁLOGOS MAESTROS
# ============================================================================

# Departamentos de la empresa
DEPARTAMENTOS = [
    "Finanzas", "Operaciones", "Recursos Humanos", "Tecnología",
    "Ventas", "Marketing", "Legal", "Logística", "Compras",
    "Administración", "Producción", "Calidad"
]

# Categorías de gasto
CATEGORIAS = [
    "Servicios Profesionales", "Suministros de Oficina", "Tecnología y Software",
    "Viáticos y Viajes", "Mantenimiento", "Materia Prima", "Publicidad",
    "Capacitación", "Seguros", "Transporte y Logística", "Alquiler de Equipos",
    "Consultoría Externa", "Servicios de Limpieza", "Seguridad",
    "Telecomunicaciones", "Utilities", "Gastos de Representación"
]

# Proveedores legítimos (60 proveedores)
PROVEEDORES_LEGITIMOS = [
    {"id": f"PROV-{str(i).zfill(4)}", "nombre": nombre, "ruc": f"20{random.randint(100000000, 999999999)}", "categoria": cat}
    for i, (nombre, cat) in enumerate([
        ("Tech Solutions SAC", "Tecnología y Software"),
        ("Grupo Logístico del Norte", "Transporte y Logística"),
        ("Servicios Industriales Perú", "Mantenimiento"),
        ("Distribuidora Nacional SAC", "Materia Prima"),
        ("Consultora Estratégica Lima", "Consultoría Externa"),
        ("Office Depot Perú", "Suministros de Oficina"),
        ("Global Training Corp", "Capacitación"),
        ("Marketing Digital Perú", "Publicidad"),
        ("Seguridad Total SAC", "Seguridad"),
        ("Clean Services Perú", "Servicios de Limpieza"),
        ("Telefónica del Perú", "Telecomunicaciones"),
        ("Luz del Sur", "Utilities"),
        ("Seguros Pacífico", "Seguros"),
        ("Transportes Cruz del Sur", "Transporte y Logística"),
        ("Constructora Los Andes", "Mantenimiento"),
        ("Proveedora Industrial Lima", "Materia Prima"),
        ("DataCenter Perú SAC", "Tecnología y Software"),
        ("Catering Gourmet Lima", "Gastos de Representación"),
        ("Imprenta Nacional SAC", "Suministros de Oficina"),
        ("Laboratorios QA Perú", "Calquiler de Equipos"),
        ("Asesoría Legal Corp", "Servicios Profesionales"),
        ("Mantenimiento Express", "Mantenimiento"),
        ("Software Factory SAC", "Tecnología y Software"),
        ("Courier Express Perú", "Transporte y Logística"),
        ("Capacitaciones Pro SAC", "Capacitación"),
        ("Suministros del Pacífico", "Materia Prima"),
        ("Energía Verde SAC", "Utilities"),
        ("Publicidad Creativa SAC", "Publicidad"),
        ("Consulting Group Perú", "Consultoría Externa"),
        ("Alquiler de Equipos SAC", "Alquiler de Equipos"),
        ("Protección y Vigilancia", "Seguridad"),
        ("Servicios TI del Sur", "Tecnología y Software"),
        ("Transportes Rápidos SAC", "Transporte y Logística"),
        ("Materiales Premium SAC", "Materia Prima"),
        ("Asesoría Tributaria Lima", "Servicios Profesionales"),
        ("Red de Comunicaciones SAC", "Telecomunicaciones"),
        ("Fumigaciones Perú SAC", "Servicios de Limpieza"),
        ("Eventos Corporativos SAC", "Gastos de Representación"),
        ("Papelería Central SAC", "Suministros de Oficina"),
        ("Ingeniería Aplicada SAC", "Mantenimiento"),
        ("Cloud Services Perú", "Tecnología y Software"),
        ("Logística Integral SAC", "Transporte y Logística"),
        ("Alimentos del Valle SAC", "Gastos de Representación"),
        ("Ferretería Industrial SAC", "Materia Prima"),
        ("Diseño Gráfico Pro SAC", "Publicidad"),
        ("Academia Empresarial SAC", "Capacitación"),
        ("Seguros Continental", "Seguros"),
        ("Electricidad Total SAC", "Mantenimiento"),
        ("Textiles Industriales SAC", "Materia Prima"),
        ("Auditoría y Control SAC", "Servicios Profesionales"),
        ("Mobiliario Corporativo SAC", "Suministros de Oficina"),
        ("Agencia de Viajes Corp", "Viáticos y Viajes"),
        ("Hotel Business Lima", "Viáticos y Viajes"),
        ("Aerolíneas del Pacífico", "Viáticos y Viajes"),
        ("Rent a Car Ejecutivo", "Viáticos y Viajes"),
        ("Restaurante Ejecutivo SAC", "Gastos de Representación"),
        ("Servicio de Traducción SAC", "Servicios Profesionales"),
        ("Pinturas Industriales SAC", "Mantenimiento"),
        ("Repuestos Mecánicos SAC", "Mantenimiento"),
        ("Uniformes Corp SAC", "Suministros de Oficina"),
    ], start=1)
]

# Proveedores fantasma (para fraude)
PROVEEDORES_FANTASMA = [
    {"id": "PROV-9001", "nombre": "Soluciones Integrales XYZ EIRL", "ruc": "20612345678", "categoria": "Consultoría Externa"},
    {"id": "PROV-9002", "nombre": "Inversiones y Proyectos JML SAC", "ruc": "20698765432", "categoria": "Servicios Profesionales"},
    {"id": "PROV-9003", "nombre": "Corporación Nexus Global SAC", "ruc": "20687654321", "categoria": "Tecnología y Software"},
    {"id": "PROV-9004", "nombre": "Servicios Generales M&R EIRL", "ruc": "20676543210", "categoria": "Mantenimiento"},
    {"id": "PROV-9005", "nombre": "Trading Internacional ABC SAC", "ruc": "20665432109", "categoria": "Materia Prima"},
    {"id": "PROV-9006", "nombre": "Consultores Asociados del Perú EIRL", "ruc": "20654321098", "categoria": "Consultoría Externa"},
    {"id": "PROV-9007", "nombre": "Grupo Empresarial Fénix SAC", "ruc": "20643210987", "categoria": "Servicios Profesionales"},
    {"id": "PROV-9008", "nombre": "Soluciones Tech Avanzadas EIRL", "ruc": "20632109876", "categoria": "Tecnología y Software"},
]

# Empleados autorizadores
EMPLEADOS = [
    {"id": f"EMP-{str(i).zfill(3)}", "nombre": nombre, "cargo": cargo, "departamento": dept, "nivel_aprobacion": nivel}
    for i, (nombre, cargo, dept, nivel) in enumerate([
        ("Carlos Mendoza", "Gerente de Finanzas", "Finanzas", 50000),
        ("María García", "Jefe de Compras", "Compras", 25000),
        ("Roberto Silva", "Director de Operaciones", "Operaciones", 100000),
        ("Ana Torres", "Gerente de TI", "Tecnología", 40000),
        ("Luis Ramírez", "Jefe de Logística", "Logística", 20000),
        ("Patricia Flores", "Gerente de RRHH", "Recursos Humanos", 30000),
        ("Jorge Castillo", "Jefe de Marketing", "Marketing", 25000),
        ("Daniela Vega", "Coordinador de Compras", "Compras", 10000),
        ("Fernando Rojas", "Analista de Finanzas", "Finanzas", 5000),
        ("Sofía Herrera", "Asistente Administrativo", "Administración", 3000),
        ("Miguel Paredes", "Jefe de Producción", "Producción", 20000),
        ("Claudia Ríos", "Gerente Legal", "Legal", 35000),
        ("Ricardo Luna", "Director General", "Administración", 200000),
        ("Andrea Salazar", "Jefe de Calidad", "Calidad", 15000),
        ("Pedro Gutiérrez", "Coordinador de Ventas", "Ventas", 15000),
        ("Valeria Morales", "Analista de Compras", "Compras", 5000),
        ("Héctor Díaz", "Jefe de Mantenimiento", "Operaciones", 15000),
        ("Lucía Campos", "Coordinadora de RRHH", "Recursos Humanos", 10000),
        ("Alberto Vargas", "Gerente de Ventas", "Ventas", 40000),
        ("Carmen Delgado", "Asistente de Gerencia", "Administración", 5000),
    ], start=1)
]

# Métodos de pago
METODOS_PAGO = ["Transferencia Bancaria", "Cheque", "Tarjeta Corporativa", "Efectivo", "Letra de Cambio"]

# Centros de costo
CENTROS_COSTO = [
    "CC-001 Administración General", "CC-002 Producción Planta 1",
    "CC-003 Producción Planta 2", "CC-004 Ventas Nacional",
    "CC-005 Ventas Internacional", "CC-006 Investigación y Desarrollo",
    "CC-007 Almacén Central", "CC-008 Transporte",
    "CC-009 Sistemas", "CC-010 Recursos Humanos"
]

# Cuentas contables
CUENTAS_CONTABLES = {
    "Servicios Profesionales": "6320 - Honorarios Profesionales",
    "Suministros de Oficina": "6560 - Suministros Diversos",
    "Tecnología y Software": "6340 - Servicios de TI",
    "Viáticos y Viajes": "6310 - Viáticos y Gastos de Viaje",
    "Mantenimiento": "6350 - Mantenimiento y Reparaciones",
    "Materia Prima": "6110 - Materias Primas",
    "Publicidad": "6370 - Publicidad y Marketing",
    "Capacitación": "6330 - Capacitación del Personal",
    "Seguros": "6520 - Seguros",
    "Transporte y Logística": "6360 - Transporte y Flete",
    "Alquiler de Equipos": "6540 - Alquileres",
    "Consultoría Externa": "6325 - Consultoría",
    "Servicios de Limpieza": "6355 - Servicios de Limpieza",
    "Seguridad": "6380 - Seguridad y Vigilancia",
    "Telecomunicaciones": "6390 - Comunicaciones",
    "Utilities": "6510 - Servicios Públicos",
    "Gastos de Representación": "6315 - Gastos de Representación",
}

# Monedas
MONEDAS = ["PEN", "USD"]

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generar_numero_factura(prefijo="F"):
    """Genera número de factura realista"""
    serie = random.choice(["F001", "F002", "F003", "E001", "E002"])
    numero = random.randint(1, 99999999)
    return f"{serie}-{str(numero).zfill(8)}"

def generar_numero_oc():
    """Genera número de orden de compra"""
    return f"OC-{random.randint(2024001, 2024999)}"

def generar_fecha_aleatoria(inicio, fin, horario_laboral=True):
    """Genera fecha aleatoria con opción de horario laboral"""
    delta = fin - inicio
    dias = random.randint(0, delta.days)
    fecha = inicio + timedelta(days=dias)
    
    if horario_laboral:
        hora = random.randint(8, 18)
        minuto = random.randint(0, 59)
    else:
        # Fuera de horario
        hora = random.choice([*range(0, 7), *range(20, 24)])
        minuto = random.randint(0, 59)
    
    return fecha.replace(hour=hora, minute=minuto, second=random.randint(0, 59))

def generar_monto_normal(categoria):
    """Genera montos realistas según categoría"""
    rangos = {
        "Servicios Profesionales": (500, 15000),
        "Suministros de Oficina": (50, 3000),
        "Tecnología y Software": (200, 25000),
        "Viáticos y Viajes": (100, 8000),
        "Mantenimiento": (200, 12000),
        "Materia Prima": (1000, 50000),
        "Publicidad": (500, 20000),
        "Capacitación": (300, 10000),
        "Seguros": (1000, 15000),
        "Transporte y Logística": (300, 8000),
        "Alquiler de Equipos": (500, 10000),
        "Consultoría Externa": (1000, 20000),
        "Servicios de Limpieza": (200, 3000),
        "Seguridad": (500, 8000),
        "Telecomunicaciones": (100, 5000),
        "Utilities": (200, 8000),
        "Gastos de Representación": (100, 5000),
    }
    rango = rangos.get(categoria, (100, 10000))
    return round(np.random.lognormal(mean=np.log(np.mean(rango)), sigma=0.5), 2)

# ============================================================================
# GENERACIÓN DE TRANSACCIONES NORMALES
# ============================================================================

def generar_transacciones_normales(n):
    """Genera n transacciones legítimas"""
    transacciones = []
    
    for i in range(n):
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        empleado = random.choice(EMPLEADOS)
        categoria = proveedor["categoria"]
        moneda = random.choices(MONEDAS, weights=[0.7, 0.3])[0]
        monto = generar_monto_normal(categoria)
        
        # Limitar monto al nivel de aprobación del empleado (con excepciones normales)
        if monto > empleado["nivel_aprobacion"] and random.random() > 0.05:
            monto = round(random.uniform(100, empleado["nivel_aprobacion"] * 0.8), 2)
        
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, horario_laboral=True)
        
        # Días hábiles principalmente
        while fecha.weekday() >= 5 and random.random() > 0.03:
            fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, horario_laboral=True)
        
        igv = round(monto * 0.18, 2)
        monto_total = round(monto + igv, 2)
        
        transacciones.append({
            "transaction_id": f"TXN-{str(i+1).zfill(6)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": categoria,
            "cuenta_contable": CUENTAS_CONTABLES.get(categoria, "6999 - Otros"),
            "descripcion": generar_descripcion(categoria),
            "monto_base": monto,
            "igv": igv,
            "monto_total": monto_total,
            "moneda": moneda,
            "tipo_cambio": round(random.uniform(3.65, 3.85), 4) if moneda == "USD" else 1.0,
            "metodo_pago": random.choices(METODOS_PAGO, weights=[0.45, 0.25, 0.15, 0.05, 0.10])[0],
            "numero_factura": generar_numero_factura(),
            "numero_oc": generar_numero_oc(),
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": random.choices(["Aprobada", "Pendiente", "Rechazada"], weights=[0.85, 0.10, 0.05])[0],
            "es_fraude": 0,
            "tipo_fraude": "Ninguno",
            "riesgo_score": round(random.uniform(0, 0.25), 4),
            "notas": ""
        })
    
    return transacciones

def generar_descripcion(categoria):
    """Genera descripción realista de transacción"""
    descripciones = {
        "Servicios Profesionales": [
            "Honorarios por asesoría contable mensual",
            "Servicios de auditoría externa Q{q}".format(q=random.randint(1,4)),
            "Consultoría en gestión empresarial",
            "Servicios legales - revisión de contratos",
            "Asesoría tributaria mensual",
            "Peritaje técnico especializado",
        ],
        "Suministros de Oficina": [
            "Papel bond A4 - 50 millares",
            "Tóner para impresoras HP",
            "Material de escritorio variado",
            "Folders y archivadores",
            "Útiles de oficina - pedido mensual",
            "Cartuchos de tinta y papel fotográfico",
        ],
        "Tecnología y Software": [
            "Licencias Microsoft 365 - renovación anual",
            "Servidor Dell PowerEdge - adquisición",
            "Soporte técnico mensual infraestructura",
            "Licencias SAP - módulo financiero",
            "Equipos de cómputo - 5 laptops",
            "Renovación licencias antivirus corporativo",
            "Desarrollo de módulo ERP personalizado",
        ],
        "Viáticos y Viajes": [
            "Pasajes aéreos Lima-Arequipa - equipo de ventas",
            "Hospedaje Hotel Business - conferencia",
            "Viáticos nacionales - auditoría de planta",
            "Pasajes terrestres equipo de supervisión",
            "Alquiler de vehículo - visita a clientes",
            "Gastos de alimentación - viaje corporativo",
        ],
        "Mantenimiento": [
            "Mantenimiento preventivo maquinaria Planta 1",
            "Reparación de sistema eléctrico - oficina central",
            "Mantenimiento de aires acondicionados",
            "Pintura y refacción de oficinas",
            "Reparación de montacargas",
            "Mantenimiento de grupo electrógeno",
        ],
        "Materia Prima": [
            "Acero inoxidable - lote producción",
            "Componentes electrónicos - pedido mensual",
            "Insumos químicos para producción",
            "Material de empaque - cajas y cintas",
            "Telas industriales - orden de producción",
            "Resinas y polímeros - lote Q{q}".format(q=random.randint(1,4)),
        ],
        "Publicidad": [
            "Campaña digital - redes sociales Q{q}".format(q=random.randint(1,4)),
            "Diseño e impresión de brochures corporativos",
            "Pauta publicitaria en medios digitales",
            "Producción de video institucional",
            "Material POP para feria comercial",
        ],
        "Capacitación": [
            "Curso de liderazgo - personal gerencial",
            "Capacitación en seguridad industrial",
            "Taller de Excel avanzado - equipo financiero",
            "Certificación PMP - 3 colaboradores",
            "Diplomado en gestión de proyectos",
        ],
        "Seguros": [
            "Póliza de seguro patrimonial - renovación",
            "Seguro de responsabilidad civil",
            "Seguro vehicular - flota corporativa",
            "Seguro SCTR - personal de planta",
            "Póliza de seguro de vida grupal",
        ],
        "Transporte y Logística": [
            "Flete terrestre Lima-Trujillo - mercadería",
            "Servicio de courier - envíos corporativos",
            "Transporte de personal - ruta norte",
            "Almacenaje temporal - despacho pendiente",
            "Servicio de mudanza - reubicación de oficina",
        ],
        "Alquiler de Equipos": [
            "Alquiler de grúa - proyecto construcción",
            "Alquiler de equipos de cómputo - evento",
            "Arrendamiento de maquinaria pesada",
            "Alquiler de equipos audiovisuales",
        ],
        "Consultoría Externa": [
            "Consultoría en transformación digital",
            "Estudio de mercado - expansión regional",
            "Consultoría en procesos de calidad ISO",
            "Asesoría en implementación de ERP",
            "Diagnóstico organizacional",
        ],
        "Servicios de Limpieza": [
            "Servicio de limpieza mensual - sede principal",
            "Fumigación trimestral de oficinas",
            "Limpieza profunda - planta de producción",
            "Servicio de desinfección COVID",
        ],
        "Seguridad": [
            "Servicio de vigilancia mensual",
            "Instalación de cámaras de seguridad",
            "Monitoreo 24/7 - central de alarmas",
            "Servicio de resguardo - transporte de valores",
        ],
        "Telecomunicaciones": [
            "Servicio de internet corporativo - mensual",
            "Plan de telefonía móvil corporativa",
            "Enlace dedicado de datos - sede principal",
            "Servicio de videoconferencia empresarial",
        ],
        "Utilities": [
            "Servicio de electricidad - sede principal",
            "Servicio de agua - planta de producción",
            "Gas natural - planta industrial",
            "Energía eléctrica - almacén central",
        ],
        "Gastos de Representación": [
            "Almuerzo ejecutivo con clientes",
            "Cena de cierre de negociación",
            "Coffee break - reunión de directorio",
            "Evento de integración corporativa",
            "Atención a delegación extranjera",
        ],
    }
    opciones = descripciones.get(categoria, ["Servicio general"])
    return random.choice(opciones)

# ============================================================================
# GENERACIÓN DE FRAUDES
# ============================================================================

def generar_fraudes_fraccionamiento(base_id):
    """
    FRAUDE 1: Fraccionamiento de compras (Structuring)
    Dividir una compra grande en múltiples compras pequeñas para
    evadir el límite de aprobación.
    """
    fraudes = []
    empleado_fraudulento = EMPLEADOS[7]  # Daniela Vega - Coordinador de Compras (límite 10,000)
    
    # 8 casos de fraccionamiento
    for caso in range(8):
        monto_real = random.uniform(15000, 45000)
        num_partes = random.randint(3, 6)
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        fecha_base = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        for parte in range(num_partes):
            monto_fraccion = round(monto_real / num_partes + random.uniform(-200, 200), 2)
            # Asegurar que cada fracción esté bajo el límite
            monto_fraccion = min(monto_fraccion, 9800)
            igv = round(monto_fraccion * 0.18, 2)
            fecha = fecha_base + timedelta(days=random.randint(0, 3))
            
            fraudes.append({
                "transaction_id": f"TXN-F1-{str(base_id).zfill(4)}",
                "fecha": fecha.strftime("%Y-%m-%d"),
                "hora": generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, True).strftime("%H:%M:%S"),
                "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
                "proveedor_id": proveedor["id"],
                "proveedor_nombre": proveedor["nombre"],
                "proveedor_ruc": proveedor["ruc"],
                "categoria": proveedor["categoria"],
                "cuenta_contable": CUENTAS_CONTABLES.get(proveedor["categoria"], "6999 - Otros"),
                "descripcion": f"Compra fraccionada - parte {parte+1}/{num_partes}",
                "monto_base": monto_fraccion,
                "igv": igv,
                "monto_total": round(monto_fraccion + igv, 2),
                "moneda": "PEN",
                "tipo_cambio": 1.0,
                "metodo_pago": "Transferencia Bancaria",
                "numero_factura": generar_numero_factura(),
                "numero_oc": generar_numero_oc(),
                "centro_costo": random.choice(CENTROS_COSTO),
                "departamento": "Compras",
                "autorizado_por_id": empleado_fraudulento["id"],
                "autorizado_por": empleado_fraudulento["nombre"],
                "cargo_autorizador": empleado_fraudulento["cargo"],
                "nivel_aprobacion": empleado_fraudulento["nivel_aprobacion"],
                "estado": "Aprobada",
                "es_fraude": 1,
                "tipo_fraude": "Fraccionamiento de compras",
                "riesgo_score": round(random.uniform(0.75, 0.95), 4),
                "notas": f"Grupo de fraccionamiento #{caso+1}. Monto real estimado: S/. {monto_real:,.2f}"
            })
            base_id += 1
    
    return fraudes, base_id

def generar_fraudes_proveedores_fantasma(base_id):
    """
    FRAUDE 2: Proveedores Fantasma (Shell Companies)
    Pagos a empresas ficticias controladas por empleados internos.
    """
    fraudes = []
    # Empleados involucrados en el esquema
    empleados_complices = [EMPLEADOS[0], EMPLEADOS[1]]  # Carlos Mendoza y María García
    
    for _ in range(60):
        fantasma = random.choice(PROVEEDORES_FANTASMA)
        complice = random.choice(empleados_complices)
        monto = round(random.uniform(3000, 25000), 2)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        fraudes.append({
            "transaction_id": f"TXN-F2-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": fantasma["id"],
            "proveedor_nombre": fantasma["nombre"],
            "proveedor_ruc": fantasma["ruc"],
            "categoria": fantasma["categoria"],
            "cuenta_contable": CUENTAS_CONTABLES.get(fantasma["categoria"], "6999 - Otros"),
            "descripcion": random.choice([
                "Servicios de consultoría especializada",
                "Asesoría en gestión de proyectos",
                "Informe de análisis de mercado",
                "Estudio de factibilidad técnica",
                "Desarrollo de plan estratégico",
                "Servicios profesionales diversos",
                "Consultoría en optimización de procesos",
                "Análisis de riesgos operativos",
            ]),
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": random.choice(["Transferencia Bancaria", "Cheque"]),
            "numero_factura": generar_numero_factura(),
            "numero_oc": generar_numero_oc(),
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": complice["departamento"],
            "autorizado_por_id": complice["id"],
            "autorizado_por": complice["nombre"],
            "cargo_autorizador": complice["cargo"],
            "nivel_aprobacion": complice["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Proveedor fantasma",
            "riesgo_score": round(random.uniform(0.85, 0.99), 4),
            "notas": f"Proveedor fantasma: {fantasma['nombre']}. RUC sospechoso: {fantasma['ruc']}"
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_duplicados(base_id):
    """
    FRAUDE 3: Transacciones Duplicadas
    Pagos duplicados al mismo proveedor por el mismo concepto.
    """
    fraudes = []
    
    for _ in range(40):
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        empleado = random.choice(EMPLEADOS)
        monto = round(random.uniform(1000, 15000), 2)
        igv = round(monto * 0.18, 2)
        factura = generar_numero_factura()
        oc = generar_numero_oc()
        descripcion = generar_descripcion(proveedor["categoria"])
        fecha_base = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        # Crear la transacción original y su duplicado
        for dup in range(2):
            fecha = fecha_base + timedelta(days=random.randint(0, 5)) if dup == 1 else fecha_base
            
            fraudes.append({
                "transaction_id": f"TXN-F3-{str(base_id).zfill(4)}",
                "fecha": fecha.strftime("%Y-%m-%d"),
                "hora": generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, True).strftime("%H:%M:%S"),
                "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
                "proveedor_id": proveedor["id"],
                "proveedor_nombre": proveedor["nombre"],
                "proveedor_ruc": proveedor["ruc"],
                "categoria": proveedor["categoria"],
                "cuenta_contable": CUENTAS_CONTABLES.get(proveedor["categoria"], "6999 - Otros"),
                "descripcion": descripcion,
                "monto_base": monto,
                "igv": igv,
                "monto_total": round(monto + igv, 2),
                "moneda": "PEN",
                "tipo_cambio": 1.0,
                "metodo_pago": "Transferencia Bancaria",
                "numero_factura": factura,  # Misma factura = duplicado
                "numero_oc": oc,
                "centro_costo": random.choice(CENTROS_COSTO),
                "departamento": empleado["departamento"],
                "autorizado_por_id": empleado["id"],
                "autorizado_por": empleado["nombre"],
                "cargo_autorizador": empleado["cargo"],
                "nivel_aprobacion": empleado["nivel_aprobacion"],
                "estado": "Aprobada",
                "es_fraude": 1,
                "tipo_fraude": "Transacción duplicada",
                "riesgo_score": round(random.uniform(0.70, 0.90), 4),
                "notas": f"Factura duplicada: {factura}. Posible doble pago."
            })
            base_id += 1
    
    return fraudes, base_id

def generar_fraudes_horario(base_id):
    """
    FRAUDE 4: Transacciones fuera de horario laboral
    Aprobaciones en madrugada, fines de semana o feriados.
    """
    fraudes = []
    
    for _ in range(80):
        proveedor = random.choice(PROVEEDORES_LEGITIMOS + PROVEEDORES_FANTASMA[:3])
        empleado = random.choice(EMPLEADOS[:5])
        monto = round(random.uniform(2000, 20000), 2)
        igv = round(monto * 0.18, 2)
        
        # Generar fecha fuera de horario
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, horario_laboral=False)
        # Algunos en fines de semana
        if random.random() > 0.5:
            while fecha.weekday() < 5:
                fecha += timedelta(days=1)
        
        fraudes.append({
            "transaction_id": f"TXN-F4-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"] if isinstance(proveedor, dict) else proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": proveedor["categoria"],
            "cuenta_contable": CUENTAS_CONTABLES.get(proveedor["categoria"], "6999 - Otros"),
            "descripcion": generar_descripcion(proveedor["categoria"]) if proveedor["id"][:8] != "PROV-900" else "Servicio urgente no programado",
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": random.choice(MONEDAS),
            "tipo_cambio": round(random.uniform(3.65, 3.85), 4) if random.random() > 0.5 else 1.0,
            "metodo_pago": random.choice(["Transferencia Bancaria", "Cheque"]),
            "numero_factura": generar_numero_factura(),
            "numero_oc": generar_numero_oc(),
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Transacción fuera de horario",
            "riesgo_score": round(random.uniform(0.60, 0.85), 4),
            "notas": f"Transacción registrada fuera de horario laboral: {fecha.strftime('%H:%M')} - {fecha.strftime('%A')}"
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_sobrefacturacion(base_id):
    """
    FRAUDE 5: Sobrefacturación
    Montos inflados significativamente respecto al valor de mercado.
    """
    fraudes = []
    
    items_sobrefacturados = [
        ("Suministros de Oficina", "Papel bond A4 - 10 millares", 350, 2800),
        ("Tecnología y Software", "Licencia de software básico", 500, 8500),
        ("Mantenimiento", "Cambio de focos LED oficina", 200, 4500),
        ("Suministros de Oficina", "Tóner genérico para impresora", 80, 1200),
        ("Servicios de Limpieza", "Limpieza mensual - 1 oficina", 800, 6000),
        ("Capacitación", "Taller de Excel básico - 4 horas", 600, 5500),
        ("Mantenimiento", "Reparación de grifo - baño oficina", 150, 3200),
        ("Suministros de Oficina", "Sillas de escritorio básicas x5", 1500, 12000),
        ("Tecnología y Software", "Mouse y teclado USB x10", 300, 4800),
        ("Mantenimiento", "Pintura interior - 1 oficina 20m2", 400, 7500),
    ]
    
    for _ in range(50):
        item = random.choice(items_sobrefacturados)
        categoria, descripcion, valor_real, valor_inflado = item
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        empleado = random.choice(EMPLEADOS)
        
        monto = round(random.uniform(valor_inflado * 0.8, valor_inflado * 1.2), 2)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        fraudes.append({
            "transaction_id": f"TXN-F5-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": categoria,
            "cuenta_contable": CUENTAS_CONTABLES.get(categoria, "6999 - Otros"),
            "descripcion": f"{descripcion} [PRECIO MERCADO: ~S/.{valor_real}]",
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": random.choice(METODOS_PAGO),
            "numero_factura": generar_numero_factura(),
            "numero_oc": generar_numero_oc(),
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Sobrefacturación",
            "riesgo_score": round(random.uniform(0.70, 0.92), 4),
            "notas": f"Valor de mercado estimado: S/.{valor_real}. Monto facturado: S/.{monto:,.2f}. Sobreprecio: {((monto/valor_real)-1)*100:.0f}%"
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_conflicto_interes(base_id):
    """
    FRAUDE 6: Conflicto de Interés / Auto-aprobación
    Empleado aprueba sus propias solicitudes o de familiares.
    """
    fraudes = []
    
    for _ in range(35):
        empleado = random.choice(EMPLEADOS[:8])
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        monto = round(random.uniform(1000, empleado["nivel_aprobacion"] * 0.95), 2)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        fraudes.append({
            "transaction_id": f"TXN-F6-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": random.choice(["Gastos de Representación", "Viáticos y Viajes", "Capacitación"]),
            "cuenta_contable": "6315 - Gastos de Representación",
            "descripcion": random.choice([
                "Gastos de representación - evento no documentado",
                "Viáticos personales - destino no verificado",
                "Capacitación externa - proveedor no habitual",
                "Gastos de viaje - justificación pendiente",
                "Evento corporativo - sin lista de asistentes",
            ]),
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": random.choice(["Tarjeta Corporativa", "Efectivo"]),
            "numero_factura": generar_numero_factura(),
            "numero_oc": "",  # Sin OC = señal de alerta
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Conflicto de interés",
            "riesgo_score": round(random.uniform(0.65, 0.88), 4),
            "notas": f"Auto-aprobación detectada. Solicitante = Aprobador: {empleado['nombre']}. Sin orden de compra."
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_lavado(base_id):
    """
    FRAUDE 7: Lavado de Activos (Layering)
    Múltiples transacciones entre entidades relacionadas para ocultar origen.
    """
    fraudes = []
    
    # Crear cadenas de transacciones sospechosas
    for cadena in range(10):
        monto_base = round(random.uniform(20000, 80000), 2)
        fecha_inicio_cadena = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        fantasmas_cadena = random.sample(PROVEEDORES_FANTASMA, min(3, len(PROVEEDORES_FANTASMA)))
        
        for paso, fantasma in enumerate(fantasmas_cadena):
            monto = round(monto_base * (1 + random.uniform(-0.05, 0.05)), 2)  # Montos similares
            igv = round(monto * 0.18, 2)
            fecha = fecha_inicio_cadena + timedelta(days=paso * random.randint(1, 3))
            empleado = random.choice(EMPLEADOS[:3])
            
            fraudes.append({
                "transaction_id": f"TXN-F7-{str(base_id).zfill(4)}",
                "fecha": fecha.strftime("%Y-%m-%d"),
                "hora": generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN, True).strftime("%H:%M:%S"),
                "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
                "proveedor_id": fantasma["id"],
                "proveedor_nombre": fantasma["nombre"],
                "proveedor_ruc": fantasma["ruc"],
                "categoria": fantasma["categoria"],
                "cuenta_contable": CUENTAS_CONTABLES.get(fantasma["categoria"], "6999 - Otros"),
                "descripcion": random.choice([
                    "Servicio de intermediación comercial",
                    "Comisión por gestión de negocios",
                    "Honorarios por representación comercial",
                    "Servicios de broker - operación internacional",
                ]),
                "monto_base": monto,
                "igv": igv,
                "monto_total": round(monto + igv, 2),
                "moneda": random.choice(["PEN", "USD"]),
                "tipo_cambio": round(random.uniform(3.65, 3.85), 4),
                "metodo_pago": "Transferencia Bancaria",
                "numero_factura": generar_numero_factura(),
                "numero_oc": generar_numero_oc(),
                "centro_costo": random.choice(CENTROS_COSTO),
                "departamento": empleado["departamento"],
                "autorizado_por_id": empleado["id"],
                "autorizado_por": empleado["nombre"],
                "cargo_autorizador": empleado["cargo"],
                "nivel_aprobacion": empleado["nivel_aprobacion"],
                "estado": "Aprobada",
                "es_fraude": 1,
                "tipo_fraude": "Lavado de activos",
                "riesgo_score": round(random.uniform(0.88, 0.99), 4),
                "notas": f"Cadena de layering #{cadena+1}, paso {paso+1}. Montos similares entre entidades fantasma."
            })
            base_id += 1
    
    return fraudes, base_id

def generar_fraudes_viajes_ficticios(base_id):
    """
    FRAUDE 8: Gastos de viaje ficticios
    Reembolsos por viajes que nunca ocurrieron.
    """
    fraudes = []
    
    for _ in range(45):
        empleado = random.choice(EMPLEADOS)
        monto = round(random.uniform(800, 6000), 2)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        destinos_ficticios = [
            "Lima-Cusco (sin registro de embarque)",
            "Lima-Arequipa (hotel sin reserva confirmada)",
            "Lima-Piura (viaje no autorizado)",
            "Lima-Chiclayo (sin informe de visita)",
            "Lima-Iquitos (sin agenda de reuniones)",
        ]
        
        fraudes.append({
            "transaction_id": f"TXN-F8-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": random.choice(PROVEEDORES_LEGITIMOS[51:55])["id"],
            "proveedor_nombre": random.choice(["Agencia de Viajes Corp", "Hotel Business Lima", "Aerolíneas del Pacífico", "Rent a Car Ejecutivo"]),
            "proveedor_ruc": f"20{random.randint(100000000, 999999999)}",
            "categoria": "Viáticos y Viajes",
            "cuenta_contable": "6310 - Viáticos y Gastos de Viaje",
            "descripcion": f"Reembolso viáticos - {random.choice(destinos_ficticios)}",
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": random.choice(["Efectivo", "Tarjeta Corporativa"]),
            "numero_factura": generar_numero_factura(),
            "numero_oc": "",
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Gastos de viaje ficticios",
            "riesgo_score": round(random.uniform(0.60, 0.85), 4),
            "notas": "Viaje sin documentación de soporte completa. Sin boarding pass ni informe de actividades."
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_notas_credito(base_id):
    """
    FRAUDE 9: Manipulación de notas de crédito
    Notas de crédito ficticias para desviar fondos.
    """
    fraudes = []
    
    for _ in range(30):
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        empleado = random.choice(EMPLEADOS[:5])
        monto = round(random.uniform(2000, 15000), 2)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        fraudes.append({
            "transaction_id": f"TXN-F9-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": proveedor["categoria"],
            "cuenta_contable": CUENTAS_CONTABLES.get(proveedor["categoria"], "6999 - Otros"),
            "descripcion": random.choice([
                "Nota de crédito - devolución sin registro de ingreso",
                "Nota de crédito - ajuste de precio retroactivo",
                "Nota de crédito - descuento no pactado en contrato",
                "Nota de crédito - anulación parcial sin sustento",
            ]),
            "monto_base": -monto,  # Negativo por ser nota de crédito
            "igv": -igv,
            "monto_total": round(-(monto + igv), 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": "Nota de Crédito",
            "numero_factura": f"NC01-{str(random.randint(1,99999999)).zfill(8)}",
            "numero_oc": "",
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Manipulación de notas de crédito",
            "riesgo_score": round(random.uniform(0.72, 0.93), 4),
            "notas": "Nota de crédito sin documentación de devolución física. Sin aprobación de almacén."
        })
        base_id += 1
    
    return fraudes, base_id

def generar_fraudes_montos_umbral(base_id):
    """
    FRAUDE 10: Montos justo debajo del umbral de aprobación
    Transacciones diseñadas para estar justo debajo del límite.
    """
    fraudes = []
    umbrales = [3000, 5000, 10000, 15000, 20000, 25000]
    
    for _ in range(50):
        umbral = random.choice(umbrales)
        # Monto entre 90% y 99.5% del umbral
        monto = round(umbral * random.uniform(0.90, 0.995), 2)
        proveedor = random.choice(PROVEEDORES_LEGITIMOS)
        empleado = [e for e in EMPLEADOS if e["nivel_aprobacion"] >= umbral]
        if not empleado:
            empleado = [EMPLEADOS[0]]
        empleado = random.choice(empleado)
        igv = round(monto * 0.18, 2)
        fecha = generar_fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        
        fraudes.append({
            "transaction_id": f"TXN-F10-{str(base_id).zfill(4)}",
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M:%S"),
            "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()],
            "proveedor_id": proveedor["id"],
            "proveedor_nombre": proveedor["nombre"],
            "proveedor_ruc": proveedor["ruc"],
            "categoria": proveedor["categoria"],
            "cuenta_contable": CUENTAS_CONTABLES.get(proveedor["categoria"], "6999 - Otros"),
            "descripcion": generar_descripcion(proveedor["categoria"]),
            "monto_base": monto,
            "igv": igv,
            "monto_total": round(monto + igv, 2),
            "moneda": "PEN",
            "tipo_cambio": 1.0,
            "metodo_pago": "Transferencia Bancaria",
            "numero_factura": generar_numero_factura(),
            "numero_oc": generar_numero_oc(),
            "centro_costo": random.choice(CENTROS_COSTO),
            "departamento": empleado["departamento"],
            "autorizado_por_id": empleado["id"],
            "autorizado_por": empleado["nombre"],
            "cargo_autorizador": empleado["cargo"],
            "nivel_aprobacion": empleado["nivel_aprobacion"],
            "estado": "Aprobada",
            "es_fraude": 1,
            "tipo_fraude": "Monto bajo umbral sospechoso",
            "riesgo_score": round(random.uniform(0.55, 0.80), 4),
            "notas": f"Monto S/.{monto:,.2f} sospechosamente cercano al umbral de S/.{umbral:,.2f} ({(monto/umbral)*100:.1f}%)"
        })
        base_id += 1
    
    return fraudes, base_id


# ============================================================================
# GENERACIÓN DEL DATASET COMPLETO
# ============================================================================

def main():
    print("=" * 70)
    print("GENERADOR DE DATASET - AUDITORÍA FORENSE")
    print("Proyecto: Agente de Detección de Fraude en Transacciones")
    print("=" * 70)
    
    # 1. Generar transacciones normales
    print("\n[1/11] Generando transacciones normales...")
    normales = generar_transacciones_normales(NUM_TRANSACCIONES_NORMALES)
    print(f"   ✓ {len(normales)} transacciones normales generadas")
    
    # 2. Generar fraudes
    base_id = 1
    
    print("[2/11] Generando fraudes - Fraccionamiento de compras...")
    f1, base_id = generar_fraudes_fraccionamiento(base_id)
    print(f"   ✓ {len(f1)} transacciones de fraccionamiento")
    
    print("[3/11] Generando fraudes - Proveedores fantasma...")
    f2, base_id = generar_fraudes_proveedores_fantasma(base_id)
    print(f"   ✓ {len(f2)} transacciones con proveedores fantasma")
    
    print("[4/11] Generando fraudes - Transacciones duplicadas...")
    f3, base_id = generar_fraudes_duplicados(base_id)
    print(f"   ✓ {len(f3)} transacciones duplicadas")
    
    print("[5/11] Generando fraudes - Fuera de horario...")
    f4, base_id = generar_fraudes_horario(base_id)
    print(f"   ✓ {len(f4)} transacciones fuera de horario")
    
    print("[6/11] Generando fraudes - Sobrefacturación...")
    f5, base_id = generar_fraudes_sobrefacturacion(base_id)
    print(f"   ✓ {len(f5)} transacciones sobrefacturadas")
    
    print("[7/11] Generando fraudes - Conflicto de interés...")
    f6, base_id = generar_fraudes_conflicto_interes(base_id)
    print(f"   ✓ {len(f6)} transacciones con conflicto de interés")
    
    print("[8/11] Generando fraudes - Lavado de activos...")
    f7, base_id = generar_fraudes_lavado(base_id)
    print(f"   ✓ {len(f7)} transacciones de lavado")
    
    print("[9/11] Generando fraudes - Viajes ficticios...")
    f8, base_id = generar_fraudes_viajes_ficticios(base_id)
    print(f"   ✓ {len(f8)} gastos de viaje ficticios")
    
    print("[10/11] Generando fraudes - Notas de crédito...")
    f9, base_id = generar_fraudes_notas_credito(base_id)
    print(f"   ✓ {len(f9)} notas de crédito manipuladas")
    
    print("[11/11] Generando fraudes - Montos bajo umbral...")
    f10, base_id = generar_fraudes_montos_umbral(base_id)
    print(f"   ✓ {len(f10)} transacciones bajo umbral sospechoso")
    
    # Combinar todo
    todos_fraudes = f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9 + f10
    todas_transacciones = normales + todos_fraudes
    
    # Crear DataFrame
    df = pd.DataFrame(todas_transacciones)
    
    # Mezclar aleatoriamente
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Reasignar IDs secuenciales
    df["transaction_id"] = [f"TXN-{str(i+1).zfill(6)}" for i in range(len(df))]
    
    # Ordenar por fecha
    df = df.sort_values(["fecha", "hora"]).reset_index(drop=True)
    
    # ============================================================================
    # GUARDAR ARCHIVOS
    # ============================================================================
    
    output_dir = "/home/claude"
    
    # Dataset completo (con etiquetas de fraude - para entrenamiento/validación)
    filepath_completo = os.path.join(output_dir, "transacciones_completo.csv")
    df.to_csv(filepath_completo, index=False, encoding="utf-8-sig")
    
    # Dataset sin etiquetas (para demo del agente - simula data real)
    df_demo = df.drop(columns=["es_fraude", "tipo_fraude", "riesgo_score", "notas"])
    filepath_demo = os.path.join(output_dir, "transacciones_empresa_2024.csv")
    df_demo.to_csv(filepath_demo, index=False, encoding="utf-8-sig")
    
    # Catálogo de proveedores
    proveedores_all = PROVEEDORES_LEGITIMOS + PROVEEDORES_FANTASMA
    df_proveedores = pd.DataFrame(proveedores_all)
    filepath_prov = os.path.join(output_dir, "catalogo_proveedores.csv")
    df_proveedores.to_csv(filepath_prov, index=False, encoding="utf-8-sig")
    
    # Catálogo de empleados
    df_empleados = pd.DataFrame(EMPLEADOS)
    filepath_emp = os.path.join(output_dir, "catalogo_empleados.csv")
    df_empleados.to_csv(filepath_emp, index=False, encoding="utf-8-sig")
    
    # ============================================================================
    # RESUMEN ESTADÍSTICO
    # ============================================================================
    
    print("\n" + "=" * 70)
    print("RESUMEN DEL DATASET GENERADO")
    print("=" * 70)
    print(f"\nTotal de transacciones: {len(df):,}")
    print(f"Transacciones normales: {len(normales):,} ({len(normales)/len(df)*100:.1f}%)")
    print(f"Transacciones fraudulentas: {len(todos_fraudes):,} ({len(todos_fraudes)/len(df)*100:.1f}%)")
    print(f"\nPeriodo: {FECHA_INICIO.strftime('%Y-%m-%d')} a {FECHA_FIN.strftime('%Y-%m-%d')}")
    print(f"Proveedores legítimos: {len(PROVEEDORES_LEGITIMOS)}")
    print(f"Proveedores fantasma: {len(PROVEEDORES_FANTASMA)}")
    print(f"Empleados: {len(EMPLEADOS)}")
    
    print(f"\n{'Tipo de Fraude':<40} {'Cantidad':>10} {'%':>8}")
    print("-" * 60)
    fraude_counts = df[df["es_fraude"] == 1]["tipo_fraude"].value_counts()
    for tipo, count in fraude_counts.items():
        print(f"{tipo:<40} {count:>10} {count/len(todos_fraudes)*100:>7.1f}%")
    
    print(f"\n{'Columnas del dataset':}")
    for col in df.columns:
        print(f"  • {col}")
    
    monto_total = df["monto_total"].sum()
    monto_fraude = df[df["es_fraude"] == 1]["monto_total"].sum()
    print(f"\nMonto total transaccionado: S/. {monto_total:,.2f}")
    print(f"Monto en fraudes: S/. {monto_fraude:,.2f}")
    print(f"% del monto en fraudes: {monto_fraude/monto_total*100:.2f}%")
    
    print(f"\nArchivos generados:")
    print(f"  1. {filepath_completo}")
    print(f"     (Dataset completo con etiquetas de fraude)")
    print(f"  2. {filepath_demo}")
    print(f"     (Dataset para demo - sin etiquetas)")
    print(f"  3. {filepath_prov}")
    print(f"     (Catálogo de proveedores)")
    print(f"  4. {filepath_emp}")
    print(f"     (Catálogo de empleados)")
    print(f"\n{'=' * 70}")
    print("Dataset generado exitosamente!")
    print("=" * 70)

if __name__ == "__main__":
    main()
