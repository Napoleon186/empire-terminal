import streamlit as st
import google.generativeai as genai
import feedparser
import json
import time
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import urllib.parse

# --- CONFIGURATION PAGE & DESIGN ---
st.set_page_config(
    page_title="Napoleon Terminal",
    page_icon="🦅",
    layout="wide", # On passe en mode "Grand Écran"
    initial_sidebar_state="expanded"
)

# ⚠️ TA CLÉ API ICI
try:
    API_KEY = st.secrets["AIzaSyDAf-WC1QRB4ayxzEaxp7oOJzq2MP13Bxc"]
except:
    API_KEY = "AIzaSyDAf-WC1QRB4ayxzEaxp7oOJzq2MP13Bxc" 

genai.configure(api_key=API_KEY)

# --- LISTE DES ACTIFS SURVEILLÉS ---
ASSETS = {
    "🪙 Bitcoin (BTC)": "BTC-USD",
    "💎 Ethereum (ETH)": "ETH-USD",
    "🚀 Solana (SOL)": "SOL-USD",
    "🤖 Nvidia (NVDA)": "NVDA",
    "🚗 Tesla (TSLA)": "TSLA",
    "🍏 Apple (AAPL)": "AAPL",
    "🇺🇸 S&P 500": "^GSPC"
}

# --- BRIQUE 1 : TECHNIQUE & GRAPHIQUES ---
def get_market_data(symbol):
    """Récupère historique + RSI + Prix actuel"""
    try:
        # On télécharge plus de données pour le graphique (6 mois)
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        # Calcul RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Dernières valeurs
        current_price = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1])
        
        # Calcul variation 24h
        prev_price = float(df['Close'].iloc[-2])
        variation = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "price": current_price,
            "rsi": current_rsi,
            "variation": variation,
            "history": df['Close'] # On renvoie tout l'historique pour le dessin
        }
    except Exception as e:
        st.error(f"Erreur Data: {e}")
        return None

# --- BRIQUE 2 : NEWS CIBLÉES (Google News) ---
def get_specific_news(query):
    """Cherche les news SPÉCIFIQUES à l'actif choisi"""
    # On encode la requête pour l'URL (ex: "Tesla Stock")
    encoded_query = urllib.parse.quote(f"{query} finance news")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(rss_url)
    return [entry.title for entry in feed.entries[:5]]

def analyze_sentiment(news_list, asset_name):
    if not news_list: return []
    
    prompt = f"""
    Analyse ces titres de news concernant {asset_name}.
    ATTENTION : Sois critique. Discerne la vraie info de la "Hype".
    Pour chaque titre, renvoie un JSON strict : {{"titre": "...", "sentiment": "BULLISH/BEARISH/NEUTRAL"}}.
    Titres : {json.dumps(news_list)}
    """
    
    model = genai.GenerativeModel(
        'gemini-flash-latest',
        generation_config={"response_mime_type": "application/json"}
    )
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except:
        return []

# --- BRIQUE 3 : STRATÈGE SUPRÊME ---
def get_strategic_verdict(asset_name, tech_data, sentiment_score):
    prompt = f"""
    Tu es le conseiller personnel de Napoléon Bonaparte, réincarné en Trader d'élite.
    
    ACTIF CIBLÉ : {asset_name.upper()}
    
    RAPPORTS DU FRONT :
    1. TECHNIQUE : RSI à {tech_data['rsi']:.1f} (Rappel: <30=Soldes, >70=Surchauffe).
    2. FONDAMENTAL : Sentiment News à {sentiment_score}/100.
    
    ORDRES :
    Donne un ordre clair : ACHAT, VENTE, ou ATTENTE.
    Justifie avec une autorité militaire et une logique implacable.
    Style : Direct, Historique, Puissant. Max 3 phrases.
    """
    model = genai.GenerativeModel('gemini-flash-latest')
    return model.generate_content(prompt).text

# ==========================================
#              INTERFACE UTILISATEUR
# ==========================================

# -- SIDEBAR (Le Tableau de Bord) --
with st.sidebar:
    st.title("🦅 Empire Terminal")
    st.markdown("---")
    
    # LE SÉLECTEUR MAGIQUE
    selected_asset_name = st.selectbox("🎯 Cible à analyser", list(ASSETS.keys()))
    symbol = ASSETS[selected_asset_name]
    
    st.markdown("---")
    st.caption(f"Symbole Ticker : {symbol}")
    st.info("Connecté au Satellite Google News 🛰️")

# -- MAIN PAGE --
st.title(f"Analyse Stratégique : {selected_asset_name}")

if st.button("🚀 LANCER L'ASSAUT ANALYTIQUE", type="primary"):
    
    # Barre de progression stylée
    progress_text = "Analyse en cours..."
    my_bar = st.progress(0, text=progress_text)
    
    # 1. DATA MARKETS
    data = get_market_data(symbol)
    my_bar.progress(30, text="📡 Récupération des données de marché...")
    
    # 2. DATA NEWS
    # On nettoie le nom pour la recherche (ex: "Coinbase (COIN)" -> "Coinbase")
    search_term = selected_asset_name.split("(")[0] 
    news = get_specific_news(search_term)
    my_bar.progress(60, text=f"📰 Lecture des dépêches sur {search_term}...")
    
    sentiments = analyze_sentiment(news, search_term)
    my_bar.progress(90, text="🧠 Délibération du Conseil de Guerre...")
    
    # 3. SCORING
    score_news = 50 + sum([10 if n['sentiment']=='BULLISH' else -10 if n['sentiment']=='BEARISH' else 0 for n in sentiments])
    score_news = max(0, min(100, score_news))
    
    verdict = get_strategic_verdict(search_term, data, score_news)
    my_bar.progress(100, text="Terminé.")
    time.sleep(0.5)
    my_bar.empty() # On cache la barre

    # --- AFFICHAGE DES RÉSULTATS (Layout Pro) ---
    
    # Ligne 1 : Les KPIs clés
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Prix Actuel", f"{data['price']:.2f} $", f"{data['variation']:.2f}%")
    with col2:
        st.metric("RSI (Technique)", f"{data['rsi']:.1f}", "Zone Surchauffe" if data['rsi']>70 else "Zone Achat" if data['rsi']<30 else "Neutre")
    with col3:
        delta_news = score_news - 50
        st.metric("Sentiment News", f"{score_news}/100", f"{delta_news} pts")

    st.markdown("---")

    # Ligne 2 : Graphique & Verdict
    c1, c2 = st.columns([2, 1]) # La colonne graph est 2x plus large
    
    with c1:
        st.subheader("📉 Topographie (6 mois)")
        st.line_chart(data['history'], color="#FF4B4B") # Couleur rouge impérial
        
    with c2:
        st.subheader("📜 Ordre Impérial")
        
        verdict_upper = verdict.upper()
        if "ACHAT" in verdict_upper:
            st.success(verdict, icon="🟢")
        elif "ATTENTE" in verdict_upper:
            st.warning(verdict, icon="✋")
        elif "VENTE" in verdict_upper:
            st.error(verdict, icon="🔴")
        else:
            st.info(verdict) # Cas par défaut si l'IA est ambiguë
        
        with st.expander("Voir les dépêches interceptées"):
            for s in sentiments:
                icon = "🟢" if s['sentiment'] == "BULLISH" else "🔴" if s['sentiment'] == "BEARISH" else "⚪"
                st.write(f"{icon} {s['titre']}")

else:
    st.info("Sélectionnez un actif dans le menu de gauche et lancez l'assaut.")
