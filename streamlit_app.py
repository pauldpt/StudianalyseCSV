"""
Interface Streamlit professionnelle pour analyse CSV.
UI moderne, interactive, et accessible aux non-initiés.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime

# Imports personnalises
from core_analysis import (
    CSVAnalyzer, GroqClient, load_custom_corrections,
    CONFIDENCE_THRESHOLD_AUTO, CONFIDENCE_THRESHOLD_FIX_ALL
)
from graphiques import GraphicsGenerator
from rapport_generator import RapportGenerator

# Configuration Streamlit
st.set_page_config(
    page_title="Analyse et Nettoyage CSV",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)




# --- DESIGN PREMIUM PRO ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

body {
    color: #f0f2f5;
    background: linear-gradient(135deg, #0f172a 0%, #1a1f3a 100%);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Titres premium */
h1, h2, h3 {
    color: #ffffff !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

h1 { 
    font-size: 2.5rem !important;
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    margin-bottom: 1rem !important;
}

h2 { 
    font-size: 1.6rem !important; 
    margin-top: 2rem !important;
    color: #ffffff !important;
}

h3 { font-size: 1.2rem !important; }

/* Metriques premium */
[data-testid="stMetric"] {
    background: rgba(255, 107, 53, 0.08) !important;
    border: 1px solid rgba(255, 107, 53, 0.2) !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
}

/* Sidebar moderne et impressive */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(26, 31, 58, 0.98) 100%) !important;
    border-right: 1px solid rgba(255, 107, 53, 0.15) !important;
    backdrop-filter: blur(20px) !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:first-child {
    background: linear-gradient(135deg, rgba(255, 107, 53, 0.1) 0%, rgba(255, 107, 53, 0.05) 100%) !important;
    border: 1px solid rgba(255, 107, 53, 0.15) !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    margin-bottom: 1.5rem !important;
}

[data-testid="stSidebar"] h1 {
    color: #ffffff !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    margin-bottom: 0.2rem !important;
}

[data-testid="stSidebar"] h2 {
    color: #ff6b35 !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1rem !important;
    opacity: 0.8 !important;
}

[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
    font-size: 1rem !important;
    margin-top: 1rem !important;
}

[data-testid="stSidebar"] p {
    color: #cbd5e0 !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
}

/* Messages stylés */
[data-testid="stAlert"] {
    border: 1px solid rgba(255, 107, 53, 0.2) !important;
    border-radius: 1rem !important;
    background: rgba(255, 107, 53, 0.08) !important;
    backdrop-filter: blur(10px) !important;
    padding: 1.2rem 1.5rem !important;
    font-weight: 500 !important;
}

/* Dataframe premium */
[data-testid="stDataFrame"] {
    border-radius: 1rem !important;
    border: 1px solid rgba(255, 107, 53, 0.15) !important;
    overflow: hidden !important;
}

/* Boutons premium */
button[kind="primary"] {
    background: linear-gradient(135deg, #ff6b35 0%, #ff5722 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 0.8rem !important;
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 8px 16px rgba(255, 107, 53, 0.25) !important;
    text-transform: capitalize !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(135deg, #ff7c4a 0%, #ff6838 100%) !important;
    box-shadow: 0 12px 24px rgba(255, 107, 53, 0.35) !important;
    transform: translateY(-2px) !important;
}

button[kind="primary"]:active {
    transform: translateY(0) !important;
}

button {
    border-radius: 0.8rem !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255, 107, 53, 0.2) !important;
    background: transparent !important;
    color: #ff6b35 !important;
    padding: 0.75rem 1.5rem !important;
}

button:hover {
    background: rgba(255, 107, 53, 0.1) !important;
    border-color: rgba(255, 107, 53, 0.4) !important;
}

/* Inputs premium */
input, textarea, select {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 107, 53, 0.2) !important;
    color: #f0f2f5 !important;
    border-radius: 0.8rem !important;
    padding: 0.75rem 1rem !important;
    font-weight: 500 !important;
}

input:focus, textarea:focus, select:focus {
    border-color: #ff6b35 !important;
    background: rgba(255, 107, 53, 0.1) !important;
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.15) !important;
}

/* Separateurs modern */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(255, 107, 53, 0.3), transparent) !important;
    margin: 1.5rem 0 !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 107, 53, 0.15) !important;
    border-radius: 0.8rem !important;
    background: rgba(255, 107, 53, 0.05) !important;
}

/* Progress indicator */
.progress-bar {
    height: 3px !important;
    background: linear-gradient(90deg, #ff6b35, #ff8c42) !important;
    border-radius: 2px !important;
}
</style>
""", unsafe_allow_html=True)

