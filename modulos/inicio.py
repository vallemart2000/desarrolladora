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
        except:
            pass 
    return df

def render_inicio(df_v, df_p, df_cl, conn, URL_SHEET, fmt_moneda):
    st.title("🏠 Panel de Control y Cartera")

    # --- 1. REPARACIÓN DE ESTRUCTURA ---
    cols_v = {
        "id_venta": 0, "fecha_registro": "", "ubicacion": "", "cliente": "", 
        "vendedor": "", "precio_total": 0.0, "enganche_pagado": 0.0, 
        "mensualidad": 0.0, "estatus_pago": "Activo", "inicio_mensualidades": "",
        "plazo_meses": 0
    }
    df_v = verificar_y_reparar_columnas(df_v, cols_v, "ventas", conn, URL_SHEET)

    # --- 2. MÉTRICAS GENERALES (Con formato de comas) ---
    c1, c2, c3, c4 = st.columns(4)
    total_recaudado = (df_v["enganche_pagado"].sum() + df_p["monto"].sum()) if not df_p.empty else df_v["enganche_pagado"].sum()
    valor_cartera = df_v[df_v['estatus_pago'] == 'Activo']['precio_total'].sum()
    
    c1.metric("💰 Ingresos Totales", fmt_moneda(total_recaudado))
    c2.metric("👥 Clientes Activos", df_v[df_v["estatus_pago"] == "Activo"].shape[0])
    c3.metric("📈 Valor Cartera", fmt_moneda(valor_cartera))
    c4.metric("🏗️ Lotes Vendidos", df_v.shape[0])

    st.markdown("---")

    # --- 3. LÓGICA DE CARTERA VENCIDA ---
    if df_v.empty:
        st.info("No hay datos de ventas.")
        return

    if not df_p.empty:
        pagos_totales = df_p.groupby('ubicacion')['monto'].sum().reset_index()
        pagos_totales.columns = ['ubicacion', 'total_abonado_mensualidades']
    else:
        pagos_totales = pd.DataFrame(columns=['ubicacion', 'total_abonado_mensualidades'])

    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(pagos_totales, on='ubicacion', how='left').fillna(0)
    
    hoy = datetime.now()

    def calcular_mora_real(row):
        try:
            f_inicio = pd.to_datetime(row['inicio_mensualidades'])
            if pd.isnull(f_inicio): f_inicio = hoy
            
            meses_transcurridos = (hoy.year - f_inicio.year) * 12 + (hoy.month - f_inicio.month)
            if hoy.day < f_inicio.day: meses_transcurridos -= 1
            
            mensualidad = float(row['mensualidad'])
            deuda_total_a_hoy = max(0, meses_transcurridos) * mensualidad
            pagado_real = float(row['total_abonado_mensualidades'])
            
            saldo_vencido = max(0.0, deuda_total_a_hoy - pagado_real)
            
            meses_cubiertos = pagado_real / mensualidad if mensualidad > 0 else 0
            fecha_vencimiento_pendiente = f_inicio + pd.DateOffset(months=int(meses_cubiertos))
            dias_atraso = (hoy - fecha_vencimiento_pendiente).days if saldo_vencido > 0 else 0
            
            return pd.Series([max(0, dias_atraso), saldo_vencido])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_mora_real, axis=1)

    # --- 4. CONTACTO Y ESTATUS ---
    def link_contacto(row, tipo):
        try:
            cl_info = df_cl[df_cl['nombre'] == row['cliente']].iloc[0]
            if tipo == "WA":
                tel_limpio = re.sub(r'\D', '', str(cl_info['telefono']))
                tel_final = "52" + tel_limpio if len(tel_limpio) == 10 else tel_limpio
                msg = (f"Hola {row['cliente']}, te saludamos de Valle Mart. Detectamos un saldo pendiente en tu lote "
                       f"{row['ubicacion']} por {fmt_moneda(row['pago_corriente'])}. Contamos con {row['dias_atraso']} días de atraso.")
                return f"https://wa.me/{tel_final}?text={urllib.parse.quote(msg)}"
            else:
                mail = cl_info['correo']
                return f"mailto:{mail}?subject=Estado de Cuenta - Lote {row['ubicacion']}"
        except: return None

    df_cartera['WhatsApp'] = df_cartera.apply(lambda r: link_contacto(r, "WA"), axis=1)
    df_cartera['Correo'] = df_cartera.apply(lambda r: link_contacto(r, "Mail"), axis=1)

    # --- 5. TABLA DE COBRANZA ---
    st.subheader("📋 Control de Cobranza y Contacto")
    
    c_f1, c_f2 = st.columns(2)
    solo_mora = c_f1.toggle("Ver solo clientes con adeudo", value=True)
    busqueda = c_f2.text_input("🔍 Buscar cliente o lote:")

    df_mostrar = df_cartera.copy()
    if solo_mora:
        df_mostrar = df_mostrar[df_mostrar['pago_corriente'] > 0]
    if busqueda:
        df_mostrar = df_mostrar[df_mostrar['cliente'].astype(str).str.contains(busqueda, case=False) | 
                                df_mostrar['ubicacion'].astype(str).str.contains(busqueda, case=False)]

    if not df_mostrar.empty:
        df_mostrar = df_mostrar.sort_values("dias_atraso", ascending=False)
        df_viz = df_mostrar.copy()
        df_viz["Saldo Vencido"] = df_viz["pago_corriente"].apply(fmt_moneda)
        df_viz['Estatus'] = df_viz['dias_atraso'].apply(
            lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 MORA (+25d)" if x > 25 else "🟢 AL CORRIENTE")
        )

        st.dataframe(
            df_viz[["Estatus", "ubicacion", "cliente", "dias_atraso", "Saldo Vencido", "WhatsApp", "Correo"]],
            column_config={
                "ubicacion": "Lote",
                "cliente": "Cliente",
                "dias_atraso": "Días de Atraso",
                "Saldo Vencido": st.column_config.TextColumn("Saldo Vencido", alignment="right"),
                "WhatsApp": st.column_config.LinkColumn("📲 Enviar WA", display_text="Chat"),
                "Correo": st.column_config.LinkColumn("📧 Enviar Mail", display_text="Email")
            },
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.success("🎉 No se encontraron deudas pendientes con los filtros aplicados.")
