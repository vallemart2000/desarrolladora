import streamlit as st
import pandas as pd
from datetime import datetime

def render_comisiones(df_v, df_p_com, conn, URL_SHEET, fmt_moneda):
    st.title("🎖️ Gestión de Comisiones")
    
    # --- CONFIGURACIÓN DE NEGOCIO ---
    PORCENTAJE_COMISION = 0.03  # 3% por defecto (puedes cambiarlo)
    
    if df_v.empty:
        st.warning("No hay ventas registradas para calcular comisiones.")
        return

    # --- 1. PROCESAMIENTO DE DATOS ---
    # Calculamos lo que cada vendedor debería ganar por sus ventas
    df_v['comision_total'] = df_v['precio_total'].astype(float) * PORCENTAJE_COMISION
    
    # Resumen por vendedor (Lo devengado)
    resumen_vendedores = df_v.groupby('vendedor')['comision_total'].sum().reset_index()
    resumen_vendedores.columns = ['Vendedor', 'Total Devengado']

    # Resumen de lo ya pagado (desde la hoja de pagos_comisiones)
    if not df_p_com.empty:
        pagos_hechos = df_p_com.groupby('vendedor')['monto'].sum().reset_index()
        pagos_hechos.columns = ['Vendedor', 'Total Pagado']
        resumen_final = pd.merge(resumen_vendedores, pagos_hechos, on='Vendedor', how='left').fillna(0)
    else:
        resumen_final = resumen_vendedores.copy()
        resumen_final['Total Pagado'] = 0.0

    resumen_final['Saldo Pendiente'] = resumen_final['Total Devengado'] - resumen_final['Total Pagado']

    # --- 2. DASHBOARD DE MÉTRICAS ---
    total_comisiones_globlal = resumen_final['Total Devengado'].sum()
    total_pagado_global = resumen_final['Total Pagado'].sum()
    total_pendiente_global = resumen_final['Saldo Pendiente'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Comisiones Totales", f"$ {total_comisiones_globlal:,.2f}")
    col2.metric("💸 Total Pagado", f"$ {total_pagado_global:,.2f}")
    col3.metric("⏳ Pendiente por Pagar", f"$ {total_pendiente_global:,.2f}", delta_color="inverse")

    st.markdown("---")

    # --- 3. SECCIÓN DE REGISTRO DE PAGO ---
    with st.expander("➕ Registrar Pago de Comisión"):
        with st.form("form_pago_comision"):
            c_v, c_m, c_f = st.columns(3)
            vendedor_sel = c_v.selectbox("Seleccionar Vendedor", resumen_final['Vendedor'].unique())
            monto_pago = c_m.number_input("Monto a Pagar ($)", min_value=0.0, step=100.0)
            fecha_pago = c_f.date_input("Fecha de Pago", datetime.now())
            nota = st.text_input("Nota o Referencia (ej. Pago lote 05)")
            
            if st.form_submit_button("Confirmar Pago"):
                nuevo_pago = pd.DataFrame([{
                    "vendedor": vendedor_sel,
                    "monto": monto_pago,
                    "fecha": fecha_pago.strftime('%Y-%m-%d'),
                    "nota": nota
                }])
                
                # Actualizar Google Sheets
                df_p_com_new = pd.concat([df_p_com, nuevo_pago], ignore_index=True)
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos_comisiones", data=df_p_com_new)
                st.success(f"Pago registrado para {vendedor_sel}")
                st.rerun()

    # --- 4. VISUALIZACIÓN DE CARTERA POR VENDEDOR ---
    st.subheader("📊 Estado por Vendedor")
    
    # Aplicamos el criterio de Pandas Style para asegurar comas y signo $
    df_resumen_estilado = resumen_final.style.format({
        "Total Devengado": "$ {:,.2f}",
        "Total Pagado": "$ {:,.2f}",
        "Saldo Pendiente": "$ {:,.2f}"
    })

    st.dataframe(
        df_resumen_estilado,
        column_config={
            "Vendedor": "Vendedor",
            "Total Devengado": "Devengado",
            "Total Pagado": "Pagado",
            "Saldo Pendiente": "Saldo Pendiente"
        },
        use_container_width=True,
        hide_index=True
    )

    # --- 5. DETALLE Y RANKING ---
    tab1, tab2 = st.tabs(["📈 Ranking de Ventas", "📜 Historial de Pagos"])
    
    with tab1:
        st.write("Ventas totales y comisión generada por contrato:")
        df_ventas_detalle = df_v[['vendedor', 'cliente', 'ubicacion', 'precio_total', 'comision_total']].copy()
        
        # Aplicamos estilo al ranking
        df_ranking_estilado = df_ventas_detalle.style.format({
            "precio_total": "$ {:,.2f}",
            "comision_total": "$ {:,.2f}"
        })

        st.dataframe(
            df_ranking_estilado,
            column_config={
                "vendedor": "Vendedor", 
                "cliente": "Cliente", 
                "ubicacion": "Lote", 
                "precio_total": "Venta ($)", 
                "comision_total": "Comisión ($)"
            },
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        if not df_p_com.empty:
            st.write("Últimos pagos realizados:")
            df_hist_pagos = df_p_com.sort_values(by="fecha", ascending=False).copy()
            
            # Aplicamos estilo al historial de pagos
            df_hist_pagos_estilado = df_hist_pagos.style.format({
                "monto": "$ {:,.2f}"
            })

            st.dataframe(
                df_hist_pagos_estilado,
                column_config={
                    "vendedor": "Vendedor",
                    "monto": "Monto Pagado",
                    "fecha": "Fecha de Pago",
                    "nota": "Referencia"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay historial de pagos aún.")
