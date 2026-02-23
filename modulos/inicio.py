import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Tablero de Control - Cartera")

    if df_v.empty:
        st.info("No hay ventas registradas para mostrar en la cartera.")
        return

    # --- PROCESAMIENTO DE DATOS ---
    # 1. Obtener el último pago por cada ubicación
    if not df_p.empty:
        df_p['fecha'] = pd.to_datetime(df_p['fecha'])
        ultimo_pago = df_p.sort_values('fecha').groupby('lote')['fecha'].last().reset_index()
        ultimo_pago.columns = ['ubicacion', 'fecha_ultimo_pago']
    else:
        ultimo_pago = pd.DataFrame(columns=['ubicacion', 'fecha_ultimo_pago'])

    # 2. Unir Ventas con Último Pago
    df_cartera = df_v.merge(ultimo_pago, on='ubicacion', how='left')
    
    # 3. Calcular Días de Atraso
    hoy = datetime.now()
    def calcular_atraso(row):
        # Si nunca ha pagado, se toma la fecha de la venta como referencia
        fecha_ref = row['fecha_ultimo_pago'] if pd.notnull(row['fecha_ultimo_pago']) else pd.to_datetime(row['fecha'])
        dias = (hoy - fecha_ref).days
        return max(0, dias)

    df_cartera['dias_atraso'] = df_cartera.apply(calcular_atraso, axis=1)

    # --- LÓGICA DE SEMÁFORO (COLORES) ---
    def color_semaforo(dias):
        if dias > 75:
            return "🔴 Crítico"
        elif dias > 25:
            return "🟡 Preventivo"
        else:
            return "🟢 Al corriente"

    df_cartera['Semaforo'] = df_cartera['dias_atraso'].apply(color_semaforo)

    # --- GENERACIÓN DE LINKS DE CONTACTO ---
    def generar_wa(row):
        # Intentar buscar el teléfono en la tabla de clientes
        tel = ""
        if not df_cl.empty and row['cliente'] in df_cl['nombre'].values:
            tel = df_cl[df_cl['nombre'] == row['cliente']]['telefono'].values[0]
        
        if not tel or tel == "": return None
        
        msg = f"Hola {row['cliente']}, te saludamos de Valle Mart. Notamos un atraso de {row['dias_atraso']} días en tu lote {row['ubicacion']}. ¿Podemos apoyarte en algo?"
        return f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"

    def generar_mail(row):
        correo = ""
        if not df_cl.empty and row['cliente'] in df_cl['nombre'].values:
            correo = df_cl[df_cl['nombre'] == row['cliente']]['correo'].values[0]
        
        if not correo or correo == "": return None
        
        asunto = f"Recordatorio de Pago - Lote {row['ubicacion']}"
        cuerpo = f"Estimado {row['cliente']},\n\nLe informamos que presenta un atraso de {row['dias_atraso']} días en sus pagos..."
        return f"mailto:{correo}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"

    df_cartera['WhatsApp'] = df_cartera.apply(generar_wa, axis=1)
    df_cartera['Correo'] = df_cartera.apply(generar_mail, axis=1)

    # --- MÉTRICAS RÁPIDAS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Lotes Vendidos", len(df_cartera))
    m2.metric("En Riesgo (>25 días)", len(df_cartera[df_cartera['dias_atraso'] > 25]))
    m3.metric("Críticos (>75 días)", len(df_cartera[df_cartera['dias_atraso'] > 75]))

    st.divider()

    # --- TABLA DE CARTERA CONFIGURADA ---
    st.subheader("📋 Detalle de Cartera y Cobranza")
    
    columnas_display = [
        "Semaforo", "ubicacion", "cliente", "dias_atraso", 
        "mensualidad", "WhatsApp", "Correo"
    ]
    
    # Configuración de la tabla interactiva
    st.data_editor(
        df_cartera[columnas_display],
        column_config={
            "Semaforo": st.column_config.TextColumn("Estatus", width="medium"),
            "ubicacion": "Lote",
            "cliente": "Cliente",
            "dias_atraso": st.column_config.NumberColumn("Días Atraso", format="%d d"),
            "mensualidad": st.column_config.NumberColumn("Mensualidad", format="$ %.2f"),
            "WhatsApp": st.column_config.LinkColumn("📲 Enviar WA", display_text="Enviar Mensaje"),
            "Correo": st.column_config.LinkColumn("📧 Enviar Mail", display_text="Enviar Invitación")
        },
        use_container_width=True,
        hide_index=True,
        key="tabla_inicio_cartera"
    )

    # Leyenda de colores
    st.caption("🟢 0-25 días | 🟡 26-75 días | 🔴 +75 días")
