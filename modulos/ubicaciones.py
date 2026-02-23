import streamlit as st
import pandas as pd

def render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos):
    st.title("📍 Gestión de Inventario (Ubicaciones)")

    tab_lista, tab_nuevo = st.tabs(["📋 Inventario Actual", "➕ Agregar Lote"])

    # --- PESTAÑA 1: LISTA ---
    with tab_lista:
        st.subheader("Control de Lotes y Disponibilidad")
        if df_u.empty:
            st.info("No hay lotes registrados.")
        else:
            # Filtros rápidos
            c1, c2 = st.columns(2)
            f_estatus = c1.multiselect("Filtrar por Estatus", options=df_u["estatus"].unique(), default=df_u["estatus"].unique())
            
            df_mostrar = df_u[df_u["estatus"].isin(f_estatus)]

            st.dataframe(
                df_mostrar,
                column_config={
                    "id_lote": st.column_config.NumberColumn("ID", format="%d"),
                    "precio": st.column_config.NumberColumn("Precio Lista", format="$ %.2f"),
                    "comision": st.column_config.NumberColumn("Comisión Sugerida", format="$ %.2f"),
                    "estatus": st.column_config.SelectboxColumn("Estatus", options=["Disponible", "Vendido", "Apartado", "Bloqueado"])
                },
                use_container_width=True,
                hide_index=True
            )

    # --- PESTAÑA 2: NUEVO LOTE ---
    with tab_nuevo:
        st.subheader("Registrar Nueva Ubicación")
        with st.form("form_nueva_ub"):
            col1, col2 = st.columns(2)
            f_ubi = col1.text_input("Nombre de Ubicación (Ej: M01-L01) *")
            f_fase = col2.selectbox("Fase/Etapa", ["Etapa 1", "Etapa 2", "Etapa 3", "Club"])
            
            f_pre = col1.number_input("Precio de Lista ($)", min_value=0.0, step=1000.0)
            f_com = col2.number_input("Comisión Sugerida ($)", min_value=0.0, step=500.0)
            
            st.info("ℹ️ El ID del lote iniciará automáticamente en 1001.")
            
            if st.form_submit_button("💾 Guardar Ubicación", type="primary"):
                if not f_ubi:
                    st.error("❌ La ubicación es obligatoria.")
                elif f_ubi in df_u["ubicacion"].values:
                    st.error("❌ Esta ubicación ya existe.")
                else:
                    # --- LÓGICA ID 1001+ ---
                    if df_u.empty:
                        nuevo_id = 1001
                    else:
                        max_id = df_u["id_lote"].max()
                        nuevo_id = int(max_id + 1) if max_id >= 1001 else 1001

                    nueva_ub = pd.DataFrame([{
                        "id_lote": nuevo_id,
                        "ubicacion": f_ubi.strip().upper(),
                        "fase": f_fase,
                        "precio": f_pre,
                        "comision": f_com,
                        "estatus": "Disponible"
                    }])

                    df_act = pd.concat([df_u, nueva_ub], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_act)
                    st.success(f"✅ Lote {f_ubi} registrado con ID {nuevo_id}.")
                    st.cache_data.clear(); st.rerun()
