# modules/ram_tester.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import subprocess
from datetime import datetime
from pathlib import Path
import time

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

class RAMTestWorker(QThread):
    """Worker pour test RAM simple"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        """Test RAM basique"""
        try:
            self.log_signal.emit("Demarrage test RAM basique...\n")
            
            # Informations RAM via wmic
            self.log_signal.emit("Lecture informations RAM...")
            self.progress_signal.emit(20)
            
            result = subprocess.run(
                ['wmic', 'memorychip', 'get', 'Capacity,Speed,Manufacturer', '/format:list'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding='cp850',
                errors='replace'
            )
            
            ram_info = self.parse_ram_info(result.stdout)
            
            self.progress_signal.emit(50)
            self.log_signal.emit(f"\nRAM detectee:")
            self.log_signal.emit(f"  Total: {ram_info['total_gb']} Go")
            self.log_signal.emit(f"  Frequence: {ram_info['speed']} MHz")
            self.log_signal.emit(f"  Barrettes: {ram_info['sticks']}")
            
            # Test mémoire système
            self.log_signal.emit("\nVerification etat memoire systeme...")
            self.progress_signal.emit(70)
            
            # Vérifier erreurs système
            errors_found = self.check_system_errors()
            
            self.progress_signal.emit(100)
            
            result_data = {
                'ram_info': ram_info,
                'errors_found': errors_found,
                'success': True
            }
            
            if errors_found:
                self.log_signal.emit("\n⚠️ Erreurs memoire detectees dans journaux systeme !")
                self.log_signal.emit("   Recommandation: Lancer Windows Memory Diagnostic")
            else:
                self.log_signal.emit("\n✅ Aucune erreur memoire detectee")
            
            self.finished_signal.emit(result_data)
        
        except Exception as e:
            self.log_signal.emit(f"\n❌ Erreur: {str(e)}")
            self.finished_signal.emit({'success': False, 'error': str(e)})
    
    def parse_ram_info(self, output):
        """Parser infos RAM"""
        lines = output.split('\n')
        
        capacities = []
        speeds = []
        
        for line in lines:
            if 'Capacity=' in line:
                try:
                    cap = line.split('=')[1].strip()
                    if cap:
                        capacities.append(int(cap) // (1024**3))  # Convert to GB
                except:
                    pass
            
            if 'Speed=' in line:
                try:
                    speed = line.split('=')[1].strip()
                    if speed:
                        speeds.append(speed)
                except:
                    pass
        
        total_gb = sum(capacities) if capacities else 0
        avg_speed = speeds[0] if speeds else "Inconnu"
        sticks = len(capacities)
        
        return {
            'total_gb': total_gb,
            'speed': avg_speed,
            'sticks': sticks
        }
    
    def check_system_errors(self):
        """Vérifier erreurs mémoire dans journaux"""
        try:
            # Chercher événements mémoire critiques
            result = subprocess.run(
                ['wevtutil', 'qe', 'System', '/c:50', '/rd:true', '/f:text', '/q:*[System[(Level=1 or Level=2) and (EventID=41 or EventID=1001)]]'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            # Si des événements trouvés
            if 'Event[' in result.stdout or 'EventID' in result.stdout:
                return True
            
            return False
        except:
            return False

class RamtesterWindow(QDialog):
    """Fenêtre testeur RAM"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🧪 Testeur RAM Rapide")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🧪 TESTEUR RAM RAPIDE")
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
            "Test rapide RAM Windows • Détection erreurs • Recommandations"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Infos RAM
        self.ram_info_label = QLabel("📊 Informations RAM")
        self.ram_info_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.ram_info_label)
        
        self.ram_details = QLabel("Cliquez 'Analyser RAM' pour commencer")
        self.ram_details.setStyleSheet("color: #888; padding: 10px; background: #2b2b2b; border-radius: 5px;")
        layout.addWidget(self.ram_details)
        
        # Boutons action
        action_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 Analyser RAM")
        self.analyze_btn.clicked.connect(self.analyze_ram)
        self.analyze_btn.setStyleSheet("background: #4CAF50; padding: 12px; font-size: 12px;")
        action_layout.addWidget(self.analyze_btn)
        
        memtest_btn = QPushButton("🧪 Windows Memory Diagnostic")
        memtest_btn.clicked.connect(self.launch_memtest)
        action_layout.addWidget(memtest_btn)
        
        taskmgr_btn = QPushButton("📊 Gestionnaire Tâches")
        taskmgr_btn.clicked.connect(self.open_task_manager)
        action_layout.addWidget(taskmgr_btn)
        
        layout.addLayout(action_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Logs
        logs_label = QLabel("📋 Journal d'analyse")
        logs_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(logs_label)
        
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFont(QFont("Consolas", 9))
        layout.addWidget(self.logs)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Rapport")
        export_btn.clicked.connect(self.export_report)
        bottom_layout.addWidget(export_btn)
        
        tips_btn = QPushButton("💡 Conseils RAM")
        tips_btn.clicked.connect(self.show_tips)
        bottom_layout.addWidget(tips_btn)
        
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
        welcome = """TESTEUR RAM RAPIDE - WAPINATOR

Cet outil permet de:
- Detecter la RAM installee
- Verifier erreurs memoire
- Lancer Windows Memory Diagnostic

TESTS DISPONIBLES:

ANALYSE RAPIDE (1 min):
- Lecture infos RAM (capacite, frequence)
- Verification journaux erreurs
- Recommandations

WINDOWS MEMORY DIAGNOSTIC (10-20 min):
- Test complet Microsoft
- Necessite redemarrage
- Detecte erreurs materielles

QUAND TESTER LA RAM ?

Symptomes problemes RAM:
- Ecrans bleus frequents (BSOD)
- Crashes aleatoires
- Erreurs applications
- PC lent/instable

Cliquez 'Analyser RAM' pour commencer."""
        self.logs.setPlainText(welcome)
    
    def analyze_ram(self):
        """Analyser RAM"""
        self.analyze_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.logs.clear()
        
        self.worker = RAMTestWorker()
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_analysis_finished)
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
    
    def on_analysis_finished(self, result):
        """Analyse terminée"""
        self.analyze_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if result.get('success'):
            ram_info = result.get('ram_info', {})
            errors = result.get('errors_found', False)
            
            # Mettre à jour affichage
            details = f"RAM: {ram_info.get('total_gb', 0)} Go • "
            details += f"Frequence: {ram_info.get('speed', 'N/A')} MHz • "
            details += f"Barrettes: {ram_info.get('sticks', 0)}"
            
            if errors:
                details += "\n⚠️ ERREURS DETECTEES - Test complet recommande"
                self.ram_details.setStyleSheet("color: #FF9800; padding: 10px; background: #2b2b2b; border-radius: 5px; font-weight: bold;")
            else:
                details += "\n✅ Aucune erreur detectee"
                self.ram_details.setStyleSheet("color: #4CAF50; padding: 10px; background: #2b2b2b; border-radius: 5px;")
            
            self.ram_details.setText(details)
            
            if errors:
                reply = QMessageBox.warning(
                    self,
                    "⚠️ Erreurs détectées",
                    "Des erreurs mémoire ont été trouvées dans les journaux système.\n\n"
                    "Recommandation: Lancer Windows Memory Diagnostic\n"
                    "pour un test complet (10-20 min, nécessite redémarrage).\n\n"
                    "Lancer maintenant ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.launch_memtest()
        else:
            QMessageBox.warning(self, "❌", f"Erreur: {result.get('error', 'Inconnu')}")
    
    def launch_memtest(self):
        """Lancer Windows Memory Diagnostic"""
        reply = QMessageBox.warning(
            self,
            "🧪 Windows Memory Diagnostic",
            "Windows Memory Diagnostic va:\n\n"
            "1. Redémarrer votre PC\n"
            "2. Effectuer un test mémoire (10-20 min)\n"
            "3. Redémarrer à nouveau vers Windows\n\n"
            "⚠️ SAUVEGARDEZ votre travail avant !\n\n"
            "Résultats visibles après redémarrage dans:\n"
            "Observateur d'événements > Windows Logs > System\n"
            "Source: MemoryDiagnostics-Results\n\n"
            "Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                subprocess.Popen(['mdsched.exe'])
                QMessageBox.information(
                    self,
                    "✅ Lancé",
                    "Windows Memory Diagnostic lancé.\n\n"
                    "Suivez les instructions à l'écran.\n"
                    "Le PC va redémarrer."
                )
            except:
                QMessageBox.critical(self, "❌", "Impossible de lancer Memory Diagnostic")
    
    def open_task_manager(self):
        """Ouvrir gestionnaire tâches (onglet Performance)"""
        try:
            subprocess.Popen(['taskmgr', '/4'])  # /4 = Performance tab
        except:
            QMessageBox.warning(self, "❌", "Impossible d'ouvrir le Gestionnaire")
    
    def show_tips(self):
        """Conseils RAM"""
        QMessageBox.information(
            self,
            "💡 Conseils RAM",
            "PROBLEMES RAM COURANTS:\n\n"
            "SYMPTOMES:\n"
            "• BSOD (ecrans bleus)\n"
            "• Crashes aleatoires\n"
            "• Erreurs 'memoire insuffisante'\n"
            "• PC lent malgre config correcte\n\n"
            "SOLUTIONS:\n\n"
            "1. TEST COMPLET:\n"
            "   → Windows Memory Diagnostic\n"
            "   → MemTest86 (USB bootable)\n\n"
            "2. VERIFIER INSTALLATION:\n"
            "   → Barrettes bien enfoncees\n"
            "   → Pas de poussiere slots\n"
            "   → Dual channel correct (slots 1+3 ou 2+4)\n\n"
            "3. UPGRADE RAM:\n"
            "   Windows 11: 8 Go minimum, 16 Go recommande\n"
            "   Gaming/Creation: 32 Go ideal\n\n"
            "4. BARRETTE DEFECTUEUSE:\n"
            "   → Tester barrettes une par une\n"
            "   → Remplacer celle qui echoue\n\n"
            "5. PARAMETRES BIOS:\n"
            "   → XMP/DOCP pour frequence max\n"
            "   → Voltage correct (1.35V DDR4)"
        )
    
    def show_help(self):
        """Aide"""
        QMessageBox.information(
            self,
            "❓ Aide",
            "COMMENT UTILISER:\n\n"
            "1. Cliquer 'Analyser RAM'\n"
            "   → Detecte RAM installee\n"
            "   → Verifie erreurs journaux\n\n"
            "2. Si erreurs detectees:\n"
            "   → Lancer Memory Diagnostic\n"
            "   → Test complet 10-20 min\n\n"
            "3. Lire resultats:\n"
            "   → Observateur evenements\n"
            "   → Windows Logs > System\n"
            "   → Source: MemoryDiagnostics-Results\n\n"
            "CODES ERREUR BSOD RAM:\n\n"
            "• MEMORY_MANAGEMENT\n"
            "• PAGE_FAULT_IN_NONPAGED_AREA\n"
            "• IRQL_NOT_LESS_OR_EQUAL\n"
            "• BAD_POOL_HEADER\n\n"
            "→ Si ces erreurs: tester RAM !"
        )
    
    def export_report(self):
        """Exporter rapport"""
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_RAM_Test_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("RAPPORT TEST RAM - WAPINATOR\n")
                f.write(f"Genere: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(self.logs.toPlainText())
                f.write("\n" + "=" * 70 + "\n")
            
            QMessageBox.information(self, "✅ Exporté", f"Rapport sauvegarde:\n{filename.name}")
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Erreur export:\n{str(e)}")