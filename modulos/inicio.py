import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Cartera de Clientes Activos")

    # --- VALIDACIÓN DE SEGURIDAD INICIAL ---
    if isinstance(df_v, str) or df_v.empty:
        st.error("❌ No se pudo cargar la tabla de ventas. Verifica la conexión con Google Sheets.")
        return

    # --- 1. PROCESAMIENTO DE FECHAS Y PAGOS (CON PROTECCIÓN) ---
    try:
        df_v['fecha'] = pd.to_datetime(df_v['fecha'])
        
        # Solo procesamos si df_p es un DataFrame válido y tiene la columna 'lote'
        if isinstance(df_p, pd.DataFrame) and not df_p.empty and 'lote' in df_p.columns:
            df_p['fecha'] = pd.to_datetime(df_p['fecha'])
            # Agrupamos para obtener el último pago por lote
            ultimo_pago = df_p.sort_values('fecha').groupby('lote')['fecha'].last().reset_index()
            ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
        else:
            # Si la tabla pagos falla o está vacía, creamos una estructura vacía para evitar el KeyError
            ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])
            
    except Exception as e:
        st.warning(f"Aviso: La tabla de pagos no está disponible o tiene un formato distinto. ({e})")
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # --- 2. UNIR VENTAS CON ÚLTIMOS PAGOS ---
    # Filtramos ventas activas si la columna existe
    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy() if "estatus_pago" in df_v.columns else df_v.copy()
    
    # Unimos con la información del último pago
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    # --- 3. CÁLCULO DE DÍAS DE ATRASO Y MONTO DEUDA ---
    hoy = datetime.now()
    
    def calcular_datos_atraso(row):
        # Si no hay fecha_ultimo_pago, usamos la fecha de venta
        fecha_ref = row['fecha_ultimo_pago'] if pd.notnull(row['fecha_ultimo_pago']) else row['fecha']
        
        try:
            dias = (hoy - pd.to_datetime(fecha_ref)).days
            dias = max(0, dias)
            
            m_monto = float(row.get('mensualidad', 0))
            meses_atraso = dias // 30
            if meses_atraso < 1 and dias > 0: meses_atraso = 1
            
            pago_corr = meses_atraso * m_monto if dias > 30 else m_monto
            return pd.Series([dias, pago_corr])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_datos_atraso, axis=1)

    # --- 4. SEMÁFORO ---
    df_cartera['Estatus Cobro'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 PREVENTIVO (+25d)" if x > 25 else "🟢 AL CORRIENTE")
    )

    # --- 5. FILTROS Y MÉTRICAS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes Activos", len(df_cartera))
    c2.metric("En Alerta (🟡)", len(df_cartera[df_cartera['dias_atraso'] > 25]))
    c3.metric("Urgentes (🔴)", len(df_cartera[df_cartera['dias_atraso'] > 75]))

    st.write("### 🔍 Filtros de Cartera")
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)

    df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy() if solo_atrasados else df_cartera.copy()

    # --- 6. TABLA FINAL ---
    st.subheader("📋 Control de Cobranza y Contacto")
    if df_mostrar.empty:
        st.success("✨ No hay atrasos detectados en este momento.")
    else:
        # Mostramos solo columnas existentes para evitar nuevos errores
        columnas_finales = ["Estatus Cobro", "ubicacion", "cliente", "fecha_ultimo_pago", "dias_atraso", "pago_corriente"]
        cols_a_usar = [c for c in columnas_finales if c in df_mostrar.columns]
        
        st.data_editor(
            df_mostrar[cols_a_usar],
            column_config={
                "fecha_ultimo_pago": st.column_config.DateColumn("Último Pago", format="DD/MM/YYYY"),
                "pago_corriente": st.column_config.NumberColumn("Pago para Corriente", format="$ %.2f"),
                "dias_atraso": st.column_config.NumberColumn("Días", format="%d d")
            },
            use_container_width=True,
            hide_index=True,
            disabled=True,
            key="tabla_cobranza_blindada"
        )
