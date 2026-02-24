import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def verificar_y_reparar_columnas(df, columnas_necesarias, worksheet_name, conn, URL_SHEET):
    """Sincroniza la estructura de la base de datos si faltan columnas."""
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

    # --- 2. MÉTRICAS RÁPIDAS ---
    c1, c2, c3, c4 = st.columns(4)
    total_recaudado = (df_v["enganche_pagado"].sum() + df_p["monto"].sum()) if not df_p.empty else df_v["enganche_pagado"].sum()
    
    c1.metric("💰 Ingresos Totales", f"$ {total_recaudado:,.2f}")
    c2.metric("👥 Clientes Activos", df_v[df_v["estatus_pago"] == "Activo"].shape[0])
    c3.metric("📈 Valor Cartera", f"$ {df_v[df_v['estatus_pago'] == 'Activo']['precio_total'].sum():,.2f}")
    c4.metric("🏗️ Lotes Vendidos", df_v.shape[0])

    st.markdown("---")

    # --- 3. PROCESAMIENTO DE COBRANZA ---
    if df_v.empty:
        st.info("No hay datos de ventas registradas.")
        return

    # Obtener último pago
    if not df_p.empty:
        df_p_clean = df_p.copy()
        df_p_clean['fecha'] = pd.to_datetime(df_p_clean['fecha'], errors='coerce')
        ultimo_pago = df_p_clean.dropna(subset=['fecha']).sort_values('fecha').groupby('ubicacion')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # Unir Datos
    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    hoy = datetime.now()
    
    def calcular_detalles_cobro(row):
        try:
            # Si no hay pago, la referencia es el inicio de mensualidades
            fecha_ref = pd.to_datetime(row['fecha_ultimo_pago']) if pd.notnull(row['fecha_ultimo_pago']) else pd.to_datetime(row['inicio_mensualidades'])
            dias = max(0, (hoy - fecha_ref).days)
            
            mensualidad = float(row['mensualidad'])
            # Lógica de cobro: si tiene más de 30 días, calculamos meses. Si no, sugerimos 1 mensualidad.
            meses_atraso = max(1, dias // 30) if dias > 25 else 0
            pago_sugerido = meses_atraso * mensualidad if dias > 25 else 0.0
            
            return pd.Series([dias, pago_sugerido])
        except:
            return pd.Series([0, 0.0])

    df_cartera[['dias_atraso', 'pago_corriente']] = df_cartera.apply(calcular_detalles_cobro, axis=1)

    # --- 4. GENERACIÓN DE LINKS DE CONTACTO ---
    def generar_contacto(row, tipo):
        try:
            datos_cl = df_cl[df_cl['nombre'] == row['cliente']].iloc[0]
            if tipo == "WA":
                tel = datos_cl['telefono']
                if not tel or str(tel) == 'nan': return None
                msg = (f"Hola {row['cliente']}, te saludamos de Valle Mart. "
                       f"Notamos un atraso de {row['dias_atraso']} días en tu lote {row['ubicacion']}. "
                       f"Monto para regularizar: {fmt_moneda(row['pago_corriente'])}. ¿Cómo podemos apoyarte?")
                return f"https://wa.me/{str(tel).strip()}?text={urllib.parse.quote(msg)}"
            else:
                mail = datos_cl['correo']
                if not mail or str(mail) == 'nan': return None
                asunto = f"Aviso de Cobranza - Lote {row['ubicacion']}"
                cuerpo = (f"Estimado {row['cliente']},\n\nLe informamos que su cuenta presenta "
                          f"{row['dias_atraso']} días de atraso. El monto sugerido para estar "
                          f"al corriente es de {fmt_moneda(row['pago_corriente'])}.")
                return f"mailto:{mail}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
        except: return None

    df_cartera['WhatsApp'] = df_cartera.apply(lambda r: generar_contacto(r, "WA"), axis=1)
    df_cartera['Correo'] = df_cartera.apply(lambda r: generar_contacto(r, "Mail"), axis=1)

    # --- 5. SEMÁFORO (25 y 75 días) ---
    df_cartera['Estatus'] = df_cartera['dias_atraso'].apply(
        lambda x: "🔴 CRÍTICO (+75d)" if x > 75 else ("🟡 PREVENTIVO (+25d)" if x > 25 else "🟢 AL CORRIENTE")
    )

    # --- 6. TABLA PRINCIPAL ---
    st.subheader("📋 Control de Cobranza y Contacto")
    
    # Interruptor encendido por defecto
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)
    
    df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy() if solo_atrasados else df_cartera.copy()

    if df_mostrar.empty:
        st.success("✨ No hay cuentas pendientes de cobro con los filtros actuales.")
    else:
        # Columnas solicitadas: Estatus, Ubicación, Cliente, Días de Atraso, Pago para estar al Corriente, Enviar WA, Enviar Correo
        df_mostrar = df_mostrar.rename(columns={"ubicacion": "Ubicación", "dias_atraso": "Días de Atraso", "pago_corriente": "Pago para estar al Corriente"})
        cols_finales = ["Estatus", "Ubicación", "Cliente", "Días de Atraso", "Pago para estar al Corriente", "WhatsApp", "Correo"]
        
        st.dataframe(
            df_mostrar[cols_finales].sort_values("Días de Atraso", ascending=False),
            column_config={
                "Pago para estar al Corriente": st.column_config.NumberColumn(format="$ %.2f"),
                "Días de Atraso": st.column_config.NumberColumn(format="%d días"),
                "WhatsApp": st.column_config.LinkColumn("📲 Enviar WA", display_text="WhatsApp"),
                "Correo": st.column_config.LinkColumn("📧 Enviar Correo", display_text="Email")
            },
            use_container_width=True,
            hide_index=True
        )

    # --- 7. PRÓXIMOS VENCIMIENTOS ---
    st.markdown("---")
    with st.expander("📅 Ver próximos vencimientos (Próximos 7 días)"):
        # Calculamos quiénes cumplen su ciclo mensual en la próxima semana
        # Basado en el día del mes de 'inicio_mensualidades'
        dia_hoy = hoy.day
        df_vencen = df_cartera.copy()
        df_vencen['dia_pago'] = pd.to_datetime(df_vencen['inicio_mensualidades']).dt.day
        
        # Filtramos los que pagan entre hoy y hoy + 7 días
        prox_7 = df_vencen[(df_vencen['dia_pago'] >= dia_hoy) & (df_vencen['dia_pago'] <= dia_hoy + 7)]
        
        if prox_7.empty:
            st.info("No hay vencimientos programados para los próximos 7 días.")
        else:
            st.table(prox_7[["ubicacion", "cliente", "mensualidad"]].rename(columns={"ubicacion":"Lote", "mensualidad":"Monto Mensual"}))
