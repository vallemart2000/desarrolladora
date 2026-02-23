import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Cartera de Clientes Activos")

    if df_v.empty:
        st.info("No hay ventas registradas para mostrar en la cartera.")
        return

    # --- 1. PROCESAMIENTO DE FECHAS Y PAGOS ---
    df_v['fecha'] = pd.to_datetime(df_v['fecha'])
    
    if not df_p.empty:
        df_p['fecha'] = pd.to_datetime(df_p['fecha'])
        ultimo_pago = df_p.sort_values('fecha').groupby('lote')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # --- 2. UNIR VENTAS CON ÚLTIMOS PAGOS ---
    df_cartera = df_v[df_v["estatus_pago"] == "Activo"].copy()
    df_cartera = df_cartera.merge(ultimo_pago, on='ubicacion', how='left')
    
    # --- 3. CÁLCULO DE DÍAS DE ATRASO ---
    hoy = datetime.now()
    def calcular_dias(row):
        fecha_referencia = row['fecha_ultimo_pago'] if pd.notnull(row['fecha_ultimo_pago']) else row['fecha']
        diferencia = (hoy - fecha_referencia).days
        return max(0, diferencia)

    df_cartera['dias_atraso'] = df_cartera.apply(calcular_dias, axis=1)

    # --- 4. LÓGICA DE COLORES (SEMÁFORO) ---
    def definir_estatus(dias):
        if dias > 75:
            return "🔴 CRÍTICO (+75 días)"
        elif dias > 25:
            return "🟡 PREVENTIVO (+25 días)"
        else:
            return "🟢 AL CORRIENTE"

    df_cartera['Estatus Cobro'] = df_cartera['dias_atraso'].apply(definir_estatus)

    # --- 5. GENERACIÓN DE LINKS DE CONTACTO ---
    def link_whatsapp(row):
        try:
            tel = df_cl[df_cl['nombre'] == row['cliente']]['telefono'].values[0]
            if not tel or str(tel) == 'nan': return None
            mensaje = f"Hola {row['cliente']}, te saludamos de Valle Mart. Notamos un atraso de {row['dias_atraso']} días en los pagos de tu lote {row['ubicacion']}. ¿Podemos apoyarte en algo?"
            return f"https://wa.me/{str(tel).strip()}?text={urllib.parse.quote(mensaje)}"
        except: return None

    def link_correo(row):
        try:
            mail = df_cl[df_cl['nombre'] == row['cliente']]['correo'].values[0]
            if not mail or str(mail) == 'nan': return None
            asunto = f"Invitación de Pago - Lote {row['ubicacion']}"
            cuerpo = f"Estimado {row['cliente']},\n\nLe enviamos un cordial saludo de parte de Desarrolladora Valle Mart.\n\nLe recordamos que su cuenta presenta un atraso de {row['dias_atraso']} días. Le invitamos a ponerse en contacto con nosotros para regularizar su situación."
            return f"mailto:{mail}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
        except: return None

    df_cartera['WhatsApp'] = df_cartera.apply(link_whatsapp, axis=1)
    df_cartera['Invitación Correo'] = df_cartera.apply(link_correo, axis=1)

    # --- 6. MÉTRICAS DE RESUMEN ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes Activos", len(df_cartera))
    col2.metric("En Alerta (🟡)", len(df_cartera[df_cartera['dias_atraso'] > 25]))
    col3.metric("Urgentes (🔴)", len(df_cartera[df_cartera['dias_atraso'] > 75]))

    st.markdown("---")

    # --- 7. FILTRO SWITCH (NUEVO) ---
    st.write("### 🔍 Filtros de Cartera")
    # Switch activo por defecto (value=True)
    solo_atrasados = st.toggle("Ocultar clientes al corriente", value=True)

    # Aplicamos el filtro si el switch está activo
    if solo_atrasados:
        df_mostrar = df_cartera[df_cartera['dias_atraso'] > 25].copy()
    else:
        df_mostrar = df_cartera.copy()

    # --- 8. TABLA DINÁMICA DE CARTERA ---
    st.subheader("📋 Control de Cobranza y Contacto")

    if df_mostrar.empty:
        st.success("✨ ¡Felicidades! No hay clientes con atraso según el filtro seleccionado.")
    else:
        df_final = df_mostrar[[
            "Estatus Cobro", "ubicacion", "cliente", "dias_atraso", 
            "mensualidad", "WhatsApp", "Invitación Correo"
        ]].sort_values("dias_atraso", ascending=False)

        st.data_editor(
            df_final,
            column_config={
                "Estatus Cobro": st.column_config.TextColumn("Semáforo", width="medium"),
                "ubicacion": "Lote",
                "cliente": "Nombre del Cliente",
                "dias_atraso": st.column_config.NumberColumn("Días de Atraso", format="%d d"),
                "mensualidad": st.column_config.NumberColumn("Mensualidad", format="$ %.2f"),
                "WhatsApp": st.column_config.LinkColumn("📲 Enviar WA", display_text="Enviar Mensaje"),
                "Invitación Correo": st.column_config.LinkColumn("📧 Enviar Mail", display_text="Enviar Invitación")
            },
            use_container_width=True,
            hide_index=True,
            disabled=True,
            key="editor_cartera_inicio_filtrado"
        )

    st.caption("Nota: Los días de atraso se calculan desde el último pago registrado o, en su defecto, desde la fecha de firma del contrato.")
