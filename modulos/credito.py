import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_detalle_credito(df_v, df_p, fmt_moneda):
    st.title("📊 Detalle de Crédito y Estado de Cuenta")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
        return

    # --- LIMPIEZA Y NORMALIZACIÓN ---
    columnas_esperadas = {
        'precio_total': 0.0, 'enganche_pagado': 0.0, 'enganche_requerido': 0.0,
        'mensualidad': 0.0, 'plazo_meses': 1, 'fecha_contrato': None, 
        'fecha_registro': None, 'inicio_mensualidades': None, 
        'ubicacion': 'N/A', 'cliente': 'N/A'
    }
    
    for col, default in columnas_esperadas.items():
        if col not in df_v.columns:
            df_v[col] = default

    # 1. SELECTOR DE CONTRATO
    opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
    seleccion = st.selectbox("🔍 Seleccione un Contrato:", opciones_vta)
    
    ubi_sel = seleccion.split(" | ")[0]
    v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
    
    # --- LÓGICA FINANCIERA CORREGIDA ---
    try:
        precio_total_vta = float(v['precio_total'])
        eng_req = float(v['enganche_requerido'])
        eng_pag_en_ventas = float(v['enganche_pagado']) # Lo que el sistema dice que tiene de enganche
        mensualidad_pactada = float(v['mensualidad'])
        plazo = int(v['plazo_meses'])
    except:
        st.error("Error en los datos numéricos.")
        return

    # Suma TOTAL de dinero que ha entrado a la tabla de pagos para esta ubicación
    suma_pagos_tabla = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0.0
    
    # El "Dinero para Mensualidades" es la suma de pagos menos lo que se usó para completar el enganche requerido
    # Si eng_pag_en_ventas < eng_req, significa que aún no hay dinero para mensualidades.
    dinero_para_mensualidades = max(0.0, suma_pagos_tabla - (eng_req))
    
    # Total pagado real (Enganche pagado hasta el momento + lo que sea de mensualidades)
    # Nota: eng_pag_en_ventas ya incluye los abonos que se fueron a enganche
    total_pagado_acumulado = suma_pagos_tabla 

    # --- CÁLCULO DE ATRASOS ---
    # Solo calculamos atrasos si ya debería haber empezado a pagar mensualidades (Estatus Activo)
    saldo_vencido = 0.0
    num_atrasos = 0
    
    if pd.notnull(v['inicio_mensualidades']) and v['estatus_pago'] == "Activo":
        f_ini = pd.to_datetime(v['inicio_mensualidades'])
        hoy = datetime.now()
        meses_transcurridos = (hoy.year - f_ini.year) * 12 + (hoy.month - f_ini.month)
        meses_a_cobrar = max(0, meses_transcurridos + 1) # +1 porque se cobra al inicio del mes
        deuda_esperada = meses_a_cobrar * mensualidad_pactada
        
        saldo_vencido = max(0.0, deuda_esperada - dinero_para_mensualidades)
        num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

    # --- SECCIÓN: RESUMEN ---
    porcentaje_total = min(1.0, total_pagado_acumulado / precio_total_vta) if precio_total_vta > 0 else 0
    
    st.markdown("### 📋 Resumen del Crédito")
    st.write(f"**Avance de Pago Total: {int(porcentaje_total * 100)}%**")
    st.progress(porcentaje_total)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write(f"**📍 Lote:** {v['ubicacion']}")
        st.write(f"**👤 Cliente:** {v['cliente']}")
        f_disp = v['fecha_contrato'] if pd.notnull(v['fecha_contrato']) else v['fecha_registro']
        st.write(f"**📅 Contrato:** {pd.to_datetime(f_disp).strftime('%d/%m/%Y')}")
    with c2:
        st.metric("Total Pagado", f"$ {total_pagado_acumulado:,.2f}")
        st.write(f"**💰 Precio Venta:** $ {precio_total_vta:,.2f}")
        st.write(f"**📥 Enganche:** $ {eng_pag_en_ventas:,.2f} / $ {eng_req:,.2f}")
    with c3:
        st.metric("Saldo Vencido", f"$ {saldo_vencido:,.2f}", 
                  delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else "Al día", 
                  delta_color="inverse")
        st.write(f"**📉 Saldo Pendiente:** $ {max(0.0, precio_total_vta - total_pagado_acumulado):,.2f}")

    st.divider()

    # --- TABLA DE AMORTIZACIÓN ---
    st.subheader("📅 Plan de Pagos (Mensualidades)")
    
    if v['estatus_pago'] != "Activo":
        st.info("La tabla de mensualidades se activará cuando el enganche esté cubierto al 100%.")
    else:
        datos_amort = []
        # El saldo insoluto de las mensualidades es: Precio Total - Enganche Requerido
        saldo_m_insoluto = precio_total_vta - eng_req
        bolsa_dinero = dinero_para_mensualidades 

        f_mens = pd.to_datetime(v['inicio_mensualidades'])

        for i in range(1, plazo + 1):
            fecha_pago = f_mens + relativedelta(months=i-1)
            pago_este_mes = 0.0
            
            if bolsa_dinero >= mensualidad_pactada:
                estatus = "✅ Pagado"
                pago_este_mes = mensualidad_pactada
                bolsa_dinero -= mensualidad_pactada
            elif bolsa_dinero > 0:
                estatus = "⚠️ Parcial"
                pago_este_mes = bolsa_dinero
                bolsa_dinero = 0
            else:
                estatus = "⏳ Pendiente"
                pago_este_mes = 0.0
                
            saldo_m_insoluto = max(0.0, saldo_m_insoluto - mensualidad_pactada)
            
            datos_amort.append({
                "Cuota": i,
                "Fecha": fecha_pago,
                "Monto": mensualidad_pactada,
                "Estatus": estatus,
                "Abonado": pago_este_mes,
                "Saldo": saldo_m_insoluto
            })

        df_visual = pd.DataFrame(datos_amort)
        st.dataframe(
            df_visual.style.format({
                "Monto": "$ {:,.2f}",
                "Abonado": "$ {:,.2f}",
                "Saldo": "$ {:,.2f}",
                "Fecha": lambda x: x.strftime('%d/%m/%Y')
            }),
            column_config={
                "Cuota": "No.",
                "Monto": "Cuota Mensual",
                "Abonado": "Pagado",
                "Saldo": "Capital Restante"
            },
            use_container_width=True, 
            hide_index=True
        )
