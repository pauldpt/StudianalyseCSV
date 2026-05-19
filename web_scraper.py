"""
Web Scraper pour extraire des tableaux HTML depuis n'importe quel site
Transforme les données en CSV exploitable
"""

import io
import pandas as pd
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class WebScraper:
    """Scrape des tableaux HTML depuis une URL et les retourne en DataFrame"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.last_scraped_df = None
        self.last_url = None
        
    def scrape_tables(self, url: str) -> List[pd.DataFrame]:
        """
        Scrape tous les tableaux HTML d'une URL.
        Retourne une liste de DataFrames.
        """
        if not BEAUTIFULSOUP_AVAILABLE:
            raise ImportError("BeautifulSoup4 requiert: pip install beautifulsoup4")
        
        try:
            print(f"[SCRAPE] Récupération de {url}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            print(f"[OK] Réponse reçue ({len(response.text)} caractères)")
            
            # Extraire tous les tableaux
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            print(f"[FOUND] {len(tables)} tableau(x) détecté(s)")
            
            if not tables:
                print("[WARN] Aucun tableau <table> trouvé. Essai avec pandas.read_html()...")
                try:
                    dfs = pd.read_html(url)
                    print(f"[OK] Pandas a trouvé {len(dfs)} tableau(x)")
                    return dfs
                except:
                    return []
            
            dataframes = []
            for i, table in enumerate(tables, 1):
                try:
                    df = pd.read_html(io.StringIO(str(table)))[0]
                    
                    # Nettoyage basique
                    df.columns = [str(col).strip() for col in df.columns]
                    df = df.dropna(how='all')  # Supprimer les lignes vides
                    
                    if len(df) > 0:
                        print(f"[TABLE {i}] {len(df)} lignes × {len(df.columns)} colonnes")
                        dataframes.append(df)
                except Exception as e:
                    print(f"[WARN] Tableau {i} non parsable: {e}")
                    continue
            
            return dataframes
        
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Erreur réseau: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Erreur scraping: {e}")
            return []
    
    def scrape_best_table(self, url: str) -> Optional[pd.DataFrame]:
        """
        Scrape une URL et retourne le PLUS GRAND tableau trouvé.
        Idéal pour avoir directement le résultat utile.
        """
        tables = self.scrape_tables(url)
        
        if not tables:
            return None
        
        # Retourner le plus grand tableau
        best_df = max(tables, key=lambda df: len(df) * len(df.columns))
        self.last_scraped_df = best_df
        self.last_url = url
        
        print(f"[BEST] Plus grand tableau: {len(best_df)} × {len(best_df.columns)}")
        return best_df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: Optional[str] = None) -> str:
        """Sauvegarde le DataFrame en CSV"""
        if output_path is None:
            output_path = f"scraped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
        print(f"[SAVE] Données sauvegardées: {output_path}")
        
        return output_path
    
    def get_table_stats(self, df: pd.DataFrame) -> Dict:
        """Retourne des stats sur le tableau"""
        return {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'missing_percent': float((df.isna().sum().sum() / (len(df) * len(df.columns)) * 100).round(2)),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }


# Test rapide
if __name__ == "__main__":
    scraper = WebScraper()
    
    # Test avec Wikipedia (tableau des communes)
    test_url = "https://fr.wikipedia.org/wiki/Communes_de_France"
    print(f"\nTest: {test_url}\n")
    
    df = scraper.scrape_best_table(test_url)
    if df is not None:
        print("\nStats:")
        stats = scraper.get_table_stats(df)
        print(f"  Lignes: {stats['rows']}")
        print(f"  Colonnes: {stats['columns']}")
        print(f"  Valeurs manquantes: {stats['missing_percent']:.1f}%")
        print(f"\nAperçu:")
        print(df.head())
        
        # Sauvegarder
        csv_path = scraper.save_to_csv(df)
        print(f"\nFichier créé: {csv_path}")
