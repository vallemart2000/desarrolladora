import streamlit as st

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Sistema Zona Valle")
    st.success("✅ Conexión Estable")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ventas Totales", len(df_v))
    with col2:
        st.metric("Clientes", len(df_cl))
    with col3:
        total_recuperado = df_p["monto"].sum() if not df_p.empty else 0
        st.metric("Cobranza Total", fmt_moneda(total_recuperado))

    st.subheader("📋 Ventas Recientes")
    st.dataframe(df_v.tail(10), use_container_width=True, hide_index=True)
