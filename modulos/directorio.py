import streamlit as st
import pandas as pd

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Verifica si faltan columnas y solo actualiza si hay cambios reales."""
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
        except Exception as e:
            if "429" in str(e):
                st.warning(f"⚠️ Google está ocupado. Sincronizando...")
            else:
                st.error(f"Error al reparar {worksheet_name}: {e}")
    return df

def render_directorio(df_cl, df_vd, conn, URL_SHEET):
    st.title("📇 Directorio General")

    # Definición de estructuras
    cols_cl = {"id_cliente": 1001, "nombre": "", "telefono": "", "correo": ""}
    cols_vd = {"id_vendedor": 1001, "nombre": "", "telefono": "", "correo": "", "comision_acumulada": 0.0}
    
    # Ejecutar reparación
    df_cl = verificar_y_reparar_columnas(df_cl, cols_cl, "clientes", conn, URL_SHEET)
    df_vd = verificar_y_reparar_columnas(df_vd, cols_vd, "vendedores", conn, URL_SHEET)

    tab_clientes, tab_vendedores = st.tabs(["👥 Directorio de Clientes", "👔 Equipo de Vendedores"])

    # --- TABLA CLIENTES ---
    with tab_clientes:
        st.subheader("Gestión de Clientes")
        
        c1, c2 = st.columns(2)
        with c1.expander("➕ Registrar Nuevo Cliente"):
            with st.form("form_nuevo_cl"):
                f_nom = st.text_input("Nombre Completo *")
                f_tel = st.text_input("Teléfono")
                f_eml = st.text_input("Correo")
                if st.form_submit_button("💾 Guardar Cliente", type="primary"):
                    if not f_nom:
                        st.error("Nombre obligatorio.")
                    else:
                        nid = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1001
                        nuevo = pd.DataFrame([{"id_cliente": nid, "nombre": f_nom.strip(), "telefono": f_tel.strip(), "correo": f_eml.strip()}])
                        df_cl = pd.concat([df_cl, nuevo], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                        st.success("✅ Cliente registrado."); st.cache_data.clear(); st.rerun()

        with c2.expander("✏️ Editar Cliente Existente"):
            if df_cl.empty:
                st.info("No hay clientes para editar.")
            else:
                cliente_a_editar = st.selectbox("Seleccione cliente", df_cl["nombre"].tolist(), key="edit_cl_select")
                idx_cl = df_cl[df_cl["nombre"] == cliente_a_editar].index[0]
                
                with st.form("form_edit_cl"):
                    e_nom = st.text_input("Nombre", value=df_cl.at[idx_cl, "nombre"])
                    e_tel = st.text_input("Teléfono", value=str(df_cl.at[idx_cl, "telefono"]))
                    e_eml = st.text_input("Correo", value=str(df_cl.at[idx_cl, "correo"]))
                    
                    if st.form_submit_button("💾 Actualizar Datos"):
                        df_cl.at[idx_cl, "nombre"] = e_nom.strip()
                        df_cl.at[idx_cl, "telefono"] = e_tel.strip()
                        df_cl.at[idx_cl, "correo"] = e_eml.strip()
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                        st.success("✅ Datos actualizados."); st.cache_data.clear(); st.rerun()

        st.markdown("---")
        busqueda_cl = st.text_input("🔍 Buscar cliente", "", key="search_cl")
        df_m_cl = df_cl[df_cl['nombre'].str.contains(busqueda_cl, case=False, na=False)] if busqueda_cl else df_cl
        st.dataframe(df_m_cl, use_container_width=True, hide_index=True)

    # --- TABLA VENDEDORES ---
    with tab_vendedores:
        st.subheader("Equipo de Ventas")

        cv1, cv2 = st.columns(2)
        with cv1.expander("➕ Registrar Nuevo Vendedor"):
            with st.form("form_nuevo_vd"):
                f_nom_v = st.text_input("Nombre Vendedor *")
                f_tel_v = st.text_input("Teléfono")
                if st.form_submit_button("💾 Registrar Vendedor", type="primary"):
                    if not f_nom_v:
                        st.error("Nombre obligatorio.")
                    else:
                        nid_v = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 501
                        nuevo_v = pd.DataFrame([{"id_vendedor": nid_v, "nombre": f_nom_v.strip(), "telefono": f_tel_v.strip(), "comision_acumulada": 0.0}])
                        df_vd = pd.concat([df_vd, nuevo_v], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)
                        st.success("✅ Vendedor registrado."); st.cache_data.clear(); st.rerun()

        with cv2.expander("✏️ Editar Vendedor Existente"):
            if df_vd.empty:
                st.info("No hay vendedores para editar.")
            else:
                vendedor_a_editar = st.selectbox("Seleccione vendedor", df_vd["nombre"].tolist(), key="edit_vd_select")
                idx_vd = df_vd[df_vd["nombre"] == vendedor_a_editar].index[0]
                
                with st.form("form_edit_vd"):
                    e_nom_v = st.text_input("Nombre", value=df_vd.at[idx_vd, "nombre"])
                    e_tel_v = st.text_input("Teléfono", value=str(df_vd.at[idx_vd, "telefono"]))
                    # No editamos comisión acumulada aquí por seguridad contable
                    
                    if st.form_submit_button("💾 Actualizar Datos"):
                        df_vd.at[idx_vd, "nombre"] = e_nom_v.strip()
                        df_vd.at[idx_vd, "telefono"] = e_tel_v.strip()
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)
                        st.success("✅ Datos actualizados."); st.cache_data.clear(); st.rerun()

        st.markdown("---")
        busqueda_vd = st.text_input("🔍 Buscar vendedor", "", key="search_vd")
        df_m_vd = df_vd[df_vd['nombre'].str.contains(busqueda_vd, case=False, na=False)] if busqueda_vd else df_vd
        st.dataframe(df_m_vd, column_config={
            "comision_acumulada": st.column_config.NumberColumn("Comisiones", format="$ %.2f")
        }, use_container_width=True, hide_index=True)