# Initialisation session
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None
if 'proposals' not in st.session_state:
    st.session_state.proposals = None
if 'renaming_map' not in st.session_state:
    st.session_state.renaming_map = {}
if 'cleaned_df' not in st.session_state:
    st.session_state.cleaned_df = None
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'graphs' not in st.session_state:
    st.session_state.graphs = []
if 'question_graphs' not in st.session_state:
    st.session_state.question_graphs = []
if 'result_files' not in st.session_state:
    st.session_state.result_files = {}
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = None
if 'csv_bytes' not in st.session_state:
    st.session_state.csv_bytes = None
if 'current_file_path' not in st.session_state:
    st.session_state.current_file_path = None
if 'uploaded_temp_path' not in st.session_state:
    st.session_state.uploaded_temp_path = None
if 'uploaded_signature' not in st.session_state:
    st.session_state.uploaded_signature = None


def get_api_key():
    """Recupere la cle API Groq."""
    # Methode 1: Variable d'environnement
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        return api_key
    
    # Methode 2: Secrets Streamlit
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
        if api_key:
            return api_key
    except:
        pass
    
    # Methode 3: Input utilisateur
    return None


def validate_data_file(file_obj, max_size_mb=200):
    """Valide un fichier de données avant le traitement."""
    if file_obj is None:
        return False, "Aucun fichier sélectionné"
    
    # Formats acceptés
    supported_formats = ('.csv', '.xlsx', '.xls', '.json', '.parquet', '.tsv', '.txt')
    
    # Vérifier l'extension
    file_lower = file_obj.name.lower()
    if not any(file_lower.endswith(fmt) for fmt in supported_formats):
        formats_str = ", ".join(supported_formats)
        return False, f"Format invalide - formats acceptés: {formats_str}"
    
    # Vérifier la taille
    file_size_mb = len(file_obj.getvalue()) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False, f"Fichier trop volumineux ({file_size_mb:.1f} MB > {max_size_mb} MB)"
    
    # Vérifier que le fichier n'est pas vide
    if file_size_mb < 0.001:  # Moins de 1 KB
        return False, "Fichier vide"
    
    return True, "OK"


def load_data_file(file_obj):
    """Charge un fichier de données dans un DataFrame pandas."""
    import pandas as pd
    import json
    from io import BytesIO
    
    file_lower = file_obj.name.lower()
    
    try:
        if file_lower.endswith('.csv'):
            return pd.read_csv(file_obj)
        elif file_lower.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_obj)
        elif file_lower.endswith('.json'):
            return pd.read_json(file_obj)
        elif file_lower.endswith('.parquet'):
            return pd.read_parquet(file_obj)
        elif file_lower.endswith(('.tsv', '.txt')):
            # TSV ou TXT avec délimiteur auto-détecté
            return pd.read_csv(file_obj, sep='\t')
    except Exception as e:
        return None, f"Erreur lors de la lecture: {str(e)}"
    
    return None, "Format non reconnu"


def show_navigation_buttons(current_step, total_steps):
    """Affiche les boutons Précédent et Suivant."""
    step_descriptions = [
        "Chargement",
        "Vérification",
        "Nettoyage",
        "Export"
    ]
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_step > 0:
            if st.button("Précédent", use_container_width=True):
                st.session_state.current_tab = current_step - 1
                st.rerun()
        else:
            st.empty()
    
    with col2:
        progress_pct = int((current_step + 1) / total_steps * 100)
        progress_text = f"Étape {current_step + 1}/{total_steps} - {step_descriptions[current_step]} ({progress_pct}%)"
        st.markdown(f"<div style='text-align: center; padding: 0.8rem; color: #cbd5e0; background: rgba(255,107,53,0.08); border-radius: 0.6rem;'>{progress_text}</div>", unsafe_allow_html=True)
    
    with col3:
        if current_step < total_steps - 1:
            if st.button("Suivant", use_container_width=True):
                st.session_state.current_tab = current_step + 1
                st.rerun()
        else:
            st.empty()


