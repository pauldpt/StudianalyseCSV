# Analyse CSV + Web Scraper (Flask)

Application web en francais pour:
- charger et verifier des CSV,
- nettoyer les donnees,
- analyser automatiquement les donnees,
- generer des graphiques et un rapport,
- scraper des tableaux HTML depuis une URL.

## 1) Installation

Prerequis:
- Python 3.10+

Commandes:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2) Lancer l'application web

```powershell
python web_app.py
```

Puis ouvrir:
- http://127.0.0.1:5000

## 3) Utilisation rapide

1. Importer un CSV (ou charger un fichier scrape).
2. Verifier les colonnes et suggestions de renommage.
3. Nettoyer les donnees.
4. Lancer l'analyse automatique.
5. Generer le rapport.
6. (Optionnel) Utiliser l'onglet Web Scraper pour extraire un tableau depuis une URL.

## 4) Configuration API (optionnel)

Si vous utilisez des fonctions IA qui necessitent une cle API:
- dupliquez `secrets.example.toml` en `secrets.toml`
- renseignez votre cle

Ne poussez jamais `secrets.toml` sur GitHub.

## 5) Fichiers importants

- `web_app.py`: API Flask + orchestration pipeline
- `web_scraper.py`: extraction de tableaux web
- `core_analysis.py`: coeur d'analyse
- `graphiques.py`: generation des graphiques
- `rapport_generator.py`: generation de rapport
- `index.html`: interface web

## 6) Notes

- Les dossiers `output_*` et `scraped_data/` sont generes a l'execution.
- Le fichier `secrets.toml` est ignore par git.
