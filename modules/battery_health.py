# modules/battery_health.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path

class BatteryHealthWorker(QThread):
    """Worker thread pour générer rapport batterie"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        """Générer rapport batterie Windows"""
        try:
            self.log_signal.emit("🔋 Génération du rapport batterie...")
            
            # Générer rapport avec powercfg
            result = subprocess.run(
                ["powercfg", "/batteryreport", "/output", "battery-report.html"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.finished_signal.emit({'error': 'Échec génération rapport'})
                return
            
            self.log_signal.emit("✅ Rapport généré")
            self.log_signal.emit("📊 Analyse en cours...")
            
            # Parser le fichier HTML généré
            report_path = Path("battery-report.html")
            
            if not report_path.exists():
                self.finished_signal.emit({'error': 'Fichier rapport introuvable'})
                return
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extraire les informations
            data = self.parse_battery_report(html_content)
            
            # Supprimer le fichier temporaire
            try:
                os.remove(report_path)
            except:
                pass
            
            self.finished_signal.emit(data)
        
        except Exception as e:
            self.finished_signal.emit({'error': str(e)})
    
    def parse_battery_report(self, html):
        """Parser le rapport HTML"""
        data = {
            'design_capacity': 0,
            'full_charge_capacity': 0,
            'cycle_count': 0,
            'chemistry': 'Unknown',
            'manufacturer': 'Unknown',
            'serial': 'Unknown',
            'manufacture_date': 'Unknown'
        }
        
        try:
            # Design capacity
            match = re.search(r'DESIGN CAPACITY</td>.*?<td[^>]*>(\d+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['design_capacity'] = int(match.group(1))
            
            # Full charge capacity
            match = re.search(r'FULL CHARGE CAPACITY</td>.*?<td[^>]*>(\d+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['full_charge_capacity'] = int(match.group(1))
            
            # Cycle count
            match = re.search(r'CYCLE COUNT</td>.*?<td[^>]*>(\d+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['cycle_count'] = int(match.group(1))
            
            # Chemistry
            match = re.search(r'CHEMISTRY</td>.*?<td[^>]*>([^<]+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['chemistry'] = match.group(1).strip()
            
            # Manufacturer
            match = re.search(r'MANUFACTURER</td>.*?<td[^>]*>([^<]+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['manufacturer'] = match.group(1).strip()
            
            # Serial
            match = re.search(r'SERIAL NUMBER</td>.*?<td[^>]*>([^<]+)</td>', html, re.DOTALL | re.IGNORECASE)
            if match:
                data['serial'] = match.group(1).strip()
        
        except Exception as e:
            print(f"Erreur parsing: {e}")
        
        return data

class BatteryhealthWindow(QDialog):
    """Fenêtre santé batterie"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔋 Santé Batterie Laptop")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🔋 ANALYSEUR SANTÉ BATTERIE")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        help_btn = QPushButton("❓ Aide")
        help_btn.clicked.connect(self.show_help)
        help_btn.setFixedWidth(100)
        header_layout.addWidget(help_btn)
        
        layout.addLayout(header_layout)
        
        # Info
        info = QLabel(
            "Analyse détaillée de l'état de santé de votre batterie laptop\n"
            "Utilise la commande PowerCfg native de Windows"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Analyser Batterie")
        self.scan_btn.clicked.connect(self.analyze_battery)
        btn_layout.addWidget(self.scan_btn)
        
        tips_btn = QPushButton("💡 Conseils Autonomie")
        tips_btn.clicked.connect(self.show_battery_tips)
        btn_layout.addWidget(tips_btn)
        
        calibrate_btn = QPushButton("⚙️ Guide Calibration")
        calibrate_btn.clicked.connect(self.show_calibration_guide)
        btn_layout.addWidget(calibrate_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Résultats
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setFont(QFont("Consolas", 9))
        layout.addWidget(self.results)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Rapport")
        export_btn.clicked.connect(self.export_report)
        bottom_layout.addWidget(export_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QLabel { color: white; }
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
            QTextEdit {
                background: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                text-align: center;
                background: #2b2b2b;
            }
            QProgressBar::chunk {
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # Welcome message
        self.show_welcome()
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║           🔋 ANALYSEUR SANTÉ BATTERIE LAPTOP                ║
╚══════════════════════════════════════════════════════════════╝

🎯 QUE FAIT CET OUTIL ?

Génère un rapport détaillé sur l'état de votre batterie laptop:
- Capacité actuelle vs capacité neuve
- Usure de la batterie (%)
- Cycles de charge effectués
- Autonomie estimée
- Historique d'utilisation

📊 INFORMATIONS FOURNIES:

✅ Capacité Design (capacité d'origine à neuf)
✅ Capacité Actuelle (capacité réelle aujourd'hui)
✅ Pourcentage d'usure
✅ Nombre de cycles de charge
✅ Chimie batterie (Li-ion, Li-Po, etc.)
✅ Fabricant et numéro de série
✅ Recommandations selon état

💡 QUAND UTILISER ?

- Batterie se vide rapidement
- Laptop acheté d'occasion (vérifier usure)
- Avant période de garantie expirée
- Tous les 6 mois pour surveillance

⚡ UTILISATION:

Cliquez "Analyser Batterie" pour lancer le diagnostic !
L'analyse prend 5-10 secondes.

═══════════════════════════════════════════════════════════════

⚠️  IMPORTANT:

Cet outil utilise la commande native Windows "powercfg /batteryreport"
Nécessite un laptop avec batterie (ne fonctionne pas sur PC fixe)

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(text)
    
    def analyze_battery(self):
        """Lancer analyse batterie"""
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        
        self.results.setPlainText("🔄 Génération du rapport batterie...\n")
        
        # Lancer worker
        self.worker = BatteryHealthWorker()
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_analysis_finished)
        self.worker.start()
    
    def append_log(self, text):
        """Ajouter log"""
        self.results.append(text)
    
    def on_analysis_finished(self, data):
        """Traiter résultats"""
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if 'error' in data:
            if 'pas de batterie' in data['error'].lower() or 'unable to perform' in data['error'].lower():
                self.results.setPlainText("""
❌ AUCUNE BATTERIE DÉTECTÉE

Cet outil nécessite un ordinateur portable avec batterie.

🖥️  DÉTECTÉ: PC de bureau ou laptop sans batterie

Cet outil ne fonctionne que sur:
- Laptops / Ordinateurs portables
- Avec batterie installée et reconnue par Windows

Si vous êtes sur un laptop:
- Vérifiez que la batterie est bien installée
- Redémarrez le PC
- Vérifiez Gestionnaire de périphériques > Batteries
""")
            else:
                self.results.setPlainText(f"""
❌ ERREUR GÉNÉRATION RAPPORT

Une erreur s'est produite lors de la génération du rapport:
{data['error']}

💡 SOLUTIONS:

1. Relancer l'outil en mode Administrateur
   → Clic droit Wapinator > Exécuter en tant qu'administrateur

2. Vérifier que la batterie est reconnue
   → Gestionnaire de périphériques > Batteries
   → "Microsoft AC Adapter" et "Microsoft ACPI-Compliant Control Method Battery"
   doivent être présents

3. Mettre à jour drivers batterie
   → Boîte à Outils > Snappy Driver Installer

4. Si problème persiste
   → Contacter support fabricant laptop
""")
            return
        
        # Générer rapport
        report = self.generate_report(data)
        self.results.setPlainText(report)
    
    def generate_report(self, data):
        """Générer rapport détaillé"""
        design = data['design_capacity']
        current = data['full_charge_capacity']
        
        # Calculer usure
        if design > 0:
            health_percent = (current / design) * 100
            wear_percent = 100 - health_percent
        else:
            health_percent = 0
            wear_percent = 100
        
        cycles = data['cycle_count']
        
        report = "╔" + "═"*70 + "╗\n"
        report += "║" + " "*18 + "🔋 RAPPORT SANTÉ BATTERIE" + " "*26 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        # Informations générales
        report += "📋 INFORMATIONS GÉNÉRALES\n"
        report += "─" * 70 + "\n"
        report += f"• Fabricant: {data['manufacturer']}\n"
        report += f"• Numéro de série: {data['serial']}\n"
        report += f"• Chimie: {data['chemistry']}\n"
        report += f"• Date de fabrication: {data['manufacture_date']}\n\n"
        
        # Capacités
        report += "📊 CAPACITÉS\n"
        report += "─" * 70 + "\n"
        report += f"• Capacité Design (neuve): {design:,} mWh\n"
        report += f"• Capacité Actuelle: {current:,} mWh\n"
        report += f"• Différence: {design - current:,} mWh\n\n"
        
        # État de santé
        report += "💚 ÉTAT DE SANTÉ\n"
        report += "─" * 70 + "\n"
        
        # Barre visuelle
        bar_length = 50
        filled = int((health_percent / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        report += f"Santé batterie: {health_percent:.1f}%\n"
        report += f"[{bar}]\n\n"
        
        report += f"• Usure totale: {wear_percent:.1f}%\n"
        report += f"• Cycles de charge: {cycles}\n\n"
        
        # Évaluation
        report += "🎯 ÉVALUATION\n"
        report += "─" * 70 + "\n"
        
        if health_percent >= 90:
            status = "✅ EXCELLENTE"
            color_icon = "🟢"
            advice = "Votre batterie est en excellent état !\nPas d'action nécessaire."
        elif health_percent >= 80:
            status = "✅ BONNE"
            color_icon = "🟢"
            advice = "Votre batterie est en bon état.\nUsure normale pour son âge."
        elif health_percent >= 70:
            status = "⚠️ CORRECTE"
            color_icon = "🟡"
            advice = "Usure visible mais acceptable.\nSurveillez l'évolution tous les 3 mois."
        elif health_percent >= 60:
            status = "⚠️ USÉE"
            color_icon = "🟡"
            advice = "Batterie significativement usée.\nPrévoir remplacement sous 6-12 mois."
        elif health_percent >= 50:
            status = "🔴 TRÈS USÉE"
            color_icon = "🔴"
            advice = "Batterie en fin de vie.\nRemplacement recommandé rapidement."
        else:
            status = "🚨 CRITIQUE"
            color_icon = "🔴"
            advice = "Batterie HS ou quasi morte.\nREMPLACEMENT URGENT nécessaire !"
        
        report += f"{color_icon} État: {status}\n"
        report += f"   {advice}\n\n"
        
        # Cycles
        report += "🔄 ANALYSE CYCLES\n"
        report += "─" * 70 + "\n"
        
        if cycles == 0:
            report += "⚠️ Nombre de cycles non disponible (driver/firmware)\n"
        elif cycles < 100:
            report += f"🟢 Cycles: {cycles} - Batterie très peu utilisée\n"
        elif cycles < 300:
            report += f"🟢 Cycles: {cycles} - Utilisation normale\n"
        elif cycles < 500:
            report += f"🟡 Cycles: {cycles} - Utilisation moyenne\n"
        elif cycles < 800:
            report += f"🟡 Cycles: {cycles} - Utilisation intensive\n"
        else:
            report += f"🔴 Cycles: {cycles} - Très nombreux cycles (usure avancée)\n"
        
        report += "\nℹ️  Durée de vie typique: 300-500 cycles pour la plupart des batteries\n"
        report += "   1 cycle = charge complète 0% → 100%\n\n"
        
        # Autonomie estimée
        report += "⏱️  AUTONOMIE ESTIMÉE\n"
        report += "─" * 70 + "\n"
        
        # Calcul approximatif (basé sur capacité)
        if design > 0:
            # Moyenne: 50 Wh = environ 5h d'autonomie en usage léger
            estimated_hours = (current / 1000) / 10  # Approximation simpliste
            report += f"• Autonomie estimée (usage léger): ~{estimated_hours:.1f}h\n"
            report += f"• Autonomie estimée (usage normal): ~{estimated_hours * 0.7:.1f}h\n"
            report += f"• Autonomie estimée (usage intensif): ~{estimated_hours * 0.4:.1f}h\n\n"
            report += "⚠️ Ces valeurs sont approximatives et dépendent de:\n"
            report += "   • Luminosité écran\n"
            report += "   • Applications en cours\n"
            report += "   • Processeur utilisé\n"
            report += "   • Paramètres d'alimentation\n\n"
        
        # Recommandations
        report += "╔" + "═"*70 + "╗\n"
        report += "║" + " "*22 + "💡 RECOMMANDATIONS" + " "*29 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        if health_percent >= 80:
            report += "✅ VOTRE BATTERIE EST EN BON ÉTAT\n\n"
            report += "Conseils pour prolonger sa durée de vie:\n"
            report += "• Éviter décharges complètes (< 20%)\n"
            report += "• Idéal: maintenir charge entre 20-80%\n"
            report += "• Éviter températures extrêmes (< 0°C ou > 35°C)\n"
            report += "• Débrancher chargeur quand batterie pleine (si pas en usage)\n"
            report += "• Calibrer la batterie tous les 3 mois (voir Guide Calibration)\n"
        
        elif health_percent >= 60:
            report += "⚠️ VOTRE BATTERIE MONTRE DES SIGNES D'USURE\n\n"
            report += "Actions recommandées:\n"
            report += "• Commencer à prévoir un remplacement (6-12 mois)\n"
            report += "• Utiliser modes économie d'énergie Windows\n"
            report += "• Réduire luminosité écran\n"
            report += "• Fermer applications inutiles\n"
            report += "• Vérifier prix batterie de remplacement:\n"
            report += "  → Site fabricant laptop\n"
            report += "  → Amazon/LDLC/materiel.net (compatible)\n"
        
        else:
            report += "🚨 REMPLACEMENT BATTERIE URGENT\n\n"
            report += "Votre batterie est en fin de vie et devrait être remplacée.\n\n"
            report += "Options:\n"
            report += "1. BATTERIE OFFICIELLE (recommandé)\n"
            report += "   → Site fabricant laptop\n"
            report += "   → Garantie + qualité assurée\n"
            report += "   → Plus cher (80-150€)\n\n"
            report += "2. BATTERIE COMPATIBLE\n"
            report += "   → Amazon, eBay (attention arnaqueurs)\n"
            report += "   → Vérifier compatibilité exacte (modèle laptop)\n"
            report += "   → Moins cher (40-80€)\n"
            report += "   → Risque: qualité variable\n\n"
            report += "3. SERVICE RÉPARATION\n"
            report += "   → Centre agréé fabricant\n"
            report += "   → Installation + garantie\n"
            report += "   → Prix: pièce + main d'œuvre (100-200€)\n\n"
            report += "⚠️ EN ATTENDANT:\n"
            report += "• Utiliser laptop branché sur secteur en priorité\n"
            report += "• Avoir chargeur toujours avec vous\n"
            report += "• Sauvegarder travail régulièrement (coupures possibles)\n"
        
        report += "\n" + "═" * 70 + "\n"
        report += "📚 Pour plus de conseils: Bouton 'Conseils Autonomie'\n"
        report += "⚙️  Pour recalibrer: Bouton 'Guide Calibration'\n"
        report += "═" * 70 + "\n"
        
        return report
    
    def show_battery_tips(self):
        """Afficher conseils autonomie"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║              💡 CONSEILS POUR PROLONGER AUTONOMIE           ║
╚══════════════════════════════════════════════════════════════╝

🎯 OBJECTIF: Maximiser durée entre deux charges

═══════════════════════════════════════════════════════════════

⚙️  PARAMÈTRES WINDOWS

1️⃣  MODE ÉCONOMIE D'ÉNERGIE
   • Cliquer icône batterie (barre tâches)
   • Curseur sur "Meilleure autonomie"
   • Ou: Paramètres > Système > Batterie > Mode économie

2️⃣  LUMINOSITÉ ÉCRAN (impact énorme!)
   • Réduire à 40-50% (touche Fn + F5/F6 selon laptop)
   • Économie: +30-50% d'autonomie !
   • Paramètres > Système > Affichage

3️⃣  DÉSACTIVER CLAVIER RÉTROÉCLAIRÉ
   • Souvent Fn + Espace ou Fn + F4
   • Consomme 2-5% batterie

4️⃣  WIFI/BLUETOOTH OFF SI NON UTILISÉ
   • Mode Avion si pas besoin réseau
   • Économie: +10-15%

═══════════════════════════════════════════════════════════════

📱 APPLICATIONS

1️⃣  FERMER APPS INUTILES
   • Gestionnaire tâches (Ctrl+Shift+Échap)
   • Fermer Chrome/Firefox si non utilisé (gros consommateurs)
   • Discord, Spotify en arrière-plan = -10% autonomie

2️⃣  LIMITER ONGLETS NAVIGATEUR
   • Max 5-10 onglets ouverts
   • Extensions consomment aussi (AdBlock, etc.)

3️⃣  APPS EN ARRIÈRE-PLAN
   • Paramètres > Confidentialité > Apps en arrière-plan
   • Désactiver toutes sauf essentielles

═══════════════════════════════════════════════════════════════

🎮 GAMING / USAGE INTENSIF

⚠️  Gaming sur batterie = À ÉVITER !
   • Décharge très rapide (1-2h max)
   • Usure accélérée de la batterie
   • Performances bridées par processeur

💡 SI GAMING NÉCESSAIRE:
   • Baisser graphismes en jeu
   • Limiter FPS (30-60 au lieu de 144)
   • Passer en 1080p au lieu de 1440p/4K

═══════════════════════════════════════════════════════════════

❄️  TEMPÉRATURES

- Éviter utilisation sous soleil direct
- Ne pas bloquer ventilations
- Éviter utilisation sur lit/couverture (surchauffe)
- Utiliser sur surface dure et plane
- Température idéale: 15-25°C

═══════════════════════════════════════════════════════════════

🔌 HABITUDES CHARGE

MYTHE: "Il faut décharger complètement puis charger à 100%"
→ FAUX pour batteries Li-ion modernes !

✅ BONNES PRATIQUES:
- Charger quand batterie atteint 20-30%
- Débrancher vers 80-90% (pas obligé attendre 100%)
- Éviter laisser branché H24 si possible
- OK de charger plusieurs fois par jour (mieux que décharge totale)

❌ MAUVAISES PRATIQUES:
- Décharges complètes régulières (0-5%)
- Laisser batterie morte plusieurs jours
- Charger uniquement à 100% (pas nécessaire)
- Laisser laptop branché 24/7 pendant des mois

═══════════════════════════════════════════════════════════════

📊 MONITORING

Surveiller consommation:
- Paramètres > Système > Batterie > "Utilisation batterie"
- Identifier apps qui consomment le plus
- Ajuster en conséquence

═══════════════════════════════════════════════════════════════

⚡ GAINS ATTENDUS

Si application TOUS ces conseils:
- +50-100% d'autonomie vs utilisation "normale"
- Exemple: 3h → 5-6h d'autonomie

Si application CONSEILS ESSENTIELS uniquement:
- Luminosité 40%
- Mode économie
- Fermer apps inutiles
→ +30-50% d'autonomie (3h → 4-4.5h)

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(tips)
    
    def show_calibration_guide(self):
        """Guide calibration batterie"""
        guide = """╔══════════════════════════════════════════════════════════════╗
║            ⚙️  GUIDE CALIBRATION BATTERIE                   ║
╚══════════════════════════════════════════════════════════════╝

🎯 POURQUOI CALIBRER ?

Avec le temps, l'indicateur Windows de % batterie devient imprécis.
Windows pense que batterie est à 50% alors qu'elle est à 40% réel.

La calibration "recalibre" l'indicateur pour qu'il soit précis à nouveau.

═══════════════════════════════════════════════════════════════

⏱️  FRÉQUENCE: Tous les 3 mois OU si indicateur semble faux

═══════════════════════════════════════════════════════════════

📋 ÉTAPES DE CALIBRATION (4-6 heures)

⚠️  IMPORTANT: Ne pas interrompre le processus !
⚠️  Faire pendant une nuit ou weekend

─────────────────────────────────────────────────────────────

1️⃣  PRÉPARATION (5 minutes)

   • Sauvegarder tout travail en cours
   • Fermer toutes applications
   • Désactiver mise en veille:
     → Paramètres > Système > Alimentation
     → "Mettre en veille après": JAMAIS (secteur ET batterie)
     → "Désactiver écran après": JAMAIS

   • Désactiver économiseur d'écran
   • Désactiver hibernation:
     → CMD en admin: powercfg /h off

─────────────────────────────────────────────────────────────

2️⃣  CHARGE COMPLÈTE (2-3 heures)

   • Brancher laptop sur secteur
   • Laisser charger jusqu'à 100%
   • Attendre 1-2h SUPPLÉMENTAIRES après 100%
     (pour charge "top-off")
   
   💡 Vous pouvez utiliser le PC normalement pendant charge

─────────────────────────────────────────────────────────────

3️⃣  DÉCHARGE COMPLÈTE (3-6 heures)

   ⚠️  ÉTAPE CRITIQUE - Ne pas interrompre !

   • Débrancher le chargeur
   • Laisser laptop ALLUMÉ
   • Ouvrir un fichier texte ou vidéo YouTube (empêche veille)
   • Attendre que batterie atteigne 0%
   • Laptop s'éteindra automatiquement

   💡 Pour accélérer (optionnel):
     • Luminosité écran 100%
     • Lancer vidéo YouTube en boucle
     • Ouvrir plusieurs onglets navigateur

   ⏱️  Durée: Dépend de votre autonomie actuelle
       • Batterie saine: 4-8h
       • Batterie usée: 1-3h

─────────────────────────────────────────────────────────────

4️⃣  REPOS (2-5 heures)

   • Laisser laptop ÉTEINT pendant 2-5 heures
   • Batterie complètement morte
   • Ne PAS rebrancher pendant ce temps

   💡 C'est le moment idéal pour:
     • Aller dormir (si fait la nuit)
     • Faire autre chose (si fait le jour)

─────────────────────────────────────────────────────────────

5️⃣  RECHARGE COMPLÈTE (2-3 heures)

   • Rebrancher chargeur (laptop toujours éteint)
   • Laisser charger jusqu'à 100%
   • NE PAS allumer pendant la charge
   • Attendre 1h après 100%

─────────────────────────────────────────────────────────────

6️⃣  FINALISATION (5 minutes)

   • Allumer le laptop
   • Vérifier que % batterie = 100%
   • Réactiver paramètres mise en veille:
     → Paramètres > Système > Alimentation
     → Remettre vos paramètres habituels
   
   • Réactiver hibernation:
     → CMD en admin: powercfg /h on

   ✅ CALIBRATION TERMINÉE !

═══════════════════════════════════════════════════════════════

📊 RÉSULTATS ATTENDUS

AVANT calibration:
- Indicateur imprécis
- Coupures inattendues à 10-20%
- Charge "bloquée" à 95-99%

APRÈS calibration:
- Indicateur précis ✅
- Décharge linéaire et prévisible
- Charge complète jusqu'à 100%

═══════════════════════════════════════════════════════════════

⚠️  PRÉCAUTIONS

❌ Ne PAS calibrer trop souvent
   → Max 1x tous les 2-3 mois
   → Décharge complète = usure batterie

❌ Ne PAS calibrer si batterie < 50% santé
   → Risque de ne plus pouvoir rallumer laptop
   → Faire remplacer batterie d'abord

✅ OK de ne jamais calibrer
   → Pas obligatoire pour fonctionnement
   → Juste pour précision indicateur

═══════════════════════════════════════════════════════════════

💡 ALTERNATIVE SIMPLE (si pas le temps)

Méthode rapide (moins efficace mais OK):
1. Charger à 100%
2. Débrancher et utiliser jusqu'à 20%
3. Rebrancher immédiatement
4. Laisser charger jusqu'à 100%
5. Répéter 2-3 fois

⏱️  Durée: 1 journée normale d'utilisation
📊 Efficacité: 60% vs calibration complète

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(guide)
    
    def show_help(self):
        """Aide générale"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║                     ❓ AIDE - SANTÉ BATTERIE                ║
╚══════════════════════════════════════════════════════════════╝

🤔 QU'EST-CE QUE LA SANTÉ BATTERIE ?

La santé batterie représente la capacité actuelle de votre batterie
comparée à sa capacité lorsqu'elle était neuve.

Exemple:
- Batterie neuve: 50,000 mWh (100%)
- Après 2 ans: 40,000 mWh (80% santé = 20% usure)

═══════════════════════════════════════════════════════════════

🔋 COMPRENDRE LES VALEURS

CAPACITÉ DESIGN:
- Capacité annoncée par fabricant (batterie neuve)
- Ne change jamais
- Exemple: 50,000 mWh

CAPACITÉ ACTUELLE (Full Charge Capacity):
- Capacité réelle aujourd'hui
- Diminue avec le temps/usage
- Exemple après 2 ans: 40,000 mWh

USURE:
- Perte de capacité en %
- Formule: (1 - Actuelle/Design) × 100
- Exemple: (1 - 40000/50000) × 100 = 20%

CYCLES:
- 1 cycle = charge complète 0% → 100%
- Ou équivalent: 50% → 100% = 0.5 cycle
- Batteries modernes: 300-500 cycles de vie

═══════════════════════════════════════════════════════════════

📊 DURÉE DE VIE BATTERIE

FACTEURS D'USURE:

1. TEMPS (40%)
   • Batterie vieillit même si laptop inutilisé
   • Usure: ~10-15% par an

2. CYCLES (30%)
   • Chaque charge/décharge use la batterie
   • 300-500 cycles = durée vie normale

3. TEMPÉRATURE (20%)
   • Chaleur = ennemi #1 des batteries
   • > 35°C = usure accélérée
   • < 0°C = performance réduite

4. DÉCHARGES PROFONDES (10%)
   • Décharges < 5% usent plus
   • Maintenir 20-80% = idéal

═══════════════════════════════════════════════════════════════

⏱️  DURÉE VIE MOYENNE

Usage NORMAL:
- 2-4 ans avant usure significative (< 80%)
- 4-6 ans avant remplacement obligatoire (< 60%)

Usage INTENSIF (gaming, vidéo):
- 1-2 ans avant usure significative
- 2-3 ans avant remplacement

Usage LÉGER (bureautique):
- 4-6 ans avant usure significative
- 6-8 ans avant remplacement

═══════════════════════════════════════════════════════════════

🛠️  DÉPANNAGE

PROBLÈME: "L'analyse ne fonctionne pas"
→ Relancer Wapinator en administrateur
→ Vérifier Gestionnaire périph > Batteries
→ MAJ drivers batterie (Snappy Driver Installer)

PROBLÈME: "Cycles = 0"
→ Normal sur certains laptops (driver ne fournit pas info)
→ Pas grave, autres indicateurs sont fiables

PROBLÈME: "Capacité = 0"
→ Batterie non reconnue ou HS
→ Vérifier branchement batterie (si amovible)
→ Contacter support fabricant

═══════════════════════════════════════════════════════════════

💰 COÛT REMPLACEMENT

BATTERIE OFFICIELLE: 80-150€
BATTERIE COMPATIBLE: 40-80€
MAIN D'ŒUVRE (si non remplaçable): 50-100€

Total: 100-250€ selon laptop et choix

💡 Avant d'acheter:
- Vérifier si batterie amovible (facile) ou intégrée (difficile)
- Chercher tuto YouTube: "replace battery [votre modèle laptop]"
- Comparer prix officiel vs compatible

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter rapport"""
        content = self.results.toPlainText()
        
        if not content or "BIENVENUE" in content or "CONSEILS" in content:
            QMessageBox.warning(self, "⚠️", "Aucun rapport d'analyse à exporter.\nLancez d'abord une analyse.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Batterie_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 70 + "\n")
                f.write("  RAPPORT SANTÉ BATTERIE - WAPINATOR\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 70 + "\n\n")
                f.write(content)
            
            reply = QMessageBox.question(
                self,
                "✅ Rapport exporté",
                f"Rapport sauvegardé:\n{filename.name}\n\nOuvrir le fichier ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(filename)
        
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Impossible d'exporter:\n{str(e)}")