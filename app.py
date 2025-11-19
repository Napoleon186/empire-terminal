import streamlit as st
import google.generativeai as genai
import feedparser
import json
import time
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import urllib.parse
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION DESIGN "DEEPMIND" ---
st.set_page_config(
    page_title="Empire Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Injection de CSS pour le look "Apple/Dark"
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetricValue"] {
        font-size: 28px; font-family: 'Helvetica Neue', sans-serif; font-weight: 700;
    }
    .stButton>button {
        background-color: #2962FF; color: white; border-radius: 8px; border: none; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0039CB;
    }
</style>
""", unsafe_allow_html=True)

# ⚠️ TA CLÉ API (À remplacer si besoin ou utiliser st.secrets)
try:
    API_KEY = st.secrets["AIzaSyDAf-WC1QRB4ayxzEaxp7oOJzq2MP13Bxc"]
except:
    API_KEY = "AIzaSyDAf-WC1QRB4ayxzEaxp7oOJzq2MP13Bxc" 
genai.configure(api_key=API_KEY)

# --- MOTEUR ANALYTIQUE ROBUSTE (V3.2) ---
def get_deep_market_data(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        
        if df.empty: 
            st.error("Aucune donnée reçue. Vérifiez le symbole.")
            return None
            
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.droplevel(1)
        
        # 1. MACD
        macd_df = ta.macd(df['Close'])
        # Recherche dynamique des colonnes
        macd_line_col = [c for c in macd_df.columns if c.startswith('MACD_')][0]
        macd_signal_col = [c for c in macd_df.columns if c.startswith('MACDs_')][0]
        df = pd.concat([df, macd_df], axis=1)

        # 2. BOLLINGER BANDS (20 jours)
        bb_df = ta.bbands(df['Close'], length=20)
        # Recherche dynamique des colonnes
        bbu_col = [c for c in bb_df.columns if c.startswith('BBU_')][0] # Upper
        bbl_col = [c for c in bb_df.columns if c.startswith('BBL_')][0] # Lower
        df = pd.concat([df, bb_df], axis=1)

        # 3. RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        analysis = {
            "price": float(last['Close']),
            "change_pct": float((last['Close'] - prev['Close']) / prev['Close'] * 100),
            "rsi": float(last['RSI']),
            "macd_line": float(last[macd_line_col]),
            "macd_signal": float(last[macd_signal_col]),
            "bb_upper": float(last[bbu_col]),
            "bb_lower": float(last[bbl_col]),
            "history": df, # On passe tout l'historique pour le graph
            # On passe aussi les noms de colonnes trouvés pour que le graph sache quoi dessiner
            "col_names": {"bbu": bbu_col, "bbl": bbl_col} 
        }
        return analysis
        
    except Exception as e:
        st.error(f"Erreur Technique : {e}")
        return None

# --- MOTEUR GRAPHIQUE PRO (CORRIGÉ) ---
def plot_pro_chart(df, symbol, col_names):
    # On récupère les bons noms de colonnes trouvés par le moteur
    bbu = col_names['bbu']
    bbl = col_names['bbl']

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 1. Chandeliers
    fig.add_trace(go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name='Prix'), row=1, col=1)

    # 2. Bandes de Bollinger (Avec les noms dynamiques !)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', width=1, dash='dot'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', width=1, dash='dot'), name='BB Lower'), row=1, col=1)

    # 3. RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#2962FF', width=2), name='RSI'), row=2, col=1)
    
    # Seuils RSI
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=70, y1=70, line=dict(color="red", width=1, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=30, y1=30, line=dict(color="green", width=1, dash="dash"), row=2, col=1)

    fig.update_layout(
        title=f"Analyse Technique : {symbol}",
        yaxis_title='Prix ($)',
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- INTELLIGENCE STRATÉGIQUE ---
def get_emperor_verdict(asset, data, sentiment):
    prompt = f"""
    Agis comme un Trader Institutionnel.
    ACTIF : {asset}
    TECHNIQUE : Prix {data['price']:.2f}, RSI {data['rsi']:.1f}, MACD {data['macd_line']:.2f}.
    SENTIMENT NEWS : {sentiment}/100.
    
    Donne une stratégie concise :
    1. ANALYSE (C'est haussier ou baissier ?)
    2. ACTION (Acheter maintenant ? Attendre ?)
    3. NIVEAUX (Stop Loss suggéré)
    """
    model = genai.GenerativeModel('gemini-flash-latest')
    return model.generate_content(prompt).text

# --- MAIN APP ---

col_logo, col_title = st.columns([1, 5])
with col_logo: st.write("🦅")
with col_title: st.title("EMPIRE TERMINAL")

# Barre de recherche
c1, c2 = st.columns([3, 1])
with c1:
    asset_input = st.text_input("Rechercher un actif (ex: BTC-USD, NVDA, AAPL)", value="BTC-USD")
with c2:
    st.write("")
    st.write("")
    launch = st.button("INITIALISER L'ANALYSE")

if launch:
    with st.spinner("Extraction des données vectorielles & Analyse Deep Learning..."):
        
        # 1. DATA
        tech_data = get_deep_market_data(asset_input)
        
        if tech_data:
            # Simulation news (pour l'exemple)
            sentiment_score = 60 
            
            # 2. KPI
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Prix", f"{tech_data['price']:.2f}$", f"{tech_data['change_pct']:.2f}%")
            k2.metric("RSI", f"{tech_data['rsi']:.1f}", "Surchauffe" if tech_data['rsi']>70 else "Soldé" if tech_data['rsi']<30 else "Neutre")
            
            macd_delta = tech_data['macd_line'] - tech_data['macd_signal']
            k3.metric("Momentum MACD", f"{macd_delta:.2f}", "Hausse" if macd_delta > 0 else "Baisse")
            
            dist_bb = tech_data['price'] - tech_data['bb_lower']
            k4.metric("Support Bollinger", f"{dist_bb:.0f} pts", "Danger" if dist_bb < 0 else "Secure")
            
            st.markdown("---")
            
            # 3. GRAPHIQUE (Appel corrigé avec les noms de colonnes)
            chart = plot_pro_chart(tech_data['history'], asset_input, tech_data['col_names'])
            st.plotly_chart(chart, use_container_width=True)
            
            # 4. RAPPORT
            st.subheader("🧠 Analyse Systémique")
            verdict = get_emperor_verdict(asset_input, tech_data, sentiment_score)

            st.info(verdict)

