import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Optional
from core_analysis import GroqClient
import os

# Palette de couleurs et template Plotly par défaut
COLORS = {
    'primary': '#1f77b4',
    'warning': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'info': '#17becf',
    'light': '#f9f9f9',
    'dark': '#222',
}
PLOTLY_TEMPLATE = 'plotly_white'
MAX_ROWS_FOR_VIZ = 120000

# --- Ajout d'une fonction de mapping question -> type de graphique pertinent ---
def guess_graph_type_from_question(question: str) -> str:
    """Retourne le type de graphique le plus pertinent selon la question métier."""
    q = question.lower()
    if any(word in q for word in ["évolution", "evolution", "tendance", "progression", "variation", "temps", "date", "mois", "année", "an"]):
        return "line"
    if any(word in q for word in ["répartition", "distribution", "part", "proportion", "pourcentage", "ventilation"]):
        return "pie"
    if any(word in q for word in ["comparaison", "comparative", "écart", "différence", "vs", "par rapport"]):
        return "bar"
    if any(word in q for word in ["corrélation", "relation", "lien", "impact", "influence"]):
        return "scatter"
    if any(word in q for word in ["top", "meilleur", "plus", "moins", "classement", "ranking", "palmarès"]):
        return "bar"
    if any(word in q for word in ["valeur", "répartition des valeurs", "valeurs extrêmes", "outlier", "boxplot"]):
        return "box"
    return "bar"  # fallback générique


# --- Intégration de la méthode dans la bonne classe ---


