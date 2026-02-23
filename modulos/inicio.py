import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Verifica si faltan columnas y las agrega al DataFrame y a la base de datos."""
    cambios = False
    for col, default_val in columnas_necesarias.items():
        if col not in df.columns:
            df[col] = default_val
            cambios = True
    
    if cambios:
        try:
            conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
            st.toast(f"🛠️ Base de datos '{worksheet_name}' actualizada con nuevas columnas.")
        except Exception as e:
            st.error(f"Error al intentar reparar columnas en {worksheet_name}: {e}")
    return df

def render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda):
    st.title("🏠 Cartera de Clientes Activos")

    # --- 1. AUTORREPARACIÓN DE ESTRUCTURA ---
    # Columnas necesarias para Ventas y sus valores por defecto
    cols_v = {
        "estatus_pago": "Activo",
        "mensualidad": 0.0,
        "ubicacion": "N/A",
        "cliente": "Desconocido",
        "fecha": datetime.now().strftime('%Y-%m-%d')
    }
    df_v = verificar_y_reparar_columnas(df_v, cols_v, "ventas", conn, URL_SHEET)

    # Columnas necesarias para Pagos
    cols_p = {
        "lote": "N/A",
        "fecha": datetime.now().strftime('%Y-%m-%d'),
        "monto": 0.0
    }
    df_p = verificar_y_reparar_columnas(df_p, cols_p, "pagos", conn, URL_SHEET)

    # --- 2. PROCESAMIENTO DE PAGOS ---
    if not df_p.empty:
        df_p['fecha'] = pd.to_datetime(df_p['fecha'], errors='coerce')
        df_p['lote'] = df_p['lote'].astype(str).str.strip()
        
        # Obtenemos el último pago
        ultimo_pago = df_p.dropna(subset=['fecha']).sort_values('fecha').groupby('lote')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # --- 3. UNIR VENTAS CON ÚLTIMOS PAGOS ---
    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera['ubicacion'] = df_cartera['ubicacion'].astype(str).str.strip()
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    # --- 4. CÁLCULO DE DÍAS DE ATRASO Y MONTO DEUDA ---
    hoy = datetime.now()
    def calcular_atraso(row):
        fecha_ref = row['fecha_ultimo_pago'] if pd.notnull(row['fecha_ultimo_pago']) else row['fecha']
        try:
            dias = (hoy - pd.to_datetime(fecha_ref)).days
            dias = max(0, dias)
            # Cálculo de regularización
            m_monto = float(row['mensualidad'])
            meses_atraso = max(1, dias // 30) if dias > 0 else 0
            pago_corr = meses_atraso * m_monto if dias > 30 else m_monto
            return pd.Series([dias, pago_corr])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_atraso, axis=1)

    # --- 5. SEMÁFORO Y FILTROS ---
    df_cartera['Estatus Cobro'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 PREVENTIVO (+25d)" if x > 25 else "🟢 AL CORRIENTE")
    )

    st.write("### 🔍 Filtros de Cartera")
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)

    df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy() if solo_atrasados else df_cartera.copy()

    # --- 6. TABLA FINAL ---
    st.subheader("📋 Control de Cobranza y Contacto")
    if df_mostrar.empty:
        st.success("✨ Todo al corriente.")
    else:
        # Mostramos solo las columnas clave
        cols_finales = ["Estatus Cobro", "ubicacion", "cliente", "fecha_ultimo_pago", "dias_atraso", "pago_corriente"]
        st.data_editor(
            df_mostrar[cols_finales],
            column_config={
                "fecha_ultimo_pago": st.column_config.DateColumn("Último Pago", format="DD/MM/YYYY"),
                "pago_corriente": st.column_config.NumberColumn("Pago para Corriente", format="$ %.2f"),
                "dias_atraso": st.column_config.NumberColumn("Días", format="%d d")
            },
            use_container_width=True, hide_index=True, disabled=True
        )
