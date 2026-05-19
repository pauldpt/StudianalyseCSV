#!/usr/bin/env python3
"""
AGENT IA UNIVERSEL - Analyse n'importe quel CSV avec Groq (gratuit)
- Détection automatique des colonnes en UN SEUL appel API
- Proposition de renommage et de type (date, nombre, catégorie, id, texte)
- Nettoyage des données (virgules, symboles, dates, fautes d'orthographe)
- Génération de questions stratégiques diplomatiques
- Détection des outliers et anomalies
- Rapport complet des corrections appliquées

Utilisation:
    python agent_groq.py --input fichier.csv
    python agent_groq.py --input fichier.csv --auto
    python agent_groq.py --input fichier.csv --fix-all
    python agent_groq.py --input fichier.csv --api-key VOTRE_CLE_GROQ
"""

import pandas as pd
import numpy as np
import argparse
import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from groq import Groq
from rapidfuzz import process as fuzz_process
DEFAULT_MODEL = "llama-3.3-70b-versatile"
CONFIDENCE_THRESHOLD_AUTO = 0.7
CONFIDENCE_THRESHOLD_FIX_ALL = 0.5

CUSTOM_CORRECTIONS = {}
def load_custom_corrections():
    global CUSTOM_CORRECTIONS
    if Path("corrections.json").exists():
        try:
            with open("corrections.json", 'r', encoding='utf-8') as f:
                CUSTOM_CORRECTIONS = json.load(f)
                print("[INFO] Dictionnaire de corrections personnalisées chargé.")
        except:
            pass

KNOWN_CATEGORIES = {
    "statut": ["Terminé", "Abandonné", "En cours", "Inscrit"],
    "financeur": ["CPF", "Région", "France Travail", "OPCO", "Auto-financé"],
    "niveau": ["Débutant", "Intermédiaire", "Avancé", "Expert"]
}

def clean_number(value) -> Optional[float]:
    """Nettoie les nombres en gérant les séparateurs de milliers et décimaux."""
    if pd.isna(value) or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    s = str(value).strip()
    s = re.sub(r'[€$£%]', '', s)  # Supprime les symboles monétaires
    
    # Détecte le format des séparateurs (virgule décimale ou point décimal)
    comma_count = s.count(',')
    dot_count = s.count('.')
    
    if comma_count > 1:  # Ex: "1 234,56" -> virgule = 1, espace ignore, c'est FAUX
        # Format français avec espaces : "1 234,56"
        s = s.replace(' ', '').replace(',', '.')
    elif dot_count > 1:  # Ex: "1.234.567,89"
        # Format avec points comme séparateur de milliers
        s = s.replace('.', '').replace(',', '.')
    elif comma_count == 1 and dot_count == 0:
        # Ambigu : "1,5" peut être 1.5 (français) ou 1 avec 5 (rare)
        # Heuristique : si peu de décimales, c'est un format français
        s = s.replace(',', '.')
    elif dot_count == 1 and comma_count == 0:
        # Format anglo-saxon normal : "1234.56"
        pass
    
    s = re.sub(r'[^\d\.\-]', '', s)  # Supprime tout sauf chiffres, point, moins
    
    try:
        # Gère les chaînes avec plusieurs points (cas rare)
        dots = s.count('.')
        if dots > 1:
            # Garde le dernier point comme séparateur décimal
            parts = s.split('.')
            s = ''.join(parts[:-1]) + '.' + parts[-1]
        
        return float(s)
    except ValueError:
        return None

def clean_date(value) -> Optional[str]:
    if pd.isna(value) or value == '':
        return None
    s = str(value).strip()
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y",
        "%Y%m%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except:
        pass
    return None

