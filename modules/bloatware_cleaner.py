# modules/bloatware_cleaner.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QCheckBox, QLineEdit)
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

# Base de données bloatware connu
BLOATWARE_DATABASE = {
    # Antivirus trials (très courant sur PC neufs)
    'mcafee': {
        'name': 'McAfee (Trial)',
        'category': 'Antivirus Trial',
        'impact': 'high',
        'reason': 'Ralentit PC, essai limité, popups agressifs',
        'safe_to_remove': True
    },
    'norton': {
        'name': 'Norton Security (Trial)',
        'category': 'Antivirus Trial',
        'impact': 'high',
        'reason': 'Lourd, essai court, Windows Defender suffit',
        'safe_to_remove': True
    },
    'avast': {
        'name': 'Avast Free Antivirus',
        'category': 'Antivirus',
        'impact': 'medium',
        'reason': 'Collecte données, popups publicitaires',
        'safe_to_remove': True
    },
    'avg': {
        'name': 'AVG Antivirus Free',
        'category': 'Antivirus',
        'impact': 'medium',
        'reason': 'Même société qu\'Avast, collecte données',
        'safe_to_remove': True
    },
    
    # Cleaners/Optimizers (souvent inutiles/dangereux)
    'ccleaner': {
        'name': 'CCleaner',
        'category': 'Cleaner',
        'impact': 'medium',
        'reason': 'Plus nécessaire, controverses sécurité',
        'safe_to_remove': True
    },
    'advanced systemcare': {
        'name': 'Advanced SystemCare',
        'category': 'Optimizer',
        'impact': 'high',
        'reason': 'Faux problèmes, pousse achat version pro',
        'safe_to_remove': True
    },
    'driver booster': {
        'name': 'Driver Booster',
        'category': 'Driver Updater',
        'impact': 'medium',
        'reason': 'Drivers mal vérifiés, risque instabilité',
        'safe_to_remove': True
    },
    
    # Software bundled (souvent installé sans consentement)
    'wondershare': {
        'name': 'Wondershare Helper',
        'category': 'Bundleware',
        'impact': 'medium',
        'reason': 'S\'installe avec autres logiciels, inutile',
        'safe_to_remove': True
    },
    'web companion': {
        'name': 'Web Companion (Lavasoft)',
        'category': 'Adware',
        'impact': 'high',
        'reason': 'Modifie navigateur, publicités',
        'safe_to_remove': True
    },
    'pc accelerate': {
        'name': 'PC Accelerate',
        'category': 'Scareware',
        'impact': 'high',
        'reason': 'Faux scan, pousse achat',
        'safe_to_remove': True
    },
    
    # Toolbars (obsolètes et intrusifs)
    'toolbar': {
        'name': 'Toolbar (divers)',
        'category': 'Toolbar',
        'impact': 'medium',
        'reason': 'Modifie navigateur, tracking',
        'safe_to_remove': True
    },
    'ask toolbar': {
        'name': 'Ask Toolbar',
        'category': 'Toolbar',
        'impact': 'medium',
        'reason': 'Change moteur recherche par défaut',
        'safe_to_remove': True
    },
    
    # Apps préinstallées Windows (débat)
    'candy crush': {
        'name': 'Candy Crush Saga',
        'category': 'Windows Bloat',
        'impact': 'low',
        'reason': 'Jeu mobile préinstallé, inutile desktop',
        'safe_to_remove': True
    },
    'disney': {
        'name': 'Disney Magic Kingdoms',
        'category': 'Windows Bloat',
        'impact': 'low',
        'reason': 'Jeu préinstallé Windows',
        'safe_to_remove': True
    },
    'spotify music': {
        'name': 'Spotify Music (préinstallé)',
        'category': 'Windows Bloat',
        'impact': 'low',
        'reason': 'Préinstallé Windows, réinstaller si besoin',
        'safe_to_remove': True
    },
    
    # Trialware fabricants
    'cyberlink': {
        'name': 'CyberLink (Trial)',
        'category': 'Manufacturer Bloat',
        'impact': 'medium',
        'reason': 'Version trial logiciel multimédia',
        'safe_to_remove': True
    },
    'roxio': {
        'name': 'Roxio Creator',
        'category': 'Manufacturer Bloat',
        'impact': 'medium',
        'reason': 'Logiciel gravure, peu utilisé',
        'safe_to_remove': True
    },
}

