#!/usr/bin/env python3
"""
Application web d'analyse CSV - Interface moderne HTML/CSS
Backend Python léger avec Flask
"""

import os
import sys
import io
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from core_analysis import CSVAnalyzer
from graphiques import GraphicsGenerator
from rapport_generator import RapportGenerator
from web_scraper import WebScraper
from confidence_calculator import ConfidenceCalculator
import traceback

app = Flask(__name__, template_folder='.', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Custom JSON encoder pour gérer les types Pandas
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Pour Flask 3.x, utiliser json provider
try:
    from flask.json.provider import DefaultJSONProvider
    
    class CustomJSONProvider(DefaultJSONProvider):
        def default(self, o):
            if isinstance(o, (np.integer, np.int64, np.int32)):
                return int(o)
            elif isinstance(o, (np.floating, np.float64, np.float32)):
                if np.isnan(o):
                    return 0
                return float(o)
            elif isinstance(o, np.ndarray):
                return o.tolist()
            return super().default(o)
    
    app.json = CustomJSONProvider(app)
except ImportError:
    # Pour Flask < 3.x
    app.json_encoder = NumpyEncoder

# State globale
state = {
    'analyzer': None,
    'output_dir': None,
    'api_key': None,
    'loaded': False,
    'cleaned': False,
    'analyzed': False,
    'proposals': {},
    'renaming_map': {},
    'context': ''
}

# Dictionnaire de mapping pour suggestions de renommage
COLUMN_SUGGESTIONS = {
    # Abréviations courtes
    'dep': 'département',
    'com': 'commune',
    'agg': 'agglomération',
    'atm': 'atmosphère',
    'col': 'collision',
    'lum': 'luminosité',
    'int': 'intersection',
    'hrmn': 'heure_minute',
    'an': 'année',
    'jour': 'jour',
    'mois': 'mois',
    'num_acc': 'num_accident',
    'adr': 'adresse',
    'lat': 'latitude',
    'long': 'longitude',
    # Patterns communs
    'id': 'identifiant',
    'qty': 'quantité',
    'amt': 'montant',
    'addr': 'adresse',
    'temp': 'température',
    'val': 'valeur',
    'cnt': 'compte',
    'pct': 'pourcentage',
    'avg': 'moyenne',
    'max': 'maximum',
    'min': 'minimum',
}

def suggest_column_name(original_name: str) -> str:
    """Suggère un nom de colonne basé sur l'original"""
    lower_name = original_name.lower().strip()
    
    # Check exact match
    if lower_name in COLUMN_SUGGESTIONS:
        return COLUMN_SUGGESTIONS[lower_name]
    
    # Check partial matches
    for abbrev, full_name in COLUMN_SUGGESTIONS.items():
        if abbrev in lower_name:
            return full_name
    
    # Si c'est une abréviation courte (2-4 chars), capitaliser
    if len(lower_name) <= 4 and lower_name.isalpha():
        return lower_name.capitalize()
    
    # Return original if no suggestion
    return original_name


def get_api_key():
    """Récupère la clé API"""
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


@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Récupère l'état actuel"""
    return jsonify({
        'loaded': state['loaded'],
        'cleaned': state['cleaned'],
        'analyzed': state['analyzed'],
        'output_dir': state['output_dir'],
        'test_marker': 'FICHIER BIEN LU - 20260518'
    })


@app.route('/api/files')
def api_files():
    """Récupère la liste des CSV"""
    csv_files = sorted(set(list(Path(".").glob("*.csv")) + list(Path(".").glob("temp_*.csv"))))
    
    files = []
    for f in csv_files:
        try:
            size = f.stat().st_size / 1024 / 1024
            files.append({
                'name': f.name,
                'path': str(f),
                'size': f"{size:.2f} MB"
            })
        except:
            pass
    
    return jsonify({'files': files})


@app.route('/api/load', methods=['POST'])
def api_load():
    """Charge un CSV"""
    try:
        # Vérifier si c'est un upload de fichier ou une requête JSON
        if 'file' in request.files:
            # Upload de fichier
            file = request.files['file']
            if not file or file.filename == '':
                return jsonify({'error': 'Aucun fichier sélectionné'}), 400
            
            # Sauvegarder le fichier temporairement
            temp_path = f"temp_{file.filename}"
            file.save(temp_path)
            filepath = temp_path
        else:
            # Requête JSON avec filepath
            data = request.json
            filepath = data.get('filepath')
            
            if not filepath or not Path(filepath).exists():
                return jsonify({'error': 'Fichier non trouvé'}), 400
        
        api_key = state['api_key']
        if not api_key:
            return jsonify({'error': 'Clé API non configurée'}), 400
        
        state['analyzer'] = CSVAnalyzer(filepath, api_key=api_key)
        
        if not state['analyzer'].load_data():
            return jsonify({'error': 'Erreur lors du chargement'}), 400
        
        state['output_dir'] = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        Path(state['output_dir']).mkdir(exist_ok=True)
        
        # Analyser les colonnes
        proposals = state['analyzer'].analyze_columns()
        
        state['loaded'] = True
        
        columns = []
        cleaned_proposals = {}
        for col, prop in proposals.items():
            cleaned_prop = {}
            for key, val in prop.items():
                if isinstance(val, float) and np.isnan(val):
                    cleaned_prop[key] = 0
                else:
                    cleaned_prop[key] = val
            cleaned_proposals[col] = cleaned_prop
            
            # Suggest a new name based on the original
            suggested_name = suggest_column_name(col)
            
            columns.append({
                'name': col,
                'suggested_name': suggested_name,
                'description': cleaned_prop.get('description', col),
                'type': cleaned_prop.get('data_type', '?'),
                'confidence': int(cleaned_prop.get('confidence', 0) * 100)
            })
        
        state['proposals'] = cleaned_proposals
        
        return jsonify({
            'success': True,
            'rows': len(state['analyzer'].df),
            'cols': len(state['analyzer'].df.columns),
            'columns': columns,
            'output_dir': state['output_dir']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/proposals')
def api_proposals():
    """Récupère les propositions de colonnes"""
    try:
        if not state.get('proposals'):
            return jsonify({'error': 'Aucune proposition disponible'}), 400
        
        proposals_list = []
        for col_orig, proposal in state['proposals'].items():
            proposals_list.append({
                'original': col_orig,
                'proposed': proposal.get('proposed_name', col_orig),
                'type': proposal.get('data_type', '?'),
                'confidence': int(proposal.get('confidence', 0) * 100),
                'description': proposal.get('description', '')
            })
        
        return jsonify({
            'success': True,
            'proposals': proposals_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-preview')
def api_data_preview():
    """Obtient un aperçu des données"""
    try:
        if not state['analyzer']:
            return jsonify({'error': 'Aucun fichier chargé'}), 400
        
        df = state['analyzer'].df
        preview_data = df.head(5).to_dict(orient='records')
        
        return jsonify({
            'success': True,
            'data': preview_data,
            'rows': len(df),
            'cols': len(df.columns),
            'columns': list(df.columns)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-columns', methods=['POST'])
def api_update_columns():
    """Met à jour les noms et types de colonnes"""
    try:
        data = request.json
        updates = data.get('updates', {})
        
        if not state['analyzer']:
            return jsonify({'error': 'Aucun fichier chargé'}), 400
        
        # Renommer les colonnes dans proposals
        for col_orig, update_info in updates.items():
            if col_orig in state['proposals']:
                state['proposals'][col_orig]['proposed_name'] = update_info.get('name', col_orig)
                state['proposals'][col_orig]['type'] = update_info.get('type', '?')
        
        # Mettre à jour aussi le DataFrame
        rename_map = {}
        for col_orig, update_info in updates.items():
            if col_orig in state['analyzer'].df.columns:
                rename_map[col_orig] = update_info.get('name', col_orig)
        
        if rename_map:
            state['analyzer'].df = state['analyzer'].df.rename(columns=rename_map)
        
        state['renaming_map'] = rename_map
        
        return jsonify({
            'success': True,
            'message': 'Colonnes mises à jour',
            'updates': len(rename_map)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/context', methods=['POST'])
def api_context():
    """Définit le contexte métier"""
    try:
        data = request.json
        state['context'] = data.get('context', '')
        return jsonify({'success': True, 'context': state['context']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clean', methods=['POST'])
def api_clean():
    """Nettoie les données"""
    try:
        if not state['analyzer']:
            return jsonify({'error': 'Aucun fichier chargé'}), 400
        
        state['analyzer'].clean_data()
        
        rows_before = len(state['analyzer'].df)
        rows_after = len(state['analyzer'].cleaned_df)
        nulls_before = state['analyzer'].df.isna().sum().sum()
        nulls_after = state['analyzer'].cleaned_df.isna().sum().sum()
        
        state['cleaned'] = True
        
        return jsonify({
            'success': True,
            'rows_before': rows_before,
            'rows_after': rows_after,
            'nulls_before': nulls_before,
            'nulls_after': nulls_after,
            'reduction': 100 * (nulls_before - nulls_after) / max(nulls_before, 1)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Génère l'analyse avec graphiques pertinents pour chaque question"""
    try:
        if not state['cleaned']:
            return jsonify({'error': 'Veuillez d\'abord nettoyer les données'}), 400
        
        # Générer les questions
        questions = state['analyzer'].generate_strategic_questions_and_graphs()
        print(f"\n[DEBUG /api/analyze] {len(questions)} questions générées")
        if questions:
            print(f"[DEBUG] Première question: {questions[0]}")
        
        # Générer les graphiques PERTINENTS pour chaque question
        try:
            output_dir = state['output_dir']
            Path(output_dir).mkdir(exist_ok=True)
            graphics_gen = GraphicsGenerator(state['analyzer'].cleaned_df, output_dir)
            graphs = graphics_gen.generate_graphs_for_questions(questions)
            print(f"[OK] {len(graphs)} graphiques générés avec succès")
            print(f"[DEBUG] Graphes générés: {graphs[:3]}")
        except Exception as e:
            print(f"[WARN] Graphiques non générés: {str(e)}")
            import traceback as tb
            print(tb.format_exc())
            graphs = []
        
        state['analyzed'] = True
        
        # Construire la réponse avec questions ET graphiques appairés
        formatted_response = []
        for i, q in enumerate(questions, 1):
            # Trouver le graphique correspondant à cette question
            graph_file = None
            if i - 1 < len(graphs):
                graph_file = graphs[i - 1]
            
            question_text = q.get('question', q.get('text', f'Question {i}'))
            formatted_response.append({
                'id': i,
                'question': question_text,
                'utility': q.get('utilite', ''),
                'columns': q.get('colonnes', []),
                'graph_type': q.get('type_graphique', 'bar'),
                'graph_file': graph_file
            })
            print(f"[DEBUG Q{i}] question={question_text[:50]}, graph_file={graph_file}")
        
        return jsonify({
            'success': True,
            'questions': formatted_response,
            'questions_count': len(formatted_response),
            'graphs_count': len(graphs),
            'output_dir': str(output_dir)
        })
    
    except Exception as e:
        print(f"[ERROR /api/analyze] {str(e)}")
        import traceback as tb
        print(tb.format_exc())
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/export', methods=['POST'])
def api_export():
    """Exporte les données"""
    try:
        if not state['cleaned']:
            return jsonify({'error': 'Aucune donnée à exporter'}), 400
        
        output_path = Path(state['output_dir']) / "donnees_nettoyees.csv"
        state['analyzer'].cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
        
        return jsonify({
            'success': True,
            'path': str(output_path),
            'size': f"{output_path.stat().st_size / 1024:.2f} KB"
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report', methods=['POST'])
def api_report():
    """Génère le rapport"""
    try:
        if not state['analyzed']:
            return jsonify({'error': 'Veuillez d\'abord générer l\'analyse'}), 400
        
        rapport = RapportGenerator(state['output_dir'])
        
        # Récupérer les questions et propositions
        analyzer = state.get('analyzer')
        if not analyzer:
            return jsonify({'error': 'Analyseur non disponible'}), 400

        questions = getattr(analyzer, 'questions', []) or []
        proposals = getattr(analyzer, 'proposals', {}) or {}

        # Récupérer les graphiques générés pour les intégrer au rapport
        graphs = []
        graphs_embedded = []
        output_dir = Path(state['output_dir'])
        print(f"[DEBUG] /api/report output_dir={output_dir} exists={output_dir.exists()}")
        for graph_file in sorted(output_dir.glob('graph_*.html')):
            print(f"[DEBUG] /api/report graph trouvé: {graph_file.name}")
            graphs.append(graph_file.name)
            try:
                with open(graph_file, 'r', encoding='utf-8') as f:
                    graph_html = f.read()
                graphs_embedded.append(f"""
                <div class="graph-section">
                    {graph_html}
                </div>
                """)
            except Exception as e:
                print(f"[WARN] Impossible de lire {graph_file.name}: {e}")

        print(f"[DEBUG] /api/report graphs_count={len(graphs)} embedded_count={len(graphs_embedded)}")

        cleaned_df = getattr(analyzer, 'cleaned_df', None)
        nb_lignes = len(cleaned_df) if cleaned_df is not None else 0
        nb_colonnes = len(cleaned_df.columns) if cleaned_df is not None and hasattr(cleaned_df, 'columns') else 0
        
        # Générer le rapport HTML simple
        rapport_path = rapport.generate_html(
            titre="Rapport d'Analyse",
            nom_fichier="data.csv",
            nb_lignes=nb_lignes,
            nb_colonnes=nb_colonnes,
            renaming_map=proposals,
            questions=questions,
            anomalies_log={},
            graphs=graphs,
            graphs_embedded=graphs_embedded
        )

        # Sécurité: si le template n'a pas rendu la section graphiques,
        # l'injecter directement dans le fichier HTML généré.
        if graphs_embedded and rapport_path and Path(rapport_path).exists():
            report_html = Path(rapport_path).read_text(encoding='utf-8')
            if 'Visualisations Interactives' not in report_html:
                graphs_section = """
            <div class="section">
                <h3>5. Visualisations Interactives</h3>
                <p style="color: #64748b; margin-bottom: 20px;">Les graphiques suivants ont été générés automatiquement à partir de vos données.</p>
                {graphs_html}
            </div>
""".replace('{graphs_html}', '\n'.join(graphs_embedded))
                report_html = report_html.replace(
                    '<div class="section">\n                <h3>6. Recommandations Qualité</h3>',
                    graphs_section + '\n            <div class="section">\n                <h3>6. Recommandations Qualité</h3>'
                )
                Path(rapport_path).write_text(report_html, encoding='utf-8')
        
        if not rapport_path or not Path(rapport_path).exists():
            return jsonify({'error': 'Erreur lors de la génération du rapport'}), 400
        
        return jsonify({
            'success': True,
            'path': str(rapport_path),
            'graphs_count': len(graphs)
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/download/<path:filename>')
def api_download(filename):
    """Télécharge un fichier"""
    try:
        filepath = Path(filename)
        if filepath.exists():
            return send_file(filepath, as_attachment=True)
        return jsonify({'error': 'Fichier non trouvé'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/graph/<filename>')
def serve_graph(filename):
    """Serve graphique HTML avec le bon Content-Type"""
    try:
        if state['output_dir']:
            filepath = Path(state['output_dir']) / filename
            if filepath.exists() and filepath.suffix == '.html':
                from flask import Response
                with open(filepath, 'r', encoding='utf-8') as f:
                    return Response(f.read(), mimetype='text/html; charset=utf-8')
        return jsonify({'error': 'Graphique non trouvé'}), 404
    except Exception as e:
        print(f"[ERROR] Erreur serve_graph: {e}")
        return jsonify({'error': str(e)}), 500


# === NOUVELLES ROUTES: WEB SCRAPER + CONFIDENCE ===

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Scrape un tableau HTML depuis une URL ou du HTML pur"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL ou HTML requise'}), 400
        
        # Créer l'instance scraper (sera utilisée pour stats et sauvegarde)
        scraper = WebScraper(timeout=15)
        
        # Vérifier si c'est une URL ou du HTML pur
        is_html = url.strip().startswith('<') or url.strip().startswith('<!DOCTYPE')
        
        if is_html:
            # Traiter comme HTML pur
            print(f"[SCRAPE] HTML pur détecté ({len(url)} caractères)")
            try:
                df = pd.read_html(io.StringIO(url))[0]
                print(f"[OK] Tableau parsé: {len(df)} lignes × {len(df.columns)} colonnes")
            except Exception as e:
                print(f"[ERROR] Parsing HTML échoué: {e}")
                return jsonify({'error': f'HTML invalide: {str(e)}'}), 400
        else:
            # Traiter comme URL
            if not url.startswith('http'):
                url = 'https://' + url
            
            print(f"[SCRAPE] URL: {url}")
            df = scraper.scrape_best_table(url)
        
        if df is None or len(df) == 0:
            return jsonify({'error': 'Aucun tableau trouvé'}), 400
        
        stats = scraper.get_table_stats(df)
        
        # Sauvegarder le fichier scraped
        scraped_filename = f"scraped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        scraped_path = Path('scraped_data') / scraped_filename
        Path('scraped_data').mkdir(exist_ok=True)
        
        scraper.save_to_csv(df, str(scraped_path))
        
        return jsonify({
            'success': True,
            'filename': scraped_filename,
            'filepath': str(scraped_path),
            'stats': stats,
            'preview': df.head(5).to_dict(orient='records')
        })
    
    except Exception as e:
        print(f"[ERROR] Scrape failed: {e}")
        import traceback as tb
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 500


@app.route('/api/scrape-load', methods=['POST'])
def api_scrape_load():
    """Scrape une URL ET charge directement le tableau dans l'app"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL requise'}), 400
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        scraper = WebScraper(timeout=15)
        df = scraper.scrape_best_table(url)
        
        if df is None or len(df) == 0:
            return jsonify({'error': 'Aucun tableau trouvé'}), 400
        
        # Sauvegarder et charger dans l'app
        scraped_filename = f"scraped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        Path('scraped_data').mkdir(exist_ok=True)
        scraped_path = Path('scraped_data') / scraped_filename
        scraper.save_to_csv(df, str(scraped_path))
        
        # Charger directement dans l'analyseur
        api_key = state['api_key']
        if not api_key:
            return jsonify({'error': 'Clé API non configurée'}), 400
        
        state['analyzer'] = CSVAnalyzer(str(scraped_path), api_key=api_key)
        
        if not state['analyzer'].load_data():
            return jsonify({'error': 'Erreur lors du chargement'}), 400
        
        state['output_dir'] = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        Path(state['output_dir']).mkdir(exist_ok=True)
        
        proposals = state['analyzer'].analyze_columns()
        state['loaded'] = True
        
        columns = []
        cleaned_proposals = {}
        for col, prop in proposals.items():
            cleaned_prop = {}
            for key, val in prop.items():
                if isinstance(val, float) and np.isnan(val):
                    cleaned_prop[key] = 0
                else:
                    cleaned_prop[key] = val
            cleaned_proposals[col] = cleaned_prop
            
            columns.append({
                'name': col,
                'description': cleaned_prop.get('description', col),
                'type': cleaned_prop.get('data_type', '?'),
                'confidence': int(cleaned_prop.get('confidence', 0) * 100)
            })
        
        state['proposals'] = cleaned_proposals
        
        return jsonify({
            'success': True,
            'source': 'web_scraper',
            'url': url,
            'filename': scraped_filename,
            'rows': len(state['analyzer'].df),
            'cols': len(state['analyzer'].df.columns),
            'columns': columns,
            'output_dir': state['output_dir']
        })
    
    except Exception as e:
        print(f"[ERROR] Scrape-load failed: {e}")
        import traceback as tb
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 500


@app.route('/api/confidence', methods=['POST'])
def api_confidence():
    """Calcule les scores de confiance pour les colonnes"""
    try:
        if not state['analyzer'] or state['analyzer'].cleaned_df is None:
            # Fallback: utiliser le df original si cleaned_df n'existe pas
            if not state['analyzer'] or not hasattr(state['analyzer'], 'df') or state['analyzer'].df is None:
                return jsonify({'error': 'Aucune donnée disponible'}), 400
            df_to_check = state['analyzer'].df
        else:
            df_to_check = state['analyzer'].cleaned_df
        
        calc = ConfidenceCalculator(df_to_check)
        
        # Confiance par colonne
        col_confidence = calc.get_all_columns_confidence()
        
        # Score de confiance global
        overall_scores = [c['confidence'] for c in col_confidence.values()]
        global_score = np.mean(overall_scores) if overall_scores else 0.0
        
        return jsonify({
            'success': True,
            'global_confidence': round(global_score, 2),
            'global_icon': calc.get_confidence_icon(global_score),
            'columns': col_confidence,
            'quality_summary': 'Excellente ✓' if global_score >= 0.85 else 'Bonne ✓' if global_score >= 0.70 else 'Moyenne ⚠️'
        })
    
    except Exception as e:
        print(f"[ERROR] Confidence failed: {e}")
        import traceback as tb
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 500


@app.route('/api/question-confidence', methods=['POST'])
def api_question_confidence():
    """Calcule la confiance d'une question spécifique"""
    try:
        if not state['analyzer'] or state['analyzer'].cleaned_df is None:
            return jsonify({'error': 'Aucune donnée disponible'}), 400
        
        data = request.json
        columns = data.get('columns', [])
        
        calc = ConfidenceCalculator(state['analyzer'].cleaned_df)
        conf = calc.calculate_question_confidence(columns)
        
        return jsonify({
            'success': True,
            'confidence': conf
        })
    
    except Exception as e:
        print(f"[ERROR] Question confidence failed: {e}")
        import traceback as tb
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 500


def main():
    """Point d'entrée"""
    state['api_key'] = get_api_key()
    
    if not state['api_key']:
        print("\n❌ Erreur: Clé API Groq non trouvée")
        print("   Configurez GROQ_API_KEY ou secrets.toml\n")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("  [>>] Application web lancée".center(60))
    print("  Ouvrez: http://localhost:5000".center(60))
    print("="*60 + "\n")
    
    app.run(debug=False, host='127.0.0.1', port=5000)


if __name__ == '__main__':
    main()
