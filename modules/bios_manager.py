# modules/bios_manager.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QGroupBox, QScrollArea, 
                            QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
                            QHeaderView, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import subprocess
import platform
import webbrowser
from datetime import datetime

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

# Base de données des fabricants et leurs outils
BIOS_MANUFACTURERS = {
    'asus': {
        'name': 'ASUS',
        'tools': ['EZ Flash', 'ASUS Update Utility'],
        'download_url': 'https://www.asus.com/support/',
        'color': '#FF6600'
    },
    'msi': {
        'name': 'MSI',
        'tools': ['M-Flash', 'Live Update'],
        'download_url': 'https://www.msi.com/support',
        'color': '#E74C3C'
    },
    'gigabyte': {
        'name': 'Gigabyte',
        'tools': ['Q-Flash', '@BIOS'],
        'download_url': 'https://www.gigabyte.com/Support',
        'color': '#FF9800'
    },
    'asrock': {
        'name': 'ASRock',
        'tools': ['Instant Flash', 'ASRock Live Update'],
        'download_url': 'https://www.asrock.com/support/',
        'color': '#2196F3'
    },
    'dell': {
        'name': 'Dell',
        'tools': ['Dell BIOS Update', 'SupportAssist'],
        'download_url': 'https://www.dell.com/support',
        'color': '#0084FF'
    },
    'hp': {
        'name': 'HP',
        'tools': ['HP BIOS Update', 'HP Support Assistant'],
        'download_url': 'https://support.hp.com',
        'color': '#0096D6'
    },
    'lenovo': {
        'name': 'Lenovo',
        'tools': ['Lenovo System Update', 'BIOS Update Utility'],
        'download_url': 'https://support.lenovo.com',
        'color': '#E2231A'
    },
    'generic': {
        'name': 'Generic',
        'tools': ['USB Flash Method'],
        'download_url': '',
        'color': '#9E9E9E'
    }
}

# Explications des paramètres BIOS courants
BIOS_SETTINGS = {
    'boot': {
        'name': '🔄 Boot Order / Ordre de Démarrage',
        'description': 'Définit l\'ordre dans lequel le PC cherche un système d\'exploitation',
        'common_options': [
            ('Windows Boot Manager', 'Démarre Windows (recommandé en premier)'),
            ('USB/Removable', 'Clé USB ou disque externe'),
            ('CD/DVD Drive', 'Lecteur optique'),
            ('Network Boot', 'Démarrage réseau (PXE)')
        ],
        'recommendation': '💡 Mettez Windows Boot Manager en premier pour démarrage rapide',
        'danger_level': 'low'
    },
    'secure_boot': {
        'name': '🔒 Secure Boot',
        'description': 'Sécurité qui vérifie l\'authenticité du système d\'exploitation au démarrage',
        'common_options': [
            ('Enabled', 'Activé - Sécurité maximale (requis Windows 11)'),
            ('Disabled', 'Désactivé - Compatible dual boot Linux')
        ],
        'recommendation': '💡 Laissez Activé sauf si vous installez Linux en dual boot',
        'danger_level': 'medium'
    },
    'xmp_docp': {
        'name': '⚡ XMP / DOCP (RAM Overclocking)',
        'description': 'Active le profil overclock de votre RAM pour atteindre sa fréquence annoncée',
        'common_options': [
            ('Disabled', 'Désactivé - RAM tourne à 2133MHz (par défaut)'),
            ('Profile 1', 'Activé - RAM atteint sa vitesse annoncée (ex: 3200MHz)')
        ],
        'recommendation': '💡 ACTIVEZ-LE ! Sinon votre RAM ne tourne pas à sa vitesse max',
        'danger_level': 'low'
    },
    'virtualization': {
        'name': '🖥️ Virtualization (VT-x / AMD-V)',
        'description': 'Active la virtualisation matérielle pour machines virtuelles et émulateurs',
        'common_options': [
            ('Enabled', 'Activé - Permet VirtualBox, VMware, WSL2, Hyper-V'),
            ('Disabled', 'Désactivé - VMs ne fonctionnent pas')
        ],
        'recommendation': '💡 Activez si vous utilisez VirtualBox, WSL2, Docker, ou émulateurs',
        'danger_level': 'low'
    },
    'tpm': {
        'name': '🔐 TPM 2.0 (Trusted Platform Module)',
        'description': 'Puce de sécurité pour chiffrement et authentification',
        'common_options': [
            ('Enabled', 'Activé - OBLIGATOIRE pour Windows 11'),
            ('Disabled', 'Désactivé - Windows 11 ne s\'installera pas')
        ],
        'recommendation': '💡 DOIT être activé pour Windows 11',
        'danger_level': 'medium'
    },
    'fast_boot': {
        'name': '⚡ Fast Boot',
        'description': 'Accélère le démarrage en sautant certains tests matériels',
        'common_options': [
            ('Enabled', 'Activé - Démarrage ultra rapide'),
            ('Disabled', 'Désactivé - Plus lent mais meilleure compatibilité')
        ],
        'recommendation': '💡 Activé pour gain de temps. Désactivez si problèmes démarrage',
        'danger_level': 'low'
    },
    'ahci_raid': {
        'name': '💾 SATA Mode (AHCI / RAID / IDE)',
        'description': 'Mode de fonctionnement des disques SATA',
        'common_options': [
            ('AHCI', 'Mode moderne - Recommandé pour SSD/HDD (TRIM supporté)'),
            ('RAID', 'Pour configuration RAID multiple disques'),
            ('IDE', 'Mode ancien - Compatibilité vieux OS')
        ],
        'recommendation': '💡 AHCI pour utilisation normale. RAID seulement si configuré.',
        'danger_level': 'high'
    },
    'csm': {
        'name': '🔄 CSM (Compatibility Support Module)',
        'description': 'Émule le BIOS Legacy pour compatibilité anciens OS',
        'common_options': [
            ('Disabled', 'Désactivé - Mode UEFI pur (recommandé)'),
            ('Enabled', 'Activé - Compatibilité BIOS Legacy')
        ],
        'recommendation': '💡 Désactivé pour Windows 10/11 UEFI',
        'danger_level': 'medium'
    },
    'resizable_bar': {
        'name': '📊 Resizable BAR / SAM',
        'description': 'Améliore performances GPU en donnant accès direct à toute la VRAM',
        'common_options': [
            ('Enabled', 'Activé - +5-15% FPS dans certains jeux'),
            ('Disabled', 'Désactivé')
        ],
        'recommendation': '💡 Activez si GPU récent (RTX 3000+, RX 6000+)',
        'danger_level': 'low'
    },
    'pcie_gen': {
        'name': '🚀 PCIe Generation',
        'description': 'Version du bus PCIe (Gen 3, Gen 4, Gen 5)',
        'common_options': [
            ('Auto', 'Automatique - Détecte la meilleure version'),
            ('Gen 4', 'Force PCIe 4.0'),
            ('Gen 3', 'Force PCIe 3.0')
        ],
        'recommendation': '💡 Laissez sur Auto',
        'danger_level': 'low'
    }
}


