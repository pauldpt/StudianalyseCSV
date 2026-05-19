"""
Module core d'analyse CSV - Logique métier indépendante de l'UI.
Réutilisable pour Streamlit, CLI, ou autre interface.
"""


# Chargement du .env tout en haut pour la clé API
import os
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from groq import Groq
from rapidfuzz import process as fuzz_process

 # Configuration
DEFAULT_MODEL = "openai/gpt-oss-safeguard-20b"
CONFIDENCE_THRESHOLD_AUTO = 0.7
CONFIDENCE_THRESHOLD_FIX_ALL = 0.5

KNOWN_CATEGORIES = {
    "statut": ["Terminé", "Abandonné", "En cours", "Inscrit"],
    "financeur": ["CPF", "Région", "France Travail", "OPCO", "Auto-financé"],
    "niveau": ["Débutant", "Intermédiaire", "Avancé", "Expert"]
}

# === THÈMES CONTEXTUELS PRÉDÉFINIS ===
CONTEXTE_THEMES = {
    "accidents": {
        "name": "Accidents routiers",
        "q1_utilite": "Identifier les facteurs de risque majeurs pour cibler les campagnes de prévention.",
        "q2_utilite": "Détecter les interactions entre facteurs (ex: accidents nocturnes en urbain) pour adapter les mesures.",
        "q3_utilite": "Identifier les configurations à haut risque pour concentrer les ressources de contrôle.",
        "q4_utilite": "Anticiper les pics d'accidents (ex: vacances) pour renforcer la prévention et les secours.",
        "q5_utilite": "Comparer les profils de risque pour stratifier les actions de sécurité."
    },
    "formation": {
        "name": "Formation & Apprentissage",
        "q1_utilite": "Cibler les relances pour éviter les abandons définitifs et sécuriser le financement.",
        "q2_utilite": "Intervenir rapidement sur les blocages techniques ou de motivation.",
        "q3_utilite": "Évaluer l'efficacité de la formation selon le profil d'apprenant.",
        "q4_utilite": "Identifier les modules qui marchent bien et les axes d'amélioration.",
        "q5_utilite": "Comparer les résultats par profil d'apprenant pour optimiser l'accompagnement pédagogique."
    },
    "ventes": {
        "name": "Ventes & Revenue",
        "q1_utilite": "Identifier les segments les plus lucratifs pour maximiser le revenue.",
        "q2_utilite": "Analyser les interactions client-produit pour optimiser les bundles de vente.",
        "q3_utilite": "Détecter les sous-segments à fort potentiel pour ciblage marketing.",
        "q4_utilite": "Repérer les tendances saisonnières pour ajuster la production et le stock.",
        "q5_utilite": "Comparer les performances par segment pour réallouer les ressources commerciales."
    },
    "rh": {
        "name": "Ressources Humaines",
        "q1_utilite": "Identifier les caractéristiques des salariés à plus haut risque de turnover.",
        "q2_utilite": "Analyser comment les interactions (département x niveau) affectent l'engagement et la rétention.",
        "q3_utilite": "Détecter les profils critiques à surveiller pour réduire les pertes de talents.",
        "q4_utilite": "Anticiper les pics de départs (ex: post-vacances) pour renforcer la rétention.",
        "q5_utilite": "Comparer les conditions par équipe pour identifier les meilleures pratiques."
    },
    "sante": {
        "name": "Santé & Médical",
        "q1_utilite": "Identifier les conditions les plus fréquentes pour prioriser les ressources médicales.",
        "q2_utilite": "Analyser l'interaction entre facteurs (ex: âge x comorbidités) pour stratifier le risque.",
        "q3_utilite": "Détecter les profils à haut risque pour des interventions préventives ciblées.",
        "q4_utilite": "Anticiper les pics de demande saisonniers pour optimiser les effectifs.",
        "q5_utilite": "Comparer les résultats par type de patient pour améliorer les protocoles de traitement."
    },
    "logistique": {
        "name": "Logistique & Supply Chain",
        "q1_utilite": "Identifier les routes/zones les plus critiques pour optimiser les ressources.",
        "q2_utilite": "Analyser les interactions (véhicule x condition) pour prédire les retards.",
        "q3_utilite": "Détecter les points faibles du réseau pour minimiser les ruptures.",
        "q4_utilite": "Anticiper les pics de demande saisonnière pour ajuster la capacité.",
        "q5_utilite": "Comparer les performances par région pour identifier les meilleures pratiques."
    },
    "generic": {  # Défaut
        "name": "Analyse générique",
        "q1_utilite": "Comprendre la distribution du facteur principal pour identifier les priorités.",
        "q2_utilite": "Analyser les interactions entre facteurs pour détecter les patterns.",
        "q3_utilite": "Identifier les sous-groupes significatifs pour des analyses ciblées.",
        "q4_utilite": "Observer les tendances temporelles pour anticiper les changements.",
        "q5_utilite": "Comparer les profils des sous-groupes pour prendre des décisions stratégiques."
    }
}

CUSTOM_CORRECTIONS = {}

def load_custom_corrections():
    """Charge les corrections personnalisées depuis corrections.json."""
    global CUSTOM_CORRECTIONS
    try:
        with open('corrections.json', 'r', encoding='utf-8') as f:
            CUSTOM_CORRECTIONS = json.load(f)
    except FileNotFoundError:
        CUSTOM_CORRECTIONS = {}

def clean_number(value) -> Optional[float]:
    """Nettoie et convertit une valeur en nombre."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return None
    return None

def clean_date(date_str) -> Optional[str]:
    """Nettoie et convertit une chaîne en date ISO."""
    if date_str is None or (isinstance(date_str, float) and np.isnan(date_str)):
        return None
    date_str = str(date_str).strip()
    formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d', '%d.%m.%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None

def normalize_category(s, col_name=None, strict_mode=True) -> Optional[str]:
    """Normalise une chaîne catégorielles."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip()
    if not s:
        return None
    if col_name and col_name in CUSTOM_CORRECTIONS:
        for orig, fixed in CUSTOM_CORRECTIONS[col_name].items():
            if s.lower() == orig.lower():
                return fixed
    if strict_mode:
        import unicodedata
        s = ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))
    return s.lower().strip()

class GroqClient:
    """Client API Groq robuste."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.model = model or DEFAULT_MODEL
        self.client = Groq(api_key=self.api_key)

    def chat(self, prompt: str) -> str:
        """Appel IA."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API error: {e}")

