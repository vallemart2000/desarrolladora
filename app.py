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
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        
        if df is None or df.empty:
            if pestana == "ubicaciones":
                # Cambiamos 'comision' por 'enganche_req'
                return pd.DataFrame(columns=["id_lote", "ubicacion", "manzana", "lote", "fase", "precio", "enganche_req", "estatus"])
            
            if pestana == "ventas":
                # Estructura robusta para soportar Apartados y Ventas
                return pd.DataFrame(columns=[
                    "id_venta", "fecha_registro", "fecha_contrato", "inicio_mensualidades", 
                    "ubicacion", "cliente", "vendedor", "precio_total", 
                    "enganche_pagado", "enganche_requerido", "plazo_meses", 
                    "mensualidad", "estatus_pago", "comentarios"
                ])
            
            if pestana == "pagos":
                # Estandarizamos columnas de pagos
                return pd.DataFrame(columns=["id_pago", "fecha", "ubicacion", "cliente", "monto", "metodo", "folio", "comentarios"])
            
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
        ["🏠 Inicio (Cartera)", "📈 Reportes Financieros", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "📍 Ubicaciones", "👥 Directorio"]
    )
    
    st.divider()

    if st.button("🔄 Actualizar Información", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.write("### 🌐 Sistema")
    st.success("✅ Conectado a la Nube")
    ahora = datetime.now().strftime("%H:%M:%S")
    st.info(f"Última Sincronización: {ahora}")

# --- RENDERIZADO DE MÓDULOS ---

if menu == "🏠 Inicio (Cartera)":
    # Corregido: Cargamos 'clientes' en lugar de 'directorio'
    df_v, df_p, df_cl = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("clientes")
    render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda)

elif menu == "📈 Reportes Financieros":
    df_v, df_p, df_g = cargar_datos("ventas"), cargar_datos("pagos"), cargar_datos("gastos")
    render_reportes(df_v, df_p, df_g, fmt_moneda)

elif menu == "📝 Ventas":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")
    df_p = cargar_datos("pagos")
    # Llamada actualizada con df_p para soportar el archivado de pagos
    render_ventas(df_v, df_u, df_cl, df_vd, df_p, conn, URL_SHEET, fmt_moneda)

elif menu == "📊 Detalle de Crédito":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    render_detalle_credito(df_v, df_p, fmt_moneda)

elif menu == "💰 Cobranza":
    df_v, df_p = cargar_datos("ventas"), cargar_datos("pagos")
    # Pasamos cargar_datos para que cobranza pueda actualizar 'ubicaciones' al formalizar
    render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "💸 Gastos":
    df_g = cargar_datos("gastos")
    render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "📍 Ubicaciones":
    df_u = cargar_datos("ubicaciones")
    render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Directorio":
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")
    render_directorio(df_cl, df_vd, conn, URL_SHEET)
