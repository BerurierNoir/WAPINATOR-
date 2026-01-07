# modules/advanced_tools_window.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

class AdvancedToolsWindow(QDialog):
    """Fenêtre hub pour tous les modules avancés"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("🔧 Outils Avancés")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout()
        
        # Titre
        title = QLabel("🔧 OUTILS AVANCÉS DE DÉPANNAGE")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Modules additionnels pour diagnostics professionnels")
        subtitle.setStyleSheet("color: #888; font-size: 11px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Zone scrollable pour les boutons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # LISTE DES MODULES
        modules = [
            {
                "name": "📘 Analyseur BSOD",
                "desc": "Analyse fichiers .dmp et traduit codes erreur",
                "color": "#2196F3",
                "module": "bsod_analyzer"
            },
            {
                "name": "🔋 Santé Batterie",
                "desc": "Rapport détaillé usure batterie laptop",
                "color": "#4CAF50",
                "module": "battery_health"
            },
            {
                "name": "🌐 Test Réseau Avancé",
                "desc": "Speedtest + Packet Loss + Traceroute visuel",
                "color": "#00BCD4",
                "module": "network_tester"
            },
            {
                "name": "💾 Gestionnaire Drivers",
                "desc": "Scan + MAJ + Backup + Rollback drivers",
                "color": "#9C27B0",
                "module": "driver_manager"
            },
            {
                "name": "🚀 Nettoyeur Démarrage",
                "desc": "Optimise temps de boot + score impact",
                "color": "#FF9800",
                "module": "startup_manager"
            },
            {
                "name": "💊 Santé Windows",
                "desc": "Check intégrité + services + score global",
                "color": "#E91E63",
                "module": "windows_health"
            },
            {
                "name": "🌡️ Moniteur Températures",
                "desc": "Graph temps réel + alertes + historique",
                "color": "#F44336",
                "module": "temp_monitor"
            },
            {
                "name": "🔄 Réparateur Windows Update",
                "desc": "Reset complet WU + fix erreurs courantes",
                "color": "#3F51B5",
                "module": "windows_update_fix"
            },
            {
                "name": "🧪 Testeur RAM Rapide",
                "desc": "Test RAM en Windows (10-20 min)",
                "color": "#009688",
                "module": "ram_tester"
            },
            {
                "name": "🗑️ Nettoyeur Bloatware",
                "desc": "Détecte + supprime programmes inutiles",
                "color": "#795548",
                "module": "bloatware_cleaner"
            }
        ]
        
        for module_info in modules:
            self.create_module_button(scroll_layout, module_info)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Bouton fermer
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #F44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #D32F2F; }
        """)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QLabel { color: white; }
            QScrollArea { border: 1px solid #444; background: #2b2b2b; }
        """)
    
    def create_module_button(self, layout, module_info):
        """Créer un bouton pour chaque module"""
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Info module
        info_layout = QVBoxLayout()
        name_label = QLabel(module_info['name'])
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        desc_label = QLabel(module_info['desc'])
        desc_label.setStyleSheet("color: #888; font-size: 10px;")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        container_layout.addLayout(info_layout)
        
        container_layout.addStretch()
        
        # Bouton lancer
        launch_btn = QPushButton("🚀 Lancer")
        launch_btn.setFixedWidth(120)
        launch_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {module_info['color']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background: {self.darken_color(module_info['color'])};
            }}
        """)
        
        # Connecter au lancement du module
        launch_btn.clicked.connect(lambda: self.launch_module(module_info['module']))
        container_layout.addWidget(launch_btn)
        
        container.setLayout(container_layout)
        container.setStyleSheet("""
            QWidget {
                background: #2b2b2b;
                border: 2px solid #444;
                border-radius: 10px;
            }
            QWidget:hover {
                border: 2px solid #4CAF50;
            }
        """)
        
        layout.addWidget(container)
    
    def darken_color(self, hex_color):
        """Assombrir une couleur hex"""
        from PyQt6.QtGui import QColor
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        l = max(0, l - 30)
        color.setHsl(h, s, l, a)
        return color.name()
    
    def launch_module(self, module_name):
            """Lancer un module spécifique"""
            try:
                # Import dynamique du module
                if module_name == 'bsod_analyzer':
                    from modules.bsod_analyzer import BsodanalyzerWindow
                    window = BsodanalyzerWindow(self.parent_window)
                elif module_name == 'battery_health':
                    from modules.battery_health import BatteryhealthWindow
                    window = BatteryhealthWindow(self.parent_window)
                elif module_name == 'network_tester':
                    from modules.network_tester import NetworktesterWindow
                    window = NetworktesterWindow(self.parent_window)
                elif module_name == 'driver_manager':
                    from modules.driver_manager import DrivermanagerWindow
                    window = DrivermanagerWindow(self.parent_window)
                elif module_name == 'startup_manager':
                    from modules.startup_manager import StartupmanagerWindow
                    window = StartupmanagerWindow(self.parent_window)
                elif module_name == 'windows_health':
                    from modules.windows_health import WindowshealthWindow
                    window = WindowshealthWindow(self.parent_window)
                elif module_name == 'temp_monitor':
                    from modules.temp_monitor import TempmonitorWindow
                    window = TempmonitorWindow(self.parent_window)
                elif module_name == 'bloatware_cleaner':
                    from modules.bloatware_cleaner import BloatwarecleanerWindow
                    window = BloatwarecleanerWindow(self.parent_window)
                elif module_name == 'windows_update_fix':
                    from modules.windows_update_fix import WindowsupdatefixWindow
                    window = WindowsupdatefixWindow(self.parent_window)
                elif module_name == 'ram_tester':
                    from modules.ram_tester import RamtesterWindow
                    window = RamtesterWindow(self.parent_window)
                else:
                    raise ImportError(f"Module {module_name} non reconnu")
                
                window.exec()
                
            except ImportError as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "⚠️ Module non disponible",
                    f"Le module '{module_name}' n'est pas encore installé.\n\nErreur: {str(e)}"
                )
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "❌ Erreur",
                    f"Impossible de lancer le module:\n{str(e)}"
                )