class ColumnAnalyzer:
    """Analyste de colonnes avec IA optionnelle."""
    def __init__(self, api_client: GroqClient):
        self.api_client = api_client

    def analyze_all_columns(self, columns_info: List[Dict]) -> Dict:
        """Analyse complète des colonnes."""
        result = {}
        has_jma = any(c['name'].lower() in ['jour', 'mois', 'an'] for c in columns_info)

        for col in columns_info:
            info = col.copy()
            info['proposed_name'] = self._smart_rename(info['name'])
            info['data_type'] = self._guess_data_type(info)
            info['confidence'] = 0.8
            result[col['name']] = info

        return result

    def _smart_rename(self, col_name: str) -> str:
        """Renomme intelligemment une colonne."""
        import unicodedata
        col = col_name.strip()
        col = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', col)
        col = ''.join((c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn'))
        col = col.lower()
        col = re.sub(r'[\s\-]+', '_', col)
        col = re.sub(r'[^a-z0-9_]', '', col)
        
        mapping = [
            (r'^(jour|mois|an|annee|année|date|year|month|day)$', r'\1'),
            (r'^(hrmn|heure|hr|mn)$', 'heure_minute'),
            (r'^(montant|prix|cost|revenue|valeur)$', 'montant'),
            (r'^(nb|nombre|qty|quantite)$', 'nombre'),
            (r'^(id|identifiant|code)$', 'identifiant'),
            (r'^(lat|latitude)$', 'latitude'),
            (r'^(long|longitude)$', 'longitude'),
            (r'^(dep|departement)$', 'departement'),
            (r'^(com|commune|ville)$', 'commune'),
            (r'^(agg|agglomeration)$', 'agglomeration'),
            (r'^(atm|atmosphere)$', 'atmosphere'),
            (r'^(col|collision)$', 'collision'),
        ]
        
        for pattern, repl in mapping:
            if re.match(pattern, col):
                col = re.sub(pattern, repl, col)
                break
        
        col = re.sub(r'__+', '_', col)
        col = col.strip('_')
        return col

    def _guess_data_type(self, col_info: Dict) -> str:
        """Devine le type d'une colonne."""
        col_name = col_info['name'].lower()
        samples = col_info.get('samples', [])
        nunique = col_info.get('nunique', 0)

        if any(kw in col_name for kw in ['date', 'jour', 'mois', 'année', 'year', 'month', 'created']):
            return 'date'

        if samples:
            numeric_count = 0
            for val in samples:
                try:
                    if isinstance(val, str) and len(val) == 5 and val.isdigit():
                        continue
                    float(val)
                    numeric_count += 1
                except (ValueError, TypeError):
                    pass
            if numeric_count >= len(samples) * 0.8:
                return 'number'

        if any(kw in col_name for kw in ['prix', 'montant', 'cost', 'revenue', 'qty', 'quantity']):
            return 'number'

        if nunique < 15:
            return 'category'
        if nunique > len(samples) * 0.7:
            return 'text'

        return 'text'

    def _verify_actual_type(self, col_name: str, col_info: Dict) -> Optional[str]:
        """Vérifie le type réel par inspection."""
        samples = col_info.get('samples', [])
        nunique = col_info.get('nunique', 0)
        
        if not samples:
            return None

        numeric_count = sum(1 for v in samples if clean_number(v) is not None)
        if numeric_count >= len(samples) * 0.8:
            return 'number'

        date_count = sum(1 for v in samples if clean_date(str(v)) is not None)
        if date_count >= len(samples) * 0.6:
            return 'date'

        if nunique < 15:
            return 'category'

        return None
        if not result or any(_has_no_proposed_name(v) for v in result.values()):
            print("[AVERTISSEMENT] IA n'a pas retourné de JSON valide ou mapping incomplet. Mapping par défaut intelligent activé.")
            result = {}
            for col in columns_info:
                cname = col['name']
                # Correction spéciale pour jour/mois/an : on garde les colonnes d'origine avec leur nom et type 'number'
                if has_jma and cname.lower() in ['jour', 'mois', 'an']:
                    result[cname] = {
                        'proposed_name': cname.lower(),
                        'data_type': 'number',
                        'confidence': 0.95
                    }
                else:
                    result[cname] = {
                        'proposed_name': self._smart_rename(cname),
                        'data_type': self._guess_data_type(col),
                        'confidence': 0.3
                    }

        # Forcer la traduction snake_case sur tous les noms proposés
        for k, v in result.items():
            if 'proposed_name' in v:
                v['proposed_name'] = self._smart_rename(v['proposed_name'])

        return result
    
    def _smart_rename(self, col_name: str) -> str:
        """
        Renomme intelligemment une colonne selon des patterns robustes :
        - Nettoie accents, majuscules, caractères spéciaux
        - Traduit les abréviations et mots-clés fréquents (date, heure, montant, etc.)
        - Génère un nom snake_case métier lisible même pour colonnes inconnues
        """
        import unicodedata
        # 1. Nettoyage général
        col = col_name.strip()
        # Remplacer camelCase par snake_case
        col = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', col)
        # Enlever accents
        col = ''.join((c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn'))
        # Tout en minuscules
        col = col.lower()
        # Remplacer espaces et tirets par underscore
        col = re.sub(r'[\s\-]+', '_', col)
        # Supprimer caractères non alphanumériques sauf underscore
        col = re.sub(r'[^a-z0-9_]', '', col)
        # 2. Mapping d'abréviations et mots-clés fréquents (élargie)
        mapping = [
            (r'^jour$', 'date_jour'),
            (r'^mois$', 'date_mois'),
            (r'^an$', 'date_an'),
            (r'^(dt|date|annee|year)$', 'date'),
            (r'^(hrmn|heure|heureminute|heure_minute|hr|mn|min|minute)$', 'heure_minute'),
            (r'^(montant|mnt|amount|total|prix|cost|revenue|valeur|value)$', 'montant'),
            (r'^(nb|nombre|qty|quantite|quantity)$', 'nombre'),
            (r'^(cat|categorie|category)$', 'categorie'),
            (r'^(desc|description|texte|text)$', 'description'),
            (r'^(id|identifiant|code|pk|fk|row)$', 'identifiant'),
            (r'^(lat|latitude)$', 'latitude'),
            (r'^(long|longitude)$', 'longitude'),
            (r'^(dep|departement)$', 'departement'),
            (r'^(com|commune|ville|city)$', 'commune'),
            (r'^(agg|agglomeration)$', 'agglomeration'),
            (r'^(atm|atmosphere)$', 'atmosphere'),
            (r'^(col|collision)$', 'collision'),
            (r'^(adr|adresse|address)$', 'adresse'),
            (r'^(lum|lumiere|luminosite|light|brightness)$', 'luminosite'),
            (r'^(vit|vitesse|speed)$', 'vitesse'),
            (r'^(meteo|weather|cond|condition)$', 'meteo'),
            (r'^(grav|gravite|severity)$', 'gravite'),
            (r'^(bless|blesse|injury|injured)$', 'blesses'),
            (r'^(mort|mortality|dead|deaths)$', 'deces'),
            (r'^(sexe|gender|sex|homme|femme|male|female)$', 'sexe'),
            (r'^(age|years_old|ans)$', 'age'),
            (r'^(nb_vehicles|nb_cars|vehicles|cars)$', 'nombre_vehicules'),
        ]
        # Si la colonne est un mot-clé exact ou commence par un mot-clé, on remplace
        for pattern, repl in mapping:
            if re.match(pattern, col):
                col = re.sub(pattern, repl, col)
                break
        # 3. Nettoyage final : pas de double underscore, pas de _ en début/fin
        col = re.sub(r'__+', '_', col)
        col = col.strip('_')
        return col
    
    def _guess_data_type(self, col_info: Dict) -> str:
        """Devine le type d'une colonne selon ses caractéristiques RÉELLES (robuste, jamais code postal en nombre, gestion avancée des dates, fallback IA)."""
        col_name = col_info['name'].lower()
        samples = col_info.get('samples', [])
        nunique = col_info.get('nunique', 0)

        # Jamais code postal en nombre !
        if 'code postal' in col_name or 'postal code' in col_name or 'cp' == col_name.strip():
            return 'category'

        # === PRIORITÉ 1: Détection par OBSERVATIONS RÉELLES ===
        # 1a. Détection avancée des dates (formats, valeurs, noms)
        date_keywords = ['date', 'jour', 'mois', 'année', 'annee', 'year', 'month', 'day', 'created', 'updated', 'timestamp', 'datetime']
        if any(kw in col_name for kw in date_keywords):
            return 'date'
        if samples:
            date_count = 0
            for val in samples:
                val_str = str(val).strip()
                # Patterns de date courants (fr, en, iso)
                if any(sep in val_str for sep in ['/', '-', '.', ' ']) and 4 <= len(val_str) <= 19:
                    import re
                    if re.match(r'^(\d{1,4}[-/\. ]\d{1,2}[-/\. ]\d{1,4})$', val_str) or re.match(r'^(\d{4}-\d{2}-\d{2})', val_str):
                        date_count += 1
            if date_count >= len(samples) * 0.6:
                return 'date'

        # 1b. Détection avancée des nombres (hors code postal)
        if samples:
            numeric_count = 0
            for val in samples:
                try:
                    # Exclure les codes postaux déguisés en nombre (5 chiffres, pas de décimale)
                    if isinstance(val, str) and (len(val) == 5 and val.isdigit()):
                        continue
                    float(val)
                    numeric_count += 1
                except (ValueError, TypeError):
                    pass
            if numeric_count >= len(samples) * 0.8:
                return 'number'

        # === PRIORITÉ 2: Détection par MOTS-CLÉS (plus robuste) ===
        if any(kw in col_name for kw in ['id', 'identifiant', 'numero', 'order id', 'customer id', 'pk', 'fk', 'row']):
            return 'id'
        if any(kw in col_name for kw in ['prix', 'montant', 'cost', 'revenue', 'qty', 'quantite', 'nombre', 'sales', 'profit', 'discount', 'quantity', 'amount', 'total', 'value']):
            return 'number'

        # === PRIORITÉ 3: Détection par STATISTIQUES ===
        if nunique < 15:
            return 'category'
        if nunique > len(samples) * 0.7:
            return 'text'

        # Par défaut
        return 'text'



class CSVAnalyzer:
    # Colonnes à exclure pour les évolutions temporelles (pas de sens métier)
    forbidden_evolution = {'jour', 'mois', 'an', 'annee', 'année', 'date', 'hrmn', 'heure', 'time', 'timestamp'}
    """Analyseur principal de CSV."""
    def __init__(self, input_file: str, api_key: str = None, model: str = None):
        self.input_path = Path(input_file)
        if not self.input_path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {input_file}")
        self.model = model or DEFAULT_MODEL
        self.api_client = GroqClient(api_key, self.model)
        self.analyzer = ColumnAnalyzer(self.api_client)
        self.df = None
        self.proposals = {}
        self.renaming_map = {}
        self.column_types = {}
        self.cleaned_df = None
        self.questions = []
        self.anomalies_log = {}

    def load_data(self) -> bool:
        """Charge le fichier de données en detectant le format et l'encodage."""
        file_lower = str(self.input_path).lower()
        
        # Pour les fichiers non-CSV, utiliser pandas directement
        if file_lower.endswith('.xlsx') or file_lower.endswith('.xls'):
            try:
                self.df = pd.read_excel(self.input_path)
                print(f"[OK] Excel chargé : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                return True
            except Exception as e:
                print(f"[ERREUR] Excel : {e}")
                return False
        
        elif file_lower.endswith('.json'):
            try:
                self.df = pd.read_json(self.input_path)
                print(f"[OK] JSON chargé : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                return True
            except Exception as e:
                print(f"[ERREUR] JSON : {e}")
                return False
        
        elif file_lower.endswith('.parquet'):
            try:
                self.df = pd.read_parquet(self.input_path)
                print(f"[OK] Parquet chargé : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                return True
            except Exception as e:
                print(f"[ERREUR] Parquet : {e}")
                return False
        
        elif file_lower.endswith(('.tsv', '.txt')):
            try:
                self.df = pd.read_csv(self.input_path, sep='\t')
                print(f"[OK] TSV chargé : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                return True
            except Exception as e:
                print(f"[ERREUR] TSV : {e}")
                return False
        
        # Pour CSV, utiliser la logique d'auto-détection existante
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        separators = [',', ';', '\t', '|', ' ']
        
        for enc in encodings:
            try:
                with open(self.input_path, 'r', encoding=enc) as f:
                    first_line = f.readline().strip()
                
                best_sep = ','
                max_count = 0
                for sep in separators:
                    count = first_line.count(sep)
                    if count > max_count:
                        max_count = count
                        best_sep = sep
                
                if max_count == 0:
                    best_sep = ','
                
                self.df = pd.read_csv(self.input_path, encoding=enc, sep=best_sep)
                print(f"[OK] Charge : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                
                
                try:
                    if 'etat' in self.df.columns and 'note' in self.df.columns:
                        # On trouve les lignes où etat est vide et note contient des lettres
                        mask = self.df['etat'].isna() & self.df['note'].astype(str).str.contains(r'[A-Za-z]', na=False)
                        if mask.any():
                            self.df.loc[mask, 'etat'] = self.df.loc[mask, 'note']
                            self.df.loc[mask, 'note'] = np.nan
                except Exception as e:
                    print(f"[INFO] L'astuce de réalignement a été ignorée : {e}")
                # ------------------------------
                
                return True
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"[ERREUR] {e}")
                # On continue pour essayer un autre encodage
        
        print("[ERREUR] Impossible de lire le fichier.")
        return False

    def analyze_columns(self) -> Dict:
        """Analyse toutes les colonnes avec l'IA + validation forte."""
        columns_info = []
        for col in self.df.columns:
            sample = self.df[col].dropna().head(5).tolist()
            nunique = self.df[col].nunique()
            null_pct = (self.df[col].isna().sum() / len(self.df)) * 100
            columns_info.append({
                'name': col,
                'samples': sample,
                'nunique': nunique,
                'null_pct': null_pct
            })
        
        results = self.analyzer.analyze_all_columns(columns_info)
        
        # Assurer que tous les résultats ont des valeurs valides
        self.proposals = {}
        for col_info in columns_info:
            col_name = col_info['name']
            prop = results.get(col_name, {})
            
            # Fallback si la proposition est vide
            if not prop or not prop.get('proposed_name'):
                prop = {
                    'proposed_name': col_name,
                    'data_type': self.analyzer._guess_data_type(col_info),
                    'confidence': 0.0
                }
            
            # === VALIDATION FORTE: Vérifier le type contre les vraies données ===
            
            detected_type = prop.get('data_type', 'text')
            actual_type = self._verify_actual_type(col_name, col_info)
            
            # Si le type IA semble faux, utiliser le type réel
            if actual_type and actual_type != detected_type:
                try:
                    print(f"[CORRECTION] {col_name}: Type IA '{detected_type}' → Type réel '{actual_type}'", flush=True)
                except UnicodeEncodeError:
                    print(f"[CORRECTION] {col_name}: Type IA '{detected_type}' -> Type réel '{actual_type}'", flush=True)
                prop['data_type'] = actual_type
                prop['confidence'] = max(prop.get('confidence', 0), 0.6)  # Boost confiance
            
            # === FILTRAGE: EXCLURE LES COLONNES ID DU MAPPING ===
            if prop.get('data_type') == 'id':
                print(f"[EXCLU] {col_name}: Colonne ID exclue du mapping")
                self.column_types[col_name] = 'id'  # Garder pour info
                continue  # N'ajouter ni aux propositions ni au renaming_map
            
            self.proposals[col_name] = prop
            self.renaming_map[col_name] = prop.get('proposed_name', col_name)
            self.column_types[col_name] = prop.get('data_type', 'text')
        
        print(f"[OK] Mapping généré pour {len(self.renaming_map)} colonnes")
        print(f"[TYPES] {dict(self.column_types)}")
        return self.proposals
    
    def _verify_actual_type(self, col_name: str, col_info: Dict) -> Optional[str]:
        """Vérifie le type RÉEL basé sur les données du dataframe."""
        if col_name not in self.df.columns:
            return None
        
        col_data = self.df[col_name]
        
        # === Test 0: Est-ce un ID? (AVANT de tester les nombres!) ===
        col_name_lower = col_name.lower()
        if any(kw in col_name_lower for kw in ['id', 'identifiant', 'code', 'pk', 'fk', 'row']):
            # Vérifier que c'est une séquence unique (1,2,3,4...)
            non_null = col_data.dropna()
            nunique = non_null.nunique()
            total = len(non_null)
            
            # Si 95%+ de valeurs sont uniques → c'est un ID!
            if nunique >= total * 0.95:
                print(f"[ID DÉTECTÉ] {col_name}: {nunique}/{total} valeurs uniques = ID séquentiel")
                return 'id'
        
        # === Test 1: Est-ce un nombre? ===
        try:
            non_null = col_data.dropna()
            if len(non_null) > 0:
                numeric_count = 0
                for val in non_null.head(20):
                    try:
                        float(val)
                        numeric_count += 1
                    except (ValueError, TypeError):
                        pass
                
                if numeric_count >= len(non_null.head(20)) * 0.9:
                    return 'number'
        except:
            pass
        
        # === Test 2: Est-ce une date? ===
        try:
            non_null = col_data.dropna()
            if len(non_null) > 0:
                date_count = 0
                for val in non_null.head(10):
                    val_str = str(val).strip()
                    if any(sep in val_str for sep in ['/', '-', '.']) and len(val_str) <= 10:
                        import re
                        if re.match(r'^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$', val_str):
                            date_count += 1
                
                if date_count >= len(non_null.head(10)) * 0.7:
                    return 'date'
        except:
            pass
        
        # === Test 3: Peu de valeurs uniques = catégorie ===
        nunique = col_data.nunique()
        if nunique < 20 and nunique > 1:
            return 'category'
        
        # Par défaut: texte
        return 'text'

    def clean_data(self):
        """Nettoie les donnees selon les types detectes et fusionne jour/mois/an en date si présent."""
        self.cleaned_df = self.df.copy()
        is_large_dataset = len(self.cleaned_df) > 300000

        # --- ASTUCE : Correction automatique du décalage CSV ---
        if 'etat' in self.cleaned_df.columns and 'note' in self.cleaned_df.columns:
            mask = self.cleaned_df['etat'].isna() & self.cleaned_df['note'].astype(str).str.match(r'[A-Za-z]')
            self.cleaned_df.loc[mask, 'etat'] = self.cleaned_df.loc[mask, 'note']
            self.cleaned_df.loc[mask, 'note'] = np.nan
        # -------------------------------------------------------

        # --- FUSION jour/mois/an en colonne date (mais on garde les colonnes d'origine) ---
        cols_lower = [c.lower() for c in self.cleaned_df.columns]
        if all(x in cols_lower for x in ['jour', 'mois', 'an']):
            col_jour = [c for c in self.cleaned_df.columns if c.lower() == 'jour'][0]
            col_mois = [c for c in self.cleaned_df.columns if c.lower() == 'mois'][0]
            col_an = [c for c in self.cleaned_df.columns if c.lower() == 'an'][0]
            # Version vectorisée: beaucoup plus rapide sur gros volumes.
            years = pd.to_numeric(self.cleaned_df[col_an], errors='coerce')
            months = pd.to_numeric(self.cleaned_df[col_mois], errors='coerce')
            days = pd.to_numeric(self.cleaned_df[col_jour], errors='coerce')
            self.cleaned_df['date'] = pd.to_datetime(
                {
                    'year': years,
                    'month': months,
                    'day': days,
                },
                errors='coerce'
            )
            # Adapter le mapping pour la nouvelle colonne (on garde jour/mois/an)
            self.renaming_map['date'] = 'date'
            self.column_types['date'] = 'date'

        for orig_col, new_col in self.renaming_map.items():
            if orig_col not in self.cleaned_df.columns:
                continue

            data_type = self.column_types.get(orig_col, 'text')
            if data_type == 'number':
                series = self.cleaned_df[orig_col]
                if pd.api.types.is_numeric_dtype(series):
                    self.cleaned_df[orig_col] = pd.to_numeric(series, errors='coerce')
                else:
                    self.cleaned_df[orig_col] = pd.to_numeric(
                        series.astype(str).str.replace(',', '.', regex=False),
                        errors='coerce'
                    )
            elif data_type == 'date':
                self.cleaned_df[orig_col] = pd.to_datetime(self.cleaned_df[orig_col], errors='coerce')
            elif data_type == 'category':
                if is_large_dataset:
                    # Réduit fortement le coût CPU pour les très gros CSV.
                    self.cleaned_df[orig_col] = self.cleaned_df[orig_col].astype('string').str.strip()
                else:
                    self.cleaned_df[orig_col] = self.cleaned_df[orig_col].apply(
                        lambda x: normalize_category(x, orig_col, strict_mode=True)
                    )

        self.cleaned_df = self.cleaned_df.rename(columns=self.renaming_map)
        


    def generate_strategic_questions_and_graphs(self, contexte_metier: str = "") -> List[Dict]:
        """Génère questions métier PERTINENTES adaptées au contexte thématique."""
        print("\n[IA] Génération de questions métier...")
        df = self.cleaned_df if self.cleaned_df is not None else self.df

        # === AUTO-DÉTECTION DU DOMAINE ===
        # Analyser les noms de colonnes pour détecter le domaine automatiquement
        all_cols_lower = ' '.join([c.lower() for c in df.columns])
        
        domain = "generic"
        # Mots-clés accidents (colonnes renommées + originales)
        if any(x in all_cols_lower for x in ['luminosite', 'collision', 'vitesse', 'atmosphere', 'agglomeration', 'route', 'accident', 'lum', 'col', 'atm', 'agg', 'num_acc']):
            domain = "accidents"
        # Mots-clés formation
        elif any(x in all_cols_lower for x in ['taux', 'completion', 'inactivite', 'apprenant', 'statut', 'formation', 'module', 'score']):
            domain = "formation"
        # Mots-clés ventes
        elif any(x in all_cols_lower for x in ['revenue', 'sales', 'customer', 'segment', 'product', 'montant', 'order', 'ship']):
            domain = "ventes"
        # Mots-clés RH
        elif any(x in all_cols_lower for x in ['departement', 'employee', 'turnover', 'rh', 'salaire', 'employe', 'hired', 'resign']):
            domain = "rh"
        
        # Utiliser le thème fourni si disponible, sinon utiliser le domaine détecté
        theme = contexte_metier.lower().strip() if contexte_metier else domain
        if theme not in CONTEXTE_THEMES:
            theme = "generic"
        
        print(f"[AUTO-DETECT] Domaine: {domain} | Thème: {theme}")
        utilites = CONTEXTE_THEMES[theme]
        print(f"[THÈME] {utilites['name']}")

        # Détection date
        cols_lower = [c.lower() for c in df.columns]
        date_components = set()
        if all(x in cols_lower for x in ['jour', 'mois', 'an']):
            try:
                df['date'] = pd.to_datetime(df[['an', 'mois', 'jour']].astype(str).agg('-'.join, axis=1), errors='coerce')
                date_components = {'jour', 'mois', 'an'}
            except Exception:
                pass

        # Classification des colonnes
        cols_all_num = df.select_dtypes(include=['number']).columns.tolist()
        cols_all_cat = df.select_dtypes(include=['object', 'category']).columns.tolist()
        cols_date = df.select_dtypes(include=['datetime', 'datetime64[ns]']).columns.tolist()

        forbidden_exact = {'id', 'pk', 'fk', 'row', 'index', 'jour', 'mois', 'an', 'annee', 'année'}
        forbidden_contains = {'num_acc', 'latitude', 'longitude'}

        def is_forbidden_col(col_name: str) -> bool:
            col_lower = col_name.lower()
            if col_lower in date_components:
                return True
            if col_lower in forbidden_exact:
                return True
            if col_lower.startswith('id_') or col_lower.endswith('_id'):
                return True
            if any(token in col_lower for token in forbidden_contains):
                return True
            if re.search(r'(^|[_\W])(id|pk|fk)([_\W]|$)', col_lower):
                return True
            return False
        
        # Identifier vraies valeurs vs codes
        cols_num_values = []
        cols_num_codes = []
        code_threshold = max(10, min(60, int(len(df) * 0.1)))
        
        for c in cols_all_num:
            if is_forbidden_col(c):
                continue

            try:
                unique_count = int(df[c].nunique(dropna=True))
                if unique_count <= 1:
                    continue
                if 2 <= unique_count <= code_threshold:
                    cols_num_codes.append(c)
                else:
                    cols_num_values.append(c)
            except Exception:
                pass

        cols_cat = [
            c for c in cols_all_cat
            if not is_forbidden_col(c) and df[c].nunique(dropna=True) > 1
        ]
        for c in cols_num_codes:
            if c not in cols_cat:
                cols_cat.append(c)

        questions = self._generate_domain_specific_questions(
            df, cols_num_codes, cols_num_values, cols_cat, cols_date, domain, utilites
        )

        # Valider et dédupliquer
        valid_questions = []
        seen = set()
        df_cols = set(df.columns)
        for q in questions:
            cols = q.get('colonnes', [])
            question_key = (tuple(sorted(cols)), q.get('type_graphique'))
            if all(c in df_cols for c in cols) and len(cols) > 0 and question_key not in seen:
                valid_questions.append(q)
                seen.add(question_key)
        
        if valid_questions:
            self.questions = valid_questions[:10]
            print(f"[OK] {len(self.questions)} questions générées et validées")
            return self.questions
        
        # Fallback
        print("[WARN] Génération locale fallback enrichie")
        fallback = self._questions_generic(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)

        if not fallback:
            # Ultime sécurité: au moins une question exploitable, quel que soit le CSV.
            candidate_cols = [c for c in df.columns if df[c].nunique(dropna=True) > 1]
            if candidate_cols:
                fallback.append({
                    'question': f"Quelle est la répartition des observations selon {candidate_cols[0]} ?",
                    'colonnes': [candidate_cols[0]],
                    'type_graphique': 'bar',
                    'utilite': utilites.get('q1_utilite', "Obtenir une vue d'ensemble des données"),
                    'interpretations': ['', '']
                })

        self.questions = fallback[:10] if fallback else []
        print(f"[FALLBACK] {len(self.questions)} questions générées")
        return self.questions

    def _generate_domain_specific_questions(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, domain, utilites):
        """Génère des questions INTELLIGENTES et SPÉCIFIQUES selon le domaine détecté."""
        questions = []
        
        if domain == "accidents":
            return self._questions_accidents(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)
        elif domain == "formation":
            return self._questions_formation(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)
        elif domain == "ventes":
            return self._questions_ventes(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)
        elif domain == "rh":
            return self._questions_rh(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)
        else:
            return self._questions_generic(df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites)

    def _questions_accidents(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites):
        """Questions intelligentes pour domaine SÉCURITÉ ROUTIÈRE (9 questions)."""
        questions = []
        all_cols = cols_num_codes + cols_num_values + cols_cat
        
        # Q1: Facteur de risque principal
        if cols_num_codes:
            primary = cols_num_codes[0]
            if len(df[primary].unique()) <= 12:
                questions.append({
                    'question': f"Quels sont les types de {primary} les plus fréquents?",
                    'colonnes': [primary],
                    'type_graphique': 'pie',
                    'utilite': "Identifier les facteurs de risque majeurs pour cibler les campagnes de prévention.",
                    'interpretations': ['', '']
                })
        
        # Q2: Luminosité et collision
        lum_cols = [c for c in cols_num_codes if 'lum' in c.lower()]
        col_cols = [c for c in cols_num_codes if 'col' in c.lower()]
        if lum_cols and col_cols:
            questions.append({
                'question': f"Les types de collision varient-ils selon la luminosité (nuit/jour)?",
                'colonnes': [lum_cols[0], col_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Détecter les interactions entre facteurs pour adapter les mesures de sécurité.",
                'interpretations': ['', '']
            })
        
        # Q3: Zone géographique
        agg_cols = [c for c in cols_num_codes if 'agg' in c.lower()]
        if agg_cols:
            questions.append({
                'question': f"Y a-t-il des zones (urbain/rural) avec plus d'accidents?",
                'colonnes': [agg_cols[0]],
                'type_graphique': 'pie',
                'utilite': "Adapter les mesures de sécurité par type de zone urbain/rural.",
                'interpretations': ['', '']
            })
        
        # Q4: Atmosphère
        atm_cols = [c for c in cols_num_codes if 'atm' in c.lower()]
        if atm_cols and cols_num_values:
            questions.append({
                'question': f"Comment l'atmosphère (météo) influence-t-elle les accidents?",
                'colonnes': [atm_cols[0], cols_num_values[0]] if cols_num_values else [atm_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Anticiper les pics d'accidents lors de mauvaises conditions météorologiques.",
                'interpretations': ['', '']
            })
        
        # Q5: Intersection
        int_cols = [c for c in cols_num_codes if 'int' in c.lower()]
        if int_cols:
            questions.append({
                'question': f"Les types d'intersection (croisement/sortie) influencent-ils les accidents?",
                'colonnes': [int_cols[0]],
                'type_graphique': 'histogram',
                'utilite': "Identifier les configurations à haut risque pour concentrer les ressources.",
                'interpretations': ['', '']
            })
        
        # Q6: Heures critiques
        date_cols = [c for c in df.columns if any(x in c.lower() for x in ['heure', 'hrmn', 'time', 'hour'])]
        if date_cols:
            questions.append({
                'question': f"Y a-t-il des heures spécifiques à plus haut risque?",
                'colonnes': [date_cols[0]],
                'type_graphique': 'line',
                'utilite': "Renforcer la prévention et les secours lors des pics horaires.",
                'interpretations': ['', '']
            })
        
        # Q7: Corrélation facteurs
        if len(cols_num_values) > 1:
            questions.append({
                'question': f"Quel est le lien entre {cols_num_values[0]} et {cols_num_values[1]}?",
                'colonnes': [cols_num_values[0], cols_num_values[1]],
                'type_graphique': 'scatter',
                'utilite': "Déterminer les facteurs corrélés pour stratifier les actions de sécurité.",
                'interpretations': ['', '']
            })
        
        # Q8: Jour de la semaine
        day_cols = [c for c in df.columns if any(x in c.lower() for x in ['jour', 'day'])]
        if day_cols:
            questions.append({
                'question': f"La gravité des accidents varie-t-elle selon le jour?",
                'colonnes': [day_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Adapter le déploiement des secours selon le jour de la semaine.",
                'interpretations': ['', '']
            })
        
        # Q9: Mois critiques
        month_cols = [c for c in df.columns if any(x in c.lower() for x in ['mois', 'month'])]
        if month_cols:
            questions.append({
                'question': f"Y a-t-il des périodes saisonnières plus à risque?",
                'colonnes': [month_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Anticiper les pics d'accidents (vacances, hivers) pour renforcer prévention.",
                'interpretations': ['', '']
            })
        
        return questions

    def _questions_formation(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites):
        """Questions intelligentes pour domaine FORMATION/RH (8+ questions)."""
        questions = []
        all_cols = cols_num_codes + cols_num_values + cols_cat
        
        def find_col(keywords):
            for col in all_cols:
                if any(kw in col.lower() for kw in keywords):
                    return col
            return None
        
        completion_cols = find_col(['completion', 'progress', 'taux', 'complete'])
        inactivity_cols = find_col(['inactivite', 'inactif', 'inactive', 'jours', 'days'])
        status_cols = find_col(['statut', 'status', 'etat'])
        score_cols = find_col(['score', 'resultat', 'result', 'note'])
        module_cols = find_col(['module', 'cours', 'formation', 'training'])
        
        # Q1: Apprenants inactifs
        if inactivity_cols:
            questions.append({
                'question': f"Quels apprenants sont inactifs depuis plus de 15 jours?",
                'colonnes': [inactivity_cols],
                'type_graphique': 'histogram',
                'utilite': "Cibler les relances pour éviter les abandons définitifs et sécuriser le financement.",
                'interpretations': ['', '']
            })
        
        # Q2: Distribution de complétion
        if completion_cols:
            questions.append({
                'question': f"Quel est le taux de complétion des apprenants? Qui est bloqué sous 20%?",
                'colonnes': [completion_cols],
                'type_graphique': 'histogram',
                'utilite': "Intervenir rapidement sur les blocages techniques ou de motivation.",
                'interpretations': ['', '']
            })
        
        # Q3: Statut vs complétion
        if status_cols and completion_cols:
            questions.append({
                'question': f"Comment la complétion varie-t-elle selon le statut?",
                'colonnes': [status_cols, completion_cols],
                'type_graphique': 'bar',
                'utilite': "Évaluer l'efficacité de la formation selon le profil d'apprenant.",
                'interpretations': ['', '']
            })
        
        # Q4: Performance par module
        if module_cols and score_cols:
            questions.append({
                'question': f"Quels modules ont les meilleurs scores de réussite?",
                'colonnes': [module_cols, score_cols],
                'type_graphique': 'bar',
                'utilite': "Identifier les modules performants et les axes d'amélioration.",
                'interpretations': ['', '']
            })
        
        # Q5: Corrélation complétion vs score
        if completion_cols and score_cols:
            questions.append({
                'question': f"Le taux de complétion influence-t-il le score final?",
                'colonnes': [completion_cols, score_cols],
                'type_graphique': 'scatter',
                'utilite': "Mesurer le lien entre engagement et résultat d'apprentissage.",
                'interpretations': ['', '']
            })
        
        # Q6: Distribution statut
        if status_cols:
            questions.append({
                'question': f"Quel est le profil de statut des apprenants?",
                'colonnes': [status_cols],
                'type_graphique': 'pie',
                'utilite': "Comparer les résultats par profil d'apprenant pour optimiser l'accompagnement.",
                'interpretations': ['', '']
            })
        
        # Q7: Module et inactivité
        if module_cols and inactivity_cols:
            questions.append({
                'question': f"Quels modules ont les taux d'inactivité les plus élevés?",
                'colonnes': [module_cols, inactivity_cols],
                'type_graphique': 'bar',
                'utilite': "Identifier les modules nécessitant un meilleur support pédagogique.",
                'interpretations': ['', '']
            })
        
        # Q8: Score par statut
        if score_cols and status_cols:
            questions.append({
                'question': f"Le score final varie-t-il selon le statut de l'apprenant?",
                'colonnes': [status_cols, score_cols],
                'type_graphique': 'bar',
                'utilite': "Évaluer si certains profils réussissent mieux que d'autres.",
                'interpretations': ['', '']
            })
        
        return questions

    def _questions_ventes(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites):
        """Questions intelligentes pour domaine VENTES/BUSINESS (8+ questions)."""
        questions = []
        
        revenue_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['revenue', 'sales', 'montant', 'profit'])]
        segment_cols = [c for c in cols_cat if any(x in c.lower() for x in ['segment', 'customer'])]
        product_cols = [c for c in cols_cat if any(x in c.lower() for x in ['product', 'category', 'sub-category'])]
        quantity_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['quantity', 'qte', 'quantite'])]
        discount_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['discount', 'promotion'])]
        region_cols = [c for c in cols_cat if any(x in c.lower() for x in ['region', 'pays', 'state', 'country', 'city'])]
        
        # Q1: Segments lucratifs
        if segment_cols and revenue_cols:
            questions.append({
                'question': f"Quels segments client génèrent le plus de revenue?",
                'colonnes': [segment_cols[0], revenue_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Identifier les segments les plus lucratifs pour maximiser le revenue.",
                'interpretations': ['', '']
            })
        
        # Q2: Performance produits
        if product_cols and revenue_cols:
            questions.append({
                'question': f"Quels produits/catégories ont la meilleure performance?",
                'colonnes': [product_cols[0], revenue_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Optimiser le mix produit pour augmenter la rentabilité.",
                'interpretations': ['', '']
            })
        
        # Q3: Corrélation revenue vs quantity
        if revenue_cols and quantity_cols:
            questions.append({
                'question': f"Y a-t-il une corrélation entre la quantité et le revenue?",
                'colonnes': [quantity_cols[0], revenue_cols[0]],
                'type_graphique': 'scatter',
                'utilite': "Déterminer l'élasticité prix pour optimiser les stratégies.",
                'interpretations': ['', '']
            })
        
        # Q4: Impact des remises
        if revenue_cols and discount_cols:
            questions.append({
                'question': f"Comment les remises impactent-elles le revenue?",
                'colonnes': [discount_cols[0], revenue_cols[0]],
                'type_graphique': 'scatter',
                'utilite': "Évaluer l'efficacité des promotions sur le chiffre d'affaires.",
                'interpretations': ['', '']
            })
        
        # Q5: Performance régionale
        if region_cols and revenue_cols:
            questions.append({
                'question': f"Quelles régions ont les meilleures performances?",
                'colonnes': [region_cols[0], revenue_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Identifier les zones à fort potentiel pour ciblage marketing.",
                'interpretations': ['', '']
            })
        
        # Q6: Distribution revenue
        if revenue_cols:
            questions.append({
                'question': f"Quelle est la distribution du revenue (moyenne, variation)?",
                'colonnes': [revenue_cols[0]],
                'type_graphique': 'histogram',
                'utilite': "Comprendre la variabilité des ventes pour ajuster les prévisions.",
                'interpretations': ['', '']
            })
        
        # Q7: Segment vs région
        if segment_cols and region_cols:
            questions.append({
                'question': f"Quelle est la répartition des segments par région?",
                'colonnes': [segment_cols[0], region_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Comparer les mix produit par région pour optimiser la distribution.",
                'interpretations': ['', '']
            })
        
        # Q8: Quantity vs segment
        if quantity_cols and segment_cols:
            questions.append({
                'question': f"La quantité vendue varie-t-elle selon le segment?",
                'colonnes': [segment_cols[0], quantity_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Adapter la stratégie de volume selon le profil client.",
                'interpretations': ['', '']
            })
        
        return questions

    def _questions_rh(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites):
        """Questions intelligentes pour domaine RH (6+ questions)."""
        questions = []
        
        turnover_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['turnover', 'depart', 'resignation'])]
        salary_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['salaire', 'salary', 'compensation'])]
        dept_cols = [c for c in cols_cat if any(x in c.lower() for x in ['departement', 'dept', 'department', 'division'])]
        level_cols = [c for c in cols_cat if any(x in c.lower() for x in ['level', 'niveau', 'position', 'role'])]
        tenure_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['tenure', 'anciennete', 'years', 'ans'])]
        performance_cols = [c for c in (cols_num_values + cols_num_codes) if any(x in c.lower() for x in ['performance', 'score', 'rating'])]
        
        # Q1: Turnover par département
        if dept_cols and turnover_cols:
            questions.append({
                'question': f"Quel département a le taux de turnover le plus élevé?",
                'colonnes': [dept_cols[0], turnover_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Identifier les équipes à risque pour renforcer la rétention des talents.",
                'interpretations': ['', '']
            })
        
        # Q2: Salaire par département
        if dept_cols and salary_cols:
            questions.append({
                'question': f"Comment le salaire varie-t-il selon le département?",
                'colonnes': [dept_cols[0], salary_cols[0]],
                'type_graphique': 'bar',
                'utilite': "Analyser l'équité salariale et identifier les écarts entre équipes.",
                'interpretations': ['', '']
            })
        
        # Q3: Tenure vs Turnover
        if tenure_cols and turnover_cols:
            questions.append({
                'question': f"Y a-t-il une corrélation entre l'ancienneté et le risque de départ?",
                'colonnes': [tenure_cols[0], turnover_cols[0]],
                'type_graphique': 'scatter',
                'utilite': "Évaluer si les départs sont concentrés sur certains profils (juniors/seniors).",
                'interpretations': ['', '']
            })
        
        # Q4: Distribution par niveau
        if level_cols:
            questions.append({
                'question': f"Quelle est la répartition des salariés par niveau?",
                'colonnes': [level_cols[0]],
                'type_graphique': 'pie',
                'utilite': "Évaluer la structure organisationnelle et les hiérarchies.",
                'interpretations': ['', '']
            })
        
        # Q5: Performance et Turnover
        if performance_cols and turnover_cols:
            questions.append({
                'question': f"Les meilleurs performeurs partent-ils plus que les autres?",
                'colonnes': [performance_cols[0], turnover_cols[0]],
                'type_graphique': 'scatter',
                'utilite': "Analyser si la fuite des talents porte sur les hauts performeurs.",
                'interpretations': ['', '']
            })
        
        # Q6: Salaire vs Performance
        if salary_cols and performance_cols:
            questions.append({
                'question': f"Y a-t-il une corrélation entre salaire et performance?",
                'colonnes': [salary_cols[0], performance_cols[0]],
                'type_graphique': 'scatter',
                'utilite': "Vérifier si la politique de rémunération récompense la performance.",
                'interpretations': ['', '']
            })
        
        return questions

    def _questions_generic(self, df, cols_num_codes, cols_num_values, cols_cat, cols_date, utilites):
        """Questions génériques par défaut."""
        questions = []
        used = set()

        def add_question(question: str, colonnes: List[str], type_graphique: str, utilite: str):
            key = (tuple(colonnes), type_graphique)
            if colonnes and key not in used:
                questions.append({
                    'question': question,
                    'colonnes': colonnes,
                    'type_graphique': type_graphique,
                    'utilite': utilite,
                    'interpretations': ['', '']
                })
                used.add(key)

        cat_candidates = [c for c in cols_cat if df[c].nunique(dropna=True) <= 40]
        primary_cat = cat_candidates[0] if cat_candidates else (cols_cat[0] if cols_cat else None)
        primary_num = cols_num_values[0] if cols_num_values else (cols_num_codes[0] if cols_num_codes else None)

        # Q1: Répartition par catégorie principale
        if primary_cat:
            unique_vals = int(df[primary_cat].nunique(dropna=True))
            graph_type = 'pie' if unique_vals <= 12 else 'bar'
            add_question(
                f"Quelle est la répartition des observations par {primary_cat} ?",
                [primary_cat],
                graph_type,
                utilites.get('q1_utilite', 'Identifier les catégories dominantes')
            )

        # Q2: Distribution d'une métrique numérique
        if primary_num:
            add_question(
                f"Comment se distribue la variable {primary_num} ?",
                [primary_num],
                'histogram',
                utilites.get('q2_utilite', 'Comprendre la dispersion et les anomalies potentielles')
            )

        # Q3: Catégorie vs métrique
        if primary_cat and primary_num:
            add_question(
                f"Comment {primary_num} varie-t-il selon {primary_cat} ?",
                [primary_cat, primary_num],
                'bar',
                utilites.get('q3_utilite', 'Comparer la performance par segment')
            )

        # Q4: Corrélation entre deux numériques
        if len(cols_num_values) >= 2:
            add_question(
                f"Y a-t-il une relation entre {cols_num_values[0]} et {cols_num_values[1]} ?",
                [cols_num_values[0], cols_num_values[1]],
                'scatter',
                utilites.get('q4_utilite', 'Détecter les relations entre indicateurs')
            )
        elif len(cols_num_codes) >= 2:
            add_question(
                f"Comment {cols_num_codes[0]} varie-t-il selon {cols_num_codes[1]} ?",
                [cols_num_codes[1], cols_num_codes[0]],
                'bar',
                utilites.get('q4_utilite', 'Analyser l\'interaction entre deux dimensions')
            )

        # Q5: Évolution temporelle si disponible
        if cols_date and primary_num:
            add_question(
                f"Comment {primary_num} évolue-t-il dans le temps ?",
                [cols_date[0], primary_num],
                'line',
                utilites.get('q5_utilite', 'Repérer les tendances temporelles')
            )

        # Q6: Répartition croisée de deux catégories
        if len(cat_candidates) >= 2:
            add_question(
                f"Quelle est la répartition croisée entre {cat_candidates[0]} et {cat_candidates[1]} ?",
                [cat_candidates[0], cat_candidates[1]],
                'bar',
                utilites.get('q6_utilite', 'Mettre en évidence des segments combinés')
            )

        return questions[:8]

    def save_results(self, output_dir: str = None) -> str:
        """Sauvegarde tous les resultats."""
        if output_dir is None:
            output_dir = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        out_path = Path(output_dir)
        out_path.mkdir(exist_ok=True)

        # Donnees nettoyees
        clean_csv = out_path / "donnees_nettoyees.csv"
        self.cleaned_df.to_csv(clean_csv, index=False, encoding='utf-8-sig', sep=';')

        # Mapping
        mapping_file = out_path / "renaming_map.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.renaming_map, f, indent=2, ensure_ascii=False)

        # Proposals
        proposals_file = out_path / "proposals.json"
        with open(proposals_file, 'w', encoding='utf-8') as f:
            json.dump(self.proposals, f, indent=2, ensure_ascii=False)

        return str(out_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        theme = sys.argv[2] if len(sys.argv) > 2 else ""  # Passer vide pour auto-détection
        print(f"[CLI] Analyse automatique du fichier : {input_file}")
        analyzer = CSVAnalyzer(input_file, model=DEFAULT_MODEL)
        if analyzer.load_data():
            analyzer.analyze_columns()
            analyzer.clean_data()
            questions = analyzer.generate_strategic_questions_and_graphs(contexte_metier=theme)
            
            # Génération du rapport HTML/PDF
            try:
                from rapport_generator import RapportGenerator
                from graphiques import GraphicsGenerator
                
                output_dir = analyzer.save_results()
                
                # Générer les graphiques pour chaque question
                graph_gen = GraphicsGenerator(analyzer.cleaned_df, output_dir)
                graphs = []
                for q in questions:
                    try:
                        graph_file = graph_gen.generate_graph_for_question(
                            q.get('question', ''),
                            contexte=theme,
                            colonnes=q.get('colonnes', []),
                            type_graphique=q.get('type_graphique')
                        )
                        if graph_file:
                            graphs.append(graph_file)
                    except Exception as e:
                        print(f"[WARN] Graphique non généré: {e}")
                
                # Générer des graphiques supplémentaires (distributions, corrélations)
                # MAIS: exclure les colonnes ID et peu pertinentes
                try:
                    num_cols = analyzer.cleaned_df.select_dtypes(include=['number']).columns.tolist()
                    
                    # Filtrer les colonnes pertinentes
                    useful_cols = []
                    for col in num_cols:
                        # Skip ID columns (trop uniques)
                        try:
                            unique_count = analyzer.cleaned_df[col].nunique()
                            if unique_count > 500:  # Probablement un ID
                                continue
                        except:
                            continue
                        
                        # Skip date components
                        if any(x in col.lower() for x in ['date_jour', 'date_mois', 'date_an', 'num_acc']):
                            continue
                        
                        # Skip les colonnes déjà utilisées dans les questions
                        already_used = False
                        for q in questions:
                            if col in q.get('colonnes', []):
                                already_used = True
                                break
                        if already_used:
                            continue
                        
                        useful_cols.append(col)
                    
                    # Générer max 3 graphiques bonus
                    for col in useful_cols[:3]:
                        try:
                            graph_file = graph_gen.graph_distribution_numeric(col)
                            if graph_file:
                                graphs.append(graph_file)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                rapport_gen = RapportGenerator(output_dir)
                result_files = rapport_gen.generate_complete_report(
                    df=analyzer.cleaned_df,
                    renaming_map=analyzer.renaming_map,
                    proposals=analyzer.proposals,
                    questions=questions,
                    graphs=graphs,
                    nom_fichier=input_file,
                    contexte_metier=theme
                )
                print(f"[OK] Rapport généré : {result_files.get('html')}")
            except Exception as e:
                print(f"[ERREUR] Rapport non généré : {e}")
        else:
            print("[ERREUR] Chargement du CSV impossible.")
    else:
        print("Usage : python core_analysis.py <fichier.csv> [theme]")
        print("\nThèmes disponibles:")
        for theme_key, theme_info in CONTEXTE_THEMES.items():
            print(f"  - {theme_key}: {theme_info['name']}")
