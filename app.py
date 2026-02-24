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
        # Forzamos la lectura de la pestaña
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        
        if df is None or df.empty:
            if pestana == "ubicaciones":
                return pd.DataFrame(columns=["id_lote", "ubicacion", "manzana", "lote", "fase", "precio", "comision", "estatus"])
            if pestana == "ventas":
                # Agregamos estatus_pago y mensualidad por defecto
                return pd.DataFrame(columns=["id_venta", "fecha", "ubicacion", "cliente", "vendedor", "precio_total", "enganche", "plazo_meses", "mensualidad", "comision", "estatus_pago"])
            if pestana == "pagos":
                return pd.DataFrame(columns=["fecha", "monto", "lote", "concepto"])
            if pestana == "clientes":
                return pd.DataFrame(columns=["id_cliente", "nombre", "telefono", "correo"])
            if pestana == "vendedores":
                return pd.DataFrame(columns=["id_vendedor", "nombre", "telefono", "comision_base"])
            return pd.DataFrame()
            
        return df
    except Exception as e:
        st.sidebar.error(f"⚠️ Error en pestaña '{pestana}': {str(e)[:50]}")
        return pd.DataFrame()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("🏢 Valle Mart")
    
    st.subheader("Navegación")
    menu = st.radio(
        "Seleccione un módulo:",
        ["🏠 Inicio (Cartera)", "📈 Reportes Financieros", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "📍 Ubicaciones", "👥 Clientes"]
    )
    
    st.divider()

    if st.button("🔄 Actualizar Información", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.write("### 🌐 Sistema")
    # Indicador visual de estado de conexión
    st.success("✅ Conectado a la Nube")
    ahora = datetime.now().strftime("%H:%M:%S")
    st.info(f"Última Sincronización: {ahora}")

# --- RENDERIZADO DE MÓDULOS ---
# Pasamos 'conn' y 'URL_SHEET' a los módulos que necesitan guardar datos o autorreparar columnas

if menu == "🏠 Inicio (Cartera)":
    df_v, df_p, df_cl = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("clientes")
    # Agregamos parámetros para que el inicio pueda reparar columnas si faltan
    render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda)

elif menu == "📈 Reportes Financieros":
    df_v, df_p, df_g = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("gastos")
    render_reportes(df_v, df_p, df_g, fmt_moneda)

elif menu == "📝 Ventas":
    df_v, df_u, df_cl, df_vd = cargar_datos("ventas"), cargar_datos("ubicaciones"), cargar_datos("clientes"), cargar_datos("vendedores")
    render_ventas(df_v, df_u, df_cl, df_vd, conn, URL_SHEET, fmt_moneda)

elif menu == "📊 Detalle de Crédito":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    render_detalle_credito(df_v, df_p, fmt_moneda)

elif menu == "💰 Cobranza":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "💸 Gastos":
    df_g = cargar_datos("gastos")
    render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "📍 Ubicaciones":
    df_u = cargar_datos("ubicaciones")
    render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Clientes":
    df_cl = cargar_datos("clientes")
    render_directorio(df_cl, conn, URL_SHEET, cargar_datos)


