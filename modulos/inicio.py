import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import re

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    if df is None or (isinstance(df, pd.DataFrame) and df.empty and len(df.columns) == 0):
        df = pd.DataFrame(columns=columnas_necesarias.keys())
    
    cambios = False
    for col, default_val in columnas_necesarias.items():
        if col not in df.columns:
            df[col] = default_val
            cambios = True
    
    if cambios:
        try:
            conn.update(spreadsheet=URL_SHEET, worksheet=worksheet_name, data=df)
            st.toast(f"🛠️ Estructura de '{worksheet_name}' sincronizada.")
        except:
            pass 
    return df

def render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda):
    st.title("🏠 Panel de Control y Cartera")

    # --- 1. REPARACIÓN DE ESTRUCTURA ---
    cols_v = {
        "id_venta": 0, "fecha_registro": "", "ubicacion": "", "cliente": "", 
        "vendedor": "", "precio_total": 0.0, "enganche_pagado": 0.0, 
        "mensualidad": 0.0, "estatus_pago": "Activo", "inicio_mensualidades": ""
    }
    df_v = verificar_y_reparar_columnas(df_v, cols_v, "ventas", conn, URL_SHEET)

    # --- 2. MÉTRICAS ---
    c1, c2, c3, c4 = st.columns(4)
    total_recaudado = (df_v["enganche_pagado"].sum() + df_p["monto"].sum()) if not df_p.empty else df_v["enganche_pagado"].sum()
    
    c1.metric("💰 Ingresos Totales", f"$ {total_recaudado:,.2f}")
    c2.metric("👥 Clientes Activos", df_v[df_v["estatus_pago"] == "Activo"].shape[0])
    c3.metric("📈 Valor Cartera", f"$ {df_v[df_v['estatus_pago'] == 'Activo']['precio_total'].sum():,.2f}")
    c4.metric("🏗️ Lotes Vendidos", df_v.shape[0])

    st.markdown("---")

    # --- 3. LÓGICA DE COBRANZA ---
    if df_v.empty:
        st.info("No hay datos de ventas.")
        return

    if not df_p.empty:
        df_p_clean = df_p.copy()
        df_p_clean['fecha'] = pd.to_datetime(df_p_clean['fecha'], errors='coerce')
        ultimo_pago = df_p_clean.dropna(subset=['fecha']).sort_values('fecha').groupby('ubicacion')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    hoy = datetime.now()
    
    def calcular_detalles(row):
        try:
            fecha_ref = pd.to_datetime(row['fecha_ultimo_pago']) if pd.notnull(row['fecha_ultimo_pago']) else pd.to_datetime(row['inicio_mensualidades'])
            dias = max(0, (hoy - fecha_ref).days)
            mensualidad = float(row['mensualidad'])
            meses_atraso = max(1, dias // 30) if dias > 25 else 0
            pago_sugerido = meses_atraso * mensualidad if dias > 25 else 0.0
            return pd.Series([dias, pago_sugerido])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_detalles, axis=1)

    # --- 4. CONTACTO (Lógica de Teléfono Corregida) ---
    def link_contacto(row, tipo):
        try:
            cl_info = df_cl[df_cl['nombre'] == row['cliente']].iloc[0]
            if tipo == "WA":
                # Limpiamos el teléfono de espacios, guiones o paréntesis
                tel_sucio = str(cl_info['telefono'])
                tel_limpio = re.sub(r'\D', '', tel_sucio) # Deja solo números
                
                # Si el número tiene 10 dígitos, le falta el código de país (México = 52)
                if len(tel_limpio) == 10:
                    tel_final = "52" + tel_limpio
                else:
                    tel_final = tel_limpio
                
                msg = f"Hola {row['cliente']}, tu lote {row['ubicacion']} tiene {row['dias_atraso']} días de atraso. El pago para estar al corriente es de {fmt_moneda(row['pago_corriente'])}."
                return f"https://wa.me/{tel_final}?text={urllib.parse.quote(msg)}"
            else:
                mail = cl_info['correo']
                return f"mailto:{mail}?subject=Aviso Lote {row['ubicacion']}&body=Atraso de {row['dias_atraso']} días."
        except: 
            return None

    df_cartera['WhatsApp'] = df_cartera.apply(lambda r: link_contacto(r, "WA"), axis=1)
    df_cartera['Correo'] = df_cartera.apply(lambda r: link_contacto(r, "Mail"), axis=1)

    df_cartera['Estatus'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 PREVENTIVO (+25d)" if x > 25 else "🟢 AL CORRIENTE")
    )

    # --- 5. TABLA ---
    st.subheader("📋 Control de Cobranza y Contacto")
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)
    
    if solo_atrasados:
        df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy()
    else:
        df_mostrar = df_cartera.copy()

    if not df_mostrar.empty:
        df_mostrar = df_mostrar.rename(columns={
            "ubicacion": "Ubicación",
            "cliente": "Cliente",
            "dias_atraso": "Días de Atraso",
            "pago_corriente": "Pago para estar al Corriente"
        })
        
        cols_finales = ["Estatus", "Ubicación", "Cliente", "Días de Atraso", "Pago para estar al Corriente", "WhatsApp", "Correo"]
        
        st.dataframe(
            df_mostrar[cols_finales],
            column_config={
                "Pago para estar al Corriente": st.column_config.NumberColumn(format="$ %.2f"),
                "WhatsApp": st.column_config.LinkColumn("📲 Enviar WA", display_text="WhatsApp"),
                "Correo": st.column_config.LinkColumn("📧 Enviar Correo", display_text="Email")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.success("🎉 Todo al corriente.")