class BiosInfoWorker(QThread):
    """Worker pour récupérer les infos BIOS"""
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        bios_info = self.get_bios_info()
        self.finished_signal.emit(bios_info)
    
    def get_bios_info(self):
        """Récupère les informations BIOS via WMI et commandes système"""
        info = {
            'manufacturer': 'Unknown',
            'version': 'Unknown',
            'date': 'Unknown',
            'motherboard': 'Unknown',
            'mode': 'Unknown',
            'secure_boot': 'Unknown'
        }
        
        try:
            # Essayer avec WMI
            import wmi
            c = wmi.WMI()
            
            # Infos BIOS
            for bios in c.Win32_BIOS():
                info['manufacturer'] = bios.Manufacturer or 'Unknown'
                info['version'] = bios.SMBIOSBIOSVersion or 'Unknown'
                info['date'] = bios.ReleaseDate[:8] if bios.ReleaseDate else 'Unknown'
            
            # Infos Carte mère
            for board in c.Win32_BaseBoard():
                info['motherboard'] = f"{board.Manufacturer} {board.Product}"
        
        except ImportError:
            # Fallback sans WMI
            pass
        
        # Mode UEFI/Legacy
        try:
            result = subprocess.run(
                ['powershell', '-Command', '$env:firmware_type'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            # Alternative : vérifier existence dossier UEFI
            import os
            if os.path.exists('C:\\Windows\\Panther\\setupact.log'):
                info['mode'] = 'UEFI'
            else:
                info['mode'] = 'Legacy BIOS'
        except:
            info['mode'] = 'Unknown'
        
        # Secure Boot status
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Confirm-SecureBootUEFI'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if 'True' in result.stdout:
                info['secure_boot'] = 'Enabled ✅'
            else:
                info['secure_boot'] = 'Disabled ❌'
        except:
            info['secure_boot'] = 'N/A (Legacy BIOS)'
        
        # Détection fabricant carte mère
        info['detected_manufacturer'] = self.detect_manufacturer(info['motherboard'])
        
        return info
    
    def detect_manufacturer(self, motherboard_name):
        """Détecte le fabricant depuis le nom de la carte mère"""
        motherboard_lower = motherboard_name.lower()
        
        for key, data in BIOS_MANUFACTURERS.items():
            if data['name'].lower() in motherboard_lower:
                return key
        
        return 'generic'


class BiosmanagerWindow(QDialog):
    """Fenêtre principale du BIOS Manager"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("⚙️ BIOS/UEFI Manager")
        self.setMinimumSize(1100, 800)
        
        self.bios_info = {}
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # En-tête
        self.create_header(main_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Informations
        self.info_tab = QWidget()
        self.create_info_tab()
        self.tabs.addTab(self.info_tab, "📊 Informations")
        
        # Tab 2: Mise à jour
        self.update_tab = QWidget()
        self.create_update_tab()
        self.tabs.addTab(self.update_tab, "🔄 Mise à Jour")
        
        # Tab 3: Tutoriels
        self.tutorial_tab = QWidget()
        self.create_tutorial_tab()
        self.tabs.addTab(self.tutorial_tab, "📚 Tutoriels")
        
        # Tab 4: Paramètres BIOS
        self.settings_tab = QWidget()
        self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "🎓 Paramètres BIOS")
        
        main_layout.addWidget(self.tabs)
        
        # Boutons
        self.create_action_buttons(main_layout)
        
        self.setLayout(main_layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: white;
            }
            QTabWidget::pane {
                border: 2px solid #444;
                background: #2b2b2b;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #3a3a3a;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
            }
            QTabBar::tab:hover {
                background: #555;
            }
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #4CAF50;
            }
            QLabel {
                color: white;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #444;
                color: white;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton {
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                transform: scale(1.05);
            }
            QTableWidget {
                background-color: #2b2b2b;
                border: 1px solid #444;
                gridline-color: #444;
                color: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Scanner au démarrage
        self.scan_bios()
    
    def create_header(self, layout):
        """Crée l'en-tête"""
        header = QLabel("⚙️ BIOS/UEFI MANAGER")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Gérez votre BIOS en toute sécurité")
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Avertissement
        warning = QLabel("⚠️ ATTENTION: Mise à jour BIOS = Risque si mal faite | Ne JAMAIS éteindre pendant MAJ")
        warning.setStyleSheet("""
            background: #F44336;
            color: white;
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 10px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
    
    def create_info_tab(self):
        """Tab informations BIOS"""
        layout = QVBoxLayout()
        
        # Groupe infos principales
        info_group = QGroupBox("📊 INFORMATIONS BIOS/UEFI ACTUELLES")
        info_layout = QVBoxLayout()
        
        # Labels pour afficher les infos
        self.manufacturer_label = QLabel("Fabricant: Détection en cours...")
        self.version_label = QLabel("Version: Détection en cours...")
        self.date_label = QLabel("Date: Détection en cours...")
        self.motherboard_label = QLabel("Carte mère: Détection en cours...")
        self.mode_label = QLabel("Mode: Détection en cours...")
        self.secureboot_label = QLabel("Secure Boot: Détection en cours...")
        
        for label in [self.manufacturer_label, self.version_label, self.date_label,
                     self.motherboard_label, self.mode_label, self.secureboot_label]:
            label.setFont(QFont("Segoe UI", 11))
            label.setStyleSheet("padding: 5px; background: #1a1a1a; border-radius: 3px; margin: 2px;")
            info_layout.addWidget(label)
        
        # Bouton rescan
        rescan_btn = QPushButton("🔄 Re-scanner")
        rescan_btn.clicked.connect(self.scan_bios)
        rescan_btn.setStyleSheet("background: #2196F3; color: white; margin-top: 10px;")
        info_layout.addWidget(rescan_btn)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Groupe Windows version
        win_group = QGroupBox("🪟 INFORMATIONS SYSTÈME")
        win_layout = QVBoxLayout()
        
        win_ver = platform.platform()
        win_label = QLabel(f"Windows: {win_ver}")
        win_label.setStyleSheet("padding: 5px; background: #1a1a1a; border-radius: 3px;")
        win_layout.addWidget(win_label)
        
        win_group.setLayout(win_layout)
        layout.addWidget(win_group)
        
        layout.addStretch()
        self.info_tab.setLayout(layout)
    
    def create_update_tab(self):
        """Tab mise à jour BIOS"""
        layout = QVBoxLayout()
        
        # Groupe sélection fabricant
        manufacturer_group = QGroupBox("🏭 SÉLECTIONNEZ VOTRE FABRICANT")
        manufacturer_layout = QVBoxLayout()
        
        self.manufacturer_combo = QComboBox()
        for key, data in BIOS_MANUFACTURERS.items():
            self.manufacturer_combo.addItem(f"{data['name']}", key)
        self.manufacturer_combo.currentIndexChanged.connect(self.on_manufacturer_changed)
        self.manufacturer_combo.setStyleSheet("""
            QComboBox {
                background: #3a3a3a;
                color: white;
                padding: 10px;
                border: 2px solid #444;
                border-radius: 5px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #3a3a3a;
                color: white;
                selection-background-color: #4CAF50;
            }
        """)
        manufacturer_layout.addWidget(self.manufacturer_combo)
        
        manufacturer_group.setLayout(manufacturer_layout)
        layout.addWidget(manufacturer_group)
        
        # Groupe outils disponibles
        tools_group = QGroupBox("🛠️ OUTILS DE MISE À JOUR")
        tools_layout = QVBoxLayout()
        
        self.tools_text = QTextEdit()
        self.tools_text.setReadOnly(True)
        self.tools_text.setMaximumHeight(150)
        tools_layout.addWidget(self.tools_text)
        
        download_btn = QPushButton("🌐 Ouvrir Page Téléchargement Officielle")
        download_btn.clicked.connect(self.open_download_page)
        download_btn.setStyleSheet("background: #4CAF50; color: white;")
        tools_layout.addWidget(download_btn)
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)
        
        # Checklist avant MAJ
        checklist_group = QGroupBox("✅ CHECKLIST AVANT MISE À JOUR")
        checklist_layout = QVBoxLayout()
        
        checklist_text = QTextEdit()
        checklist_text.setReadOnly(True)
        checklist_text.setHtml("""
        <h3 style="color: #F44336;">⚠️ CRITIQUES - OBLIGATOIRES</h3>
        <ul>
            <li><b>✅ Batterie Laptop > 50%</b> (ou branché sur secteur)</li>
            <li><b>✅ PC Fixe sur onduleur/parasurtenseur</b> (éviter coupure courant)</li>
            <li><b>✅ Télécharger BIOS depuis site OFFICIEL constructeur</b></li>
            <li><b>✅ Vérifier modèle EXACT carte mère</b> (BIOS incorrect = brick)</li>
            <li><b>✅ Lire le changelog</b> (savoir ce qui change)</li>
        </ul>
        
        <h3 style="color: #FF9800;">💡 RECOMMANDÉS</h3>
        <ul>
            <li>📸 Prendre photos paramètres BIOS actuels</li>
            <li>💾 Sauvegarder données importantes</li>
            <li>🔄 Point de restauration Windows</li>
            <li>📝 Noter paramètres custom (XMP, boot order, etc.)</li>
        </ul>
        
        <h3 style="color: #4CAF50;">🚀 PENDANT LA MISE À JOUR</h3>
        <ul>
            <li><b>❌ NE PAS ÉTEINDRE LE PC</b></li>
            <li><b>❌ NE PAS RETIRER L'ALIMENTATION</b></li>
            <li><b>❌ NE PAS APPUYER SUR DES TOUCHES</b></li>
            <li>⏱️ Patience : 5-15 minutes normal</li>
            <li>🔄 PC redémarre plusieurs fois = NORMAL</li>
        </ul>
        """)
        checklist_layout.addWidget(checklist_text)
        
        checklist_group.setLayout(checklist_layout)
        layout.addWidget(checklist_group)
        
        self.update_tab.setLayout(layout)
        
        # Charger infos fabricant auto-détecté
        self.on_manufacturer_changed()
    
    def create_tutorial_tab(self):
        """Tab tutoriels"""
        layout = QVBoxLayout()
        
        # Sélecteur de fabricant pour tutoriel
        fab_layout = QHBoxLayout()
        fab_label = QLabel("Sélectionnez votre fabricant:")
        self.tutorial_combo = QComboBox()
        for key, data in BIOS_MANUFACTURERS.items():
            self.tutorial_combo.addItem(f"{data['name']}", key)
        self.tutorial_combo.currentIndexChanged.connect(self.load_tutorial)
        self.tutorial_combo.setStyleSheet("""
            QComboBox {
                background: #3a3a3a;
                color: white;
                padding: 8px;
                border: 2px solid #444;
                border-radius: 5px;
            }
        """)
        fab_layout.addWidget(fab_label)
        fab_layout.addWidget(self.tutorial_combo)
        layout.addLayout(fab_layout)
        
        # Zone de texte pour le tutoriel
        self.tutorial_text = QTextEdit()
        self.tutorial_text.setReadOnly(True)
        layout.addWidget(self.tutorial_text)
        
        self.tutorial_tab.setLayout(layout)
        
        # Charger tutoriel par défaut
        self.load_tutorial()
    
    def create_settings_tab(self):
        """Tab explications paramètres BIOS"""
        layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Créer un groupe pour chaque paramètre
        for setting_id, setting_data in BIOS_SETTINGS.items():
            self.create_setting_group(scroll_layout, setting_id, setting_data)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.settings_tab.setLayout(layout)
    
    def create_setting_group(self, layout, setting_id, setting_data):
        """Crée un groupe pour un paramètre BIOS"""
        # Couleur selon danger
        colors = {
            'low': '#4CAF50',
            'medium': '#FF9800',
            'high': '#F44336'
        }
        color = colors.get(setting_data.get('danger_level', 'low'), '#4CAF50')
        
        group = QGroupBox(setting_data['name'])
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: #2b2b2b;
                border: 2px solid {color};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 11px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {color};
            }}
        """)
        
        group_layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel(setting_data['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #ccc; font-size: 10px; padding: 5px;")
        group_layout.addWidget(desc_label)
        
        # Options courantes
        if setting_data.get('common_options'):
            options_label = QLabel("<b>Options courantes:</b>")
            options_label.setStyleSheet("color: white; margin-top: 10px;")
            group_layout.addWidget(options_label)
            
            for option, explanation in setting_data['common_options']:
                option_label = QLabel(f"  • <b>{option}</b>: {explanation}")
                option_label.setWordWrap(True)
                option_label.setStyleSheet("color: #bbb; font-size: 10px; padding-left: 15px;")
                group_layout.addWidget(option_label)
        
        # Recommandation
        rec_label = QLabel(setting_data['recommendation'])
        rec_label.setWordWrap(True)
        rec_label.setStyleSheet(f"""
            background: {color}40;
            color: white;
            padding: 8px;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        """)
        group_layout.addWidget(rec_label)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def create_action_buttons(self, layout):
        """Boutons d'action"""
        button_layout = QHBoxLayout()
        
        # Bouton guide complet
        guide_btn = QPushButton("📖 Guide Complet BIOS")
        guide_btn.clicked.connect(self.show_complete_guide)
        guide_btn.setStyleSheet("background: #9C27B0; color: white;")
        button_layout.addWidget(guide_btn)
        
        # Bouton fermer
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: #F44336; color: white;")
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def scan_bios(self):
        """Lance le scan des infos BIOS"""
        self.manufacturer_label.setText("🔄 Scan en cours...")
        
        # Démarrer le worker
        self.bios_worker = BiosInfoWorker()
        self.bios_worker.finished_signal.connect(self.on_bios_scanned)
        self.bios_worker.start()
    
    def on_bios_scanned(self, info):
        """Callback quand le scan est terminé"""
        self.bios_info = info
        
        # Afficher les infos
        self.manufacturer_label.setText(f"🏭 Fabricant BIOS: {info['manufacturer']}")
        self.version_label.setText(f"📌 Version: {info['version']}")
        
        # Formater la date si possible
        try:
            date_str = info['date']
            if len(date_str) == 8:
                formatted_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]}"
                self.date_label.setText(f"📅 Date: {formatted_date}")
            else:
                self.date_label.setText(f"📅 Date: {date_str}")
        except:
            self.date_label.setText(f"📅 Date: {info['date']}")
        
        self.motherboard_label.setText(f"🔧 Carte mère: {info['motherboard']}")
        
        # Mode avec couleur
        mode_color = "#4CAF50" if info['mode'] == "UEFI" else "#FF9800"
        self.mode_label.setText(f"⚙️ Mode: {info['mode']}")
        self.mode_label.setStyleSheet(f"padding: 5px; background: {mode_color}40; border-radius: 3px; margin: 2px; font-weight: bold;")
        
        self.secureboot_label.setText(f"🔒 Secure Boot: {info['secure_boot']}")
        
        # Sélectionner le fabricant auto-détecté
        detected_manu = info.get('detected_manufacturer', 'generic')
        for i in range(self.manufacturer_combo.count()):
            if self.manufacturer_combo.itemData(i) == detected_manu:
                self.manufacturer_combo.setCurrentIndex(i)
                break
    
    def on_manufacturer_changed(self):
        """Quand le fabricant change"""
        manufacturer_key = self.manufacturer_combo.currentData()
        manufacturer = BIOS_MANUFACTURERS[manufacturer_key]
        
        # Mettre à jour les outils
        tools_html = f"<h3 style='color: {manufacturer['color']};'>{manufacturer['name']}</h3>"
        tools_html += "<p><b>Outils disponibles:</b></p><ul>"
        
        for tool in manufacturer['tools']:
            tools_html += f"<li>{tool}</li>"
        
        tools_html += "</ul>"
        tools_html += "<p><i>Utilisez l'outil fourni par votre fabricant pour mise à jour sécurisée.</i></p>"
        
        self.tools_text.setHtml(tools_html)
    
    def open_download_page(self):
        """Ouvre la page de téléchargement du fabricant"""
        manufacturer_key = self.manufacturer_combo.currentData()
        manufacturer = BIOS_MANUFACTURERS[manufacturer_key]
        
        if manufacturer['download_url']:
            webbrowser.open(manufacturer['download_url'])
            QMessageBox.information(
                self,
                "🌐 Page Ouverte",
                f"La page de support {manufacturer['name']} a été ouverte dans votre navigateur.\n\n"
                f"Recherchez votre modèle exact de carte mère pour télécharger le BIOS."
            )
        else:
            QMessageBox.warning(
                self,
                "⚠️ Fabricant Générique",
                "Veuillez rechercher le site de support de votre fabricant manuellement."
            )
    
    def load_tutorial(self):
        """Charge le tutoriel pour le fabricant sélectionné"""
        manufacturer_key = self.tutorial_combo.currentData()
        manufacturer = BIOS_MANUFACTURERS[manufacturer_key]
        
        # Tutoriel générique par fabricant
        tutorials = {
            'asus': self.get_asus_tutorial(),
            'msi': self.get_msi_tutorial(),
            'gigabyte': self.get_gigabyte_tutorial(),
            'asrock': self.get_asrock_tutorial(),
            'dell': self.get_dell_tutorial(),
            'hp': self.get_hp_tutorial(),
            'lenovo': self.get_lenovo_tutorial(),
            'generic': self.get_generic_tutorial()
        }
        
        tutorial_html = tutorials.get(manufacturer_key, self.get_generic_tutorial())
        self.tutorial_text.setHtml(tutorial_html)
    
    def get_asus_tutorial(self):
        return """
        <h2 style="color: #FF6600;">📚 TUTORIEL MISE À JOUR BIOS ASUS</h2>
        
        <h3>Méthode 1: EZ Flash (Dans le BIOS) - RECOMMANDÉE</h3>
        <ol>
            <li>Téléchargez le BIOS depuis <b>support.asus.com</b></li>
            <li>Extrayez le fichier .CAP sur une <b>clé USB (FAT32)</b></li>
            <li>Redémarrez et appuyez sur <b>DEL</b> ou <b>F2</b> au démarrage</li>
            <li>Appuyez sur <b>F7</b> pour passer en mode avancé</li>
            <li>Allez dans <b>Tool → ASUS EZ Flash 3 Utility</b></li>
            <li>Sélectionnez votre clé USB et le fichier BIOS</li>
            <li>Confirmez et <b>ATTENDEZ</b> (5-10 min, ne rien toucher!)</li>
            <li>Le PC redémarre automatiquement</li>
        </ol>
        
        <h3>Méthode 2: USB BIOS Flashback</h3>
        <p><i>(Si carte mère récente avec bouton dédié au dos)</i></p>
        <ol>
            <li>Renommez le fichier BIOS exactement comme indiqué sur site ASUS</li>
            <li>Copiez sur clé USB (FAT32) dans racine</li>
            <li>PC <b>ÉTEINT</b>, branchez USB sur port Flashback</li>
            <li>Appuyez 3 secondes sur bouton Flashback</li>
            <li>LED clignote = mise à jour en cours (3-5 min)</li>
            <li>LED fixe = terminé, retirez USB et démarrez</li>
        </ol>
        
        <p style="background: #F44336; color: white; padding: 10px; border-radius: 5px;">
        <b>⚠️ IMPORTANT ASUS:</b><br>
        - Après MAJ, BIOS reset aux valeurs par défaut<br>
        - Réactivez XMP, boot order, etc.<br>
        - Si PC ne boot pas : Clear CMOS (jumper ou pile 30 sec)
        </p>
        """
    
    def get_msi_tutorial(self):
        return """
        <h2 style="color: #E74C3C;">📚 TUTORIEL MISE À JOUR BIOS MSI</h2>
        
        <h3>Méthode 1: M-Flash (Dans le BIOS) - RECOMMANDÉE</h3>
        <ol>
            <li>Téléchargez le BIOS depuis <b>msi.com/support</b></li>
            <li>Extrayez le fichier (souvent .zip avec plusieurs fichiers)</li>
            <li>Copiez TOUT le contenu sur <b>clé USB (FAT32)</b></li>
            <li>Redémarrez et appuyez sur <b>DEL</b> au démarrage</li>
            <li>Appuyez sur <b>F7</b> pour mode avancé</li>
            <li>Allez dans <b>M-Flash</b> (souvent touche F6)</li>
            <li>Sélectionnez le fichier BIOS</li>
            <li>Confirmez et <b>ATTENDEZ</b> sans rien toucher</li>
            <li>Le PC redémarre tout seul</li>
        </ol>
        
        <h3>Méthode 2: Flash BIOS Button</h3>
        <p><i>(Cartes mères récentes uniquement)</i></p>
        <ol>
            <li>Renommez le fichier comme indiqué (ex: MSI.ROM)</li>
            <li>Placez sur clé USB FAT32, racine</li>
            <li>PC éteint, branchez sur port Flash BIOS</li>
            <li>Appuyez sur bouton Flash BIOS (3-5 sec)</li>
            <li>LED rouge clignote = en cours</li>
            <li>LED éteinte = terminé</li>
        </ol>
        
        <p style="background: #FF9800; color: white; padding: 10px; border-radius: 5px;">
        <b>💡 ASTUCE MSI:</b><br>
        - Certains BIOS MSI ont 2 fichiers : un .ROM et un .TXT<br>
        - Copiez les DEUX sur la clé USB<br>
        - Ne renommez rien si pas demandé explicitement
        </p>
        """
    
    def get_gigabyte_tutorial(self):
        return """
        <h2 style="color: #FF9800;">📚 TUTORIEL MISE À JOUR BIOS GIGABYTE</h2>
        
        <h3>Méthode: Q-Flash (Dans le BIOS)</h3>
        <ol>
            <li>Téléchargez le BIOS depuis <b>gigabyte.com/Support</b></li>
            <li>Extrayez le fichier (souvent extension .F## comme F7, F12)</li>
            <li>Copiez sur <b>clé USB FAT32</b></li>
            <li>Redémarrez et appuyez sur <b>DEL</b> au démarrage</li>
            <li>Appuyez sur <b>F8</b> pour lancer Q-Flash</li>
            <li>Sélectionnez <b>Update BIOS</b></li>
            <li>Choisissez votre fichier BIOS</li>
            <li>Confirmez et <b>PATIENCE</b> (peut être long)</li>
            <li>Message "Update Complete" → Redémarrage auto</li>
        </ol>
        
        <h3>Alternative: Q-Flash Plus</h3>
        <p><i>(Bouton au dos de la carte mère)</i></p>
        <ol>
            <li>Renommez le fichier BIOS en <b>gigabyte.bin</b></li>
            <li>Clé USB FAT32, fichier à la racine</li>
            <li>PC éteint, USB sur port Q-Flash Plus</li>
            <li>Appuyez sur bouton Q-Flash Plus (arrière)</li>
            <li>LED clignote = mise à jour</li>
            <li>LED arrête = terminé</li>
        </ol>
        
        <p style="background: #4CAF50; color: white; padding: 10px; border-radius: 5px;">
        <b>✅ INFO GIGABYTE:</b><br>
        - Q-Flash très fiable et simple<br>
        - Version F## = version BIOS (F7 plus vieux que F12)<br>
        - Lisez le changelog : certaines MAJ ne sont pas rétrogradables
        </p>
        """
    
    def get_generic_tutorial(self):
        return """
        <h2>📚 TUTORIEL GÉNÉRIQUE MISE À JOUR BIOS</h2>
        
        <h3>Méthode USB (Plus sûre)</h3>
        <ol>
            <li>Identifiez EXACTEMENT votre carte mère (modèle + révision)</li>
            <li>Téléchargez le BIOS OFFICIEL depuis site fabricant</li>
            <li>Préparez une clé USB formatée en <b>FAT32</b></li>
            <li>Extrayez et copiez le BIOS sur la clé</li>
            <li>Redémarrez et entrez dans le BIOS (DEL/F2/F10)</li>
            <li>Cherchez l'outil de flash (M-Flash, Q-Flash, EZ Flash, etc.)</li>
            <li>Sélectionnez le fichier et lancez</li>
            <li><b>NE RIEN FAIRE</b> pendant 5-15 minutes</li>
            <li>Attendez redémarrage automatique</li>
        </ol>
        
        <h3>Touches BIOS courantes</h3>
        <ul>
            <li><b>DEL</b> - ASUS, MSI, Gigabyte, ASRock (majorité)</li>
            <li><b>F2</b> - Dell, certains laptops</li>
            <li><b>F10</b> - HP</li>
            <li><b>F1</b> - Lenovo anciens modèles</li>
            <li><b>F12</b> - Lenovo récents</li>
        </ul>
        
        <h3>⚠️ QUE FAIRE SI ÇA TOURNE MAL?</h3>
        <ol>
            <li><b>Pas de panique!</b> Laissez faire minimum 30 minutes</li>
            <li>Si vraiment bloqué: Clear CMOS (jumper ou pile 30 sec)</li>
            <li>Si PC ne démarre plus: Dual BIOS ou Flash BIOS button</li>
            <li>En dernier recours: Flasher puce BIOS (SAV ou expert)</li>
        </ol>
        
        <p style="background: #F44336; color: white; padding: 10px; border-radius: 5px;">
        <b>🚨 RÈGLES D'OR:</b><br>
        1. Vérifiez 3 fois le modèle exact<br>
        2. Téléchargez UNIQUEMENT depuis site officiel<br>
        3. Batterie laptop > 50% ou sur secteur<br>
        4. NE JAMAIS éteindre pendant mise à jour<br>
        5. En cas de doute, NE LE FAITES PAS
        </p>
        """
    
    def get_asrock_tutorial(self):
        return self.get_generic_tutorial().replace("GÉNÉRIQUE", "ASROCK")
    
    def get_dell_tutorial(self):
        return self.get_generic_tutorial().replace("GÉNÉRIQUE", "DELL")
    
    def get_hp_tutorial(self):
        return self.get_generic_tutorial().replace("GÉNÉRIQUE", "HP")
    
    def get_lenovo_tutorial(self):
        return self.get_generic_tutorial().replace("GÉNÉRIQUE", "LENOVO")
    
    def show_complete_guide(self):
        """Affiche le guide complet dans une nouvelle fenêtre"""
        guide_text = """
        <h1 style="color: #4CAF50;">📖 GUIDE COMPLET BIOS/UEFI</h1>
        
        <h2>🤔 C'EST QUOI LE BIOS?</h2>
        <p>Le <b>BIOS</b> (Basic Input/Output System) ou <b>UEFI</b> (son successeur moderne) est le 
        premier programme qui se lance quand vous allumez votre PC. C'est lui qui:</p>
        <ul>
            <li>Vérifie que tout le matériel fonctionne (RAM, disques, GPU...)</li>
            <li>Démarre Windows ou un autre OS</li>
            <li>Permet de configurer le matériel</li>
        </ul>
        
        <h2>💡 POURQUOI METTRE À JOUR?</h2>
        <ul>
            <li><b>Support nouveaux CPUs</b> (ex: Ryzen 5000 sur B450)</li>
            <li><b>Corrections bugs</b> (freeze, incompatibilités)</li>
            <li><b>Nouvelles fonctionnalités</b> (Resizable BAR, etc.)</li>
            <li><b>Meilleures performances</b> (optimisations RAM/CPU)</li>
            <li><b>Compatibilité Windows 11</b> (TPM, Secure Boot)</li>
        </ul>
        
        <h2>⚠️ QUAND NE PAS METTRE À JOUR?</h2>
        <ul>
            <li>Si tout fonctionne parfaitement ("If it ain't broken...")</li>
            <li>Pas de batterie suffisante (laptop)</li>
            <li>Orages / coupures de courant fréquentes</li>
            <li>Vous n'êtes pas sûr du modèle exact</li>
        </ul>
        
        <h2>🔑 PARAMÈTRES IMPORTANTS</h2>
        <p>Référez-vous à l'onglet "Paramètres BIOS" pour explications détaillées de:</p>
        <ul>
            <li>Boot Order</li>
            <li>Secure Boot</li>
            <li>XMP/DOCP (important pour RAM!)</li>
            <li>Virtualization</li>
            <li>TPM 2.0</li>
            <li>Et bien plus...</li>
        </ul>
        
        <h2>🆘 EN CAS DE PROBLÈME</h2>
        <h3>PC ne démarre plus après MAJ BIOS?</h3>
        <ol>
            <li><b>Clear CMOS</b>:
                <ul>
                    <li>Éteignez PC et débranchez</li>
                    <li>Retirez pile bouton carte mère 30 secondes</li>
                    <li>Ou utilisez jumper CLR_CMOS</li>
                    <li>Réessayez de démarrer</li>
                </ul>
            </li>
            <li><b>Dual BIOS</b> (Gigabyte): Appuyez Power + Reset simultanément</li>
            <li><b>Flash BIOS Button</b>: Utilisez méthode USB sans PC allumé</li>
            <li>En dernier recours: SAV ou reprogrammation puce BIOS</li>
        </ol>
        
        <h2>📱 RESSOURCES UTILES</h2>
        <ul>
            <li><b>Forums:</b> Reddit r/buildapc, Tom's Hardware</li>
            <li><b>Vidéos:</b> YouTube (cherchez votre modèle exact)</li>
            <li><b>Manuels:</b> Téléchargez le manuel de votre carte mère</li>
        </ul>
        
        <p style="background: #2196F3; color: white; padding: 15px; border-radius: 5px; font-size: 14px;">
        <b>💡 CONSEIL FINAL:</b><br>
        Si vous n'êtes pas sûr, NE LE FAITES PAS ou demandez à quelqu'un d'expérimenté.
        Une erreur de BIOS peut "bricker" votre carte mère. En cas de doute, l'onglet
        Tutoriels vous guide étape par étape pour votre fabricant spécifique.
        </p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("📖 Guide Complet BIOS/UEFI")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(guide_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                min-width: 700px;
                min-height: 500px;
            }
        """)
        msg.exec()


# Point d'entrée pour test standalone
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = BiosmanagerWindow(None)
    window.show()
    sys.exit(app.exec())
