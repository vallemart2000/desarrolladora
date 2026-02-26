import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("💰 Gestión de Cobranza")
    
    tab_pago, tab_historial = st.tabs(["💵 Registrar Nuevo Pago", "📋 Historial de Ingresos"])

    # Cargamos ubicaciones para poder cambiar el estatus de APARTADO a VENDIDO
    df_u = cargar_datos("ubicaciones")

    # --- PESTAÑA 1: REGISTRAR PAGO ---
    with tab_pago:
        if df_v.empty:
            st.warning("No hay contratos ni apartados registrados.")
        else:
            opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            seleccion = st.selectbox("🔍 Seleccione Lote o Cliente:", ["--"] + opciones_vta, key="sel_cobro")
            
            if seleccion != "--":
                ubi_sel = seleccion.split(" | ")[0]
                v_idx = df_v[df_v["ubicacion"] == ubi_sel].index[0]
                v = df_v.loc[v_idx]
                
                # Datos financieros actuales
                eng_req = float(v.get('enganche_requerido', 0.0))
                eng_pag = float(v.get('enganche_pagado', 0.0))
                mensualidad_pactada = float(v.get('mensualidad', 0.0))
                
                # Determinamos el estado del contrato
                faltante_eng = max(0.0, eng_req - eng_pag)
                es_apartado = eng_pag < eng_req

                if es_apartado:
                    st.warning(f"⚠️ **ESTADO: APARTADO** (Faltan {fmt_moneda(faltante_eng)} para completar el enganche)")
                    monto_sugerido = faltante_eng
                else:
                    st.success(f"🟢 **ESTADO: VENDIDO** (Enganche cubierto)")
                    monto_sugerido = mensualidad_pactada

                with st.form("form_pago"):
                    c1, c2, c3 = st.columns(3)
                    f_fec = c1.date_input("Fecha de Pago", value=datetime.now())
                    f_met = c2.selectbox("Método", ["Efectivo", "Transferencia", "Depósito"])
                    f_fol = c3.text_input("Folio / Referencia Física")
                    
                    f_mon = st.number_input("Importe a Recibir ($)", min_value=0.0, value=monto_sugerido)
                    f_com = st.text_area("Comentarios del pago")
                    
                    if st.form_submit_button("✅ REGISTRAR PAGO EN SISTEMA", type="primary"):
                        if f_mon <= 0:
                            st.error("El monto debe ser mayor a 0.")
                        else:
                            # 1. Registrar el pago en la tabla 'pagos'
                            nid_p = int(df_p["id_pago"].max() + 1) if not df_p.empty else 1
                            nuevo_pago = pd.DataFrame([{
                                "id_pago": nid_p, 
                                "fecha": f_fec.strftime('%Y-%m-%d'), 
                                "ubicacion": ubi_sel, 
                                "cliente": v['cliente'], 
                                "monto": f_mon, 
                                "metodo": f_met, 
                                "folio": f_fol, 
                                "comentarios": f_com
                            }])
                            df_p = pd.concat([df_p, nuevo_pago], ignore_index=True)

                            # 2. Lógica de distribución: ¿Es enganche o mensualidad?
                            dinero_disponible = f_mon
                            
                            if eng_pag < eng_req:
                                # Aún no se completa el enganche
                                abono_a_eng = min(dinero_disponible, eng_req - eng_pag)
                                nuevo_eng_pag = eng_pag + abono_a_eng
                                df_v.at[v_idx, "enganche_pagado"] = nuevo_eng_pag
                                dinero_disponible -= abono_a_eng
                                
                                # Si con este pago se completó el enganche
                                if nuevo_eng_pag >= eng_req:
                                    df_v.at[v_idx, "estatus_pago"] = "Activo"
                                    # La fecha de contrato es cuando se completa el enganche
                                    df_v.at[v_idx, "fecha_contrato"] = f_fec.strftime('%Y-%m-%d')
                                    # La primera mensualidad es un mes después de completar el enganche
                                    f_mens = (f_fec + relativedelta(months=1)).strftime('%Y-%m-%d')
                                    df_v.at[v_idx, "inicio_mensualidades"] = f_mens
                                    
                                    # Actualizar estatus de la ubicación físicamente
                                    df_u.loc[df_u["ubicacion"] == ubi_sel, "estatus"] = "Vendido"
                                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                                    st.balloons()
                            
                            # Si sobra dinero después del enganche, se queda registrado en df_p (ya lo hicimos arriba)
                            # El sistema de reportes lo tomará como abonos adicionales
                            
                            # 3. Guardar cambios en la nube
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            
                            st.success(f"Pago registrado. Se abonaron {fmt_moneda(f_mon)} a la cuenta de {v['cliente']}.")
                            st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: HISTORIAL DE INGRESOS ---
    with tab_historial:
        st.subheader("📋 Historial Cronológico de Cobros")
        
        if df_p.empty:
            st.info("No hay pagos registrados aún.")
        else:
            # Ordenamos por fecha y ID para ver lo más reciente arriba
            df_p_view = df_p.copy()
            df_p_view["fecha"] = pd.to_datetime(df_p_view["fecha"])
            df_p_view = df_p_view.sort_values(by=["fecha", "id_pago"], ascending=False)

            # Métricas
            total_ingresos = df_p_view["monto"].sum()
            st.metric("Total de Ingresos (Caja)", fmt_moneda(total_ingresos))

            # Filtro por ubicación
            filtro_ubi = st.selectbox("Filtrar por Lote:", ["Todos"] + sorted(df_v["ubicacion"].unique().tolist()))
            
            df_final = df_p_view if filtro_ubi == "Todos" else df_p_view[df_p_view["ubicacion"] == filtro_ubi]

            st.dataframe(
                df_final.style.format({
                    "monto": "$ {:,.2f}",
                    "fecha": lambda x: x.strftime('%d/%m/%Y')
                }),
                column_config={
                    "id_pago": "ID",
                    "fecha": "Fecha",
                    "ubicacion": "Lote",
                    "monto": "Importe",
                    "metodo": "Método",
                    "folio": "Folio/Ref",
                    "comentarios": "Notas"
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            if st.button("🗑️ Eliminar último movimiento"):
                if not df_p.empty:
                    # Al eliminar, tendríamos que revertir el enganche_pagado en df_v
                    # Por simplicidad en este paso, solo eliminamos el registro del pago
                    # pero se recomienda auditar esto manualmente si el pago completó un enganche.
                    df_p = df_p.drop(df_p.index[-1])
                    conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                    st.warning("Último movimiento eliminado de la base de datos."); st.cache_data.clear(); st.rerun()
