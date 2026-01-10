# modules/privacy_telemetry.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QCheckBox, QGroupBox, 
                            QScrollArea, QWidget, QProgressBar, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import subprocess
import winreg
import os
import json
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

# Configuration des paramètres de confidentialité
PRIVACY_CONFIG = {
    'telemetry': {
        'name': '🔴 Télémétrie Windows',
        'desc': 'Désactive l\'envoi de données d\'utilisation à Microsoft',
        'services': [
            'DiagTrack',  # Connected User Experiences and Telemetry
            'dmwappushservice',  # WAP Push Message Routing Service
        ],
        'registry': [
            (r'SOFTWARE\Policies\Microsoft\Windows\DataCollection', 'AllowTelemetry', 0),
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection', 'AllowTelemetry', 0),
        ],
        'tasks': [
            r'\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser',
            r'\Microsoft\Windows\Application Experience\ProgramDataUpdater',
            r'\Microsoft\Windows\Autochk\Proxy',
            r'\Microsoft\Windows\Customer Experience Improvement Program\Consolidator',
            r'\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip',
        ],
        'severity': 'high'
    },
    
    'cortana': {
        'name': '🎤 Cortana / Copilot',
        'desc': 'Désactive l\'assistant vocal et Copilot',
        'registry': [
            (r'SOFTWARE\Policies\Microsoft\Windows\Windows Search', 'AllowCortana', 0),
            (r'SOFTWARE\Microsoft\PolicyManager\default\Experience\AllowCortana', 'value', 0),
            (r'SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot', 'TurnOffWindowsCopilot', 1),
        ],
        'services': [],
        'tasks': [],
        'severity': 'medium'
    },
    
    'advertising': {
        'name': '📢 Publicité Personnalisée',
        'desc': 'Désactive le tracking publicitaire',
        'registry': [
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo', 'Enabled', 0),
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy', 'TailoredExperiencesWithDiagnosticDataEnabled', 0),
        ],
        'services': [],
        'tasks': [],
        'severity': 'medium'
    },
    
    'location': {
        'name': '📍 Localisation',
        'desc': 'Désactive le suivi de localisation',
        'registry': [
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location', 'Value', 'Deny'),
            (r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}', 'SensorPermissionState', 0),
        ],
        'services': ['lfsvc'],  # Geolocation Service
        'tasks': [],
        'severity': 'medium'
    },
    
    'webcam_mic': {
        'name': '🎥 Caméra & Micro',
        'desc': 'Désactive l\'accès automatique en arrière-plan (apps peuvent toujours demander)',
        'registry': [
            # Ne pas bloquer complètement (Deny) mais désactiver accès automatique
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged', 'Value', 'Deny'),
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged', 'Value', 'Deny'),
        ],
        'services': [],
        'tasks': [],
        'severity': 'low'
    },
    
    'timeline': {
        'name': '📅 Timeline / Historique',
        'desc': 'Désactive l\'historique d\'activité Windows',
        'registry': [
            (r'SOFTWARE\Policies\Microsoft\Windows\System', 'EnableActivityFeed', 0),
            (r'SOFTWARE\Policies\Microsoft\Windows\System', 'PublishUserActivities', 0),
            (r'SOFTWARE\Policies\Microsoft\Windows\System', 'UploadUserActivities', 0),
        ],
        'services': [],
        'tasks': [],
        'severity': 'low'
    },
    
    'feedback': {
        'name': '💬 Feedback & Diagnostics',
        'desc': 'Désactive les demandes de feedback Windows',
        'registry': [
            (r'SOFTWARE\Microsoft\Siuf\Rules', 'NumberOfSIUFInPeriod', 0),
            (r'SOFTWARE\Policies\Microsoft\Windows\DataCollection', 'DoNotShowFeedbackNotifications', 1),
        ],
        'services': [],
        'tasks': [
            r'\Microsoft\Windows\Feedback\Siuf\DmClient',
            r'\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload',
        ],
        'severity': 'low'
    },
    
    'wifi_sense': {
        'name': '📡 Wi-Fi Sense',
        'desc': 'Désactive le partage Wi-Fi automatique',
        'registry': [
            (r'SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting', 'value', 0),
            (r'SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowAutoConnectToWiFiSenseHotspots', 'value', 0),
        ],
        'services': [],
        'tasks': [],
        'severity': 'medium'
    },
    
    'biometrics': {
        'name': '👁️ Biométrie Cloud',
        'desc': 'Désactive l\'envoi des données biométriques',
        'registry': [
            (r'SOFTWARE\Policies\Microsoft\Biometrics', 'Enabled', 0),
        ],
        'services': [],
        'tasks': [],
        'severity': 'low'
    },
    
    'app_diagnostics': {
        'name': '🔍 Diagnostics Applications',
        'desc': 'Empêche les apps d\'accéder aux diagnostics',
        'registry': [
            (r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\appDiagnostics', 'Value', 'Deny'),
        ],
        'services': [],
        'tasks': [],
        'severity': 'low'
    },
    
    'sync_settings': {
        'name': '🔄 Synchronisation Paramètres',
        'desc': 'Désactive la sync des paramètres sur cloud Microsoft',
        'registry': [
            (r'SOFTWARE\Policies\Microsoft\Windows\SettingSync', 'DisableSettingSync', 2),
            (r'SOFTWARE\Policies\Microsoft\Windows\SettingSync', 'DisableSettingSyncUserOverride', 1),
        ],
        'services': [],
        'tasks': [],
        'severity': 'low'
    }
}

# Domaines Microsoft à bloquer (hosts file)
# Divisés en 2 catégories : SAFE (pas d'impact) et AGGRESSIVE (peut affecter Update/Store)

TRACKING_DOMAINS_SAFE = [
    # Domaines de télémétrie pure (aucun impact sur fonctionnalités)
    'telecommand.telemetry.microsoft.com',
    'telecommand.telemetry.microsoft.com.nsatc.net',
    'oca.telemetry.microsoft.com',
    'oca.telemetry.microsoft.com.nsatc.net',
    'sqm.telemetry.microsoft.com',
    'sqm.telemetry.microsoft.com.nsatc.net',
    'watson.telemetry.microsoft.com',
    'watson.telemetry.microsoft.com.nsatc.net',
    'df.telemetry.microsoft.com',
    'reports.wes.df.telemetry.microsoft.com',
    'wes.df.telemetry.microsoft.com',
    'services.wes.df.telemetry.microsoft.com',
    'sqm.df.telemetry.microsoft.com',
    'telemetry.microsoft.com',
    'watson.ppe.telemetry.microsoft.com',
    'telemetry.appex.bing.net',
    'telemetry.urs.microsoft.com',
    'telemetry.appex.bing.net:443',
    'vortex-sandbox.data.microsoft.com',
    'settings-sandbox.data.microsoft.com',
    'survey.watson.microsoft.com',
    'watson.live.com',
    'watson.microsoft.com',
    'statsfe2.ws.microsoft.com',
    'statsfe1.ws.microsoft.com',
    'corpext.msitadfs.glbdns2.microsoft.com',
    'compatexchange.cloudapp.net',
    'pre.footprintpredict.com',
    'feedback.windows.com',
    'feedback.microsoft-hohm.com',
    'feedback.search.microsoft.com',
]

TRACKING_DOMAINS_AGGRESSIVE = [
    # ⚠️ CES DOMAINES PEUVENT AFFECTER:
    # - Windows Update (vortex.data.microsoft.com)
    # - Microsoft Store
    # - Certaines fonctionnalités cloud
    'vortex.data.microsoft.com',
    'vortex-win.data.microsoft.com',
    'redir.metaservices.microsoft.com',
    'choice.microsoft.com',
    'choice.microsoft.com.nsatc.net',
    'cs1.wpc.v0cdn.net',
    'a-0001.a-msedge.net',
    'statsfe2.update.microsoft.com.akadns.net',
    'sls.update.microsoft.com.akadns.net',
    'fe2.update.microsoft.com.akadns.net',
    'diagnostics.support.microsoft.com',
    'corp.sts.microsoft.com',
    'i1.services.social.microsoft.com',
    'i1.services.social.microsoft.com.nsatc.net',
]

# Liste complète (par défaut = SAFE uniquement)
TRACKING_DOMAINS = TRACKING_DOMAINS_SAFE


# PROFILS PRÉDÉFINIS
PROFILES = {
    'gamer': {
        'name': '🎮 Mode Gamer',
        'desc': 'Protège vie privée SANS affecter gaming (Xbox, Game Pass, Store)',
        'categories': ['telemetry'],  # Uniquement télémétrie de base
        'block_hosts': True,
        'aggressive': False,  # Mode Safe uniquement
        'color': '#2196F3'
    },
    'normal': {
        'name': '⚖️ Mode Normal',
        'desc': 'Équilibre entre confidentialité et fonctionnalités (recommandé)',
        'categories': ['telemetry', 'cortana', 'advertising', 'wifi_sense', 'feedback'],
        'block_hosts': True,
        'aggressive': False,  # Mode Safe
        'color': '#4CAF50'
    },
    'ultra_safe': {
        'name': '🔒 Mode Ultra Safe',
        'desc': 'Confidentialité MAXIMALE - Bloque TOUT (peut limiter fonctionnalités)',
        'categories': [
            'telemetry', 'cortana', 'advertising', 'location', 
            'webcam_mic', 'timeline', 'feedback', 'wifi_sense',
            'biometrics', 'app_diagnostics', 'sync_settings'
        ],
        'block_hosts': True,
        'aggressive': True,  # Mode Agressif
        'color': '#F44336'
    }
}


class BackupManager:
    """Gère les sauvegardes et restaurations de configuration"""
    
    @staticmethod
    def get_default_backup_dir():
        """Retourne le dossier de backup par défaut"""
        documents = Path.home() / "Documents"
        backup_dir = documents / "Wapinator" / "Privacy_Backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    @staticmethod
    def create_backup(backup_path=None):
        """Crée une sauvegarde complète de l'état actuel"""
        if backup_path is None:
            backup_dir = BackupManager.get_default_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"privacy_backup_{timestamp}.json"
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'windows_version': BackupManager.get_windows_version(),
            'services': {},
            'registry': {},
            'tasks': {},
            'hosts': BackupManager.backup_hosts()
        }
        
        # Sauvegarder les services
        for category in PRIVACY_CONFIG.values():
            for service in category['services']:
                backup_data['services'][service] = BackupManager.get_service_status(service)
        
        # Sauvegarder le registre
        for category in PRIVACY_CONFIG.values():
            for reg_path, reg_name, _ in category['registry']:
                key = f"{reg_path}\\{reg_name}"
                backup_data['registry'][key] = BackupManager.get_registry_value(reg_path, reg_name)
        
        # Sauvegarder les tâches
        for category in PRIVACY_CONFIG.values():
            for task in category['tasks']:
                backup_data['tasks'][task] = BackupManager.get_task_status(task)
        
        # Écrire le fichier JSON
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return backup_path
    
    @staticmethod
    def restore_backup(backup_path):
        """Restaure une sauvegarde"""
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        results = {
            'success': [],
            'failed': []
        }
        
        # Restaurer les services
        for service_name, service_data in backup_data['services'].items():
            if service_data and BackupManager.restore_service(service_name, service_data):
                results['success'].append(f"Service {service_name}")
            else:
                results['failed'].append(f"Service {service_name}")
        
        # Restaurer le registre
        for key, reg_data in backup_data['registry'].items():
            if reg_data and BackupManager.restore_registry(key, reg_data):
                results['success'].append(f"Registre {key}")
            else:
                results['failed'].append(f"Registre {key}")
        
        # Restaurer les tâches
        for task_path, task_data in backup_data['tasks'].items():
            if task_data and BackupManager.restore_task(task_path, task_data):
                results['success'].append(f"Tâche {task_path}")
            else:
                results['failed'].append(f"Tâche {task_path}")
        
        # Restaurer hosts
        if BackupManager.restore_hosts(backup_data['hosts']):
            results['success'].append("Fichier hosts")
        else:
            results['failed'].append("Fichier hosts")
        
        return results
    
    @staticmethod
    def get_windows_version():
        """Récupère la version de Windows"""
        try:
            result = subprocess.run(
                ['ver'],
                capture_output=True,
                text=True,
                shell=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            return result.stdout.strip()
        except:
            return "Unknown"
    
    @staticmethod
    def get_service_status(service_name):
        """Récupère l'état d'un service"""
        try:
            result = subprocess.run(
                ['sc', 'query', service_name],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if result.returncode != 0:
                return None
            
            status = "stopped"
            if "RUNNING" in result.stdout:
                status = "running"
            
            # Récupérer le type de démarrage
            config_result = subprocess.run(
                ['sc', 'qc', service_name],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            start_type = "auto"
            if "DISABLED" in config_result.stdout:
                start_type = "disabled"
            elif "DEMAND" in config_result.stdout:
                start_type = "manual"
            
            return {
                'status': status,
                'start_type': start_type
            }
        except:
            return None
    
    @staticmethod
    def get_registry_value(path, name):
        """Récupère une valeur du registre"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                path,
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
            value, reg_type = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            
            return {
                'value': value,
                'type': reg_type
            }
        except:
            return None
    
    @staticmethod
    def get_task_status(task_path):
        """Récupère l'état d'une tâche planifiée"""
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', task_path, '/FO', 'LIST'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if result.returncode != 0:
                return None
            
            status = "enabled"
            if "Disabled" in result.stdout or "Désactivé" in result.stdout:
                status = "disabled"
            
            return {'status': status}
        except:
            return None
    
    @staticmethod
    def backup_hosts():
        """Sauvegarde le fichier hosts"""
        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extraire uniquement les lignes Wapinator
            wapinator_lines = []
            for line in content.split('\n'):
                if 'Wapinator' in line or (line.strip() and any(domain in line for domain in TRACKING_DOMAINS_SAFE + TRACKING_DOMAINS_AGGRESSIVE)):
                    wapinator_lines.append(line)
            
            return {
                'full_content': content,
                'wapinator_lines': wapinator_lines
            }
        except:
            return None
    
    @staticmethod
    def restore_service(service_name, service_data):
        """Restaure un service"""
        try:
            # Changer le type de démarrage
            start_type_map = {
                'auto': 'auto',
                'manual': 'demand',
                'disabled': 'disabled'
            }
            start_type = start_type_map.get(service_data['start_type'], 'auto')
            
            subprocess.run(
                ['sc', 'config', service_name, f'start={start_type}'],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            # Démarrer le service si nécessaire
            if service_data['status'] == 'running':
                subprocess.run(
                    ['sc', 'start', service_name],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
            
            return True
        except:
            return False
    
    @staticmethod
    def restore_registry(key_path, reg_data):
        """Restaure une valeur du registre"""
        try:
            path, name = key_path.rsplit('\\', 1)
            
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    path,
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                )
            except FileNotFoundError:
                key = winreg.CreateKeyEx(
                    winreg.HKEY_LOCAL_MACHINE,
                    path,
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                )
            
            winreg.SetValueEx(key, name, 0, reg_data['type'], reg_data['value'])
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    @staticmethod
    def restore_task(task_path, task_data):
        """Restaure une tâche planifiée"""
        try:
            if task_data['status'] == 'enabled':
                subprocess.run(
                    ['schtasks', '/Change', '/TN', task_path, '/ENABLE'],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
            return True
        except:
            return False
    
    @staticmethod
    def restore_hosts(hosts_data):
        """Restaure le fichier hosts"""
        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
            
            # Lire le contenu actuel
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                current_content = f.read()
            
            # Supprimer toutes les lignes Wapinator
            lines = current_content.split('\n')
            cleaned_lines = []
            skip_section = False
            
            for line in lines:
                if '# Wapinator' in line:
                    skip_section = True
                    continue
                
                if skip_section:
                    # Vérifier si c'est une ligne de domaine bloqué
                    if any(domain in line for domain in TRACKING_DOMAINS_SAFE + TRACKING_DOMAINS_AGGRESSIVE):
                        continue
                    else:
                        skip_section = False
                
                if not skip_section:
                    cleaned_lines.append(line)
            
            # Écrire le fichier nettoyé
            with open(hosts_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned_lines))
            
            # Flush DNS
            subprocess.run(
                ['ipconfig', '/flushdns'],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            return True
        except:
            return False


class PrivacyWorker(QThread):
    """Worker thread pour appliquer les modifications"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, selected_categories, block_hosts, aggressive_mode=False):
        super().__init__()
        self.selected_categories = selected_categories
        self.block_hosts = block_hosts
        self.aggressive_mode = aggressive_mode
        self.success_count = 0
        self.fail_count = 0
    
    def run(self):
        try:
            total_steps = len(self.selected_categories)
            if self.block_hosts:
                total_steps += 1
            
            current_step = 0
            
            # Appliquer chaque catégorie sélectionnée
            for category_id in self.selected_categories:
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                self.progress_signal.emit(progress)
                
                self.apply_category(category_id)
            
            # Bloquer les domaines si demandé
            if self.block_hosts:
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                self.progress_signal.emit(progress)
                self.block_tracking_domains()
            
            # Résumé final
            self.log_signal.emit("\n" + "="*60)
            self.log_signal.emit("✅ OPÉRATION TERMINÉE")
            self.log_signal.emit(f"Succès: {self.success_count} | Échecs: {self.fail_count}")
            self.log_signal.emit("="*60)
            
            # Recommandations
            self.log_signal.emit("\n💡 RECOMMANDATIONS:")
            self.log_signal.emit("• Redémarrez Windows pour appliquer tous les changements")
            self.log_signal.emit("• Vérifiez Paramètres > Confidentialité pour confirmer")
            self.log_signal.emit("• Certains changements nécessitent Windows Pro/Enterprise")
            
            self.finished_signal.emit(True, "Modifications appliquées avec succès!")
            
        except Exception as e:
            self.log_signal.emit(f"\n❌ ERREUR CRITIQUE: {str(e)}")
            self.finished_signal.emit(False, f"Erreur: {str(e)}")
    
    def apply_category(self, category_id):
        """Applique les modifications pour une catégorie"""
        config = PRIVACY_CONFIG[category_id]
        self.log_signal.emit(f"\n{'='*60}")
        self.log_signal.emit(f"{config['name']}")
        self.log_signal.emit(f"{'='*60}")
        
        # Désactiver les services
        if config['services']:
            self.log_signal.emit("\n🔧 Services à désactiver:")
            for service in config['services']:
                if self.disable_service(service):
                    self.success_count += 1
                else:
                    self.fail_count += 1
        
        # Modifier le registre
        if config['registry']:
            self.log_signal.emit("\n📝 Modifications registre:")
            for reg_path, reg_name, reg_value in config['registry']:
                if self.set_registry(reg_path, reg_name, reg_value):
                    self.success_count += 1
                else:
                    self.fail_count += 1
        
        # Désactiver les tâches planifiées
        if config['tasks']:
            self.log_signal.emit("\n📅 Tâches planifiées à désactiver:")
            for task in config['tasks']:
                if self.disable_task(task):
                    self.success_count += 1
                else:
                    self.fail_count += 1
    
    def disable_service(self, service_name):
        """Désactive un service Windows"""
        try:
            # Arrêter le service
            subprocess.run(
                ['sc', 'stop', service_name],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            # Désactiver le service
            result = subprocess.run(
                ['sc', 'config', service_name, 'start=disabled'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if result.returncode == 0 or "SUCCESS" in result.stdout:
                self.log_signal.emit(f"  ✅ Service '{service_name}' désactivé")
                return True
            else:
                self.log_signal.emit(f"  ⚠️ Service '{service_name}' non trouvé ou déjà désactivé")
                return True  # Pas vraiment une erreur
                
        except Exception as e:
            self.log_signal.emit(f"  ❌ Échec service '{service_name}': {str(e)}")
            return False
    
    def set_registry(self, path, name, value):
        """Modifie une valeur dans le registre"""
        try:
            # Déterminer le type de valeur
            if isinstance(value, int):
                reg_type = winreg.REG_DWORD
            elif isinstance(value, str):
                reg_type = winreg.REG_SZ
            else:
                reg_type = winreg.REG_DWORD
            
            # Ouvrir/créer la clé
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    path,
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                )
            except FileNotFoundError:
                # Créer la clé si elle n'existe pas
                key = winreg.CreateKeyEx(
                    winreg.HKEY_LOCAL_MACHINE,
                    path,
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                )
            
            # Définir la valeur
            winreg.SetValueEx(key, name, 0, reg_type, value)
            winreg.CloseKey(key)
            
            self.log_signal.emit(f"  ✅ Registre: {name} = {value}")
            return True
            
        except PermissionError:
            self.log_signal.emit(f"  ❌ Permission refusée pour {name} (nécessite admin)")
            return False
        except Exception as e:
            self.log_signal.emit(f"  ❌ Échec registre {name}: {str(e)}")
            return False
    
    def disable_task(self, task_path):
        """Désactive une tâche planifiée"""
        try:
            result = subprocess.run(
                ['schtasks', '/Change', '/TN', task_path, '/DISABLE'],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            if result.returncode == 0 or "SUCCESS" in result.stdout:
                task_name = task_path.split('\\')[-1]
                self.log_signal.emit(f"  ✅ Tâche '{task_name}' désactivée")
                return True
            else:
                task_name = task_path.split('\\')[-1]
                self.log_signal.emit(f"  ⚠️ Tâche '{task_name}' non trouvée")
                return True  # Pas vraiment une erreur
                
        except Exception as e:
            self.log_signal.emit(f"  ❌ Échec tâche: {str(e)}")
            return False
    
    def block_tracking_domains(self):
        """Bloque les domaines de tracking dans le fichier hosts"""
        self.log_signal.emit(f"\n{'='*60}")
        if self.aggressive_mode:
            self.log_signal.emit("🚫 BLOCAGE DOMAINES (MODE AGRESSIF)")
            self.log_signal.emit("⚠️  ATTENTION: Peut affecter Windows Update et Microsoft Store")
            domains_to_block = TRACKING_DOMAINS_SAFE + TRACKING_DOMAINS_AGGRESSIVE
        else:
            self.log_signal.emit("🚫 BLOCAGE DOMAINES (MODE SAFE)")
            self.log_signal.emit("✅ Mode recommandé - N'affecte pas les fonctionnalités")
            domains_to_block = TRACKING_DOMAINS_SAFE
        
        self.log_signal.emit(f"{'='*60}\n")
        
        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
            
            # Lire le fichier hosts actuel
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                hosts_content = f.read()
            
            # Vérifier combien de domaines sont déjà bloqués
            already_blocked = sum(1 for domain in domains_to_block if domain in hosts_content)
            
            if already_blocked == len(domains_to_block):
                self.log_signal.emit(f"✅ Tous les domaines ({len(domains_to_block)}) sont déjà bloqués")
                self.success_count += 1
                return True
            
            # Ajouter les nouveaux domaines
            new_domains = []
            for domain in domains_to_block:
                if domain not in hosts_content:
                    new_domains.append(domain)
            
            if new_domains:
                # Ajouter un en-tête si nécessaire
                mode_label = "Aggressive" if self.aggressive_mode else "Safe"
                header = f"\n\n# Wapinator - Blocage Tracking Microsoft ({mode_label})\n"
                if header not in hosts_content:
                    hosts_content += header
                
                # Ajouter les nouveaux domaines
                for domain in new_domains:
                    hosts_content += f"0.0.0.0 {domain}\n"
                
                # Écrire le fichier
                with open(hosts_path, 'w', encoding='utf-8') as f:
                    f.write(hosts_content)
                
                self.log_signal.emit(f"✅ {len(new_domains)} nouveaux domaines bloqués")
                self.log_signal.emit(f"   Total: {len(domains_to_block)} domaines dans le fichier hosts")
                
                # Flush DNS
                self.log_signal.emit("\n🔄 Actualisation DNS...")
                subprocess.run(
                    ['ipconfig', '/flushdns'],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                self.log_signal.emit("✅ Cache DNS vidé")
                
                self.success_count += 1
                return True
            else:
                self.log_signal.emit("✅ Aucun nouveau domaine à ajouter")
                self.success_count += 1
                return True
                
        except PermissionError:
            self.log_signal.emit("❌ Permission refusée - Lancez Wapinator en administrateur")
            self.fail_count += 1
            return False
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.fail_count += 1
            return False


class ScanWorker(QThread):
    """Worker pour scanner l'état actuel de confidentialité"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        results = {}
        
        self.log_signal.emit("🔍 SCAN DE LA CONFIDENTIALITÉ EN COURS...")
        self.log_signal.emit("="*60 + "\n")
        
        for category_id, config in PRIVACY_CONFIG.items():
            self.log_signal.emit(f"\n{config['name']}")
            self.log_signal.emit("-" * 40)
            
            enabled_count = 0
            total_count = 0
            
            # Vérifier services
            for service in config['services']:
                total_count += 1
                if self.check_service(service):
                    enabled_count += 1
                    self.log_signal.emit(f"  🔴 Service '{service}' ACTIF")
                else:
                    self.log_signal.emit(f"  ✅ Service '{service}' désactivé")
            
            # Vérifier registre
            for reg_path, reg_name, expected_value in config['registry']:
                total_count += 1
                current_value = self.check_registry(reg_path, reg_name)
                if current_value != expected_value:
                    enabled_count += 1
                    self.log_signal.emit(f"  🔴 Registre '{reg_name}' = {current_value} (attendu: {expected_value})")
                else:
                    self.log_signal.emit(f"  ✅ Registre '{reg_name}' correctement configuré")
            
            # Vérifier tâches
            for task in config['tasks']:
                total_count += 1
                if self.check_task(task):
                    enabled_count += 1
                    task_name = task.split('\\')[-1]
                    self.log_signal.emit(f"  🔴 Tâche '{task_name}' ACTIVE")
                else:
                    task_name = task.split('\\')[-1]
                    self.log_signal.emit(f"  ✅ Tâche '{task_name}' désactivée")
            
            # Calculer le score
            if total_count > 0:
                privacy_score = int(((total_count - enabled_count) / total_count) * 100)
            else:
                privacy_score = 100
            
            results[category_id] = {
                'score': privacy_score,
                'enabled': enabled_count,
                'total': total_count
            }
            
            # Afficher le score
            if privacy_score >= 80:
                emoji = "✅"
                status = "BON"
            elif privacy_score >= 50:
                emoji = "⚠️"
                status = "MOYEN"
            else:
                emoji = "🔴"
                status = "MAUVAIS"
            
            self.log_signal.emit(f"\n  {emoji} Score confidentialité: {privacy_score}% ({status})")
        
        # Vérifier hosts
        self.log_signal.emit("\n" + "="*60)
        self.log_signal.emit("🚫 FICHIER HOSTS")
        self.log_signal.emit("="*60)
        blocked_count = self.check_hosts()
        total_possible = len(TRACKING_DOMAINS_SAFE) + len(TRACKING_DOMAINS_AGGRESSIVE)
        
        results['hosts'] = {
            'blocked': blocked_count,
            'total': total_possible
        }
        
        self.log_signal.emit(f"\n✅ {blocked_count}/{total_possible} domaines de tracking bloqués")
        self.log_signal.emit(f"   • Mode Safe disponible: {len(TRACKING_DOMAINS_SAFE)} domaines")
        self.log_signal.emit(f"   • Mode Agressif disponible: +{len(TRACKING_DOMAINS_AGGRESSIVE)} domaines")
        
        # Score global
        self.log_signal.emit("\n" + "="*60)
        total_score = sum(r['score'] for r in results.values() if 'score' in r) / len([r for r in results.values() if 'score' in r])
        
        if total_score >= 80:
            emoji = "✅"
            status = "EXCELLENTE"
        elif total_score >= 60:
            emoji = "⚠️"
            status = "MOYENNE"
        else:
            emoji = "🔴"
            status = "FAIBLE"
        
        self.log_signal.emit(f"{emoji} CONFIDENTIALITÉ GLOBALE: {int(total_score)}% ({status})")
        self.log_signal.emit("="*60)
        
        self.finished_signal.emit(results)
    
    def check_service(self, service_name):
        """Vérifie si un service est actif"""
        try:
            result = subprocess.run(
                ['sc', 'query', service_name],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            return "RUNNING" in result.stdout
        except:
            return False
    
    def check_registry(self, path, name):
        """Lit une valeur du registre"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                path,
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except:
            return None
    
    def check_task(self, task_path):
        """Vérifie si une tâche est active"""
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', task_path],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            # Vérifier si la tâche existe et n'est pas désactivée
            if result.returncode == 0:
                return "Disabled" not in result.stdout and "Désactivé" not in result.stdout
            return False
        except:
            return False
    
    def check_hosts(self):
        """Compte combien de domaines sont bloqués dans hosts"""
        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                hosts_content = f.read()
            
            safe_blocked = sum(1 for domain in TRACKING_DOMAINS_SAFE if domain in hosts_content)
            aggressive_blocked = sum(1 for domain in TRACKING_DOMAINS_AGGRESSIVE if domain in hosts_content)
            total_blocked = safe_blocked + aggressive_blocked
            
            return total_blocked
        except:
            return 0


class PrivacytelemetryWindow(QDialog):
    """Fenêtre principale du module Privacy & Telemetry"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔒 Privacy & Telemetry Manager")
        self.setMinimumSize(1000, 750)
        
        # Variables
        self.scan_results = {}
        self.checkboxes = {}
        self.backup_path = BackupManager.get_default_backup_dir()
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # En-tête
        self.create_header(main_layout)
        
        # Profils prédéfinis
        self.create_profiles_section(main_layout)
        
        # Section Backup/Restore
        self.create_backup_section(main_layout)
        
        # Zone scrollable pour les options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Créer les groupes d'options
        self.create_privacy_options(scroll_layout)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Zone de log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(250)
        self.log_text.setFont(QFont("Consolas", 9))
        main_layout.addWidget(self.log_text)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Boutons d'action
        self.create_action_buttons(main_layout)
        
        self.setLayout(main_layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: white;
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
            QCheckBox {
                spacing: 8px;
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666;
                border-radius: 4px;
                background: #2b2b2b;
            }
            QCheckBox::indicator:checked {
                background: #4CAF50;
                border-color: #4CAF50;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #444;
                color: #0f0;
                font-family: Consolas;
                border-radius: 5px;
            }
            QProgressBar {
                border: 2px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
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
        """)
    
    def create_header(self, layout):
        """Crée l'en-tête"""
        header = QLabel("🔒 PRIVACY & TELEMETRY MANAGER")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Protégez votre vie privée en désactivant le tracking Windows")
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Avertissement
        warning = QLabel("⚠️ Nécessite les droits administrateur | Redémarrage recommandé après modifications")
        warning.setStyleSheet("""
            background: #FF9800;
            color: black;
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 10px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
    
    def create_profiles_section(self, layout):
        """Crée la section des profils prédéfinis"""
        profiles_group = QGroupBox("🎯 PROFILS PRÉDÉFINIS - Configuration en 1 clic")
        profiles_layout = QHBoxLayout()
        
        for profile_id, profile_data in PROFILES.items():
            profile_btn = QPushButton(profile_data['name'])
            profile_btn.setToolTip(profile_data['desc'])
            profile_btn.setFixedHeight(60)
            profile_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {profile_data['color']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {self.darken_color(profile_data['color'])};
                }}
            """)
            profile_btn.clicked.connect(lambda checked, pid=profile_id: self.load_profile(pid))
            profiles_layout.addWidget(profile_btn)
        
        profiles_group.setLayout(profiles_layout)
        profiles_group.setStyleSheet("""
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
        """)
        layout.addWidget(profiles_group)
    
    def create_backup_section(self, layout):
        """Crée la section backup/restore"""
        backup_group = QGroupBox("💾 SAUVEGARDE & RESTAURATION")
        backup_layout = QVBoxLayout()
        
        # Info chemin de backup
        path_layout = QHBoxLayout()
        path_label = QLabel("📁 Dossier de sauvegarde:")
        path_label.setStyleSheet("color: white; font-size: 10px;")
        path_layout.addWidget(path_label)
        
        self.backup_path_label = QLabel(str(self.backup_path))
        self.backup_path_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-family: Consolas;")
        path_layout.addWidget(self.backup_path_label, 1)
        
        change_path_btn = QPushButton("📂 Changer")
        change_path_btn.setFixedWidth(100)
        change_path_btn.clicked.connect(self.change_backup_path)
        change_path_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 9px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        path_layout.addWidget(change_path_btn)
        
        backup_layout.addLayout(path_layout)
        
        # Boutons backup/restore
        buttons_layout = QHBoxLayout()
        
        create_backup_btn = QPushButton("💾 Créer Sauvegarde AVANT modifications")
        create_backup_btn.clicked.connect(self.create_backup)
        create_backup_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover { background: #388E3C; }
        """)
        buttons_layout.addWidget(create_backup_btn)
        
        restore_backup_btn = QPushButton("♻️ Restaurer depuis Sauvegarde")
        restore_backup_btn.clicked.connect(self.restore_backup)
        restore_backup_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover { background: #F57C00; }
        """)
        buttons_layout.addWidget(restore_backup_btn)
        
        backup_layout.addLayout(buttons_layout)
        
        backup_group.setLayout(backup_layout)
        backup_group.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #FF9800;
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
                color: #FF9800;
            }
        """)
        layout.addWidget(backup_group)
    
    def create_privacy_options(self, layout):
        """Crée les groupes d'options de confidentialité"""
        
        # Sévérité HIGH
        high_group = QGroupBox("🔴 PRIORITÉ HAUTE - Tracking intensif")
        high_layout = QVBoxLayout()
        
        # Sévérité MEDIUM  
        medium_group = QGroupBox("🟡 PRIORITÉ MOYENNE - Collecte données")
        medium_layout = QVBoxLayout()
        
        # Sévérité LOW
        low_group = QGroupBox("🟢 PRIORITÉ BASSE - Confort / Fonctionnalités")
        low_layout = QVBoxLayout()
        
        # Répartir les options par sévérité
        for category_id, config in PRIVACY_CONFIG.items():
            checkbox = QCheckBox(f"{config['name']}")
            checkbox.setToolTip(config['desc'])
            
            # Texte descriptif
            desc_label = QLabel(f"   └─ {config['desc']}")
            desc_label.setStyleSheet("color: #888; font-size: 9px; margin-left: 25px;")
            
            self.checkboxes[category_id] = checkbox
            
            if config['severity'] == 'high':
                high_layout.addWidget(checkbox)
                high_layout.addWidget(desc_label)
            elif config['severity'] == 'medium':
                medium_layout.addWidget(checkbox)
                medium_layout.addWidget(desc_label)
            else:
                low_layout.addWidget(checkbox)
                low_layout.addWidget(desc_label)
        
        high_group.setLayout(high_layout)
        medium_group.setLayout(medium_layout)
        low_group.setLayout(low_layout)
        
        layout.addWidget(high_group)
        layout.addWidget(medium_group)
        layout.addWidget(low_group)
        
        # Option hosts
        hosts_group = QGroupBox("🚫 BLOCAGE DOMAINES (fichier hosts)")
        hosts_layout = QVBoxLayout()
        
        self.hosts_checkbox = QCheckBox(f"✅ Bloquer domaines de tracking (Mode Safe - Recommandé)")
        self.hosts_checkbox.setToolTip("Bloque uniquement les domaines de télémétrie pure")
        hosts_layout.addWidget(self.hosts_checkbox)
        
        hosts_info = QLabel(f"   └─ {len(TRACKING_DOMAINS_SAFE)} domaines bloqués (telemetry.microsoft.com, watson.*, etc.)")
        hosts_info.setStyleSheet("color: #888; font-size: 9px; margin-left: 25px;")
        hosts_layout.addWidget(hosts_info)
        
        # Option mode agressif
        self.aggressive_checkbox = QCheckBox("⚠️ Mode Agressif (bloquer domaines supplémentaires)")
        self.aggressive_checkbox.setToolTip("⚠️ Peut affecter Windows Update et Microsoft Store")
        hosts_layout.addWidget(self.aggressive_checkbox)
        
        aggressive_warning = QLabel(f"   └─ ⚠️ +{len(TRACKING_DOMAINS_AGGRESSIVE)} domaines (vortex.data, *.update.microsoft.com)")
        aggressive_warning.setStyleSheet("color: #FF9800; font-size: 9px; margin-left: 25px; font-weight: bold;")
        hosts_layout.addWidget(aggressive_warning)
        
        hosts_group.setLayout(hosts_layout)
        layout.addWidget(hosts_group)
        
        # ⚠️ AVERTISSEMENT GAMERS
        gaming_warning = QLabel(
            "🎮 GAMERS: Les paramètres ci-dessus ne bloquent PAS Xbox Live.\n"
            "   Cependant, si vous utilisez Xbox Game Pass / Microsoft Store,\n"
            "   NE PAS activer le Mode Agressif (peut bloquer téléchargements)."
        )
        gaming_warning.setStyleSheet("""
            background: #2196F3;
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 9px;
            font-weight: bold;
        """)
        layout.addWidget(gaming_warning)
        
        # Boutons de sélection rapide
        select_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("☑️ Tout sélectionner")
        select_all_btn.clicked.connect(self.select_all)
        select_all_btn.setStyleSheet("background: #4CAF50; color: white;")
        
        select_recommended_btn = QPushButton("⭐ Recommandés (Priorité haute)")
        select_recommended_btn.clicked.connect(self.select_recommended)
        select_recommended_btn.setStyleSheet("background: #FF9800; color: white;")
        
        deselect_all_btn = QPushButton("☐ Tout désélectionner")
        deselect_all_btn.clicked.connect(self.deselect_all)
        deselect_all_btn.setStyleSheet("background: #F44336; color: white;")
        
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(select_recommended_btn)
        select_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(select_layout)
    
    def create_action_buttons(self, layout):
        """Crée les boutons d'action"""
        button_layout = QHBoxLayout()
        
        # Bouton scan
        scan_btn = QPushButton("🔍 Scanner l'état actuel")
        scan_btn.clicked.connect(self.start_scan)
        scan_btn.setStyleSheet("background: #2196F3; color: white;")
        button_layout.addWidget(scan_btn)
        
        # Bouton appliquer
        self.apply_btn = QPushButton("✅ Appliquer les modifications")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setStyleSheet("background: #4CAF50; color: white;")
        button_layout.addWidget(self.apply_btn)
        
        # Bouton tutoriel
        tutorial_btn = QPushButton("📚 Guide & Explications")
        tutorial_btn.clicked.connect(self.show_tutorial)
        tutorial_btn.setStyleSheet("background: #9C27B0; color: white;")
        button_layout.addWidget(tutorial_btn)
        
        # Bouton fermer
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: #F44336; color: white;")
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def select_all(self):
        """Sélectionne toutes les options"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
        self.hosts_checkbox.setChecked(True)
        # Ne PAS activer mode agressif par défaut
    
    def select_recommended(self):
        """Sélectionne les options recommandées (priorité haute)"""
        for category_id, checkbox in self.checkboxes.items():
            if PRIVACY_CONFIG[category_id]['severity'] == 'high':
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)
        self.hosts_checkbox.setChecked(True)
        self.aggressive_checkbox.setChecked(False)  # Mode safe recommandé
    
    def deselect_all(self):
        """Désélectionne toutes les options"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
        self.hosts_checkbox.setChecked(False)
        self.aggressive_checkbox.setChecked(False)
    
    def start_scan(self):
        """Lance le scan de confidentialité"""
        self.log_text.clear()
        self.apply_btn.setEnabled(False)
        
        # Démarrer le worker
        self.scan_worker = ScanWorker()
        self.scan_worker.log_signal.connect(self.append_log)
        self.scan_worker.finished_signal.connect(self.scan_finished)
        self.scan_worker.start()
    
    def scan_finished(self, results):
        """Appelé quand le scan est terminé"""
        self.scan_results = results
        self.apply_btn.setEnabled(True)
        self.append_log("\n✅ Scan terminé ! Vous pouvez maintenant appliquer les modifications.")
    
    def apply_changes(self):
        """Applique les modifications sélectionnées"""
        # Vérifier qu'au moins une option est sélectionnée
        selected_categories = [
            cat_id for cat_id, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]
        
        if not selected_categories and not self.hosts_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "⚠️ Aucune option",
                "Veuillez sélectionner au moins une option à appliquer."
            )
            return
        
        # Avertissement mode agressif
        aggressive_warning = ""
        if self.hosts_checkbox.isChecked() and self.aggressive_checkbox.isChecked():
            aggressive_warning = "\n⚠️ MODE AGRESSIF ACTIVÉ:\n   Peut affecter Windows Update et Microsoft Store!"
        
        # Demander confirmation
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation",
            f"Êtes-vous sûr de vouloir appliquer ces modifications?\n\n"
            f"• {len(selected_categories)} catégories sélectionnées\n"
            f"• Blocage hosts: {'Oui' if self.hosts_checkbox.isChecked() else 'Non'}\n"
            f"• Mode: {'Agressif' if self.aggressive_checkbox.isChecked() else 'Safe (Recommandé)'}"
            f"{aggressive_warning}\n\n"
            f"⚠️ Nécessite droits administrateur\n"
            f"💡 Redémarrage recommandé après",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Démarrer l'application
        self.log_text.clear()
        self.apply_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Démarrer le worker avec le mode agressif
        self.privacy_worker = PrivacyWorker(
            selected_categories,
            self.hosts_checkbox.isChecked(),
            self.aggressive_checkbox.isChecked()  # Mode agressif
        )
        self.privacy_worker.log_signal.connect(self.append_log)
        self.privacy_worker.progress_signal.connect(self.update_progress)
        self.privacy_worker.finished_signal.connect(self.apply_finished)
        self.privacy_worker.start()
    
    def apply_finished(self, success, message):
        """Appelé quand l'application est terminée"""
        self.apply_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(
                self,
                "✅ Succès",
                f"{message}\n\n"
                f"💡 Redémarrez Windows pour appliquer tous les changements.\n\n"
                f"Vous pouvez relancer un scan pour vérifier."
            )
        else:
            QMessageBox.warning(
                self,
                "⚠️ Erreur",
                f"{message}\n\n"
                f"Vérifiez que Wapinator est lancé en administrateur."
            )
    
    def update_progress(self, value):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
    
    def append_log(self, text):
        """Ajoute du texte au log"""
        self.log_text.append(text)
        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def load_profile(self, profile_id):
        """Charge un profil prédéfini"""
        profile = PROFILES[profile_id]
        
        # Confirmation
        reply = QMessageBox.question(
            self,
            f"🎯 Charger {profile['name']}",
            f"{profile['desc']}\n\n"
            f"Catégories: {len(profile['categories'])}\n"
            f"Blocage hosts: {'Oui' if profile['block_hosts'] else 'Non'}\n"
            f"Mode: {'Agressif' if profile['aggressive'] else 'Safe'}\n\n"
            f"Charger cette configuration?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Désélectionner tout
        self.deselect_all()
        
        # Sélectionner les catégories du profil
        for category_id in profile['categories']:
            if category_id in self.checkboxes:
                self.checkboxes[category_id].setChecked(True)
        
        # Configurer hosts
        self.hosts_checkbox.setChecked(profile['block_hosts'])
        self.aggressive_checkbox.setChecked(profile['aggressive'])
        
        # Message de confirmation
        self.append_log(f"\n✅ Profil '{profile['name']}' chargé avec succès!")
        self.append_log(f"   • {len(profile['categories'])} catégories sélectionnées")
        self.append_log(f"   • Blocage hosts: {'Oui' if profile['block_hosts'] else 'Non'}")
        self.append_log(f"   • Mode: {'Agressif' if profile['aggressive'] else 'Safe'}")
    
    def change_backup_path(self):
        """Change le dossier de sauvegarde"""
        new_path = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier de sauvegarde",
            str(self.backup_path)
        )
        
        if new_path:
            self.backup_path = Path(new_path)
            self.backup_path_label.setText(str(self.backup_path))
            self.append_log(f"\n📁 Dossier de sauvegarde changé: {self.backup_path}")
    
    def create_backup(self):
        """Crée une sauvegarde de l'état actuel"""
        reply = QMessageBox.question(
            self,
            "💾 Créer Sauvegarde",
            "Créer une sauvegarde de l'état actuel?\n\n"
            "La sauvegarde contiendra:\n"
            "• État des services (DiagTrack, etc.)\n"
            "• Valeurs du registre\n"
            "• État des tâches planifiées\n"
            "• Contenu du fichier hosts\n\n"
            "💡 Recommandé AVANT toute modification!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        try:
            self.log_text.clear()
            self.append_log("💾 CRÉATION SAUVEGARDE EN COURS...")
            self.append_log("="*60)
            
            # Créer la sauvegarde
            backup_file = BackupManager.create_backup(self.backup_path / f"privacy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            self.append_log(f"✅ Sauvegarde créée avec succès!")
            self.append_log(f"📁 Emplacement: {backup_file}")
            self.append_log(f"📊 Taille: {backup_file.stat().st_size / 1024:.2f} Ko")
            self.append_log("="*60)
            self.append_log("\n💡 Vous pouvez maintenant appliquer des modifications en toute sécurité.")
            
            QMessageBox.information(
                self,
                "✅ Sauvegarde Créée",
                f"Sauvegarde créée avec succès!\n\n"
                f"Fichier: {backup_file.name}\n"
                f"Emplacement: {backup_file.parent}\n\n"
                f"Utilisez 'Restaurer' pour revenir à cet état."
            )
            
        except Exception as e:
            self.append_log(f"\n❌ ERREUR: {str(e)}")
            QMessageBox.critical(
                self,
                "❌ Erreur",
                f"Impossible de créer la sauvegarde:\n{str(e)}\n\n"
                f"Vérifiez que Wapinator est lancé en administrateur."
            )
    
    def restore_backup(self):
        """Restaure depuis une sauvegarde"""
        # Sélectionner le fichier de sauvegarde
        backup_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une sauvegarde",
            str(self.backup_path),
            "Fichiers JSON (*.json)"
        )
        
        if not backup_file:
            return
        
        try:
            # Lire les infos de la sauvegarde
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            timestamp = datetime.fromisoformat(backup_data['timestamp'])
            
            # Confirmation
            reply = QMessageBox.question(
                self,
                "♻️ Restaurer Sauvegarde",
                f"Restaurer cette sauvegarde?\n\n"
                f"📅 Date: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"🖥️ Version: {backup_data['windows_version']}\n\n"
                f"⚠️ ATTENTION: Cela va:\n"
                f"• Réactiver les services\n"
                f"• Restaurer les valeurs du registre\n"
                f"• Réactiver les tâches planifiées\n"
                f"• Nettoyer le fichier hosts\n\n"
                f"💡 Redémarrage recommandé après",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            # Restaurer
            self.log_text.clear()
            self.append_log("♻️ RESTAURATION EN COURS...")
            self.append_log("="*60)
            self.append_log(f"📁 Fichier: {Path(backup_file).name}")
            self.append_log(f"📅 Date sauvegarde: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
            self.append_log("="*60 + "\n")
            
            results = BackupManager.restore_backup(backup_file)
            
            # Afficher les résultats
            self.append_log(f"\n✅ SUCCÈS: {len(results['success'])} éléments restaurés")
            for item in results['success']:
                self.append_log(f"   ✅ {item}")
            
            if results['failed']:
                self.append_log(f"\n❌ ÉCHECS: {len(results['failed'])} éléments")
                for item in results['failed']:
                    self.append_log(f"   ❌ {item}")
            
            self.append_log("\n" + "="*60)
            self.append_log("♻️ RESTAURATION TERMINÉE")
            self.append_log("💡 Redémarrez Windows pour finaliser")
            self.append_log("="*60)
            
            QMessageBox.information(
                self,
                "✅ Restauration Terminée",
                f"Sauvegarde restaurée avec succès!\n\n"
                f"Succès: {len(results['success'])}\n"
                f"Échecs: {len(results['failed'])}\n\n"
                f"💡 Redémarrez Windows pour finaliser."
            )
            
        except Exception as e:
            self.append_log(f"\n❌ ERREUR: {str(e)}")
            QMessageBox.critical(
                self,
                "❌ Erreur",
                f"Impossible de restaurer la sauvegarde:\n{str(e)}\n\n"
                f"Vérifiez que Wapinator est lancé en administrateur."
            )
    
    def darken_color(self, hex_color):
        """Assombrir une couleur hex (nécessaire pour les profils)"""
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        l = max(0, l - 30)
        color.setHsl(h, s, l, a)
        return color.name()
    
    def show_tutorial(self):
        """Affiche le tutoriel détaillé"""
        tutorial_text = """
<h2>🔒 GUIDE PRIVACY & TELEMETRY</h2>

<h3>📋 QU'EST-CE QUE LA TÉLÉMÉTRIE?</h3>
<p>La télémétrie est la collecte automatique de données d'utilisation par Windows.
Microsoft collecte des informations sur:</p>
<ul>
<li>Votre utilisation du système</li>
<li>Les applications installées</li>
<li>Vos habitudes de navigation</li>
<li>Vos données de localisation</li>
<li>Vos recherches et commandes vocales</li>
</ul>

<h3>🎯 PROFILS PRÉDÉFINIS</h3>
<p>Pour simplifier la configuration, 3 profils sont disponibles:</p>

<p><b>🎮 Mode Gamer:</b></p>
<ul>
<li>Protection minimale qui ne bloque PAS Xbox Live, Game Pass, ou Store</li>
<li>Désactive uniquement la télémétrie de base</li>
<li>Idéal pour: Joueurs Xbox, utilisateurs Microsoft Store</li>
</ul>

<p><b>⚖️ Mode Normal (Recommandé):</b></p>
<ul>
<li>Équilibre entre confidentialité et fonctionnalités</li>
<li>Bloque télémétrie, Cortana, publicités, WiFi Sense</li>
<li>Idéal pour: Usage quotidien, la plupart des utilisateurs</li>
</ul>

<p><b>🔒 Mode Ultra Safe:</b></p>
<ul>
<li>Confidentialité MAXIMALE - Bloque absolument tout</li>
<li>Toutes les catégories + Mode Agressif</li>
<li>Peut limiter: Windows Update, Microsoft Store, fonctionnalités cloud</li>
<li>Idéal pour: Paranoïaques de la vie privée, machines isolées</li>
</ul>

<h3>💾 SAUVEGARDE & RESTAURATION</h3>
<p><b>Fortement recommandé:</b> Créez une sauvegarde AVANT toute modification!</p>

<p><b>La sauvegarde inclut:</b></p>
<ul>
<li>État de tous les services (actif/désactivé, type de démarrage)</li>
<li>Toutes les valeurs du registre</li>
<li>État des tâches planifiées</li>
<li>Contenu complet du fichier hosts</li>
</ul>

<p><b>Emplacement par défaut:</b></p>
<code>Documents\\Wapinator\\Privacy_Backups\\</code>

<p><b>Format:</b> Fichier JSON lisible et modifiable</p>

<p><b>Pour restaurer:</b></p>
<ol>
<li>Cliquez "Restaurer depuis Sauvegarde"</li>
<li>Sélectionnez le fichier .json</li>
<li>Confirmez la restauration</li>
<li>Redémarrez Windows</li>
</ol>

<h3>🎯 CATÉGORIES EXPLIQUÉES</h3>

<b>🔴 PRIORITÉ HAUTE (Recommandé):</b>
<ul>
<li><b>Télémétrie Windows:</b> Service principal de collecte de données</li>
<li><b>Cortana/Copilot:</b> Assistant vocal qui enregistre vos commandes</li>
<li><b>Wi-Fi Sense:</b> Partage vos mots de passe Wi-Fi avec vos contacts</li>
</ul>

<b>🟡 PRIORITÉ MOYENNE:</b>
<ul>
<li><b>Publicité:</b> Tracking pour pub personnalisée dans Windows</li>
<li><b>Localisation:</b> Désactive le GPS permanent</li>
<li><b>Feedback:</b> Popups de demande d'avis Microsoft</li>
</ul>

<b>🟢 PRIORITÉ BASSE:</b>
<ul>
<li><b>Caméra/Micro:</b> Accès automatique pour toutes les apps</li>
<li><b>Timeline:</b> Historique de vos activités synchronisé</li>
<li><b>Sync paramètres:</b> Sauvegarde cloud de vos configs</li>
</ul>

<h3>🚫 BLOCAGE DOMAINES (Hosts)</h3>
<p>Modifie le fichier <code>C:\\Windows\\System32\\drivers\\etc\\hosts</code>
pour bloquer au niveau DNS les serveurs de télémétrie Microsoft.</p>

<p><b>Deux modes disponibles:</b></p>
<ul>
<li><b>Mode Safe (Recommandé):</b> Bloque uniquement les domaines de télémétrie pure (~30 domaines)</li>
<li><b>Mode Agressif:</b> Bloque également les domaines liés à Windows Update (~15 domaines supplémentaires)</li>
</ul>

<p><b>Avantages:</b></p>
<ul>
<li>Bloque les connexions réseau directement</li>
<li>Fonctionne pour tous les programmes</li>
<li>Pas de logiciel tiers nécessaire</li>
</ul>

<h3>🎮 AVERTISSEMENT GAMERS / XBOX</h3>
<ul>
<li><b>Xbox Live:</b> Non affecté par les modifications (domaines Xbox exclus)</li>
<li><b>Xbox Game Pass:</b> N'utilisez PAS le Mode Agressif (peut bloquer téléchargements)</li>
<li><b>Microsoft Store:</b> Le Mode Agressif peut empêcher les téléchargements</li>
<li><b>Streaming (Discord/OBS):</b> La catégorie Caméra/Micro bloque uniquement l'accès en arrière-plan</li>
</ul>

<h3>⚠️ PRÉCAUTIONS</h3>
<ul>
<li><b>Droits admin requis:</b> Certaines modifications nécessitent UAC</li>
<li><b>Windows Update:</b> Peut être affecté en Mode Agressif uniquement</li>
<li><b>Microsoft Store:</b> Peut avoir des problèmes en Mode Agressif</li>
<li><b>Redémarrage:</b> Nécessaire pour appliquer tous les changements</li>
<li><b>Windows 10 & 11:</b> Compatible avec les deux versions</li>
</ul>

<h3>🔄 RESTAURATION</h3>
<p>Pour annuler les modifications:</p>
<ol>
<li>Supprimez les lignes Wapinator du fichier hosts</li>
<li>Réactivez les services via services.msc</li>
<li>Restaurez les valeurs registre par défaut</li>
<li>Ou utilisez un point de restauration système</li>
</ol>

<h3>💡 RECOMMANDATIONS</h3>
<ul>
<li>Commencez par la <b>Priorité Haute</b> uniquement</li>
<li>Testez votre système après chaque modification</li>
<li>Créez un point de restauration avant</li>
<li>Gardez Windows Defender actif (pas de télémétrie excessive)</li>
</ul>

<h3>📚 RESSOURCES</h3>
<ul>
<li><a href="https://privacy.microsoft.com">Microsoft Privacy Dashboard</a></li>
<li><a href="https://docs.microsoft.com/windows/privacy/">Windows Privacy Documentation</a></li>
</ul>

<p><b>⚠️ Note:</b> Ces modifications peuvent affecter certaines fonctionnalités
Windows. Utilisez à vos risques et périls.</p>
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("📚 Guide Privacy & Telemetry")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(tutorial_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                min-width: 600px;
                min-height: 400px;
            }
        """)
        msg.exec()


# Point d'entrée pour test standalone
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = PrivacytelemetryWindow(None)
    window.show()
    sys.exit(app.exec())
