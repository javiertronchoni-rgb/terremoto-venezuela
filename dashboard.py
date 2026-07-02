import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from data_sources import (
    load_historial, get_current_snapshot, fetch_usgs_aftershocks
)
from alert_engine import check_for_updates

st.set_page_config(
    page_title="Venezuela Terremoto 2026 — Panel en Vivo",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LIGHT_RED = "#E74C3C"
DARK_RED = "#C0392B"
BLUE = "#2980B9"
ORANGE = "#E67E22"
GREEN = "#27AE60"
GRAY = "#7F8C8D"

st.markdown("""
<style>
    .kpi-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
    }
    .kpi-number {
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #95a5a6;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-delta {
        font-size: 0.85rem;
        margin-top: 2px;
    }
    .delta-up { color: #E74C3C; }
    .delta-down { color: #27AE60; }
    .info-box {
        background: #0f3460;
        border-radius: 8px;
        padding: 10px 16px;
        color: white;
        margin-bottom: 12px;
    }
    .alert-box {
        background: #2c1200;
        border-left: 4px solid #E67E22;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    .alert-time {
        font-size: 0.75rem;
        color: #95a5a6;
    }
    .stApp { background: #0d0d1a; }
    h1, h2, h3, p { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.title(" Terremotos Venezuela 2026 — Panel en Vivo")
st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} VET")

snapshot, usgs_events = get_current_snapshot()
historial = load_historial()

import pandas as pd
from data_sources import save_historial
new_row = pd.DataFrame([snapshot])
historial = pd.concat([historial, new_row], ignore_index=True)
save_historial(historial)

FALLBACK_EDIFICIOS = 1423
FALLBACK_DESPLAZADOS = 7000

last_row = historial.iloc[-1] if not historial.empty else None

def val_or_last(snap_key, hist_col):
    v = snapshot.get(snap_key)
    if v is not None and v > 0:
        return v
    if last_row is not None and hist_col in last_row:
        lv = last_row[hist_col]
        if lv is not None and lv > 0:
            return int(lv)
    return 0

muertos = val_or_last('muertos', 'muertos')
heridos = val_or_last('heridos', 'heridos')
desaparecidos = val_or_last('desaparecidos', 'desaparecidos')
replicas = snapshot.get('replicas') or len(usgs_events) or 302
edificios = snapshot.get('edificios_afectados') or FALLBACK_EDIFICIOS
desplazados = snapshot.get('desplazados') or FALLBACK_DESPLAZADOS

delta_m = 0
delta_h = 0
if len(historial) >= 2:
    prev = historial.iloc[-2]
    delta_m = muertos - (prev.get('muertos') or 0)
    delta_h = heridos - (prev.get('heridos') or 0)

col1, col2, col3, col4 = st.columns(4)
with col1:
    dm = f"+{delta_m}" if delta_m > 0 else "0"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number" style="color:{LIGHT_RED}">{muertos:,}</div>
        <div class="kpi-label">Muertos</div>
        <div class="kpi-delta {'delta-up' if delta_m > 0 else ''}">últ. cambio: {dm}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    dh = f"+{delta_h}" if delta_h > 0 else "0"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number" style="color:{ORANGE}">{heridos:,}</div>
        <div class="kpi-label">Heridos</div>
        <div class="kpi-delta {'delta-up' if delta_h > 0 else ''}">últ. cambio: {dh}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number" style="color:{GRAY}">{replicas}</div>
        <div class="kpi-label">Réplicas (≥M2.5)</div>
        <div class="kpi-delta">USGS</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number" style="color:{BLUE}">{desaparecidos:,}</div>
        <div class="kpi-label">Desaparecidos</div>
        <div class="kpi-delta">+ {edificios:,} infraest. afectadas</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([" Evolución víctimas", " Réplicas", " Balances oficiales", " Infraestructura"])

with tab1:
    st.subheader("Evolución del número de víctimas")

    if not historial.empty and len(historial) >= 2:
        df = historial.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['muertos'],
            mode='lines+markers', name='Muertos',
            line=dict(color=LIGHT_RED, width=3),
            marker=dict(size=8, color=LIGHT_RED),
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['heridos'],
            mode='lines+markers', name='Heridos',
            line=dict(color=ORANGE, width=3),
            marker=dict(size=8, color=ORANGE),
        ))
        if 'desaparecidos' in df.columns and df['desaparecidos'].notna().any():
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['desaparecidos'],
                mode='lines+markers', name='Desaparecidos',
                line=dict(color=GRAY, width=2, dash='dot'),
                marker=dict(size=6, color=GRAY),
            ))
        fig.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            yaxis_title="Personas",
            xaxis_title="Fecha",
            height=450,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay suficientes datos históricos aún. Se irán acumulando con cada apertura.")

    st.metric("Último registro", f"{muertos:,} muertos · {heridos:,} heridos · {desaparecidos:,} desaparecidos")

with tab2:
    st.subheader("Actividad sísmica — Réplicas")

    if usgs_events:
        df_usgs = pd.DataFrame(usgs_events)
        df_usgs['time'] = pd.to_datetime(df_usgs['time'])

        last_24h = df_usgs[df_usgs['time'] >= datetime.now() - timedelta(hours=24)]

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total réplicas (≥M2.5)", len(df_usgs), delta=None)
        with col_b:
            st.metric("Últimas 24h", len(last_24h))
        with col_c:
            mayor = df_usgs['mag'].max() if not df_usgs.empty else 0
            st.metric("Mayor magnitud", f"M{mayor:.1f}")

        st.markdown("<br>", unsafe_allow_html=True)

        fig2 = go.Figure()
        for _, row in df_usgs.iterrows():
            color = 'red' if row['mag'] >= 5 else 'orange' if row['mag'] >= 4 else '#555'
            size = (row['mag'] - 2) * 10
            fig2.add_trace(go.Scatter(
                x=[row['time']], y=[row['mag']],
                mode='markers',
                marker=dict(size=size, color=color, line=dict(color='white', width=0.5)),
                name=row['place'] if len(usgs_events) <= 20 else '',
                text=f"{row['place']}<br>M{row['mag']}",
                hoverinfo='text',
                showlegend=False,
            ))

        fig2.update_layout(
            template='plotly_dark',
            title="Cada burbuja = una réplica (tamaño = magnitud, color = intensidad)",
            xaxis_title="Fecha",
            yaxis_title="Magnitud",
            height=400,
            hovermode='closest',
            yaxis=dict(range=[2, 8]),
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown(f"<p style='color:#95a5a6; font-size:0.85rem; text-align:center'>"
                    f"{len(usgs_events)} réplicas registradas por USGS desde el 24 junio. "
                    f"{len(last_24h)} en las últimas 24h.</p>", unsafe_allow_html=True)
    else:
        st.info("No se pudieron obtener datos de réplicas del USGS.")

with tab3:
    st.subheader("Historial de balances oficiales")

    if not historial.empty:
        df_h = historial.copy()
        df_h['timestamp'] = pd.to_datetime(df_h['timestamp'])
        df_h = df_h.sort_values('timestamp', ascending=False).reset_index(drop=True)

        for i, row in df_h.iterrows():
            ts = row['timestamp']
            cls = "alert-box"
            st.markdown(f"""
            <div class="{cls}">
                <strong style="color:{LIGHT_RED}">{row.get('muertos', '?')} muertos</strong>
                · {row.get('heridos', '?')} heridos
                · {row.get('desaparecidos', '?')} desaparecidos
                <br>
                <span class="alert-time">{ts.strftime('%d/%m/%Y %H:%M')} — {row.get('fuente', 'N/A')}</span>
            </div>
            """, unsafe_allow_html=True)

        st.download_button(
            " Descargar historial CSV",
            data=df_h.to_csv(index=False).encode('utf-8'),
            file_name=f"venezuela_historial_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No hay balances registrados todavía.")

with tab4:
    st.subheader("Infraestructura afectada")

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        infra_data = {
            'Categoría': ['Edificios', 'Hospitales', 'Centros comerciales', 'Otras estructuras'],
            'Afectados': [383, 13, 25, 1002],
        }
        df_infra = pd.DataFrame(infra_data)
        fig4 = px.bar(
            df_infra, x='Categoría', y='Afectados',
            color='Afectados', color_continuous_scale='Reds',
            title="Daños por tipo de infraestructura",
        )
        fig4.update_layout(template='plotly_dark', height=350)
        st.plotly_chart(fig4, use_container_width=True)

    with col_i2:
        st.markdown(f"""
        <div class="info-box">
            <strong>Aeropuerto Maiquetía:</strong> Cerrado, daños estructurales
        </div>
        <div class="info-box">
            <strong>Metro de Caracas:</strong> Servicio suspendido
        </div>
        <div class="info-box">
            <strong>Gas doméstico:</strong> Corte preventivo en zonas afectadas
        </div>
        <div class="info-box">
            <strong>Electricidad:</strong> Cortes reportados en múltiples estados
        </div>
        <div class="info-box">
            <strong>Desplazados:</strong> {desplazados:,} personas
        </div>
        <div class="info-box">
            <strong>Daño económico estimado:</strong> $4.7–8.7 mil millones (USGS)
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("Fuentes: USGS · OCHA · Wikipedia · Noticias oficiales")
st.caption("Actualiza la página (F5/Cmd+R) para obtener los últimos datos.")
