# modules/startup_manager.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QTableWidget, 
                                QTableWidgetItem, QHeaderView, QCheckBox, QWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import subprocess
import winreg
import os
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

# Base de données impacts connus
KNOWN_IMPACTS = {
    # Haute priorité (garder)
    'ctfmon': 'low',  # Clavier Windows
    'igfxtray': 'low',  # Intel Graphics
    'realtek': 'low',  # Audio Realtek
    'nvbackend': 'medium',  # NVIDIA GeForce Experience
    'amdrsserv': 'medium',  # AMD Radeon
    
    # Moyenne priorité
    'discord': 'medium',
    'spotify': 'medium',
    'steam': 'high',
    'epicgameslauncher': 'high',
    'onedrive': 'medium',
    'dropbox': 'medium',
    'googledrive': 'medium',
    
    # Bloatware connu (désactiver)
    'ccleaner': 'high',
    'mcafee': 'high',
    'norton': 'high',
    'avast': 'high',
    'avg': 'high',
    'wondershare': 'high',
    'utorrent': 'medium',
    'skype': 'medium',
    'adobe': 'medium',
}

class StartupScanWorker(QThread):
    """Worker pour scanner programmes au démarrage"""
    log_signal = pyqtSignal(str)
    program_found = pyqtSignal(dict)
    finished_signal = pyqtSignal(list)
    
    def run(self):
        """Scanner tous les programmes au démarrage"""
        programs = []
        
        try:
            self.log_signal.emit("🔍 Scan des programmes au démarrage...\n")
            
            # 1. Registry - Current User
            self.log_signal.emit("📋 Analyse: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run")
            programs.extend(self.scan_registry_key(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run"
            ))
            
            # 2. Registry - Local Machine
            self.log_signal.emit("📋 Analyse: HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run")
            programs.extend(self.scan_registry_key(
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\Run"
            ))
            
            # 3. Registry - RunOnce
            self.log_signal.emit("📋 Analyse: RunOnce")
            try:
                programs.extend(self.scan_registry_key(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
                ))
            except:
                pass
            
            # 4. Startup Folders
            self.log_signal.emit("📁 Analyse: Dossiers Démarrage")
            programs.extend(self.scan_startup_folders())
            
            # 5. Task Scheduler (simplifié)
            self.log_signal.emit("⏰ Analyse: Tâches planifiées")
            programs.extend(self.scan_scheduled_tasks())
            
            self.log_signal.emit(f"\n✅ {len(programs)} programmes trouvés")
            self.finished_signal.emit(programs)
        
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit([])
    
    def scan_registry_key(self, hkey, subkey):
        """Scanner une clé de registre"""
        programs = []
        
        try:
            key = winreg.OpenKey(hkey, subkey)
            i = 0
            
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    
                    if name and value:
                        program = {
                            'name': name,
                            'path': value,
                            'location': 'Registry',
                            'location_detail': subkey,
                            'enabled': True,
                            'impact': self.estimate_impact(name, value)
                        }
                        
                        programs.append(program)
                        self.program_found.emit(program)
                    
                    i += 1
                
                except OSError:
                    break
            
            winreg.CloseKey(key)
        
        except Exception as e:
            pass
        
        return programs
    
    def scan_startup_folders(self):
        """Scanner dossiers de démarrage"""
        programs = []
        
        # Dossier utilisateur
        user_startup = Path(os.path.expandvars(
            r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
        ))
        
        # Dossier système
        common_startup = Path(os.path.expandvars(
            r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
        ))
        
        for folder in [user_startup, common_startup]:
            if folder.exists():
                for item in folder.iterdir():
                    if item.suffix in ['.lnk', '.exe', '.bat']:
                        program = {
                            'name': item.stem,
                            'path': str(item),
                            'location': 'Startup Folder',
                            'location_detail': str(folder),
                            'enabled': True,
                            'impact': self.estimate_impact(item.stem, str(item))
                        }
                        
                        programs.append(program)
                        self.program_found.emit(program)
        
        return programs
    
    def scan_scheduled_tasks(self):
        """Scanner tâches planifiées (simplifié)"""
        programs = []
        
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/fo", "csv", "/v"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="cp850",
                errors="replace"
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                for line in lines[1:]:  # Skip header
                    if 'At log on' in line or 'At startup' in line:
                        parts = line.split('","')
                        if len(parts) > 1:
                            task_name = parts[0].strip('"')
                            
                            # Ignorer tâches système Microsoft
                            if '\\Microsoft\\' in task_name:
                                continue
                            
                            program = {
                                'name': task_name.split('\\')[-1],
                                'path': task_name,
                                'location': 'Task Scheduler',
                                'location_detail': 'Tâche planifiée',
                                'enabled': True,
                                'impact': 'medium'
                            }
                            
                            programs.append(program)
                            self.program_found.emit(program)
        
        except:
            pass
        
        return programs
    
    def estimate_impact(self, name, path):
        """Estimer l'impact sur le démarrage"""
        name_lower = name.lower()
        path_lower = path.lower()
        
        # Chercher dans base connue
        for keyword, impact in KNOWN_IMPACTS.items():
            if keyword in name_lower or keyword in path_lower:
                return impact
        
        # Heuristiques
        
        # Probablement léger
        if any(x in name_lower for x in ['driver', 'service', 'system', 'windows', 'intel', 'amd', 'nvidia']):
            return 'low'
        
        # Probablement lourd
        if any(x in path_lower for x in ['steam', 'epic', 'origin', 'ubisoft', 'battle.net']):
            return 'high'
        
        # Par défaut : moyen
        return 'medium'

