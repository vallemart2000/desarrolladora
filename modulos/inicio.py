import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Sincroniza la estructura de la base de datos si faltan columnas."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty and len(df.columns) == 0):
        df = pd.DataFrame(columns=columnas_necesarias.keys())
    
    cambios = False
    for col, default_val in columnas_necesarias.items():
        if col not in df.columns:
            df[col] = default_val
            cambios = True
    
    if cambios:
        try:
            conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
            st.toast(f"🛠️ Estructura de '{worksheet_name}' sincronizada.")
        except:
            pass 
    return df

def render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda):
    st.title("🏠 Panel de Control y Cartera")

    # --- 1. REPARACIÓN DE ESTRUCTURA (Nombres actualizados) ---
    cols_v = {
        "id_venta": 0, "fecha_registro": "", "ubicacion": "", "cliente": "", 
        "vendedor": "", "precio_total": 0.0, "enganche_pagado": 0.0, 
        "mensualidad": 0.0, "estatus_pago": "Activo", "inicio_mensualidades": ""
    }
    df_v = verificar_y_reparar_columnas(df_v, cols_v, "ventas", conn, URL_SHEET)

    # --- 2. CÁLCULO DE MÉTRICAS RÁPIDAS ---
    c1, c2, c3, c4 = st.columns(4)
    
    total_ventas = df_v[df_v["estatus_pago"] == "Activo"]["precio_total"].sum()
    total_recaudado = (df_v["enganche_pagado"].sum() + df_p["monto"].sum()) if not df_p.empty else df_v["enganche_pagado"].sum()
    cartera_viva = df_v[df_v["estatus_pago"] == "Activo"].shape[0]
    
    c1.metric("📈 Valor de Cartera", f"$ {total_ventas:,.2f}")
    c2.metric("💰 Ingresos Totales", f"$ {total_recaudado:,.2f}")
    c3.metric("👥 Clientes Activos", cartera_viva)
    c4.metric("🏗️ Lotes Vendidos/Ap.", df_v.shape[0])

    st.markdown("---")

    # --- 3. PROCESAMIENTO DE COBRANZA ---
    if df_v.empty:
        st.info("No hay datos de ventas para mostrar la cartera.")
        return

    # Obtener el último pago de cada ubicación de la tabla pagos
    if not df_p.empty:
        df_p_clean = df_p.copy()
        df_p_clean['fecha'] = pd.to_datetime(df_p_clean['fecha'], errors='coerce')
        df_p_clean = df_p_clean.dropna(subset=['fecha'])
        ultimo_pago = df_p_clean.sort_values('fecha').groupby('ubicacion')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # Unir con cartera activa
    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    # --- 4. LÓGICA DE DÍAS DE ATRASO ---
    hoy = datetime.now()
    
    def analizar_atraso(row):
        # Si no hay mensualidades cobradas, la fecha de referencia es la fecha de inicio_mensualidades
        try:
            fecha_ref = pd.to_datetime(row['fecha_ultimo_pago']) if pd.notnull(row['fecha_ultimo_pago']) else pd.to_datetime(row['inicio_mensualidades'])
            dias = (hoy - fecha_ref).days
            dias = max(0, dias)
            
            # Cálculo de deuda estimada
            mensualidad = float(row['mensualidad'])
            meses_deuda = max(0, dias // 30)
            deuda = meses_deuda * mensualidad if dias > 30 else 0.0
            
            return pd.Series([dias, deuda])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'deuda_estimada']] = df_cartera.apply(analizar_atraso, axis=1)

    # --- 5. GENERACIÓN DE MENSAJES (WhatsApp / Mail) ---
    def link_wa(row):
        try:
            tel = df_cl[df_cl['nombre'] == row['cliente']]['telefono'].values[0]
            if not tel or str(tel) == 'nan': return None
            msg = (f"Hola {row['cliente']}, te saludamos de Valle Mart. "
                   f"Tu lote {row['ubicacion']} presenta un atraso de {row['dias_atraso']} días. "
                   f"Monto pendiente: {fmt_moneda(row['deuda_estimada'])}. ¿Podemos apoyarte en algo?")
            return f"https://wa.me/{str(tel).strip()}?text={urllib.parse.quote(msg)}"
        except: return None

    df_cartera['WhatsApp'] = df_cartera.apply(link_wa, axis=1)

    # --- 6. SEMÁFORO Y VISUALIZACIÓN ---
    df_cartera['Semaforo'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 Crítico (+60d)" if x > 60 else ("🟡 Preventivo (+30d)" if x > 30 else "🟢 Al día")
    )

    st.subheader("📋 Seguimiento de Cartera Activa")
    
    atraso_filter = st.checkbox("Mostrar solo clientes con atraso", value=False)
    
    df_final = df_cartera.copy()
    if atraso_filter:
        df_final = df_final[df_final["dias_atraso"] > 30]

    if df_final.empty:
        st.success("🎉 No hay clientes con atraso en este momento.")
    else:
        # Reordenar y limpiar para vista
        cols_vista = ["Semaforo", "ubicacion", "cliente", "dias_atraso", "deuda_estimada", "WhatsApp"]
        
        st.dataframe(
            df_final[cols_vista].sort_values("dias_atraso", ascending=False),
            column_config={
                "Semaforo": "Estatus",
                "ubicacion": "Lote",
                "dias_atraso": st.column_config.NumberColumn("Días Atraso", format="%d d"),
                "deuda_estimada": st.column_config.NumberColumn("Deuda Est.", format="$ %.2f"),
                "WhatsApp": st.column_config.LinkColumn("📲 Contacto", display_text="Enviar Recordatorio")
            },
            use_container_width=True,
            hide_index=True
        )

    # --- 7. PRÓXIMOS VENCIMIENTOS (A 7 DÍAS) ---
    with st.expander("📅 Ver próximos vencimientos de este mes"):
        # Lógica simplificada: los que cumplen mes pronto
        st.write("Esta sección muestra a los clientes cuya fecha de mensualidad está próxima.")
        df_prox = df_cartera[df_cartera["dias_atraso"] < 30].copy()
        st.table(df_prox[["ubicacion", "cliente", "mensualidad"]])
