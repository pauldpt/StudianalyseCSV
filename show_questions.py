#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from core_analysis import CSVAnalyzer, CONTEXTE_THEMES

# Lister les thèmes disponibles
print("\n=== THÈMES DISPONIBLES ===")
for theme_key, theme_info in CONTEXTE_THEMES.items():
    print(f"  - {theme_key}: {theme_info['name']}")

# Récupérer le thème (argument CLI ou défaut)
theme = sys.argv[1] if len(sys.argv) > 1 else "accidents"
print(f"\n[THÈME SÉLECTIONNÉ] {theme}")

a = CSVAnalyzer('temp_carcteristiques-2021.csv')
a.load_data()
a.analyze_columns()
a.clean_data()
q = a.generate_strategic_questions_and_graphs(contexte_metier=theme)

print("\n=== QUESTIONS GÉNÉRÉES ===\n")
for i, question in enumerate(q, 1):
    print(f"{i}. {question['question']}")
    print(f"   Colonnes: {question['colonnes']}")
    print(f"   Graphique: {question['type_graphique']}")
    print(f"   Utilité: {question['utilite']}")
    print()
