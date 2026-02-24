import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("💰 Gestión de Cobranza")
    
    tab_pago, tab_historial = st.tabs(["💵 Registrar Nuevo Pago", "📋 Historial y Edición"])

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
                # 1. Sumar lo que ya ha pagado (incluyendo el enganche inicial registrado en la venta)
                pagos_anteriores = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
                total_acumulado = float(v.get('enganche_pagado', 0)) + pagos_anteriores
                eng_req = float(v.get('enganche_requerido', 0))
                
                # Determinar si es Apartado o Contrato Activo
                es_apartado = v["estatus_pago"] == "Pendiente"

                if es_apartado:
                    faltante_eng = max(0.0, eng_req - total_acumulado)
                    st.warning(f"⚠️ **ESTADO: APARTADO**. Faltan {fmt_moneda(faltante_eng)} para completar el enganche y formalizar contrato.")
                    monto_sugerido = faltante_eng if faltante_eng > 0 else 0.0
                else:
                    # Lógica de mensualidades vencidas para contratos activos
                    f_ini = pd.to_datetime(v['inicio_mensualidades'])
                    hoy = datetime.now()
                    meses_transcurridos = (hoy.year - f_ini.year) * 12 + (hoy.month - f_ini.month)
                    meses_a_cobrar = max(0, meses_transcurridos + 1) # +1 para incluir el mes corriente
                    
                    deuda_esperada = meses_a_cobrar * float(v['mensualidad'])
                    # Restamos pagos que NO son del enganche (esto es un cálculo simplificado)
                    s_vencido = max(0.0, deuda_esperada - pagos_anteriores)
                    
                    if s_vencido > 0:
                        st.error(f"🔴 Atraso en Mensualidades: {fmt_moneda(s_vencido)}")
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
                        # 1. Crear Registro de Pago
                        nid = int(df_p["id_pago"].max() + 1) if not df_p.empty else 1
                        nuevo_pago = pd.DataFrame([{
                            "id_pago": nid, "fecha": f_fec.strftime('%Y-%m-%d'), 
                            "ubicacion": ubi_sel, "cliente": v['cliente'], 
                            "monto": f_mon, "metodo": f_met, "folio": f_fol, "comentarios": f_com
                        }])
                        
                        df_p = pd.concat([df_p, nuevo_pago], ignore_index=True)
                        
                        # --- RETO: REVISAR PROMOCIÓN A CONTRATO ---
                        nuevo_total = total_acumulado + f_mon
                        if es_apartado and nuevo_total >= eng_req:
                            # ¡PROMOCIÓN!
                            idx_vta = df_v[df_v["ubicacion"] == ubi_sel].index[0]
                            df_v.at[idx_vta, "estatus_pago"] = "Activo"
                            df_v.at[idx_vta, "fecha_contrato"] = f_fec.strftime('%Y-%m-%d')
                            # Primera mensualidad al siguiente mes de completar el enganche
                            f_mens = (f_fec + relativedelta(months=1)).strftime('%Y-%m-%d')
                            df_v.at[idx_vta, "inicio_mensualidades"] = f_mens
                            
                            # Actualizar Ubicación a Vendido
                            df_u.loc[df_u["ubicacion"] == ubi_sel, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            st.balloons()
                            st.success(f"🎊 ¡ENGANCHE COMPLETADO! El apartado se ha convertido en CONTRATO. Primera mensualidad: {f_mens}")
                        
                        # Guardar cambios
                        conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        
                        st.success("Pago guardado correctamente.")
                        st.cache_data.clear(); st.rerun()

    # --- PESTAÑA 2: HISTORIAL Y EDICIÓN (Se mantiene similar con ajustes visuales) ---
    with tab_historial:
        st.subheader("Historial de Pagos")
        if df_p.empty:
            st.info("No hay pagos registrados.")
        else:
            # Filtro por ubicación para facilitar la edición
            filtro_ubi = st.selectbox("Filtrar por ubicación:", ["Todos"] + df_v["ubicacion"].tolist())
            df_mostrar = df_p if filtro_ubi == "Todos" else df_p[df_p["ubicacion"] == filtro_ubi]
            
            st.dataframe(
                df_mostrar.drop(columns=["id_pago"], errors="ignore"),
                column_config={
                    "monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
                    "fecha": "Fecha"
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Botón para eliminar último pago si hubo error
            if st.button("🗑️ Eliminar último pago registrado"):
                if not df_p.empty:
                    df_p = df_p.drop(df_p.index[-1])
                    conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                    st.warning("Último pago eliminado."); st.rerun()
