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
from modulos.clientes import render_clientes

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Zona Valle - Gestión Inmobiliaria", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/"

# --- FUNCIÓN PARA FORMATO DE MONEDA ($) ---
def fmt_moneda(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"

# --- FUNCIONES DE APOYO ---
def cargar_datos(pestana):
    try:
        # Esto nos dirá en la pantalla de la app qué está pasando
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        if df.empty:
            st.sidebar.warning(f"La pestaña '{pestana}' está vacía o no existe.")
        return df
    except Exception as e:
        st.sidebar.error(f"Error en {pestana}: {e}")
        return pd.DataFrame()

# === BARRA LATERAL (SIDEBAR) ===
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.title("🏢 Zona Valle")
    
    st.subheader("Navegación")
    menu = st.radio(
        "Seleccione un módulo:",
        [
            "🏠 Inicio (Cartera)", 
            "📈 Reportes Financieros",
            "📝 Ventas", 
            "📊 Detalle de Crédito", 
            "💰 Cobranza", 
            "💸 Gastos", 
            "📍 Ubicaciones", 
            "👥 Clientes"
        ]
    )
    
    st.divider()

    if st.button("🔄 Actualizar Información", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.write("### 🌐 Sistema")
    st.success("✅ En línea")
    ahora = datetime.now().strftime("%H:%M:%S")
    st.info(f"Sincronizado: {ahora}")

# === RENDERIZADO DE MÓDULOS ===

if menu == "🏠 Inicio (Cartera)":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_cl = cargar_datos("clientes")
    render_inicio(df_v, df_p, df_cl, fmt_moneda)

elif menu == "📈 Reportes Financieros":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    render_reportes(df_v, df_p, df_g, fmt_moneda)

elif menu == "📝 Ventas":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")
    render_ventas(df_v, df_u, df_cl, df_vd, conn, URL_SHEET, fmt_moneda)

elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    render_detalle_credito(df_v, df_p, fmt_moneda)

elif menu == "💰 Cobranza":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "💸 Gastos":
    df_g = cargar_datos("gastos")
    render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "📍 Ubicaciones":
    df_u = cargar_datos("ubicaciones")
    render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Clientes":
    df_cl = cargar_datos("clientes")
    render_clientes(df_cl, conn, URL_SHEET, cargar_datos)




