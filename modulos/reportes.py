import streamlit as st
import pandas as pd

def render_reportes(df_v, df_p, df_g, fmt_moneda):
    st.title("📈 Reportes Financieros")
    st.info("Resumen general de ingresos, gastos y utilidad neta.")

    # Validar que existan datos
    if df_v.empty or df_p.empty or df_g.empty:
        st.warning("Se requieren datos en Ventas, Pagos y Gastos para generar el reporte.")
        return

    # --- PROCESAMIENTO DE DATOS ---
    # Ingresos: Suma de Enganches (Ventas) + Mensualidades (Pagos)
    total_enganches = df_v["enganche"].sum()
    total_mensualidades = df_p["monto"].sum()
    total_ingresos = total_enganches + total_mensualidades

    # Gastos
    total_gastos = df_g["monto"].sum()
    
    # Utilidad
    utilidad = total_ingresos - total_gastos

    # --- VISUALIZACIÓN ---
    
    # KPIs Principales
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", fmt_moneda(total_ingresos))
    c2.metric("Gastos Totales", fmt_moneda(total_gastos), delta=f"-{fmt_moneda(total_gastos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(utilidad))

    st.divider()

    col_graf, col_tab = st.columns([2, 1])

    with col_graf:
        st.subheader("📊 Comparativo Financiero")
        # Crear DataFrame para gráfica nativa de barras
        df_grafica = pd.DataFrame({
            "Concepto": ["Ingresos", "Gastos", "Utilidad"],
            "Monto": [total_ingresos, total_gastos, utilidad]
        }).set_index("Concepto")
        
        st.bar_chart(df_grafica)

    with col_tab:
        st.subheader("📋 Desglose de Ingresos")
        st.write(f"**Enganches:** {fmt_moneda(total_enganches)}")
        st.write(f"**Mensualidades:** {fmt_moneda(total_mensualidades)}")
        
    st.divider()

    # Resumen de Gastos por Categoría
    st.subheader("💸 Gastos por Categoría")
    if "categoria" in df_g.columns:
        resumen_gastos = df_g.groupby("categoria")["monto"].sum().reset_index()
        resumen_gastos.columns = ["Categoría", "Monto Total"]
        resumen_gastos = resumen_gastos.sort_values(by="Monto Total", ascending=False)
        
        # Aplicar formato de moneda a la tabla
        st.table(resumen_gastos.style.format({"Monto Total": "$ {:,.2f}"}))
    else:
        st.write("No se encontró la columna 'categoria' en la pestaña de gastos.")

    # Listado de Gastos Recientes
    with st.expander("Ver últimos gastos registrados"):
        st.dataframe(df_g.tail(10), use_container_width=True, hide_index=True)
