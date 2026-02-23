import streamlit as st
import pandas as pd

def render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos):
    st.title("📍 Control de Inventario")
    
    # --- FILTRO TIPO SWITCH (Activo por defecto) ---
    st.write("### 🔍 Vista de Inventario")
    ocultar_vendidos = st.toggle("Ocultar Lotes Vendidos", value=True)

    df_mostrar = df_u.copy()
    if ocultar_vendidos:
        df_mostrar = df_u[df_u["estatus"] == "Disponible"]

    # Selección de columnas visibles para el usuario (ID oculto)
    columnas_visibles = ["ubicacion", "fase", "manzana", "lote", "precio", "estatus"]
    cols_existentes = [c for c in columnas_visibles if c in df_mostrar.columns]
    
    st.dataframe(df_mostrar[cols_existentes], use_container_width=True, hide_index=True)

    tab_nueva, tab_editar = st.tabs(["✨ Agregar Ubicación", "✏️ Editar Registro"])

    # ---------------------------------------------------------
    # PESTAÑA 1: AGREGAR NUEVA UBICACIÓN
    # ---------------------------------------------------------
    with tab_nueva:
        with st.form("form_nueva_ubi"):
            st.subheader("Registrar Nuevo Lote")
            c1, c2 = st.columns(2)
            
            f_manzana = c1.number_input("🍎 Manzana", min_value=1, step=1, value=1)
            f_lote = c2.number_input("🔢 Lote", min_value=1, step=1, value=1)
            f_fase = c1.text_input("🏗️ Fase / Etapa", placeholder="Ej: Fase 1")
            f_pre = c2.number_input("💵 Precio de Lista ($)", min_value=0.0, step=1000.0)
            
            # Generación de ID automática
            nuevo_id_sugerido = 1
            if not df_u.empty and "id_lote" in df_u.columns:
                try:
                    nuevo_id_sugerido = int(float(df_u["id_lote"].max())) + 1
                except:
                    nuevo_id_sugerido = len(df_u) + 1
            
            nombre_gen = f"M{str(f_manzana).zfill(2)}-L{str(f_lote).zfill(2)}"
            st.info(f"💡 Ubicación a registrar: **{nombre_gen}** (ID interno: {nuevo_id_sugerido})")

            if st.form_submit_button("➕ AGREGAR AL INVENTARIO"):
                nueva_fila = pd.DataFrame([{
                    "id_lote": nuevo_id_sugerido,
                    "ubicacion": nombre_gen,
                    "manzana": f_manzana,
                    "lote": f_lote,
                    "fase": f_fase,
                    "precio": f_pre,
                    "estatus": "Disponible"
                }])
                
                df_u = pd.concat([df_u, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                st.success(f"✅ Lote {nombre_gen} agregado."); st.cache_data.clear(); st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: EDITAR REGISTROS
    # ---------------------------------------------------------
    with tab_editar:
        if not df_u.empty:
            ubi_lista = (df_u["id_lote"].astype(str) + " | " + df_u["ubicacion"]).tolist()
            u_sel = st.selectbox("Seleccione el lote a modificar:", ["--"] + ubi_lista)
            
            if u_sel != "--":
                id_u_sel = int(float(u_sel.split(" | ")[0]))
                idx = df_u[df_u["id_lote"].astype(float).astype(int) == id_u_sel].index[0]
                row = df_u.loc[idx]
                
                with st.form("form_edit_ubi"):
                    st.write(f"✏️ Editando: **{row['ubicacion']}**")
                    ce1, ce2 = st.columns(2)
                    e_pre = ce1.number_input("Precio Actualizado ($)", min_value=0.0, value=float(row.get("precio", 0.0)))
                    e_est = ce2.selectbox("Estatus", ["Disponible", "Vendido", "Apartado", "Bloqueado"], 
                                         index=["Disponible", "Vendido", "Apartado", "Bloqueado"].index(row["estatus"]))
                    e_fas = ce1.text_input("Fase", value=str(row.get("fase", "")))
                    
                    cb1, cb2 = st.columns(2)
                    if cb1.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df_u.at[idx, "precio"], df_u.at[idx, "estatus"], df_u.at[idx, "fase"] = e_pre, e_est, e_fas
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                        st.success("Cambios guardados."); st.cache_data.clear(); st.rerun()
                        
                    if cb2.form_submit_button("🗑️ ELIMINAR"):
                        df_u = df_u.drop(idx)
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                        st.error("Ubicación eliminada."); st.cache_data.clear(); st.rerun()
