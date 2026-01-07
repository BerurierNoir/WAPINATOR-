# modules/driver_manager.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QTableWidget, 
                            QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import subprocess
import re
import platform
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

class DriverScanWorker(QThread):
    """Worker pour scanner les drivers - VERSION WMI"""
    log_signal = pyqtSignal(str)
    driver_found = pyqtSignal(dict)
    finished_signal = pyqtSignal(list)
    
    def run(self):
        """Scanner tous les drivers système - VERSION WMI (ultra fiable)"""
        drivers = []
        
        try:
            self.log_signal.emit("🔍 Scan des drivers système en cours...\n")
            
            # Méthode WMI - Fonctionne TOUJOURS
            import wmi
            c = wmi.WMI()
            
            # Query tous les drivers système
            driver_count = 0
            for driver in c.Win32_SystemDriver():
                try:
                    driver_count += 1
                    
                    # Extraire infos
                    module_name = driver.Name or "Unknown"
                    display_name = driver.DisplayName or module_name
                    pathname = driver.PathName or ""
                    state = driver.State or "Unknown"
                    
                    # Essayer de trouver la date du fichier
                    driver_date = datetime(2000, 1, 1)
                    date_str = "N/A"
                    
                    # Nettoyer le pathname (enlever \??\ si présent)
                    if pathname:
                        pathname = pathname.replace("\\??\\", "")
                        pathname = pathname.replace("\\SystemRoot\\", "C:\\Windows\\")
                        pathname = pathname.replace("\\System32\\", "C:\\Windows\\System32\\")
                        
                        if os.path.exists(pathname):
                            try:
                                timestamp = os.path.getmtime(pathname)
                                driver_date = datetime.fromtimestamp(timestamp)
                                date_str = driver_date.strftime("%d/%m/%Y")
                            except:
                                pass
                    
                    driver_info = {
                        'name': display_name[:50],
                        'module': module_name,
                        'type': 'Kernel',
                        'date': driver_date,
                        'date_str': date_str,
                        'status': state
                    }
                    
                    drivers.append(driver_info)
                    self.driver_found.emit(driver_info)
                    
                    # Log progress tous les 50 drivers
                    if driver_count % 50 == 0:
                        self.log_signal.emit(f"Scannés: {driver_count} drivers...")
                
                except Exception as e:
                    # Ignorer ce driver et continuer
                    continue
            
            self.log_signal.emit(f"\n✅ {len(drivers)} drivers trouvés")
            self.finished_signal.emit(drivers)
        
        except ImportError:
            self.log_signal.emit("❌ Erreur: Module WMI non disponible")
            self.log_signal.emit("   Le module wmi est requis pour ce scan")
            self.finished_signal.emit([])
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit([])
    
    def parse_driver_date(self, date_str):
        """Parser date driver (format variable) - Gardé pour compatibilité"""
        try:
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    try:
                        return datetime.strptime(date_str, "%d/%m/%Y")
                    except:
                        try:
                            return datetime.strptime(date_str, "%m/%d/%Y")
                        except:
                            pass
            
            if '-' in date_str:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    pass
            
            return datetime(1990, 1, 1)
        
        except:
            return datetime(1990, 1, 1)

