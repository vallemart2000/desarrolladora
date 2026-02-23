import streamlit as st
import pandas as pd

def render_clientes(df_c, conn, URL_SHEET, cargar_datos):
    st.title("👥 Gestión de Clientes")
    
    # --- VISTA GENERAL ---
    st.write("### 🔍 Directorio de Clientes")
    if not df_c.empty:
        # 1. Definimos las columnas que queremos mostrar, incluyendo el ID
        columnas_visibles = ["id_cliente", "nombre", "telefono", "correo", "direccion", "notas"]
        cols_existentes = [c for c in columnas_visibles if c in df_c.columns]
        
        # 2. Diccionario para renombrar a "Nombre Propio"
        nuevos_nombres = {
            "id_cliente": "ID Cliente",
            "nombre": "Nombre Completo",
            "telefono": "Teléfono",
            "correo": "Correo Electrónico",
            "direccion": "Dirección",
            "notas": "Notas"
        }
        
        # Creamos una copia filtrada y renombramos
        df_visual = df_c[cols_existentes].copy().rename(columns=nuevos_nombres)

        # 3. Aplicamos Estilo (Centrado y formato de ID como entero)
        df_estilizado = df_visual.style.format({
            "ID Cliente": "{:,.0f}" # Evita decimales como 1.0
        }).set_table_styles([
            # Centrar encabezados
            {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#f0f2f6')]},
            # Centrar celdas de datos
            {'selector': 'td', 'props': [('text-align', 'center')]}
        ])

        st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
    else:
        st.info("No hay clientes registrados.")

    tab_nuevo, tab_editar = st.tabs(["✨ Agregar Cliente", "✏️ Editar Registro"])

    # --- PESTAÑA 1: AGREGAR ---
    with tab_nuevo:
        with st.form("form_nuevo_cliente"):
            st.subheader("Datos del Nuevo Cliente")
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("👤 Nombre Completo")
            f_tel = c2.text_input("📞 Teléfono")
            f_cor = c1.text_input("📧 Correo Electrónico")
            f_dir = c2.text_input("📍 Dirección")
            f_not = st.text_area("📝 Notas adicionales")
            
            nuevo_id = 1
            if not df_c.empty and "id_cliente" in df_c.columns:
                try:
                    nuevo_id = int(float(df_c["id_cliente"].max())) + 1
                except:
                    nuevo_id = len(df_c) + 1
            
            if st.form_submit_button("➕ REGISTRAR CLIENTE"):
                if not f_nom:
                    st.error("El nombre es obligatorio.")
                else:
                    nuevo_reg = pd.DataFrame([{"id_cliente": nuevo_id, "nombre": f_nom, "telefono": f_tel, "correo": f_cor, "direccion": f_dir, "notas": f_not}])
                    df_c = pd.concat([df_c, nuevo_reg], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_c)
                    st.success(f"✅ Cliente {f_nom} registrado."); st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: EDITAR ---
    with tab_editar:
        if not df_c.empty:
            cli_lista = (df_c["id_cliente"].astype(str) + " | " + df_c["nombre"]).tolist()
            c_sel = st.selectbox("Seleccione el cliente a modificar:", ["--"] + cli_lista)
            
            if c_sel != "--":
                id_c_sel = int(float(c_sel.split(" | ")[0]))
                idx = df_c[df_c["id_cliente"].astype(float).astype(int) == id_c_sel].index[0]
                row = df_c.loc[idx]
                
                with st.form("form_edit_cliente"):
                    ce1, ce2 = st.columns(2)
                    e_nom = ce1.text_input("Nombre Completo", value=row["nombre"])
                    e_tel = ce2.text_input("Teléfono", value=str(row.get("telefono", "")))
                    e_cor = ce1.text_input("Correo Electrónico", value=str(row.get("correo", "")))
                    e_dir = ce2.text_input("Dirección", value=str(row.get("direccion", "")))
                    e_not = st.text_area("Notas", value=str(row.get("notas", "")))
                    
                    cb1, cb2 = st.columns(2)
                    if cb1.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df_c.at[idx, "nombre"], df_c.at[idx, "telefono"] = e_nom, e_tel
                        df_c.at[idx, "correo"], df_c.at[idx, "direccion"] = e_cor, e_dir
                        df_c.at[idx, "notas"] = e_not
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_c)
                        st.success("Actualizado."); st.cache_data.clear(); st.rerun()
                        
                    if cb2.form_submit_button("🗑️ ELIMINAR"):
                        df_c = df_c.drop(idx)
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_c)
                        st.error("Eliminado."); st.cache_data.clear(); st.rerun()
