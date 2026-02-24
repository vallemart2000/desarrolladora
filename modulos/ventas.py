import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_ventas(df_v, df_u, df_cl, df_vd, df_p, conn, URL_SHEET, fmt_moneda):
    st.title("📝 Gestión de Ventas y Apartados")
    
    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta/Apartado", "✏️ Editor y Archivo", "📋 Historial"])

    # --- PESTAÑA 1: NUEVA VENTA ---
    with tab_nueva:
        st.subheader("Registrar Nueva Operación")
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
                        f"Precio: {fmt_moneda(costo_base)}  \n"
                        f"Enganche Mínimo Requerido: {fmt_moneda(eng_minimo)}")

                with st.form("form_nueva_venta"):
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha de hoy", value=datetime.now())
                    
                    vendedores_list = ["-- SELECCIONAR --"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
                    f_vende_sel = c1.selectbox("👔 Vendedor Registrado", vendedores_list)
                    f_vende_nuevo = c2.text_input("🆕 Nombre de Vendedor Nuevo")
                    
                    st.markdown("---")
                    clientes_list = ["-- SELECCIONAR --"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
                    f_cli_sel = st.selectbox("👤 Cliente Registrado", clientes_list)
                    f_cli_nuevo = st.text_input("🆕 Nombre de Cliente Nuevo")
                    
                    st.markdown("---")
                    cf1, cf2 = st.columns(2)
                    f_tot = cf1.number_input("Precio Final de Venta ($)", min_value=0.0, value=costo_base)
                    f_eng_hoy = cf2.number_input("Monto que entrega hoy ($)", min_value=0.0)
                    f_pla = cf2.number_input("🕒 Plazo (Meses)", min_value=1, value=12)
                    f_coment = st.text_area("📝 Comentarios")

                    cumple_enganche = f_eng_hoy >= eng_minimo
                    
                    if cumple_enganche:
                        st.success(f"✅ El monto cubre el enganche. Se generará **CONTRATO**.")
                    else:
                        st.warning(f"⚠️ El monto es menor a {fmt_moneda(eng_minimo)}. Se registrará como **APARTADO**.")

                    confirmar_vta = st.checkbox("Confirmo que los datos son correctos.")

                    if st.form_submit_button("💾 GUARDAR REGISTRO", type="primary"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "-- SELECCIONAR --" or not cliente_final:
                            st.error("❌ Error: Falta el cliente.")
                        elif vendedor_final == "-- SELECCIONAR --" or not vendedor_final:
                            st.error("❌ Error: Falta el vendedor.")
                        elif not confirmar_vta:
                            st.error("❌ Debes marcar la casilla de confirmación.")
                        else:
                            # 1.1 Registro de Cliente Nuevo si aplica
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1001
                                nuevo_cli = pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo, "telefono": "", "correo": ""}])
                                df_cl = pd.concat([df_cl, nuevo_cli], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)

                            # 1.2 REGISTRO DE VENDEDOR NUEVO (LO QUE FALTABA)
                            if f_vende_nuevo:
                                nid_vd = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 501
                                nuevo_vd = pd.DataFrame([{"id_vendedor": nid_vd, "nombre": f_vende_nuevo, "telefono": "", "comision_base": 0}])
                                df_vd = pd.concat([df_vd, nuevo_vd], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)
                            
                            # 2. Definir estatus y fechas
                            if cumple_enganche:
                                estatus_ubi = "Vendido"
                                estatus_vta = "Activo"
                                fecha_contrato = f_fec.strftime('%Y-%m-%d')
                                fecha_1ra_mens = (f_fec + relativedelta(months=1)).strftime('%Y-%m-%d')
                            else:
                                estatus_ubi = "Apartado"
                                estatus_vta = "Pendiente"
                                fecha_contrato = "PENDIENTE"
                                fecha_1ra_mens = "AL COMPLETAR ENGANCHE"

                            # 3. Registrar en df_v
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            m_calc = (f_tot - f_eng_hoy) / f_pla
                            
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, 
                                "fecha_registro": f_fec.strftime('%Y-%m-%d'),
                                "fecha_contrato": fecha_contrato,
                                "inicio_mensualidades": fecha_1ra_mens,
                                "ubicacion": f_lote, 
                                "cliente": cliente_final, 
                                "vendedor": vendedor_final, 
                                "precio_total": f_tot, 
                                "enganche_pagado": f_eng_hoy, 
                                "enganche_requerido": eng_minimo,
                                "plazo_meses": f_pla, 
                                "mensualidad": m_calc, 
                                "estatus_pago": estatus_vta,
                                "comentarios": f_coment
                            }])
                            
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            
                            # 4. Actualizar Ubicaciones
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = estatus_ubi
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success(f"✅ Registro exitoso como {estatus_ubi}")
                            st.cache_data.clear(); st.rerun()

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
                    e_fec = st.date_input("Fecha Registro", value=pd.to_datetime(datos_v["fecha_registro"]))
                    e_tot = st.number_input("Precio ($)", value=float(datos_v["precio_total"]))
                    e_eng = st.number_input("Enganche Pagado ($)", value=float(datos_v.get("enganche_pagado", 0)))
                    e_pla = st.number_input("Plazo", value=int(datos_v["plazo_meses"]))
                    
                    st.markdown("---")
                    st.warning("⚠️ ZONA DE ARCHIVADO")
                    f_motivo = st.text_input("Motivo de cancelación (Obligatorio)")
                    
                    c_save, c_arch = st.columns(2)
                    
                    if c_save.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df_v.at[idx_vta, "fecha_registro"] = e_fec.strftime('%Y-%m-%d')
                        df_v.at[idx_vta, "precio_total"] = e_tot
                        df_v.at[idx_vta, "enganche_pagado"] = e_eng
                        df_v.at[idx_vta, "plazo_meses"] = e_pla
                        df_v.at[idx_vta, "mensualidad"] = (e_tot - e_eng) / e_pla
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("Actualizado"); st.cache_data.clear(); st.rerun()

                    if c_arch.form_submit_button("📦 ARCHIVAR Y REINICIAR"):
                        if not f_motivo: st.error("Escribe el motivo.")
                        else:
                            reg_arch = datos_v.to_frame().T
                            reg_arch["fecha_cancelacion"] = datetime.now().strftime('%Y-%m-%d')
                            reg_arch["motivo"] = f_motivo
                            
                            try: df_arch_v = conn.read(spreadsheet=URL_SHEET, worksheet="archivo_ventas")
                            except: df_arch_v = pd.DataFrame()
                            df_arch_v = pd.concat([df_arch_v, reg_arch], ignore_index=True)

                            # Filtrar pagos asociados
                            pagos_lote = df_p[df_p["ubicacion"] == id_ubi_sel].copy()
                            if not pagos_lote.empty:
                                try: df_arch_p = conn.read(spreadsheet=URL_SHEET, worksheet="archivo_pagos")
                                except: df_arch_p = pd.DataFrame()
                                df_arch_p = pd.concat([df_arch_p, pagos_lote], ignore_index=True)
                                df_p = df_p[df_p["ubicacion"] != id_ubi_sel]
                                conn.update(spreadsheet=URL_SHEET, worksheet="archivo_pagos", data=df_arch_p)
                                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)

                            df_v = df_v.drop(idx_vta)
                            df_u.loc[df_u["ubicacion"] == id_ubi_sel, "estatus"] = "Disponible"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="archivo_ventas", data=df_arch_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.success("Lote liberado y venta archivada."); st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 3: HISTORIAL ---
    with tab_lista:
        if not df_v.empty:
            cols_mostrar = ["id_venta", "fecha_registro", "fecha_contrato", "ubicacion", "cliente", "estatus_pago"]
            st.dataframe(df_v[cols_mostrar], use_container_width=True, hide_index=True)
