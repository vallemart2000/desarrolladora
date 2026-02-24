import streamlit as st
import pandas as pd

def render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos):
    st.title("📍 Gestión de Inventario (Ubicaciones)")

    tab_lista, tab_nuevo, tab_editar = st.tabs(["📋 Inventario Actual", "➕ Agregar Lote", "✏️ Editar Ubicación"])

    # --- PESTAÑA 1: LISTA ---
    with tab_lista:
        st.subheader("Control de Lotes y Disponibilidad")
        if df_u.empty:
            st.info("No hay lotes registrados.")
        else:
            ocultar_vendidos = st.toggle("Ocultar ubicaciones vendidas", value=True)
            
            df_mostrar = df_u.copy()
            if ocultar_vendidos:
                df_mostrar = df_mostrar[df_mostrar["estatus"] != "Vendido"]

            st.dataframe(
                df_mostrar,
                column_config={
                    "id_lote": st.column_config.NumberColumn("ID", format="%d"),
                    "manzana": "Mz",
                    "lote": "Lt",
                    "ubicacion": "Ubicación",
                    "precio": st.column_config.NumberColumn("Precio Lista", format="$ %.2f"),
                    "enganche_req": st.column_config.NumberColumn("Enganche Req.", format="$ %.2f"),
                    "estatus": st.column_config.SelectboxColumn("Estatus", options=["Disponible", "Vendido", "Apartado", "Bloqueado"])
                },
                use_container_width=True,
                hide_index=True
            )

    # --- PESTAÑA 2: NUEVO LOTE ---
    with tab_nuevo:
        st.subheader("Registrar Nueva Ubicación")
        with st.form("form_nueva_ub"):
            c_top1, c_top2 = st.columns(2)
            f_mz = c_top1.number_input("Número de Manzana", min_value=1, step=1, value=1)
            f_lt = c_top2.number_input("Número de Lote", min_value=1, step=1, value=1)
            f_fase = c_top1.selectbox("Fase/Etapa", ["Etapa 1", "Etapa 2", "Etapa 3", "Club"])
            
            c_bot1, c_bot2 = st.columns(2)
            f_pre = c_bot1.number_input("Precio de Lista ($)", min_value=0.0, step=1000.0)
            # Cambiado de comisión a Enganche Requerido
            f_eng = c_bot2.number_input("Enganche Requerido para Contrato ($)", min_value=0.0, step=500.0)
            
            nombre_generado = f"M{int(f_mz):02d}-L{int(f_lt):02d}"
            
            st.markdown("---")
            st.info(f"📝 **Resumen:** Se registrará como **{nombre_generado}** en la **{f_fase}**.")
            
            if st.form_submit_button("💾 Guardar Ubicación", type="primary"):
                if not df_u.empty and nombre_generado in df_u["ubicacion"].values:
                    st.error(f"❌ La ubicación {nombre_generado} ya existe.")
                else:
                    nuevo_id = 1001 if df_u.empty else int(df_u["id_lote"].max() + 1)

                    nueva_ub = pd.DataFrame([{
                        "id_lote": nuevo_id,
                        "manzana": int(f_mz),
                        "lote": int(f_lt),
                        "ubicacion": nombre_generado,
                        "fase": f_fase,
                        "precio": f_pre,
                        "enganche_req": f_eng, # Nueva columna
                        "estatus": "Disponible"
                    }])

                    df_act = pd.concat([df_u, nueva_ub], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_act)
                    st.success(f"✅ {nombre_generado} registrado.")
                    st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 3: EDITAR REGISTRO ---
    with tab_editar:
        st.subheader("Modificar o Eliminar Ubicación")
        if df_u.empty:
            st.info("No hay ubicaciones para editar.")
        else:
            opciones_ubi = df_u["ubicacion"].tolist()
            ubi_sel = st.selectbox("Seleccione la ubicación a gestionar", ["--"] + opciones_ubi)

            if ubi_sel != "--":
                idx = df_u[df_u["ubicacion"] == ubi_sel].index[0]
                datos_actuales = df_u.loc[idx]

                with st.form("form_edit_ub"):
                    st.write(f"🔢 ID: **{datos_actuales['id_lote']}** | Ubicación: **{ubi_sel}**")
                    ce1, ce2 = st.columns(2)
                    
                    e_fase = ce1.selectbox("Fase/Etapa", ["Etapa 1", "Etapa 2", "Etapa 3", "Club"], 
                                         index=["Etapa 1", "Etapa 2", "Etapa 3", "Club"].index(datos_actuales["fase"]) if datos_actuales["fase"] in ["Etapa 1", "Etapa 2", "Etapa 3", "Club"] else 0)
                    e_estatus = ce2.selectbox("Estatus", ["Disponible", "Vendido", "Apartado", "Bloqueado"],
                                            index=["Disponible", "Vendido", "Apartado", "Bloqueado"].index(datos_actuales["estatus"]))
                    
                    e_pre = ce1.number_input("Precio de Lista ($)", min_value=0.0, value=float(datos_actuales["precio"]))
                    # Editando el Enganche Requerido
                    e_eng = ce2.number_input("Enganche Requerido ($)", min_value=0.0, value=float(datos_actuales.get("enganche_req", 0.0)))

                    st.markdown("---")
                    st.warning("⚠️ **Zona de Peligro**")
                    confirmar_borrado = st.checkbox(f"Confirmar eliminación de {ubi_sel}")
                    
                    c_save, c_del = st.columns(2)
                    
                    if c_save.form_submit_button("💾 Guardar Cambios", type="primary"):
                        df_u.at[idx, "fase"] = e_fase
                        df_u.at[idx, "estatus"] = e_estatus
                        df_u.at[idx, "precio"] = e_pre
                        df_u.at[idx, "enganche_req"] = e_eng

                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                        st.success(f"✅ {ubi_sel} actualizada."); st.cache_data.clear(); st.rerun()
                    
                    if c_del.form_submit_button("🗑️ Eliminar Ubicación"):
                        if confirmar_borrado:
                            df_u = df_u.drop(idx)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.error(f"🗑️ {ubi_sel} eliminada."); st.cache_data.clear(); st.rerun()
                        else:
                            st.warning("❌ Confirma para eliminar.")
