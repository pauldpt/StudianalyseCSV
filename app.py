#!/usr/bin/env python3
"""
Application d'analyse CSV - Interface épurée et légère
Remplace Streamlit par une solution plus simple et efficace
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from core_analysis import CSVAnalyzer
from graphiques import GraphicsGenerator
from rapport_generator import RapportGenerator


class CSVApp:
    """Application d'analyse de CSV"""
    
    def __init__(self):
        self.analyzer = None
        self.output_dir = None
        self.api_key = self._get_api_key()
        self.state = {}
    
    def _get_api_key(self):
        """Récupère la clé API depuis l'environnement ou secrets.toml"""
        api_key = os.environ.get("GROQ_API_KEY")
        
        if not api_key:
            secrets_path = Path(".") / "secrets.toml"
            if secrets_path.exists():
                try:
                    with open(secrets_path, 'r') as f:
                        for line in f:
                            if 'GROQ_API_KEY' in line:
                                api_key = line.split('=')[1].strip().strip('"')
                                break
                except:
                    pass
        
        return api_key
    
    def clear_screen(self):
        """Efface l'écran"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title, icon=""):
        """Affiche un titre formaté"""
        print(f"\n{'='*70}")
        print(f"  {icon} {title}".center(70))
        print(f"{'='*70}\n")
    
    def print_info(self, message):
        """Affiche une info"""
        print(f"  ℹ️  {message}")
    
    def print_success(self, message):
        """Affiche un succès"""
        print(f"  ✅ {message}")
    
    def print_error(self, message):
        """Affiche une erreur"""
        print(f"  ❌ {message}")
    
    def print_warning(self, message):
        """Affiche un avertissement"""
        print(f"  ⚠️  {message}")
    
    def print_step(self, step, total, message):
        """Affiche une étape en cours"""
        print(f"  [{step}/{total}] {message}")
    
    def show_menu(self, title, options):
        """Affiche un menu et retourne le choix"""
        self.print_header(title, "📋")
        
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        
        print()
        while True:
            try:
                choice = input("  Votre choix: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(options):
                    return int(choice)
                else:
                    self.print_error(f"Veuillez entrer un nombre entre 1 et {len(options)}")
            except KeyboardInterrupt:
                print("\n  Interruption utilisateur.\n")
                sys.exit(0)
    
    def select_csv(self):
        """Sélectionne un fichier CSV"""
        self.print_header("Sélectionner un fichier CSV", "📁")
        
        csv_files = sorted(set(list(Path(".").glob("*.csv")) + list(Path(".").glob("temp_*.csv"))))
        
        if not csv_files:
            self.print_error("Aucun fichier CSV trouvé")
            return None
        
        print("  Fichiers disponibles:\n")
        for i, f in enumerate(csv_files, 1):
            try:
                size = f.stat().st_size / 1024 / 1024
                print(f"  {i:2}. {f.name:40} ({size:7.2f} MB)")
            except:
                print(f"  {i:2}. {f.name:40}")
        
        print(f"  {len(csv_files)+1:2}. Entrer le chemin manuellement")
        print()
        
        choice = input("  Choix: ").strip()
        
        if choice.isdigit():
            choice = int(choice)
            if 1 <= choice <= len(csv_files):
                return str(csv_files[choice - 1])
            elif choice == len(csv_files) + 1:
                return input("  Chemin du fichier: ").strip()
        
        return None
    
    def load_csv(self):
        """Charge un CSV"""
        csv_file = self.select_csv()
        
        if not csv_file or not Path(csv_file).exists():
            self.print_error(f"Fichier non trouvé: {csv_file}")
            return False
        
        self.print_header("Analyse du CSV", "🔍")
        
        try:
            self.analyzer = CSVAnalyzer(csv_file, api_key=self.api_key)
            
            if not self.analyzer.load_data():
                self.print_error("Erreur lors du chargement du CSV")
                return False
            
            self.output_dir = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            Path(self.output_dir).mkdir(exist_ok=True)
            
            self.print_success(f"Fichier chargé: {len(self.analyzer.df)} lignes × {len(self.analyzer.df.columns)} colonnes")
            print(f"  Répertoire: {self.output_dir}\n")
            
            print("  ⏳ Analyse des colonnes par IA...\n")
            proposals = self.analyzer.analyze_columns()
            
            self.print_success(f"Analyse terminée ({len(proposals)} colonnes)\n")
            
            print("  Résultats:\n")
            for col, prop in proposals.items():
                col_type = prop.get('type', '?')
                conf = prop.get('confidence', 0)
                desc = prop.get('description', col)
                print(f"    • {col:25} → {desc:30} ({col_type:10}, {conf}%)")
            
            self.state['loaded'] = True
            return True
            
        except Exception as e:
            self.print_error(f"{e}")
            return False
    
    def clean_data(self):
        """Nettoie les données"""
        if not self.state.get('loaded'):
            self.print_error("Veuillez d'abord charger un CSV")
            return False
        
        self.print_header("Nettoyage des données", "🧹")
        
        try:
            print("  ⏳ Nettoyage en cours...\n")
            self.analyzer.clean_data()
            
            rows_before = len(self.analyzer.df)
            rows_after = len(self.analyzer.cleaned_df)
            nulls_before = self.analyzer.df.isna().sum().sum()
            nulls_after = self.analyzer.cleaned_df.isna().sum().sum()
            
            self.print_success("Nettoyage terminé\n")
            
            print("  Statistiques:")
            print(f"    • Lignes: {rows_before} → {rows_after}")
            print(f"    • Valeurs nulles: {nulls_before} → {nulls_after}")
            if nulls_before > 0:
                reduction = 100 * (nulls_before - nulls_after) / nulls_before
                print(f"    • Réduction: {reduction:.1f}%")
            
            self.state['cleaned'] = True
            return True
            
        except Exception as e:
            self.print_error(f"{e}")
            return False
    
    def generate_analysis(self):
        """Génère les questions et graphiques"""
        if not self.state.get('cleaned'):
            self.print_error("Veuillez d'abord nettoyer les données")
            return False
        
        self.print_header("Génération de l'analyse", "💡")
        
        try:
            print("  ⏳ Génération des questions...\n")
            questions, graphs = self.analyzer.generate_strategic_questions_and_graphs()
            
            self.print_success(f"{len(questions)} questions générées\n")
            
            print("  Questions stratégiques:")
            for i, q in enumerate(questions, 1):
                question = q.get('question', q.get('text', 'Question'))
                print(f"    {i}. {question}")
                if q.get('utilite'):
                    print(f"       └─ {q.get('utilite')}")
            
            print(f"\n  📈 {len(graphs)} graphiques générés")
            
            self.state['analyzed'] = True
            return True
            
        except Exception as e:
            self.print_error(f"{e}")
            return False
    
    def export_data(self):
        """Exporte les données"""
        if not self.state.get('cleaned'):
            self.print_error("Veuillez d'abord nettoyer les données")
            return False
        
        self.print_header("Export des données", "💾")
        
        try:
            output_path = Path(self.output_dir) / "donnees_nettoyees.csv"
            self.analyzer.cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
            
            size = output_path.stat().st_size / 1024
            self.print_success(f"Données exportées: {output_path}")
            print(f"  Taille: {size:.2f} KB")
            
            return True
            
        except Exception as e:
            self.print_error(f"{e}")
            return False
    
    def generate_report(self):
        """Génère le rapport"""
        if not self.state.get('analyzed'):
            self.print_error("Veuillez d'abord générer l'analyse")
            return False
        
        self.print_header("Génération du rapport", "📄")
        
        try:
            print("  ⏳ Génération en cours...\n")
            
            rapport = RapportGenerator(self.analyzer.cleaned_df, self.output_dir)
            rapport_path = rapport.generate()
            
            if rapport_path and Path(rapport_path).exists():
                self.print_success(f"Rapport généré: {rapport_path}")
            else:
                self.print_warning("Rapport généré mais fichier non trouvé")
            
            return True
            
        except Exception as e:
            self.print_error(f"{e}")
            return False
    
    def show_summary(self):
        """Affiche un résumé de l'analyse"""
        if not self.state.get('loaded'):
            self.print_error("Aucun fichier chargé")
            return
        
        self.print_header("Résumé de l'analyse", "📊")
        
        print(f"  Fichier: {self.analyzer.filepath}")
        print(f"  Lignes: {len(self.analyzer.df)}")
        print(f"  Colonnes: {len(self.analyzer.df.columns)}")
        print(f"  Répertoire de sortie: {self.output_dir}\n")
        
        if self.state.get('cleaned'):
            nulls = self.analyzer.cleaned_df.isna().sum().sum()
            print(f"  ✅ Données nettoyées")
            print(f"  Valeurs nulles restantes: {nulls}\n")
        
        if self.state.get('analyzed'):
            print(f"  ✅ Analyse générée")
        
        print()
    
    def run(self):
        """Boucle principale"""
        if not self.api_key:
            self.print_header("Configuration", "⚙️")
            self.print_error("Clé API Groq non trouvée")
            print("\n  Options:")
            print("    1. Variable d'environnement GROQ_API_KEY")
            print("    2. Fichier secrets.toml")
            print("    3. Fichier .env\n")
            return
        
        while True:
            self.clear_screen()
            print("\n" + "="*70)
            print("  🚀 ANALYSE DE DONNÉES CSV - Interface épurée".center(70))
            print("="*70)
            
            self.show_summary()
            
            options = [
                "Charger un CSV",
                "Nettoyer les données",
                "Générer l'analyse",
                "Exporter les données",
                "Générer le rapport",
                "Quitter"
            ]
            
            choice = self.show_menu("Menu principal", options)
            
            if choice == 1:
                self.load_csv()
            elif choice == 2:
                self.clean_data()
            elif choice == 3:
                self.generate_analysis()
            elif choice == 4:
                self.export_data()
            elif choice == 5:
                self.generate_report()
            elif choice == 6:
                print("\n  👋 Aurevoir!\n")
                break
            
            input("\n  Appuyez sur ENTER pour continuer...")


def main():
    """Point d'entrée"""
    try:
        app = CSVApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n  ⚠️ Interruption utilisateur\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ❌ Erreur: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
