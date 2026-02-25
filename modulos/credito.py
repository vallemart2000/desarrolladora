import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_detalle_credito(df_v, df_p, fmt_moneda):
    st.title("📊 Detalle de Crédito y Estado de Cuenta")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
        return

    # --- LIMPIEZA Y NORMALIZACIÓN DE COLUMNAS ---
    columnas_esperadas = {
        'precio_total': 0.0, 'enganche_pagado': 0.0, 'mensualidad': 0.0, 
        'plazo_meses': 1, 'fecha_contrato': None, 'fecha_registro': None,
        'inicio_mensualidades': None, 'ubicacion': 'N/A', 'cliente': 'N/A'
    }
    
    for col, default in columnas_esperadas.items():
        if col not in df_v.columns:
            df_v[col] = default

    # 1. SELECTOR DE CONTRATO
    opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
    seleccion = st.selectbox("🔍 Seleccione un Contrato:", opciones_vta)
    
    ubi_sel = seleccion.split(" | ")[0]
    v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
    
    # --- CÁLCULOS FINANCIEROS ---
    try:
        precio_total_vta = float(v['precio_total'])
        enganche_vta = float(v['enganche_pagado'])
        mensualidad_pactada = float(v['mensualidad'])
        plazo = int(v['plazo_meses'])
    except (ValueError, TypeError):
        st.error("Error en el formato de los datos numéricos de este contrato.")
        return

    monto_a_financiar = precio_total_vta - enganche_vta
    
    abonos_mensuales = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
    total_pagado_acumulado = enganche_vta + abonos_mensuales
    
    porcentaje_total = (total_pagado_acumulado / precio_total_vta) if precio_total_vta > 0 else 0
    porcentaje_total = min(1.0, porcentaje_total)

    f_ref = v['fecha_contrato'] if pd.notnull(v['fecha_contrato']) else v['fecha_registro']
    fecha_inicio = pd.to_datetime(f_ref)
    hoy = datetime.now()
    
    meses_transcurridos = (hoy.year - fecha_inicio.year) * 12 + (hoy.month - fecha_inicio.month)
    meses_a_deber = max(0, min(meses_transcurridos, plazo))
    deuda_esperada_a_hoy = meses_a_deber * mensualidad_pactada
    
    saldo_vencido = max(0.0, deuda_esperada_a_hoy - abonos_mensuales)
    num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

    # --- SECCIÓN: RESUMEN ---
    st.markdown("### 📋 Resumen del Crédito")
    st.write(f"**Avance Total de Pago: {int(porcentaje_total * 100)}%**")
    st.progress(porcentaje_total)
    st.write("") 

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write(f"**📍 Ubicación:** {v['ubicacion']}")
        st.write(f"**👤 Cliente:** {v['cliente']}")
        st.write(f"**📅 Fecha Contrato:** {fecha_inicio.strftime('%d-%b-%Y')}")
    with c2:
        st.metric("Total Pagado", f"$ {total_pagado_acumulado:,.2f}")
        st.write(f"**💰 Costo Total:** $ {precio_total_vta:,.2f}")
        st.write(f"**📥 Enganche Pagado:** $ {enganche_vta:,.2f}")
    with c3:
        st.metric("Saldo Vencido", f"$ {saldo_vencido:,.2f}", 
                  delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else "Al día", 
                  delta_color="inverse")
        st.write(f"**📉 Restante:** $ {max(0, precio_total_vta - total_pagado_acumulado):,.2f}")

    st.divider()

    # --- GENERACIÓN DE LA TABLA DE AMORTIZACIÓN ---
    st.subheader("📅 Cronograma de Pagos Estimado")
    
    datos_amort = []
    saldo_insoluto = monto_a_financiar
    acumulado_para_tabla = abonos_mensuales 

    f_primer_pago = pd.to_datetime(v['inicio_mensualidades']) if pd.notnull(v['inicio_mensualidades']) else fecha_inicio + relativedelta(months=1)

    for i in range(1, plazo + 1):
        fecha_pago = f_primer_pago + relativedelta(months=i-1)
        monto_abonado_a_cuota = 0.0
        
        if acumulado_para_tabla >= mensualidad_pactada:
            estatus = "✅ Pagado"
            monto_abonado_a_cuota = mensualidad_pactada
            acumulado_para_tabla -= mensualidad_pactada
        elif acumulado_para_tabla > 0:
            estatus = "⚠️ Parcial"
            monto_abonado_a_cuota = acumulado_para_tabla
            acumulado_para_tabla = 0
        else:
            estatus = "⏳ Pendiente"
            monto_abonado_a_cuota = 0.0
            
        saldo_insoluto = max(0.0, saldo_insoluto - mensualidad_pactada)
        
        datos_amort.append({
            "No. Cuota": i,
            "Fecha de Pago": fecha_pago,
            "Monto de Cuota": mensualidad_pactada,
            "Estatus": estatus,
            "Abonado a Cuota": monto_abonado_a_cuota,
            "Saldo Restante": saldo_insoluto
        })

    df_visual = pd.DataFrame(datos_amort)

    df_estilado = df_visual.style.format({
        "No. Cuota": "{:.0f}",
        "Monto de Cuota": "$ {:,.2f}",
        "Abonado a Cuota": "$ {:,.2f}",
        "Saldo Restante": "$ {:,.2f}",
        "Fecha de Pago": lambda x: x.strftime('%d-%b-%Y')
    })

    st.dataframe(
        df_estilado,
        column_config={
            "No. Cuota": "No.",
            "Fecha de Pago": "Fecha de Pago",
            "Monto de Cuota": "Cuota",
            "Estatus": "Estatus",
            "Abonado a Cuota": "Abonado",
            "Saldo Restante": "Saldo"
        },
        use_container_width=True, 
        hide_index=True
    )
