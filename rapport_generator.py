"""
Module de generation de rapports HTML/PDF professionnels.
Design premium avec HTML5 + CSS moderne + Jinja2.
"""

import json
from html import escape as html_escape
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from jinja2 import Template

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    print(f"[AVERTISSEMENT] WeasyPrint non disponible: {type(e).__name__}")
    print("Les rapports HTML fonctionnent normalement. PDF via reportlab disponible.")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[INFO] ReportLab non disponible pour PDF via reportlab")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ titre }}</title>
    <!-- Plotly for interactive charts -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        
        /* PAGE DE GARDE CORPORATE */
        .cover-page { background-color: #0f172a; color: #f8fafc; padding: 100px 50px; text-align: center; page-break-after: always; min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; border-bottom: 8px solid #3b82f6; }
        .cover-page h1 { font-size: 48px; margin-bottom: 20px; font-weight: 800; letter-spacing: -1px; }
        .cover-page p { font-size: 22px; margin-bottom: 10px; color: #94a3b8; }
        .cover-page .meta { margin-top: 60px; font-size: 14px; color: #cbd5e1; border-top: 1px solid #334155; padding-top: 30px; display: flex; gap: 20px; justify-content: center; }
        
        /* ENTETE */
        .header { background-color: #f1f5f9; color: #0f172a; padding: 30px 50px; margin-bottom: 40px; border-bottom: 1px solid #e2e8f0; border-left: 8px solid #3b82f6; }
        .header h2 { font-size: 28px; font-weight: 700; margin-bottom: 5px; }
        .header p { font-size: 16px; color: #64748b; }
        
        /* CONTENU */
        .content { padding: 0 50px; }
        .section { margin-bottom: 50px; page-break-inside: avoid; }
        .section h3 { font-size: 22px; color: #0f172a; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }
        
        /* TABLEAU SOMBRE ET ELEGANT */
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }
        table th { background-color: #0f172a; color: white; padding: 12px 15px; text-align: left; font-weight: 600; }
        table td { padding: 12px 15px; border-bottom: 1px solid #e2e8f0; color: #334155; }
        table tbody tr:nth-child(even) { background-color: #f8fafc; }
        
        /* CARTES INFO SANS GRADIENT */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .info-card { background-color: white; padding: 20px; border-radius: 6px; border: 1px solid #e2e8f0; border-left: 4px solid #0f172a; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .info-card.success { border-left-color: #10b981; }
        .info-card.warning { border-left-color: #f59e0b; }
        .info-card h4 { color: #64748b; margin-bottom: 5px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        .info-card p { font-size: 28px; font-weight: 700; color: #0f172a; }
        
        /* QUESTIONS STRATEGIQUES PRO */
        .question-card { background-color: white; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; padding: 20px; margin-bottom: 15px; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .question-card .number { display: inline-block; background-color: #eff6ff; color: #3b82f6; width: 28px; height: 28px; border-radius: 4px; text-align: center; line-height: 28px; margin-right: 12px; font-weight: 700; font-size: 14px; }
        .question-card .question-text { font-size: 16px; color: #0f172a; margin-bottom: 8px; font-weight: 600; display: inline; }
        .question-card .utility { font-size: 14px; color: #64748b; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2e8f0; }
        
        /* ANOMALIES LOG */
        .anomaly-item { background-color: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
        .anomaly-item .col-name { font-weight: 700; color: #92400e; }
        .anomaly-item .anomaly-desc { font-size: 13px; color: #b45309; margin-top: 5px; }
        
        /* PIED DE PAGE */
        .footer { background-color: #0f172a; color: #94a3b8; text-align: center; padding: 25px; margin-top: 40px; font-size: 13px; }
        
        code { background-color: #f1f5f9; padding: 4px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 13px; color: #3b82f6; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .graph-container { background-color: white; padding: 20px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center; }
        .graph-container h4 { color: #0f172a; font-size: 15px; margin-bottom: 5px; }
        .graph-container p { color: #64748b; font-size: 13px; }
        
        .graph-section {
            background-color: white;
            padding: 30px 20px;
            margin: 20px 0;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            page-break-inside: avoid;
        }
        
        .graph-section h4 {
            color: #1e293b;
            font-size: 16px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .plotly-graph {
            width: 100%;
            min-height: 500px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="cover-page">
            <h1>Rapport d'Analyse CSV</h1>
            <p>Intelligence Artificielle | Nettoyage de Données</p>
            <div class="meta">
                <p><strong>Fichier:</strong> {{ nom_fichier }}</p>
                <p><strong>Date:</strong> {{ date_rapport }}</p>
                <p><strong>Lignes:</strong> {{ nb_lignes }} | <strong>Colonnes:</strong> {{ nb_colonnes }}</p>
            </div>
        </div>
        
        <div class="header">
            <h2>Synthèse Technique</h2>
            <p>Analyse des anomalies</p>
            {% if contexte_metier %}
            <div style="margin-top:18px;padding:12px 18px;background:#e0f2fe;border-left:5px solid #2563eb;border-radius:4px;color:#0f172a;font-size:16px;">
                <b>Contexte métier utilisé :</b> {{ contexte_metier }}
            </div>
            {% endif %}
        </div>
        <div class="content">
            <div class="section">
                <h3>1. Résumé d'Exécution</h3>
                <div class="stats-grid">
                    <div class="info-card success">
                        <h4>Données Chargées</h4>
                        <p>{{ nb_lignes }} lignes</p>
                    </div>
                    <div class="info-card success">
                        <h4>Colonnes Analysées</h4>
                        <p>{{ nb_colonnes }} colonnes</p>
                    </div>
                    <div class="info-card{% if nb_anomalies > 0 %} warning{% else %} success{% endif %}">
                        <h4>Anomalies Détectées</h4>
                        <p>{{ nb_anomalies }}</p>
                    </div>
                    <div class="info-card success">
                        <h4>Précision IA</h4>
                        <p>{{ precision_moyenne }}%</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h3>2. Architecture des Données (Résumé)</h3>
                <div class="stats-grid">
                    <div class="info-card">
                        <h4>Colonnes Originales</h4>
                        <p>{{ renaming_map|length }}</p>
                    </div>
                    <div class="info-card">
                        <h4>Colonnes Nettoyées</h4>
                        <p>{{ renaming_map|length }}</p>
                    </div>
                    <div class="info-card success">
                        <h4>Qualité Moyenne</h4>
                        <p>{{ (precision_moyenne * 0.95)|round|int }}%</p>
                    </div>
                </div>
                <p style="color: #64748b; font-size: 14px; margin-top: 15px;">
                    Les colonnes suivantes ont été identifiées et nettoyées :
                    {% set col_names = [] %}
                    {% for col in renaming_map.keys() %}
                        {% if col_names.append(col) %}{% endif %}
                    {% endfor %}
                    <code style="background-color: #f8fafc; padding: 8px 12px; border-radius: 4px; display: inline-block; margin-top: 8px;">
                        {{ col_names|join(', ') }}
                    </code>
                </p>
            </div>
            
            <div class="section">
                <h3>3. Indicateurs & Questions Stratégiques</h3>
                {% for question in questions %}
                <div class="question-card">
                    <span class="number">{{ loop.index }}</span>
                    <div class="question-text">{{ question.get('question', question.get('text', 'N/A')) }}</div>
                    <div class="utility">{{ question.get('utilite', question.get('utility', 'N/A')) }}</div>
                </div>
                {% endfor %}
            </div>
            
            {% if anomalies_log %}
            <div class="section">
                <h3>4. Journal de Nettoyage</h3>
                {% for col, details in anomalies_log.items() %}
                    {% if details.problems %}
                    <div class="anomaly-item">
                        <div class="col-name">{{ col }}</div>
                        <div class="anomaly-desc">
                            {% for problem in details.problems %}
                                • {{ problem }}<br>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                {% endfor %}
            </div>
            {% endif %}
            
            
            {% if graphs %}
            <div class="section">
                <h3>5. Visualisations Interactives</h3>
                <p style="color: #64748b; margin-bottom: 20px;">Les graphiques suivants ont été générés automatiquement à partir de vos données.</p>
                {% for graph_html in graphs_embedded %}
                    {{ graph_html|safe }}
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="section">
                <h3>6. Recommandations Qualité</h3>
                <ul style="color: #475569; padding-left: 20px;">
                    <li style="margin-bottom: 8px;">Valider les règles métier avec les équipes opérationnelles.</li>
                    <li style="margin-bottom: 8px;">Consulter le journal des anomalies pour identifier la source des erreurs de saisie.</li>
                    <li style="margin-bottom: 8px;">Conserver les données originales (CSV brut) en archive sécurisée.</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Rapport généré le {{ date_rapport }} | Document Confidentiel</p>
        </div>
    </div>
</body>
</html>
"""


class RapportGenerator:
    """Generateur de rapports HTML/PDF."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html(self,
                     titre: str = "Rapport d'Analyse",
                     nom_fichier: str = "data.csv",
                     nb_lignes: int = 0,
                     nb_colonnes: int = 0,
                     renaming_map: Dict = None,
                     questions: List[Dict] = None,
                     anomalies_log: Dict = None,
                     graphs: List[str] = None,
                        contexte_metier: str = "",
                     **kwargs) -> Path:
        """Genere un rapport HTML professionnel."""
        
        # Calculs
        nb_anomalies = sum(
            len(details.get('problems', []))
            for details in (anomalies_log or {}).values()
        )
        
        # Extraction confiances
        confidences = []
        if renaming_map and isinstance(renaming_map, dict):
            for mapping in renaming_map.values():
                if isinstance(mapping, dict) and 'confidence' in mapping:
                    confidences.append(mapping['confidence'])
        
        precision_moyenne = round(sum(confidences) / len(confidences) * 100) if confidences else 100

        graphs_list = graphs or []
        graphs_embedded = kwargs.get('graphs_embedded', []) or []

        if not graphs_list or not graphs_embedded:
            discovered_graphs = sorted(self.output_dir.glob('graph_*.html'))
            print(f"[DEBUG] RapportGenerator discovered_graphs={len(discovered_graphs)} in {self.output_dir}")

            if not graphs_list:
                graphs_list = [graph_file.name for graph_file in discovered_graphs]

            if not graphs_embedded:
                for graph_file in discovered_graphs:
                    try:
                        with open(graph_file, 'r', encoding='utf-8') as f:
                            graph_html = f.read()
                        graphs_embedded.append(f"""
                        <div class="graph-section">
                            {graph_html}
                        </div>
                        """)
                    except Exception:
                        continue
        
        # Template
        template = Template(HTML_TEMPLATE)
        
        html_content = template.render(
            titre=titre,
            nom_fichier=nom_fichier,
            date_rapport=datetime.now().strftime("%d/%m/%Y %H:%M"),
            nb_lignes=nb_lignes,
            nb_colonnes=nb_colonnes,
            nb_anomalies=nb_anomalies,
            precision_moyenne=precision_moyenne,
            renaming_map=renaming_map or {},
            questions=questions or [],
            anomalies_log=anomalies_log or {},
            graphs=graphs_list,
            graphs_embedded=graphs_embedded,
                contexte_metier=contexte_metier,
        )
        
        # Sauvegarde HTML
        html_path = self.output_dir / "rapport.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[OK] Rapport HTML genere : {html_path} | graphs={len(graphs_list)} embedded={len(graphs_embedded)} | html_len={len(html_content)}")
        
        return html_path

    def _generate_pdf_from_payload(self,
                                   report_payload: Dict[str, Any],
                                   output_filename: str = "rapport.pdf") -> Optional[Path]:
        """Génère un PDF structuré directement depuis les données (robuste, sans dépendre du parsing HTML)."""
        if not REPORTLAB_AVAILABLE:
            return None

        try:
            pdf_path = self.output_dir / output_filename
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=0.6 * inch,
                leftMargin=0.6 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'PayloadTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#0f172a'),
                spaceAfter=14,
            )
            h_style = ParagraphStyle(
                'PayloadHeading',
                parent=styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#0f172a'),
                spaceBefore=10,
                spaceAfter=6,
            )
            normal_style = ParagraphStyle(
                'PayloadNormal',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=3,
            )
            muted_style = ParagraphStyle(
                'PayloadMuted',
                parent=normal_style,
                fontSize=9,
                textColor=colors.HexColor('#64748b'),
            )

            def safe_text(value: Any, max_len: int = 2200) -> str:
                text = " ".join(str(value).split())
                if not text:
                    return ""
                if len(text) > max_len:
                    text = text[:max_len - 3] + "..."
                text = text.encode('latin-1', errors='ignore').decode('latin-1')
                return html_escape(text)

            def add_line(story_ref: List, value: Any, style_ref, spacer: float = 0.03):
                txt = safe_text(value)
                if txt:
                    story_ref.append(Paragraph(txt, style_ref))
                    if spacer > 0:
                        story_ref.append(Spacer(1, spacer * inch))

            story = []

            titre = report_payload.get('titre', "Rapport d'Analyse CSV")
            story.append(Paragraph(safe_text(titre), title_style))

            add_line(story, f"Fichier : {report_payload.get('nom_fichier', 'data.csv')}", muted_style)
            add_line(story, f"Date : {report_payload.get('date_rapport', datetime.now().strftime('%d/%m/%Y %H:%M'))}", muted_style)

            if report_payload.get('contexte_metier'):
                add_line(story, f"Contexte métier : {report_payload.get('contexte_metier')}", muted_style)

            story.append(Spacer(1, 0.08 * inch))

            story.append(Paragraph("Résumé d'exécution", h_style))
            stats_table_data = [
                ["Indicateur", "Valeur"],
                ["Lignes", str(report_payload.get('nb_lignes', 0))],
                ["Colonnes", str(report_payload.get('nb_colonnes', 0))],
                ["Anomalies détectées", str(report_payload.get('nb_anomalies', 0))],
                ["Précision IA", f"{report_payload.get('precision_moyenne', 100)}%"],
                ["Graphiques", str(len(report_payload.get('graphs', []) or []))],
            ]
            stats_table = Table(stats_table_data, colWidths=[2.6 * inch, 3.9 * inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.1 * inch))

            renaming_map = report_payload.get('renaming_map', {}) or {}
            if renaming_map:
                story.append(Paragraph("Colonnes traitées", h_style))
                col_names = ", ".join(list(renaming_map.keys())[:60])
                add_line(story, col_names if col_names else "Aucune colonne", muted_style)

            questions = report_payload.get('questions', []) or []
            if questions:
                story.append(Paragraph("Questions stratégiques", h_style))
                for idx, q in enumerate(questions[:25], 1):
                    q_text = q.get('question', q.get('text', '')) if isinstance(q, dict) else str(q)
                    if q_text:
                        add_line(story, f"{idx}. {q_text}", normal_style)
                    if isinstance(q, dict):
                        util = q.get('utilite', q.get('utility', ''))
                        if util:
                            add_line(story, f"Utilité: {util}", muted_style)

            anomalies_log = report_payload.get('anomalies_log', {}) or {}
            anomaly_lines = []
            for col, details in anomalies_log.items():
                problems = details.get('problems', []) if isinstance(details, dict) else []
                for pb in problems:
                    anomaly_lines.append(f"{col}: {pb}")

            if anomaly_lines:
                story.append(Paragraph("Journal des anomalies", h_style))
                for line in anomaly_lines[:120]:
                    add_line(story, f"- {line}", normal_style)

            graphs = report_payload.get('graphs', []) or []
            if graphs:
                story.append(Paragraph("Visualisations", h_style))
                add_line(story, "Version PDF: snapshots statiques des graphiques (si disponibles).", muted_style)
                for g in graphs[:12]:
                    graph_name = str(g)
                    graph_png_path = self.output_dir / Path(graph_name).with_suffix('.png')

                    add_line(story, f"Graphique: {Path(graph_name).name}", muted_style)

                    if graph_png_path.exists():
                        try:
                            graph_img = Image(str(graph_png_path))
                            max_w = doc.width
                            max_h = 3.7 * inch

                            # Conserver le ratio tout en restant dans la page.
                            if graph_img.drawWidth > 0 and graph_img.drawHeight > 0:
                                ratio = min(max_w / graph_img.drawWidth, max_h / graph_img.drawHeight)
                                if ratio < 1:
                                    graph_img.drawWidth *= ratio
                                    graph_img.drawHeight *= ratio

                            story.append(graph_img)
                            story.append(Spacer(1, 0.07 * inch))
                        except Exception as e:
                            add_line(story, f"(Image non intégrée: {type(e).__name__})", muted_style)
                    else:
                        add_line(story, "(Aperçu image non disponible, voir version HTML interactive)", muted_style)

            story.append(Paragraph("Recommandations", h_style))
            add_line(story, "- Valider les règles métier avec les équipes opérationnelles.", normal_style)
            add_line(story, "- Vérifier les anomalies signalées avant diffusion des résultats.", normal_style)
            add_line(story, "- Conserver le CSV brut et le CSV nettoyé pour auditabilité.", normal_style)

            doc.build(story)
            print(f"[OK] Rapport PDF structuré généré (payload): {pdf_path}")
            return pdf_path

        except Exception as e:
            print(f"[ERREUR Payload PDF] {e}")
            return None

    def generate_pdf(self,
                    html_content: str = None,
                    html_path: Path = None,
                    output_filename: str = "rapport.pdf",
                    report_payload: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """Genere un rapport PDF depuis HTML (WeasyPrint si disponible, sinon reportlab)."""
        
        # Essayer WeasyPrint en premier
        if WEASYPRINT_AVAILABLE:
            try:
                if html_path is None:
                    html_path = self.output_dir / "rapport.html"
                
                pdf_path = self.output_dir / output_filename
                HTML(str(html_path)).write_pdf(str(pdf_path))
                print(f"[OK] Rapport PDF genere (WeasyPrint): {pdf_path}")
                return pdf_path
            except Exception as e:
                print(f"[ERREUR WeasyPrint] {e}")
                print("[INFO] Tentative avec ReportLab...")
        
        # Fallback sur reportlab
        if REPORTLAB_AVAILABLE:
            try:
                if report_payload:
                    payload_pdf = self._generate_pdf_from_payload(
                        report_payload=report_payload,
                        output_filename=output_filename
                    )
                    if payload_pdf:
                        return payload_pdf

                from bs4 import BeautifulSoup
                pdf_path = self.output_dir / output_filename
                
                # Lire le HTML et extraire le texte principal
                if html_path is None:
                    html_path = self.output_dir / "rapport.html"
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')

                # Retirer scripts/styles pour éviter un parsing bruité (graphiques Plotly très lourds).
                for tag in soup(['script', 'style', 'noscript']):
                    tag.decompose()
                
                # Créer PDF avec reportlab
                doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                       rightMargin=0.5*inch, leftMargin=0.5*inch,
                                       topMargin=0.75*inch, bottomMargin=0.75*inch)
                
                story = []
                styles = getSampleStyleSheet()
                
                # Style personnalisé
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=20,
                    textColor=colors.HexColor('#0f172a'),
                    spaceAfter=20,
                    alignment=TA_CENTER
                )
                
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.HexColor('#0f172a'),
                    spaceAfter=12,
                    spaceBefore=12
                )

                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=14,
                    spaceAfter=4,
                    textColor=colors.HexColor('#1f2937')
                )

                muted_style = ParagraphStyle(
                    'Muted',
                    parent=normal_style,
                    fontSize=9,
                    textColor=colors.HexColor('#64748b')
                )

                bullet_style = ParagraphStyle(
                    'Bullet',
                    parent=normal_style,
                    leftIndent=12,
                    bulletIndent=2
                )

                def normalize_text(value: str, max_len: int = 2500) -> str:
                    """Nettoie et protège le texte pour ReportLab (évite caractères non supportés)."""
                    text = " ".join(str(value).split())
                    if not text:
                        return ""
                    if len(text) > max_len:
                        text = text[:max_len - 3] + "..."
                    # Helvetica gère latin-1 mais pas certains caractères (ex: emoji).
                    text = text.encode('latin-1', errors='ignore').decode('latin-1')
                    return html_escape(text)

                def add_line(text: str, style=normal_style, spacer_inch: float = 0.03):
                    cleaned = normalize_text(text)
                    if cleaned:
                        story.append(Paragraph(cleaned, style))
                        if spacer_inch > 0:
                            story.append(Spacer(1, spacer_inch * inch))
                
                # Titre
                title = soup.select_one('.cover-page h1') or soup.find('h1')
                if title:
                    story.append(Paragraph(normalize_text(title.get_text(' ', strip=True)), title_style))
                    story.append(Spacer(1, 0.2*inch))

                # Métadonnées de couverture
                for meta in soup.select('.cover-page .meta p'):
                    add_line(meta.get_text(' ', strip=True), muted_style)

                story.append(Spacer(1, 0.1 * inch))

                # Entête synthèse
                header_h2 = soup.select_one('.header h2')
                if header_h2:
                    story.append(Paragraph(normalize_text(header_h2.get_text(' ', strip=True)), heading_style))
                for header_p in soup.select('.header p'):
                    add_line(header_p.get_text(' ', strip=True), normal_style)

                # Contexte métier éventuel
                for context_box in soup.select('.header div'):
                    ctxt = context_box.get_text(' ', strip=True)
                    if ctxt:
                        add_line(ctxt, muted_style)

                story.append(Spacer(1, 0.08 * inch))
                
                # Contenu principal
                main_content = soup.find('div', {'class': 'content'})
                if main_content:
                    sections = main_content.find_all('div', {'class': 'section'}, recursive=False)
                    for idx, section in enumerate(sections, 1):
                        # Titre section
                        section_title = section.find('h3')
                        if section_title:
                            story.append(Paragraph(normalize_text(section_title.get_text(' ', strip=True)), heading_style))
                            story.append(Spacer(1, 0.1*inch))

                        # Cartes de stats
                        for info_card in section.find_all('div', {'class': 'info-card'}):
                            card_h4 = info_card.find('h4')
                            card_p = info_card.find('p')
                            label = card_h4.get_text(' ', strip=True) if card_h4 else ''
                            value = card_p.get_text(' ', strip=True) if card_p else ''
                            if label or value:
                                add_line(f"{label}: {value}", normal_style)

                        # Questions stratégiques
                        question_cards = section.find_all('div', {'class': 'question-card'})
                        for q_card in question_cards[:40]:
                            question_text = q_card.find('div', {'class': 'question-text'})
                            utility_text = q_card.find('div', {'class': 'utility'})
                            if question_text:
                                add_line(f"- {question_text.get_text(' ', strip=True)}", bullet_style)
                            if utility_text:
                                add_line(f"Utilité: {utility_text.get_text(' ', strip=True)}", muted_style)

                        # Journal d'anomalies
                        anomalies = section.find_all('div', {'class': 'anomaly-item'})
                        for anomaly in anomalies[:80]:
                            col_name = anomaly.find('div', {'class': 'col-name'})
                            desc = anomaly.find('div', {'class': 'anomaly-desc'})
                            left = col_name.get_text(' ', strip=True) if col_name else 'Anomalie'
                            right = desc.get_text(' ', strip=True) if desc else ''
                            add_line(f"- {left}: {right}", bullet_style)

                        # Listes de recommandations
                        for li in section.find_all('li'):
                            text = li.get_text(' ', strip=True)
                            if text:
                                add_line(f"- {text}", bullet_style)

                        # Paragraphes standards (hors cartes/questions/anomalies)
                        paragraphs = section.find_all('p')
                        for p in paragraphs:
                            parent_classes = p.parent.get('class', []) if p.parent else []
                            if any(x in parent_classes for x in ['info-card', 'question-card', 'anomaly-item']):
                                continue
                            text = p.get_text(' ', strip=True)
                            if text:
                                add_line(text, normal_style)

                        # Blocs code (liste des colonnes)
                        for code in section.find_all('code'):
                            code_text = code.get_text(' ', strip=True)
                            if code_text:
                                add_line(f"Colonnes: {code_text}", muted_style)

                        # Graphiques: mention textuelle dans le PDF
                        graph_sections = section.find_all('div', {'class': 'graph-section'})
                        if graph_sections:
                            add_line(
                                f"{len(graph_sections)} visualisation(s) interactive(s) disponibles dans la version HTML.",
                                muted_style
                            )
                        
                        # Espacement entre sections (sans forcer une page vide)
                        if idx < len(sections):
                            story.append(Spacer(1, 0.12 * inch))

                # Fallback ultime: texte brut si extraction structurée trop pauvre.
                if len(story) <= 2:
                    fallback_text = main_content.get_text('\n', strip=True) if main_content else soup.get_text('\n', strip=True)
                    lines = [ln.strip() for ln in fallback_text.splitlines() if ln.strip()]
                    story.append(Paragraph("Rapport d'Analyse CSV", title_style))
                    story.append(Spacer(1, 0.1 * inch))
                    for line in lines[:250]:
                        add_line(line, normal_style)
                
                # Build PDF
                doc.build(story)
                print(f"[OK] Rapport PDF genere (ReportLab): {pdf_path}")
                return pdf_path
                
            except Exception as e:
                print(f"[ERREUR ReportLab] {e}")
                return None
        
        # Aucune option disponible
        print("[AVERTISSEMENT] Aucun générateur PDF disponible")
        print("Installez WeasyPrint: pip install weasyprint")
        print("Ou ReportLab est déjà installé (pip install reportlab beautifulsoup4)")
        return None

    def generate_complete_report(self,
                                df: pd.DataFrame,
                                renaming_map: Dict,
                                proposals: Dict,
                                questions: Optional[List] = None,
                                anomalies_log: Optional[Dict] = None,
                                graphs: Optional[List[str]] = None,
                                nom_fichier: str = "data.csv",
                                contexte_metier: str = "") -> Dict[str, Path]:
        """Génération complète HTML + PDF + JSON avec correction de formatage."""
        results = {}
        
        # 1. Préparation des graphiques pour l'intégration HTML
        graphs_embedded = []
        questions_list = questions or []
        max_len = max(len(graphs or []), len(questions_list))
        for idx in range(max_len):
            graph_file = (graphs or [None]*max_len)[idx] if idx < len(graphs or []) else None
            q = questions_list[idx] if idx < len(questions_list) else {}
            # Bloc question + utilité
            q_html = f'<div class="question-card">'
            q_html += f'<span class="number">{idx+1}</span>'
            q_html += f'<div class="question-text">{q.get('question', q.get('text', 'Question stratégique'))}</div>'
            if q.get('utilite') or q.get('utility'):
                q_html += f'<div class="utility">{q.get('utilite', q.get('utility', ''))}</div>'
            q_html += '</div>'
            # Bloc graphique
            if graph_file:
                graph_path = self.output_dir / graph_file
                if graph_path.exists():
                    try:
                        # LIRE LE CONTENU COMPLET DU FICHIER HTML ET L'INTÉGRER DIRECTEMENT
                        with open(graph_path, 'r', encoding='utf-8') as gf:
                            graph_content = gf.read()
                        # Extraire le body du graphique pour éviter les doubles <html>
                        if '<body>' in graph_content:
                            graph_body = graph_content.split('<body>', 1)[1].split('</body>', 1)[0]
                        else:
                            graph_body = graph_content
                        obj_html = f'<div class="graph-section">{q_html}<div style="border:1px solid #e0e7ef;border-radius:8px;overflow:hidden;margin:15px 0;">{graph_body}</div>'
                    except Exception as e:
                        obj_html = f'<div class="graph-section">{q_html}<div style="color:#b91c1c;">Erreur chargement graphique: {e}</div>'
                else:
                    obj_html = f'<div class="graph-section">{q_html}<div style="color:#b91c1c;">Graphique non généré ou manquant : {graph_file}</div>'
            else:
                obj_html = f'<div class="graph-section">{q_html}<div style="color:#b91c1c;">Aucun graphique associé.</div>'
            # Bloc interprétation IA (toujours sous le graphique)
            if q.get('interpretations') and isinstance(q['interpretations'], list):
                for interp in q['interpretations']:
                    if interp:
                        obj_html += f'<div style="margin:8px 0 0 0;padding:8px 12px;background:#e0f7fa;border-left:4px solid #3b82f6;border-radius:3px;color:#065f46;font-size:14px;">💡 {interp}</div>'
            obj_html += '</div>'
            graphs_embedded.append(obj_html)
        
        # 2. Nettoyage et formatage des questions stratégiques
        formatted_questions = []
        if questions:
            for idx, q in enumerate(questions, 1):
                if isinstance(q, str):
                    if "Utilité" in q:
                        parts = q.split("Utilité", 1)
                        formatted_questions.append({
                            'text': parts[0].replace(f"{idx}.", "").strip(),
                            'utility': parts[1].replace(":", "").strip()
                        })
                    else:
                        formatted_questions.append({'text': q, 'utility': ''})
                elif isinstance(q, dict):
                    formatted_questions.append(q)
        
        # 3. Construction du mapping enrichi pour le tableau HTML
        enriched_mapping = {}
        for col, new_name in renaming_map.items():
            prop = proposals.get(col, {})
            enriched_mapping[col] = {
                'proposed_name': new_name,
                'data_type': prop.get('data_type', 'unknown'),
                'confidence': prop.get('confidence', 0.5)
            }
        
        # 4. Génération effective du fichier HTML
        html_path = self.generate_html(
            titre="Rapport d'Analyse CSV",
            nom_fichier=nom_fichier,
            nb_lignes=len(df),
            nb_colonnes=len(df.columns),
            renaming_map=enriched_mapping,
            questions=formatted_questions,
            anomalies_log=anomalies_log or {},
            graphs=graphs or [],
            graphs_embedded=graphs_embedded,
            contexte_metier=contexte_metier
        )
        results['html'] = html_path
        
        # 5. Tentative de génération PDF
        confidence_values = [
            m.get('confidence', 0.5)
            for m in enriched_mapping.values()
            if isinstance(m, dict)
        ]
        precision_moyenne = round(sum(confidence_values) / len(confidence_values) * 100) if confidence_values else 100
        nb_anomalies = sum(
            len(details.get('problems', []))
            for details in (anomalies_log or {}).values()
            if isinstance(details, dict)
        )

        report_payload = {
            'titre': "Rapport d'Analyse CSV",
            'nom_fichier': nom_fichier,
            'date_rapport': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'nb_lignes': len(df),
            'nb_colonnes': len(df.columns),
            'nb_anomalies': nb_anomalies,
            'precision_moyenne': precision_moyenne,
            'renaming_map': enriched_mapping,
            'questions': formatted_questions,
            'anomalies_log': anomalies_log or {},
            'graphs': graphs or [],
            'contexte_metier': contexte_metier,
        }

        pdf_path = self.generate_pdf(html_path=html_path, report_payload=report_payload)
        if pdf_path:
            results['pdf'] = pdf_path
            
        return results