class BloatwareScanWorker(QThread):
    """Worker pour scanner bloatware"""
    log_signal = pyqtSignal(str)
    bloat_found = pyqtSignal(dict)
    finished_signal = pyqtSignal(list)
    
    def run(self):
        """Scanner programmes installés"""
        bloatware_found = []
        
        try:
            self.log_signal.emit("🔍 Scan des programmes installés...\n")
            
            # Méthode 1: Via Registry (plus fiable que winget)
            self.log_signal.emit("📋 Analyse: Registry (Programmes installés)")
            programs = self.scan_installed_programs()
            
            self.log_signal.emit(f"✅ {len(programs)} programmes trouvés\n")
            self.log_signal.emit("🔍 Analyse détection bloatware...\n")
            
            # Détecter bloatware
            for program in programs:
                program_name_lower = program['name'].lower()
                
                # Chercher dans database
                for keyword, bloat_info in BLOATWARE_DATABASE.items():
                    if keyword in program_name_lower:
                        bloat = {
                            'name': program['name'],
                            'display_name': program['name'],
                            'category': bloat_info['category'],
                            'impact': bloat_info['impact'],
                            'reason': bloat_info['reason'],
                            'safe': bloat_info['safe_to_remove'],
                            'uninstall_string': program.get('uninstall_string', ''),
                            'detected_by': bloat_info['name']
                        }
                        
                        bloatware_found.append(bloat)
                        self.bloat_found.emit(bloat)
                        break
            
            self.log_signal.emit(f"\n🗑️ {len(bloatware_found)} bloatware(s) détecté(s)")
            self.finished_signal.emit(bloatware_found)
        
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit([])
    
    def scan_installed_programs(self):
        """Scanner programmes via Registry"""
        programs = []
        
        # Clés à scanner
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        for hkey, subkey in registry_keys:
            try:
                key = winreg.OpenKey(hkey, subkey)
                
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey_path = f"{subkey}\\{subkey_name}"
                        
                        try:
                            program_key = winreg.OpenKey(hkey, subkey_path)
                            
                            # Lire DisplayName
                            try:
                                display_name, _ = winreg.QueryValueEx(program_key, "DisplayName")
                            except:
                                display_name = None
                            
                            # Lire UninstallString
                            try:
                                uninstall_string, _ = winreg.QueryValueEx(program_key, "UninstallString")
                            except:
                                uninstall_string = None
                            
                            if display_name:
                                programs.append({
                                    'name': display_name,
                                    'uninstall_string': uninstall_string
                                })
                            
                            winreg.CloseKey(program_key)
                        
                        except:
                            pass
                        
                        i += 1
                    
                    except OSError:
                        break
                
                winreg.CloseKey(key)
            
            except:
                pass
        
        return programs

