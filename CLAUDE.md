# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```powershell
python -m streamlit run app.py
```

Opens at **http://localhost:8501**. Streamlit hot-reloads on file save — no restart needed for most changes.

## Architecture

Single-file Streamlit app (`app.py`). The data flow is:

1. **`_buscar_brapi(ticker)`** — fetches raw OHLCV JSON from `brapi.dev/api/quote/{ticker}?range=ytd&interval=1d`
2. **`carregar_dados()`** — calls the above for all three tickers, converts Unix timestamps to dates, renames columns to title-case (`Open/High/Low/Close/Volume`), filters to 2025-01-01+, and returns a `dict[str, DataFrame]` keyed by display name. Cached for 1 hour via `@st.cache_data(ttl=3600)`.
3. The rest of the file is sequential Streamlit rendering — each chart section reads from `dados` directly.

## Key implementation details

**SSL**: Python on Windows doesn't trust system certificates by default. All outbound requests use `ssl._create_unverified_context()` stored in `_SSL_CTX`. Do not switch back to `yfinance` — it uses `curl_cffi` internally and is not fixable the same way, and Yahoo Finance rate-limits aggressively.

**Data source**: `brapi.dev` (Brazilian B3 API, no auth key needed for this usage). Tickers are bare B3 codes (`PETR4`, `ITUB4`, `VALE3`) — no `.SA` suffix.

**Adding a new stock**: add an entry to both `ACOES` (display name → B3 ticker) and `CORES` (display name → hex color). Everything else adapts automatically.

**Chart library**: Plotly via `plotly.graph_objects` for candlestick/scatter/histogram/bar, `plotly.express` for heatmap and correlation matrix.

## GitHub

Repositório: **https://github.com/amandapaiva/stock-analysis**

Cada alteração feita pelo Claude Code é automaticamente commitada e enviada ao GitHub. Isso é configurado via hook `PostToolUse` em `.claude/settings.json` — sempre que um arquivo é editado ou criado, o hook executa:

```bash
git add -A && git diff --cached --quiet || (git commit -m "auto: update project files" && git push origin master)
```

O git está configurado com `http.sslVerify false` localmente para contornar o problema de certificados SSL do Windows (mesmo root cause do `_SSL_CTX` na aplicação).

Para push manual:

```bash
cd "C:/Users/amand/Downloads/VSCode"
git add -A && git commit -m "mensagem" && git push origin master
```