def normalize_category(value, col_name: str = "", reference_categories: Dict[str, List[str]] = None, strict_mode: bool = False) -> str:
    """Normalise les catégories avec matching flou si disponible.
    
    strict_mode=False : Retourne la valeur capitalisée si elle ne correspond pas au dictionnaire
    strict_mode=True : Retourne None (NaN) pour les valeurs inconnues ou manquantes
    """
    # Gérer les NaN/None en entrée
    if pd.isna(value):
        return None
    
    s = str(value).strip()
    
    # Détecter les valeurs considérées comme "vides"
    if not s or s.lower() in ['', 'nan', 'null', 'none', '?', 'inconnu', '-', '--']:
        return None  # Retourner None pour les valeurs vides (sera NaN en CSV)
    
    # Si un dictionnaire personnalisé existe pour cette colonne, l'utiliser (TOUJOURS strict)
    if col_name in CUSTOM_CORRECTIONS:
        custom_dict = CUSTOM_CORRECTIONS[col_name]
        s_lower = s.lower()
        if s_lower in custom_dict:
            return custom_dict[s_lower]
        
        # Fuzzy matching sur le dictionnaire personnalisé
        keys = list(custom_dict.keys())
        if keys:
            match, score, _ = fuzz_process.extractOne(s_lower, keys)
            if score > 80:
                return custom_dict[match]
        
        # Si pas trouvé dans le dictionnaire perso, utiliser la valeur originale
        return s.strip()
    
    # Si pas de dictionnaire fourni et pas de corrections perso, retourner juste capitalisée
    if reference_categories is None:
        # Retourner la valeur telle quelle en mode lenient (pour "Nom du cours", etc.)
        return s.strip()
    
    s_lower = s.lower()
    
    # Matched exact ou contenu dans les variantes
    for canonical, variants in reference_categories.items():
        if s_lower in variants or any(v in s_lower for v in variants):
            return canonical
    
    # Fuzzy matching flou
    all_values = []
    for canonical, variants in reference_categories.items():
        all_values.extend(variants)
    
    if all_values:
        match, score, _ = fuzz_process.extractOne(s_lower, all_values)
        if score > 80:
            for canonical, variants in reference_categories.items():
                if match in variants:
                    return canonical
    
    # Fallback : retourner None en mode strict (pour cohérence), valeur en mode lenient
    if strict_mode:
        return None
    else:
        return s.strip()

# 

class GroqClient:
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.client = Groq(api_key=self.api_key)
        self.available = True

    def chat(self, prompt: str) -> str:
        if not self.available:
            return ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERREUR API Groq] {e}")
            return ""

# 

class ColumnAnalyzer:
    def __init__(self, api_client: GroqClient):
        self.client = api_client

    def analyze_all_columns(self, columns_info: List[Dict]) -> Dict:
        """Envoie TOUTES les colonnes en UNE SEULE requête IA. GAIN: 30x plus rapide!"""
        if not columns_info:
            return {}
        
        # Préparer le prompt compact (sans exemples lourds)
        prompt = """Analyse les colonnes suivantes d'un CSV. Pour CHAQUE colonne, fournis:
- proposed_name: nom français clair
- data_type: 'date', 'number', 'category', 'id', ou 'text'
- confidence: 0 à 1
- anomalies: liste de problèmes détectés

COLONNES À ANALYSER:
"""
        for i, col_info in enumerate(columns_info, 1):
            prompt += f"\n{i}. {col_info['name']}"
            if col_info['samples']:
                prompt += f" | Exemples: {col_info['samples'][:3]}"
            prompt += f" | Uniques: {col_info['nunique']} | Manquants: {col_info['null_pct']:.0f}%"
        
        prompt += """\n\nRéponds UNIQUEMENT en JSON valide, pas de texte supplémentaire:
{
  "colonne_originale": {
    "proposed_name": "...",
    "data_type": "...",
    "confidence": 0.9,
    "anomalies": ["..."]
  }
}"""
        
        response = self.client.chat(prompt)
        if not response:
            return {}
            
        # Extraction du JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}

    def analyze_column(self, col_name: str, sample_values: List[str], nunique: int, null_pct: float) -> Dict:
        prompt = f"""
Analyse la colonne suivante d'un fichier CSV.

Nom de la colonne : {col_name}
Exemples de valeurs (max 5) : {sample_values[:5]}
Nombre de valeurs uniques : {nunique}
Pourcentage de valeurs manquantes : {null_pct:.1f}%

Réponds UNIQUEMENT au format JSON suivant, sans texte supplémentaire :
{{
    "proposed_name": "nom_francais_clair",
    "data_type": "date|number|category|id|text",
    "confidence": 0.95,
    "anomalies": ["description1", "description2"]
}}

Règles :
- proposed_name : en français, lisible (ex: "date_debut", "score_obtenu", "statut_apprenant").
- data_type : date, number, category, id, text.
- confidence : entre 0 et 1.
- anomalies : décrire incohérences.
"""
        response = self.client.chat(prompt)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            for key in ['proposed_name', 'data_type', 'confidence', 'anomalies']:
                if key not in result:
                    result[key] = None
            return result
        return {}