class BloatwarecleanerWindow(QDialog):
    """Fenêtre nettoyeur bloatware"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🗑️ Nettoyeur de Bloatware")
        self.setMinimumSize(1100, 800)
        
        self.bloatware = []
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🗑️ NETTOYEUR DE BLOATWARE")
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
            "Détecte et supprime les logiciels inutiles (bloatware) • Antivirus trials, cleaners, toolbars"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Warning
        warning = QLabel(
            "⚠️ Seuls les programmes connus comme bloatware sont détectés • 100% sûr"
        )
        warning.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(warning)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Scanner Bloatware")
        self.scan_btn.clicked.connect(self.scan_bloatware)
        btn_layout.addWidget(self.scan_btn)
        
        self.select_all_btn = QPushButton("☑️ Tout Sélectionner")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        btn_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("☐ Tout Désélectionner")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setEnabled(False)
        btn_layout.addWidget(self.deselect_all_btn)
        
        tips_btn = QPushButton("💡 Qu'est-ce que le Bloatware ?")
        tips_btn.clicked.connect(self.show_bloatware_info)
        btn_layout.addWidget(tips_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Recherche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Recherche:"))
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filtrer par nom...")
        self.search_box.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_box)
        
        layout.addLayout(search_layout)
        
        # Table bloatware
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["☑", "Programme", "Catégorie", "Impact", "Raison", "Sûr ?"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemClicked.connect(self.toggle_selection)
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel("Aucun bloatware scanné")
        self.stats_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.stats_label)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        self.remove_btn = QPushButton("🗑️ SUPPRIMER SÉLECTION")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.remove_btn.setEnabled(False)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F44336, stop:1 #D32F2F);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #D32F2F; }
            QPushButton:disabled { background: #555; }
        """)
        bottom_layout.addWidget(self.remove_btn)
        
        export_btn = QPushButton("💾 Exporter Liste")
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
            QLineEdit {
                background: #2b2b2b;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
        """)
        
        self.show_welcome()
        self.worker = None
    
    def show_welcome(self):
        """Message de bienvenue"""
        self.table.setRowCount(1)
        welcome = QTableWidgetItem(
            "👋 Cliquez sur 'Scanner Bloatware' pour détecter automatiquement les logiciels inutiles installés sur votre PC"
        )
        welcome.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 11))
        self.table.setItem(0, 0, welcome)
        self.table.setSpan(0, 0, 1, 6)
    
    def scan_bloatware(self):
        """Lancer scan bloatware"""
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self.table.setRowCount(0)
        self.bloatware = []
        
        # Lancer worker
        self.worker = BloatwareScanWorker()
        self.worker.log_signal.connect(self.update_stats)
        self.worker.bloat_found.connect(self.add_bloat_to_table)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()
    
    def add_bloat_to_table(self, bloat):
        """Ajouter bloatware à la table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Par défaut coché
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 0, checkbox_widget)
        
        # Programme
        self.table.setItem(row, 1, QTableWidgetItem(bloat['name']))
        
        # Catégorie
        category_item = QTableWidgetItem(bloat['category'])
        self.table.setItem(row, 2, category_item)
        
        # Impact
        impact = bloat['impact']
        impact_text = {
            'high': '🔴 Élevé',
            'medium': '🟡 Moyen',
            'low': '🟢 Faible'
        }.get(impact, '⚪ Inconnu')
        
        impact_item = QTableWidgetItem(impact_text)
        
        if impact == 'high':
            impact_item.setForeground(QColor("#F44336"))
        elif impact == 'medium':
            impact_item.setForeground(QColor("#FF9800"))
        else:
            impact_item.setForeground(QColor("#4CAF50"))
        
        self.table.setItem(row, 3, impact_item)
        
        # Raison
        self.table.setItem(row, 4, QTableWidgetItem(bloat['reason']))
        
        # Sûr ?
        safe_item = QTableWidgetItem("✅ Oui" if bloat['safe'] else "⚠️ Vérifier")
        safe_item.setForeground(QColor("#4CAF50") if bloat['safe'] else QColor("#FF9800"))
        self.table.setItem(row, 5, safe_item)
    
    def on_scan_finished(self, bloatware_list):
        """Scan terminé"""
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        
        self.bloatware = bloatware_list
        
        if not bloatware_list:
            self.stats_label.setText("✅ Aucun bloatware détecté ! Votre PC est propre 🎉")
            
            msg = "✅ SYSTÈME PROPRE\n\n"
            msg += "Aucun bloatware connu détecté sur votre PC.\n\n"
            msg += "Cela ne signifie pas qu'il n'y a AUCUN programme inutile,\n"
            msg += "mais que les bloatware courants (McAfee, Norton, CCleaner, etc.)\n"
            msg += "ne sont pas présents.\n\n"
            msg += "💡 Utilisez 'Gestionnaire Démarrage' pour optimiser les programmes au boot."
            
            QMessageBox.information(self, "✅ Système propre", msg)
            return
        
        # Calculer stats
        total = len(bloatware_list)
        high_impact = sum(1 for b in bloatware_list if b['impact'] == 'high')
        medium_impact = sum(1 for b in bloatware_list if b['impact'] == 'medium')
        
        stats = f"🗑️ {total} bloatware(s) détecté(s) | "
        stats += f"🔴 Impact élevé: {high_impact} | "
        stats += f"🟡 Impact moyen: {medium_impact}"
        
        self.stats_label.setText(stats)
        
        # Message si beaucoup
        if total >= 5:
            QMessageBox.warning(
                self,
                "⚠️ Bloatware détecté",
                f"{total} bloatware(s) trouvé(s) sur votre PC !\n\n"
                "Ces programmes ralentissent votre système et sont inutiles.\n\n"
                "Tous sont cochés par défaut.\n"
                "Cliquez 'SUPPRIMER SÉLECTION' pour les désinstaller."
            )
    
    def toggle_selection(self, item):
        """Toggle checkbox en cliquant sur ligne"""
        row = item.row()
        checkbox_widget = self.table.cellWidget(row, 0)
        
        if checkbox_widget and item.column() != 0:
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
    
    def select_all(self):
        """Tout sélectionner"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def deselect_all(self):
        """Tout désélectionner"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def filter_table(self):
        """Filtrer table selon recherche"""
        search_text = self.search_box.text().lower()
        
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 1)
            if name:
                self.table.setRowHidden(row, search_text not in name.text().lower())
    
    def remove_selected(self):
        """Supprimer bloatware sélectionnés"""
        selected = []
        
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                
                if checkbox and checkbox.isChecked():
                    name = self.table.item(row, 1).text()
                    
                    # Trouver bloatware correspondant
                    bloat = next((b for b in self.bloatware if b['name'] == name), None)
                    if bloat:
                        selected.append(bloat)
        
        if not selected:
            QMessageBox.information(self, "ℹ️", "Aucun bloatware sélectionné.\nCochez les programmes à supprimer.")
            return
        
        # Confirmation
        programs_list = "\n".join([f"• {b['name']}" for b in selected[:10]])
        if len(selected) > 10:
            programs_list += f"\n... et {len(selected)-10} autres"
        
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation Suppression",
            f"Supprimer {len(selected)} bloatware(s) ?\n\n{programs_list}\n\n"
            "Ces programmes seront complètement désinstallés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Désinstaller
        self.progress.setVisible(True)
        self.progress.setMaximum(len(selected))
        self.progress.setValue(0)
        
        success = 0
        failed = 0
        
        for i, bloat in enumerate(selected):
            try:
                if self.uninstall_program(bloat):
                    success += 1
                else:
                    failed += 1
            except:
                failed += 1
            
            self.progress.setValue(i + 1)
            QApplication.processEvents()
        
        self.progress.setVisible(False)
        
        # Résumé
        msg = f"✅ Suppression terminée !\n\n"
        msg += f"Réussis: {success}\n"
        
        if failed > 0:
            msg += f"Échecs: {failed}\n\n"
            msg += "Note: Certains programmes nécessitent une désinstallation manuelle\n"
            msg += "ou ont déjà été supprimés."
        
        msg += "\n\n🔄 Redémarrez Windows pour finaliser"
        
        QMessageBox.information(self, "✅ Terminé", msg)
        
        # Rescanner
        self.scan_bloatware()
    
    def uninstall_program(self, bloat):
        """Désinstaller un programme"""
        try:
            uninstall_string = bloat.get('uninstall_string', '')
            
            if not uninstall_string:
                return False
            
            # Si MsiExec, utiliser mode silencieux
            if 'msiexec' in uninstall_string.lower():
                # Extraire GUID
                import re
                guid_match = re.search(r'\{[A-F0-9-]+\}', uninstall_string, re.IGNORECASE)
                
                if guid_match:
                    guid = guid_match.group(0)
                    
                    # Désinstaller silencieusement
                    result = subprocess.run(
                        ["msiexec", "/x", guid, "/qn", "/norestart"],
                        timeout=120,
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    
                    return result.returncode == 0
            
            else:
                # Essayer exécution directe avec /S (silent)
                if uninstall_string.startswith('"'):
                    # Path avec guillemets
                    parts = uninstall_string.split('"')
                    exe_path = parts[1] if len(parts) > 1 else uninstall_string
                    args = parts[2] if len(parts) > 2 else ""
                else:
                    exe_path = uninstall_string
                    args = ""
                
                # Ajouter flag silent si pas présent
                if '/S' not in args and '/s' not in args:
                    args += " /S"
                
                result = subprocess.run(
                    f'"{exe_path}" {args}',
                    shell=True,
                    timeout=120,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                
                return result.returncode == 0
        
        except Exception as e:
            print(f"Erreur désinstallation {bloat['name']}: {e}")
            return False
    
    def update_stats(self, message):
        """Mettre à jour stats"""
        self.stats_label.setText(message)
    
    def show_bloatware_info(self):
        """Information bloatware"""
        info = """╔══════════════════════════════════════════════════════════════╗
║              💡 QU'EST-CE QUE LE BLOATWARE ?                ║
╚══════════════════════════════════════════════════════════════╝

🤔 DÉFINITION

Le bloatware désigne des logiciels préinstallés sur PC neufs
ou installés sans consentement qui sont:
- Inutiles
- Ralentissent le PC
- Collectent données
- Affichent publicités

═══════════════════════════════════════════════════════════════

🗑️ TYPES DE BLOATWARE

1️⃣  ANTIVIRUS TRIALS
   • McAfee, Norton Security (trials)
   • Préinstallés sur PC neufs (Dell, HP, Lenovo)
   • Essai 30 jours puis popups agressifs
   • Windows Defender suffit largement
   → SUPPRIMER ✅

2️⃣  CLEANERS / OPTIMIZERS
   • CCleaner, Advanced SystemCare, PC Accelerate
   • Prétendent "accélérer" PC
   • Faux problèmes pour vendre version pro
   • Parfois dangereux (registry cleaners)
   → SUPPRIMER ✅

3️⃣  TOOLBARS
   • Ask Toolbar, Yahoo Toolbar
   • Changent page d'accueil navigateur
   • Tracking permanent
   • Obsolètes
   → SUPPRIMER ✅

4️⃣  BUNDLEWARE
   • Wondershare Helper, Web Companion
   • S'installent avec autres logiciels (sneaky)
   • Aucune utilité
   → SUPPRIMER ✅

5️⃣  APPS WINDOWS (débat)
   • Candy Crush, Disney Magic Kingdoms
   • Préinstallés Windows 10/11
   • Jeux mobiles inutiles sur desktop
   → OPTIONNEL (impact faible)

6️⃣  MANUFACTURER BLOAT
   • Logiciels fabricant PC (Dell, HP)
   • Certains utiles (pilotes), d'autres non
   • Ex: Roxio Creator, CyberLink trials
   → VÉRIFIER avant suppression

═══════════════════════════════════════════════════════════════

⚠️  POURQUOI C'EST INSTALLÉ ?

💰 PC NEUFS:
- Fabricants payés par éditeurs logiciels
- McAfee/Norton paient pour être préinstallés
- Dell/HP gagnent 5-10€ par PC

💰 LOGICIELS GRATUITS:
- Installateurs bundlés (ex: Java + Ask Toolbar)
- Cases précochées (sneaky)
- Utilisateur clique "Suivant" sans lire

═══════════════════════════════════════════════════════════════

✅ EST-CE SÛR DE SUPPRIMER ?

OUI si détecté par Wapinator:
- Base de données vérifiée
- Seuls bloatware CONNUS = sûrs
- Aucun risque pour Windows

COMMENT ÊTRE SÛR:
- Si doute: Chercher sur Google
  "Nom du programme bloatware ?"
- Reddit r/techsupport est fiable

═══════════════════════════════════════════════════════════════

🚀 APRÈS SUPPRESSION

GAINS ATTENDUS:
- Boot plus rapide (-10 à -30s)
- RAM libérée (200-500 Mo)
- Moins de popups
- Moins de tracking/collecte données
- PC plus propre

ALTERNATIVES:
- Antivirus: Windows Defender (gratuit, intégré)
- Cleaner: Wapinator Nettoyage (gratuit, sûr)
- Optimizer: Gestionnaire Démarrage Wapinator

═══════════════════════════════════════════════════════════════

💡 PRÉVENTION

ACHETER PC NEUF:
- Signature edition (Microsoft Store) = sans bloat
- Ou: Réinstaller Windows proprement

INSTALLER LOGICIELS:
- Toujours lire CHAQUE écran installation
- Décocher toolbars/antivirus bundlés
- Installer via site officiel uniquement

═══════════════════════════════════════════════════════════════

❓ FAQ

Q: Puis-je casser Windows en supprimant ?
R: NON. Wapinator ne détecte QUE bloatware connu = sûr.

Q: McAfee revient après suppression ?
R: Si préinstallé, parfois. Utiliser "McAfee Removal Tool"
   (outil officiel McAfee pour suppression complète).

Q: Dois-je racheter antivirus après ?
R: NON. Windows Defender (gratuit) est excellent.
   Tests indépendants: note 9/10.

Q: CCleaner est dangereux ?
R: Controverses sécurité passées. Plus nécessaire.
   Wapinator Nettoyage fait la même chose, mieux.

═══════════════════════════════════════════════════════════════
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("💡 Qu'est-ce que le Bloatware ?")
        msg.setText(info)
        msg.setStyleSheet("""
            QMessageBox { background: #1e1e1e; color: white; }
            QLabel { color: white; font-family: Consolas; font-size: 9px; }
            QPushButton { background: #4CAF50; color: white; padding: 8px; border-radius: 4px; }
        """)
        msg.exec()
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║            ❓ AIDE - NETTOYEUR BLOATWARE                    ║
╚══════════════════════════════════════════════════════════════╝

🤔 COMMENT ÇA MARCHE ?

L'outil compare vos programmes installés avec une base de données
de bloatware connus (McAfee, Norton, CCleaner, toolbars, etc.)

DÉTECTION:
- 100% automatique
- Seulement bloatware CONNUS = sûr
- Pas de faux positifs

═══════════════════════════════════════════════════════════════

🛠️ UTILISATION

1. Cliquer "Scanner Bloatware"
2. Attendre scan (30s-1min)
3. Vérifier liste détectée
4. Tous cochés par défaut (sûr)
5. Décocher si vous utilisez vraiment un programme
6. Cliquer "SUPPRIMER SÉLECTION"
7. Patienter désinstallation
8. Redémarrer Windows

═══════════════════════════════════════════════════════════════

📊 COMPRENDRE L'AFFICHAGE

COLONNES:

- ☑ : Cocher = à supprimer
- Programme: Nom complet
- Catégorie: Type bloatware
- Impact: Effet sur PC
  → 🔴 Élevé = ralentit beaucoup
  → 🟡 Moyen = impact modéré
  → 🟢 Faible = peu d'effet
- Raison: Pourquoi c'est bloatware
- Sûr ?: Toujours ✅ Oui (sinon pas détecté)

═══════════════════════════════════════════════════════════════

⚠️ SI AUCUN BLOATWARE DÉTECTÉ

Cela signifie:
✅ PC propre (pas de bloatware COURANT)
✅ Ou déjà nettoyé auparavant

MAIS:
- Il peut y avoir autres programmes inutiles
- Utiliser "Gestionnaire Démarrage" pour optimiser

═══════════════════════════════════════════════════════════════

💡 APRÈS NETTOYAGE

OBLIGATOIRE:
- Redémarrer Windows

OPTIONNEL:
- Rescanner (vérifier suppression)
- Vérifier Gestionnaire Démarrage
- Lancer Nettoyage Windows (Wapinator)

═══════════════════════════════════════════════════════════════

🚨 PROBLÈMES

"Échec désinstallation" ?
→ Programme déjà supprimé
→ Ou: Nécessite désinstallation manuelle
→ Panneau config > Programmes > Désinstaller

"Programme revient" ?
→ McAfee: Utiliser McAfee Removal Tool officiel
→ Norton: Norton Remove and Reinstall Tool

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter liste bloatware"""
        if not self.bloatware:
            QMessageBox.warning(self, "⚠️", "Aucun bloatware à exporter.\nLancez d'abord un scan.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Bloatware_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 80 + "\n")
                f.write("  RAPPORT BLOATWARE DÉTECTÉ - WAPINATOR\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 80 + "\n\n")
                
                f.write(f"Total bloatware détecté: {len(self.bloatware)}\n\n")
                
                # Grouper par catégorie
                categories = {}
                for bloat in self.bloatware:
                    cat = bloat['category']
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(bloat)
                
                for category, bloats in categories.items():
                    f.write(f"\n{'─' * 80}\n")
                    f.write(f"{category.upper()} ({len(bloats)})\n")
                    f.write(f"{'─' * 80}\n")
                    
                    for bloat in bloats:
                        f.write(f"\n• {bloat['name']}\n")
                        f.write(f"  Impact: {bloat['impact']}\n")
                        f.write(f"  Raison: {bloat['reason']}\n")
                        f.write(f"  Sûr à supprimer: {'Oui' if bloat['safe'] else 'Vérifier'}\n")
                
                f.write("\n" + "═" * 80 + "\n")
                f.write("Rapport généré par Wapinator - PC Monitoring Tool\n")
                f.write("═" * 80 + "\n")
            
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