class StartupmanagerWindow(QDialog):
    """Fenêtre gestionnaire de démarrage"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🚀 Gestionnaire de Démarrage")
        self.setMinimumSize(1200, 800)
        
        self.programs = []
        self.changes_made = []
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🚀 GESTIONNAIRE DE DÉMARRAGE")
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
            "Gérez les programmes qui se lancent au démarrage de Windows • Réduisez le temps de boot"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Warning
        warning = QLabel(
            "⚠️ ATTENTION : Ne désactivez que les programmes que vous reconnaissez !"
        )
        warning.setStyleSheet("color: #FF9800; font-size: 11px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(warning)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Scanner Démarrage")
        self.scan_btn.clicked.connect(self.scan_startup)
        btn_layout.addWidget(self.scan_btn)
        
        self.disable_selected_btn = QPushButton("❌ Désactiver Sélection")
        self.disable_selected_btn.clicked.connect(self.disable_selected)
        self.disable_selected_btn.setEnabled(False)
        self.disable_selected_btn.setStyleSheet("background: #F44336;")
        btn_layout.addWidget(self.disable_selected_btn)
        
        self.disable_bloat_btn = QPushButton("🗑️ Désactiver Bloatware")
        self.disable_bloat_btn.clicked.connect(self.disable_bloatware)
        self.disable_bloat_btn.setEnabled(False)
        btn_layout.addWidget(self.disable_bloat_btn)
        
        tips_btn = QPushButton("💡 Conseils Optimisation")
        tips_btn.clicked.connect(self.show_tips)
        btn_layout.addWidget(tips_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Table programmes
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["☑", "Nom", "Chemin", "Emplacement", "Impact", "Conseil"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel("Aucun programme scanné")
        self.stats_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.stats_label)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("✅ APPLIQUER CHANGEMENTS")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("background: #4CAF50; font-weight: bold; padding: 12px;")
        bottom_layout.addWidget(self.apply_btn)
        
        export_btn = QPushButton("💾 Exporter Liste")
        export_btn.clicked.connect(self.export_report)
        bottom_layout.addWidget(export_btn)
        
        taskmgr_btn = QPushButton("🖥️ Gestionnaire Tâches")
        taskmgr_btn.clicked.connect(self.open_task_manager)
        bottom_layout.addWidget(taskmgr_btn)
        
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
            QTableWidget {
                background: #2b2b2b;
                color: white;
                border: 1px solid #444;
                gridline-color: #444;
                alternate-background-color: #1e1e1e;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: #4CAF50; }
            QHeaderView::section {
                background: #333;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        
        self.show_welcome()
        self.worker = None
    
    def show_welcome(self):
        """Message de bienvenue"""
        self.table.setRowCount(1)
        welcome = QTableWidgetItem(
            "👋 Cliquez sur 'Scanner Démarrage' pour analyser tous les programmes qui se lancent au démarrage de Windows"
        )
        welcome.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 11))
        self.table.setItem(0, 0, welcome)
        self.table.setSpan(0, 0, 1, 6)
    
    def scan_startup(self):
        """Lancer scan programmes démarrage"""
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self.table.setRowCount(0)
        self.programs = []
        self.changes_made = []
        
        # Lancer worker
        self.worker = StartupScanWorker()
        self.worker.log_signal.connect(self.update_stats)
        self.worker.program_found.connect(self.add_program_to_table)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()
    
    def update_stats(self, message):
        """Mettre à jour les stats"""
        self.stats_label.setText(message)
    
    def add_program_to_table(self, program):
        """Ajouter programme à la table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(program['enabled'])
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 0, checkbox_widget)
        
        # Nom
        name_item = QTableWidgetItem(program['name'])
        self.table.setItem(row, 1, name_item)
        
        # Chemin (tronqué si trop long)
        path = program['path']
        if len(path) > 60:
            path = path[:57] + "..."
        self.table.setItem(row, 2, QTableWidgetItem(path))
        
        # Emplacement
        self.table.setItem(row, 3, QTableWidgetItem(program['location']))
        
        # Impact
        impact = program['impact']
        impact_text = {
            'low': '🟢 Faible',
            'medium': '🟡 Moyen',
            'high': '🔴 Élevé'
        }.get(impact, '⚪ Inconnu')
        
        impact_item = QTableWidgetItem(impact_text)
        
        if impact == 'high':
            impact_item.setForeground(QColor("#F44336"))
        elif impact == 'medium':
            impact_item.setForeground(QColor("#FF9800"))
        else:
            impact_item.setForeground(QColor("#4CAF50"))
        
        self.table.setItem(row, 4, impact_item)
        
        # Conseil
        advice = self.get_advice(program)
        self.table.setItem(row, 5, QTableWidgetItem(advice))
    
    def get_advice(self, program):
        """Obtenir conseil pour un programme"""
        name_lower = program['name'].lower()
        impact = program['impact']
        
        # Bloatware connu
        bloatware = ['ccleaner', 'mcafee', 'norton', 'avast', 'avg', 'wondershare']
        if any(b in name_lower for b in bloatware):
            return "🗑️ Désactiver (bloatware)"
        
        # Launcher gaming
        launchers = ['steam', 'epic', 'origin', 'ubisoft', 'battle.net']
        if any(l in name_lower for l in launchers):
            return "⚠️ Optionnel (lancer manuellement)"
        
        # Cloud sync
        cloud = ['onedrive', 'dropbox', 'google drive', 'icloud']
        if any(c in name_lower for c in cloud):
            return "💭 Si utilisé, garder"
        
        # Drivers système
        system = ['intel', 'amd', 'nvidia', 'realtek', 'driver']
        if any(s in name_lower for s in system):
            return "✅ Garder (système)"
        
        # Par défaut selon impact
        if impact == 'high':
            return "⚠️ Ralentit démarrage"
        elif impact == 'medium':
            return "💡 Évaluer besoin"
        else:
            return "✅ Impact faible"
    
    def on_item_clicked(self, item):
        """Gestion clic sur item"""
        # Permettre de cocher/décocher via clic sur ligne
        row = item.row()
        checkbox_widget = self.table.cellWidget(row, 0)
        
        if checkbox_widget:
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and item.column() != 0:
                checkbox.setChecked(not checkbox.isChecked())
    
    def on_scan_finished(self, programs):
        """Scan terminé"""
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.disable_selected_btn.setEnabled(True)
        self.disable_bloat_btn.setEnabled(True)
        
        self.programs = programs
        
        if not programs:
            self.stats_label.setText("❌ Aucun programme trouvé")
            return
        
        # Calculer stats
        total = len(programs)
        high_impact = sum(1 for p in programs if p['impact'] == 'high')
        medium_impact = sum(1 for p in programs if p['impact'] == 'medium')
        low_impact = sum(1 for p in programs if p['impact'] == 'low')
        
        stats = f"📊 Total: {total} programmes | "
        stats += f"🔴 Impact élevé: {high_impact} | "
        stats += f"🟡 Impact moyen: {medium_impact} | "
        stats += f"🟢 Impact faible: {low_impact}"
        
        self.stats_label.setText(stats)
        
        # Estimation temps boot
        estimated_time = high_impact * 5 + medium_impact * 2 + low_impact * 0.5
        
        if high_impact > 5:
            QMessageBox.warning(
                self,
                "⚠️ Trop de programmes au démarrage",
                f"{high_impact} programmes à fort impact détectés !\n\n"
                f"Temps démarrage estimé: +{estimated_time:.0f} secondes\n\n"
                "Recommandation: Désactiver les programmes inutiles"
            )
    
    def disable_selected(self):
        """Désactiver les programmes décochés"""
        changes = []
        
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                name = self.table.item(row, 1).text()
                
                # Trouver programme correspondant
                program = next((p for p in self.programs if p['name'] == name), None)
                
                if program:
                    # Si décoché = à désactiver
                    if not checkbox.isChecked() and program['enabled']:
                        changes.append(('disable', program))
        
        if not changes:
            QMessageBox.information(self, "ℹ️", "Aucun changement détecté.\nDécochez les programmes à désactiver.")
            return
        
        # Confirmation
        programs_list = "\n".join([f"• {p['name']}" for _, p in changes[:10]])
        if len(changes) > 10:
            programs_list += f"\n... et {len(changes)-10} autres"
        
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation",
            f"Désactiver {len(changes)} programme(s) ?\n\n{programs_list}\n\n"
            "Ces programmes ne se lanceront plus au démarrage.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.changes_made = changes
            self.apply_btn.setEnabled(True)
            QMessageBox.information(
                self,
                "✅ Prêt",
                f"{len(changes)} changement(s) enregistré(s).\n\nCliquez 'APPLIQUER CHANGEMENTS' pour finaliser."
            )
    
    def disable_bloatware(self):
        """Désactiver automatiquement le bloatware connu"""
        bloatware_keywords = ['ccleaner', 'mcafee', 'norton', 'avast', 'avg', 'wondershare', 'utorrent']
        
        changes = []
        
        for program in self.programs:
            name_lower = program['name'].lower()
            
            if any(b in name_lower for b in bloatware_keywords):
                if program['enabled']:
                    changes.append(('disable', program))
        
        if not changes:
            QMessageBox.information(self, "✅", "Aucun bloatware détecté !\n\nVotre système est propre.")
            return
        
        programs_list = "\n".join([f"• {p['name']}" for _, p in changes])
        
        reply = QMessageBox.question(
            self,
            "🗑️ Bloatware détecté",
            f"{len(changes)} bloatware(s) trouvé(s) :\n\n{programs_list}\n\nDésactiver ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.changes_made = changes
            self.apply_btn.setEnabled(True)
            QMessageBox.information(
                self,
                "✅ Prêt",
                f"{len(changes)} bloatware(s) marqué(s) pour désactivation.\n\nCliquez 'APPLIQUER CHANGEMENTS'."
            )
    
    def apply_changes(self):
        """Appliquer les changements"""
        if not self.changes_made:
            QMessageBox.warning(self, "⚠️", "Aucun changement à appliquer.")
            return
        
        success = 0
        failed = 0
        
        for action, program in self.changes_made:
            if action == 'disable':
                if self.disable_program(program):
                    success += 1
                else:
                    failed += 1
        
        # Résumé
        msg = f"✅ Changements appliqués !\n\n"
        msg += f"Réussis: {success}\n"
        
        if failed > 0:
            msg += f"Échecs: {failed}\n\n"
            msg += "Note: Certains programmes nécessitent des droits admin"
        
        msg += "\n\n🔄 Redémarrez Windows pour voir l'effet"
        
        QMessageBox.information(self, "✅ Terminé", msg)
        
        # Réinitialiser
        self.changes_made = []
        self.apply_btn.setEnabled(False)
        
        # Rescanner
        self.scan_startup()
    
    def disable_program(self, program):
        """Désactiver un programme au démarrage"""
        try:
            location = program['location']
            
            if location == 'Registry':
                # Supprimer de la registry
                subkey = program['location_detail']
                
                # Essayer HKCU
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_WRITE)
                    winreg.DeleteValue(key, program['name'])
                    winreg.CloseKey(key)
                    return True
                except:
                    pass
                
                # Essayer HKLM (nécessite admin)
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, winreg.KEY_WRITE)
                    winreg.DeleteValue(key, program['name'])
                    winreg.CloseKey(key)
                    return True
                except:
                    pass
            
            elif location == 'Startup Folder':
                # Supprimer fichier
                path = Path(program['path'])
                if path.exists():
                    path.unlink()
                    return True
            
            elif location == 'Task Scheduler':
                # Désactiver tâche
                subprocess.run(
                    ["schtasks", "/change", "/tn", program['path'], "/disable"],
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                return True
            
            return False
        
        except Exception as e:
            print(f"Erreur désactivation {program['name']}: {e}")
            return False
    
    def open_task_manager(self):
        """Ouvrir Gestionnaire des tâches"""
        try:
            subprocess.Popen(["taskmgr", "/4"], creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0)
        except:
            QMessageBox.warning(self, "❌", "Impossible d'ouvrir le Gestionnaire des tâches")
    
    def show_tips(self):
        """Conseils optimisation"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║         💡 CONSEILS OPTIMISATION DÉMARRAGE                  ║
╚══════════════════════════════════════════════════════════════╝

🎯 OBJECTIF: Réduire temps de démarrage Windows

═══════════════════════════════════════════════════════════════

✅ PROGRAMMES À GARDER ACTIVÉS

- Drivers systèmes (Intel, AMD, NVIDIA, Realtek)
- Antivirus (si bon, pas bloatware type McAfee trial)
- Utilitaires clavier/souris (Logitech, Corsair, etc.)
- Services cloud SI utilisés quotidiennement

═══════════════════════════════════════════════════════════════

❌ PROGRAMMES À DÉSACTIVER

BLOATWARE (inutile):
- CCleaner, Advanced SystemCare
- McAfee/Norton trial (préinstallé PC)
- Wondershare, Toolbar divers
- Programmes jamais utilisés

LAUNCHERS GAMING (lancer manuellement):
- Steam, Epic Games, Origin
- Battle.net, Ubisoft Connect
- GOG Galaxy, EA App

MESSAGING (lancer quand besoin):
- Discord, Skype, Teams
- Spotify, iTunes

═══════════════════════════════════════════════════════════════

🚀 GAINS ATTENDUS

AVANT:
- 10-20 programmes au démarrage
- Temps boot: 60-120 secondes
- Utilisation immédiate: Non (trop de chargements)

APRÈS (optimisé):
- 5-8 programmes essentiels
- Temps boot: 20-40 secondes
- Utilisation immédiate: Oui ✅

GAIN MOYEN: -30 à -60 secondes de boot

═══════════════════════════════════════════════════════════════

💡 RÈGLE D'OR

"Si je ne l'utilise pas dans les 5 minutes après démarrage,
 je n'en ai pas besoin au démarrage !"

Exemples:
- Steam → Désactiver (lancer quand jeu)
- Discord → Désactiver (lancer quand besoin)
- OneDrive → Garder (sync continue)
- Drivers GPU → Garder (système)

═══════════════════════════════════════════════════════════════

⚙️  OPTIMISATIONS COMPLÉMENTAIRES

1️⃣  FAST BOOT WINDOWS
   • Panneau config > Options alimentation
   • "Choisir rôle boutons alimentation"
   • "Activer démarrage rapide"

2️⃣  SSD vs HDD
   • SSD: Boot 15-30s
   • HDD: Boot 60-120s
   • Upgrade #1 pour vitesse

3️⃣  RAM SUFFISANTE
   • 8 Go minimum Windows 11
   • 16 Go recommandé
   • Manque RAM = swap disque = lent

4️⃣  DÉFRAGMENTATION (HDD uniquement)
   • SSD: NE JAMAIS défragmenter
   • HDD: 1x par mois

═══════════════════════════════════════════════════════════════

🔄 TESTER L'IMPACT

MÉTHODE:

1. Noter temps boot actuel (chrono)
2. Désactiver programmes lourds
3. Redémarrer
4. Chronométrer nouveau temps boot
5. Comparer !

MESURE PRÉCISE:
- Gestionnaire tâches > Performance
- "Durée d'activité" après boot

═══════════════════════════════════════════════════════════════

⚠️  PRÉCAUTIONS

❌ Ne JAMAIS désactiver:
- Windows Security
- Windows Update
- Drivers audio/vidéo
- Logiciels professionnels requis

✅ Toujours garder une sauvegarde:
- Point de restauration système
- Ou note programmes désactivés

En cas de problème:
→ Réactiver via Gestionnaire tâches
→ Onglet "Démarrage" > Clic droit > Activer

═══════════════════════════════════════════════════════════════
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("💡 Conseils Optimisation")
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
║           ❓ AIDE - GESTIONNAIRE DÉMARRAGE                  ║
╚══════════════════════════════════════════════════════════════╝

🤔 QU'EST-CE QUE LE DÉMARRAGE ?

Programmes qui se lancent automatiquement quand Windows démarre.
Problème: Trop de programmes = boot lent + RAM utilisée

═══════════════════════════════════════════════════════════════

📊 COMPRENDRE L'AFFICHAGE

COLONNES:

- ☑ : Coché = Actif | Décoché = À désactiver
- Nom: Nom du programme
- Chemin: Emplacement fichier
- Emplacement: Registry / Folder / Task
- Impact: Effet sur vitesse boot
  → 🟢 Faible (< 1s)
  → 🟡 Moyen (1-3s)
  → 🔴 Élevé (> 3s)
- Conseil: Recommandation

═══════════════════════════════════════════════════════════════

🛠️  UTILISATION

1. Cliquer "Scanner Démarrage"
2. Analyser liste programmes
3. Décocher programmes inutiles
4. Cliquer "Désactiver Sélection"
5. Cliquer "APPLIQUER CHANGEMENTS"
6. Redémarrer PC

RACCOURCI:
- "Désactiver Bloatware" = détecte automatiquement
  les programmes inutiles connus

═══════════════════════════════════════════════════════════════

💡 EN CAS DE PROBLÈME

Programme désactivé par erreur ?

1. Rouvrir Gestionnaire Démarrage
2. Ou: Gestionnaire tâches (Ctrl+Shift+Échap)
3. Onglet "Démarrage"
4. Clic droit programme > Activer
5. Redémarrer

═══════════════════════════════════════════════════════════════

⚠️  PROGRAMMES CRITIQUES

NE JAMAIS désactiver:
- Windows Security / Defender
- Drivers Intel/AMD/NVIDIA/Realtek
- Logiciels requis pour le travail

EN CAS DE DOUTE: Ne pas toucher

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter liste programmes"""
        if not self.programs:
            QMessageBox.warning(self, "⚠️", "Aucun programme à exporter.\nLancez d'abord un scan.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Demarrage_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 80 + "\n")
                f.write("  LISTE PROGRAMMES DÉMARRAGE - WAPINATOR\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 80 + "\n\n")
                
                f.write(f"Total programmes: {len(self.programs)}\n\n")
                
                # Grouper par impact
                for impact_level in ['high', 'medium', 'low']:
                    impact_name = {'high': 'ÉLEVÉ', 'medium': 'MOYEN', 'low': 'FAIBLE'}[impact_level]
                    icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[impact_level]
                    
                    filtered = [p for p in self.programs if p['impact'] == impact_level]
                    
                    if filtered:
                        f.write(f"\n{icon} IMPACT {impact_name} ({len(filtered)} programmes)\n")
                        f.write("─" * 80 + "\n")
                        
                        for program in filtered:
                            f.write(f"\nNom: {program['name']}\n")
                            f.write(f"Chemin: {program['path']}\n")
                            f.write(f"Emplacement: {program['location']}\n")
                            f.write(f"Statut: {'✅ Actif' if program['enabled'] else '❌ Désactivé'}\n")
                            advice = self.get_advice(program)
                            f.write(f"Conseil: {advice}\n")
                
                f.write("\n" + "═" * 80 + "\n")
                f.write("Rapport généré par Wapinator - PC Monitoring Tool\n")
                f.write("═" * 80 + "\n")
            
            reply = QMessageBox.question(
                self,
                "✅ Liste exportée",
                f"Liste sauvegardée:\n{filename.name}\n\nOuvrir le fichier ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(filename)
        
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Impossible d'exporter:\n{str(e)}")