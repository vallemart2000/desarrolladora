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
    # Aseguramos que las columnas críticas existan para evitar KeyError
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
    
    # Extraer fila seleccionada
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
    
    # Suma de abonos registrados
    abonos_mensuales = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
    total_pagado_acumulado = enganche_vta + abonos_mensuales
    
    porcentaje_total = (total_pagado_acumulado / precio_total_vta) if precio_total_vta > 0 else 0
    porcentaje_total = min(1.0, porcentaje_total)

    # Lógica de fechas
    f_ref = v['fecha_contrato'] if pd.notnull(v['fecha_contrato']) else v['fecha_registro']
    fecha_inicio = pd.to_datetime(f_ref)
    hoy = datetime.now()
    
    # Cálculo de atraso
    meses_transcurridos = (hoy.year - fecha_inicio.year) * 12 + (hoy.month - fecha_inicio.month)
    meses_a_deber = max(0, min(meses_transcurridos, plazo))
    deuda_esperada_a_hoy = meses_a_deber * mensualidad_pactada
    
    saldo_vencido = max(0, deuda_esperada_a_hoy - abonos_mensuales)
    num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

    # --- SECCIÓN: INFORMACIÓN GENERAL Y BARRA ---
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
        # Mostramos el saldo vencido. Si es mayor a 1 mensualidad, aparece en rojo (inverse)
        st.metric("Saldo Vencido", f"$ {saldo_vencido:,.2f}", 
                  delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else "Al día", 
                  delta_color="inverse")
        st.write(f"**📉 Restante:** $ {max(0, precio_total_vta - total_pagado_acumulado):,.2f}")

    st.divider()

    # --- GENERACIÓN DE LA TABLA DE AMORTIZACIÓN ---
    st.subheader("📅 Cronograma de Pagos Estimado")
    
    datos_amort = []
    saldo_insoluto = monto_a_financiar
    # Usamos una copia para ir restando en el simulador
    acumulado_para_tabla = abonos_mensuales 

    # Fecha de primer pago
    f_primer_pago = pd.to_datetime(v['inicio_mensualidades']) if pd.notnull(v['inicio_mensualidades']) else fecha_inicio + relativedelta(months=1)

    for i in range(1, plazo + 1):
        fecha_pago = f_primer_pago + relativedelta(months=i-1)
        
        if acumulado_para_tabla >= mensualidad_pactada:
            estatus = "✅ Pagado"
            acumulado_para_tabla -= mensualidad_pactada
        elif acumulado_para_tabla > 0:
            estatus = "⚠️ Parcial"
            acumulado_para_tabla = 0
        else:
            estatus = "⏳ Pendiente"
            
        saldo_insoluto = max(0, saldo_insoluto - mensualidad_pactada)
        
        datos_amort.append({
            "No. Cuota": i,
            "Fecha de Pago": fecha_pago,
            "Monto de Cuota": mensualidad_pactada,
            "Estatus": estatus,
            "Saldo Restante": saldo_insoluto
        })

    df_visual = pd.DataFrame(datos_amort)

    # Mostrar tabla con formato de moneda y fechas
    st.dataframe(
        df_visual,
        column_config={
            "Monto de Cuota": st.column_config.NumberColumn(format="$ %.2f"),
            "Saldo Restante": st.column_config.NumberColumn(format="$ %.2f"),
            "Fecha de Pago": st.column_config.DatetimeColumn(format="DD-MMM-YYYY")
        },
        use_container_width=True, 
        hide_index=True
    )