def main():
    import streamlit as st  # Patch de contournement pour UnboundLocalError


    st.title("Analyse et Nettoyage CSV")
    st.markdown("Chargez, validez et transformez vos données CSV.")
    
    st.markdown("")

    # --- RÉSUMÉ DYNAMIQUE ---
    if st.session_state.get('analyzer') and getattr(st.session_state.analyzer, 'df', None) is not None:
        df = st.session_state.analyzer.df
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Lignes", f"{len(df):,}")
        with col2:
            st.metric("Colonnes", len(df.columns))
        with col3:
            st.metric("Taille", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
        with col4:
            st.metric("Valeurs NULL", f"{df.isna().sum().sum():,}")
    else:
        st.markdown("""
        <div style='background: rgba(255, 107, 53, 0.1); border: 1px solid rgba(255, 107, 53, 0.3); 
                    border-radius: 0.8rem; padding: 1.5rem 2rem; text-align: center; color: #e2e8f0;'>
        <p style='font-size: 1.1rem; margin: 0;'><strong>Aucun fichier chargé</strong></p>
        <p style='font-size: 0.9rem; margin-top: 0.5rem; color: #cbd5e0;'>Commencez par charger un fichier de données</p>
        </div>
        """, unsafe_allow_html=True)
    
    # SIDEBAR
    with st.sidebar:
        st.markdown("""
        <div style='background: rgba(255, 107, 53, 0.08); border: 1px solid rgba(255, 107, 53, 0.2); border-radius: 0.8rem; padding: 1rem; margin-bottom: 1.5rem;'>
            <h2 style='margin: 0 0 1rem 0; color: #ff6b35; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;'>Configuration</h2>
            <p style='margin: 0; color: #cbd5e0; font-size: 0.85rem; line-height: 1.6;'>Données max: <b>200 MB</b><br/>Formats: <b>CSV, Excel, JSON, Parquet</b><br/>Encodage: <b>UTF-8</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        api_key = get_api_key()
        if not api_key:
            st.warning("Clé API Groq non trouvée")
            api_key_input = st.text_input(
                "Entrez votre clé API Groq:",
                type="password",
                help="https://console.groq.com",
                label_visibility="collapsed"
            )
            if api_key_input:
                api_key = api_key_input
        else:
            st.markdown("<p style='color: #4ade80; font-size: 0.85rem; font-weight: 600; margin: 0;'>✓ Clé API détectée</p>", unsafe_allow_html=True)





    # ONGLETS UTILISANT LA SESSION STATE
    if st.session_state.current_tab == 0:
        # =======================
        # TAB 1: CHARGEMENT
        # =======================
        st.markdown("<h1 style='color: #ffffff; border-bottom: 2px solid #ff6b35; padding-bottom: 1rem; margin-bottom: 2rem;'>① Charger vos données</h1>", unsafe_allow_html=True)
        
        st.markdown("""
        Importez votre fichier CSV ou spécifiez le chemin vers un fichier existant.
        """)
        
        with st.expander("Formats acceptés", expanded=False):
            st.markdown("""
            - **Formats**: CSV, Excel (.xlsx/.xls), JSON, Parquet, TSV/TXT
            - **Encodage**: UTF-8 recommandé
            - **Taille max**: 200 MB
            - **Première ligne**: En-têtes de colonnes (obligatoire)
            """)
        
        st.markdown("---")
        
        col1, col2 = st.columns([1.2, 1.8])
        
        with col1:
            st.subheader("Source des données")
            
            upload_method = st.radio(
                "Selectionner la source:",
                ["Upload direct", "Chemin fichier"],
                label_visibility="collapsed"
            )
            
            if upload_method == "Upload direct":
                uploaded_file = st.file_uploader(
                    "",
                    type=['csv'],
                    accept_multiple_files=False,
                    label_visibility="collapsed"
                )
                
                if uploaded_file:
                    # Valider le fichier d'abord
                    is_valid, message = validate_data_file(uploaded_file, max_size_mb=200)
                    
                    if not is_valid:
                        st.error(f"Fichier invalide: {message}")
                        file_path = None
                    else:
                        # Évite de réécrire le gros fichier à chaque rerun Streamlit.
                        upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
                        temp_path = f"temp_{uploaded_file.name}"
                        temp_exists = Path(temp_path).exists()

                        if (
                            st.session_state.uploaded_signature != upload_signature
                            or st.session_state.uploaded_temp_path != temp_path
                            or not temp_exists
                        ):
                            with st.spinner("Préparation du fichier uploadé..."):
                                with open(temp_path, 'wb') as f:
                                    f.write(uploaded_file.getbuffer())
                            st.session_state.uploaded_signature = upload_signature
                            st.session_state.uploaded_temp_path = temp_path
                            st.success(f"Fichier {uploaded_file.name} chargé")

                        file_path = st.session_state.uploaded_temp_path
                else:
                    file_path = None
            else:
                file_path = st.text_input(
                    "Chemin complet du fichier CSV:",
                    placeholder="C:\\Users\\...\\data.csv"
                )
        
        with col2:
            st.subheader("Aperçu des données")
            # L'aperçu sera affiché ici après le chargement
            preview_placeholder = st.empty()
        
        # Chargement
        if 'file_path' in locals() and file_path:
            # Si le CSV change, on repart d'un état propre pour éviter des résultats incohérents.
            if st.session_state.current_file_path != file_path:
                st.session_state.proposals = None
                st.session_state.renaming_map = {}
                st.session_state.cleaned_df = None
                st.session_state.questions = []
                st.session_state.graphs = []
                st.session_state.question_graphs = []
                st.session_state.result_files = {}
                st.session_state.output_dir = None
                st.session_state.csv_bytes = None
                st.session_state.current_file_path = file_path

            try:
                analyzer_ready = (
                    st.session_state.analyzer is not None
                    and getattr(st.session_state.analyzer, 'df', None) is not None
                    and str(getattr(st.session_state.analyzer, 'input_path', '')) == str(Path(file_path))
                )

                if not analyzer_ready:
                    with st.spinner("Chargement du CSV..."):
                        analyzer = CSVAnalyzer(
                            file_path,
                            api_key=api_key
                        )
                        if analyzer.load_data():
                            st.session_state.analyzer = analyzer
                        else:
                            st.session_state.analyzer = None

                if st.session_state.analyzer is not None and getattr(st.session_state.analyzer, 'df', None) is not None:
                    # Affichage de l'aperçu dans le placeholder de col2
                    with preview_placeholder.container():
                        st.dataframe(st.session_state.analyzer.df.head(5), use_container_width=True, height=200)
                    
                    # Métriques en une ligne
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Lignes", len(st.session_state.analyzer.df))
                    with col2:
                        st.metric("Colonnes", len(st.session_state.analyzer.df.columns))
                    with col3:
                        st.metric("Taille", f"{st.session_state.analyzer.df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
                    with col4:
                        st.metric("Valeurs NULL", f"{st.session_state.analyzer.df.isna().sum().sum()}")

                    if len(st.session_state.analyzer.df) > 300000:
                        st.warning("CSV volumineux détecté: le traitement peut être long. Les graphiques seront optimisés automatiquement.")
                    
                    # Bouton analyse
                if st.button("Analyser maintenant", use_container_width=True, type="primary"):
                        with st.spinner("Analyse en cours..."):
                            try:
                                st.session_state.proposals = st.session_state.analyzer.analyze_columns()
                                st.session_state.renaming_map = st.session_state.analyzer.renaming_map
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.success(f"Analyse complétée: {len(st.session_state.proposals)} colonnes")
                                with col2:
                                    st.info("Continuez vers l'onglet 'Vérifier'")
                            except ValueError as e:
                                st.error(f"Erreur validation: {str(e)}")
                            except TimeoutError:
                                st.error("L'analyse a dépassé le temps limite. Réessayez avec un fichier plus petit.")
                            except Exception as e:
                                st.error(f"Erreur d'analyse: {type(e).__name__} - {str(e)}")
                
            except FileNotFoundError:
                st.error(f"Fichier introuvable: {file_path}")
            except pd.errors.ParserError as e:
                st.error(f"Erreur de parsing CSV: Le fichier semble corrompu ou mal formaté")
            except Exception as e:
                st.error(f"Erreur inattendue: {type(e).__name__}")
        
        st.markdown("---")
        show_navigation_buttons(0, 4)


    # =======================
    # TAB 2: PROPOSITIONS
    # =======================
    elif st.session_state.current_tab == 1:
        st.markdown("<h1 style='color: #ffffff; border-bottom: 2px solid #ff6b35; padding-bottom: 1rem; margin-bottom: 2rem;'>② Vérifier l'analyse</h1>", unsafe_allow_html=True)
        
        with st.expander("Comment ça marche", expanded=False):
            st.markdown("""
            - **Renommer**: Donnez des noms plus explicites aux colonnes
            - **Type de données**: Spécifiez text, number, category, date ou id
            - **Validation**: Vérifiez avant de continuer
            """)
        
        st.markdown("---")
        
        if st.session_state.analyzer is None:
            st.info("Chargez d'abord un fichier CSV dans l'onglet précédent")
        else:
            if not st.session_state.proposals:
                st.warning("Lancez l'analyse en cliquant sur le bouton ci-dessus")
            else:
                st.markdown("Détection automatique des colonnes")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Colonnes", len(st.session_state.proposals))
                with col2:
                    avg_confidence = np.mean([
                        p.get('confidence', 0.5)
                        for p in st.session_state.proposals.values()
                    ])
                    st.metric("Confiance moyenne", f"{avg_confidence*100:.0f}%")
                with col3:
                    types_count = len(set(
                        p.get('data_type', 'text')
                        for p in st.session_state.proposals.values()
                    ))
                    st.metric("Types detectes", types_count)
                
                # Tableau des propositions
                st.subheader("Résumé d'analyse")
                
                proposal_data = []
                for col_orig, proposal in st.session_state.proposals.items():
                    proposal_data.append({
                        'Colonne': col_orig,
                        'Nom propose': proposal.get('proposed_name', col_orig),
                        'Type': proposal.get('data_type', 'text'),
                        'Confiance': f"{proposal.get('confidence', 0.5)*100:.0f}%",
                        'Anomalies': len(proposal.get('anomalies', []))
                    })
                
                st.dataframe(pd.DataFrame(proposal_data), use_container_width=True)
                
                # Editeur de mapping - Combiné Rename + Type
                st.subheader("Personnaliser les colonnes")
                
                for idx, (col_orig, proposal) in enumerate(st.session_state.proposals.items()):
                    col1, col2, col3 = st.columns([1, 1.5, 1.5])
                    
                    with col1:
                        st.markdown(f"**{col_orig}**")
                    
                    with col2:
                        new_name = st.text_input(
                            "Nouveau nom",
                            value=proposal.get('proposed_name', col_orig),
                            key=f"rename_{col_orig}",
                            help="Renommer cette colonne"
                        )
                        st.session_state.renaming_map[col_orig] = new_name
                    
                    with col3:
                        current_type = st.session_state.proposals[col_orig].get('data_type', 'text')
                        new_type = st.selectbox(
                            "Type",
                            ['text', 'number', 'category', 'date', 'id'],
                            index=['text', 'number', 'category', 'date', 'id'].index(current_type),
                            key=f"type_{col_orig}",
                            help="Définir le type de données"
                        )
                        st.session_state.proposals[col_orig]['data_type'] = new_type
                    
                    st.markdown("---")
                
                # Bouton valider
                if st.button("Valider et continuer", use_container_width=True, type="primary"):
                    st.success("Analyse validée avec succès")
                    st.info("Rendez-vous à l'onglet 'Nettoyer' pour générer les résultats")
        
        st.markdown("---")
        show_navigation_buttons(1, 4)

    # =======================
    # TAB 3: NETTOYAGE
    # =======================
    elif st.session_state.current_tab == 2:
        st.markdown("<h1 style='color: #ffffff; border-bottom: 2px solid #ff6b35; padding-bottom: 1rem; margin-bottom: 2rem;'>③ Nettoyer et exporter</h1>", unsafe_allow_html=True)
        
        with st.expander("Options de nettoyage", expanded=False):
            st.markdown("""
            - **Détection outliers**: Identifie les valeurs aberrantes
            - **Générer graphiques**: Crée des visualisations (peut être lent sur gros fichiers)
            - **Données et rapport**: Exporte en format CSV et HTML
            """)
        
        st.markdown("---")
        
        if st.session_state.analyzer is None:
            st.info("Commencez par charger un CSV")
        elif not st.session_state.proposals:
            st.info("Validez d'abord les propositions")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Donnees originales")
                st.dataframe(st.session_state.analyzer.df.head(5), use_container_width=True)
            
            with col2:
                st.subheader("Statistiques")
                st.metric("Lignes", len(st.session_state.analyzer.df))
                if st.session_state.analyzer is None:
                    st.info("Commencez par charger un CSV")
                elif not st.session_state.proposals:
                    st.info("Validez d'abord les propositions")
                else:
                    # --- BARRE DE RECHERCHE CONTEXTE ---
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.subheader("Contexte métier (optionnel)")
                    contexte_metier = st.text_input("Décrivez le contexte métier ou la problématique à analyser (ex: accidents, ventes, satisfaction client, etc.)", key="contexte_metier")
                    st.markdown("<hr>", unsafe_allow_html=True)

                    # Options nettoyage
                    is_very_large_dataset = len(st.session_state.analyzer.df) > 300000
                    col1, col2 = st.columns(2)
                    with col1:
                        detect_outliers = st.checkbox(
                            "Détecter les outliers (methode IQR)",
                            value=True,
                            help="Identifie les valeurs aberrantes"
                        )
                    with col2:
                        generate_graphs = st.checkbox(
                            "Générer graphiques",
                            value=not is_very_large_dataset,
                            help="Crée visualisations en Plotly (désactivé par défaut pour très gros CSV)"
                        )

                    if is_very_large_dataset:
                        st.info("Mode gros volume: privilégiez un premier test sans graphiques, puis activez-les si besoin.")

                    # Bouton nettoyage
                    if st.button("Nettoyer les données", use_container_width=True, type="primary"):
                        with st.spinner("Nettoyage en cours..."):
                            st.session_state.analyzer.clean_data()
                            st.session_state.cleaned_df = st.session_state.analyzer.cleaned_df
                            # Génération des questions et du plan stratégique avec contexte métier
                            blueprints = st.session_state.analyzer.generate_strategic_questions_and_graphs(contexte_metier)
                            st.session_state.analyzer.questions = blueprints
                            st.session_state.questions = blueprints
                            output_dir = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            st.session_state.output_dir = output_dir
                            if generate_graphs:
                                graph_gen = GraphicsGenerator(st.session_state.cleaned_df, output_dir)
                                graph_gen.generate_all_graphs()
                                st.session_state.graphs = graph_gen.generated_graphs
                            else:
                                st.session_state.graphs = []
                            st.success("Nettoyage terminé et analyses générées !")
                            st.markdown("### Données nettoyées")
                            st.dataframe(st.session_state.cleaned_df.head(5), use_container_width=True)

                            # --- TABLEAU DE BORD STRATÉGIQUE ---
                            question_graphs = []
                            if generate_graphs and hasattr(st.session_state, 'questions'):
                                st.markdown("---")
                                st.markdown("<div style='text-align: center;'><h3 style='color: #2c3e50; margin: 0;'>Tableau de Bord Stratégique</h3></div>", unsafe_allow_html=True)
                                questions = st.session_state.questions or []
                                if not questions:
                                    st.warning("Aucune question pertinente détectée automatiquement pour ce CSV. Affichage des graphiques automatiques de secours.")
                                    auto_graphs = st.session_state.graphs or []
                                    if auto_graphs:
                                        import streamlit.components.v1 as components
                                        for graph_filename in auto_graphs[:6]:
                                            full_path = Path(st.session_state.output_dir) / graph_filename
                                            if full_path.exists():
                                                with open(full_path, 'r', encoding='utf-8') as f:
                                                    st.markdown("""
                                                        <div style='width: 100%; display: flex; justify-content: center; align-items: center; margin: 24px 0;'>
                                                            <div style='background: #fff; border: 1.5px solid #e0e7ef; border-radius: 12px; box-shadow: 0 2px 8px #e0e7ef55; padding: 12px 18px; width: 95%; max-width: 900px;'>
                                                    """, unsafe_allow_html=True)
                                                    components.html(f.read(), height=550, scrolling=False)
                                                    st.markdown("""</div></div>""", unsafe_allow_html=True)
                                            else:
                                                st.warning(f"Graphique non généré ou manquant : {full_path}")
                                else:
                                    graph_gen = GraphicsGenerator(st.session_state.cleaned_df, st.session_state.output_dir)
                                    for i, q in enumerate(questions[:10]):
                                        st.markdown("<div style='margin: 2em auto 0 auto; width: 95%; max-width: 900px;'></div>", unsafe_allow_html=True)
                                        st.markdown(f"<b>Question :</b> {q.get('question', q.get('text', 'Question stratégique'))}", unsafe_allow_html=True)
                                        if q.get('utilite') or q.get('utility'):
                                            st.markdown(f"<b>Utilité :</b> {q.get('utilite', q.get('utility', ''))}", unsafe_allow_html=True)
                                        graph_filename = graph_gen.generate_graph_for_question(
                                            q.get('question', ''),
                                            contexte=contexte_metier,
                                            colonnes=q.get('colonnes', []),
                                            type_graphique=q.get('type_graphique', None)
                                        )
                                        question_graphs.append(graph_filename)
                                        if graph_filename:
                                            full_path = Path(st.session_state.output_dir) / graph_filename
                                            if full_path.exists():
                                                with open(full_path, 'r', encoding='utf-8') as f:
                                                    import streamlit.components.v1 as components
                                                    st.markdown("""
                                                        <div style='width: 100%; display: flex; justify-content: center; align-items: center; margin: 24px 0;'>
                                                            <div style='background: #fff; border: 1.5px solid #e0e7ef; border-radius: 12px; box-shadow: 0 2px 8px #e0e7ef55; padding: 12px 18px; width: 95%; max-width: 900px;'>
                                                    """, unsafe_allow_html=True)
                                                    components.html(f.read(), height=550, scrolling=False)
                                                    st.markdown("""</div></div>""", unsafe_allow_html=True)
                                            else:
                                                st.warning(f"Graphique non généré ou manquant : {full_path}")
                                        else:
                                            st.warning("Graphique non généré ou manquant.")
                                        # Interprétation
                                        interpretation = graph_gen.get_graph_interpretation(graph_filename or "")
                                        st.markdown(f"<div style='background:#f9fafb;padding:1em;border-radius:0.5em;margin-bottom:1em;text-align:left;'><b>Interprétation :</b> {interpretation}</div>", unsafe_allow_html=True)
                                        st.markdown("<hr>", unsafe_allow_html=True)

                                # --- BOUTON NEXT ---
                                st.markdown("<div style='text-align:right;'><button onclick=\"window.location.hash='Rapport'\" style='background:#667eea;color:white;padding:0.7em 2em;border:none;border-radius:0.4em;font-size:1.1em;cursor:pointer;'>Next &rarr;</button></div>", unsafe_allow_html=True)

                            st.session_state.question_graphs = question_graphs

                            # Statistiques post-nettoyage
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Lignes", len(st.session_state.cleaned_df))
                            with col2:
                                st.metric("Null original", st.session_state.analyzer.df.isna().sum().sum())
                                st.metric("Null nettoyée", st.session_state.cleaned_df.isna().sum().sum())
                            with col3:
                                st.markdown("**Colonnes renommées :**")
                                for orig, new in st.session_state.renaming_map.items():
                                    st.text(f"  {orig} → {new}")
                        
                       # 1. SAUVEGARDE PHYSIQUE (Pour les archives dans le dossier output)
                        # 1. SAUVEGARDE PHYSIQUE (Pour les archives dans le dossier output)
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
                        csv_path = Path(output_dir) / "donnees_nettoyees.csv"
                        # On utilise st.session_state.cleaned_df au lieu de analyzer.cleaned_df
                        st.session_state.cleaned_df.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
                        
                        # 2. PRÉPARATION MÉMOIRE (Pour le bouton de téléchargement Streamlit)
                        csv_bytes = st.session_state.cleaned_df.to_csv(index=False, sep=';').encode('utf-8-sig')
                        
                        # Rapport HTML/PDF
                        rapport_gen = RapportGenerator(output_dir)
                        report_graphs = getattr(st.session_state, 'question_graphs', []) or getattr(st.session_state, 'graphs', [])
                        result_files = rapport_gen.generate_complete_report(
                            df=st.session_state.cleaned_df,
                            renaming_map=st.session_state.renaming_map,
                            proposals=st.session_state.proposals,
                            questions=st.session_state.questions,
                            contexte_metier=contexte_metier,
                            graphs=report_graphs
                        )
                        
                        st.success("✓ Rapport genere!")
                        
                        # Sauvegarder dans session_state pour tab4
                        st.session_state.result_files = result_files
                        st.session_state.csv_bytes = csv_bytes
        
        st.markdown("---")
        show_navigation_buttons(2, 4)
    
    # =======================
    # TAB 4: RAPPORT & TELECHARGER
    # =======================
    elif st.session_state.current_tab == 3:
        st.markdown("<h1 style='color: #ffffff; border-bottom: 2px solid #ff6b35; padding-bottom: 1rem; margin-bottom: 2rem;'>④ Résultats et export</h1>", unsafe_allow_html=True)
        
        with st.expander("Fichiers disponibles", expanded=False):
            st.markdown("""
            - **CSV nettoyé**: Vos données transformées et validées
            - **Rapport HTML**: Visualisations et analyse complète
            - **Graphiques**: Visualisations individuelles en format HTML
            """)
        
        st.markdown("---")
        
        if not hasattr(st.session_state, 'result_files') or not st.session_state.result_files:
            st.info("Complétez d'abord l'étape 3 pour générer les résultats")
        else:
            st.success("Résultats prêts pour le téléchargement")
            
            # Downloads
            st.markdown("### Telecharger vos fichiers")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if hasattr(st.session_state, 'csv_bytes') and st.session_state.csv_bytes:
                    st.download_button(
                        label="Télécharger CSV",
                        data=st.session_state.csv_bytes,
                        file_name="donnees_nettoyees_excel.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if 'html' in st.session_state.result_files:
                    try:
                        with open(st.session_state.result_files['html'], 'rb') as f:
                            html_data = f.read()
                        st.download_button(
                            label="Télécharger HTML",
                            data=html_data,
                            file_name="rapport.html",
                            mime="text/html"
                        )
                    except Exception as e:
                        st.error(f"Erreur accès HTML: {e}")
            
            with col3:
                if 'pdf' in st.session_state.result_files:
                    try:
                        with open(st.session_state.result_files['pdf'], 'rb') as f:
                            pdf_data = f.read()
                        st.download_button(
                            label="Télécharger PDF",
                            data=pdf_data,
                            file_name="rapport.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Erreur accès PDF: {e}")
            
            if hasattr(st.session_state, 'output_dir'):
                st.info(f"Fichiers stockés dans: {st.session_state.output_dir}")
        
        st.markdown("---")
        show_navigation_buttons(3, 4)
    
    # FOOTER
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888; font-size: 0.9em;'>
    Analyse et Nettoyage CSV | Traitement sécurisé localement
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    # Ajouter cles API si necessaire
    if "GROQ_API_KEY" not in os.environ:
        # Charger depuis .streamlit/secrets.toml
        try:
            import toml
            secrets_path = Path(".streamlit/secrets.toml")
            if secrets_path.exists():
                secrets = toml.load(secrets_path)
                if "GROQ_API_KEY" in secrets:
                    os.environ["GROQ_API_KEY"] = secrets["GROQ_API_KEY"]
        except:
            pass
    
    main()
