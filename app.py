import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- IMPORTACIÓN DE MÓDULOS ---
from modulos.inicio import render_inicio
from modulos.reportes import render_reportes
from modulos.ventas import render_ventas
from modulos.credito import render_detalle_credito
from modulos.cobranza import render_cobranza
from modulos.gastos import render_gastos
from modulos.ubicaciones import render_ubicaciones
from modulos.directorio import render_directorio
from modulos.comisiones import render_comisiones

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Valle Mart - Gestión Inmobiliaria", layout="wide", page_icon="🏢")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
URL_SHEET = "https://docs.google.com/spreadsheets/d/15j-kbr6fFk-l_hgzQ28SSxQ3Hhp-FPJKT1OvNWzqtUg/"

# --- FUNCIÓN PARA FORMATO DE MONEDA ($) ---
def fmt_moneda(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except (ValueError, TypeError):
        return "$ 0.00"

# --- FUNCIÓN DE CARGA CON PARCHE PARA TABLAS VACÍAS ---
@st.cache_data(ttl=300)
def cargar_datos(pestana):
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        
        if df is None or df.empty:
            if pestana == "ubicaciones":
                return pd.DataFrame(columns=["id_lote", "ubicacion", "manzana", "lote", "fase", "precio", "enganche_req", "estatus"])
            
            if pestana == "ventas":
                return pd.DataFrame(columns=[
                    "id_venta", "fecha_registro", "fecha_contrato", "inicio_mensualidades", 
                    "ubicacion", "cliente", "vendedor", "precio_total", 
                    "enganche_pagado", "enganche_requerido", "plazo_meses", 
                    "mensualidad", "estatus_pago", "comentarios"
                ])
            
            if pestana == "pagos":
                return pd.DataFrame(columns=["id_pago", "fecha", "ubicacion", "cliente", "monto", "metodo", "folio", "comentarios"])
            
            if pestana == "clientes":
                return pd.DataFrame(columns=["id_cliente", "nombre", "telefono", "correo"])
            
            if pestana == "vendedores":
                return pd.DataFrame(columns=["id_vendedor", "nombre", "telefono", "comision_base"])

            if pestana == "pagos_comisiones": # <--- PARCHE PARA NUEVA TABLA
                return pd.DataFrame(columns=["vendedor", "monto", "fecha", "nota"])
                
            return pd.DataFrame()
            
        return df
    except Exception as e:
        st.sidebar.error(f"⚠️ Error en pestaña '{pestana}': {str(e)[:50]}")
        return pd.DataFrame()

def auditar_base_de_datos():
    st.subheader("🔍 Auditoría de Estructura")
    
    estructura_ideal = {
        "ubicaciones": ["id_lote", "ubicacion", "manzana", "lote", "fase", "precio", "enganche_req", "estatus"],
        "ventas": ["id_venta", "fecha_registro", "fecha_contrato", "inicio_mensualidades", "ubicacion", "cliente", "vendedor", "precio_total", "enganche_pagado", "enganche_requerido", "plazo_meses", "mensualidad", "estatus_pago", "comentarios"],
        "pagos": ["id_pago", "fecha", "ubicacion", "cliente", "monto", "metodo", "folio", "comentarios"],
        "clientes": ["id_cliente", "nombre", "telefono", "correo"],
        "vendedores": ["id_vendedor", "nombre", "telefono", "comision_base"],
        "pagos_comisiones": ["vendedor", "monto", "fecha", "nota"]
    }
    
    errores = 0
    for pestana, columnas_esperadas in estructura_ideal.items():
        try:
            df_real = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
            columnas_reales = df_real.columns.tolist()
            faltantes = [col for col in columnas_esperadas if col not in columnas_reales]
            
            if faltantes:
                st.error(f"❌ En **'{pestana}'** faltan: {', '.join(faltantes)}")
                errores += 1
            else:
                st.success(f"✅ **'{pestana}'** está perfecta.")
                
        except Exception:
            st.warning(f"⚠️ La pestaña **'{pestana}'** no existe en el archivo.")
            errores += 1
            
    if errores == 0:
        st.info("💡 Tu base de datos está 100% sincronizada con el código.")
    else:
        st.error(f"Se encontraron {errores} problemas de estructura.")

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("🏢 Valle Mart")
    
    st.subheader("Navegación")
    menu = st.radio(
        "Seleccione un módulo:",
        ["🏠 Inicio (Cartera)", "📈 Reportes Financieros", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "🎖️ Comisiones", "💸 Gastos", "📍 Ubicaciones", "👥 Directorio"]
    )
    
    st.divider()

    if st.button("🔄 Actualizar Información", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    with st.expander("🛠️ Herramientas de Sistema"):
        if st.button("🔍 Auditar Columnas"):
            auditar_base_de_datos()

    st.markdown("---")
    st.write("### 🌐 Sistema")
    st.success("✅ Conectado a la Nube")
    ahora = datetime.now().strftime("%H:%M:%S")
    st.info(f"Última Sincronización: {ahora}")

# --- RENDERIZADO DE MÓDULOS ---
if menu == "🏠 Inicio (Cartera)":
    df_v, df_p, df_cl = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("clientes")
    render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda)

elif menu == "📈 Reportes Financieros":
    df_v, df_p, df_g = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("gastos")
    render_reportes(df_v, df_p, df_g, fmt_moneda)

elif menu == "📝 Ventas":
    df_v, df_u, df_cl, df_vd, df_p = cargar_datos("ventas"), cargar_datos("ubicaciones"), cargar_datos("clientes"), cargar_datos("vendedores"), cargar_datos("pagos")
    render_ventas(df_v, df_u, df_cl, df_vd, df_p, conn, URL_SHEET, fmt_moneda)

elif menu == "📊 Detalle de Crédito":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    render_detalle_credito(df_v, df_p, fmt_moneda)

elif menu == "💰 Cobranza":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "🎖️ Comisiones":
    df_v = cargar_datos("ventas")
    df_p_com = cargar_datos("pagos_comisiones")
    render_comisiones(df_v, df_p_com, conn, URL_SHEET, fmt_moneda)

elif menu == "💸 Gastos":
    df_g = cargar_datos("gastos")
    render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "📍 Ubicaciones":
    df_u = cargar_datos("ubicaciones")
    render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Directorio":
    df_cl, df_vd = cargar_datos("clientes"), cargar_datos("vendedores")
    render_directorio(df_cl, df_vd, conn, URL_SHEET)
