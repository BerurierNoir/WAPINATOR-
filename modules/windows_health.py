# modules/windows_health.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Flags subprocess
import sys
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = subprocess.SW_HIDE
else:
    CREATE_NO_WINDOW = 0
    STARTUPINFO = None

class HealthCheckWorker(QThread):
    """Worker pour vérifications santé Windows"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        """Exécuter vérifications santé"""
        results = {
            'dism_check': {},
            'sfc_status': {},
            'disk_errors': {},
            'system_files': {},
            'windows_update': {},
            'services': {},
            'overall_score': 0
        }
        
        try:
            self.log_signal.emit("╔" + "═"*70 + "╗")
            self.log_signal.emit("║" + " "*18 + "🏥 VÉRIFICATION SANTÉ WINDOWS" + " "*22 + "║")
            self.log_signal.emit("╚" + "═"*70 + "╝\n")
            
            # 1. DISM CheckHealth (rapide)
            self.log_signal.emit("📊 ÉTAPE 1/6 : DISM CheckHealth (Vérification rapide)")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(16)
            
            dism_result = self.run_dism_check()
            results['dism_check'] = dism_result
            
            if dism_result['healthy']:
                self.log_signal.emit("✅ Image Windows: Saine")
            else:
                self.log_signal.emit("⚠️ Image Windows: Corruptions détectées")
            
            self.log_signal.emit("")
            
            # 2. SFC Status
            self.log_signal.emit("🔍 ÉTAPE 2/6 : Vérification fichiers système (SFC)")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(32)
            
            sfc_result = self.check_sfc_status()
            results['sfc_status'] = sfc_result
            
            if sfc_result['clean']:
                self.log_signal.emit("✅ Fichiers système: Intacts")
            else:
                self.log_signal.emit("⚠️ Fichiers système: Problèmes détectés")
            
            self.log_signal.emit("")
            
            # 3. Disk Errors
            self.log_signal.emit("💾 ÉTAPE 3/6 : Vérification erreurs disque")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(48)
            
            disk_result = self.check_disk_errors()
            results['disk_errors'] = disk_result
            
            if disk_result['errors_found']:
                self.log_signal.emit("⚠️ Erreurs disque détectées")
            else:
                self.log_signal.emit("✅ Aucune erreur disque")
            
            self.log_signal.emit("")
            
            # 4. System Files Integrity
            self.log_signal.emit("📁 ÉTAPE 4/6 : Intégrité dossiers système")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(64)
            
            system_result = self.check_system_folders()
            results['system_files'] = system_result
            
            self.log_signal.emit(f"✅ Dossiers critiques: {system_result['folders_ok']}/{system_result['folders_checked']}")
            self.log_signal.emit("")
            
            # 5. Windows Update Status
            self.log_signal.emit("🔄 ÉTAPE 5/6 : État Windows Update")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(80)
            
            update_result = self.check_windows_update()
            results['windows_update'] = update_result
            
            if update_result['working']:
                self.log_signal.emit("✅ Windows Update: Fonctionnel")
            else:
                self.log_signal.emit("⚠️ Windows Update: Problèmes possibles")
            
            self.log_signal.emit("")
            
            # 6. Critical Services
            self.log_signal.emit("⚙️ ÉTAPE 6/6 : Services critiques")
            self.log_signal.emit("─" * 70)
            self.progress_signal.emit(100)
            
            services_result = self.check_critical_services()
            results['services'] = services_result
            
            running = services_result['running']
            total = services_result['total']
            self.log_signal.emit(f"✅ Services actifs: {running}/{total}")
            self.log_signal.emit("")
            
            # Calcul score global
            score = self.calculate_health_score(results)
            results['overall_score'] = score
            
            self.finished_signal.emit(results)
        
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit({'error': str(e)})
    
    def run_dism_check(self):
        """DISM CheckHealth rapide"""
        try:
            result = subprocess.run(
                ["DISM", "/online", "/cleanup-image", "/CheckHealth"],
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="cp850",
                errors="replace"
            )
            
            output = result.stdout
            
            # Analyser output
            if "No component store corruption detected" in output or "aucune corruption" in output.lower():
                return {'healthy': True, 'needs_repair': False}
            elif "corrupt" in output.lower() or "corruption" in output.lower():
                return {'healthy': False, 'needs_repair': True}
            else:
                return {'healthy': True, 'needs_repair': False}
        
        except:
            return {'healthy': False, 'needs_repair': True, 'error': True}
    
    def check_sfc_status(self):
        """Vérifier dernier scan SFC"""
        try:
            # Lire CBS.log (fichier log SFC)
            cbs_log = Path(r"C:\Windows\Logs\CBS\CBS.log")
            
            if not cbs_log.exists():
                return {'clean': True, 'last_scan': None, 'issues_found': 0}
            
            # Lire dernières lignes
            with open(cbs_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Chercher informations récentes
            issues = 0
            for line in reversed(lines[-1000:]):  # Dernières 1000 lignes
                if "verification complete" in line.lower():
                    break
                if "corrupt" in line.lower() or "integrity violation" in line.lower():
                    issues += 1
            
            return {
                'clean': issues == 0,
                'issues_found': issues,
                'last_scan': 'Recent'
            }
        
        except:
            return {'clean': True, 'last_scan': None, 'issues_found': 0}
    
    def check_disk_errors(self):
        """Vérifier erreurs disque via événements"""
        try:
            # Query Event Log pour erreurs disque
            result = subprocess.run(
                ["wevtutil", "qe", "System", "/c:50", "/rd:true", "/f:text", "/q:*[System[Provider[@Name='disk']]]"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="cp850",
                errors="replace"
            )
            
            output = result.stdout
            
            # Compter erreurs
            error_keywords = ["error", "bad block", "failure", "warning"]
            error_count = sum(output.lower().count(keyword) for keyword in error_keywords)
            
            return {
                'errors_found': error_count > 10,  # Seuil
                'error_count': error_count
            }
        
        except:
            return {'errors_found': False, 'error_count': 0}
    
    def check_system_folders(self):
        """Vérifier existence dossiers système critiques"""
        critical_folders = [
            r"C:\Windows\System32",
            r"C:\Windows\SysWOW64",
            r"C:\Windows\System32\drivers",
            r"C:\Windows\System32\config",
            r"C:\Windows\WinSxS",
            r"C:\Program Files",
            r"C:\ProgramData"
        ]
        
        folders_ok = 0
        for folder in critical_folders:
            if Path(folder).exists():
                folders_ok += 1
        
        return {
            'folders_ok': folders_ok,
            'folders_checked': len(critical_folders),
            'all_present': folders_ok == len(critical_folders)
        }
    
    def check_windows_update(self):
        """Vérifier état Windows Update"""
        try:
            # Vérifier service Windows Update
            result = subprocess.run(
                ["sc", "query", "wuauserv"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="cp850",
                errors="replace"
            )
            
            output = result.stdout
            
            running = "RUNNING" in output
            
            return {
                'working': running,
                'service_running': running
            }
        
        except:
            return {'working': False, 'service_running': False}
    
    def check_critical_services(self):
        """Vérifier services Windows critiques"""
        critical_services = [
            "wuauserv",      # Windows Update
            "BITS",          # Background Intelligent Transfer
            "CryptSvc",      # Cryptographic Services
            "TrustedInstaller",  # Windows Modules Installer
            "eventlog",      # Event Log
            "Winmgmt",       # Windows Management Instrumentation
            "RpcSs",         # Remote Procedure Call
        ]
        
        running = 0
        
        for service in critical_services:
            try:
                result = subprocess.run(
                    ["sc", "query", service],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO,
                    encoding="cp850",
                    errors="replace"
                )
                
                if "RUNNING" in result.stdout:
                    running += 1
            
            except:
                pass
        
        return {
            'running': running,
            'total': len(critical_services),
            'all_running': running == len(critical_services)
        }
    
    def calculate_health_score(self, results):
        """Calculer score santé global (0-100)"""
        score = 100
        
        # DISM
        if not results['dism_check'].get('healthy', True):
            score -= 20
        
        # SFC
        if not results['sfc_status'].get('clean', True):
            score -= 15
        
        # Disk
        if results['disk_errors'].get('errors_found', False):
            score -= 15
        
        # System folders
        if not results['system_files'].get('all_present', True):
            score -= 20
        
        # Windows Update
        if not results['windows_update'].get('working', True):
            score -= 10
        
        # Services
        services = results['services']
        if not services.get('all_running', True):
            missing = services['total'] - services['running']
            score -= min(20, missing * 3)
        
        return max(0, score)

class WindowshealthWindow(QDialog):
    """Fenêtre vérification santé Windows"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🏥 Vérification Santé Windows")
        self.setMinimumSize(1000, 750)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🏥 VÉRIFICATION SANTÉ WINDOWS")
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
            "Diagnostic complet de l'état de santé de votre installation Windows • 6 vérifications"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Score santé (widget custom)
        self.health_widget = QWidget()
        self.health_widget.setFixedHeight(100)
        health_layout = QVBoxLayout()
        
        self.score_label = QLabel("❓ Non testé")
        self.score_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        health_layout.addWidget(self.score_label)
        
        self.score_desc = QLabel("Lancez un diagnostic pour évaluer la santé de Windows")
        self.score_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_desc.setStyleSheet("color: #888;")
        health_layout.addWidget(self.score_desc)
        
        self.health_widget.setLayout(health_layout)
        self.health_widget.setStyleSheet("background: #2b2b2b; border-radius: 10px;")
        layout.addWidget(self.health_widget)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.check_btn = QPushButton("🔍 Lancer Diagnostic")
        self.check_btn.clicked.connect(self.start_check)
        self.check_btn.setStyleSheet("background: #4CAF50; font-size: 12px; padding: 12px;")
        btn_layout.addWidget(self.check_btn)
        
        self.repair_btn = QPushButton("🔧 Réparer (DISM + SFC)")
        self.repair_btn.clicked.connect(self.start_repair)
        self.repair_btn.setEnabled(False)
        self.repair_btn.setStyleSheet("background: #FF9800;")
        btn_layout.addWidget(self.repair_btn)
        
        tips_btn = QPushButton("💡 Conseils Maintenance")
        tips_btn.clicked.connect(self.show_tips)
        btn_layout.addWidget(tips_btn)
        
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
                background: #00BCD4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0097A7; }
            QPushButton:disabled { background: #555; color: #888; }
            QTextEdit {
                background: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        self.show_welcome()
        self.worker = None
        self.last_results = None
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║        🏥 VÉRIFICATION SANTÉ WINDOWS - WAPINATOR             ║
╚══════════════════════════════════════════════════════════════╝

🎯 OBJECTIF

Diagnostic complet de l'état de santé de votre installation Windows.
Détecte corruptions, problèmes système, services défaillants.

═══════════════════════════════════════════════════════════════

📊 VÉRIFICATIONS EFFECTUÉES

1️⃣  DISM CheckHealth
   • Vérifie intégrité image Windows
   • Détecte corruptions magasin composants
   • Rapide (30-60 secondes)

2️⃣  SFC Status (System File Checker)
   • Analyse logs derniers scans SFC
   • Détecte fichiers système corrompus
   • Vérifie intégrité DLL système

3️⃣  Erreurs Disque
   • Consulte Event Log système
   • Détecte erreurs lecture/écriture
   • Identifie secteurs défectueux

4️⃣  Dossiers Système
   • Vérifie présence dossiers critiques
   • System32, drivers, config, WinSxS
   • Détecte suppressions accidentelles

5️⃣  Windows Update
   • Vérifie fonctionnement service WU
   • Détecte blocages mises à jour
   • Identifie services liés défaillants

6️⃣  Services Critiques
   • Vérifie 7 services Windows essentiels
   • RPC, WMI, Event Log, etc.
   • Détecte services arrêtés

═══════════════════════════════════════════════════════════════

📈 SCORE SANTÉ

Le score global (0-100) reflète l'état de Windows:

- 90-100 = 🟢 EXCELLENT - Aucun problème
- 70-89  = 🟡 BON - Quelques problèmes mineurs
- 50-69  = 🟠 MOYEN - Problèmes à corriger
- 0-49   = 🔴 CRITIQUE - Réparation urgente

═══════════════════════════════════════════════════════════════

💡 QUAND UTILISER ?

✅ PC lent inexplicablement
✅ Erreurs Windows fréquentes
✅ Après infection malware (nettoyée)
✅ Avant réinstallation (tester d'abord)
✅ Maintenance préventive (1x tous les 3 mois)

═══════════════════════════════════════════════════════════════

⏱️ DURÉE: 2-3 minutes (diagnostic)
        15-30 min (si réparation nécessaire)

🚀 DÉMARRAGE

Cliquez "Lancer Diagnostic" pour commencer !

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(text)
    
    def start_check(self):
        """Lancer vérification"""
        self.check_btn.setEnabled(False)
        self.repair_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.results.clear()
        self.score_label.setText("⏳ Diagnostic en cours...")
        self.score_desc.setText("Veuillez patienter 2-3 minutes")
        
        # Lancer worker
        self.worker = HealthCheckWorker()
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_check_finished)
        self.worker.start()
    
    def append_log(self, text):
        """Ajouter au log"""
        self.results.append(text)
    
    def on_check_finished(self, results):
        """Vérification terminée"""
        self.check_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.last_results = results
        
        if 'error' in results:
            self.score_label.setText("❌ ERREUR")
            self.score_desc.setText(f"Erreur: {results['error']}")
            return
        
        # Afficher score
        score = results['overall_score']
        
        if score >= 90:
            color = "#4CAF50"
            status = "🟢 EXCELLENT"
            desc = "Votre Windows est en parfaite santé !"
            self.repair_btn.setEnabled(False)
        elif score >= 70:
            color = "#8BC34A"
            status = "🟡 BON"
            desc = "Quelques problèmes mineurs détectés"
            self.repair_btn.setEnabled(True)
        elif score >= 50:
            color = "#FF9800"
            status = "🟠 MOYEN"
            desc = "Problèmes à corriger - Réparation recommandée"
            self.repair_btn.setEnabled(True)
        else:
            color = "#F44336"
            status = "🔴 CRITIQUE"
            desc = "Réparation urgente nécessaire !"
            self.repair_btn.setEnabled(True)
        
        self.score_label.setText(f"{status} - {score}/100")
        self.score_label.setStyleSheet(f"color: {color};")
        self.score_desc.setText(desc)
        
        # Générer rapport détaillé
        self.generate_detailed_report(results)
    
    def generate_detailed_report(self, results):
        """Générer rapport détaillé"""
        report = "\n╔" + "═"*70 + "╗\n"
        report += "║" + " "*20 + "📊 RAPPORT DÉTAILLÉ" + " "*30 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        # DISM
        report += "1️⃣  IMAGE WINDOWS (DISM)\n"
        report += "─" * 70 + "\n"
        if results['dism_check'].get('healthy', True):
            report += "✅ Statut: Saine - Aucune corruption détectée\n"
        else:
            report += "❌ Statut: Corrompue - Réparation nécessaire\n"
            report += "   Action: Utiliser bouton 'Réparer (DISM + SFC)'\n"
        report += "\n"
        
        # SFC
        report += "2️⃣  FICHIERS SYSTÈME (SFC)\n"
        report += "─" * 70 + "\n"
        sfc = results['sfc_status']
        if sfc.get('clean', True):
            report += "✅ Statut: Intacts - Aucun problème\n"
        else:
            issues = sfc.get('issues_found', 0)
            report += f"⚠️ Statut: {issues} problème(s) détecté(s)\n"
            report += "   Action: Lancer SFC /scannow via bouton 'Réparer'\n"
        report += "\n"
        
        # Disque
        report += "3️⃣  ERREURS DISQUE\n"
        report += "─" * 70 + "\n"
        disk = results['disk_errors']
        if not disk.get('errors_found', False):
            report += "✅ Statut: Aucune erreur significative\n"
        else:
            count = disk.get('error_count', 0)
            report += f"⚠️ Statut: {count} erreurs dans Event Log\n"
            report += "   Action: Lancer chkdsk (Boîte à Outils Wapinator)\n"
        report += "\n"
        
        # Dossiers système
        report += "4️⃣  DOSSIERS SYSTÈME\n"
        report += "─" * 70 + "\n"
        sys_files = results['system_files']
        ok = sys_files['folders_ok']
        total = sys_files['folders_checked']
        report += f"✅ Statut: {ok}/{total} dossiers critiques présents\n"
        if ok < total:
            report += "   ⚠️ Certains dossiers système manquants !\n"
            report += "   Action: Réparation Windows ou réinstallation\n"
        report += "\n"
        
        # Windows Update
        report += "5️⃣  WINDOWS UPDATE\n"
        report += "─" * 70 + "\n"
        wu = results['windows_update']
        if wu.get('working', True):
            report += "✅ Statut: Fonctionnel\n"
        else:
            report += "❌ Statut: Service arrêté ou défaillant\n"
            report += "   Action: Redémarrer service (net start wuauserv)\n"
        report += "\n"
        
        # Services
        report += "6️⃣  SERVICES CRITIQUES\n"
        report += "─" * 70 + "\n"
        services = results['services']
        running = services['running']
        total = services['total']
        report += f"• Services actifs: {running}/{total}\n"
        
        if running == total:
            report += "✅ Statut: Tous les services critiques fonctionnent\n"
        else:
            report += f"⚠️ Statut: {total - running} service(s) arrêté(s)\n"
            report += "   Action: Redémarrer services via services.msc\n"
        report += "\n"
        
        # Recommandations
        report += "╔" + "═"*70 + "╗\n"
        report += "║" + " "*22 + "💡 RECOMMANDATIONS" + " "*28 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        score = results['overall_score']
        
        if score >= 90:
            report += "🟢 VOTRE WINDOWS EST EN EXCELLENTE SANTÉ\n\n"
            report += "Aucune action nécessaire !\n"
            report += "Continuez la maintenance préventive tous les 3 mois.\n"
        
        elif score >= 70:
            report += "🟡 VOTRE WINDOWS EST EN BON ÉTAT\n\n"
            report += "Actions recommandées:\n"
            report += "• Surveiller l'évolution\n"
            report += "• Lancer une réparation préventive (optionnel)\n"
            report += "• Vérifier logs détaillés (Event Viewer)\n"
        
        else:
            report += "🔴 RÉPARATION RECOMMANDÉE\n\n"
            report += "Actions urgentes:\n"
            report += "1. Cliquer bouton 'Réparer (DISM + SFC)'\n"
            report += "2. Laisser tourner 15-30 minutes\n"
            report += "3. Redémarrer Windows\n"
            report += "4. Relancer diagnostic\n\n"
            report += "Si problèmes persistent:\n"
            report += "• Réparation avancée (Reset Windows avec conservation fichiers)\n"
            report += "• Ou: Réinstallation propre\n"
        
        report += "\n" + "═" * 70 + "\n"
        
        self.results.append(report)
    
    def start_repair(self):
        """Lancer réparation DISM + SFC"""
        reply = QMessageBox.question(
            self,
            "🔧 Réparation Windows",
            "Lancer réparation complète ?\n\n"
            "• DISM RestoreHealth (15-20 min)\n"
            "• SFC /scannow (10-15 min)\n\n"
            "Durée totale: 25-35 minutes\n"
            "Ne fermez pas cette fenêtre !",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Vérifier admin
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        
        if not is_admin:
            QMessageBox.warning(
                self,
                "⚠️ Droits administrateur requis",
                "La réparation nécessite les droits administrateur.\n\n"
                "Relancez Wapinator en tant qu'administrateur."
            )
            return
        
        # Utiliser la fonction de réparation du main
        self.close()
        
        # Appeler la fonction repair du parent
        try:
            self.parent().parent().run_task("repair", "🔧 Réparation Windows")
        except:
            QMessageBox.warning(self, "⚠️", "Utilisez l'option 'Réparer' du menu principal")
    
    def show_tips(self):
        """Conseils maintenance"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║          💡 CONSEILS MAINTENANCE WINDOWS                    ║
╚══════════════════════════════════════════════════════════════╝

🎯 MAINTENANCE PRÉVENTIVE

═══════════════════════════════════════════════════════════════

📅 MENSUEL (1x par mois)

1️⃣  Windows Update
   • Paramètres > Windows Update
   • "Rechercher des mises à jour"
   • Installer TOUTES les MAJ disponibles
   • Redémarrer

2️⃣  Nettoyage Disque
   • Wapinator > Nettoyage Windows
   • Ou: Paramètres > Stockage > Nettoyage
   • Supprimer fichiers temporaires

3️⃣  Antivirus Scan
   • Windows Security > Analyse complète
   • Ou: Malwarebytes (gratuit)
   • 1-2h de scan

═══════════════════════════════════════════════════════════════

📅 TRIMESTRIEL (1x tous les 3 mois)

1️⃣  Vérification Santé Windows
   • Wapinator > Vérification Santé
   • Si score < 80: Lancer réparation

2️⃣  Défragmentation (HDD uniquement)
   • Optimiser et défragmenter
   • PAS pour SSD !

3️⃣  Vérification Drivers
   • Wapinator > Gestionnaire Drivers
   • MAJ drivers obsolètes (>3 ans)

4️⃣  Nettoyage Démarrage
   • Wapinator > Gestionnaire Démarrage
   • Désactiver programmes inutiles

═══════════════════════════════════════════════════════════════

📅 ANNUEL (1x par an)

1️⃣  Sauvegarde Complète
   • Image système (Macrium Reflect gratuit)
   • Ou: Clone disque entier

2️⃣  Réinstallation Propre (optionnel)
   • Si PC très lent malgré optimisations
   • Reset Windows avec conservation fichiers
   • Ou: Installation propre ISO

═══════════════════════════════════════════════════════════════

🚨 MAINTENANCE D'URGENCE

Quand lancer réparation immédiate:

❌ Écrans bleus (BSOD) fréquents
❌ Programmes crashent souvent
❌ Windows très lent
❌ Erreurs "fichier système corrompu"
❌ Windows Update bloqué
❌ Impossible d'installer logiciels

→ Lancer: DISM + SFC (Wapinator)

═══════════════════════════════════════════════════════════════

🛡️  PRÉVENTION

BONNES PRATIQUES:

✅ Antivirus actif en permanence
✅ Windows Update auto (laisser activé)
✅ Ne pas télécharger sur sites louches
✅ Éviter cracks/keygens (malwares)
✅ Redémarrer PC 1x par semaine min
✅ Ne pas installer 50 logiciels inutiles

MAUVAISES PRATIQUES:

❌ Désactiver Windows Defender
❌ Ignorer Windows Update
❌ "Optimiseurs" type CCleaner
❌ Registry cleaners (danger)
❌ Laisser PC allumé 24/7 sans reboot
❌ Remplir disque à 100%

═══════════════════════════════════════════════════════════════

📊 OUTILS MAINTENANCE WAPINATOR

- 🧹 Nettoyage: Fichiers temporaires
- 🔧 Réparation: DISM + SFC
- 🔍 Diagnostic: BSOD, Réseau, Drivers
- 🚀 Optimisation: Démarrage, Gaming
- 🏥 Santé: Vérification complète

═══════════════════════════════════════════════════════════════

💾 SAUVEGARDES

RÈGLE 3-2-1:
- 3 copies de données importantes
- 2 supports différents (disque + cloud)
- 1 copie hors site (cloud, disque externe ailleurs)

SOLUTIONS:
- OneDrive (intégré Windows)
- Google Drive (gratuit 15 Go)
- Backblaze (5€/mois illimité)
- Disque externe + copie manuelle

═══════════════════════════════════════════════════════════════
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("💡 Conseils Maintenance")
        msg.setText(tips)
        msg.setStyleSheet("""
            QMessageBox { background: #1e1e1e; color: white; }
            QLabel { color: white; font-family: Consolas; font-size: 10px; }
            QPushButton { background: #4CAF50; color: white; padding: 8px; border-radius: 4px; }
        """)
        msg.exec()
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║              ❓ AIDE - VÉRIFICATION SANTÉ                   ║
╚══════════════════════════════════════════════════════════════╝

🤔 À QUOI SERT CET OUTIL ?

Diagnostique l'état de santé général de Windows.
Détecte corruptions, services défaillants, problèmes système.

Alternative rapide à DISM + SFC complets (qui prennent 30+ min)

═══════════════════════════════════════════════════════════════

📊 COMPRENDRE LE SCORE

SCORE 90-100 (🟢 Excellent):
- Aucun problème détecté
- Système stable et sain
- Maintenance préventive suffit

SCORE 70-89 (🟡 Bon):
- Quelques problèmes mineurs
- Rien de critique
- Surveillance recommandée

SCORE 50-69 (🟠 Moyen):
- Problèmes à corriger
- Système encore stable mais attention
- Réparation recommandée sous 1 mois

SCORE 0-49 (🔴 Critique):
- Problèmes graves
- Instabilités possibles
- Réparation URGENTE

═══════════════════════════════════════════════════════════════

🔧 QUAND UTILISER "RÉPARER" ?

Cliquer "Réparer (DISM + SFC)" si:
- Score < 70
- Windows instable
- Erreurs système fréquentes
- Après suppression malware

NE PAS réparer si:
- Score > 90
- Tout fonctionne bien
- "Si ça marche, touche pas"

═══════════════════════════════════════════════════════════════

⏱️  DURÉES

Diagnostic: 2-3 minutes
Réparation: 25-35 minutes (si nécessaire)

═══════════════════════════════════════════════════════════════

💡 ALTERNATIVES

Si réparation échoue ou score reste bas:

1. Reset Windows (conservation fichiers)
   → Paramètres > Récupération

2. Réinstallation propre
   → ISO Windows + USB bootable

3. Point de restauration système
   → Si créé avant problème

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter rapport"""
        content = self.results.toPlainText()
        
        if not content or "BIENVENUE" in content:
            QMessageBox.warning(self, "⚠️", "Aucun rapport à exporter.\nLancez d'abord un diagnostic.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_SanteWindows_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 70 + "\n")
                f.write("  RAPPORT SANTÉ WINDOWS - WAPINATOR\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 70 + "\n\n")
                
                if self.last_results:
                    f.write(f"SCORE GLOBAL: {self.last_results['overall_score']}/100\n\n")
                
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