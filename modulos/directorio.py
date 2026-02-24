import streamlit as st
import pandas as pd

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Verifica si faltan columnas y las agrega al DataFrame y a la base de datos."""
    cambios = False
    # Si df es None por algún error de carga, inicializamos uno vacío con las columnas
    if df is None:
        df = pd.DataFrame(columns=columnas_necesarias.keys())
        cambios = True

    for col, default_val in columnas_necesarias.items():
        if col not in df.columns:
            df[col] = default_val
            cambios = True
    
    if cambios:
        try:
            conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
            st.toast(f"🛠️ Estructura de '{worksheet_name}' actualizada.")
        except Exception as e:
            st.error(f"Error al reparar columnas en {worksheet_name}: {e}")
    return df

def render_directorio(df_cl, df_vd, conn, URL_SHEET):
    st.title("📇 Directorio General")

    # --- 1. CONFIGURACIÓN DE COLUMNAS ---
    cols_cl = {"id_cliente": 1001, "nombre": "Sin Nombre", "telefono": "", "correo": ""}
    cols_vd = {"id_vendedor": 1001, "nombre": "Sin Nombre", "telefono": "", "correo": "", "comision_acumulada": 0.0}
    
    # Reparar si es necesario
    df_cl = verificar_y_reparar_columnas(df_cl, cols_cl, "clientes", conn, URL_SHEET)
    df_vd = verificar_y_reparar_columnas(df_vd, cols_vd, "vendedores", conn, URL_SHEET)

    tab_clientes, tab_vendedores = st.tabs(["👥 Directorio de Clientes", "👔 Equipo de Vendedores"])

    # --- PESTAÑA 1: CLIENTES ---
    with tab_clientes:
        st.subheader("Gestión de Clientes")
        busqueda_cl = st.text_input("🔍 Buscar cliente por nombre", "", key="search_cl")
        
        with st.expander("➕ Registrar Nuevo Cliente"):
            with st.form("form_nuevo_cl"):
                f_nom = st.text_input("Nombre Completo *")
                f_tel = st.text_input("Teléfono")
                f_eml = st.text_input("Correo Electrónico")
                if st.form_submit_button("💾 Guardar Cliente", type="primary"):
                    if not f_nom:
                        st.error("El nombre es obligatorio.")
                    else:
                        nid = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1001
                        nuevo = pd.DataFrame([{"id_cliente": nid, "nombre": f_nom.strip(), "telefono": f_tel.strip(), "correo": f_eml.strip()}])
                        df_act = pd.concat([df_cl, nuevo], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_act)
                        st.success(f"✅ Cliente registrado."); st.cache_data.clear(); st.rerun()

        df_m_cl = df_cl[df_cl['nombre'].str.contains(busqueda_cl, case=False, na=False)] if busqueda_cl else df_cl
        st.dataframe(df_m_cl, column_config={
            "id_cliente": st.column_config.NumberColumn("ID", format="%d"),
            "nombre": "Nombre", "telefono": "Teléfono", "correo": "Correo"
        }, use_container_width=True, hide_index=True)

    # --- PESTAÑA 2: VENDEDORES ---
    with tab_vendedores:
        st.subheader("Equipo de Ventas")
        busqueda_vd = st.text_input("🔍 Buscar vendedor por nombre", "", key="search_vd")

        with st.expander("➕ Registrar Nuevo Vendedor"):
            with st.form("form_nuevo_vd"):
                f_nom_v = st.text_input("Nombre del Vendedor *")
                f_tel_v = st.text_input("Teléfono de Contacto")
                f_eml_v = st.text_input("Correo Electrónico")
                if st.form_submit_button("💾 Registrar Vendedor", type="primary"):
                    if not f_nom_v:
                        st.error("El nombre es obligatorio.")
                    else:
                        nid_v = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 1001
                        nuevo_v = pd.DataFrame([{
                            "id_vendedor": nid_v, "nombre": f_nom_v.strip(), 
                            "telefono": f_tel_v.strip(), "correo": f_eml_v.strip(),
                            "comision_acumulada": 0.0
                        }])
                        df_act_v = pd.concat([df_vd, nuevo_v], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_act_v)
                        st.success(f"✅ Vendedor registrado."); st.cache_data.clear(); st.rerun()

        df_m_vd = df_vd[df_vd['nombre'].str.contains(busqueda_vd, case=False, na=False)] if busqueda_vd else df_vd
        st.dataframe(df_m_vd, column_config={
            "id_vendedor": st.column_config.NumberColumn("ID", format="%d"),
            "nombre": "Nombre", "telefono": "Teléfono", 
            "comision_acumulada": st.column_config.NumberColumn("Comisiones Ganadas", format="$ %.2f")
        }, use_container_width=True, hide_index=True)
