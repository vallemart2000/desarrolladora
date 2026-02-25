import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("💰 Gestión de Cobranza")
    
    tab_pago, tab_historial = st.tabs(["💵 Registrar Nuevo Pago", "📋 Historial Completo de Ingresos"])

    # Necesitamos df_u para actualizar el estatus de la ubicación físicamente
    df_u = cargar_datos("ubicaciones")

    # --- PESTAÑA 1: REGISTRAR PAGO ---
    with tab_pago:
        if df_v.empty:
            st.warning("No hay ventas registradas.")
        else:
            opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            seleccion = st.selectbox("🔍 Seleccione Contrato o Apartado:", ["--"] + opciones_vta, key="sel_cobro")
            
            if seleccion != "--":
                ubi_sel = seleccion.split(" | ")[0]
                v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
                
                # --- LÓGICA DE SALDOS ---
                pagos_anteriores = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
                total_acumulado = float(v.get('enganche_pagado', 0)) + pagos_anteriores
                eng_req = float(v.get('enganche_requerido', 0))
                
                es_apartado = v["estatus_pago"] == "Pendiente"

                if es_apartado:
                    faltante_eng = max(0.0, eng_req - total_acumulado)
                    st.warning(f"⚠️ **ESTADO: APARTADO**. Faltan $ {faltante_eng:,.2f} para completar el enganche.")
                    monto_sugerido = faltante_eng if faltante_eng > 0 else 0.0
                else:
                    f_ini = pd.to_datetime(v['inicio_mensualidades'])
                    hoy = datetime.now()
                    meses_transcurridos = (hoy.year - f_ini.year) * 12 + (hoy.month - f_ini.month)
                    meses_a_cobrar = max(0, meses_transcurridos + 1)
                    deuda_esperada = meses_a_cobrar * float(v['mensualidad'])
                    s_vencido = max(0.0, deuda_esperada - pagos_anteriores)
                    
                    if s_vencido > 0:
                        st.error(f"🔴 Atraso en Mensualidades: $ {s_vencido:,.2f}")
                    else:
                        st.success(f"🟢 Al corriente.")
                    monto_sugerido = float(v['mensualidad'])

                with st.form("form_pago"):
                    c1, c2, c3 = st.columns(3)
                    f_fec = c1.date_input("Fecha de Pago", value=datetime.now())
                    f_met = c2.selectbox("Método", ["Efectivo", "Transferencia", "Depósito"])
                    f_fol = c3.text_input("Folio / Referencia")
                    
                    f_mon = st.number_input("Importe a pagar ($)", min_value=0.0, value=monto_sugerido)
                    f_com = st.text_area("Notas del pago")
                    
                    if st.form_submit_button("✅ REGISTRAR PAGO", type="primary"):
                        nid = int(df_p["id_pago"].max() + 1) if not df_p.empty else 1
                        nuevo_pago = pd.DataFrame([{
                            "id_pago": nid, "fecha": f_fec.strftime('%Y-%m-%d'), 
                            "ubicacion": ubi_sel, "cliente": v['cliente'], 
                            "monto": f_mon, "metodo": f_met, "folio": f_fol, "comentarios": f_com
                        }])
                        
                        df_p = pd.concat([df_p, nuevo_pago], ignore_index=True)
                        
                        nuevo_total = total_acumulado + f_mon
                        if es_apartado and nuevo_total >= eng_req:
                            idx_vta = df_v[df_v["ubicacion"] == ubi_sel].index[0]
                            df_v.at[idx_vta, "estatus_pago"] = "Activo"
                            df_v.at[idx_vta, "fecha_contrato"] = f_fec.strftime('%Y-%m-%d')
                            f_mens = (f_fec + relativedelta(months=1)).strftime('%Y-%m-%d')
                            df_v.at[idx_vta, "inicio_mensualidades"] = f_mens
                            df_u.loc[df_u["ubicacion"] == ubi_sel, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.balloons()
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("Pago guardado correctamente.")
                        st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: HISTORIAL UNIFICADO ---
    with tab_historial:
        st.subheader("Historial Unificado de Ingresos")
        
        # 1. Extraer Enganches de la tabla Ventas
        df_enganches = df_v[["fecha_registro", "ubicacion", "cliente", "enganche_pagado"]].copy()
        df_enganches.columns = ["fecha", "ubicacion", "cliente", "monto"]
        df_enganches["metodo"] = "Enganche Inicial"
        df_enganches["folio"] = "S/F"
        df_enganches["comentarios"] = "Pago inicial registrado en venta"

        # 2. Combinar con la tabla Pagos
        if not df_p.empty:
            df_abonos = df_p[["fecha", "ubicacion", "cliente", "monto", "metodo", "folio", "comentarios"]].copy()
            df_total_ingresos = pd.concat([df_enganches, df_abonos], ignore_index=True)
        else:
            df_total_ingresos = df_enganches

        # 3. Ordenar por fecha
        df_total_ingresos["fecha"] = pd.to_datetime(df_total_ingresos["fecha"])
        df_total_ingresos = df_total_ingresos.sort_values(by="fecha", ascending=False)

        # 4. Métricas rápidas
        total_cash = df_total_ingresos["monto"].sum()
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("💰 Total Ingresos Acumulados", f"$ {total_cash:,.2f}")
        c_m2.metric("🧾 Cantidad de Operaciones", len(df_total_ingresos))

        # 5. Filtros
        filtro_ubi = st.selectbox("Filtrar por ubicación:", ["Todos"] + df_v["ubicacion"].tolist(), key="filtro_hist_total")
        df_final = df_total_ingresos if filtro_ubi == "Todos" else df_total_ingresos[df_total_ingresos["ubicacion"] == filtro_ubi]

        df_final_estilado = df_final.style.format({
            "monto": "$ {:,.2f}",
            "fecha": lambda x: x.strftime('%d/%m/%Y')
        })

        st.dataframe(
            df_final_estilado,
            column_config={
                "fecha": "Fecha",
                "ubicacion": "Lote",
                "cliente": "Cliente",
                "monto": "Monto",
                "metodo": "Tipo/Método",
                "folio": "Folio",
                "comentarios": "Comentarios"
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        if st.button("🗑️ Eliminar último ABONO registrado"):
            if not df_p.empty:
                df_p = df_p.drop(df_p.index[-1])
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                st.warning("Último abono eliminado."); st.cache_data.clear(); st.rerun()
