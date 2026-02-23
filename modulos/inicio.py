import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Cartera de Clientes Activos")

    # --- VALIDACIÓN DE SEGURIDAD ---
    # Si df_v es una cadena (error) o está vacío, detenemos la ejecución con un mensaje claro
    if isinstance(df_v, str) or df_v.empty:
        st.error(f"❌ No se pudo cargar la tabla de ventas. Verifique la pestaña 'ventas' en Google Sheets.")
        return

    # --- 1. PROCESAMIENTO DE FECHAS Y PAGOS ---
    try:
        df_v['fecha'] = pd.to_datetime(df_v['fecha'])
        
        # Procesar pagos solo si la tabla es válida y tiene las columnas necesarias
        if not isinstance(df_p, str) and not df_p.empty and 'lote' in df_p.columns:
            df_p['fecha'] = pd.to_datetime(df_p['fecha'])
            ultimo_pago = df_p.sort_values('fecha').groupby('lote')['fecha'].last().reset_index()
            ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
        else:
            # Si no hay pagos, creamos un dataframe vacío con las columnas esperadas
            ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])
    except Exception as e:
        st.warning(f"Aviso: Hubo un detalle al procesar fechas de pagos: {e}")
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # --- 2. UNIR VENTAS CON ÚLTIMOS PAGOS ---
    # Verificamos que 'estatus_pago' exista para filtrar
    if 'estatus_pago' in df_v.columns:
        df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    else:
        df_cartera = df_v.copy()
        
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    # --- 3. CÁLCULO DE DÍAS DE ATRASO Y MONTO DEUDA ---
    hoy = datetime.now()
    def calcular_datos_atraso(row):
        # Referencia: último pago o fecha de venta
        fecha_ref = row['fecha_ultimo_pago'] if pd.notnull(row['fecha_ultimo_pago']) else row['fecha']
        
        try:
            dias = (hoy - pd.to_datetime(fecha_ref)).days
            dias = max(0, dias)
            
            mensualidad = float(row.get('mensualidad', 0))
            meses_atraso = dias // 30
            if meses_atraso < 1 and dias > 0: meses_atraso = 1
            
            monto_regularizar = meses_atraso * mensualidad if dias > 30 else mensualidad
            return pd.Series([dias, monto_regularizar])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_datos_atraso, axis=1)

    # --- 4. ESTATUS Y LINKS ---
    df_cartera['Estatus Cobro'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 PREVENTIVO (+25d)" if x > 25 else "🟢 AL CORRIENTE")
    )

    # --- 5. FILTRO Y TABLA ---
    st.write("### 🔍 Filtros de Cartera")
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)

    df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy() if solo_atrasados else df_cartera.copy()

    st.subheader("📋 Control de Cobranza y Contacto")
    if df_mostrar.empty:
        st.success("✨ No hay clientes con atraso o las tablas están vacías.")
    else:
        # Definir columnas finales a mostrar (solo las que existen)
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
