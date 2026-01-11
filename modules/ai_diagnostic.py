# modules/ai_diagnostic_v2.1_FINAL.py
"""
AI Diagnostic Prompt Generator v2.1
Génère des prompts optimisés pour diagnostic PC via IA (Claude, ChatGPT, Gemini)

Améliorations v2.1:
- Raisonnement approfondi forcé (Chain of Thought)
- Ton ultra-pédagogique avec analogies
- Tutoriels actualisés 2024-2025
- Historique complet Windows Update (10 dernières)
- Disclaimer obligatoire avant copie
- Optimisation par IA (Claude FR, ChatGPT EN→FR, Gemini FR)
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QCheckBox, QGroupBox, 
                            QScrollArea, QWidget, QComboBox, QProgressBar,
                            QRadioButton, QButtonGroup, QApplication)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
import subprocess
import platform
import psutil
import webbrowser
from datetime import datetime
import os

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

# Liste complète des symptômes
SYMPTOMS_LIST = {
    'performance': {
        'name': '🐌 Performance & Lenteur',
        'items': [
            'PC lent au démarrage (>2 minutes)',
            'Lenteur générale du système',
            'Temps de réponse élevé',
            'Ralentissements progressifs',
            'Performance dégradée au fil du temps'
        ]
    },
    'stability': {
        'name': '❄️ Stabilité & Crashes',
        'items': [
            'BSOD (écrans bleus)',
            'Redémarrages intempestifs',
            'Freezes/blocages aléatoires',
            'Programmes qui crashent',
            'Système ne répond plus'
        ]
    },
    'gaming': {
        'name': '🎮 Gaming',
        'items': [
            'FPS bas dans les jeux',
            'Stuttering/micro-freezes',
            'Input lag important',
            'Drops de FPS soudains',
            'Artefacts graphiques'
        ]
    },
    'thermal': {
        'name': '🔥 Températures & Bruit',
        'items': [
            'Surchauffe (ventilateurs bruyants)',
            'PC s\'éteint sous charge',
            'Throttling CPU/GPU',
            'Ventilateurs ne tournent pas',
            'Ventilateurs toujours à fond'
        ]
    },
    'network': {
        'name': '🌐 Réseau',
        'items': [
            'Connexion Internet instable',
            'Wi-Fi se déconnecte',
            'Latence élevée',
            'Vitesse réduite',
            'Problèmes DNS'
        ]
    },
    'hardware': {
        'name': '🔧 Hardware',
        'items': [
            'USB qui se déconnectent',
            'Périphériques non reconnus',
            'Audio crackling/coupures',
            'Moniteur problèmes affichage',
            'Disque dur bruits anormaux'
        ]
    },
    'boot': {
        'name': '🔄 Démarrage',
        'items': [
            'Écran noir au démarrage',
            'Boucle de redémarrage',
            'Erreurs au boot',
            'POST qui bloque',
            'Windows ne démarre pas'
        ]
    },
    'software': {
        'name': '💻 Logiciels',
        'items': [
            'Windows Update qui échoue',
            'Erreurs DLL manquantes',
            'Applications ne s\'installent pas',
            'Problèmes activation Windows',
            'Erreurs registre'
        ]
    },
    'storage': {
        'name': '💾 Stockage',
        'items': [
            'Espace disque plein',
            'Disque lent (100% utilisation)',
            'Erreurs lecture/écriture',
            'Fichiers corrompus',
            'SSD non reconnu'
        ]
    },
    'power': {
        'name': '⚡ Alimentation & Énergie',
        'items': [
            'PC ne s\'allume pas',
            'Coupures d\'alimentation',
            'Problèmes veille/hibernation',
            'Batterie se décharge vite (laptop)',
            'PC s\'éteint sans prévenir'
        ]
    }
}


class SystemScanWorker(QThread):
    """Worker pour scanner toutes les infos système"""
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        """Collecte toutes les informations système"""
        system_info = {
            'hardware': {},
            'software': {},
            'current_state': {},
            'logs': {},
            'tests': {}
        }
        
        try:
            # 1. Hardware Info (20%)
            self.progress_signal.emit("🔍 Scan matériel...", 10)
            system_info['hardware'] = self.get_hardware_info()
            self.progress_signal.emit("✅ Matériel scanné", 20)
            
            # 2. Software Info (40%)
            self.progress_signal.emit("💻 Scan logiciels...", 30)
            system_info['software'] = self.get_software_info()
            self.progress_signal.emit("✅ Logiciels scannés", 40)
            
            # 3. Current State (60%)
            self.progress_signal.emit("📊 État actuel...", 50)
            system_info['current_state'] = self.get_current_state()
            self.progress_signal.emit("✅ État capturé", 60)
            
            # 4. Logs & Errors (80%)
            self.progress_signal.emit("📝 Analyse logs...", 70)
            system_info['logs'] = self.get_system_logs()
            self.progress_signal.emit("✅ Logs analysés", 80)
            
            # 5. Tests Performed (100%)
            self.progress_signal.emit("🔧 Vérif tests...", 90)
            system_info['tests'] = self.get_performed_tests()
            self.progress_signal.emit("✅ Scan terminé!", 100)
            
        except Exception as e:
            self.progress_signal.emit(f"❌ Erreur: {str(e)}", 0)
        
        self.finished_signal.emit(system_info)
    
    def get_hardware_info(self):
        """Récupère infos matériel"""
        hw_info = {}
        
        try:
            # CPU
            hw_info['cpu'] = {
                'model': platform.processor() or 'Unknown',
                'cores_physical': psutil.cpu_count(logical=False),
                'cores_logical': psutil.cpu_count(logical=True),
                'frequency': psutil.cpu_freq().max if psutil.cpu_freq() else 'Unknown',
                'current_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 'Unknown'
            }
            
            # RAM
            ram = psutil.virtual_memory()
            hw_info['ram'] = {
                'total_gb': round(ram.total / (1024**3), 1),
                'type': 'DDR4',
                'speed': 'Unknown'
            }
            
            # GPU
            hw_info['gpu'] = self.get_gpu_info()
            
            # Disques
            hw_info['storage'] = []
            for partition in psutil.disk_partitions():
                if 'cdrom' not in partition.opts and partition.fstype:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        hw_info['storage'].append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total_gb': round(usage.total / (1024**3), 1),
                            'used_gb': round(usage.used / (1024**3), 1),
                            'free_gb': round(usage.free / (1024**3), 1),
                            'percent': usage.percent
                        })
                    except:
                        pass
            
            # Carte mère via WMI
            try:
                import wmi
                c = wmi.WMI()
                for board in c.Win32_BaseBoard():
                    hw_info['motherboard'] = {
                        'manufacturer': board.Manufacturer,
                        'model': board.Product
                    }
                    break
            except:
                hw_info['motherboard'] = {'manufacturer': 'Unknown', 'model': 'Unknown'}
            
        except Exception as e:
            hw_info['error'] = str(e)
        
        return hw_info
    
    def get_gpu_info(self):
        """Détecte la carte graphique"""
        try:
            import wmi
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                if 'Microsoft' not in gpu.Name:
                    vram_bytes = gpu.AdapterRAM
                    vram_gb = round(vram_bytes / (1024**3), 1) if vram_bytes else 'Unknown'
                    
                    return {
                        'model': gpu.Name,
                        'vram_gb': vram_gb,
                        'driver': gpu.DriverVersion,
                        'driver_date': gpu.DriverDate[:8] if gpu.DriverDate else 'Unknown'
                    }
        except:
            pass
        
        return {
            'model': 'Unknown',
            'vram_gb': 'Unknown',
            'driver': 'Unknown',
            'driver_date': 'Unknown'
        }
    
    def get_software_info(self):
        """Récupère infos logicielles"""
        sw_info = {}
        
        try:
            # Windows
            sw_info['os'] = {
                'name': platform.system(),
                'version': platform.version(),
                'release': platform.release(),
                'build': platform.win32_ver()[1] if platform.system() == 'Windows' else 'N/A',
                'architecture': platform.machine()
            }
            
            # BIOS
            try:
                import wmi
                c = wmi.WMI()
                for bios in c.Win32_BIOS():
                    sw_info['bios'] = {
                        'manufacturer': bios.Manufacturer,
                        'version': bios.SMBIOSBIOSVersion,
                        'date': bios.ReleaseDate[:8] if bios.ReleaseDate else 'Unknown'
                    }
                    break
            except:
                sw_info['bios'] = {'manufacturer': 'Unknown', 'version': 'Unknown', 'date': 'Unknown'}
            
            # Historique Windows Update (10 dernières)
            sw_info['update_history'] = self.get_windows_update_history()
            
        except Exception as e:
            sw_info['error'] = str(e)
        
        return sw_info
    
    def get_windows_update_history(self):
        """Récupère l'historique des 10 dernières MAJ Windows"""
        updates = []
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-HotFix | Sort-Object -Property InstalledOn -Descending | Select-Object -First 10 | Format-Table -Property HotFixID, InstalledOn, Description -AutoSize'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[2:]:  # Skip headers
                    if line.strip():
                        updates.append(line.strip())
                
                return updates if updates else ["Impossible à déterminer"]
        except:
            pass
        
        return ["Impossible à déterminer"]
    
    def get_current_state(self):
        """État actuel du système"""
        state = {}
        
        try:
            # Utilisation
            cpu_percent = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            
            state['usage'] = {
                'cpu_percent': cpu_percent,
                'ram_used_gb': round(ram.used / (1024**3), 1),
                'ram_total_gb': round(ram.total / (1024**3), 1),
                'ram_percent': ram.percent
            }
            
            # Processus gourmands
            state['top_processes'] = self.get_top_processes()
            
            # Uptime
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            
            state['uptime'] = f"{days} jours {hours} heures"
            
        except Exception as e:
            state['error'] = str(e)
        
        return state
    
    def get_top_processes(self):
        """Top 5 processus par RAM"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    processes.append({
                        'name': proc.info['name'],
                        'memory_mb': round(proc.info['memory_info'].rss / (1024**2), 1)
                    })
                except:
                    pass
            
            processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            return processes[:5]
        
        except:
            return []
    
    def get_system_logs(self):
        """Analyse les logs système"""
        logs = {}
        
        try:
            logs['event_viewer'] = self.get_event_viewer_errors()
            logs['bsod'] = self.check_bsod_dumps()
            logs['windows_update'] = self.check_wu_errors()
            
        except Exception as e:
            logs['error'] = str(e)
        
        return logs
    
    def get_event_viewer_errors(self):
        """Récupère erreurs Event Viewer"""
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-EventLog -LogName System -EntryType Error -Newest 20 | Select-Object TimeGenerated, Source, EventID, Message'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                error_count = max(0, len(lines) - 3)
                return {
                    'count': error_count,
                    'sample': result.stdout[:500]
                }
        except:
            pass
        
        return {'count': 'Non disponible', 'sample': ''}
    
    def check_bsod_dumps(self):
        """Vérifie les dumps BSOD"""
        bsod_info = {
            'recent_dumps': [],
            'location': r'C:\Windows\Minidump'
        }
        
        try:
            minidump_path = r'C:\Windows\Minidump'
            if os.path.exists(minidump_path):
                dumps = []
                for file in os.listdir(minidump_path):
                    if file.endswith('.dmp'):
                        filepath = os.path.join(minidump_path, file)
                        mtime = os.path.getmtime(filepath)
                        dumps.append({
                            'filename': file,
                            'date': datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
                        })
                
                dumps.sort(key=lambda x: x['date'], reverse=True)
                bsod_info['recent_dumps'] = dumps[:5]
        except:
            pass
        
        return bsod_info
    
    def check_wu_errors(self):
        """Vérifie erreurs Windows Update"""
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-WindowsUpdateLog; Get-Content $env:USERPROFILE\\Desktop\\WindowsUpdate.log -Tail 20'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                timeout=10
            )
            
            if 'error' in result.stdout.lower() or 'failed' in result.stdout.lower():
                return "Erreurs détectées"
            else:
                return "Aucune erreur récente"
        except:
            return "Non vérifiable"
    
    def get_performed_tests(self):
        """Vérifie quels tests ont été effectués"""
        tests = {}
        
        try:
            tests['sfc'] = self.check_sfc_status()
            tests['dism'] = self.check_dism_status()
            tests['memory'] = "Non effectué (vérifier manuellement)"
            
        except Exception as e:
            tests['error'] = str(e)
        
        return tests
    
    def check_sfc_status(self):
        """Vérifie si SFC a été exécuté"""
        try:
            log_path = r'C:\Windows\Logs\CBS\CBS.log'
            if os.path.exists(log_path):
                mtime = os.path.getmtime(log_path)
                last_run = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
                return f"Dernier scan: {last_run}"
        except:
            pass
        
        return "Non exécuté récemment"
    
    def check_dism_status(self):
        """Vérifie si DISM a été exécuté"""
        try:
            log_path = r'C:\Windows\Logs\DISM\dism.log'
            if os.path.exists(log_path):
                mtime = os.path.getmtime(log_path)
                last_run = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
                return f"Dernier scan: {last_run}"
        except:
            pass
        
        return "Non exécuté récemment"


class AIDiagnosticWindow(QDialog):
    """Fenêtre principale AI Diagnostic Generator v2.1"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🤖 AI Diagnostic Prompt Generator v2.1")
        self.setMinimumSize(1200, 900)
        
        # Variables
        self.system_info = {}
        self.selected_symptoms = []
        self.context_answers = {}
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # En-tête
        self.create_header(main_layout)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Sections
        self.create_symptoms_section(scroll_layout)
        self.create_context_section(scroll_layout)
        self.create_scan_section(scroll_layout)
        self.create_ai_selection(scroll_layout)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Prompt display
        self.create_prompt_display(main_layout)
        
        # Boutons
        self.create_action_buttons(main_layout)
        
        self.setLayout(main_layout)
        
        # Style
        self.apply_styles()
    
    def apply_styles(self):
        """Applique les styles CSS"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: white;
            }
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #4CAF50;
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
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 3px;
                background: #2b2b2b;
            }
            QCheckBox::indicator:checked {
                background: #4CAF50;
                border-color: #4CAF50;
            }
            QComboBox {
                background: #3a3a3a;
                color: white;
                padding: 8px;
                border: 2px solid #444;
                border-radius: 5px;
                min-height: 25px;
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
            QTextEdit {
                background-color: #1a1a1a;
                border: 2px solid #444;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 10px;
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
            QProgressBar {
                border: 2px solid #444;
                border-radius: 5px;
                text-align: center;
                background: #2b2b2b;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #4CAF50, stop:1 #2196F3);
                border-radius: 3px;
            }
            QRadioButton {
                color: white;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 9px;
                background: #2b2b2b;
            }
            QRadioButton::indicator:checked {
                background: #4CAF50;
                border-color: #4CAF50;
            }
        """)
    
    def create_header(self, layout):
        """Crée l'en-tête"""
        header = QLabel("🤖 AI DIAGNOSTIC PROMPT GENERATOR v2.1")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Raisonnement approfondi + Tutoriels détaillés + Disclaimer sécurité")
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        info = QLabel("💡 Cochez symptômes → Répondez questions → Scannez → Copiez le prompt optimisé")
        info.setStyleSheet("""
            background: #2196F3;
            color: white;
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 10px;
        """)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
    
    def create_symptoms_section(self, layout):
        """Section symptômes"""
        symptoms_group = QGroupBox("📋 ÉTAPE 1: Sélectionnez vos symptômes")
        symptoms_layout = QVBoxLayout()
        
        self.symptom_checkboxes = {}
        
        for category_id, category_data in SYMPTOMS_LIST.items():
            cat_label = QLabel(category_data['name'])
            cat_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11px; margin-top: 10px;")
            symptoms_layout.addWidget(cat_label)
            
            for symptom in category_data['items']:
                cb = QCheckBox(symptom)
                cb.setStyleSheet("margin-left: 20px; padding: 3px;")
                symptoms_layout.addWidget(cb)
                self.symptom_checkboxes[symptom] = cb
        
        clear_btn = QPushButton("🔄 Tout décocher")
        clear_btn.clicked.connect(self.clear_symptoms)
        clear_btn.setStyleSheet("background: #FF9800; color: white; margin-top: 10px;")
        symptoms_layout.addWidget(clear_btn)
        
        symptoms_group.setLayout(symptoms_layout)
        layout.addWidget(symptoms_group)
    
    def create_context_section(self, layout):
        """Section questions contextuelles"""
        context_group = QGroupBox("❓ ÉTAPE 2: Questions Contextuelles")
        context_layout = QVBoxLayout()
        
        # Quand
        when_layout = QHBoxLayout()
        when_label = QLabel("📅 Quand le problème a commencé:")
        when_label.setMinimumWidth(200)
        self.when_combo = QComboBox()
        self.when_combo.addItems([
            "Aujourd'hui",
            "Cette semaine",
            "Ce mois-ci",
            "Plus longtemps",
            "Depuis toujours"
        ])
        when_layout.addWidget(when_label)
        when_layout.addWidget(self.when_combo)
        context_layout.addLayout(when_layout)
        
        # Fréquence
        freq_layout = QHBoxLayout()
        freq_label = QLabel("🔄 À quelle fréquence:")
        freq_label.setMinimumWidth(200)
        self.freq_combo = QComboBox()
        self.freq_combo.addItems([
            "Constamment",
            "Plusieurs fois par jour",
            "Une fois par jour",
            "Occasionnellement",
            "Rarement"
        ])
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_combo)
        context_layout.addLayout(freq_layout)
        
        # Modifications
        modif_layout = QHBoxLayout()
        modif_label = QLabel("⚙️ Modifications récentes:")
        modif_label.setMinimumWidth(200)
        self.modif_combo = QComboBox()
        self.modif_combo.addItems([
            "Aucune modification",
            "Installation nouveau hardware",
            "Mise à jour Windows",
            "Nouveaux drivers",
            "Nouveau programme installé",
            "Overclocking",
            "Nettoyage physique PC"
        ])
        modif_layout.addWidget(modif_label)
        modif_layout.addWidget(self.modif_combo)
        context_layout.addLayout(modif_layout)
        
        # Usage
        usage_layout = QHBoxLayout()
        usage_label = QLabel("🎮 Utilisation principale:")
        usage_label.setMinimumWidth(200)
        self.usage_combo = QComboBox()
        self.usage_combo.addItems([
            "Gaming",
            "Bureautique",
            "Montage vidéo/3D",
            "Streaming",
            "Programmation",
            "Navigation web"
        ])
        usage_layout.addWidget(usage_label)
        usage_layout.addWidget(self.usage_combo)
        context_layout.addLayout(usage_layout)
        
        # Notes
        notes_label = QLabel("📝 Notes additionnelles (optionnel):")
        notes_label.setStyleSheet("margin-top: 10px;")
        context_layout.addWidget(notes_label)
        
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText("Ajoutez ici toute information supplémentaire pertinente...")
        context_layout.addWidget(self.notes_text)
        
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)
    
    def create_scan_section(self, layout):
        """Section scan système"""
        scan_group = QGroupBox("🔍 ÉTAPE 3: Scan Automatique du Système")
        scan_layout = QVBoxLayout()
        
        self.scan_btn = QPushButton("🔄 SCANNER LE PC MAINTENANT")
        self.scan_btn.clicked.connect(self.start_system_scan)
        self.scan_btn.setStyleSheet("""
            background: #4CAF50;
            color: white;
            font-size: 13px;
            padding: 15px;
        """)
        scan_layout.addWidget(self.scan_btn)
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        scan_layout.addWidget(self.scan_progress)
        
        self.scan_status = QLabel("Cliquez pour scanner (collecte automatique de ~150+ informations)")
        self.scan_status.setStyleSheet("color: #888; font-style: italic; text-align: center;")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_layout.addWidget(self.scan_status)
        
        self.scan_summary = QLabel()
        self.scan_summary.setVisible(False)
        self.scan_summary.setStyleSheet("""
            background: #2b2b2b;
            padding: 10px;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            margin-top: 10px;
        """)
        scan_layout.addWidget(self.scan_summary)
        
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)
    
    def create_ai_selection(self, layout):
        """Section choix de l'IA"""
        ai_group = QGroupBox("🤖 ÉTAPE 4: Choisissez votre IA")
        ai_layout = QVBoxLayout()
        
        self.ai_button_group = QButtonGroup()
        
        claude_rb = QRadioButton("🟣 Claude (Anthropic) - Recommandé pour diagnostic technique")
        claude_rb.setChecked(True)
        self.ai_button_group.addButton(claude_rb, 0)
        ai_layout.addWidget(claude_rb)
        
        chatgpt_rb = QRadioButton("🟢 ChatGPT (OpenAI) - Bon pour explications détaillées")
        self.ai_button_group.addButton(chatgpt_rb, 1)
        ai_layout.addWidget(chatgpt_rb)
        
        gemini_rb = QRadioButton("🔵 Gemini (Google) - Alternative efficace")
        self.ai_button_group.addButton(gemini_rb, 2)
        ai_layout.addWidget(gemini_rb)
        
        generic_rb = QRadioButton("⚪ Format Générique - Compatible toutes IA")
        self.ai_button_group.addButton(generic_rb, 3)
        ai_layout.addWidget(generic_rb)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
    
    def create_prompt_display(self, layout):
        """Zone d'affichage du prompt généré"""
        prompt_group = QGroupBox("📄 PROMPT GÉNÉRÉ (Prêt à copier)")
        prompt_layout = QVBoxLayout()
        
        info_layout = QHBoxLayout()
        self.char_count_label = QLabel("0 caractères")
        self.char_count_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.char_count_label)
        info_layout.addStretch()
        prompt_layout.addLayout(info_layout)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setMinimumHeight(300)
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setPlaceholderText(
            "Le prompt généré apparaîtra ici...\n\n"
            "1. Cochez vos symptômes\n"
            "2. Répondez aux questions\n"
            "3. Scannez le PC\n"
            "4. Cliquez 'Générer Prompt'\n"
            "5. Copiez et collez dans votre IA préférée !"
        )
        prompt_layout.addWidget(self.prompt_text)
        
        prompt_group.setLayout(prompt_layout)
        prompt_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #2196F3;
            }
            QGroupBox::title {
                color: #2196F3;
            }
        """)
        layout.addWidget(prompt_group)
    
    def create_action_buttons(self, layout):
        """Boutons d'action"""
        button_layout = QHBoxLayout()
        
        generate_btn = QPushButton("✨ GÉNÉRER PROMPT")
        generate_btn.clicked.connect(self.generate_prompt)
        generate_btn.setStyleSheet("background: #4CAF50; color: white; font-size: 12px;")
        button_layout.addWidget(generate_btn)
        
        copy_btn = QPushButton("📋 COPIER")
        copy_btn.clicked.connect(self.copy_prompt)
        copy_btn.setStyleSheet("background: #2196F3; color: white;")
        button_layout.addWidget(copy_btn)
        
        export_btn = QPushButton("💾 EXPORTER .TXT")
        export_btn.clicked.connect(self.export_prompt)
        export_btn.setStyleSheet("background: #9C27B0; color: white;")
        button_layout.addWidget(export_btn)
        
        open_ai_btn = QPushButton("🌐 OUVRIR IA")
        open_ai_btn.clicked.connect(self.open_ai_website)
        open_ai_btn.setStyleSheet("background: #FF9800; color: white;")
        button_layout.addWidget(open_ai_btn)
        
        close_btn = QPushButton("❌ FERMER")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: #F44336; color: white;")
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def clear_symptoms(self):
        """Décocher tous les symptômes"""
        for cb in self.symptom_checkboxes.values():
            cb.setChecked(False)
    
    def start_system_scan(self):
        """Lance le scan système"""
        self.scan_btn.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        self.scan_status.setText("🔄 Scan en cours...")
        
        self.scan_worker = SystemScanWorker()
        self.scan_worker.progress_signal.connect(self.on_scan_progress)
        self.scan_worker.finished_signal.connect(self.on_scan_finished)
        self.scan_worker.start()
    
    def on_scan_progress(self, message, progress):
        """Update progress"""
        self.scan_status.setText(message)
        self.scan_progress.setValue(progress)
    
    def on_scan_finished(self, system_info):
        """Scan terminé"""
        self.system_info = system_info
        self.scan_btn.setEnabled(True)
        self.scan_progress.setVisible(False)
        
        summary_text = f"""✅ Scan terminé avec succès!

📊 Informations collectées:
• Hardware: {len(system_info.get('hardware', {}))} catégories
• Software: {len(system_info.get('software', {}))} catégories  
• État actuel: {len(system_info.get('current_state', {}))} métriques
• Logs analysés: {len(system_info.get('logs', {}))} sources

💡 Prêt à générer le prompt!"""
        
        self.scan_summary.setText(summary_text)
        self.scan_summary.setVisible(True)
        self.scan_status.setText("✅ Scan terminé! Vous pouvez maintenant générer le prompt.")
        
        QMessageBox.information(
            self,
            "✅ Scan Terminé",
            "Toutes les informations système ont été collectées!\n\n"
            "Vous pouvez maintenant générer le prompt optimisé."
        )
    
    def generate_prompt(self):
        """Génère le prompt"""
        selected_symptoms = [symptom for symptom, cb in self.symptom_checkboxes.items() if cb.isChecked()]
        
        if not selected_symptoms:
            QMessageBox.warning(
                self,
                "⚠️ Symptômes manquants",
                "Veuillez cocher au moins un symptôme avant de générer le prompt."
            )
            return
        
        if not self.system_info:
            reply = QMessageBox.question(
                self,
                "❓ Scan non effectué",
                "Le scan système n'a pas été effectué.\n\n"
                "Voulez-vous générer le prompt sans les informations système?\n"
                "(Recommandé: Scannez d'abord pour un diagnostic plus précis)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        ai_id = self.ai_button_group.checkedId()
        ai_names = ['claude', 'chatgpt', 'gemini', 'generic']
        ai_name = ai_names[ai_id]
        
        prompt = self.build_prompt(ai_name, selected_symptoms)
        
        self.prompt_text.setPlainText(prompt)
        self.char_count_label.setText(f"{len(prompt)} caractères")
        
        cursor = self.prompt_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.prompt_text.setTextCursor(cursor)
        
        QMessageBox.information(
            self,
            "✅ Prompt Généré",
            f"Prompt généré avec succès!\n\n"
            f"Longueur: {len(prompt)} caractères\n"
            f"IA optimisée: {ai_name.title()}\n\n"
            f"Cliquez 'Copier' puis collez dans votre IA préférée."
        )
    
    def build_prompt(self, ai_name, selected_symptoms):
        """Construction du prompt selon l'IA"""
        from modules.prompt_templates_v2 import (
            build_claude_prompt_v2,
            build_chatgpt_prompt_v2,
            build_gemini_prompt_v2,
            build_generic_prompt_v2
        )
        
        context = {
            'when': self.when_combo.currentText(),
            'frequency': self.freq_combo.currentText(),
            'modifications': self.modif_combo.currentText(),
            'usage': self.usage_combo.currentText(),
            'notes': self.notes_text.toPlainText().strip()
        }
        
        if ai_name == 'claude':
            return build_claude_prompt_v2(selected_symptoms, context, self.system_info)
        elif ai_name == 'chatgpt':
            return build_chatgpt_prompt_v2(selected_symptoms, context, self.system_info)
        elif ai_name == 'gemini':
            return build_gemini_prompt_v2(selected_symptoms, context, self.system_info)
        else:
            return build_generic_prompt_v2(selected_symptoms, context, self.system_info)
    
    def copy_prompt(self):
        """Copie le prompt avec disclaimer obligatoire"""
        prompt = self.prompt_text.toPlainText()
        
        if not prompt or prompt == self.prompt_text.placeholderText():
            QMessageBox.warning(
                self,
                "⚠️ Aucun prompt",
                "Veuillez d'abord générer un prompt avant de copier."
            )
            return
        
        # DISCLAIMER OBLIGATOIRE
        disclaimer_dialog = QMessageBox(self)
        disclaimer_dialog.setWindowTitle("⚠️ AVERTISSEMENT IMPORTANT")
        disclaimer_dialog.setIcon(QMessageBox.Icon.Warning)
        
        disclaimer_text = """Ce prompt va générer un diagnostic via Intelligence Artificielle.

RÈGLES ESSENTIELLES :

✋ NE SUIVEZ PAS LES SOLUTIONS AVEUGLÉMENT
   → Les IA peuvent faire des erreurs
   → Lisez ATTENTIVEMENT chaque étape
   → Comprenez ce que vous faites AVANT

🛡️ TOUJOURS CRÉER UN BACKUP
   → Point de restauration OBLIGATOIRE
   → Sauvegarde données importantes

🤝 EN CAS DE DOUTE → DEMANDEZ DE L'AIDE
   → Ami compétent en informatique
   → Professionnel (technicien, magasin)

🔴 SI QUELQUE CHOSE NE VA PAS
   → Arrêtez IMMÉDIATEMENT
   → Restaurez le point de restauration
   → Ne continuez PAS si confusion

💡 L'IA EST UN OUTIL D'AIDE, PAS UN REMPLACEMENT
   → Elle analyse des données
   → Elle propose des pistes
   → VOUS prenez la responsabilité

═══════════════════════════════════════════════════════════

Avez-vous bien compris ces avertissements ?"""
        
        disclaimer_dialog.setText(disclaimer_text)
        disclaimer_dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        disclaimer_dialog.button(QMessageBox.StandardButton.Yes).setText("✅ OUI, j'ai compris")
        disclaimer_dialog.button(QMessageBox.StandardButton.No).setText("❌ Annuler")
        
        result = disclaimer_dialog.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            clipboard = QApplication.clipboard()
            clipboard.setText(prompt)
            
            QMessageBox.information(
                self,
                "✅ Copié!",
                f"Prompt copié dans le presse-papier!\n\n"
                f"⚠️ RAPPEL: Créez un point de restauration AVANT toute manipulation!\n\n"
                f"Collez-le maintenant dans votre IA préférée."
            )
        else:
            QMessageBox.information(
                self,
                "Annulé",
                "Copie annulée. Prenez le temps de bien lire les avertissements."
            )
    
    def export_prompt(self):
        """Exporte le prompt en .txt"""
        prompt = self.prompt_text.toPlainText()
        
        if not prompt or prompt == self.prompt_text.placeholderText():
            QMessageBox.warning(
                self,
                "⚠️ Aucun prompt",
                "Veuillez d'abord générer un prompt avant d'exporter."
            )
            return
        
        from PyQt6.QtWidgets import QFileDialog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"diagnostic_prompt_{timestamp}.txt"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le Prompt",
            default_name,
            "Fichiers texte (*.txt)"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(prompt)
                
                QMessageBox.information(
                    self,
                    "✅ Exporté!",
                    f"Prompt exporté avec succès!\n\n"
                    f"Fichier: {filepath}\n"
                    f"Taille: {len(prompt)} caractères"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "❌ Erreur",
                    f"Impossible d'exporter le fichier:\n{str(e)}"
                )
    
    def open_ai_website(self):
        """Ouvre le site de l'IA sélectionnée"""
        ai_id = self.ai_button_group.checkedId()
        
        urls = {
            0: 'https://claude.ai',
            1: 'https://chat.openai.com',
            2: 'https://gemini.google.com',
            3: 'https://claude.ai'
        }
        
        ai_names = {
            0: 'Claude',
            1: 'ChatGPT',
            2: 'Gemini',
            3: 'Claude'
        }
        
        url = urls.get(ai_id, 'https://claude.ai')
        ai_name = ai_names.get(ai_id, 'IA')
        
        webbrowser.open(url)
        
        QMessageBox.information(
            self,
            "🌐 Page Ouverte",
            f"{ai_name} a été ouvert dans votre navigateur!\n\n"
            f"Collez-y le prompt copié pour obtenir votre diagnostic."
        )


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = AIDiagnosticWindow(None)
    window.show()
    sys.exit(app.exec())
