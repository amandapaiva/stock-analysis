import ssl
import json
import urllib.request
import warnings

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Análise de Ações 2025",
    page_icon="📈",
    layout="wide",
)

ACOES = {
    "Petrobras (PETR4)": "PETR4",
    "Itaú (ITUB4)":      "ITUB4",
    "Vale (VALE3)":      "VALE3",
}

CORES = {
    "Petrobras (PETR4)": "#009C3B",
    "Itaú (ITUB4)":      "#003087",
    "Vale (VALE3)":      "#0047AB",
}

_SSL_CTX = ssl._create_unverified_context()


def _buscar_brapi(ticker: str) -> list[dict]:
    url = f"https://brapi.dev/api/quote/{ticker}?range=ytd&interval=1d"
    with urllib.request.urlopen(url, context=_SSL_CTX, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["results"][0].get("historicalDataPrice", [])


@st.cache_data(ttl=3600)
def carregar_dados() -> dict[str, pd.DataFrame]:
    frames = {}
    for nome, ticker in ACOES.items():
        registros = _buscar_brapi(ticker)
        df = pd.DataFrame(registros)
        df["date"] = pd.to_datetime(df["date"], unit="s").dt.normalize()
        df = df.set_index("date").sort_index()
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        # Filtra apenas 2025
        df = df[df.index >= "2025-01-01"]
        frames[nome] = df
    return frames


def retorno_acumulado(df: pd.DataFrame) -> pd.Series:
    return (df["Close"] / df["Close"].iloc[0] - 1) * 100


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("📈 Análise de Ações Brasileiras — 2025")
st.caption("Petrobras · Itaú · Vale | Dados via brapi.dev (B3)")

with st.spinner("Carregando dados..."):
    try:
        dados = carregar_dados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

for nome, df in dados.items():
    if df.empty:
        st.error(f"Sem dados para {nome}.")
        st.stop()

# ── Métricas resumo ───────────────────────────────────────────────────────────

st.subheader("Resumo do Período")
cols = st.columns(3)

for i, (nome, df) in enumerate(dados.items()):
    preco_inicio = float(df["Close"].iloc[0])
    preco_atual  = float(df["Close"].iloc[-1])
    retorno      = (preco_atual / preco_inicio - 1) * 100
    maxima       = float(df["High"].max())
    minima       = float(df["Low"].min())
    volatilidade = float(df["Close"].pct_change().std() * (252 ** 0.5) * 100)

    with cols[i]:
        st.metric(
            label=nome,
            value=f"R$ {preco_atual:.2f}",
            delta=f"{retorno:+.2f}%",
        )
        st.caption(
            f"Máxima: R$ {maxima:.2f} | Mínima: R$ {minima:.2f} | "
            f"Volatilidade anual: {volatilidade:.1f}%"
        )

st.divider()

# ── 1. Retorno acumulado comparativo ─────────────────────────────────────────

st.subheader("Retorno Acumulado Comparativo")

fig_ret = go.Figure()
for nome, df in dados.items():
    ret = retorno_acumulado(df)
    fig_ret.add_trace(go.Scatter(
        x=df.index,
        y=ret,
        name=nome,
        line=dict(color=CORES[nome], width=2),
        hovertemplate="%{x|%d/%m/%Y}<br>Retorno: %{y:.2f}%<extra>" + nome + "</extra>",
    ))

fig_ret.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig_ret.update_layout(
    yaxis_title="Retorno acumulado (%)",
    xaxis_title="Data",
    hovermode="x unified",
    height=420,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_ret, use_container_width=True)

st.divider()

# ── 2. Candlestick + Volume ───────────────────────────────────────────────────

st.subheader("Cotação Diária — Candlestick")

acao_sel = st.selectbox("Selecione a ação", list(ACOES.keys()))
df_sel   = dados[acao_sel]

fig_candle = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.75, 0.25],
    vertical_spacing=0.04,
)

fig_candle.add_trace(
    go.Candlestick(
        x=df_sel.index,
        open=df_sel["Open"],
        high=df_sel["High"],
        low=df_sel["Low"],
        close=df_sel["Close"],
        name="Preço",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

fig_candle.add_trace(
    go.Bar(
        x=df_sel.index,
        y=df_sel["Volume"],
        name="Volume",
        marker_color=CORES[acao_sel],
        opacity=0.6,
    ),
    row=2, col=1,
)

fig_candle.update_layout(
    xaxis_rangeslider_visible=False,
    height=520,
    showlegend=False,
    yaxis_title="Preço (R$)",
    yaxis2_title="Volume",
)
st.plotly_chart(fig_candle, use_container_width=True)

st.divider()

# ── 3. Distribuição de retornos diários ───────────────────────────────────────

st.subheader("Distribuição dos Retornos Diários")

fig_hist = go.Figure()
for nome, df in dados.items():
    ret_dia = df["Close"].pct_change().dropna() * 100
    fig_hist.add_trace(go.Histogram(
        x=ret_dia,
        name=nome,
        opacity=0.65,
        nbinsx=60,
        marker_color=CORES[nome],
    ))

fig_hist.update_layout(
    barmode="overlay",
    xaxis_title="Retorno diário (%)",
    yaxis_title="Frequência",
    height=380,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ── 4. Retorno mensal — heatmap ───────────────────────────────────────────────

st.subheader("Retorno Mensal por Ação")

MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

linhas = []
for nome, df in dados.items():
    mensal = df["Close"].resample("ME").last().pct_change() * 100
    for dt, val in mensal.dropna().items():
        linhas.append({"Ação": nome, "Mês": MESES_PT[dt.month], "Retorno": round(float(val), 2)})

df_mensal = pd.DataFrame(linhas)
pivot     = df_mensal.pivot(index="Ação", columns="Mês", values="Retorno")
meses_ord = [MESES_PT[m] for m in range(1, 13) if MESES_PT[m] in pivot.columns]
pivot     = pivot[meses_ord]

fig_heat = px.imshow(
    pivot,
    text_auto=".1f",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0,
    aspect="auto",
    labels=dict(color="Retorno (%)"),
)
fig_heat.update_layout(height=260, coloraxis_colorbar=dict(title="(%)"))
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── 5. Correlação ─────────────────────────────────────────────────────────────

st.subheader("Correlação entre as Ações")

ret_diarios = pd.DataFrame({
    nome: df["Close"].pct_change()
    for nome, df in dados.items()
}).dropna()

corr = ret_diarios.corr()

fig_corr = px.imshow(
    corr,
    text_auto=".2f",
    color_continuous_scale="Blues",
    zmin=0, zmax=1,
    aspect="auto",
)
fig_corr.update_layout(height=300)
st.plotly_chart(fig_corr, use_container_width=True)

st.caption("Fonte: brapi.dev · B3 · Atualizado automaticamente a cada hora")
