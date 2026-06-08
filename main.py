import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="글로벌 주식 비교 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  .stApp { background: #0a0e1a; color: #e8eaf0; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1221 0%, #111827 100%);
    border-right: 1px solid #1e2d45;
  }
  [data-testid="stSidebar"] .stMarkdown h2 {
    color: #38bdf8; font-size: 0.85rem; letter-spacing: 0.15em;
    text-transform: uppercase; border-bottom: 1px solid #1e2d45; padding-bottom: 8px;
  }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
    border: 1px solid #1e2d45;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
  }
  .metric-card:hover { border-color: #38bdf8; }
  .metric-ticker { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748b; letter-spacing: 0.1em; }
  .metric-name   { font-size: 0.95rem; font-weight: 600; color: #cbd5e1; margin: 2px 0 8px; }
  .metric-price  { font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 600; color: #f1f5f9; }
  .metric-return { font-size: 0.9rem; font-weight: 600; margin-top: 4px; }
  .positive { color: #34d399; }
  .negative { color: #f87171; }

  /* Section headers */
  .section-title {
    font-size: 1.1rem; font-weight: 700; color: #38bdf8;
    letter-spacing: 0.05em; margin: 24px 0 12px;
    display: flex; align-items: center; gap: 8px;
  }
  .section-title::after {
    content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, #1e2d45, transparent);
  }

  /* Hero banner */
  .hero {
    background: linear-gradient(135deg, #0f2744 0%, #0c1a35 50%, #0a1628 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute; top: -40px; right: -40px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%);
    border-radius: 50%;
  }
  .hero h1 { font-size: 1.8rem; font-weight: 700; color: #f1f5f9; margin: 0 0 6px; }
  .hero p  { color: #64748b; font-size: 0.9rem; margin: 0; }
  .hero .badge {
    display: inline-block; background: #0f2744; border: 1px solid #1e3a5f;
    border-radius: 20px; padding: 4px 12px; font-size: 0.75rem;
    color: #38bdf8; margin-right: 8px; margin-top: 12px;
  }

  /* Plotly chart background override */
  .js-plotly-plot .plotly { border-radius: 12px; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 10px; padding: 4px; gap: 2px; }
  .stTabs [data-baseweb="tab"] { background: transparent; color: #64748b; border-radius: 8px; padding: 8px 20px; font-weight: 500; }
  .stTabs [aria-selected="true"] { background: #1e2d45 !important; color: #38bdf8 !important; }

  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
KR_STOCKS = {
    "삼성전자":   "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차":     "005380.KS",
    "NAVER":      "035420.KS",
    "카카오":     "035720.KS",
    "셀트리온":   "068270.KS",
    "KB금융":     "105560.KS",
    "POSCO홀딩스":"005490.KS",
    "기아":       "000270.KS",
}

US_STOCKS = {
    "Apple":    "AAPL",
    "NVIDIA":   "NVDA",
    "Microsoft":"MSFT",
    "Amazon":   "AMZN",
    "Alphabet": "GOOGL",
    "Meta":     "META",
    "Tesla":    "TSLA",
    "Broadcom": "AVGO",
    "JPMorgan": "JPM",
    "Berkshire":"BRK-B",
}

PERIOD_OPTIONS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년":   "1y",
    "2년":   "2y",
    "5년":   "5y",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_data(tickers: list[str], period: str) -> dict[str, pd.DataFrame]:
    result = {}
    for t in tickers:
        try:
            df = yf.download(t, period=period, progress=False, auto_adjust=True)
            if not df.empty:
                result[t] = df
        except Exception:
            pass
    return result

@st.cache_data(ttl=600, show_spinner=False)
def fetch_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}

def calc_return(df: pd.DataFrame) -> float:
    if df is None or df.empty or len(df) < 2:
        return 0.0
    close = df["Close"].squeeze()
    return float((close.iloc[-1] / close.iloc[0] - 1) * 100)

def calc_volatility(df: pd.DataFrame) -> float:
    if df is None or df.empty or len(df) < 5:
        return 0.0
    close = df["Close"].squeeze()
    return float(close.pct_change().dropna().std() * np.sqrt(252) * 100)

def last_price(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    return float(df["Close"].squeeze().iloc[-1])

def normalize(df: pd.DataFrame) -> pd.Series:
    close = df["Close"].squeeze()
    return close / close.iloc[0] * 100

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,14,26,0.6)",
    font=dict(family="Noto Sans KR, JetBrains Mono", color="#94a3b8", size=11),
    xaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45", linecolor="#1e2d45"),
    yaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45", linecolor="#1e2d45"),
    legend=dict(bgcolor="rgba(15,23,42,0.8)", bordercolor="#1e2d45", borderwidth=1),
    margin=dict(l=10, r=10, t=40, b=10),
    hovermode="x unified",
)

KR_COLORS = [
    "#38bdf8","#0ea5e9","#7dd3fc","#bae6fd",
    "#93c5fd","#60a5fa","#3b82f6","#1d4ed8","#2563eb","#1e40af",
]
US_COLORS = [
    "#34d399","#10b981","#6ee7b7","#a7f3d0",
    "#86efac","#4ade80","#22c55e","#16a34a","#15803d","#166534",
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    period_label = st.selectbox("📅 조회 기간", list(PERIOD_OPTIONS.keys()), index=3)
    period = PERIOD_OPTIONS[period_label]

    st.markdown("---")
    st.markdown("## 🇰🇷 한국 종목 선택")
    kr_selected = st.multiselect(
        "코스피 종목", list(KR_STOCKS.keys()),
        default=["삼성전자", "SK하이닉스", "현대차", "NAVER"],
        label_visibility="collapsed",
    )

    st.markdown("## 🇺🇸 미국 종목 선택")
    us_selected = st.multiselect(
        "나스닥/NYSE 종목", list(US_STOCKS.keys()),
        default=["Apple", "NVIDIA", "Microsoft", "Tesla"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("## 📊 차트 설정")
    show_volume   = st.checkbox("거래량 표시", value=True)
    show_ma       = st.checkbox("이동평균선 (20/60일)", value=True)
    show_bb       = st.checkbox("볼린저 밴드", value=False)
    normalize_ret = st.checkbox("수익률 정규화 비교", value=True)

    st.markdown("---")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("데이터 출처: Yahoo Finance")

# ── Validate selections ───────────────────────────────────────────────────────
if not kr_selected and not us_selected:
    st.warning("사이드바에서 최소 하나 이상의 종목을 선택해주세요.")
    st.stop()

kr_tickers = {n: KR_STOCKS[n] for n in kr_selected}
us_tickers = {n: US_STOCKS[n] for n in us_selected}
all_tickers = {**kr_tickers, **us_tickers}

# ── Fetch ─────────────────────────────────────────────────────────────────────
with st.spinner("📡 시장 데이터 수신 중..."):
    all_data = fetch_data(list(all_tickers.values()), period)

# ── Hero ──────────────────────────────────────────────────────────────────────
kr_badge = f"🇰🇷 한국 {len(kr_selected)}종목" if kr_selected else ""
us_badge = f"🇺🇸 미국 {len(us_selected)}종목" if us_selected else ""
st.markdown(f"""
<div class="hero">
  <h1>📈 글로벌 주식 비교 대시보드</h1>
  <p>실시간 주가 데이터 기반 한·미 주요 종목 수익률 비교 분석</p>
  <span class="badge">{kr_badge}</span>
  <span class="badge">{us_badge}</span>
  <span class="badge">📅 {period_label}</span>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 수익률 비교", "📉 개별 차트", "🏆 성과 순위", "📋 상세 지표"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — 수익률 비교
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Metric cards ──
    col_groups = []
    if kr_selected:
        col_groups.append(("🇰🇷 한국 종목", kr_tickers, KR_COLORS))
    if us_selected:
        col_groups.append(("🇺🇸 미국 종목", us_tickers, US_COLORS))

    for title, tickers, colors in col_groups:
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(tickers), 5))
        for i, (name, ticker) in enumerate(tickers.items()):
            df = all_data.get(ticker)
            ret = calc_return(df)
            price = last_price(df)
            sign = "+" if ret >= 0 else ""
            css_cls = "positive" if ret >= 0 else "negative"
            arrow = "▲" if ret >= 0 else "▼"
            col_idx = i % len(cols)
            with cols[col_idx]:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-ticker">{ticker}</div>
                  <div class="metric-name">{name}</div>
                  <div class="metric-price">{price:,.2f}</div>
                  <div class="metric-return {css_cls}">{arrow} {sign}{ret:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Normalized return chart ──
    if normalize_ret:
        st.markdown('<div class="section-title">📈 정규화 수익률 추이 (기준: 100)</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for i, (name, ticker) in enumerate(kr_tickers.items()):
            df = all_data.get(ticker)
            if df is not None and not df.empty:
                norm = normalize(df)
                fig.add_trace(go.Scatter(
                    x=norm.index, y=norm.values, name=f"🇰🇷 {name}",
                    line=dict(color=KR_COLORS[i % len(KR_COLORS)], width=2),
                    hovertemplate=f"<b>{name}</b><br>%{{y:.2f}}<extra></extra>",
                ))
        for i, (name, ticker) in enumerate(us_tickers.items()):
            df = all_data.get(ticker)
            if df is not None and not df.empty:
                norm = normalize(df)
                fig.add_trace(go.Scatter(
                    x=norm.index, y=norm.values, name=f"🇺🇸 {name}",
                    line=dict(color=US_COLORS[i % len(US_COLORS)], width=2, dash="dot"),
                    hovertemplate=f"<b>{name}</b><br>%{{y:.2f}}<extra></extra>",
                ))
        fig.add_hline(y=100, line_dash="dash", line_color="#475569", line_width=1)
        fig.update_layout(**CHART_LAYOUT, height=420, title="")
        st.plotly_chart(fig, use_container_width=True)

    # ── Bar chart ──
    st.markdown('<div class="section-title">📊 기간 수익률 비교 (막대)</div>', unsafe_allow_html=True)
    names, returns, flags, bar_colors = [], [], [], []
    for name, ticker in kr_tickers.items():
        df = all_data.get(ticker)
        ret = calc_return(df)
        names.append(name); returns.append(ret); flags.append("🇰🇷")
        bar_colors.append("#34d399" if ret >= 0 else "#f87171")
    for name, ticker in us_tickers.items():
        df = all_data.get(ticker)
        ret = calc_return(df)
        names.append(name); returns.append(ret); flags.append("🇺🇸")
        bar_colors.append("#34d399" if ret >= 0 else "#f87171")

    sorted_pairs = sorted(zip(returns, names, flags, bar_colors), reverse=True)
    s_ret, s_names, s_flags, s_colors = zip(*sorted_pairs) if sorted_pairs else ([], [], [], [])

    fig2 = go.Figure(go.Bar(
        x=list(s_names),
        y=list(s_ret),
        marker_color=list(s_colors),
        marker_line_width=0,
        text=[f"{r:+.2f}%" for r in s_ret],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11),
        customdata=list(s_flags),
        hovertemplate="<b>%{x}</b><br>수익률: %{y:.2f}%<extra></extra>",
    ))
    fig2.update_layout(**CHART_LAYOUT, height=380, bargap=0.3)
    fig2.update_yaxis(ticksuffix="%")
    st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — 개별 차트
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">종목 상세 차트</div>', unsafe_allow_html=True)
    chart_name = st.selectbox("종목 선택", list(all_tickers.keys()))
    ticker = all_tickers[chart_name]
    df = all_data.get(ticker)

    if df is None or df.empty:
        st.error("데이터를 불러올 수 없습니다.")
    else:
        close = df["Close"].squeeze()
        open_ = df["Open"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        vol   = df["Volume"].squeeze() if "Volume" in df.columns else None

        rows = 2 if (show_volume and vol is not None) else 1
        row_heights = [0.75, 0.25] if rows == 2 else [1.0]
        fig3 = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                              vertical_spacing=0.04, row_heights=row_heights)

        # Candlestick
        fig3.add_trace(go.Candlestick(
            x=df.index, open=open_, high=high, low=low, close=close,
            name=chart_name,
            increasing=dict(fillcolor="#34d399", line=dict(color="#34d399")),
            decreasing=dict(fillcolor="#f87171", line=dict(color="#f87171")),
        ), row=1, col=1)

        # MA
        if show_ma and len(close) >= 20:
            ma20 = close.rolling(20).mean()
            fig3.add_trace(go.Scatter(x=df.index, y=ma20, name="MA20",
                line=dict(color="#fbbf24", width=1.5, dash="dot")), row=1, col=1)
        if show_ma and len(close) >= 60:
            ma60 = close.rolling(60).mean()
            fig3.add_trace(go.Scatter(x=df.index, y=ma60, name="MA60",
                line=dict(color="#a78bfa", width=1.5, dash="dash")), row=1, col=1)

        # Bollinger Bands
        if show_bb and len(close) >= 20:
            ma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            upper = ma20 + 2 * std20
            lower = ma20 - 2 * std20
            fig3.add_trace(go.Scatter(x=df.index, y=upper, name="BB Upper",
                line=dict(color="#94a3b8", width=1, dash="dot"), showlegend=False), row=1, col=1)
            fig3.add_trace(go.Scatter(x=df.index, y=lower, name="BB Lower",
                line=dict(color="#94a3b8", width=1, dash="dot"),
                fill="tonexty", fillcolor="rgba(148,163,184,0.05)", showlegend=False), row=1, col=1)

        # Volume
        if show_volume and vol is not None and rows == 2:
            vol_colors = ["#34d399" if c >= o else "#f87171"
                          for c, o in zip(close, open_)]
            fig3.add_trace(go.Bar(x=df.index, y=vol, name="거래량",
                marker_color=vol_colors, marker_line_width=0, opacity=0.7), row=2, col=1)

        fig3.update_layout(**CHART_LAYOUT, height=550, title=f"{chart_name} ({ticker})")
        fig3.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig3, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — 성과 순위
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">🏆 수익률 순위</div>', unsafe_allow_html=True)

    rows_data = []
    for name, ticker in all_tickers.items():
        df = all_data.get(ticker)
        if df is not None and not df.empty:
            ret = calc_return(df)
            vol_ = calc_volatility(df)
            price = last_price(df)
            market = "🇰🇷 한국" if ticker in kr_tickers.values() else "🇺🇸 미국"
            rows_data.append({
                "종목명": name, "티커": ticker, "시장": market,
                "현재가": price, f"수익률 ({period_label})": ret,
                "연환산 변동성 (%)": vol_,
                "샤프 지수": round(ret / vol_, 2) if vol_ > 0 else 0,
            })

    if rows_data:
        rank_df = pd.DataFrame(rows_data).sort_values(f"수익률 ({period_label})", ascending=False).reset_index(drop=True)
        rank_df.index += 1

        def style_row(val):
            if isinstance(val, float):
                if val > 0: return "color: #34d399; font-weight: 600;"
                elif val < 0: return "color: #f87171; font-weight: 600;"
            return ""

        styled = (
            rank_df.style
            .applymap(style_row, subset=[f"수익률 ({period_label})", "샤프 지수"])
            .format({
                "현재가": "{:,.2f}",
                f"수익률 ({period_label})": "{:+.2f}%",
                "연환산 변동성 (%)": "{:.2f}%",
            })
            .set_properties(**{
                "background-color": "#0a0e1a",
                "color": "#cbd5e1",
                "border-color": "#1e2d45",
            })
            .set_table_styles([
                {"selector": "th", "props": [
                    ("background-color", "#111827"), ("color", "#38bdf8"),
                    ("font-weight", "600"), ("border-color", "#1e2d45"),
                ]},
                {"selector": "tr:hover td", "props": [("background-color", "#111827")]},
            ])
        )
        st.dataframe(styled, use_container_width=True)

        # Scatter: Return vs Volatility
        st.markdown('<div class="section-title">리스크-수익률 산점도</div>', unsafe_allow_html=True)
        fig4 = px.scatter(
            rank_df,
            x="연환산 변동성 (%)", y=f"수익률 ({period_label})",
            text="종목명", color="시장",
            color_discrete_map={"🇰🇷 한국": "#38bdf8", "🇺🇸 미국": "#34d399"},
            size_max=14,
        )
        fig4.update_traces(textposition="top center", textfont=dict(size=10, color="#cbd5e1"),
                           marker=dict(size=12, line=dict(width=1, color="#0a0e1a")))
        fig4.add_hline(y=0, line_dash="dash", line_color="#475569", line_width=1)
        fig4.update_layout(**CHART_LAYOUT, height=420,
                           xaxis_title="연환산 변동성 (%)", yaxis_title=f"수익률 ({period_label}) (%)")
        fig4.update_yaxes(ticksuffix="%")
        fig4.update_xaxes(ticksuffix="%")
        st.plotly_chart(fig4, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — 상세 지표
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">📋 상세 재무 지표</div>', unsafe_allow_html=True)
    detail_name = st.selectbox("종목 선택 ", list(all_tickers.keys()), key="detail_sel")
    detail_ticker = all_tickers[detail_name]

    with st.spinner("재무 데이터 로딩 중..."):
        info = fetch_info(detail_ticker)

    if info:
        c1, c2, c3 = st.columns(3)
        def info_metric(col, label, key, fmt=None):
            val = info.get(key, "N/A")
            if val != "N/A" and fmt:
                try: val = fmt.format(val)
                except: pass
            col.metric(label, val)

        with c1:
            st.markdown("**📌 기업 정보**")
            info_metric(c1, "시가총액", "marketCap", "{:,.0f}")
            info_metric(c1, "섹터", "sector")
            info_metric(c1, "직원 수", "fullTimeEmployees", "{:,.0f}")
        with c2:
            st.markdown("**💰 밸류에이션**")
            info_metric(c2, "PER (TTM)", "trailingPE", "{:.2f}x")
            info_metric(c2, "PBR", "priceToBook", "{:.2f}x")
            info_metric(c2, "EV/EBITDA", "enterpriseToEbitda", "{:.2f}x")
        with c3:
            st.markdown("**📈 가격 정보**")
            info_metric(c3, "52주 최고", "fiftyTwoWeekHigh", "{:,.2f}")
            info_metric(c3, "52주 최저", "fiftyTwoWeekLow", "{:,.2f}")
            info_metric(c3, "배당수익률", "dividendYield")

        # Description
        desc = info.get("longBusinessSummary", "")
        if desc:
            st.markdown('<div class="section-title">기업 소개</div>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#94a3b8;font-size:0.88rem;line-height:1.7">{desc[:600]}{"..." if len(desc)>600 else ""}</p>', unsafe_allow_html=True)
    else:
        st.info("상세 재무 데이터를 불러올 수 없습니다.")
