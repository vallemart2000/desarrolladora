import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_ventas(df_v, df_u, df_cl, df_vd, df_p, conn, URL_SHEET, fmt_moneda):
    st.title("📝 Gestión de Ventas y Apartados")
    
    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta/Apartado", "✏️ Editor y Archivo", "📋 Historial"])

    # --- PESTAÑA 1: NUEVA VENTA ---
    with tab_nueva:
        st.subheader("Registrar Nuevo Contrato")
        lotes_libres = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
        
        if not lotes_libres:
            st.warning("No hay lotes disponibles.")
        else:
            f_lote = st.selectbox("📍 Seleccione Lote", ["--"] + lotes_libres, key="nv_lote")
            if f_lote != "--":
                row_u = df_u[df_u["ubicacion"] == f_lote].iloc[0]
                costo_base = float(row_u.get('precio', 0.0))
                eng_minimo = float(row_u.get('enganche_req', 0.0))
                
                st.info(f"💰 **Condiciones del Lote:** \n"
                        f"Precio Lista: {fmt_moneda(costo_base)}  \n"
                        f"Enganche Requerido: {fmt_moneda(eng_minimo)}")

                with st.form("form_nueva_venta"):
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha de Contrato", value=datetime.now())
                    
                    vendedores_list = ["-- SELECCIONAR --"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
                    f_vende_sel = c1.selectbox("👔 Vendedor", vendedores_list)
                    f_vende_nuevo = c2.text_input("🆕 ¿Vendedor Nuevo?")
                    
                    st.markdown("---")
                    clientes_list = ["-- SELECCIONAR --"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
                    f_cli_sel = st.selectbox("👤 Cliente", clientes_list)
                    f_cli_nuevo = st.text_input("🆕 ¿Cliente Nuevo?")
                    
                    st.markdown("---")
                    cf1, cf2, cf3 = st.columns(3)
                    f_tot = cf1.number_input("Precio Final de Venta ($)", min_value=0.0, value=costo_base)
                    f_pla = cf2.number_input("🕒 Plazo (Meses)", min_value=1, value=12)
                    f_comision = cf3.number_input("Comisión Pactada ($)", min_value=0.0, step=100.0)
                    
                    f_coment = st.text_area("📝 Notas Adicionales")

                    # Lógica de cálculo solicitada: (Total - Enganche) / Plazo
                    m_calc = (f_tot - eng_minimo) / f_pla if f_pla > 0 else 0
                    
                    st.write(f"📊 **Proyección de Mensualidad:** {fmt_moneda(m_calc)} (al cubrir enganche)")
                    st.warning("⚠️ Al guardar, el lote quedará como **APARTADO**. Los pagos deben registrarse en Cobranza.")

                    if st.form_submit_button("💾 GENERAR CONTRATO", type="primary"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "-- SELECCIONAR --" or not cliente_final:
                            st.error("❌ Indique el cliente.")
                        elif vendedor_final == "-- SELECCIONAR --" or not vendedor_final:
                            st.error("❌ Indique el vendedor.")
                        else:
                            # 1. Alta de nuevos registros (Clientes/Vendedores)
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1001
                                df_cl = pd.concat([df_cl, pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)

                            if f_vende_nuevo:
                                nid_vd = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 501
                                df_vd = pd.concat([df_vd, pd.DataFrame([{"id_vendedor": nid_vd, "nombre": f_vende_nuevo}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)

                            # 2. Registro de la Venta
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, 
                                "fecha_registro": f_fec.strftime('%Y-%m-%d'),
                                "ubicacion": f_lote, 
                                "cliente": cliente_final, 
                                "vendedor": vendedor_final, 
                                "precio_total": f_tot, 
                                "enganche_pagado": 0, # Siempre inicia en 0
                                "enganche_requerido": eng_minimo,
                                "comision_venta": f_comision,
                                "plazo_meses": f_pla, 
                                "mensualidad": m_calc, 
                                "estatus_pago": "Pendiente",
                                "comentarios": f_coment
                            }])
                            
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            
                            # 3. Actualizar Ubicación a APARTADO
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Apartado"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success(f"✅ Contrato {nid_vta} creado. Lote {f_lote} ahora está APARTADO.")
                            st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: EDITOR Y ARCHIVO ---
    with tab_editar:
        st.subheader("Modificar Contratos Existentes")
        if df_v.empty: st.info("No hay ventas registradas.")
        else:
            lista_ventas = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            edit_sel = st.selectbox("Seleccione Contrato", ["--"] + lista_ventas)
            
            if edit_sel != "--":
                id_ubi_sel = edit_sel.split(" | ")[0]
                idx_vta = df_v[df_v["ubicacion"] == id_ubi_sel].index[0]
                datos_v = df_v.loc[idx_vta]
                
                with st.form("form_edit_vta"):
                    e_tot = st.number_input("Precio Final ($)", value=float(datos_v["precio_total"]))
                    e_pla = st.number_input("Plazo (Meses)", value=int(datos_v["plazo_meses"]))
                    e_com = st.number_input("Comisión ($)", value=float(datos_v.get("comision_venta", 0)))
                    
                    st.markdown("---")
                    st.error("🚨 CANCELACIÓN DE VENTA")
                    f_motivo = st.text_input("Motivo de cancelación")
                    
                    c_save, c_cancel = st.columns(2)
                    
                    if c_save.form_submit_button("💾 ACTUALIZAR DATOS"):
                        # Recalcular mensualidad con la misma fórmula
                        eng_req = float(datos_v["enganche_requerido"])
                        df_v.at[idx_vta, "precio_total"] = e_tot
                        df_v.at[idx_vta, "plazo_meses"] = e_pla
                        df_v.at[idx_vta, "comision_venta"] = e_com
                        df_v.at[idx_vta, "mensualidad"] = (e_tot - eng_req) / e_pla
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("Contrato actualizado."); st.cache_data.clear(); st.rerun()

                    if c_cancel.form_submit_button("❌ CANCELAR CONTRATO"):
                        if not f_motivo: st.error("Escriba el motivo.")
                        else:
                            # Mover a archivo (simplificado)
                            df_v = df_v.drop(idx_vta)
                            df_u.loc[df_u["ubicacion"] == id_ubi_sel, "estatus"] = "Disponible"
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.success("Venta cancelada y lote liberado."); st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 3: HISTORIAL ---
    with tab_lista:
        if not df_v.empty:
            st.subheader("📋 Historial")
            df_mostrar = df_v[["id_venta", "ubicacion", "cliente", "precio_total", "mensualidad", "estatus_pago"]].copy()
            st.dataframe(df_mostrar.style.format({"precio_total": "$ {:,.2f}", "mensualidad": "$ {:,.2f}"}), use_container_width=True, hide_index=True)
