import streamlit as st
import pandas as pd

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Verifica si faltan columnas y las agrega al DataFrame y a la base de datos."""
    cambios = False
    for col, default_val in columnas_necesarias.items():
        if col not in df.columns:
            df[col] = default_val
            cambios = True
    
    if cambios:
        try:
            conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
            st.toast(f"🛠️ Estructura de '{worksheet_name}' actualizada.")
        except Exception as e:
            st.error(f"Error al reparar columnas: {e}")
    return df

def render_clientes(df_cl, conn, URL_SHEET, cargar_datos):
    st.title("👥 Gestión de Clientes")

    # --- 1. VERIFICACIÓN DE ESTRUCTURA ---
    cols_necesarias = {
        "id_cliente": 1001,
        "nombre": "Sin Nombre",
        "telefono": "",
        "correo": ""
    }
    df_cl = verificar_y_reparar_columnas(df_cl, cols_necesarias, "clientes", conn, URL_SHEET)

    tab_lista, tab_nuevo = st.tabs(["📋 Directorio de Clientes", "➕ Registrar Nuevo"])

    # --- PESTAÑA 1: LISTA DE CLIENTES ---
    with tab_lista:
        st.subheader("Clientes Registrados")
        if df_cl.empty:
            st.info("No hay clientes registrados aún.")
        else:
            # Buscador por nombre
            busqueda = st.text_input("🔍 Buscar cliente por nombre", "")
            if busqueda:
                df_mostrar = df_cl[df_cl['nombre'].str.contains(busqueda, case=False, na=False)]
            else:
                df_mostrar = df_cl

            st.dataframe(
                df_mostrar,
                column_config={
                    "id_cliente": st.column_config.NumberColumn("ID", format="%d"),
                    "nombre": "Nombre Completo",
                    "telefono": "Teléfono",
                    "correo": "Correo Electrónico"
                },
                use_container_width=True,
                hide_index=True
            )

    # --- PESTAÑA 2: REGISTRO NUEVO ---
    with tab_nuevo:
        st.subheader("Agregar Cliente al Sistema")
        
        with st.form("form_nuevo_cliente"):
            col1, col2 = st.columns(2)
            f_nombre = col1.text_input("Nombre Completo *")
            f_tel = col2.text_input("Teléfono (con clave de país, ej: 521...)")
            f_mail = col1.text_input("Correo Electrónico")
            
            st.info("💡 El ID se asignará automáticamente comenzando desde el 1001.")
            
            btn_guardar = st.form_submit_button("💾 Guardar Cliente", type="primary")

            if btn_guardar:
                if not f_nombre:
                    st.error("❌ El nombre es obligatorio.")
                else:
                    # --- LÓGICA DE ID 1001+ ---
                    if df_cl.empty:
                        nuevo_id = 1001
                    else:
                        max_id = df_cl["id_cliente"].max()
                        # Si el ID más alto es menor a 1001, forzamos el inicio en 1001
                        nuevo_id = int(max_id + 1) if max_id >= 1001 else 1001

                    # Crear el nuevo registro
                    nuevo_cliente = pd.DataFrame([{
                        "id_cliente": nuevo_id,
                        "nombre": f_nombre.strip(),
                        "telefono": f_tel.strip(),
                        "correo": f_mail.strip()
                    }])

                    # Concatenar y subir a Google Sheets
                    df_actualizado = pd.concat([df_cl, nuevo_cliente], ignore_index=True)
                    
                    try:
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_actualizado)
                        st.success(f"✅ Cliente '{f_nombre}' registrado con éxito con el ID {nuevo_id}.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

        # --- OPCIÓN DE CARGA MASIVA (Opcional) ---
        st.markdown("---")
        with st.expander("📤 Carga Masiva desde Excel/CSV"):
            archivo = st.file_uploader("Subir archivo", type=["xlsx", "csv"])
            if archivo:
                df_subida = pd.read_excel(archivo) if archivo.name.endswith('xlsx') else pd.read_csv(archivo)
                st.write("Vista previa de datos a importar:")
                st.dataframe(df_subida.head())
                
                if st.button("Confirmar Importación Masiva"):
                    # Aquí se podría aplicar la misma lógica de ID correlativo para cada fila
                    st.warning("Función en desarrollo: Asegúrate de que las columnas coincidan.")
