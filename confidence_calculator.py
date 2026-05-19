"""
Calculateur de confiance pour les questions et analyses
Évalue la qualité/solidité d'une question basée sur les données
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class ConfidenceCalculator:
    """Calcule les scores de confiance pour les questions et graphiques"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows = len(df)
        
    def calculate_column_confidence(self, col: str) -> float:
        """
        Calcule la confiance d'une colonne basée sur :
        - Complétude (% de valeurs non-nulles)
        - Variabilité (entropy pour catégories, variance pour numériques)
        """
        if col not in self.df.columns:
            return 0.0
        
        series = self.df[col]
        
        # Complétude (0 à 0.5)
        missing_ratio = series.isna().sum() / self.total_rows
        completeness_score = max(0, 1 - missing_ratio) * 0.5
        
        # Variabilité (0 à 0.5)
        if series.dtype in ['object', 'category']:
            # Catégorique: plus il y a de variété, mieux c'est
            unique_ratio = series.nunique() / max(1, self.total_rows * 0.1)
            unique_ratio = min(1, unique_ratio)
            variability_score = unique_ratio * 0.5
        else:
            # Numérique: variance normalisée
            try:
                numeric_series = pd.to_numeric(series, errors='coerce')
                mean_val = numeric_series.mean()
                if mean_val != 0:
                    cv = numeric_series.std() / abs(mean_val)  # Coefficient of variation
                    cv = min(cv, 2)  # Cap à 2
                    variability_score = (cv / 2) * 0.5
                else:
                    variability_score = 0.3
            except:
                variability_score = 0.3
        
        confidence = completeness_score + variability_score
        return min(1.0, confidence)
    
    def calculate_question_confidence(self, columns: List[str], 
                                      question_type: str = 'general') -> Dict:
        """
        Calcule la confiance d'une question basée sur ses colonnes
        
        Returns: {
            'overall': float (0-1),
            'completeness': float,
            'variability': float,
            'data_quality': string,
            'recommendation': string
        }
        """
        if not columns:
            return {
                'overall': 0.0,
                'completeness': 0.0,
                'variability': 0.0,
                'data_quality': 'Aucune colonne',
                'recommendation': 'Sélectionnez des colonnes valides'
            }
        
        # Vérifier que les colonnes existent
        valid_cols = [c for c in columns if c in self.df.columns]
        if not valid_cols:
            return {
                'overall': 0.0,
                'completeness': 0.0,
                'variability': 0.0,
                'data_quality': 'Colonnes non trouvées',
                'recommendation': 'Les colonnes ne sont pas dans le dataset'
            }
        
        # Calculer la confiance pour chaque colonne
        col_confidences = [self.calculate_column_confidence(c) for c in valid_cols]
        avg_col_confidence = np.mean(col_confidences)
        
        # Bonus/pénalité selon le nombre de colonnes
        if len(valid_cols) == 1:
            # Une seule colonne: ok pour distribution
            bonus = 0
        elif len(valid_cols) == 2:
            # Deux colonnes: comparaison, bon pour corrélation
            bonus = 0.05
        else:
            # Plusieurs colonnes: plus complexe, pénalité
            bonus = -0.1
        
        overall_confidence = min(1.0, avg_col_confidence + bonus)
        
        # Évaluation qualitative
        if overall_confidence >= 0.85:
            quality = 'Excellente ✓'
            recommendation = 'Confiance élevée - Résultats fiables'
        elif overall_confidence >= 0.70:
            quality = 'Bonne ✓'
            recommendation = 'Résultats exploitables'
        elif overall_confidence >= 0.55:
            quality = 'Moyenne ⚠️'
            recommendation = 'À valider - Données partielles'
        elif overall_confidence >= 0.40:
            quality = 'Faible ⚠️'
            recommendation = 'Attention - Données incomplètes'
        else:
            quality = 'Très faible ❌'
            recommendation = 'Non recommandé - Trop de données manquantes'
        
        # Calculer les sous-scores
        completeness = np.mean([
            1 - (self.df[c].isna().sum() / self.total_rows) 
            for c in valid_cols
        ])
        variability = np.mean([
            (self.df[c].nunique() / self.total_rows) if self.df[c].dtype in ['object', 'category']
            else min(1, (self.df[c].std() / (self.df[c].mean() + 1e-6)))
            for c in valid_cols
        ])
        
        return {
            'overall': round(overall_confidence, 2),
            'completeness': round(completeness, 2),
            'variability': round(variability, 2),
            'data_quality': quality,
            'recommendation': recommendation,
            'columns_checked': valid_cols,
            'columns_missing': [c for c in columns if c not in self.df.columns]
        }
    
    def get_confidence_icon(self, score: float) -> str:
        """Retourne un indicateur visuel basé sur le score"""
        if score >= 0.85:
            return '█████'  # Excellent
        elif score >= 0.70:
            return '████░'  # Bon
        elif score >= 0.55:
            return '███░░'  # Moyen
        else:
            return '██░░░'  # Faible
    
    def calculate_graph_confidence(self, col1: str, col2: Optional[str] = None) -> float:
        """Calcule la confiance d'un graphique basé sur ses colonnes"""
        cols = [col1]
        if col2:
            cols.append(col2)
        
        result = self.calculate_question_confidence(cols)
        return result['overall']
    
    def get_all_columns_confidence(self) -> Dict[str, Dict]:
        """Retourne la confiance pour TOUTES les colonnes"""
        result = {}
        for col in self.df.columns:
            score = self.calculate_column_confidence(col)
            result[col] = {
                'confidence': round(score, 2),
                'icon': self.get_confidence_icon(score),
                'completeness': round(1 - (self.df[col].isna().sum() / self.total_rows), 2),
                'unique_values': int(self.df[col].nunique()),
                'dtype': str(self.df[col].dtype)
            }
        return result


# Test rapide
if __name__ == "__main__":
    # Créer un petit DataFrame de test
    test_data = {
        'age': [25, 30, 35, None, 40],
        'nom': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'score': [85.5, 90.0, None, 78.5, 92.0]
    }
    df = pd.DataFrame(test_data)
    
    calc = ConfidenceCalculator(df)
    
    print("=== TEST CONFIANCE ===\n")
    
    print("Confiance par colonne:")
    all_conf = calc.get_all_columns_confidence()
    for col, stats in all_conf.items():
        print(f"  {col}: {stats['icon']} {stats['confidence']:.0%}")
    
    print("\nConfiance pour une question:")
    q_conf = calc.calculate_question_confidence(['age', 'score'])
    print(f"  Score global: {q_conf['overall']:.0%}")
    print(f"  Qualité: {q_conf['data_quality']}")
    print(f"  Recommandation: {q_conf['recommendation']}")