class GraphicsGenerator:
    def _save_figure_outputs(self, fig, filename: str, include_plotlyjs='cdn', full_html: bool = True) -> str:
        """Sauvegarde un graphe en HTML + PNG (si possible), puis l'enregistre dans la liste des graphes."""
        html_path = self.output_dir / filename
        fig.write_html(str(html_path), include_plotlyjs=include_plotlyjs, full_html=full_html)
        self.generated_graphs.append(filename)

        # Le PNG statique sert au PDF (ReportLab), qui ne peut pas intégrer les graphes interactifs.
        if self._png_export_enabled:
            png_path = self.output_dir / Path(filename).with_suffix('.png')
            try:
                fig.write_image(str(png_path), format='png', width=1280, height=720, scale=1)
            except Exception as e:
                # Si Kaleido n'est pas dispo, on n'insiste pas pour éviter le coût CPU sur chaque graphe.
                if not self._png_warning_shown:
                    print("[INFO] Export PNG indisponible (PDF sans images de graphes).")
                    print("[INFO] Installez 'kaleido' pour activer les graphes dans le PDF.")
                    print(f"[INFO] Détail export PNG: {type(e).__name__}")
                    self._png_warning_shown = True
                self._png_export_enabled = False

        return filename

    def graph_categorical_distribution(self, col: str, top_n: int = 10) -> Optional[str]:
        """Bar chart de répartition d'une variable catégorielle avec option de croisement."""
        if col not in self.df.columns:
            return None
        
        # Chercher une deuxième dimension pour enrichir le graphique
        cat_cols = self._get_categorical_cols()
        second_cat = None
        for c in cat_cols:
            if c != col and self.df[c].nunique() < 6 and self.df[c].nunique() > 1:
                second_cat = c
                break
        
        fig = go.Figure()
        
        if second_cat:
            # Graphique avec deux dimensions (stacked ou grouped)
            crosstab = pd.crosstab(self.df[col], self.df[second_cat])
            crosstab = crosstab.iloc[:top_n]
            colors = px.colors.qualitative.Set2
            
            for i, second_val in enumerate(crosstab.columns):
                fig.add_trace(go.Bar(
                    name=str(second_val),
                    x=crosstab.index.astype(str),
                    y=crosstab[second_val],
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f"<b>%{{x}}</b><br>{second_cat}: {second_val}<br>Effectif: %{{y}}<extra></extra>",
                ))
            
            barmode = 'group'
        else:
            # Graphique simple
            value_counts = self.df[col].value_counts(dropna=True).head(top_n)
            colors_palette = px.colors.sequential.Blues_r
            colors = [colors_palette[int(i / top_n * (len(colors_palette) - 1))] for i in range(len(value_counts))]
            
            fig.add_trace(go.Bar(
                x=value_counts.index.astype(str),
                y=value_counts.values,
                marker_color=colors,
                text=value_counts.values,
                textposition="outside",
                hovertemplate=f"<b>%{{x}}</b><br>Effectif: %{{y}}<extra></extra>",
            ))
            
            barmode = None
        
        fig.update_layout(
            title={
                'text': f"<b>Distribution - {col}</b>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=18, color=COLORS.get('dark', '#222'))
            },
            xaxis_title=col,
            yaxis_title="Effectif",
            template=PLOTLY_TEMPLATE,
            height=480,
            margin=dict(l=70, r=40, t=90, b=70),
            font=dict(family="Arial, sans-serif", size=12),
            barmode=barmode,
            legend=dict(x=1.0, y=1.0, bgcolor='rgba(255,255,255,0.8)', bordercolor='rgb(200,200,200)', borderwidth=1) if second_cat else dict(showlegend=False)
        )
        filename = f"graph_03_categories_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def graph_croise_moyenne(self, cat_col: str, num_col: str) -> Optional[str]:
        """Bar chart de la moyenne d'une variable numérique par catégorie avec tendance visible et sous-catégories."""
        if cat_col not in self.df.columns or num_col not in self.df.columns:
            return None
        
        # Chercher une deuxième dimension pour croiser les données
        cat_cols = self._get_categorical_cols()
        second_cat = None
        for col in cat_cols:
            if col != cat_col and self.df[col].nunique() < 8 and self.df[col].nunique() > 1:
                second_cat = col
                break
        
        fig = go.Figure()
        
        if second_cat:
            # Créer un graphique groupé avec 2 dimensions
            grouped = self.df.groupby([cat_col, second_cat])[num_col].mean().reset_index()
            colors_map = {val: px.colors.qualitative.Pastel[i % len(px.colors.qualitative.Pastel)] 
                         for i, val in enumerate(grouped[second_cat].unique())}
            
            for second_val in sorted(grouped[second_cat].unique()):
                subset = grouped[grouped[second_cat] == second_val].sort_values(cat_col)
                fig.add_trace(go.Bar(
                    x=subset[cat_col].astype(str),
                    y=subset[num_col],
                    name=str(second_val),
                    marker_color=colors_map[second_val],
                    text=[f"{v:.1f}" for v in subset[num_col]],
                    textposition="outside",
                    hovertemplate=f"<b>%{{x}}</b><br>{second_cat}: {second_val}<br>{num_col}: %{{y:.2f}}<extra></extra>",
                ))
            
            title_text = f"Moyenne de {num_col} par {cat_col} et {second_cat}"
        else:
            # Graphique simple avec gradient
            grouped = self.df.groupby(cat_col)[num_col].mean().sort_values(ascending=False)
            max_val = grouped.values.max()
            min_val = grouped.values.min()
            colors = []
            for val in grouped.values:
                norm_val = (val - min_val) / (max_val - min_val) if max_val > min_val else 0.5
                r = int(31 + (179 * (1 - norm_val)))
                g = int(119 + (91 * (1 - norm_val)))
                b = int(180 - (20 * (1 - norm_val)))
                colors.append(f'rgb({r},{g},{b})')
            
            fig.add_trace(go.Bar(
                x=grouped.index.astype(str),
                y=grouped.values,
                marker_color=colors,
                text=[f"{v:.1f}" for v in grouped.values],
                textposition="outside",
                hovertemplate=f"<b>%{{x}}</b><br>{num_col}: %{{y:.2f}}<extra></extra>",
            ))
            
            title_text = f"Moyenne de {num_col} par {cat_col}"
        
        fig.update_layout(
            title={
                'text': f"<b>{title_text}</b>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=18, color=COLORS.get('dark', '#222'))
            },
            xaxis_title=cat_col,
            yaxis_title=f"Moyenne de {num_col}",
            template=PLOTLY_TEMPLATE,
            height=480,
            margin=dict(l=70, r=40, t=90, b=70),
            font=dict(family="Arial, sans-serif", size=12),
            barmode='group',
            legend=dict(x=1.0, y=1.0, bgcolor='rgba(255,255,255,0.8)', bordercolor='rgb(200,200,200)', borderwidth=1)
        )
        filename = f"graph_business_moyenne_{num_col}_{cat_col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def graph_pie_chart(self, col: str, top_n: int = 8) -> Optional[str]:
        """Pie chart d'une variable catégorielle (top_n modalités)."""
        if col not in self.df.columns:
            return None
        value_counts = self.df[col].value_counts(dropna=True).head(top_n)
        if value_counts.empty:
            return None
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=value_counts.index.astype(str),
            values=value_counts.values,
            hole=0.3,
            marker_colors=[COLORS.get('primary', '#1f77b4')] * len(value_counts),
        ))
        fig.update_layout(
            title={
                'text': f"<b>Répartition (Pie) - {col}</b>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=20, color=COLORS.get('dark', '#222'))
            },
            template=PLOTLY_TEMPLATE,
            height=480,
            margin=dict(l=60, r=30, t=80, b=60),
        )
        filename = f"graph_03_pie_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    """Generateur de graphiques professionnels avec IA intégrée."""

    def graph_distribution_numeric(self, col: str = None) -> Optional[str]:
        """Histogramme/Distribution d'une variable numérique."""
        num_cols = self._get_numeric_cols()
        if col is None:
            if not num_cols:
                return None
            col = num_cols[0]
        if col not in self.df.columns:
            return None
        data = self.df[col].dropna()
        if len(data) < 3:
            return None
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=data,
            nbinsx=min(40, max(10, int(np.sqrt(len(data))))),
            marker_color=COLORS.get('primary', '#1f77b4'),
            opacity=0.85,
            hoverlabel=dict(bgcolor=COLORS.get('light', '#f9f9f9'), font_size=13, font_family="Segoe UI"),
        ))
        fig.update_layout(
            title={
                'text': f"<b>Distribution - {col}</b>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=20, color=COLORS.get('dark', '#222'))
            },
            xaxis_title=col,
            yaxis_title="Effectif",
            template=PLOTLY_TEMPLATE,
            height=480,
            margin=dict(l=60, r=30, t=80, b=60),
        )
        filename = f"graph_01_distribution_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)


    def generate_graph_for_question(self, question: str, utilite: str = None, contexte: str = "", colonnes: list = None, type_graphique: str = None, **kwargs) -> Optional[str]:
        """
        Génère un graphique aligné avec la question métier et les colonnes associées.
        
        Args:
            question: Le texte de la question
            utilite: Utilité de la question
            contexte: Contexte métier
            colonnes: Liste des colonnes à utiliser
            type_graphique: Type de graphique préféré ('line', 'bar', 'scatter', 'pie', 'histogram', 'box')
        """
        if not question:
            return None
        
        # Vérifier utilite (éviter les Series pandas)
        try:
            if utilite is not None:
                utilite = str(utilite).strip()
                if not utilite or utilite == 'nan':
                    utilite = None
        except Exception:
            utilite = None
        
        colonnes = colonnes or kwargs.get('colonnes', [])
        if not colonnes:
            return None
        
        # Convertir en liste de strings sûrement
        try:
            colonnes = [str(c).strip() for c in colonnes]
        except Exception:
            return None
        
        # Obtenir les types de colonnes disponibles
        num_cols = self._get_numeric_cols()
        cat_cols = self._get_categorical_cols()
        date_cols = self._get_date_cols()
        
        # === Cas 1 colonne ===
        if len(colonnes) == 1:
            c = colonnes[0]
            
            if type_graphique == 'pie' and c in cat_cols:
                return self.graph_categorical_distribution(c)
            
            if type_graphique == 'histogram' or type_graphique == 'bar':
                if c in num_cols:
                    return self.graph_distribution_numeric(c)
                if c in cat_cols:
                    return self.graph_categorical_distribution(c)
            
            if type_graphique == 'box':
                if c in num_cols:
                    return self.graph_boxplot_numeric(c)
            
            # Fallback automatique selon type de colonne
            if c in num_cols:
                return self.graph_distribution_numeric(c)
            if c in cat_cols:
                return self.graph_categorical_distribution(c)
            if c in date_cols:
                data = self.df[c].dropna()
                if len(data) < 3:
                    return None
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=data, marker_color=COLORS['primary'], opacity=0.85))
                fig.update_layout(title=f"<b>Distribution - {c}</b>", xaxis_title=c, yaxis_title="Effectif", template=PLOTLY_TEMPLATE)
                filename = f"graph_01_distribution_{c}.html"
                return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)
            return None
        
        # === Cas 2 colonnes ===
        if len(colonnes) == 2:
            c1, c2 = colonnes
            
            # Line graph: date + numeric (évolution)
            if type_graphique == 'line':
                if (c1 in num_cols and c2 in date_cols) or (c2 in num_cols and c1 in date_cols):
                    col_num = c1 if c1 in num_cols else c2
                    col_date = c2 if c2 in date_cols else c1
                    df = self.df[[col_date, col_num]].dropna().sort_values(col_date)
                    if len(df) < 3:
                        return None
                    
                    fig = go.Figure()
                    
                    # === Données brutes (si peu de points) ou lissées (si nombreux points) ===
                    if len(df) > 100:
                        df[col_num + '_smoothed'] = df[col_num].rolling(window=10, min_periods=1).mean()
                        y_vals = df[col_num + '_smoothed']
                        mode_marker = 'lines'  # Sans marqueurs si lissé
                        name_trace = f'{col_num} (lissé)'
                    else:
                        y_vals = df[col_num]
                        mode_marker = 'lines+markers'
                        name_trace = col_num
                    
                    fig.add_trace(go.Scatter(
                        x=df[col_date],
                        y=y_vals,
                        mode=mode_marker,
                        name=name_trace,
                        line=dict(color=COLORS['primary'], width=3),
                        marker=dict(size=6, color=COLORS['primary']),
                        hovertemplate='<b>%{x}</b><br>' + col_num + ': %{y:.2f}<extra></extra>'
                    ))
                    
                    # === Ajouter une bande de tendance (min-max rolling) ===
                    try:
                        if len(df) > 10:
                            df['min_val'] = df[col_num].rolling(window=5, min_periods=1).min()
                            df['max_val'] = df[col_num].rolling(window=5, min_periods=1).max()
                            
                            fig.add_trace(go.Scatter(
                                x=df[col_date],
                                y=df['max_val'],
                                mode='lines',
                                line=dict(width=0),
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                            
                            fig.add_trace(go.Scatter(
                                x=df[col_date],
                                y=df['min_val'],
                                mode='lines',
                                line=dict(width=0),
                                fillcolor='rgba(31, 119, 180, 0.1)',
                                fill='tonexty',
                                name='Plage (min-max)',
                                hoverinfo='skip'
                            ))
                    except Exception:
                        pass
                    
                    fig.update_layout(
                        title=f"<b>Évolution de {col_num}</b>",
                        xaxis_title=col_date,
                        yaxis_title=col_num,
                        template=PLOTLY_TEMPLATE,
                        height=500,
                        hovermode='x unified'
                    )
                    filename = f"graph_evolution_{col_num}.html"
                    return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)
            
            # Bar graph: categorical + numeric (comparaison)
            if type_graphique == 'bar':
                if (c1 in cat_cols and c2 in num_cols):
                    return self.graph_croise_moyenne(c1, c2)
                if (c2 in cat_cols and c1 in num_cols):
                    return self.graph_croise_moyenne(c2, c1)
            
            # Scatter graph: numeric + numeric (corrélation)
            if type_graphique == 'scatter':
                if c1 in num_cols and c2 in num_cols:
                    return self.graph_scatter_plot(c1, c2)
            
            # Fallback: Numeric + date : évolution
            if (c1 in num_cols and c2 in date_cols) or (c2 in num_cols and c1 in date_cols):
                col_num = c1 if c1 in num_cols else c2
                col_date = c2 if c2 in date_cols else c1
                df = self.df[[col_date, col_num]].dropna().sort_values(col_date)
                if len(df) < 3:
                    return None
                
                fig = go.Figure()
                
                # Lissage automatique si trop de points
                if len(df) > 100:
                    df[col_num + '_smoothed'] = df[col_num].rolling(window=10, min_periods=1).mean()
                    y_vals = df[col_num + '_smoothed']
                    mode_marker = 'lines'
                else:
                    y_vals = df[col_num]
                    mode_marker = 'lines+markers'
                
                fig.add_trace(go.Scatter(
                    x=df[col_date],
                    y=y_vals,
                    mode=mode_marker,
                    line=dict(color=COLORS['primary'], width=3),
                    marker=dict(size=6, color=COLORS['primary'])
                ))
                
                fig.update_layout(
                    title=f"<b>Évolution de {col_num}</b>",
                    xaxis_title=col_date,
                    yaxis_title=col_num,
                    template=PLOTLY_TEMPLATE,
                    height=500
                )
                filename = f"graph_evolution_{col_num}.html"
                return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)
            
            # Numeric + categorical : moyenne par catégorie
            if (c1 in num_cols and c2 in cat_cols):
                return self.graph_croise_moyenne(c2, c1)
            if (c2 in num_cols and c1 in cat_cols):
                return self.graph_croise_moyenne(c1, c2)
            
            # 2 numeriques : scatter/correlation
            if c1 in num_cols and c2 in num_cols:
                return self.graph_scatter_plot(c1, c2)
            
            return None
        
        # === 3+ colonnes: pas implémenté ===
        return None

    def _get_numeric_cols(self) -> list:
        """Retourne la liste des colonnes numériques du DataFrame."""
        if self.df.empty:
            return []
        return [
            col for col in self.df.select_dtypes(include=[np.number]).columns
            if self.df[col].nunique(dropna=True) > 1
        ]

    def _is_identifier_like(self, col: str) -> bool:
        """Heuristique: détecte les colonnes identifiants (peu pertinentes pour corrélations métier)."""
        col_lower = str(col).lower()

        if (
            col_lower in {"id", "index", "uuid"}
            or col_lower.startswith("id_")
            or col_lower.endswith("_id")
            or "identifiant" in col_lower
            or "num_acc" in col_lower
            or col_lower.startswith("num_")
        ):
            return True

        series = self.df[col].dropna()
        if len(series) < 3:
            return False

        unique_ratio = series.nunique(dropna=True) / len(series)

        # Colonne quasi-unique et monotone: typiquement un identifiant ou index séquentiel.
        try:
            if unique_ratio >= 0.98 and (series.is_monotonic_increasing or series.is_monotonic_decreasing):
                return True
        except Exception:
            pass

        return unique_ratio >= 0.995

    def _get_business_numeric_cols(self) -> list:
        """Colonnes numériques utiles à l'analyse métier (hors identifiants)."""
        return [col for col in self._get_numeric_cols() if not self._is_identifier_like(col)]

    def _get_categorical_cols(self) -> list:
        """Retourne la liste des colonnes catégorielles du DataFrame, robuste aux StringDtype avec NA."""
        if self.df.empty:
            return []
        cols = set(self.df.select_dtypes(include=["object", "category"]).columns)
        # Ajoute explicitement les colonnes string (StringDtype), même avec NA
        for col in self.df.columns:
            if pd.api.types.is_string_dtype(self.df[col]):
                cols.add(col)
        return [col for col in cols if self.df[col].nunique(dropna=True) > 1]

    def _get_date_cols(self) -> list:
        """Retourne la liste des colonnes de type date/datetime du DataFrame (robuste à StringDtype)."""
        if self.df.empty:
            return []
        return [col for col in self.df.columns if pd.api.types.is_datetime64_any_dtype(self.df[col])]

    def __init__(self, df: pd.DataFrame, output_dir: str = "output"):
        self.df_full = df
        self.was_sampled_for_viz = False
        if len(df) > MAX_ROWS_FOR_VIZ:
            self.df = df.sample(n=MAX_ROWS_FOR_VIZ, random_state=42).copy()
            self.was_sampled_for_viz = True
            print(f"[INFO] Dataset volumineux ({len(df)} lignes): graphiques calculés sur un échantillon de {len(self.df)} lignes.")
        else:
            self.df = df
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.generated_graphs = []
        self._png_export_enabled = True
        self._png_warning_shown = False
        api_key = os.environ.get("GROQ_API_KEY")
        # Si streamlit est dispo ET secrets, on récupère la clé, sinon on ignore
        try:
            import streamlit
            secrets = getattr(streamlit, "secrets", None)
            if not api_key and secrets and "GROQ_API_KEY" in secrets:
                api_key = secrets["GROQ_API_KEY"]
        except ImportError:
            pass
        self.api_client = GroqClient(api_key) if api_key else None

    def graph_boxplot_numeric(self, col: str = None) -> Optional[str]:
        # Amélioration du rendu : couleurs, labels, responsive, hover info, accessibilité
        if col is None:
            cols = self._get_numeric_cols()
            if not cols: return None
            col = cols[0]
        if col not in self.df.columns: return None
        data = self.df[col].dropna()
        if len(data) < 3: return None

        Q1, Q3 = data.quantile(0.25), data.quantile(0.75)
        outliers = data[(data < Q1 - 1.5 * (Q3 - Q1)) | (data > Q3 + 1.5 * (Q3 - Q1))]

        fig = go.Figure()
        fig.add_trace(go.Box(
            y=data,
            name=col,
            marker_color=COLORS['primary'],
            boxmean='sd',
            boxpoints='outliers',
            hoverlabel=dict(bgcolor=COLORS['light'], font_size=13, font_family="Segoe UI"),
            line=dict(width=2)
        ))
        if len(outliers) > 0:
            fig.add_trace(go.Scatter(
                y=outliers,
                x=[col]*len(outliers),
                mode='markers',
                name='Valeurs aberrantes',
                marker=dict(size=10, color=COLORS['warning'], symbol='diamond'),
                hoverinfo='y+name',
                showlegend=True
            ))
        fig.update_layout(
            title={
                'text': f"<b>Analyse Boxplot - {col}</b><br><sub>{len(outliers)} outliers détectés</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=20, color=COLORS['dark'])
            },
            yaxis_title=col,
            template=PLOTLY_TEMPLATE,
            height=480,
            margin=dict(l=60, r=30, t=80, b=60),
        )
        filename = f"graph_boxplot_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def graph_correlation_matrix(self) -> Optional[str]:
        """Matrice de correlation pour variables numeriques pertinentes."""
        # On filtre les colonnes identifiant pour garder des corrélations métier lisibles.
        numeric_cols = self._get_business_numeric_cols()
        if len(numeric_cols) < 2:
            numeric_cols = self._get_numeric_cols()
        if len(numeric_cols) < 2:
            return None
        numeric_df = self.df[numeric_cols]
        corr_matrix = numeric_df.corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0, zmax=1, zmin=-1,
            hovertemplate='<b>%{x} vs %{y}</b><br>Correlation : %{z:.2f}<extra></extra>'
        ))
        fig.update_layout(
            title="<b>Matrice de Corrélation Stratégique</b><br><sub>Relations entre les indicateurs métiers (hors identifiants)</sub>",
            template=PLOTLY_TEMPLATE,
            height=600, width=800
        )
        filename = "graph_04_correlations.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs=True, full_html=True)

    def graph_scatter_plot(self, col1: str = None, col2: str = None) -> Optional[str]:
        business_cols = self._get_business_numeric_cols()
        numeric_cols = business_cols if len(business_cols) >= 2 else self._get_numeric_cols()
        if len(numeric_cols) < 2: return None
        if col1 is None: col1 = numeric_cols[0]
        if col2 is None: col2 = numeric_cols[1]
        data = self.df[[col1, col2]].dropna()
        if len(data) < 3: return None

        fig = go.Figure()
        
        # === Points du scatter ===
        fig.add_trace(go.Scatter(
            x=data[col1],
            y=data[col2],
            mode='markers',
            marker=dict(
                color=data[col1],
                colorscale='Viridis',  # Palette continue valide
                showscale=True,
                size=6,
                opacity=0.6
            ),
            name='Données'
        ))
        
        # === AJOUT: Ligne de régression (trendline) ===
        try:
            # Calculer la régression linéaire
            z = np.polyfit(data[col1], data[col2], 1)  # degré 1 = linéaire
            p = np.poly1d(z)
            
            # Générer la ligne de régression
            x_trend = np.linspace(data[col1].min(), data[col1].max(), 100)
            y_trend = p(x_trend)
            
            # Calculer le coefficient de corrélation
            correlation = data[col1].corr(data[col2])
            
            fig.add_trace(go.Scatter(
                x=x_trend,
                y=y_trend,
                mode='lines',
                line=dict(color='red', width=3, dash='dash'),
                name=f'Tendance (r={correlation:.2f})',
                hovertemplate='Tendance<br>%{x:.2f}<br>%{y:.2f}<extra></extra>'
            ))
        except Exception as e:
            print(f"[INFO] Tendance non calculée pour {col1} vs {col2}: {e}")
        
        fig.update_layout(
            title=f"<b>Correlation : {col1} vs {col2}</b>", 
            xaxis_title=col1, 
            yaxis_title=col2, 
            template=PLOTLY_TEMPLATE, 
            height=500,
            hovermode='closest'
        )

        # Eviter l'affichage SI abrégé (ex: 202.1B) pour les colonnes entières volumineuses.
        try:
            x_vals = pd.to_numeric(data[col1], errors='coerce').dropna()
            if len(x_vals) > 0 and np.allclose(x_vals.to_numpy() % 1, 0):
                fig.update_xaxes(tickformat=",.0f")
        except Exception:
            pass

        try:
            y_vals = pd.to_numeric(data[col2], errors='coerce').dropna()
            if len(y_vals) > 0 and np.allclose(y_vals.to_numpy() % 1, 0):
                fig.update_yaxes(tickformat=",.0f")
        except Exception:
            pass

        filename = f"graph_06_scatter_{col1.replace(' ', '_')}_vs_{col2.replace(' ', '_')}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs=True, full_html=True)

    def graph_sunburst_hierarchie(self, cols_hierarchy: List[str], value_col: str = None) -> Optional[str]:
        """Sunburst chart pour visualiser une hiérarchie multi-variables."""
        if len(cols_hierarchy) < 2:
            return None
        
        # Garder les colonnes qui existent
        cols_hierarchy = [c for c in cols_hierarchy if c in self.df.columns]
        if len(cols_hierarchy) < 2:
            return None
        
        # Déterminer la colonne de valeur
        if value_col is None:
            num_cols = self._get_numeric_cols()
            value_col = num_cols[0] if num_cols else None
        
        if value_col is None:
            agg_data = self.df.groupby(cols_hierarchy).size().reset_index(name='count')
            value_col = 'count'
        else:
            agg_data = self.df.groupby(cols_hierarchy)[value_col].sum().reset_index()

        if len(agg_data) == 0:
            return None

        # Créer le sunburst
        fig = px.sunburst(
            agg_data,
            ids=cols_hierarchy,
            parents=['' if i == 0 else cols_hierarchy[i-1] for i in range(len(cols_hierarchy))],
            values=value_col,
            color=value_col,
            color_continuous_scale='Viridis'
        )

        title_cols = ' > '.join([c.replace('_', ' ').title()[:15] for c in cols_hierarchy])
        fig.update_layout(
            title=f"<b>Relation Hiérarchique</b><br><sub>Décomposition par {title_cols}</sub>",
            template=PLOTLY_TEMPLATE,
            height=700
        )

        filename = f"graph_sunburst_{'_'.join(cols_hierarchy[:3])}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs=True, full_html=True)

    def graph_bubble_3d(self, col_x: str = None, col_y: str = None, col_size: str = None, col_color: str = None) -> Optional[str]:
        """Bubble chart 3D+ pour comparer 3-4 dimensions simultanément."""
        num_cols = self._get_numeric_cols()
        cat_cols = self._get_categorical_cols()
        
        if len(num_cols) < 2:
            return None
        
        # Sélectionner les colonnes par défaut
        if col_x is None:
            col_x = num_cols[0]
        if col_y is None:
            col_y = num_cols[1] if len(num_cols) > 1 else num_cols[0]
        if col_size is None and len(num_cols) > 2:
            col_size = num_cols[2]
        if col_color is None and cat_cols:
            col_color = cat_cols[0]
        
        data = self.df[[col_x, col_y]].copy()
        if col_size:
            data[col_size] = self.df[col_size]
        if col_color:
            data[col_color] = self.df[col_color]
        
        data = data.dropna(subset=[col_x, col_y])
        if len(data) == 0:
            return None

        fig = px.scatter(
            data,
            x=col_x,
            y=col_y,
            size=col_size if col_size else None,
            color=col_color if col_color else None,
            hover_data=list(data.columns),
            opacity=0.6
        )

        subtitle = f"{col_x} vs {col_y}"
        if col_size:
            subtitle += f" (taille: {col_size})"
        if col_color:
            subtitle += f" (couleur: {col_color})"

        fig.update_layout(
            title=f"<b>Analyse Multi-Dimensionnelle</b><br><sub>{subtitle}</sub>",
            template=PLOTLY_TEMPLATE,
            height=600,
            hovermode='closest'
        )

        filename = f"graph_bubble_{col_x}_{col_y}.html".replace(' ', '_')
        return self._save_figure_outputs(fig, filename, include_plotlyjs=True, full_html=True)

    def graph_sankey_flow(self, source_col: str, target_col: str, value_col: str = None) -> Optional[str]:
        # Amélioration du rendu : couleurs, labels, responsive, hover info, accessibilité
        if source_col not in self.df.columns or target_col not in self.df.columns:
            return None
        if value_col is None:
            flow_data = self.df.groupby([source_col, target_col]).size().reset_index(name='count')
            value_col = 'count'
        else:
            flow_data = self.df.groupby([source_col, target_col])[value_col].sum().reset_index()
        if len(flow_data) == 0:
            return None
        sources = flow_data[source_col].unique().tolist()
        targets = flow_data[target_col].unique().tolist()
        all_nodes = sources + targets
        source_indices = [all_nodes.index(s) for s in flow_data[source_col]]
        target_indices = [all_nodes.index(t) for t in flow_data[target_col]]
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=all_nodes,
                color=COLORS.get('primary', '#1f77b4'),
                hoverlabel=dict(bgcolor=COLORS['light'], font_size=13, font_family="Segoe UI")
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=flow_data[value_col].tolist()
            )
        )])
        fig.update_layout(
            title={
                'text': f"<b>Flux : {source_col.title()} -> {target_col.title()}</b>",
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=20, color=COLORS['dark'])
            },
            template=PLOTLY_TEMPLATE,
            height=520,
            margin=dict(l=60, r=30, t=80, b=60),
            font=dict(family="Segoe UI, Arial", size=13)
        )
        filename = f"graph_sankey_{source_col}_{target_col}.html".replace(' ', '_')
        self.output_dir.mkdir(exist_ok=True)
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def generate_graphs_for_questions(self, questions: List[dict]) -> List[str]:
        """Génère des graphiques PERTINENTS pour chaque question posée."""
        print("[GRAPHIQUES] Génération de graphiques par question...")
        self.generated_graphs = []
        
        for i, question in enumerate(questions, 1):
            try:
                q_text = question.get('question', '')
                q_cols = question.get('colonnes', [])
                q_type = question.get('type_graphique', 'bar')
                
                if not q_cols:
                    continue
                
                # Générer le graphique approprié selon la question
                if len(q_cols) == 1:
                    # Question sur 1 seule colonne
                    col = q_cols[0]
                    if col not in self.df.columns:
                        continue
                    
                    # Déterminer le type
                    if self.df[col].dtype in ['float64', 'int64']:
                        # Numérique = distribution
                        graph_file = self._graph_distribution_for_question(col, i, q_text)
                    else:
                        # Catégorique = répartition
                        graph_file = self._graph_category_for_question(col, i, q_text)
                    
                    if graph_file:
                        self.generated_graphs.append(graph_file)
                
                elif len(q_cols) == 2:
                    # Question sur 2 colonnes
                    col1, col2 = q_cols[0], q_cols[1]
                    if col1 not in self.df.columns or col2 not in self.df.columns:
                        continue
                    
                    type1 = self.df[col1].dtype in ['float64', 'int64']
                    type2 = self.df[col2].dtype in ['float64', 'int64']
                    
                    if type1 and type2:
                        # 2 numériques = scatter + ligne de tendance
                        graph_file = self._graph_scatter_for_question(col1, col2, i, q_text)
                    elif not type1 and type2:
                        # Catégorique + Numérique = barres groupées
                        graph_file = self._graph_bar_grouped_for_question(col1, col2, i, q_text)
                    elif type1 and not type2:
                        # Numérique + Catégorique = barres groupées (inversé)
                        graph_file = self._graph_bar_grouped_for_question(col2, col1, i, q_text)
                    else:
                        # 2 catégories = heatmap ou sankey
                        graph_file = self._graph_heatmap_for_question(col1, col2, i, q_text)
                    
                    if graph_file:
                        self.generated_graphs.append(graph_file)
                
            except Exception as e:
                print(f"[WARN] Graphique Q{i} échoué: {e}")
        
        print(f"[OK] {len(self.generated_graphs)} graphiques générés avec succès")
        return self.generated_graphs

    def _graph_distribution_for_question(self, col: str, q_num: int, question: str) -> Optional[str]:
        """Génère une distribution (histogramme ou boxplot) pour une variable numérique."""
        if col not in self.df.columns:
            return None
        
        # Histogramme pour voir la distribution
        fig = px.histogram(
            self.df,
            x=col,
            nbins=20,
            title=f"<b>Question {q_num}: {question[:60]}</b><br><sub>Distribution de {col}</sub>",
            labels={col: col.replace('_', ' ').title()},
            color_discrete_sequence=['#0071e3']
        )
        
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=450,
            margin=dict(l=70, r=40, t=100, b=70),
            font=dict(family="Arial, sans-serif", size=12),
            xaxis_title=col.replace('_', ' ').title(),
            yaxis_title="Nombre d'observations"
        )
        
        filename = f"graph_q{q_num:02d}_distribution_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def _graph_category_for_question(self, col: str, q_num: int, question: str) -> Optional[str]:
        """Génère un graphique de répartition pour une variable catégorique."""
        if col not in self.df.columns:
            return None
        
        value_counts = self.df[col].value_counts(dropna=True).head(12)
        if value_counts.empty:
            return None
        
        df_counts = value_counts.reset_index()
        df_counts.columns = [col, 'count']
        
        fig = px.bar(
            df_counts,
            x=col,
            y='count',
            title=f"<b>Question {q_num}: {question[:60]}</b><br><sub>Répartition de {col}</sub>",
            labels={col: col.replace('_', ' ').title(), 'count': 'Effectif'},
            color_discrete_sequence=['#0071e3']
        )
        
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=450,
            margin=dict(l=70, r=40, t=100, b=70),
            font=dict(family="Arial, sans-serif", size=12),
            xaxis_title=col.replace('_', ' ').title(),
            yaxis_title="Nombre d'observations"
        )
        
        filename = f"graph_q{q_num:02d}_categories_{col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def _graph_scatter_for_question(self, col1: str, col2: str, q_num: int, question: str) -> Optional[str]:
        """Génère un scatter plot avec ligne de tendance pour 2 variables numériques."""
        if col1 not in self.df.columns or col2 not in self.df.columns:
            return None
        
        data = self.df[[col1, col2]].dropna()
        if len(data) < 3:
            return None
        
        fig = px.scatter(
            data,
            x=col1,
            y=col2,
            title=f"<b>Question {q_num}: {question[:60]}</b><br><sub>Relation {col1} vs {col2}</sub>",
            labels={col1: col1.replace('_', ' ').title(), col2: col2.replace('_', ' ').title()},
            trendline="ols",
            trendline_color_override="#ff7f0e"
        )
        
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=500,
            margin=dict(l=70, r=40, t=100, b=70),
            font=dict(family="Arial, sans-serif", size=12)
        )
        
        filename = f"graph_q{q_num:02d}_scatter_{col1}_vs_{col2}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def _graph_bar_grouped_for_question(self, cat_col: str, num_col: str, q_num: int, question: str) -> Optional[str]:
        """Génère des barres groupées pour comparer une métrique par catégorie."""
        if cat_col not in self.df.columns or num_col not in self.df.columns:
            return None
        
        # Grouper et calculer la moyenne
        df_grouped = self.df.groupby(cat_col)[num_col].mean().reset_index()
        df_grouped = df_grouped.sort_values(num_col, ascending=False)
        
        fig = px.bar(
            df_grouped,
            x=cat_col,
            y=num_col,
            title=f"<b>Question {q_num}: {question[:60]}</b><br><sub>Moyenne de {num_col} par {cat_col}</sub>",
            labels={cat_col: cat_col.replace('_', ' ').title(), num_col: f"Moyenne {num_col}"},
            text=num_col,
            color=num_col,
            color_continuous_scale='Blues'
        )
        
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=450,
            margin=dict(l=70, r=40, t=100, b=70),
            font=dict(family="Arial, sans-serif", size=12),
            showlegend=False
        )
        
        filename = f"graph_q{q_num:02d}_comparison_{cat_col}_vs_{num_col}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def _graph_heatmap_for_question(self, cat1: str, cat2: str, q_num: int, question: str) -> Optional[str]:
        """Génère une heatmap pour 2 variables catégoriques."""
        if cat1 not in self.df.columns or cat2 not in self.df.columns:
            return None
        
        crosstab = pd.crosstab(self.df[cat1], self.df[cat2])
        
        fig = px.imshow(
            crosstab,
            title=f"<b>Question {q_num}: {question[:60]}</b><br><sub>Relation {cat1} vs {cat2}</sub>",
            labels=dict(x=cat2.replace('_', ' ').title(), y=cat1.replace('_', ' ').title(), color="Effectif"),
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=500,
            margin=dict(l=100, r=40, t=100, b=70),
            font=dict(family="Arial, sans-serif", size=12)
        )
        
        filename = f"graph_q{q_num:02d}_heatmap_{cat1}_vs_{cat2}.html"
        return self._save_figure_outputs(fig, filename, include_plotlyjs='cdn', full_html=True)

    def generate_all_graphs(self, skip_timeseries: bool = True) -> List[str]:
        """Génère des graphiques stratégiques et INTELLIGENTS."""
        print("[GRAPHIQUES] Génération Business Intelligente en cours...")
        self.generated_graphs = []
        num_cols = self._get_numeric_cols()
        business_num_cols = self._get_business_numeric_cols()
        cat_cols = self._get_categorical_cols()
        date_cols = self._get_date_cols()

        # === ÉTAPE 1: Détecter les colonnes clés par contexte ===
        
        # Clé métrique: Plus grande variable numérique (ex: Sales, Revenue, Profit, etc.)
        metric_candidates = business_num_cols if business_num_cols else num_cols
        metric_col = max(metric_candidates, key=lambda c: self.df[c].std()) if metric_candidates else None
        
        # Dimensions catégorielles par priorité
        dims_cat = {}
        
        # Dimension 1: Segmentation client/produit
        for pattern in ['segment', 'category', 'type', 'classe', 'groupe']:
            for col in cat_cols:
                if pattern in col.lower():
                    dims_cat['segment'] = col
                    break
        
        # Dimension 2: Localisation
        for pattern in ['region', 'country', 'state', 'city', 'zone']:
            for col in cat_cols:
                if pattern in col.lower():
                    dims_cat['region'] = col
                    break
        
        # Dimension 3: Autre catégorie importante
        if len(cat_cols) > 2:
            for col in cat_cols:
                if col not in dims_cat.values() and self.df[col].nunique() < 20:
                    dims_cat['category'] = col
                    break

        # === ÉTAPE 2: Générer des graphiques stratégiques ===
        
        print(f"[INFO] Métrique principale: {metric_col}")
        print(f"[INFO] Dimensions détectées: {dims_cat}")
        
        # Graph 1: Distribution de la métrique principale
        if metric_col:
            try:
                self.graph_distribution_numeric(metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_distribution_numeric échoué: {e}")
        
        # Graph 2: Anomalies (outliers)
        if metric_col:
            try:
                self.graph_boxplot_numeric(metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_boxplot_numeric échoué: {e}")
        
        # Graph 3: Métrique par Segment (croisement 1 cat + 1 num)
        if metric_col and 'segment' in dims_cat:
            try:
                self.graph_croise_moyenne(dims_cat['segment'], metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_croise_moyenne {dims_cat['segment']} x {metric_col} échoué: {e}")
        
        # Graph 4: Métrique par Région (croisement 1 cat + 1 num)
        if metric_col and 'region' in dims_cat:
            try:
                self.graph_croise_moyenne(dims_cat['region'], metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_croise_moyenne {dims_cat['region']} x {metric_col} échoué: {e}")
        
        # Graph 5: Répartition Segment x Région (croisement 2 cat)
        if 'segment' in dims_cat and 'region' in dims_cat:
            try:
                self.graph_croise_repartition(dims_cat['segment'], dims_cat['region'])
            except Exception as e:
                print(f"[DEBUG] graph_croise_repartition échoué: {e}")
        
        # Graph 6: Distribution d'une catégorie
        if cat_cols:
            try:
                primary_cat = next((c for c in cat_cols if self.df[c].nunique() < 15), cat_cols[0])
                self.graph_categorical_distribution(primary_cat, top_n=10)
            except Exception as e:
                print(f"[DEBUG] graph_categorical_distribution échoué: {e}")
        
        # Graph 7: Pie chart d'une catégorie
        if cat_cols:
            try:
                pie_cat = next((c for c in cat_cols if 5 < self.df[c].nunique() < 12), None)
                if pie_cat:
                    self.graph_pie_chart(pie_cat, top_n=8)
            except Exception as e:
                print(f"[DEBUG] graph_pie_chart échoué: {e}")
        
        # Graph 8: Corrélations si 2+ colonnes numériques
        if len(num_cols) >= 2:
            try:
                self.graph_correlation_matrix()
            except Exception as e:
                print(f"[DEBUG] graph_correlation_matrix échoué: {e}")
        
        # Graph 9: Scatter plot de 2 métriques (si disponible)
        if len(business_num_cols) >= 2:
            try:
                col1, col2 = business_num_cols[0], business_num_cols[1]
                self.graph_scatter_plot(col1, col2)
            except Exception as e:
                print(f"[DEBUG] graph_scatter_plot échoué: {e}")
        
        # === ÉTAPE 3: Graphiques MULTI-VARIABLES Premium ===
        
        # Graph 10: Bubble 3D (3-4 variables simultanément)
        if len(num_cols) >= 2:
            try:
                self.graph_bubble_3d()
            except Exception as e:
                print(f"[DEBUG] graph_bubble_3d échoué: {e}")
        
        # Graph 11: Sunburst hiérarchique (2-3 catégories)
        if len(cat_cols) >= 2:
            try:
                hierarchy = list(dims_cat.values())[:3]
                if len(hierarchy) >= 2:
                    self.graph_sunburst_hierarchie(hierarchy, value_col=metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_sunburst_hierarchie échoué: {e}")
        
        # Graph 12: Sankey flow (segment → région)
        if 'segment' in dims_cat and 'region' in dims_cat:
            try:
                self.graph_sankey_flow(dims_cat['segment'], dims_cat['region'], metric_col)
            except Exception as e:
                print(f"[DEBUG] graph_sankey_flow échoué: {e}")
        
        # === ÉTAPE 4: Remplir avec des graphiques supplémentaires ===
        
        # Graphiques supplémentaires: toutes les autres métriques
        for col in num_cols:
            if col != metric_col and len(self.generated_graphs) < 15:
                try:
                    self.graph_distribution_numeric(col)
                except Exception:
                    pass
        
        # Graphiques supplémentaires: toutes les autres catégories
        for col in cat_cols:
            if col not in dims_cat.values() and len(self.generated_graphs) < 15:
                try:
                    if 3 < self.df[col].nunique() < 20:
                        self.graph_categorical_distribution(col, top_n=10)
                except Exception:
                    pass
        
        print(f"[OK] {len(self.generated_graphs)} graphiques générés avec succès")
        return self.generated_graphs
    
    def get_graph_interpretation(self, graph_filename: str) -> str:
        """Génère une analyse textuelle d'un graphique pour affichage SOUS le graphe (sans emoji, mise en page claire)."""
        if 'distribution' in graph_filename.lower():
            return "<b>Distribution :</b> Ce graphique montre la répartition des valeurs. Les pics indiquent les zones de concentration. Les valeurs isolées peuvent être des anomalies."
        elif 'boxplot' in graph_filename.lower():
            return "<b>Anomalies :</b> Les points isolés sont des valeurs aberrantes (outliers). La boîte représente 50% des observations centrales. Analysez les outliers pour comprendre les cas exceptionnels."
        elif 'categories' in graph_filename.lower():
            return "<b>Catégories :</b> Répartition par groupe. Les barres hautes sont dominantes. Repérez les déséquilibres ou segments sous-exploités."
        elif 'correlation' in graph_filename.lower():
            return "<b>Corrélations :</b> Les zones rouges indiquent des relations positives, les bleues des négatives. Repérez les carrés serrés pour identifier les variables clés."
        elif 'scatter' in graph_filename.lower():
            return "<b>Relation X-Y :</b> Chaque point représente une observation. Une ligne droite indique une forte relation. Points dispersés = faible relation. Points isolés = cas exceptionnels."
        elif 'pie' in graph_filename.lower():
            return "<b>Composition :</b> Parts du total en pourcentage. Vérifiez si 1-2 catégories dominent (> 50%). Déséquilibre = opportunité d'optimisation."
        elif 'moyenne' in graph_filename.lower():
            return "<b>Performance par segment :</b> Les barres hautes sont les meilleurs résultats. Comparez les segments pour identifier les top performers et les retardataires."
        elif 'repartition' in graph_filename.lower():
            return "<b>Multi-catégorie :</b> Chaque couleur représente un type. Les empilements montrent la composition. Repérez les concentrations ou déséquilibres."
        elif 'bubble' in graph_filename.lower():
            return "<b>Multidimensionnel :</b> X et Y = 2 variables. Taille du point = 3ème variable. Couleur = catégorie. Les gros points isolés ont une forte influence."
        elif 'sunburst' in graph_filename.lower():
            return "<b>Hiérarchie :</b> De dehors vers dedans = du général au particulier. Cliquez sur les segments pour explorer les niveaux inférieurs."
        elif 'sankey' in graph_filename.lower():
            return "<b>Flux entre catégories :</b> L'épaisseur des bandes représente le volume. Suivez les chemins pour voir les transitions et concentrations majeures."
        else:
            return "<b>Analyse du graphique.</b>"

    def generate_graphs_from_questions(self, questions: List[dict]) -> List[str]:
        """Génère des graphiques adaptés à chaque question stratégique (20 max)."""
        print("[GRAPHIQUES] Génération ciblée sur les problématiques IA...")
        self.generated_graphs = []
        num_cols = self._get_numeric_cols()
        cat_cols = self._get_categorical_cols()
        date_cols = self._get_date_cols()
        used = set()
        for q in questions[:20]:
            qtext = q.get("question", "").lower()
            # Heuristique simple pour mapper question → type de graphique
            if any(x in qtext for x in ["évolution", "progression", "variation", "temps", "chronologie", "mois", "année", "date"]):
                # Courbe temporelle
                if date_cols and num_cols:
                    col_x = date_cols[0]
                    col_y = next((c for c in num_cols if c not in used), num_cols[0])
                    fname = self.graph_distribution_numeric(col_y)  # Peut être remplacé par une line plot si dispo
                    used.add(col_y)
                    if fname:
                        self.generated_graphs.append(fname)
            elif any(x in qtext for x in ["répartition", "catégorie", "segment", "groupe", "proportion", "part"]):
                # Catégories
                if cat_cols:
                    col = next((c for c in cat_cols if c not in used), cat_cols[0])
                    fname = self.graph_categorical_distribution(col)
                    used.add(col)
                    if fname:
                        self.generated_graphs.append(fname)
            elif any(x in qtext for x in ["corrélation", "relation", "lien", "impact"]):
                # Corrélation
                if len(num_cols) >= 2:
                    fname = self.graph_correlation_matrix()
                    if fname:
                        self.generated_graphs.append(fname)
            elif any(x in qtext for x in ["anomalie", "outlier", "valeur extrême", "exception"]):
                # Boxplot
                if num_cols:
                    col = next((c for c in num_cols if c not in used), num_cols[0])
                    fname = self.graph_boxplot_numeric(col)
                    used.add(col)
                    if fname:
                        self.generated_graphs.append(fname)
            elif any(x in qtext for x in ["moyenne", "performance", "score", "succès", "taux"]):
                # Croisement catégorie-numérique
                if cat_cols and num_cols:
                    col_cat = next((c for c in cat_cols if c not in used), cat_cols[0])
                    col_num = next((c for c in num_cols if c not in used), num_cols[0])
                    fname = self.graph_croise_moyenne(col_cat, col_num)
                    used.add(col_cat)
                    used.add(col_num)
                    if fname:
                        self.generated_graphs.append(fname)
            else:
                # Fallback: distribution numérique
                if num_cols:
                    col = next((c for c in num_cols if c not in used), num_cols[0])
                    fname = self.graph_distribution_numeric(col)
                    used.add(col)
                    if fname:
                        self.generated_graphs.append(fname)
            if len(self.generated_graphs) >= 20:
                break
        print(f"[✓] {len(self.generated_graphs)} graphiques générés pour les problématiques IA.")
        return self.generated_graphs