import streamlit as st
import pandas as pd
from datetime import datetime

def render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("💸 Gestión de Gastos")
    
    # --- VISTA GENERAL ---
    st.write("### 🔍 Historial de Gastos")
    if not df_g.empty:
        # Mostramos la tabla principal
        st.dataframe(df_g, use_container_width=True, hide_index=True)
        total_gastos = df_g["monto"].sum()
        st.info(f"💰 **Gasto Total Acumulado:** {fmt_moneda(total_gastos)}")
    else:
        st.info("No hay gastos registrados.")

    tab_nuevo, tab_editar = st.tabs(["✨ Registrar Gasto", "✏️ Editar / Eliminar"])

    # ---------------------------------------------------------
    # PESTAÑA 1: REGISTRAR NUEVO GASTO
    # ---------------------------------------------------------
    with tab_nuevo:
        with st.form("form_nuevo_gasto"):
            st.subheader("Detalles del Egreso")
            c1, c2 = st.columns(2)
            
            f_fec = c1.date_input("📅 Fecha", value=datetime.now())
            f_cat = c2.selectbox("📂 Categoría", [
                "Publicidad", "Comisiones", "Mantenimiento", 
                "Papelería", "Servicios (Luz/Agua)", "Sueldos", "Otros"
            ])
            
            f_mon = c1.number_input("💵 Monto ($)", min_value=0.0, step=100.0)
            f_des = c2.text_input("📝 Descripción / Concepto", placeholder="Ej: Pago de Facebook Ads")
            
            f_com = st.text_area("🗒️ Notas adicionales")

            # Generación de ID automático
            nuevo_id = 1
            if not df_g.empty and "id_gasto" in df_g.columns:
                try:
                    nuevo_id = int(float(df_g["id_gasto"].max())) + 1
                except:
                    nuevo_id = len(df_g) + 1

            if st.form_submit_button("✅ REGISTRAR GASTO", type="primary"):
                if f_mon <= 0:
                    st.error("El monto debe ser mayor a $0")
                else:
                    nuevo_reg = pd.DataFrame([{
                        "id_gasto": nuevo_id,
                        "fecha": f_fec.strftime('%Y-%m-%d'),
                        "categoria": f_cat,
                        "monto": f_mon,
                        "concepto": f_des,
                        "notas": f_com
                    }])
                    
                    df_g = pd.concat([df_g, nuevo_reg], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=df_g)
                    st.success(f"✅ Gasto por {fmt_moneda(f_mon)} registrado."); st.cache_data.clear(); st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: EDITAR O ELIMINAR
    # ---------------------------------------------------------
    with tab_editar:
        if not df_g.empty:
            gastos_lista = (df_g["id_gasto"].astype(str) + " | " + df_g["fecha"] + " | " + df_g["concepto"]).tolist()
            g_sel = st.selectbox("Seleccione el gasto a modificar:", ["--"] + gastos_lista[::-1])
            
            if g_sel != "--":
                id_g_sel = int(float(g_sel.split(" | ")[0]))
                idx = df_g[df_g["id_gasto"].astype(float).astype(int) == id_g_sel].index[0]
                row = df_g.loc[idx]
                
                with st.form("form_edit_gasto"):
                    st.write(f"✏️ Editando Gasto ID: {id_g_sel}")
                    ce1, ce2 = st.columns(2)
                    
                    e_fec = ce1.date_input("Fecha", value=pd.to_datetime(row["fecha"]))
                    e_cat = ce2.selectbox("Categoría", [
                        "Publicidad", "Comisiones", "Mantenimiento", 
                        "Papelería", "Servicios (Luz/Agua)", "Sueldos", "Otros"
                    ], index=["Publicidad", "Comisiones", "Mantenimiento", "Papelería", "Servicios (Luz/Agua)", "Sueldos", "Otros"].index(row["categoria"]))
                    
                    e_mon = ce1.number_input("Monto ($)", min_value=0.0, value=float(row["monto"]))
                    e_des = ce2.text_input("Concepto", value=str(row["concepto"]))
                    
                    e_com = st.text_area("Notas", value=str(row.get("notas", "")))
                    
                    cb1, cb2 = st.columns(2)
                    if cb1.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df_g.at[idx, "fecha"] = e_fec.strftime('%Y-%m-%d')
                        df_g.at[idx, "categoria"] = e_cat
                        df_g.at[idx, "monto"] = e_mon
                        df_g.at[idx, "concepto"] = e_des
                        df_g.at[idx, "notas"] = e_com
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=df_g)
                        st.success("Gasto actualizado."); st.cache_data.clear(); st.rerun()
                        
                    if cb2.form_submit_button("🗑️ ELIMINAR GASTO"):
                        df_g = df_g.drop(idx)
                        conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=df_g)
                        st.error("Gasto eliminado."); st.cache_data.clear(); st.rerun()
