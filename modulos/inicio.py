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

    cols_v = {
        "id_venta": 0, "fecha_registro": "", "ubicacion": "", "cliente": "", 
        "vendedor": "", "precio_total": 0.0, "enganche_pagado": 0.0, 
        "mensualidad": 0.0, "estatus_pago": "Activo", "inicio_mensualidades": "",
        "plazo_meses": 0
    }
    df_v = verificar_y_reparar_columnas(df_v, cols_v, "ventas", conn, URL_SHEET)

    total_recaudado = (df_v["enganche_pagado"].sum() + df_p["monto"].sum()) if not df_p.empty else df_v["enganche_pagado"].sum()
    valor_cartera = df_v[df_v['estatus_pago'] == 'Activo']['precio_total'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Ingresos Totales", fmt_moneda(total_recaudado))
    c2.metric("👥 Clientes Activos", df_v[df_v["estatus_pago"] == "Activo"].shape[0])
    c3.metric("📈 Valor Cartera", fmt_moneda(valor_cartera))
    c4.metric("🏗️ Lotes Vendidos", df_v.shape[0])

    st.markdown("---")

    if df_v.empty:
        st.info("No hay datos de ventas registrados.")
        return

    pagos_resumen = df_p.groupby('ubicacion')['monto'].sum().reset_index() if not df_p.empty else pd.DataFrame(columns=['ubicacion', 'monto'])
    pagos_resumen.columns = ['ubicacion', 'total_pagado_cuotas']

    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(pagos_resumen, on='ubicacion', how='left').fillna(0)
    
    hoy = datetime.now()

    def calc_mora(row):
        try:
            f_ini = pd.to_datetime(row['inicio_mensualidades'])
            if pd.isnull(f_ini): f_ini = hoy
            diff = (hoy.year - f_ini.year) * 12 + (hoy.month - f_ini.month)
            if hoy.day < f_ini.day: diff -= 1
            mensualidad = float(row['mensualidad'])
            deuda_teorica = max(0, diff) * mensualidad
            pagado = float(row['total_pagado_cuotas'])
            saldo = max(0.0, deuda_teorica - pagado)
            cubiertos = pagado / mensualidad if mensualidad > 0 else 0
            vence_pendiente = f_ini + pd.DateOffset(months=int(cubiertos))
            dias = (hoy - vence_pendiente).days if saldo > 0 else 0
            return pd.Series([max(0, dias), saldo])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['atraso', 'monto_vencido']] = df_cartera.apply(calc_mora, axis=1)

    def link_contacto(row, tipo):
        try:
            cl_info = df_cl[df_cl['nombre'] == row['cliente']].iloc[0]
            if tipo == "WA":
                tel_limpio = re.sub(r'\D', '', str(cl_info['telefono']))
                tel_final = "52" + tel_limpio if len(tel_limpio) == 10 else tel_limpio
                msg = (f"Hola {row['cliente']}, te saludamos de Valle Mart. Detectamos un saldo pendiente en tu lote "
                       f"{row['ubicacion']} por {fmt_moneda(row['monto_vencido'])}. Contamos con {row['atraso']} días de atraso.")
                return f"https://wa.me/{tel_final}?text={urllib.parse.quote(msg)}"
            else:
                mail = cl_info['correo']
                return f"mailto:{mail}?subject=Estado de Cuenta - Lote {row['ubicacion']}"
        except: return None

    df_cartera['WhatsApp'] = df_cartera.apply(lambda r: link_contacto(r, "WA"), axis=1)
    df_cartera['Correo'] = df_cartera.apply(lambda r: link_contacto(r, "Mail"), axis=1)

    st.subheader("📋 Control de Cobranza y Contacto")
    
    cf1, cf2 = st.columns(2)
    solo_mora = cf1.toggle("Ver solo clientes con adeudo", value=True)
    busqueda = cf2.text_input("🔍 Buscar cliente o lote:")

    df_viz = df_cartera.copy()
    if solo_mora:
        df_viz = df_viz[df_viz['monto_vencido'] > 0]
    if busqueda:
        df_viz = df_viz[df_viz['cliente'].astype(str).str.contains(busqueda, case=False) | 
                        df_viz['ubicacion'].astype(str).str.contains(busqueda, case=False)]

    if not df_viz.empty:
        df_viz = df_viz.sort_values("atraso", ascending=False)
        
        df_viz['Estatus'] = df_viz['atraso'].apply(
            lambda x: "🔴 CRÍTICO(+75)" if x > 75 else ("🟡 MORA(+25)" if x > 25 else "🟢 AL CORRIENTE")
        )

        df_estilado = df_viz[["Estatus", "ubicacion", "cliente", "atraso", "monto_vencido", "WhatsApp", "Correo"]].style.format({
            "monto_vencido": "$ {:,.2f}"
        })

        st.dataframe(
            df_estilado,
            column_config={
                "ubicacion": "Lote",
                "cliente": "Cliente",
                "atraso": "Días de Atraso",
                "monto_vencido": "Saldo Vencido",
                "WhatsApp": st.column_config.LinkColumn("📲 WA", display_text="Chat"),
                "Correo": st.column_config.LinkColumn("📧 Mail", display_text="Email")
            },
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.success("🎉 Todo al corriente.")
