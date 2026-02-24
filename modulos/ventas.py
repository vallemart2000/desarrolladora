import streamlit as st
import pandas as pd
from datetime import datetime

# Añadimos df_p a los argumentos de la función
def render_ventas(df_v, df_u, df_cl, df_vd, df_p, conn, URL_SHEET, fmt_moneda):
    st.title("📝 Gestión de Ventas")
    
    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta", "✏️ Editor y Archivo", "📋 Historial"])

    # --- PESTAÑA 1: NUEVA VENTA ---
    with tab_nueva:
        st.subheader("Registrar Contrato Nuevo")
        lotes_libres = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
        
        if not lotes_libres:
            st.warning("No hay lotes disponibles.")
        else:
            f_lote = st.selectbox("📍 Seleccione Lote", ["--"] + lotes_libres, key="nv_lote")
            if f_lote != "--":
                row_u = df_u[df_u["ubicacion"] == f_lote].iloc[0]
                costo_base = float(row_u.get('precio', 0.0))
                comision_base = float(row_u.get('comision', 0.0))
                st.info(f"💰 Sugerido: Precio {fmt_moneda(costo_base)} | Comisión {fmt_moneda(comision_base)}")

                with st.form("form_nueva_venta"):
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha", value=datetime.now())
                    vendedores_list = ["-- SELECCIONAR --"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
                    f_vende_sel = c1.selectbox("👔 Vendedor Registrado", vendedores_list)
                    f_vende_nuevo = c2.text_input("🆕 Nuevo Vendedor")
                    
                    st.markdown("---")
                    clientes_list = ["-- SELECCIONAR --"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
                    f_cli_sel = st.selectbox("👤 Cliente Registrado", clientes_list)
                    f_cli_nuevo = st.text_input("🆕 Nuevo Cliente")
                    
                    st.markdown("---")
                    cf1, cf2 = st.columns(2)
                    f_tot = cf1.number_input("Precio Final ($)", min_value=0.0, value=costo_base)
                    f_eng = cf2.number_input("Enganche ($)", min_value=0.0)
                    f_comision = cf1.number_input("Comisión ($)", min_value=0.0, value=comision_base)
                    f_pla = cf2.number_input("🕒 Plazo (Meses)", min_value=1, value=12)
                    
                    m_calc = (f_tot - f_eng) / f_pla if f_pla > 0 else 0
                    st.metric("Mensualidad Resultante", fmt_moneda(m_calc))
                    f_coment = st.text_area("📝 Comentarios")

                    st.markdown("---")
                    cliente_display = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                    
                    st.info(f"""**Resumen de Venta:**
* **Lote:** {f_lote} | **Cliente:** {cliente_display}
* **Financiamiento:** {f_pla} meses de {fmt_moneda(m_calc)}
* **Total:** {fmt_moneda(f_tot)} (Enganche: {fmt_moneda(f_eng)})""")
                    
                    confirmar_vta = st.checkbox("Confirmo que los montos y datos del contrato son correctos.")

                    if st.form_submit_button("💾 GUARDAR VENTA", type="primary"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "-- SELECCIONAR --" or not cliente_final:
                            st.error("❌ Error: Falta el cliente.")
                        elif not confirmar_vta:
                            st.error("❌ Debes marcar la casilla de confirmación.")
                        else:
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1001
                                nuevo_cli = pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo, "telefono": "", "correo": ""}])
                                df_cl = pd.concat([df_cl, nuevo_cli], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                            
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, "fecha": f_fec.strftime('%Y-%m-%d'), 
                                "ubicacion": f_lote, "cliente": cliente_final, "vendedor": vendedor_final, 
                                "precio_total": f_tot, "enganche": f_eng, "plazo_meses": f_pla, 
                                "mensualidad": m_calc, "comision": f_comision, "comentarios": f_coment, "estatus_pago": "Activo"
                            }])
                            
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.success(f"✅ Venta registrada."); st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: EDITOR Y ARCHIVO ---
    with tab_editar:
        st.subheader("Modificar o Archivar Venta")
        if df_v.empty: st.info("No hay ventas.")
        else:
            lista_ventas = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            edit_sel = st.selectbox("Seleccione Venta", ["--"] + lista_ventas)
            
            if edit_sel != "--":
                id_ubi_sel = edit_sel.split(" | ")[0]
                idx_vta = df_v[df_v["ubicacion"] == id_ubi_sel].index[0]
                datos_v = df_v.loc[idx_vta]
                
                with st.form("form_edit_arch"):
                    st.write(f"Gestionando: **{id_ubi_sel}**")
                    e_fec = st.date_input("Fecha", value=pd.to_datetime(datos_v["fecha"]))
                    e_tot = st.number_input("Precio ($)", value=float(datos_v["precio_total"]))
                    e_eng = st.number_input("Enganche ($)", value=float(datos_v["enganche"]))
                    e_pla = st.number_input("Plazo", value=int(datos_v["plazo_meses"]))
                    
                    st.markdown("---")
                    st.warning("⚠️ ZONA DE ARCHIVADO Y LIMPIEZA")
                    st.write("Al archivar, se eliminarán todos los pagos históricos de este lote para dejarlo en ceros.")
                    f_motivo = st.text_input("Motivo de cancelación (Obligatorio)")
                    
                    c_save, c_arch = st.columns(2)
                    
                    if c_save.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df_v.at[idx_vta, "fecha"] = e_fec.strftime('%Y-%m-%d')
                        df_v.at[idx_vta, "precio_total"] = e_tot
                        df_v.at[idx_vta, "enganche"] = e_eng
                        df_v.at[idx_vta, "plazo_meses"] = e_pla
                        df_v.at[idx_vta, "mensualidad"] = (e_tot - e_eng) / e_pla
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("Actualizado"); st.cache_data.clear(); st.rerun()

                    if c_arch.form_submit_button("📦 ARCHIVAR Y REINICIAR LOTE"):
                        if not f_motivo: 
                            st.error("Escribe el motivo.")
                        else:
                            # 1. ARCHIVAR LA VENTA
                            reg_arch = datos_v.to_frame().T
                            reg_arch["fecha_cancelacion"] = datetime.now().strftime('%Y-%m-%d')
                            reg_arch["motivo"] = f_motivo
                            
                            try: df_arch_v = conn.read(spreadsheet=URL_SHEET, worksheet="archivo_ventas")
                            except: df_arch_v = pd.DataFrame()
                            df_arch_v = pd.concat([df_arch_v, reg_arch], ignore_index=True)

                            # 2. RETO: ARCHIVAR Y ELIMINAR PAGOS ASOCIADOS
                            # Filtramos los pagos que pertenecen a esta ubicación (lote)
                            pagos_lote = df_p[df_p["lote"] == id_ubi_sel].copy()
                            
                            if not pagos_lote.empty:
                                try: df_arch_p = conn.read(spreadsheet=URL_SHEET, worksheet="archivo_pagos")
                                except: df_arch_p = pd.DataFrame()
                                
                                # Añadimos información de contexto al archivo de pagos
                                pagos_lote["id_venta_origen"] = datos_v["id_venta"]
                                pagos_lote["motivo_cancelacion"] = f_motivo
                                
                                df_arch_p = pd.concat([df_arch_p, pagos_lote], ignore_index=True)
                                # Eliminamos los pagos de la tabla activa
                                df_p = df_p[df_p["lote"] != id_ubi_sel]
                                
                                # Actualizamos las hojas de pagos
                                conn.update(spreadsheet=URL_SHEET, worksheet="archivo_pagos", data=df_arch_p)
                                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                                st.write(f"✅ {len(pagos_lote)} pagos movidos al archivo.")

                            # 3. ACTUALIZAR ESTADOS RESTANTES
                            df_v = df_v.drop(idx_vta)
                            df_u.loc[df_u["ubicacion"] == id_ubi_sel, "estatus"] = "Disponible"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="archivo_ventas", data=df_arch_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success(f"Lote {id_ubi_sel} listo para una nueva venta.")
                            st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 3: HISTORIAL ---
    with tab_lista:
        if not df_v.empty:
            st.dataframe(df_v.drop(columns=["id_venta"], errors="ignore"), use_container_width=True, hide_index=True)
