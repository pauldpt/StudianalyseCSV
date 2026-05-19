#!/usr/bin/env python3
"""
Script de test rapide - Verifie que l'installation fonctionne.
Usage: python test_installation.py
"""

import sys
import os
from pathlib import Path

def print_section(title):
    """Affiche un titre."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}\n")

def test_python():
    """Verifie la version Python."""
    print_section("1. Version Python")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python {version}")
    if sys.version_info < (3, 10):
        print("⚠️  AVERTISSEMENT: Python 3.10+ recommande")
        return False
    print("✅ OK")
    return True

def test_imports():
    """Teste les imports des modules."""
    print_section("2. Imports des modules")
    
    modules = [
        ("pandas", "Manipulation donnees"),
        ("numpy", "Calculs numeriques"),
        ("groq", "API Groq"),
        ("rapidfuzz", "Fuzzy matching"),
        ("streamlit", "Interface web"),
        ("plotly", "Graphiques"),
        ("jinja2", "Templating"),
    ]
    
    all_ok = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name:15} - {description}")
        except ImportError as e:
            print(f"❌ {module_name:15} - MANQUANT")
            all_ok = False
    
    return all_ok

def test_files():
    """Verifie les fichiers importants."""
    print_section("3. Fichiers du projet")
    
    required_files = [
        ("core_analysis.py", "Module core"),
        ("graphiques.py", "Module graphiques"),
        ("rapport_generator.py", "Module rapports"),
        ("streamlit_app.py", "App Streamlit"),
        ("corrections.json", "Dictionnaire personnalise"),
        ("requirements.txt", "Dependances"),
    ]
    
    all_ok = True
    for filename, description in required_files:
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {filename:25} - {description} ({size} bytes)")
        else:
            print(f"❌ {filename:25} - MANQUANT")
            all_ok = False
    
    return all_ok

def test_api_key():
    """Verifie la cle API Groq."""
    print_section("4. Configuration API Groq")
    
    # Verifier environnement
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        masked = api_key[:10] + "*" * 20 + api_key[-10:]
        print(f"✅ Variable GROQ_API_KEY trouvee")
        print(f"   Valeur: {masked}")
        return True
    
    # Verifier secrets.toml
    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        with open(secrets_path) as f:
            content = f.read()
            if "GROQ_API_KEY" in content:
                print(f"✅ Cle API trouvee dans .streamlit/secrets.toml")
                return True
    
    print(f"⚠️  Cle API Groq non trouvee")
    print(f"   Definir: $env:GROQ_API_KEY='votre_cle'")
    print(f"   OU creer: .streamlit/secrets.toml")
    return False

def test_groq_connection():
    """Teste la connexion a l'API Groq."""
    print_section("5. Connexion API Groq")
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("⚠️  Cle API non disponible - test skipped")
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Test simple
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Repondre par 'OK'"}],
            max_tokens=10
        )
        
        if "OK" in response.choices[0].message.content:
            print("✅ API Groq fonctionnelle")
            return True
    except Exception as e:
        print(f"❌ Erreur API: {e}")
        return False
    
    return False

def test_csv_loading():
    """Teste le chargement d'un CSV de test."""
    print_section("6. Chargement CSV de test")
    
    # Chercher un CSV
    csv_files = list(Path(".").glob("*.csv"))
    if not csv_files:
        csv_files = list(Path(".github/skills/diplomatic-reporting").glob("*.csv"))
    
    if not csv_files:
        print("⚠️  Aucun fichier CSV trouve - test skipped")
        return False
    
    test_file = csv_files[0]
    print(f"  Utilisation: {test_file}")
    
    try:
        import pandas as pd
        df = pd.read_csv(test_file)
        print(f"✅ CSV charge : {len(df)} lignes x {len(df.columns)} colonnes")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Lance tous les tests."""
    print("\n")
    print("  🧹 Agent IA Universel - Test d'Installation")
    print("\n")
    
    results = {
        "Python": test_python(),
        "Imports": test_imports(),
        "Fichiers": test_files(),
        "API Key": test_api_key(),
        "Connexion Groq": test_groq_connection(),
        "CSV Loading": test_csv_loading(),
    }
    
    # Resume
    print_section("RESULTAT FINAL")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} {name}")
    
    print(f"\n  Score: {passed}/{total}\n")
    
    if passed == total:
        print("🎉 Tous les tests passes! L'installation est OK.")
        print("\nVous pouvez maintenant demarrer Streamlit:")
        print("  streamlit run streamlit_app.py\n")
        return 0
    elif passed >= total - 1:
        print("⚠️  Installation presque OK - certains tests ont echoue.")
        print("Reinstaller les dependances: pip install -r requirements.txt\n")
        return 1
    else:
        print("❌ Des problemes d'installation detectes.")
        print("Consultez GUIDE_STREAMLIT.md pour plus de details.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