# 

class AgentIAUniversel:
    def __init__(self, input_file: str, api_key: str = None, auto_mode: bool = False, fix_all_mode: bool = False, model: str = DEFAULT_MODEL):
        self.input_path = Path(input_file)
        if not self.input_path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {input_file}")
        self.auto_mode = auto_mode
        self.fix_all_mode = fix_all_mode  # Nouveau mode : corriger tout sans interaction
        self.api_client = GroqClient(api_key, model)
        self.analyzer = ColumnAnalyzer(self.api_client)
        self.df = None
        self.proposals = {}
        self.renaming_map = {}
        self.column_types = {}
        self.cleaned_df = None
        self.questions = []
        self.anomalies_log = {}  # Traçabilité des corrections

    def load_data(self):
        """Charge le CSV en détectant automatiquement encodage et séparateur."""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        # Séparateurs possibles
        separators = [',', ';', '\t', '|', ' ']
        
        for enc in encodings:
            try:
                # Lire juste la première ligne pour détecter le séparateur
                with open(self.input_path, 'r', encoding=enc) as f:
                    first_line = f.readline().strip()
                
                # Compter le nombre de séparateurs dans la première ligne
                best_sep = ','
                max_count = 0
                for sep in separators:
                    count = first_line.count(sep)
                    if count > max_count:
                        max_count = count
                        best_sep = sep
                
                if max_count == 0:
                    # Aucun séparateur trouvé ? Peut-être que c'est un fichier sans en-tête ?
                    # On force la virgule
                    best_sep = ','
                
                print(f"[DÉTECTION] Séparateur détecté : '{best_sep}' ({max_count} occurrences sur la première ligne)")
                
                # Recharger avec le bon séparateur
                self.df = pd.read_csv(self.input_path, encoding=enc, sep=best_sep)
                print(f"[OK] Chargé avec encodage {enc}, séparateur '{best_sep}' : {len(self.df)} lignes x {len(self.df.columns)} colonnes")
                return True
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"[ERREUR] {e}")
                return False
        
        print("[ERREUR] Impossible de lire le fichier CSV avec les encodages et séparateurs testés.")
        return False

    def propose_renaming(self):
        print("\n[ANALYSE DES COLONNES PAR IA - 1 APPEL API POUR TOUTES]")
        print("=" * 70)
        
        # Préparer les infos de TOUTES les colonnes en une fois
        columns_info = []
        for col in self.df.columns:
            sample = self.df[col].dropna().head(5).tolist()
            nunique = self.df[col].nunique()
            null_pct = (self.df[col].isna().sum() / len(self.df)) * 100
            columns_info.append({
                'name': col,
                'samples': sample,
                'nunique': nunique,
                'null_pct': round(null_pct, 1)
            })
        
        # UN SEUL appel IA pour toutes les colonnes
        print("[INFO] Analyse complète en 1 requête API")
        results = self.analyzer.analyze_all_columns(columns_info)
        
        self.proposals = {}
        for idx, col_info in enumerate(columns_info, 1):
            col = col_info['name']
            self.proposals[col] = results.get(col, {})
            
            # Affichage
            r = self.proposals[col]
            conf = r.get('confidence', 0)
            print(f"[{idx}/{len(columns_info)}] {col}")
            print(f"    -> {r.get('proposed_name', '?')} | Type: {r.get('data_type', '?')} | Confiance: {conf:.0%}")
            if r.get('anomalies'):
                anomalies_str = ', '.join(r['anomalies'][:3])  # Limiter l'affichage
                print(f"    [!] Anomalies: {anomalies_str}")
        
        # Sauvegarder les proposals comme checkpoint
        self._save_proposals_checkpoint()

    def interactive_validation(self):
        print("\n[VALIDATION DES RENOMMAGES]")
        print("=" * 70)
        
        for col, info in self.proposals.items():
            proposed = info.get('proposed_name', col)
            dtype = info.get('data_type', 'text')
            conf = info.get('confidence', 0)
            
            # Mode fix_all : accepter automatiquement tous les renommages au-dessus du seuil
            if self.fix_all_mode:
                if conf >= CONFIDENCE_THRESHOLD_FIX_ALL:
                    print(f"[FIXALL] {col} -> {proposed} (conf: {conf:.0%})")
                    self.renaming_map[col] = proposed
                    self.column_types[col] = dtype
                else:
                    # Même les faibles confiances, utiliser l'heuristique
                    print(f"[FIXALL] {col} -> {proposed} (conf basse: {conf:.0%}, utilisé quand même)")
                    self.renaming_map[col] = proposed
                    self.column_types[col] = dtype
                continue
            
            # Mode auto : accepter confiance >= seuil
            if self.auto_mode and conf >= CONFIDENCE_THRESHOLD_AUTO:
                print(f"[AUTO] {col} -> {proposed} (conf: {conf:.0%})")
                self.renaming_map[col] = proposed
                self.column_types[col] = dtype
                continue
            
            # Mode interactif
            print(f"\nColonne originale : {col}")
            print(f"Proposition : {proposed} (type: {dtype}, confiance: {conf:.0%})")
            choix = input("Accepter (o), Modifier (m), Sauter (s) : ").strip().lower()
            if choix == 'o':
                self.renaming_map[col] = proposed
                self.column_types[col] = dtype
            elif choix == 'm':
                new_name = input("Nouveau nom : ").strip()
                if new_name:
                    self.renaming_map[col] = new_name
                    self.column_types[col] = dtype
                else:
                    self.renaming_map[col] = col
            else:
                self.renaming_map[col] = col

    def apply_cleaning(self):
        print("\n[NETTOYAGE DES DONNÉES]")
        print("=" * 70)
        self.cleaned_df = self.df.rename(columns=self.renaming_map)
        self.anomalies_log = {}  # Pour tracer les corrections
        
        # Colonnes qui doivent être normalisées strictement (avec dictionnaire)
        strict_normalize_keywords = ['statut', 'état', 'etat', 'status', 'state', 'financeur', 'financier', 'level', 'niveau']
        
        for orig_col, new_col in self.renaming_map.items():
            dtype = self.column_types.get(orig_col, 'text')
            col_anomalies = []
            
            if dtype == 'number':
                before = self.cleaned_df[new_col].notna().sum()
                self.cleaned_df[new_col] = self.cleaned_df[new_col].apply(clean_number)
                after = self.cleaned_df[new_col].notna().sum()
                col_anomalies.append(f"Conversion numérique ({after - before} valeurs perdues)")
                
                # Détection des outliers (IQR method)
                outliers = self._detect_outliers(self.cleaned_df[new_col])
                if len(outliers) > 0:
                    col_anomalies.append(f"Outliers détectés: {len(outliers)} valeurs")
                    print(f"  [!] {new_col}: {len(outliers)} outliers detectes (ex: {outliers[:3]})")
                
                print(f"  [OK] {new_col}: conversion numerique")
                
            elif dtype == 'date':
                before = self.cleaned_df[new_col].notna().sum()
                self.cleaned_df[new_col] = self.cleaned_df[new_col].apply(clean_date)
                after = self.cleaned_df[new_col].notna().sum()
                col_anomalies.append(f"Conversion date ({after - before} valeurs perdues)")
                print(f"  [OK] {new_col}: conversion date")
                
            elif dtype == 'category':
                unique_before = self.cleaned_df[new_col].nunique()
                
                # Vérifier si cette colonne devrait être normalisée strictement
                should_normalize_strict = any(keyword in orig_col.lower() for keyword in strict_normalize_keywords)
                
                if should_normalize_strict:
                    # Mode strict : utiliser dictionnaire et "Inconnu" pour valeurs inconnues
                    self.cleaned_df[new_col] = self.cleaned_df[new_col].apply(
                        lambda x: normalize_category(x, orig_col, strict_mode=True)
                    )
                else:
                    # Mode lenient : garder les valeurs telles quelles (juste trim/capitalize)
                    self.cleaned_df[new_col] = self.cleaned_df[new_col].apply(
                        lambda x: normalize_category(x, orig_col, strict_mode=False)
                    )
                
                unique_after = self.cleaned_df[new_col].nunique()
                col_anomalies.append(f"Normalisation categorielle ({unique_before} -> {unique_after} valeurs uniques)")
                print(f"  [OK] {new_col}: normalisation categorielle ({unique_before} -> {unique_after})")
            
            if col_anomalies:
                self.anomalies_log[new_col] = col_anomalies
        
        print("[OK] Nettoyage terminé")
    
    def _detect_outliers(self, series: pd.Series, threshold: float = 1.5) -> List[Any]:
        """Détecte les outliers avec la méthode IQR."""
        numeric_series = pd.to_numeric(series, errors='coerce')
        if numeric_series.isna().all():
            return []
        
        Q1 = numeric_series.quantile(0.25)
        Q3 = numeric_series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)].dropna().tolist()
        return outliers[:5]  # Retourner max 5
    
    def _save_proposals_checkpoint(self):
        """Sauvegarde les proposals comme checkpoint pour pouvoir les recharger."""
        checkpoint_file = Path("proposals_checkpoint.json")
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.proposals, f, indent=2, ensure_ascii=False)
        print(f"[CHECKPOINT] Proposals sauvegardées dans {checkpoint_file}")

    def generate_strategic_questions(self) -> List[str]:
        print("\n[GÉNÉRATION DE QUESTIONS STRATÉGIQUES - AVEC UTILITÉ]")
        print("=" * 70)

        # Construction de la liste des colonnes renommées avec leur type
        col_lines = []
        for orig, new in self.renaming_map.items():
            dtype = self.column_types.get(orig, 'text')
            col_lines.append(f"- {new} ({dtype})")
        cols_text = "\n".join(col_lines)

        # Prompt qui impose le format "question + utilité"
        prompt = f"""Voici les colonnes d'un dataset après nettoyage :

{cols_text}

Génère 10 questions stratégiques que la direction devrait se poser, en utilisant UNIQUEMENT ces colonnes.
Pour chaque question, ajoute une ligne "Utilité :" qui explique en une phrase courte l’intérêt métier de cette question (gain, anticipation, pilotage…).

Format attendu pour chaque question :
1. [Question précise et actionnable]
Utilité : [Explication de l’utilité]

Ne donne aucun texte avant ou après la liste. Ne mets pas d’exemples génériques, adapte-toi aux colonnes fournies.
"""

        response = self.api_client.chat(prompt)
        if response:
            lines = response.strip().split('\n')
            # On garde toutes les lignes, mais on s'assure qu'elles commencent par un chiffre ou "Utilité"
            questions_with_utility = []
            for line in lines:
                line = line.strip()
                if re.match(r'^\d+\.', line) or line.startswith('Utilité :'):
                    questions_with_utility.append(line)
            if questions_with_utility:
                print("\n".join(questions_with_utility))
                return questions_with_utility

        print("[ERREUR] L'API n'a pas renvoyé de questions valides.")
        return []

    def save_results(self, output_dir: str = None):
        if output_dir is None:
            output_dir = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_path = Path(output_dir)
        out_path.mkdir(exist_ok=True)

        # 1. Données nettoyées
        clean_csv = out_path / "donnees_nettoyees.csv"

        # 2. Mapping des renommages
        mapping_file = out_path / "renaming_map.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.renaming_map, f, indent=2, ensure_ascii=False)
        print(f"[SAUVEGARDE] Mapping : {mapping_file}")
        
        # 3. Proposals (IA analysis)
        proposals_file = out_path / "proposals.json"
        with open(proposals_file, 'w', encoding='utf-8') as f:
            json.dump(self.proposals, f, indent=2, ensure_ascii=False)
        print(f"[SAUVEGARDE] Proposals IA : {proposals_file}")

        # 4. Questions stratégiques
        questions_file = out_path / "questions_strategiques.txt"
        with open(questions_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.questions))
        print(f"[SAUVEGARDE] Questions : {questions_file}")
        
        # 5. Rapport complet des anomalies et corrections
        if hasattr(self, 'anomalies_log') and self.anomalies_log:
            anomalies_file = out_path / "anomalies_log.json"
            with open(anomalies_file, 'w', encoding='utf-8') as f:
                json.dump(self.anomalies_log, f, indent=2, ensure_ascii=False)
            print(f"[SAUVEGARDE] Rapport anomalies : {anomalies_file}")
        
        # 6. Résumé
        summary_file = out_path / "RESUME.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("RÉSUMÉ DE L'ANALYSE ET DU NETTOYAGE\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Fichier d'entrée : {self.input_path.name}\n")
            f.write(f"Lignes : {len(self.df)} -> {len(self.cleaned_df)}\n")
            f.write(f"Colonnes : {len(self.df.columns)}\n\n")
            f.write("RENOMMAGES EFFECTUÉS:\n")
            for old, new in self.renaming_map.items():
                f.write(f"  {old} -> {new}\n")
            f.write("\n" + "=" * 70 + "\n")
        print(f"[SAUVEGARDE] Résumé : {summary_file}")

    def run(self):
        print("\n" + "=" * 70)
        print("AGENT IA UNIVERSEL - Analyse de données brutes (Groq)")
        print("=" * 70)
        
        # Charger les corrections personnalisées
        load_custom_corrections()
        
        if not self.load_data():
            return False
        
        self.propose_renaming()
        
        if self.fix_all_mode:
            # Mode fix-all : accepter tout automatiquement
            print("\n[MODE FIXALL] Acceptation automatique de toutes les corrections...")
            for orig_col, new_col in self.proposals.items():
                info = self.proposals[orig_col]
                self.renaming_map[orig_col] = info.get('proposed_name', orig_col)
                self.column_types[orig_col] = info.get('data_type', 'text')
        else:
            # Mode normal avec validation
            self.interactive_validation()
        
        self.apply_cleaning()
        self.questions = self.generate_strategic_questions()
        self.save_results()
        print("\n[SUCCÈS] Pipeline terminé.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Agent IA universel pour analyser et nettoyer n'importe quel CSV avec Groq (gratuit)",
        epilog="""
EXEMPLES D'UTILISATION:
  python agent_groq.py --input data.csv
  python agent_groq.py --input data.csv --auto
  python agent_groq.py --input data.csv --fix-all
  python agent_groq.py --input data.csv --api-key VOTRE_CLE_GROQ
  
AVEC VARIABLE D'ENVIRONNEMENT:
  $env:GROQ_API_KEY='votre_cle'; python agent_groq.py --input data.csv

AMÉLIORATIONS V2:
  [x] Analyse de toutes les colonnes en 1 appel API (30x plus rapide)
  [x] Mode --fix-all pour correction automatique complete
  [x] Detection des outliers (methode IQR)
  [x] Rapport complet des anomalies
  [x] Support des corrections personnalisees (corrections.json)
  [x] Meilleure gestion des separateurs CSV
  [x] Checkpoints pour recharger les proposals
        """
    )
    parser.add_argument("--input", required=True, help="Chemin du fichier CSV d'entrée")
    parser.add_argument("--api-key", help="Clé API Groq (ou variable d'environnement GROQ_API_KEY)")
    parser.add_argument("--auto", action="store_true", help="Mode automatique (accepte confiance > 70%)")
    parser.add_argument("--fix-all", action="store_true", help="Corrige automatiquement TOUT sans interaction utilisateur")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modèle Groq (défaut: {DEFAULT_MODEL})")
    args = parser.parse_args()

    try:
        agent = AgentIAUniversel(
            args.input, 
            args.api_key, 
            auto_mode=args.auto, 
            fix_all_mode=args.fix_all, 
            model=args.model
        )
        agent.run()
    except FileNotFoundError as e:
        print(f"\n[ERREUR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERREUR FATALE] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()