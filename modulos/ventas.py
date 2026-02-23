import streamlit as st
import pandas as pd
from datetime import datetime

def render_ventas(df_v, df_u, df_cl, df_vd, conn, URL_SHEET, fmt_moneda):
    st.title("📝 Gestión de Ventas")
    
    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta", "✏️ Editor de Ventas", "📋 Historial"])

    # ---------------------------------------------------------
    # PESTAÑA 1: NUEVA VENTA
    # ---------------------------------------------------------
    with tab_nueva:
        st.subheader("Registrar Contrato Nuevo")
        
        # Filtramos solo los lotes disponibles
        lotes_libres = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
        
        if not lotes_libres:
            st.warning("No hay lotes disponibles en el inventario.")
        else:
            f_lote = st.selectbox("📍 Seleccione Lote a Vender", ["--"] + lotes_libres, key="nv_lote")
            
            if f_lote != "--":
                # EXTRAEMOS LA FILA DE LA UBICACIÓN SELECCIONADA
                row_u = df_u[df_u["ubicacion"] == f_lote].iloc[0]
                
                # JALAMOS PRECIO Y COMISIÓN SUGERIDOS (con seguridad por si no existen las columnas)
                costo_base = float(row_u.get('precio', 0.0))
                comision_base = float(row_u.get('comision', 0.0))
                
                st.info(f"💰 Datos sugeridos para {f_lote}: Precio {fmt_moneda(costo_base)} | Comisión {fmt_moneda(comision_base)}")

                with st.form("form_nueva_venta_modular"):
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha de Contrato", value=datetime.now())
                    
                    vendedores_list = ["-- SELECCIONAR --"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
                    col_v1, col_v2 = st.columns([2, 1])
                    f_vende_sel = col_v1.selectbox("👔 Vendedor Registrado", vendedores_list)
                    f_vende_nuevo = col_v2.text_input("🆕 Nuevo Vendedor")
                    
                    st.write("👤 **Información del Cliente**")
                    clientes_list = ["-- SELECCIONAR --"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
                    col_c1, col_c2 = st.columns([2, 1])
                    f_cli_sel = col_c1.selectbox("Cliente Registrado", clientes_list)
                    f_cli_nuevo = col_c2.text_input("🆕 Nuevo Cliente")
                    
                    st.markdown("---")
                    st.write("💰 **Condiciones Financieras**")
                    cf1, cf2 = st.columns(2)
                    f_tot = cf1.number_input("Precio Final de Venta ($)", min_value=0.0, value=costo_base)
                    f_eng = cf2.number_input("Enganche Recibido ($)", min_value=0.0)
                    
                    cf1_b, cf2_b = st.columns(2)
                    # AQUÍ SE ASIGNA LA COMISIÓN AUTOMÁTICAMENTE
                    f_comision = cf1_b.number_input("Monto de Comisión ($)", min_value=0.0, value=comision_base)
                    f_pla = cf2_b.number_input("🕒 Plazo en Meses", min_value=1, value=12)
                    
                    st.markdown("---")
                    # Cálculo de mensualidad
                    m_calc = (f_tot - f_eng) / f_pla if f_pla > 0 else 0
                    
                    col_met, col_btn = st.columns([2, 1])
                    col_met.metric("Mensualidad Resultante", fmt_moneda(m_calc))
                    
                    if col_btn.form_submit_button("🔄 Actualizar Cálculos"):
                        st.rerun()

                    f_coment = st.text_area("📝 Comentarios de la venta")

                    if st.form_submit_button("💾 GUARDAR VENTA", type="primary"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "-- SELECCIONAR --" or not cliente_final:
                            st.error("❌ Error: Debe asignar un cliente.")
                        else:
                            # Alta rápida de cliente si es nuevo
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1
                                nuevo_cli = pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo, "telefono": "", "correo": ""}])
                                df_cl = pd.concat([df_cl, nuevo_cli], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                            
                            # Alta rápida de vendedor si es nuevo
                            if f_vende_nuevo:
                                nid_v = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 1
                                nuevo_vd = pd.DataFrame([{"id_vendedor": nid_v, "nombre": f_vende_nuevo, "telefono": "", "comision_base": 0}])
                                df_vd = pd.concat([df_vd, nuevo_vd], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)

                            # Registro de la venta
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, 
                                "fecha": f_fec.strftime('%Y-%m-%d'), 
                                "ubicacion": f_lote,
                                "cliente": cliente_final, 
                                "vendedor": vendedor_final, 
                                "precio_total": f_tot,
                                "enganche": f_eng, 
                                "plazo_meses": f_pla, 
                                "mensualidad": m_calc, 
                                "comision": f_comision, 
                                "comentarios": f_coment, 
                                "estatus_pago": "Activo"
                            }])
                            
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            # Actualizar estatus del lote en ubicaciones
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success("✅ Venta registrada con éxito.")
                            st.cache_data.clear()
                            st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: EDITOR DE VENTAS
    # ---------------------------------------------------------
    with tab_editar:
        st.subheader("Modificar Venta Existente")
        if df_v.empty:
            st.info("No hay ventas para editar.")
        else:
            lista_ventas = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            edit_sel = st.selectbox("Seleccione la venta a corregir", ["--"] + lista_ventas)
            
            if edit_sel != "--":
                id_ubi_sel = edit_sel.split(" | ")[0]
                datos_v = df_v[df_v["ubicacion"] == id_ubi_sel].iloc[0]
                
                with st.form("form_editor_ventas_mod"):
                    st.write(f"✏️ Editando: **{id_ubi_sel}**")
                    ce1, ce2 = st.columns(2)
                    e_fec = ce1.date_input("Fecha", value=pd.to_datetime(datos_v["fecha"]))
                    
                    cli_lista_nombres = df_cl["nombre"].tolist() if not df_cl.empty else []
                    vd_lista_nombres = df_vd["nombre"].tolist() if not df_vd.empty else []
                    
                    e_cli = ce1.selectbox("Cliente", cli_lista_nombres, index=cli_lista_nombres.index(datos_v["cliente"]) if datos_v["cliente"] in cli_lista_nombres else 0)
                    e_vende = ce2.selectbox("Vendedor", vd_lista_nombres, index=vd_lista_nombres.index(datos_v["vendedor"]) if datos_v["vendedor"] in vd_lista_nombres else 0)
                    
                    e1, e2 = st.columns(2)
                    e_tot = e1.number_input("Precio Final ($)", min_value=0.0, value=float(datos_v["precio_total"]))
                    e_eng = e2.number_input("Enganche ($)", min_value=0.0, value=float(datos_v["enganche"]))
                    
                    e1_b, e2_b = st.columns(2)
                    e_com = e1_b.number_input("Comisión ($)", min_value=0.0, value=float(datos_v.get("comision", 0.0)))
                    e_pla = e2_b.number_input("Plazo (Meses)", min_value=1, value=int(datos_v["plazo_meses"]))
                    
                    e_mensu = (e_tot - e_eng) / e_pla
                    st.metric("Nueva Mensualidad", fmt_moneda(e_mensu))
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        idx = df_v[df_v["ubicacion"] == id_ubi_sel].index[0]
                        df_v.at[idx, "fecha"] = e_fec.strftime('%Y-%m-%d')
                        df_v.at[idx, "cliente"] = e_cli
                        df_v.at[idx, "vendedor"] = e_vende
                        df_v.at[idx, "precio_total"] = e_tot
                        df_v.at[idx, "enganche"] = e_eng
                        df_v.at[idx, "plazo_meses"] = e_pla
                        df_v.at[idx, "mensualidad"] = e_mensu
                        df_v.at[idx, "comision"] = e_com
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("¡Actualizado!")
                        st.cache_data.clear()
                        st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 3: HISTORIAL
    # ---------------------------------------------------------
    with tab_lista:
        if not df_v.empty:
            nuevos_nombres = {
                "fecha": "Fecha", "ubicacion": "Ubicación", "cliente": "Cliente",
                "vendedor": "Vendedor", "precio_total": "Precio Total",
                "enganche": "Enganche", "plazo_meses": "Plazo (Meses)",
                "mensualidad": "Mensualidad", "comision": "Comisión",
                "comentarios": "Comentarios", "estatus_pago": "Estatus"
            }
            
            df_historial = df_v.drop(columns=["id_venta"], errors="ignore").rename(columns=nuevos_nombres)
            df_historial['Fecha'] = pd.to_datetime(df_historial['Fecha'])

            df_final = df_historial.style.format({
                "Fecha": lambda t: t.strftime('%d-%b-%Y'),
                "Precio Total": "$ {:,.2f}",
                "Enganche": "$ {:,.2f}",
                "Mensualidad": "$ {:,.2f}",
                "Comisión": "$ {:,.2f}",
                "Plazo (Meses)": "{:,.0f}"
            }).set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#f0f2f6')]}
            ])

            st.dataframe(df_final, use_container_width=True, hide_index=True)
        else:
            st.info("No hay historial de ventas.")
