# 🚀 Demarrage Rapide - Agent IA Universel v2.0

## ⚡ 5 minutes pour commencer

### 1️⃣ Installation (2 min)

```bash
# Installer dependances
pip install -r requirements.txt

# OU verifier installation
python test_installation.py
```

### 2️⃣ Configurer API Groq (2 min)

**Option A: Variable d'environnement** (recommande)

```powershell
$env:GROQ_API_KEY="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"
```

**Option B: Fichier secrets**

Creer `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "gsk_..."
```

**Option C: Input dans l'app** (pendant execution)

### 3️⃣ Lancer l'interface web (1 min)

**Windows - Clic**:
```
Double-clic: DEMARRER_STREAMLIT.bat
```

**Windows - PowerShell**:
```powershell
.\DEMARRER_STREAMLIT.ps1
```

**Terminal**:
```bash
streamlit run streamlit_app.py
```

Puis ouvrir: http://localhost:8501

---

## 📋 Workflow Streamlit

```
1. Upload CSV
   ↓
2. Preview donnees
   ↓
3. Lancer analyse IA
   ↓
4. Verifier propositions
   ↓
5. Nettoyer donnees
   ↓
6. Generer rapports
   ↓
7. Telecharger fichiers ✅
```

---

## 🎯 Cas d'usage rapidement

### Cas 1: Nettoyer un CSV

1. Ouvrir Streamlit
2. Upload fichier (ou entrer chemin)
3. Cliquer "Lancer l'analyse IA"
4. Valider propositions (onglet 2)
5. Cliquer "Nettoyer les donnees" (onglet 3)
6. Telecharger CSV nettoye depuis onglet 4

**Temps total:** ~3-5 minutes

### Cas 2: Generer un rapport pro

Apres nettoyage:
1. Aller onglet "Rapport"
2. Selectionner format (HTML/PDF/Tous)
3. Cliquer "Generer"
4. Telecharger fichiers generes

**Temps:** ~1-2 minutes

### Cas 3: Batch processing (CLI)

```bash
# Lancer pour traiter directement
python exemple_utilisation.py

# Ou utiliser ancienne interface CLI
python agent_groq.py --input data.csv --fix-all
```

---

## 📊 Fichiers generes

Apres execution, dossier `output_YYYYMMDD_HHMMSS/`:

```
├── donnees_nettoyees.csv          ← CSV nettoye ✅
├── rapport.html                   ← Rapport web interactif
├── rapport.pdf                    ← Rapport imprimable
├── renaming_map.json              ← Mapping colonnes
├── proposals.json                 ← Propositions IA
├── anomalies_log.json             ← Transformations
├── graph_01_distribution_*.html   ← Histogrammes (Plotly)
├── graph_02_boxplot_*.html        ← Boxplots + outliers
├── graph_03_categories_*.html     ← Bar charts
├── graph_04_correlations.html     ← Heatmap correlations
├── graph_05_timeseries_*.html     ← Tendances temporelles
├── graph_06_scatter_*.html        ← Scatter plots
├── graph_07_pie_*.html            ← Pie charts
└── graph_08_statistics_summary.html ← Dashboard stats
```

**Total:** 6+ fichiers essentiels + 8+ graphiques interactifs

---

## 🔧 Lancement rapide

### Windows (Plus facile)

Double-clic sur:
- `DEMARRER_STREAMLIT.bat` (cmd)
- `DEMARRER_STREAMLIT.ps1` (PowerShell)

### Terminal

```bash
# Definer cle API
$env:GROQ_API_KEY="votre_cle_api"

# Lancer
streamlit run streamlit_app.py

# URL affichee automatiquement: http://localhost:8501
```

---

## 🛑 Erreurs courantes & Solutions

| Erreur | Solution |
|--------|----------|
| `GROQ_API_KEY not found` | Definir: `$env:GROQ_API_KEY="cle"` |
| `ModuleNotFoundError: pandas` | `pip install -r requirements.txt` |
| `Port 8501 already in use` | `streamlit run streamlit_app.py --server.port=8502` |
| `WeasyPrint error (PDF)` | Installer GTK3: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer |
| `Streamlit bloque` | Ctrl+C puis relancer |

---

## 💡 Tips & Tricks

1. **Creer `.streamlit/secrets.toml`** pour ne pas saisir API key a chaque fois
2. **Utiliser --fix-all** une fois propositions validees (plus rapide)
3. **Personaliser corrections.json** pour domaine metier specifique
4. **Export PDF** pour rapports a envoyer (meilleure portabilite)
5. **Sauvegarder donnees originales** avant nettoyage

---

## 📚 Aller plus loin

| Document | Contenu |
|----------|---------|
| **GUIDE_STREAMLIT.md** | Guide complet interface web |
| **README.md** | Documentation technique completes |
| **exemple_utilisation.py** | Code Python directs |
| **test_installation.py** | Verifier tout fonctionne |

---

## 🎓 Ressources

- **Groq API:** https://console.groq.com/docs
- **Streamlit:** https://docs.streamlit.io/library/get-started
- **Plotly:** https://plotly.com/python/
- **pandas:** https://pandas.pydata.org/docs

---

## ✅ Check-list debut

- [ ] Python 3.10+ installe
- [ ] `pip install -r requirements.txt` execute
- [ ] Cle API Groq disponible
- [ ] `test_installation.py` passe (optionnel)
- [ ] Vous etes pret!

---

## 🚀 Lancer MAINTENANT

```bash
streamlit run streamlit_app.py
```

**Ou double-clic sur:** `DEMARRER_STREAMLIT.bat`

---

**Bienvenue dans Agent IA Universel v2.0!**

*Bonne analyse de donnees! 📊✨*
