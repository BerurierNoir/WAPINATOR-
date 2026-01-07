# modules/temp_monitor.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QMessageBox, QWidget, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from pathlib import Path
import subprocess

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

try:
    import wmi
    WMI_AVAILABLE = True
except:
    WMI_AVAILABLE = False

class TempWidget(QWidget):
    """Widget affichage température"""
    
    def __init__(self, label, icon="🌡️"):
        super().__init__()
        self.label_text = label
        self.icon = icon
        self.temp_value = None
        self.max_temp = None
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Label
        self.name_label = QLabel(f"{icon} {label}")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        
        # Température
        self.temp_label = QLabel("--°C")
        self.temp_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.temp_label)
        
        # Max
        self.max_label = QLabel("Max: --°C")
        self.max_label.setFont(QFont("Segoe UI", 9))
        self.max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.max_label.setStyleSheet("color: #888;")
        layout.addWidget(self.max_label)
        
        # Status
        self.status_label = QLabel("⚪ Non mesuré")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QWidget {
                background: #2b2b2b;
                border: 2px solid #444;
                border-radius: 10px;
                padding: 10px;
            }
        """)
    
    def update_temp(self, temp):
        """Mettre à jour température"""
        if temp is None or temp == 0:
            self.temp_label.setText("--°C")
            self.status_label.setText("⚪ Non disponible")
            self.status_label.setStyleSheet("color: #888;")
            return
        
        self.temp_value = temp
        
        # Mettre à jour max
        if self.max_temp is None or temp > self.max_temp:
            self.max_temp = temp
            self.max_label.setText(f"Max: {self.max_temp:.0f}°C")
        
        # Afficher température
        self.temp_label.setText(f"{temp:.0f}°C")
        
        # Déterminer couleur et status
        if temp < 50:
            color = "#4CAF50"
            status = "🟢 Normal"
        elif temp < 70:
            color = "#8BC34A"
            status = "🟢 Correct"
        elif temp < 80:
            color = "#FF9800"
            status = "🟡 Chaud"
        elif temp < 90:
            color = "#FF5722"
            status = "🟠 Très chaud"
        else:
            color = "#F44336"
            status = "🔴 CRITIQUE"
        
        self.temp_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def reset_max(self):
        """Réinitialiser max"""
        self.max_temp = self.temp_value
        if self.max_temp:
            self.max_label.setText(f"Max: {self.max_temp:.0f}°C")

class TempmonitorWindow(QDialog):
    """Fenêtre moniteur températures"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🌡️ Moniteur de Températures")
        self.setMinimumSize(900, 700)
        
        self.monitoring = False
        self.temp_history = {
            'cpu': [],
            'gpu': [],
            'disk': []
        }
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🌡️ MONITEUR DE TEMPÉRATURES EN TEMPS RÉEL")
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
            "Surveillance en temps réel des températures CPU, GPU, Disques • Alertes si surchauffe"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Widgets températures
        temp_grid = QGridLayout()
        temp_grid.setSpacing(15)
        
        self.cpu_widget = TempWidget("CPU", "🔥")
        temp_grid.addWidget(self.cpu_widget, 0, 0)
        
        self.gpu_widget = TempWidget("GPU", "🎮")
        temp_grid.addWidget(self.gpu_widget, 0, 1)
        
        self.disk_widget = TempWidget("Disque", "💾")
        temp_grid.addWidget(self.disk_widget, 0, 2)
        
        layout.addLayout(temp_grid)
        
        # Boutons contrôle
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Démarrer Surveillance")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setStyleSheet("background: #4CAF50; padding: 12px; font-size: 12px;")
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background: #F44336;")
        control_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser Max")
        self.reset_btn.clicked.connect(self.reset_max_temps)
        control_layout.addWidget(self.reset_btn)
        
        layout.addLayout(control_layout)
        
        # Boutons actions
        action_layout = QHBoxLayout()
        
        stress_btn = QPushButton("🔥 Stress Test")
        stress_btn.clicked.connect(self.show_stress_test_guide)
        action_layout.addWidget(stress_btn)
        
        cooling_btn = QPushButton("❄️ Conseils Refroidissement")
        cooling_btn.clicked.connect(self.show_cooling_tips)
        action_layout.addWidget(cooling_btn)
        
        layout.addLayout(action_layout)
        
        # Zone logs
        logs_label = QLabel("📊 Historique & Alertes")
        logs_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(logs_label)
        
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFont(QFont("Consolas", 9))
        self.logs.setMaximumHeight(200)
        layout.addWidget(self.logs)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Historique")
        export_btn.clicked.connect(self.export_history)
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
        
        # Timer refresh
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_temperatures)
        
        # WMI
        if WMI_AVAILABLE:
            try:
                self.wmi = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                self.ohm_available = True
            except:
                self.wmi = wmi.WMI()
                self.ohm_available = False
        else:
            self.wmi = None
            self.ohm_available = False
        
        self.show_welcome()
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """MONITEUR DE TEMPERATURES - WAPINATOR

Surveillance temps réel des températures CPU, GPU, Disques

LIMITATIONS:
- Windows n'expose pas toujours les capteurs via WMI
- Pour monitoring complet: installer Open Hardware Monitor

TEMPERATURES NORMALES:
CPU: 30-45°C repos, 60-75°C charge, >85°C = CHAUD
GPU: 30-40°C repos, 60-80°C gaming, >85°C = ATTENTION
Disques: 30-45°C normal, >55°C = DANGER

Cliquez "Démarrer Surveillance" pour commencer."""
        self.logs.setPlainText(text)
    
    def start_monitoring(self):
        """Démarrer surveillance"""
        self.monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.logs.clear()
        self.log("Surveillance démarrée")
        self.log("Rafraîchissement toutes les 2 secondes")
        
        self.timer.start(2000)
        self.update_temperatures()
    
    def stop_monitoring(self):
        """Arrêter surveillance"""
        self.monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.timer.stop()
        
        self.log("Surveillance arrêtée")
        self.generate_summary()
    
    def update_temperatures(self):
        """Mettre à jour températures"""
        if not self.monitoring:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # CPU
        cpu_temp = self.get_cpu_temp()
        self.cpu_widget.update_temp(cpu_temp)
        
        if cpu_temp and cpu_temp > 0:
            self.temp_history['cpu'].append((timestamp, cpu_temp))
            
            if cpu_temp > 85:
                self.log(f"ALERTE CPU: {cpu_temp:.0f}°C (> 85°C) - {timestamp}")
        
        # GPU
        gpu_temp = self.get_gpu_temp()
        self.gpu_widget.update_temp(gpu_temp)
        
        if gpu_temp and gpu_temp > 0:
            self.temp_history['gpu'].append((timestamp, gpu_temp))
            
            if gpu_temp > 85:
                self.log(f"ALERTE GPU: {gpu_temp:.0f}°C (> 85°C) - {timestamp}")
        
        # Disque
        disk_temp = self.get_disk_temp()
        self.disk_widget.update_temp(disk_temp)
        
        if disk_temp and disk_temp > 0:
            self.temp_history['disk'].append((timestamp, disk_temp))
            
            if disk_temp > 55:
                self.log(f"ALERTE DISQUE: {disk_temp:.0f}°C (> 55°C) - {timestamp}")
    
    def get_cpu_temp(self):
        """Obtenir température CPU"""
        try:
            if self.ohm_available:
                try:
                    sensors = self.wmi.Sensor()
                    for sensor in sensors:
                        if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                            return float(sensor.Value)
                except:
                    pass
            
            try:
                w = wmi.WMI(namespace="root\\wmi")
                temps = w.MSAcpi_ThermalZoneTemperature()
                
                if temps:
                    temp_k = temps[0].CurrentTemperature / 10.0
                    temp_c = temp_k - 273.15
                    
                    if 20 < temp_c < 120:
                        return temp_c
            except:
                pass
        except:
            pass
        
        return None
    
    def get_gpu_temp(self):
        """Obtenir température GPU"""
        try:
            if self.ohm_available:
                try:
                    sensors = self.wmi.Sensor()
                    for sensor in sensors:
                        if sensor.SensorType == 'Temperature':
                            name_lower = sensor.Name.lower()
                            if any(keyword in name_lower for keyword in ['gpu', 'graphics', 'nvidia', 'amd']):
                                return float(sensor.Value)
                except:
                    pass
            
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader'],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    temp = float(result.stdout.strip())
                    if 20 < temp < 120:
                        return temp
            except:
                pass
        except:
            pass
        
        return None
    
    def get_disk_temp(self):
        """Obtenir température disque"""
        try:
            if self.ohm_available:
                try:
                    sensors = self.wmi.Sensor()
                    for sensor in sensors:
                        if sensor.SensorType == 'Temperature':
                            name_lower = sensor.Name.lower()
                            if any(keyword in name_lower for keyword in ['hdd', 'ssd', 'drive', 'disk']):
                                return float(sensor.Value)
                except:
                    pass
        except:
            pass
        
        return None

    def reset_max_temps(self):
        """Réinitialiser températures max"""
        self.cpu_widget.reset_max()
        self.gpu_widget.reset_max()
        self.disk_widget.reset_max()
        
        self.log("Températures max réinitialisées")
    
    def log(self, message):
        """Ajouter message au log"""
        self.logs.append(message)
        self.logs.verticalScrollBar().setValue(
            self.logs.verticalScrollBar().maximum()
        )
    
    def generate_summary(self):
        """Générer résumé session"""
        self.log("\n" + "=" * 60)
        self.log("RESUME SESSION")
        self.log("=" * 60)
        
        if self.temp_history['cpu']:
            temps = [t for _, t in self.temp_history['cpu']]
            avg = sum(temps) / len(temps)
            max_temp = max(temps)
            
            self.log(f"\nCPU:")
            self.log(f"  Température moyenne: {avg:.1f}°C")
            self.log(f"  Température max: {max_temp:.1f}°C")
            
            if max_temp > 85:
                self.log(f"  SURCHAUFFE détectée !")
            elif max_temp > 75:
                self.log(f"  Température élevée")
            else:
                self.log(f"  Température normale")
        
        if self.temp_history['gpu']:
            temps = [t for _, t in self.temp_history['gpu']]
            avg = sum(temps) / len(temps)
            max_temp = max(temps)
            
            self.log(f"\nGPU:")
            self.log(f"  Température moyenne: {avg:.1f}°C")
            self.log(f"  Température max: {max_temp:.1f}°C")
        
        if self.temp_history['disk']:
            temps = [t for _, t in self.temp_history['disk']]
            avg = sum(temps) / len(temps)
            max_temp = max(temps)
            
            self.log(f"\nDISQUE:")
            self.log(f"  Température moyenne: {avg:.1f}°C")
            self.log(f"  Température max: {max_temp:.1f}°C")
        
        self.log("\n" + "=" * 60)
    
    def show_stress_test_guide(self):
        """Guide stress test"""
        QMessageBox.information(self, "Guide Stress Test", 
            "STRESS TEST CPU: Prime95 (mersenne.org)\n"
            "STRESS TEST GPU: FurMark (geeks3d.com)\n\n"
            "Températures acceptables:\n"
            "CPU: <85°C excellent, 85-95°C limite\n"
            "GPU: <80°C excellent, 80-90°C normal")
    
    def show_cooling_tips(self):
        """Conseils refroidissement"""
        QMessageBox.information(self, "Conseils Refroidissement",
            "1. Nettoyage PC (poussière) : -10 à -20°C\n"
            "2. Pâte thermique (si >3 ans) : -5 à -15°C\n"
            "3. Ventilation boîtier\n"
            "4. Positionnement PC (pas contre mur)\n\n"
            "Solutions extrêmes:\n"
            "- Ventirad CPU upgrade (30-60€)\n"
            "- Watercooling AIO (80-150€)")
    
    def show_help(self):
        """Aide"""
        QMessageBox.information(self, "Aide",
            "Cet outil lit les températures via WMI.\n\n"
            "LIMITATIONS: Nécessite capteurs supportés\n"
            "Pour monitoring complet: HWiNFO64\n\n"
            "COULEURS:\n"
            "Vert (<70°C): Normal\n"
            "Orange (80-90°C): Chaud\n"
            "Rouge (>90°C): CRITIQUE")
    
    def export_history(self):
        """Exporter historique"""
        if not any(self.temp_history.values()):
            QMessageBox.warning(self, "Erreur", "Aucun historique à exporter")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Temp_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("HISTORIQUE TEMPERATURES - WAPINATOR\n")
                f.write(f"Généré: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                
                for component in ['cpu', 'gpu', 'disk']:
                    if self.temp_history[component]:
                        temps = [t for _, t in self.temp_history[component]]
                        f.write(f"{component.upper()}:\n")
                        f.write(f"  Moyenne: {sum(temps)/len(temps):.1f}°C\n")
                        f.write(f"  Max: {max(temps):.1f}°C\n\n")
            
            QMessageBox.information(self, "Exporté", f"Sauvegardé: {filename.name}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {str(e)}")
    
    def closeEvent(self, event):
        """Fermeture"""
        if self.monitoring:
            self.stop_monitoring()
        event.accept()