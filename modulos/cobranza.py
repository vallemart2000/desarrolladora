import streamlit as st
import pandas as pd
from datetime import datetime

def render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("💰 Gestión de Cobranza")
    
    tab_pago, tab_historial = st.tabs(["💵 Registrar Nuevo Pago", "📋 Historial y Edición"])

    # ---------------------------------------------------------
    # PESTAÑA 1: REGISTRAR PAGO
    # ---------------------------------------------------------
    with tab_pago:
        if df_v.empty:
            st.warning("No hay ventas registradas.")
        else:
            opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            seleccion = st.selectbox("🔍 Seleccione Contrato:", ["--"] + opciones_vta, key="sel_cobro")
            
            if seleccion != "--":
                ubi_sel = seleccion.split(" | ")[0]
                v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
                
                # Cálculos de deuda sugerida
                p_previos = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty and "monto" in df_p.columns else 0
                f_con = pd.to_datetime(v['fecha'])
                hoy = datetime.now()
                meses_t = (hoy.year - f_con.year) * 12 + (hoy.month - f_con.month)
                deuda_esp = max(0, min(meses_t, int(v['plazo_meses']))) * float(v['mensualidad'])
                s_vencido = max(0, deuda_esp - p_previos)
                
                monto_sug = s_vencido if s_vencido > 0 else float(v['mensualidad'])
                
                if s_vencido > 0:
                    st.error(f"⚠️ Atraso detectado: {fmt_moneda(s_vencido)}")
                else:
                    st.success(f"✅ Al corriente. Sugerido: {fmt_moneda(monto_sug)}")

                with st.form("form_nuevo_pago_modular"):
                    c1, c2, c3 = st.columns(3)
                    f_fec = c1.date_input("Fecha", value=datetime.now())
                    f_met = c2.selectbox("Método", ["Efectivo", "Transferencia", "Depósito"])
                    f_fol = c3.text_input("Folio Comprobante")
                    
                    col_m, col_r = st.columns([2, 1])
                    f_mon = col_m.number_input("Importe ($)", min_value=0.0, value=monto_sug)
                    if col_r.form_submit_button("🔄 Actualizar"): st.rerun()
                    
                    f_com = st.text_area("Notas")
                    if st.form_submit_button("✅ REGISTRAR PAGO", type="primary"):
                        nid = 1
                        if not df_p.empty and "id_pago" in df_p.columns:
                            try: nid = int(float(df_p["id_pago"].max())) + 1
                            except: nid = len(df_p) + 1
                        
                        nuevo = pd.DataFrame([{
                            "id_pago": nid, "fecha": f_fec.strftime('%Y-%m-%d'), 
                            "ubicacion": ubi_sel, "cliente": v['cliente'], 
                            "monto": f_mon, "metodo": f_met, "folio": f_fol, "comentarios": f_com
                        }])
                        df_p = pd.concat([df_p, nuevo], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                        st.success("Pago registrado"); st.cache_data.clear(); st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: HISTORIAL Y EDICIÓN
    # ---------------------------------------------------------
    with tab_historial:
        st.subheader("Historial de Pagos")
        if df_p.empty:
            st.info("No hay pagos registrados.")
        else:
            # Selector para editar
            opciones_edit = []
            for _, fila in df_p.iterrows():
                id_l = int(float(fila['id_pago']))
                opciones_edit.append(f"{id_l} | {fila['fecha']} | {fila['ubicacion']} | {fmt_moneda(fila['monto'])}")
            
            pago_sel = st.selectbox("✏️ Seleccione para modificar o eliminar:", ["--"] + opciones_edit[::-1])
            
            if pago_sel != "--":
                id_p_sel = int(float(pago_sel.split(" | ")[0]))
                idx_pago = df_p[df_p["id_pago"].astype(float).astype(int) == id_p_sel].index[0]
                datos_p = df_p.loc[idx_pago]

                with st.expander("🛠️ Panel de Edición", expanded=True):
                    with st.form("edit_pago_modular"):
                        ec1, ec2, ec3 = st.columns(3)
                        e_fec = ec1.date_input("Fecha", value=pd.to_datetime(datos_p["fecha"]))
                        e_met = ec2.selectbox("Método", ["Efectivo", "Transferencia", "Depósito"], 
                                             index=["Efectivo", "Transferencia", "Depósito"].index(datos_p["metodo"]) if datos_p["metodo"] in ["Efectivo", "Transferencia", "Depósito"] else 0)
                        e_fol = ec3.text_input("Folio", value=str(datos_p.get("folio", "")))
                        e_mon = st.number_input("Monto ($)", min_value=0.0, value=float(datos_p["monto"]))
                        e_com = st.text_area("Comentarios", value=str(datos_p.get("comentarios", "")))
                        
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("💾 GUARDAR CAMBIOS"):
                            df_p.at[idx_pago, "fecha"] = e_fec.strftime('%Y-%m-%d')
                            df_p.at[idx_pago, "metodo"], df_p.at[idx_pago, "folio"] = e_met, e_fol
                            df_p.at[idx_pago, "monto"], df_p.at[idx_pago, "comentarios"] = e_mon, e_com
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            st.success("¡Pago actualizado!"); st.cache_data.clear(); st.rerun()
                            
                        if b2.form_submit_button("🗑️ ELIMINAR PAGO"):
                            df_p = df_p.drop(idx_pago)
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            st.error("Pago eliminado."); st.cache_data.clear(); st.rerun()

            st.divider()
            
            # --- NUEVA LÓGICA DE TABLA ESTILIZADA ---
            # 1. Renombrado y Ocultamiento de ID
            nuevos_nombres_p = {
                "fecha": "Fecha de Pago",
                "ubicacion": "Ubicación",
                "cliente": "Cliente",
                "monto": "Monto Pagado",
                "metodo": "Método",
                "folio": "Folio / Referencia",
                "comentarios": "Notas"
            }
            
            df_visual_p = df_p.drop(columns=["id_pago"], errors="ignore").rename(columns=nuevos_nombres_p)
            
            # 2. Asegurar formato de fecha para el estilizado
            df_visual_p["Fecha de Pago"] = pd.to_datetime(df_visual_p["Fecha de Pago"])
            
            # 3. Aplicar Formatos y Centrado
            df_p_estilizado = df_visual_p.style.format({
                "Fecha de Pago": lambda t: t.strftime('%d-%b-%Y'),
                "Monto Pagado": "$ {:,.2f}"
            }).set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#f0f2f6')]},
                {'selector': 'td', 'props': [('text-align', 'center')]}
            ])
            
            st.dataframe(df_p_estilizado, use_container_width=True, hide_index=True)
