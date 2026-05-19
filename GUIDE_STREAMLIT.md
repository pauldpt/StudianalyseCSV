#  StudianalyseCSV v2.0
**Analyse et nettoyage CSV avec intelligence artificielle - Interface web + Rapports professionnels**

---

##  Table des matieres
1. [Installation](#installation)
2. [Architecture](#architecture)
3. [Usage](#usage)
4. [Fonctionnalites](#fonctionnalites)
5. [Configuration](#configuration)
6. [FAQ](#faq)

---

##  Installation

### Prerequis
- Python 3.10+
- Cle API Groq (https://console.groq.com)

### Etapes

1. **Cloner/telecharger le projet**
```bash
cd "mise en place projet py"
```

2. **Installer les dependances**
```bash
pip install -r requirements.txt
```

3. **Configurer la cle API**

**Option A - Variable d'environnement (recommande)**:
```powershell
# Windows PowerShell
$env:GROQ_API_KEY="votre_cle_api_ici"
```

**Option B - Fichier secrets Streamlit**:
```bash
# Creer .streamlit/secrets.toml avec votre cle
echo 'GROQ_API_KEY = "votre_cle_api_ici"' > .streamlit/secrets.toml
```

**Option C - Input manuel** dans l'app Streamlit

---

##  Architecture

### Modules Python

```
projet/
 core_analysis.py          # Logique metier (CSV, IA, nettoyage)
 graphiques.py             # Generation de graphiques Plotly
 rapport_generator.py      # Rapports HTML/PDF professionnels
 streamlit_app.py          # Interface web interactive
 agent_groq.py             # [ANCIEN] CLI originelle (conserve)
 corrections.json          # Dictionnaire personnalise
 requirements.txt          # Dependances Python
 README_STREAMLIT.md       # Ce guide
 .streamlit/
     config.toml           # Config Streamlit
     secrets.toml          # Secrets (API key)
```

### Flux de donnees

```
CSV -> Charger -> Analyser (IA) -> Propositions -> Valider -> Nettoyer -> Graphiques -> Rapport
```

### Classes principales

#### `CSVAnalyzer` (core_analysis.py)
- Charge CSV avec detection auto (encodage, separateur)
- Analyse colonnes via IA (1 appel API pour N colonnes)
- Nettoie donnees selon types detectes
- Sauvegarde resultats

#### `GraphicsGenerator` (graphiques.py)
- Distribution (histogramme + KDE)
- Boxplot (detection outliers IQR)
- Categories (barres, pie charts)
- Correlation (heatmap)
- Timeseries (tendances)
- Scatter plots + regression

#### `RapportGenerator` (rapport_generator.py)
- Template HTML professionnel (CSS embarque)
- Export PDF via WeasyPrint
- Metadata JSON
- Design premium (gradient, cards, tables)

---

##  Usage

### Option 1: Interface Web Streamlit (RECOMMANDEE)

```bash
streamlit run streamlit_app.py
```

Puis ouvrir http://localhost:8501

**Workflow:**
1. Upload CSV ou entrer chemin fichier
2. Previsualize les donnees
3. Lancer analyse IA
4. Verifier et editer propositions
5. Lancer nettoyage automatique
6. Generer rapports (HTML/PDF)
7. Telecharger fichiers

**Avantages:**
-  Interface intuitive (no CLI)
-  Preview avant/apres en temps reel
-  Editeur de mapping interactif
-  Rapports generes localement
-  Telecharge fichiers directement

### Option 2: CLI Classique

```bash
# Mode interactif (approuver chaque correction)
python agent_groq.py --input data.csv

# Mode automatique (> 70% confiance)
python agent_groq.py --input data.csv --auto

# Mode fix-all (accepter tout)
python agent_groq.py --input data.csv --fix-all
```

---

##  Fonctionnalites principales

### 1. Analyse IA (1 appel = N colonnes)

**Ce que fait l'IA:**
- Propose nom francais pour chaque colonne
- Detecte type de donnee (text, number, date, category, id)
- Identifie anomalies (valeurs manquantes, formats, outliers)
- Estime confiance par colonne (0.0 - 1.0)

**Exemple de proposition:**
```json
{
  "ID Client": {
    "proposed_name": "identifiant_client",
    "data_type": "id",
    "confidence": 0.95,
    "anomalies": []
  },
  "Montant ": {
    "proposed_name": "montant",
    "data_type": "number",
    "confidence": 0.88,
    "anomalies": ["2 valeurs manquantes", "1 format bizare"]
  }
}
```

### 2. Graphiques interactifs (Plotly + Design pro)

Generes automatiquement pour chaque CSV:

 **Distribution numeriques**
- Histogramme + KDE
- Lignes pour moyenne/mediane
- Interactive (zoom, hover, export PNG)

 **Boxplots**
- Detecte outliers (methode IQR)
- Surligne aberrantes en rouge
- Affiche statistiques descriptives

 **Categories**
- Bar charts et pie charts
- Pourcentages au hover
- Top N valeurs

 **Correlations**
- Heatmap interactive
- Valeurs numeriques
- Color scale -1 a +1

 **Timeseries**
- Si colonne date existe
- Regression lineaire
- Trends temporelles

**Design Premium:**
- Palette Material Design
- Interactivite Plotly (zoom, pan, export)
- Export PNG/SVG integre
- Responsive (mobile-friendly)
- Auto-light/dark mode

### 3. Rapport HTML professionnel

**Structure:**
-  Page de garde (design gradient violet/rose)
-  Resume technique (nb lignes, colonnes, anomalies)
-  Mapping applique (table avec confiance)
-  Questions strategiques (generees par IA)
-  Journal anomalies (problemes detectes)
-  Galerie graphiques (preview + liens)
-  Recommandations

**Design:**
- Material Design (modern, pro, 2024)
- Responsive (mobile + desktop + print)
- Print-ready et paginee
- CSS embarque (standalone, pas de CDN)
- Accessible (WCAG AA)

**Export PDF:**
- WeasyPrint pour qualite maximale
- Preserves formatting CSS
- Images integrees
- ~3-5 secondes pour generer (~20 pages)

### 4. Nettoyage de donnees

**Nombres:**
- Parse formats francais (1 234,56) et anglo-saxons (1,234.56)
- Supprime symboles (, $, %)
- Convertit en float avec precision

**Dates:**
- Detecte 10+ formats (DD/MM/YYYY, YYYY-MM-DD, DD.MM.YYYY, etc.)
- Normalise ISO 8601 (YYYY-MM-DD)
- Valide dates
- Recupere valeurs partielles

**Categories:**
- Fuzzy matching (rapidfuzz, 80% threshold)
- Normalise variants (accentuation, casse)
- Applique corrections.json personnalise
- Preserve ordre frequence

**Outliers:**
- IQR method (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
- Detection et log
- Visualisation Plotly
- Preserve dans CSV nettoye

---

##  Configuration

### Fichier `.streamlit/secrets.toml`

```toml
# API Groq (SECURITE: pas dans git!)
GROQ_API_KEY = "gsk_..."

# Modele IA
GROQ_MODEL = "llama-3.3-70b-versatile"

# Seuils confiance
CONFIDENCE_AUTO_THRESHOLD = 0.7
CONFIDENCE_FIX_ALL_THRESHOLD = 0.5

# Rapports
OUTPUT_FORMAT = "html"  # html, pdf, both
GENERATE_GRAPHS = true
GRAPH_STYLE = "plotly"
```

### Personnaliser corrections.json

**Format:**
```json
{
  "statut": {
    "termine": "Termin",
    "fin": "Termin",
    "complete": "Termin",
    "abandonne": "Abandonn",
    "annule": "Abandonn"
  },
  "financeur": {
    "cpf": "CPF",
    "region": "Rgion",
    "france travail": "France Travail",
    "opco": "OPCO"
  }
}
```

**Comment ajouter:**
1. Editer `corrections.json`
2. Format: `"variante_en_minuscules": "Valeur_Canonique"`
3. Dechargement automatique au demarrage

---

##  Examples de sortie

### Fichiers generes

Apres execution, dossier `output_YYYYMMDD_HHMMSS/`:

```
output_20260413_114542/
 donnees_nettoyees.csv           # CSV nettoye
 renaming_map.json               # Mapping colonnes
 proposals.json                  # Propositions IA
 anomalies_log.json              # Transformations effectuees
 rapport.html                    # Rapport interactif (20-30 pages)
 rapport.pdf                     # Rapport imprimable
 graph_01_distribution_*.html    # Graphiques Plotly interactifs
 graph_02_boxplot_*.html         # Outliers detection
 graph_03_categories_*.html      # Distribution categories
 graph_04_correlations.html      # Heatmap correlations
 graph_05_timeseries_*.html      # Tendances temporelles
 graph_06_scatter_*.html         # Scatter plots
 graph_07_pie_*.html             # Pie charts composition
 graph_08_statistics_summary.html # Dashboard stats
 RESUME.txt                      # Execution summary
```

---

##  Modes d'execution

| Mode | Seuil Confiance | Usage |
|------|-----------------|-------|
| **Interactif** | Manual | Approuver chaque proposition |
| **Auto** | 70%+ | Accepter automatiquement si confiance > 70% |
| **Fix-all** | 0%+ | Accepter TOUT (a utiliser avec precaution) |

**Recommandation:**
1. Premiere fois: **Interactif** (verifier qualite)
2. Production: **Auto** (bon equilibre rapidite/securite)
3. Donnees connues: **Fix-all** (rapide)

---

##  Troubleshooting

### Q: "GROQ_API_KEY not found"
**R:** Definir variable environnement:
```powershell
$env:GROQ_API_KEY="votre_cle"
streamlit run streamlit_app.py
```

### Q: WeasyPrint n'installe pas
**R:** Sur Windows:
1. Installer GTK3: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
2. Puis: `pip install weasyprint --no-binary :all:`

### Q: Streamlit bloque sur "Running..."
**R:** Tuer python et recommencer:
```powershell
Get-Process python | Stop-Process -Force
streamlit run streamlit_app.py
```

### Q: Erreur encodage Windows
**R:** Deja regle (cp1252 -> UTF-8)
Alternative: `chcp 65001` ou `Set-Culture fr-FR`

### Q: Graphiques ne s'affichent pas
**R:** Verifier que Plotly est installe:
```bash
pip install --upgrade plotly
```

---

##  API Documentation

### CSVAnalyzer

```python
from core_analysis import CSVAnalyzer

# Initialiser
analyzer = CSVAnalyzer(
    input_file="data.csv",
    api_key="gsk_...",
    model="llama-3.3-70b-versatile"
)

# Charger donnees
analyzer.load_data()

# Analyser avec IA (1 appel API)
proposals = analyzer.analyze_columns()

# Nettoyer selon types
analyzer.clean_data()

# Sauvegarder resultats
output_dir = analyzer.save_results("output/")
```

### GraphicsGenerator

```python
from graphiques import GraphicsGenerator

graph_gen = GraphicsGenerator(df, output_dir="output/")

# Generer tous les graphiques
graphs = graph_gen.generate_all_graphs()

# Ou graphiques specifiques
graph_gen.graph_distribution_numeric("Montant")
graph_gen.graph_boxplot_numeric("Age")
graph_gen.graph_categorical_distribution("Statut")
graph_gen.graph_correlation_matrix()
graph_gen.graph_scatter_plot("Age", "Montant")
```

### RapportGenerator

```python
from rapport_generator import RapportGenerator

rapport_gen = RapportGenerator("output/")

# Generation complete HTML + PDF + JSON
files = rapport_gen.generate_complete_report(
    df=cleaned_df,
    renaming_map=mapping,
    proposals=proposals,
    questions=questions_list,
    anomalies_log=anomalies,
    graphs=graph_list,
    nom_fichier="data.csv"
)
# Retourne: {'html': Path(...), 'pdf': Path(...), 'json': Path(...)}
```

---

##  Customization

### Changer palette de couleurs (graphiques.py)

```python
COLORS = {
    'primary': '#667eea',      # Bleu (Gradients)
    'secondary': '#ff7f0e',    # Orange
    'success': '#2ca02c',      # Vert
    'warning': '#d62728',      # Rouge
    'info': '#9467bd'          # Pourpre
}
```

### Changer template rapport

Editer `HTML_TEMPLATE` dans `rapport_generator.py`:

```python
# CSS: modifier bloc <style>
# - Couleurs: gradients background-color
# - Fonts: font-family
# - Spacing: padding/margin
# - Responsive: media queries

# Layout: modifier structure HTML
# - Page de garde: .cover-page
# - Sections: .section
# - Cards: .info-card
```

### Ajouter nouveau graphique

```python
# Dans graphiques.py, classe GraphicsGenerator:
def graph_custom_viz(self) -> Optional[str]:
    """Ma visualisation perso."""
    fig = go.Figure()
    # ... logique plotly
    filename = "graph_XX_custom.html"
    filepath = self.output_dir / filename
    fig.write_html(filepath)
    self.generated_graphs.append(filename)
    return filename
```

Puis appeler dans `generate_all_graphs()`:
```python
try:
    self.graph_custom_viz()
except Exception as e:
    print(f"[ERREUR GRAPH] Custom: {e}")
```

---

##  Ressources

- **Groq API:** https://console.groq.com
- **Streamlit Docs:** https://docs.streamlit.io
- **Plotly Gallery:** https://plotly.com/python
- **pandas API:** https://pandas.pydata.org/docs
- **WeasyPrint:** https://weasyprint.org/documentation

---

##  Licence & Credit

**StudianalyseCSV v2.0**
- Analyse CSV avec IA (Groq LLM)
- Interface web (Streamlit)
- Graphiques pro (Plotly)
- Rapports HTML/PDF (Jinja2 + WeasyPrint)
- Design Material v3

Developpe avec  pour transformer donnees messy en insights professionnels.

---

**Version:** 2.0 | **Date:** 2026-04-13 | **Python:** 3.10+ | **Status:** Production-Ready 

