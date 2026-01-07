# modules/windows_update_fix.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import subprocess
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

class WindowsUpdateFixWorker(QThread):
    """Worker pour réparer Windows Update"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, operations):
        super().__init__()
        self.operations = operations
    
    def run(self):
        """Exécuter réparation Windows Update"""
        try:
            self.log_signal.emit("Démarrage réparation Windows Update...\n")
            
            total_ops = len(self.operations)
            
            for i, operation in enumerate(self.operations):
                progress = int((i / total_ops) * 100)
                self.progress_signal.emit(progress)
                
                if operation == 'stop_services':
                    self.stop_wu_services()
                elif operation == 'clear_cache':
                    self.clear_wu_cache()
                elif operation == 'start_services':
                    self.start_wu_services()
                elif operation == 'reset_components':
                    self.reset_wu_components()
                elif operation == 'repair_store':
                    self.repair_component_store()
            
            self.progress_signal.emit(100)
            self.log_signal.emit("\n✅ Réparation terminée avec succès !")
            self.finished_signal.emit(True)
        
        except Exception as e:
            self.log_signal.emit(f"\n❌ Erreur: {str(e)}")
            self.finished_signal.emit(False)
    
    def stop_wu_services(self):
        """Arrêter les services Windows Update"""
        self.log_signal.emit("🛑 Arrêt des services Windows Update...")
        
        services = ['wuauserv', 'cryptSvc', 'bits', 'msiserver']
        
        for service in services:
            try:
                subprocess.run(
                    ['net', 'stop', service],
                    capture_output=True,
                    timeout=30,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                self.log_signal.emit(f"  ✅ Service {service} arrêté")
            except:
                self.log_signal.emit(f"  ⚠️ Service {service} déjà arrêté")
    
    def clear_wu_cache(self):
        """Vider le cache Windows Update"""
        self.log_signal.emit("\n🗑️ Nettoyage cache Windows Update...")
        
        cache_paths = [
            r"C:\Windows\SoftwareDistribution\Download",
            r"C:\Windows\SoftwareDistribution\DataStore"
        ]
        
        for cache_path in cache_paths:
            try:
                path = Path(cache_path)
                if path.exists():
                    # Supprimer contenu
                    for item in path.iterdir():
                        try:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                import shutil
                                shutil.rmtree(item)
                        except:
                            pass
                    
                    self.log_signal.emit(f"  ✅ Cache vidé: {cache_path}")
                else:
                    self.log_signal.emit(f"  ℹ️ Cache non trouvé: {cache_path}")
            except Exception as e:
                self.log_signal.emit(f"  ⚠️ Erreur nettoyage {cache_path}: {str(e)}")
    
    def start_wu_services(self):
        """Redémarrer les services Windows Update"""
        self.log_signal.emit("\n▶️ Redémarrage des services...")
        
        services = ['wuauserv', 'cryptSvc', 'bits', 'msiserver']
        
        for service in services:
            try:
                subprocess.run(
                    ['net', 'start', service],
                    capture_output=True,
                    timeout=30,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                self.log_signal.emit(f"  ✅ Service {service} démarré")
            except:
                self.log_signal.emit(f"  ⚠️ Erreur démarrage {service}")
    
    def reset_wu_components(self):
        """Réinitialiser composants Windows Update"""
        self.log_signal.emit("\n🔄 Réinitialisation composants WU...")
        
        commands = [
            ['regsvr32', '/s', 'wuaueng.dll'],
            ['regsvr32', '/s', 'wuapi.dll'],
            ['regsvr32', '/s', 'wups.dll'],
            ['regsvr32', '/s', 'wucltux.dll']
        ]
        
        for cmd in commands:
            try:
                subprocess.run(
                    cmd,
                    timeout=10,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                self.log_signal.emit(f"  ✅ Composant réenregistré: {cmd[2]}")
            except:
                self.log_signal.emit(f"  ⚠️ Erreur: {cmd[2]}")
    
    def repair_component_store(self):
        """Réparer magasin de composants"""
        self.log_signal.emit("\n🔧 Réparation magasin composants (DISM)...")
        self.log_signal.emit("  ⏳ Cela peut prendre plusieurs minutes...")
        
        try:
            result = subprocess.run(
                ['dism', '/online', '/cleanup-image', '/restorehealth'],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes max
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ Magasin composants réparé")
            else:
                self.log_signal.emit("  ⚠️ Erreur réparation DISM")
        except subprocess.TimeoutExpired:
            self.log_signal.emit("  ⚠️ Timeout DISM (> 10 min)")
        except Exception as e:
            self.log_signal.emit(f"  ⚠️ Erreur: {str(e)}")

class WindowsupdatefixWindow(QDialog):
    """Fenêtre réparateur Windows Update"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔄 Réparateur Windows Update")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🔄 RÉPARATEUR WINDOWS UPDATE")
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
            "Résout les problèmes de Windows Update • Reset cache & services • Réparation composants"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Warning
        warning = QLabel(
            "⚠️ ATTENTION : Nécessite droits administrateur • Fermer programmes importants"
        )
        warning.setStyleSheet("color: #FF9800; font-size: 11px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(warning)
        
        # Boutons action rapide
        quick_layout = QHBoxLayout()
        
        self.quick_fix_btn = QPushButton("⚡ Réparation Rapide")
        self.quick_fix_btn.clicked.connect(self.quick_fix)
        self.quick_fix_btn.setStyleSheet("background: #4CAF50; padding: 12px; font-size: 12px;")
        quick_layout.addWidget(self.quick_fix_btn)
        
        self.full_fix_btn = QPushButton("🔧 Réparation Complète")
        self.full_fix_btn.clicked.connect(self.full_fix)
        self.full_fix_btn.setStyleSheet("background: #2196F3; padding: 12px; font-size: 12px;")
        quick_layout.addWidget(self.full_fix_btn)
        
        layout.addLayout(quick_layout)
        
        # Boutons actions individuelles
        actions_layout = QHBoxLayout()
        
        stop_btn = QPushButton("🛑 Arrêter Services")
        stop_btn.clicked.connect(lambda: self.run_fix(['stop_services']))
        actions_layout.addWidget(stop_btn)
        
        clear_btn = QPushButton("🗑️ Vider Cache")
        clear_btn.clicked.connect(lambda: self.run_fix(['stop_services', 'clear_cache', 'start_services']))
        actions_layout.addWidget(clear_btn)
        
        reset_btn = QPushButton("🔄 Reset Composants")
        reset_btn.clicked.connect(lambda: self.run_fix(['reset_components']))
        actions_layout.addWidget(reset_btn)
        
        layout.addLayout(actions_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Logs
        logs_label = QLabel("📋 Journal d'opérations")
        logs_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(logs_label)
        
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFont(QFont("Consolas", 9))
        layout.addWidget(self.logs)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Log")
        export_btn.clicked.connect(self.export_log)
        bottom_layout.addWidget(export_btn)
        
        wu_settings_btn = QPushButton("⚙️ Paramètres WU")
        wu_settings_btn.clicked.connect(self.open_wu_settings)
        bottom_layout.addWidget(wu_settings_btn)
        
        troubleshoot_btn = QPushButton("🔍 Utilitaire Résolution")
        troubleshoot_btn.clicked.connect(self.run_troubleshooter)
        bottom_layout.addWidget(troubleshoot_btn)
        
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
        
        self.worker = None
        self.show_welcome()
    
    def show_welcome(self):
        """Message bienvenue"""
        welcome = """REPARATEUR WINDOWS UPDATE - WAPINATOR

Cet outil resout les problemes courants de Windows Update:
- Erreurs de telechargement
- Mises a jour bloquees
- Services qui ne demarrent pas
- Cache corrompu

OPERATIONS DISPONIBLES:

REPARATION RAPIDE (2-3 min):
- Arret services WU
- Vidage cache
- Redemarrage services

REPARATION COMPLETE (10-15 min):
- Reparation rapide
- Reset composants WU
- Reparation magasin composants (DISM)

Choisissez l'option adaptee a votre probleme."""
        self.logs.setPlainText(welcome)
    
    def quick_fix(self):
        """Réparation rapide"""
        reply = QMessageBox.question(
            self,
            "⚡ Réparation Rapide",
            "Durée: 2-3 minutes\n\n"
            "Actions:\n"
            "• Arrêt services Windows Update\n"
            "• Vidage cache\n"
            "• Redémarrage services\n\n"
            "Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.run_fix(['stop_services', 'clear_cache', 'start_services'])
    
    def full_fix(self):
        """Réparation complète"""
        reply = QMessageBox.question(
            self,
            "🔧 Réparation Complète",
            "Durée: 10-15 minutes\n\n"
            "Actions:\n"
            "• Arrêt services\n"
            "• Vidage cache\n"
            "• Reset composants WU\n"
            "• Réparation DISM (long)\n"
            "• Redémarrage services\n\n"
            "⚠️ Ne pas interrompre le processus !\n\n"
            "Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.run_fix(['stop_services', 'clear_cache', 'reset_components', 'repair_store', 'start_services'])
    
    def run_fix(self, operations):
        """Lancer réparation"""
        self.quick_fix_btn.setEnabled(False)
        self.full_fix_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.logs.clear()
        
        self.worker = WindowsUpdateFixWorker(operations)
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_fix_finished)
        self.worker.start()
    
    def add_log(self, message):
        """Ajouter log"""
        self.logs.append(message)
        self.logs.verticalScrollBar().setValue(
            self.logs.verticalScrollBar().maximum()
        )
    
    def update_progress(self, value):
        """Mettre à jour progression"""
        self.progress.setValue(value)
    
    def on_fix_finished(self, success):
        """Réparation terminée"""
        self.quick_fix_btn.setEnabled(True)
        self.full_fix_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if success:
            QMessageBox.information(
                self,
                "✅ Succès",
                "Réparation terminée !\n\n"
                "Actions recommandées:\n"
                "• Redémarrer PC\n"
                "• Lancer recherche mises à jour\n"
                "• Vérifier si problème résolu"
            )
        else:
            QMessageBox.warning(
                self,
                "⚠️ Attention",
                "Réparation terminée avec erreurs.\n\n"
                "Si problème persiste:\n"
                "• Vérifier log pour détails\n"
                "• Essayer 'Réparation Complète'\n"
                "• Utiliser 'Utilitaire Résolution'"
            )
    
    def open_wu_settings(self):
        """Ouvrir paramètres Windows Update"""
        try:
            subprocess.Popen(['ms-settings:windowsupdate'])
        except:
            QMessageBox.warning(self, "❌", "Impossible d'ouvrir les paramètres")
    
    def run_troubleshooter(self):
        """Lancer utilitaire résolution problèmes"""
        try:
            subprocess.Popen(['msdt.exe', '/id', 'WindowsUpdateDiagnostic'])
        except:
            QMessageBox.warning(self, "❌", "Impossible de lancer l'utilitaire")
    
    def show_help(self):
        """Aide"""
        QMessageBox.information(
            self,
            "❓ Aide",
            "ERREURS WINDOWS UPDATE COURANTES:\n\n"
            "0x80070002, 0x8024402F, 0x80240034:\n"
            "→ Essayer Réparation Rapide\n\n"
            "0x80073712, 0x800F0922:\n"
            "→ Utiliser Réparation Complète (DISM)\n\n"
            "Service ne démarre pas:\n"
            "→ Arrêter Services puis Redémarrer\n\n"
            "APRÈS RÉPARATION:\n"
            "1. Redémarrer PC\n"
            "2. Paramètres > Windows Update\n"
            "3. Rechercher mises à jour\n\n"
            "SI PROBLÈME PERSISTE:\n"
            "→ Utiliser 'Utilitaire Résolution'\n"
            "→ Créer nouveau profil utilisateur\n"
            "→ Réinstaller Windows (dernier recours)"
        )
    
    def export_log(self):
        """Exporter log"""
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_WU_Fix_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("JOURNAL REPARATION WINDOWS UPDATE - WAPINATOR\n")
                f.write(f"Genere: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(self.logs.toPlainText())
                f.write("\n" + "=" * 70 + "\n")
            
            QMessageBox.information(self, "✅ Exporté", f"Log sauvegardé:\n{filename.name}")
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Erreur export:\n{str(e)}")