class DrivermanagerWindow(QDialog):
    """Fenêtre gestionnaire de drivers"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔧 Gestionnaire de Drivers")
        self.setMinimumSize(1100, 750)
        
        self.drivers = []
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🔧 GESTIONNAIRE DE DRIVERS SYSTÈME")
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
            "Liste tous les drivers système • Identifie drivers obsolètes • Exporte rapport détaillé"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Scanner Drivers")
        self.scan_btn.clicked.connect(self.scan_drivers)
        btn_layout.addWidget(self.scan_btn)
        
        self.filter_old_btn = QPushButton("⏰ Filtrer Obsolètes (>3 ans)")
        self.filter_old_btn.clicked.connect(self.filter_old_drivers)
        self.filter_old_btn.setEnabled(False)
        btn_layout.addWidget(self.filter_old_btn)
        
        self.show_all_btn = QPushButton("📋 Afficher Tous")
        self.show_all_btn.clicked.connect(self.show_all_drivers)
        self.show_all_btn.setEnabled(False)
        btn_layout.addWidget(self.show_all_btn)
        
        tips_btn = QPushButton("💡 Conseils MAJ Drivers")
        tips_btn.clicked.connect(self.show_tips)
        btn_layout.addWidget(tips_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Table drivers
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nom", "Module", "Type", "Date", "⚠️"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel("Aucun driver scanné")
        self.stats_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.stats_label)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Liste")
        export_btn.clicked.connect(self.export_report)
        bottom_layout.addWidget(export_btn)
        
        snappy_btn = QPushButton("🚀 Ouvrir Snappy Driver Installer")
        snappy_btn.clicked.connect(self.open_snappy_guide)
        snappy_btn.setStyleSheet("background: #FF9800;")
        bottom_layout.addWidget(snappy_btn)
        
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
        """)
        
        self.show_welcome()
        self.worker = None
    
    def show_welcome(self):
        """Afficher message de bienvenue dans la table"""
        self.table.setRowCount(1)
        welcome = QTableWidgetItem("👋 Cliquez sur 'Scanner Drivers' pour analyser tous les drivers système")
        welcome.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 11))
        self.table.setItem(0, 0, welcome)
        self.table.setSpan(0, 0, 1, 5)
    
    def update_stats(self, message):
        """Mettre à jour les stats"""
        self.stats_label.setText(message)
    
    def scan_drivers(self):
        """Lancer scan des drivers"""
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        
        self.table.setRowCount(0)
        self.drivers = []
        
        # Lancer worker
        self.worker = DriverScanWorker()
        self.worker.log_signal.connect(self.update_stats)
        self.worker.driver_found.connect(self.add_driver_to_table)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()
    
    def add_driver_to_table(self, driver):
        """Ajouter driver à la table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Nom
        self.table.setItem(row, 0, QTableWidgetItem(driver['name']))
        
        # Module
        self.table.setItem(row, 1, QTableWidgetItem(driver['module']))
        
        # Type
        self.table.setItem(row, 2, QTableWidgetItem(driver['type']))
        
        # Date
        date_item = QTableWidgetItem(driver['date_str'])
        
        # Colorer selon âge
        try:
            age_years = (datetime.now() - driver['date']).days / 365
            
            if age_years > 5:
                date_item.setForeground(QColor("#F44336"))  # Rouge
            elif age_years > 3:
                date_item.setForeground(QColor("#FF9800"))  # Orange
            else:
                date_item.setForeground(QColor("#4CAF50"))  # Vert
        except:
            pass
        
        self.table.setItem(row, 3, date_item)
        
        # Warning si vieux
        warning = ""
        try:
            age_years = (datetime.now() - driver['date']).days / 365
            if age_years > 5:
                warning = "🔴 Très vieux"
            elif age_years > 3:
                warning = "⚠️ Obsolète"
        except:
            pass
        
        self.table.setItem(row, 4, QTableWidgetItem(warning))
    
    def on_scan_finished(self, drivers):
        """Scan terminé"""
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.filter_old_btn.setEnabled(True)
        self.show_all_btn.setEnabled(True)
        
        self.drivers = drivers
        
        if not drivers:
            self.stats_label.setText("❌ Aucun driver trouvé")
            return
        
        # Calculer stats
        total = len(drivers)
        old_drivers = 0
        very_old_drivers = 0
        
        for driver in drivers:
            try:
                age_years = (datetime.now() - driver['date']).days / 365
                if age_years > 5:
                    very_old_drivers += 1
                elif age_years > 3:
                    old_drivers += 1
            except:
                pass
        
        stats = f"📊 Total: {total} drivers | "
        
        if very_old_drivers > 0:
            stats += f"🔴 Très vieux: {very_old_drivers} | "
        
        if old_drivers > 0:
            stats += f"⚠️ Obsolètes: {old_drivers} | "
        
        recent = total - old_drivers - very_old_drivers
        stats += f"✅ Récents: {recent}"
        
        self.stats_label.setText(stats)
        
        # Message si beaucoup de vieux drivers
        if very_old_drivers > 10:
            QMessageBox.warning(
                self,
                "⚠️ Drivers obsolètes détectés",
                f"{very_old_drivers} drivers ont plus de 5 ans.\n\n"
                "Recommandation: Mettre à jour les drivers via Snappy Driver Installer\n"
                "(Bouton '🚀 Ouvrir Snappy Driver Installer')"
            )
    
    def filter_old_drivers(self):
        """Filtrer pour n'afficher que drivers >3 ans"""
        for row in range(self.table.rowCount()):
            date_str = self.table.item(row, 3).text()
            
            # Trouver driver correspondant
            module = self.table.item(row, 1).text()
            driver = next((d for d in self.drivers if d['module'] == module), None)
            
            if driver:
                try:
                    age_years = (datetime.now() - driver['date']).days / 365
                    self.table.setRowHidden(row, age_years <= 3)
                except:
                    self.table.setRowHidden(row, False)
        
        self.stats_label.setText("🔍 Affichage: Drivers obsolètes uniquement (>3 ans)")
    
    def show_all_drivers(self):
        """Afficher tous les drivers"""
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
        
        # Restaurer stats
        self.on_scan_finished(self.drivers)
    
    def show_tips(self):
        """Conseils MAJ drivers"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║          💡 CONSEILS MISE À JOUR DRIVERS                    ║
╚══════════════════════════════════════════════════════════════╝

🎯 POURQUOI METTRE À JOUR LES DRIVERS ?

✅ Amélioration performances (GPU notamment)
✅ Correction bugs et crashs
✅ Support nouveau matériel
✅ Nouvelles fonctionnalités
✅ Compatibilité Windows Update

═══════════════════════════════════════════════════════════════

🚀 MÉTHODE RECOMMANDÉE : SNAPPY DRIVER INSTALLER

AVANTAGES:
- 100% gratuit et open source
- Hors ligne (télécharge base drivers)
- Pas d'arnaque "driver booster" payant
- Mise à jour en masse

UTILISATION:
1. Télécharger depuis sdi-tool.org
2. Choisir version "Full" (tous drivers)
3. Lancer SDI.exe
4. Sélectionner drivers à mettre à jour
5. Installer

⏱️  Durée: 30-60 min (première fois)
💾 Taille: 5-20 Go (base complète)

═══════════════════════════════════════════════════════════════

🎯 DRIVERS PRIORITAIRES À JOUR

1️⃣  CARTE GRAPHIQUE (GPU) ⭐⭐⭐⭐⭐
   • Impact énorme sur performances jeux
   • Nouvelles optimisations chaque mois
   • Sources officielles:
     → NVIDIA: nvidia.com/drivers
     → AMD: amd.com/drivers
     → Intel: intel.com/graphics-drivers

2️⃣  CHIPSET 🔧 ⭐⭐⭐⭐
   • Communication CPU ↔ composants
   • Important pour stabilité
   • Site fabricant carte mère

3️⃣  AUDIO 🔊 ⭐⭐⭐
   • Craquements/bugs audio
   • Realtek (le plus courant)

4️⃣  RÉSEAU (Ethernet/WiFi) 🌐 ⭐⭐⭐
   • Latence gaming
   • Stabilité connexion

5️⃣  USB / SATA / NVMe 💾 ⭐⭐
   • Performances stockage
   • Bugs périphériques USB

═══════════════════════════════════════════════════════════════

⚠️  DRIVERS À NE PAS TOUCHER

❌ Drivers système critiques (ntoskrnl, hal.dll, etc.)
❌ Drivers signés Microsoft (sauf bug avéré)
❌ Si "ça marche bien, touche à rien"

💡 Règle d'or:
- Problème avec X ? → MAJ driver X
- Tout marche bien ? → Pas besoin MAJ

═══════════════════════════════════════════════════════════════

🛡️  SÉCURITÉ MAJ DRIVERS

✅ TOUJOURS créer point de restauration avant
   → Panneau config > Système > Protection système

✅ Télécharger depuis sites officiels uniquement:
   • Fabricant composant (NVIDIA, AMD, Realtek)
   • Fabricant PC (Dell, HP, Lenovo)
   • Windows Update
   • Snappy Driver Installer

❌ JAMAIS via:
   • "Driver Booster" payant (arnaque)
   • Sites russes/chinois louches
   • Torrents
   • Pubs "Votre PC a besoin MAJ drivers"

═══════════════════════════════════════════════════════════════

🔄 ROLLBACK (ANNULER MAJ)

Si problème après MAJ driver:

1. Gestionnaire périphériques (devmgmt.msc)
2. Clic droit sur périphérique
3. Propriétés > Pilote
4. "Restaurer le pilote précédent"

OU

Point de restauration système si créé avant

═══════════════════════════════════════════════════════════════

📅 FRÉQUENCE MAJ

GPU (NVIDIA/AMD):
- Gaming: Tous les mois
- Bureautique: Tous les 3-6 mois

Autres drivers:
- Si problème: Immédiatement
- Si tout marche: 1x par an max

═══════════════════════════════════════════════════════════════

🎮 CAS SPÉCIAL GAMING

DDU (Display Driver Uninstaller):
- Outil pour nettoyer 100% ancien driver GPU
- Utiliser avant MAJ GPU si problèmes
- Télécharger: guru3d.com/ddu

PROCÉDURE:
1. Télécharger nouveau driver GPU (ne pas installer)
2. Lancer DDU en mode sans échec
3. Désinstaller driver actuel (clean)
4. Redémarrer
5. Installer nouveau driver

═══════════════════════════════════════════════════════════════
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("💡 Conseils MAJ Drivers")
        msg.setText(tips)
        msg.setStyleSheet("""
            QMessageBox { background: #1e1e1e; color: white; }
            QLabel { color: white; font-family: Consolas; font-size: 10px; }
            QPushButton { background: #4CAF50; color: white; padding: 8px; border-radius: 4px; }
        """)
        msg.exec()
    
    def open_snappy_guide(self):
        """Guide Snappy Driver Installer"""
        guide = """╔══════════════════════════════════════════════════════════════╗
║        🚀 GUIDE SNAPPY DRIVER INSTALLER (SDI)               ║
╚══════════════════════════════════════════════════════════════╝

📥 TÉLÉCHARGEMENT

Site officiel: https://sdi-tool.org/

2 versions disponibles:

1. SDI LITE (~30 Mo)
   • Télécharge drivers au fur et à mesure
   • Plus long mais moins d'espace disque
   • Nécessite connexion internet

2. SDI FULL (~20 Go)
   • Base complète tous drivers
   • Hors ligne possible
   • Plus rapide
   • ⭐ RECOMMANDÉ si espace disque OK

═══════════════════════════════════════════════════════════════

📋 INSTALLATION

1. Télécharger SDI (Lite ou Full)
2. Extraire ZIP dans dossier (ex: C:\\SDI)
3. Lancer SDI.exe
4. Accepter UAC (administrateur)
5. Première fois: télécharge index drivers (5-10 min)

═══════════════════════════════════════════════════════════════

🎯 UTILISATION

INTERFACE:

┌─────────────────────────────────────────┐
│  [Expert Mode] [Install All]            │
│                                          │
│  ☐ NVIDIA Graphics Driver  [125 MB]     │
│  ☐ Realtek Audio Driver    [50 MB]      │
│  ☑ Chipset Driver           [15 MB]     │
│  ☐ Network Driver           [8 MB]      │
│                                          │
│           [Install Selected]             │
└─────────────────────────────────────────┘

ÉTAPES:

1️⃣  Attendre scan complet (barre verte 100%)

2️⃣  Lire liste drivers disponibles
   • Vert = À jour
   • Rouge = Obsolète (MAJ dispo)

3️⃣  Cocher drivers à installer
   💡 Conseil: Cocher seulement Rouge au début

4️⃣  Cliquer "Install Selected"

5️⃣  Attendre installation (10-30 min)

6️⃣  Redémarrer PC quand demandé

═══════════════════════════════════════════════════════════════

⚙️  OPTIONS RECOMMANDÉES

MODE EXPERT (Expert Mode):
- Activer pour plus d'options
- Voir versions exactes drivers

CRÉER POINT RESTAURATION:
- Cocher "Create restore point"
- Sécurité si problème

TÉLÉCHARGER UNIQUEMENT:
- "Download only" (sans installer)
- Utile pour préparer clé USB

═══════════════════════════════════════════════════════════════

⚠️  DRIVERS À ÉVITER

SDI propose TOUS les drivers, même ceux inutiles:

❌ Pilotes imprimantes si pas d'imprimante
❌ Drivers obsolètes anciens OS
❌ Drivers beta/test (sauf besoin spécifique)

✅ Installer SEULEMENT:
- Matériel présent dans PC
- Version "stable" (pas beta)
- Drivers marqués "recommended"

═══════════════════════════════════════════════════════════════

🔥 DÉPANNAGE

PROBLÈME: "Rien ne s'affiche"
→ Attendre fin scan (5-10 min première fois)
→ Vérifier connexion internet (Lite version)

PROBLÈME: "Installation échoue"
→ Désactiver antivirus temporairement
→ Lancer SDI.exe en administrateur
→ Créer exception antivirus pour SDI

PROBLÈME: "PC plante après MAJ"
→ Redémarrer en mode sans échec
→ Point de restauration système
→ Gestionnaire périph > Restaurer pilote

═══════════════════════════════════════════════════════════════

💾 BACKUP DRIVERS (BONUS)

SDI peut aussi SAUVEGARDER vos drivers actuels:

1. Mode Expert
2. "Backup" tab
3. Sélectionner drivers à sauvegarder
4. Choisir dossier destination
5. "Create backup"

Utile avant réinstall Windows !

═══════════════════════════════════════════════════════════════

🌐 ALTERNATIVES

Si SDI ne marche pas:

- WINDOWS UPDATE (intégré)
  → Paramètres > MAJ Windows > Options avancées
  → "Recevoir MAJ autres produits Microsoft"

- SITE FABRICANT
  → Support.Dell.com (si Dell)
  → Support.HP.com (si HP)
  → etc.

═══════════════════════════════════════════════════════════════

Ouvrir sdi-tool.org maintenant ?
"""
        
        reply = QMessageBox.question(
            self,
            "🚀 Snappy Driver Installer",
            guide + "\n\nOuvrir le site officiel sdi-tool.org ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            import webbrowser
            webbrowser.open("https://sdi-tool.org/")
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║               ❓ AIDE - GESTIONNAIRE DRIVERS                ║
╚══════════════════════════════════════════════════════════════╝

🤔 QU'EST-CE QU'UN DRIVER ?

Un driver (pilote) est un programme qui permet à Windows de
communiquer avec le matériel (carte graphique, audio, etc.)

Sans driver = matériel non fonctionnel ou dégradé

═══════════════════════════════════════════════════════════════

📊 COMPRENDRE L'AFFICHAGE

COLONNES:

- Nom: Nom complet du driver
- Module: Nom fichier système (.sys)
- Type: Kernel (noyau) ou User (utilisateur)
- Date: Date version driver
- ⚠️: Alerte si obsolète

COULEURS DATE:
- 🟢 Vert: < 3 ans (récent)
- 🟠 Orange: 3-5 ans (vieux)
- 🔴 Rouge: > 5 ans (très vieux)

═══════════════════════════════════════════════════════════════

🎯 QUAND METTRE À JOUR ?

✅ TOUJOURS MAJ si:
- Crashes/BSOD fréquents
- Périphérique ne marche pas
- Performances dégradées
- Message "driver obsolète"

⚠️ PARFOIS MAJ si:
- Nouveau jeu ne marche pas bien (GPU)
- Bugs audio (craquements)
- Problèmes WiFi/Ethernet

❌ PAS BESOIN MAJ si:
- Tout fonctionne parfaitement
- Drivers < 2 ans
- PC stable

═══════════════════════════════════════════════════════════════

🛠️ UTILISATION OUTIL

1. Cliquer "Scanner Drivers"
2. Attendre fin scan (30s-1min)
3. Analyser liste (rouge = vieux)
4. Filtrer obsolètes si besoin
5. Noter drivers à MAJ
6. Utiliser Snappy Driver Installer pour MAJ

═══════════════════════════════════════════════════════════════

💡 DRIVERS LES PLUS IMPORTANTS

GPU (Carte graphique): ⭐⭐⭐⭐⭐
→ Impact direct FPS gaming

Chipset: ⭐⭐⭐⭐
→ Stabilité générale PC

Audio: ⭐⭐⭐
→ Qualité son / bugs

Réseau: ⭐⭐⭐
→ Latence / stabilité connexion

USB: ⭐⭐
→ Périphériques USB

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter liste drivers"""
        if not self.drivers:
            QMessageBox.warning(self, "⚠️", "Aucun driver à exporter.\nLancez d'abord un scan.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Drivers_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 80 + "\n")
                f.write("  LISTE DRIVERS SYSTÈME - WAPINATOR\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 80 + "\n\n")
                
                f.write(f"Total drivers: {len(self.drivers)}\n\n")
                
                # Trier par date (plus vieux en premier)
                sorted_drivers = sorted(self.drivers, key=lambda d: d['date'])
                
                for driver in sorted_drivers:
                    age_years = (datetime.now() - driver['date']).days / 365
                    
                    f.write(f"{'─' * 80}\n")
                    f.write(f"Nom: {driver['name']}\n")
                    f.write(f"Module: {driver['module']}\n")
                    f.write(f"Type: {driver['type']}\n")
                    f.write(f"Date: {driver['date_str']} ({age_years:.1f} ans)\n")
                    
                    if age_years > 5:
                        f.write(f"Statut: 🔴 TRÈS VIEUX (> 5 ans)\n")
                    elif age_years > 3:
                        f.write(f"Statut: ⚠️ OBSOLÈTE (3-5 ans)\n")
                    else:
                        f.write(f"Statut: ✅ Récent (< 3 ans)\n")
                    
                    f.write("\n")
                
                f.write("═" * 80 + "\n")
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