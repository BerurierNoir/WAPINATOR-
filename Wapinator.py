import sys
import subprocess
import threading
import ctypes
import os
import shutil
import webbrowser
from pathlib import Path
from datetime import datetime
from collections import deque

import wmi
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QSlider, QDialog, QMessageBox,
    QProgressBar, QToolTip, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QCursor, QPalette, QColor, QClipboard


# ============ FLAGS ANTI-FENÊTRE CMD ============
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = subprocess.SW_HIDE
else:
    CREATE_NO_WINDOW = 0
    STARTUPINFO = None

# ============ UTILITAIRES ============
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# ============ WORKER THREAD POUR TÂCHES LONGUES ============
class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    
    def __init__(self, task_type):
        super().__init__()
        self.task_type = task_type
        
    def run(self):
        try:
            if self.task_type == "cleanup":
                self.cleanup_windows()
            elif self.task_type == "repair":
                self.repair_windows()
            elif self.task_type == "update":
                self.update_programs()
            elif self.task_type == "network":
                self.network_test()
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit("Erreur")
    
    def run_cmd(self, cmd):
        self.log_signal.emit(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}\n")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",  # UTF-8 avec gestion d'erreurs
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO
            )
            
            last_line = ""
            for line in process.stdout:
                # Nettoyer les caractères problématiques
                line = line.strip()
                
                # Remplacer les caractères bizarres courants
                replacements = {
                    'Ú': 'é',
                    'á': 'à',
                    'Ó': 'à',
                    '‚': 'é',
                    '…': 'à',
                    '\x84': 'ä',
                    '\x8a': 'è',
                    '\x82': 'é',
                }
                
                for bad, good in replacements.items():
                    line = line.replace(bad, good)
                
                # Filtrer les lignes vides ou inutiles
                if not line:
                    continue
                
                # Filtrer les lignes redondantes
                if line == last_line:
                    continue
                
                # Filtrer certains messages inutiles de Windows
                skip_keywords = [
                    "Microsoft (R)",
                    "Copyright (c)",
                    "Tous droits",
                    "All rights reserved"
                ]
                if any(keyword in line for keyword in skip_keywords):
                    continue
                
                # Afficher la ligne nettoyée
                self.log_signal.emit(line)
                last_line = line
            
            process.wait()
            return process.returncode
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {e}")
            return -1
    
    def cleanup_windows(self):
        self.log_signal.emit("╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*12 + "🧹 NETTOYAGE WINDOWS" + " "*16 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝\n")
        
        cleaned_size = 0
        cleaned_files = 0
        
        # Fichiers temporaires
        self.log_signal.emit("📁 ÉTAPE 1/4 : Fichiers temporaires")
        self.log_signal.emit("─" * 50)
        
        temp_paths = [
            (os.environ.get('TEMP'), "Temp utilisateur"),
            (os.environ.get('TMP'), "Tmp utilisateur"),
            (r"C:\Windows\Temp", "Temp Windows")
        ]
        
        for temp_path, label in temp_paths:
            if temp_path and os.path.exists(temp_path):
                try:
                    file_count = 0
                    size_freed = 0
                    
                    for item in os.listdir(temp_path):
                        item_path = os.path.join(temp_path, item)
                        try:
                            if os.path.isfile(item_path):
                                size = os.path.getsize(item_path)
                                os.remove(item_path)
                                size_freed += size
                                file_count += 1
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                file_count += 1
                        except:
                            pass
                    
                    cleaned_size += size_freed
                    cleaned_files += file_count
                    
                    if file_count > 0:
                        self.log_signal.emit(f"  ✓ {label}: {file_count} éléments ({size_freed/(1024**2):.1f} Mo)")
                    else:
                        self.log_signal.emit(f"  ○ {label}: Déjà propre")
                except:
                    self.log_signal.emit(f"  ✗ {label}: Accès refusé")
        
        # Corbeille
        self.log_signal.emit("\n🗑️  ÉTAPE 2/4 : Corbeille")
        self.log_signal.emit("─" * 50)
        ret = self.run_cmd(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
        if ret == 0:
            self.log_signal.emit("  ✓ Corbeille vidée")
        
        # Cache DNS
        self.log_signal.emit("\n🌐 ÉTAPE 3/4 : Cache DNS")
        self.log_signal.emit("─" * 50)
        ret = self.run_cmd(["ipconfig", "/flushdns"])
        if ret == 0:
            self.log_signal.emit("  ✓ Cache DNS nettoyé")
        
        # Windows Update (optionnel)
        self.log_signal.emit("\n📦 ÉTAPE 4/4 : Cache Windows Update")
        self.log_signal.emit("─" * 50)
        self.log_signal.emit("  → Arrêt des services...")
        self.run_cmd(["net", "stop", "wuauserv"])
        self.run_cmd(["net", "stop", "bits"])
        
        wu_cache = r"C:\Windows\SoftwareDistribution\Download"
        if os.path.exists(wu_cache):
            try:
                shutil.rmtree(wu_cache)
                os.makedirs(wu_cache)
                self.log_signal.emit("  ✓ Cache WU nettoyé")
            except:
                self.log_signal.emit("  ✗ Impossible de nettoyer le cache WU")
        
        self.log_signal.emit("  → Redémarrage des services...")
        self.run_cmd(["net", "start", "wuauserv"])
        self.run_cmd(["net", "start", "bits"])
        
        # Résumé
        self.log_signal.emit("\n" + "╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*15 + "✅ TERMINÉ" + " "*21 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝")
        self.log_signal.emit(f"\n📊 STATISTIQUES:")
        self.log_signal.emit(f"   • Fichiers supprimés: {cleaned_files}")
        self.log_signal.emit(f"   • Espace libéré: {cleaned_size / (1024**3):.2f} Go")
        
        self.finished_signal.emit(f"✅ Nettoyage terminé !\n\n{cleaned_files} fichiers supprimés\n{cleaned_size / (1024**3):.2f} Go libérés")
    
    def repair_windows(self):
        self.log_signal.emit("╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*11 + "🔧 RÉPARATION WINDOWS" + " "*15 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝\n")
        self.log_signal.emit("⚠️  Cette opération peut prendre 15-30 minutes")
        self.log_signal.emit("⏱️  Ne fermez pas cette fenêtre !\n")
        
        # ÉTAPE 1: DISM CheckHealth
        self.log_signal.emit("┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 1/4 : Vérification rapide (DISM Check) │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        ret_check = self.run_cmd(["DISM", "/online", "/cleanup-image", "/CheckHealth"])
        
        if ret_check == 0:
            self.log_signal.emit("✓ Aucune corruption détectée à ce niveau\n")
        else:
            self.log_signal.emit("⚠ Des problèmes potentiels détectés\n")
        
        # ÉTAPE 2: SFC /scannow
        self.log_signal.emit("┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 2/4 : Scan fichiers système (SFC)      │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        self.log_signal.emit("⏱️  Durée estimée: 10-15 minutes\n")
        ret_sfc = self.run_cmd(["sfc", "/scannow"])
        
        # ÉTAPE 3 & 4: Si erreurs détectées
        if ret_sfc != 0:
            self.log_signal.emit("\n⚠️  SFC a détecté des corruptions")
            self.log_signal.emit("→ Lancement de la réparation approfondie...\n")
            
            # DISM RestoreHealth
            self.log_signal.emit("┌" + "─"*48 + "┐")
            self.log_signal.emit("│ ÉTAPE 3/4 : Réparation image (DISM Restore) │")
            self.log_signal.emit("└" + "─"*48 + "┘")
            self.log_signal.emit("⏱️  Durée estimée: 15-20 minutes\n")
            ret_dism = self.run_cmd(["DISM", "/online", "/cleanup-image", "/RestoreHealth"])
            
            if ret_dism == 0:
                self.log_signal.emit("\n✓ Image système réparée avec succès")
            
            # SFC final
            self.log_signal.emit("\n┌" + "─"*48 + "┐")
            self.log_signal.emit("│ ÉTAPE 4/4 : Vérification finale (SFC)       │")
            self.log_signal.emit("└" + "─"*48 + "┘")
            ret_sfc_final = self.run_cmd(["sfc", "/scannow"])
            
            if ret_sfc_final == 0:
                self.log_signal.emit("\n✅ Tous les fichiers système ont été réparés !")
            else:
                self.log_signal.emit("\n⚠️  Certains problèmes persistent")
                self.log_signal.emit("💡 Un redémarrage peut résoudre les problèmes restants")
        else:
            self.log_signal.emit("\n✅ Aucune corruption de fichiers système détectée")
        
        # Résumé final
        self.log_signal.emit("\n" + "╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*15 + "✅ TERMINÉ" + " "*21 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝")
        self.log_signal.emit("\n💡 RECOMMANDATIONS:")
        self.log_signal.emit("   • Redémarrez votre PC pour finaliser")
        self.log_signal.emit("   • Vérifiez Windows Update")
        self.log_signal.emit("   • Testez les fonctionnalités qui posaient problème")
        
        self.finished_signal.emit("✅ Réparation terminée !\n\n💻 Redémarrage recommandé")
    
    def update_programs(self):
        self.log_signal.emit("╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*10 + "📦 MISE À JOUR WINGET" + " "*16 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝\n")
        
        # Vérifier winget
        self.log_signal.emit("🔍 Vérification de Winget...")
        try:
            result = subprocess.run(
                ["winget", "--version"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception("Winget non fonctionnel")
            
            version = result.stdout.decode('utf-8', errors='ignore').strip()
            self.log_signal.emit(f"✓ Winget {version} détecté\n")
        except:
            self.log_signal.emit("❌ Winget non disponible ou non installé")
            self.log_signal.emit("\n💡 SOLUTION:")
            self.log_signal.emit("   1. Ouvrir le Microsoft Store")
            self.log_signal.emit("   2. Rechercher 'App Installer'")
            self.log_signal.emit("   3. Installer/Mettre à jour")
            self.finished_signal.emit("❌ Erreur: Winget non disponible\n\nInstallez 'App Installer' depuis le Microsoft Store")
            return
        
        # MAJ sources
        self.log_signal.emit("┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 1/2 : Mise à jour des sources          │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        ret = self.run_cmd(["winget", "source", "update"])
        
        if ret == 0:
            self.log_signal.emit("✓ Sources mises à jour\n")
        
        # MAJ applications
        self.log_signal.emit("┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 2/2 : Mise à jour des applications     │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        self.log_signal.emit("⏱️  Cette opération peut prendre plusieurs minutes")
        self.log_signal.emit("📦 Mise à jour de TOUTES les applications...\n")
        
        cmd = [
            "winget", "upgrade",
            "--all",
            "--include-unknown",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
            "--disable-interactivity"
        ]
        
        ret = self.run_cmd(cmd)
        
        # Résumé
        self.log_signal.emit("\n" + "╔" + "═"*48 + "╗")
        
        if ret == 0:
            self.log_signal.emit("║" + " "*15 + "✅ TERMINÉ" + " "*21 + "║")
            self.log_signal.emit("╚" + "═"*48 + "╝")
            self.log_signal.emit("\n✅ Toutes les applications sont à jour !")
            self.finished_signal.emit("✅ Mise à jour terminée !\n\nToutes les applications sont à jour")
        else:
            self.log_signal.emit("║" + " "*10 + "⚠️  TERMINÉ AVEC WARNINGS" + " "*11 + "║")
            self.log_signal.emit("╚" + "═"*48 + "╝")
            self.log_signal.emit("\n⚠️  Certaines apps n'ont pas pu être mises à jour")
            self.log_signal.emit("💡 Causes possibles:")
            self.log_signal.emit("   • Application en cours d'exécution")
            self.log_signal.emit("   • Droits insuffisants pour certaines apps")
            self.log_signal.emit("   • Source non disponible")
            self.finished_signal.emit("⚠️  Mise à jour terminée\n\nCertaines apps ont peut-être échoué\nConsultez les logs pour détails")
    
    def network_test(self):
        """Test réseau complet : Ping + DNS + Speed test optionnel"""
        self.log_signal.emit("╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*10 + "🌐 TEST RÉSEAU COMPLET" + " "*15 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝\n")
        
        # ÉTAPE 1: Test connectivité (Ping multiple serveurs)
        self.log_signal.emit("┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 1/4 : Test connectivité (Ping)         │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        
        servers = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
            ("208.67.222.222", "OpenDNS"),
            ("9.9.9.9", "Quad9 DNS")
        ]
        
        ping_results = []
        for ip, name in servers:
            try:
                result = subprocess.run(
                    ["ping", "-n", "4", ip],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO,
                    encoding="cp850",
                    errors="replace"
                )
                
                if result.returncode == 0:
                    # Extraire stats
                    output = result.stdout
                    avg_time = "N/A"
                    packet_loss = "0%"
                    
                    for line in output.split('\n'):
                        if "Moyenne" in line or "Average" in line:
                            parts = line.split('=')
                            if len(parts) > 1:
                                avg_time = parts[-1].strip()
                        if "perdu" in line.lower() or "lost" in line.lower():
                            if "0%" in line or "0 %" in line:
                                packet_loss = "0%"
                            else:
                                # Extraire le pourcentage
                                import re
                                match = re.search(r'(\d+)%', line)
                                if match:
                                    packet_loss = match.group(0)
                    
                    status = "✓"
                    ping_results.append((name, avg_time, packet_loss, True))
                else:
                    status = "✗"
                    ping_results.append((name, "Échec", "100%", False))
                
                self.log_signal.emit(f"  {status} {name:20s} {avg_time:>15s}")
            except Exception as e:
                self.log_signal.emit(f"  ✗ {name:20s} Timeout")
                ping_results.append((name, "Timeout", "100%", False))
        
        # Résumé ping
        success_count = sum(1 for _, _, _, ok in ping_results if ok)
        self.log_signal.emit(f"\n📊 Résultat: {success_count}/{len(servers)} serveurs accessibles")
        
        # ÉTAPE 2: Test résolution DNS
        self.log_signal.emit("\n┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 2/4 : Test résolution DNS              │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        
        test_domains = [
            "google.com",
            "cloudflare.com",
            "github.com"
        ]
        
        dns_ok = 0
        for domain in test_domains:
            try:
                result = subprocess.run(
                    ["nslookup", domain],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO,
                    encoding="cp850",
                    errors="replace"
                )
                
                if result.returncode == 0 and "Address" in result.stdout:
                    self.log_signal.emit(f"  ✓ {domain}")
                    dns_ok += 1
                else:
                    self.log_signal.emit(f"  ✗ {domain} - Échec résolution")
            except:
                self.log_signal.emit(f"  ✗ {domain} - Timeout")
        
        self.log_signal.emit(f"\n📊 Résultat: {dns_ok}/{len(test_domains)} domaines résolus")
        
        # ÉTAPE 3: Informations connexion
        self.log_signal.emit("\n┌" + "─"*48 + "┐")
        self.log_signal.emit("│ ÉTAPE 3/3 : Informations réseau              │")
        self.log_signal.emit("└" + "─"*48 + "┘")
        
        try:
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="cp850",
                errors="replace"
            )
            
            if result.returncode == 0:
                output = result.stdout
                for line in output.split('\n'):
                    if "IPv4" in line or "Passerelle" in line or "Gateway" in line:
                        self.log_signal.emit(f"  {line.strip()}")
        except:
            self.log_signal.emit("  ✗ Impossible de récupérer les infos réseau")
        
        # Résumé final
        self.log_signal.emit("\n" + "╔" + "═"*48 + "╗")
        self.log_signal.emit("║" + " "*15 + "✅ TEST TERMINÉ" + " "*17 + "║")
        self.log_signal.emit("╚" + "═"*48 + "╝")
        
        if success_count == len(servers) and dns_ok == len(test_domains):
            self.log_signal.emit("\n✅ Connexion réseau: Excellente")
            self.finished_signal.emit("✅ Test réseau terminé !\n\nConnexion : Excellente")
        elif success_count > 0:
            self.log_signal.emit("\n⚠️  Connexion réseau: Correcte avec limitations")
            self.finished_signal.emit("⚠️  Test réseau terminé !\n\nConnexion : Correcte")
        else:
            self.log_signal.emit("\n❌ Connexion réseau: Problèmes détectés")
            self.finished_signal.emit("❌ Test réseau terminé !\n\nProblèmes de connexion")

# ============ REFRESH WORKER (NOUVEAU) ============
class RefreshWorker(QThread):
    """Thread pour le refresh sans bloquer l'UI"""
    data_ready = pyqtSignal(dict)
    
    def __init__(self, cpu_name, is_compact):
        super().__init__()
        self.cpu_name = cpu_name
        self.is_compact = is_compact
    
    def run(self):
        try:
            # Créer les instances WMI DANS le thread (obligatoire)
            try:
                w = wmi.WMI()
                storage = wmi.WMI(namespace="root\\Microsoft\\Windows\\Storage")
            except Exception as e:
                self.data_ready.emit({'error': f"Impossible d'initialiser WMI: {str(e)}"})
                return
            
            data = {}
            
            # CPU
            try:
                cpu_info = w.Win32_Processor()[0]
                data['cpu_percent'] = float(cpu_info.LoadPercentage) if cpu_info.LoadPercentage else 0.0
                data['cpu_cores'] = cpu_info.NumberOfCores
                data['cpu_threads'] = cpu_info.NumberOfLogicalProcessors
            except:
                data['cpu_percent'] = 0.0
                data['cpu_cores'] = "N/A"
                data['cpu_threads'] = "N/A"
            
            # RAM
            try:
                os_info = w.Win32_OperatingSystem()[0]
                total = int(os_info.TotalVisibleMemorySize) / (1024**2)
                free = int(os_info.FreePhysicalMemory) / (1024**2)
                used = total - free
                percent = (used / total) * 100
                data['ram'] = {
                    'total': total,
                    'used': used,
                    'available': free,
                    'percent': percent
                }
            except:
                data['ram'] = {'total': 0, 'used': 0, 'available': 0, 'percent': 0}
            
            # Autres infos (seulement en mode étendu)
            if not self.is_compact:
                # Windows version
                try:
                    os_info = w.Win32_OperatingSystem()[0]
                    data['windows_version'] = os_info.Caption.replace("Microsoft Windows ", "")
                except:
                    data['windows_version'] = "N/A"
                
                # Carte mère
                try:
                    board = w.Win32_BaseBoard()[0]
                    data['motherboard'] = f"{board.Manufacturer} {board.Product}"
                except:
                    data['motherboard'] = "N/A"
                
                # BIOS
                try:
                    bios = w.Win32_BIOS()[0]
                    data['bios'] = bios.SMBIOSBIOSVersion
                except:
                    data['bios'] = "N/A"
                
                # XMP
                try:
                    chips = w.Win32_PhysicalMemory()
                    states = []
                    for c in chips:
                        if c.Speed and c.ConfiguredClockSpeed:
                            states.append(int(c.ConfiguredClockSpeed) >= int(c.Speed) * 0.95)
                    if not states:
                        data['xmp'] = "❓ Inconnu"
                    else:
                        data['xmp'] = "✅ Activé" if all(states) else "❌ Désactivé"
                except:
                    data['xmp'] = "❓ Inconnu"
            
            # GPU
            try:
                gpus = w.Win32_VideoController()
                gpu_info = []
                for gpu in gpus:
                    name = gpu.Name
                    try:
                        ram_gb = int(gpu.AdapterRAM) / (1024**3) if gpu.AdapterRAM else 0
                        ram_str = f" | {ram_gb:.0f} Go" if ram_gb > 0 else ""
                    except:
                        ram_str = ""
                    gpu_info.append(f"{name}{ram_str}")
                data['gpu'] = "\n".join(gpu_info) if gpu_info else "❌ Aucun GPU"
            except:
                data['gpu'] = "❌ Erreur lecture GPU"
            
            # Disques
            try:
                drives = w.Win32_LogicalDisk(DriveType=3)
                disk_info = []
                for drive in drives:
                    letter = drive.DeviceID
                    total_gb = int(drive.Size) / (1024**3) if drive.Size else 0
                    free_gb = int(drive.FreeSpace) / (1024**3) if drive.FreeSpace else 0
                    used_gb = total_gb - free_gb
                    percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
                    alert = " ⚠️  CRITIQUE" if free_gb < (total_gb * 0.1) else ""
                    disk_info.append(f"{letter}\\ | {used_gb:.1f}/{total_gb:.1f} Go ({percent:.0f}%){alert}")
                data['disks'] = "\n".join(disk_info) if disk_info else "❌ Aucun disque"
            except:
                data['disks'] = "❌ Erreur lecture disques"
            
            # Top 5 processus
            try:
                processes = w.Win32_Process()
                sorted_procs = []
                for proc in processes:
                    try:
                        name = proc.Name
                        mem_mb = int(proc.WorkingSetSize) / (1024**2) if proc.WorkingSetSize else 0
                        if mem_mb > 10:
                            sorted_procs.append((name, mem_mb))
                    except:
                        pass
                sorted_procs.sort(key=lambda x: x[1], reverse=True)
                top5 = sorted_procs[:5]
                
                if top5:
                    top_info = []
                    for i, (name, mem) in enumerate(top5, 1):
                        top_info.append(f"{i}. {name} - {mem:.0f} Mo")
                    data['top5'] = "\n".join(top_info)
                else:
                    data['top5'] = ""
            except:
                data['top5'] = ""
            
            # Ping (léger - juste Google DNS)
            try:
                result = subprocess.run(
                    ["ping", "-n", "2", "8.8.8.8"],  # 2 pings rapides
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO,
                    encoding="cp850",
                    errors="replace"
                )
                
                if result.returncode == 0:
                    # Extraire le temps moyen
                    output = result.stdout
                    if "Moyenne" in output or "Average" in output:
                        # Format FR: "Moyenne = XXms"
                        # Format EN: "Average = XXms"
                        for line in output.split('\n'):
                            if "Moyenne" in line or "Average" in line:
                                parts = line.split('=')
                                if len(parts) > 1:
                                    ping_str = parts[-1].strip().replace('ms', '').strip()
                                    try:
                                        ping_val = int(ping_str)
                                        data['ping'] = f"{ping_val} ms"
                                        break
                                    except:
                                        pass
                        if 'ping' not in data:
                            data['ping'] = "< 1 ms"
                    else:
                        data['ping'] = "OK"
                else:
                    data['ping'] = "Échec"
            except:
                data['ping'] = "N/A"
            
            # Envoyer toutes les données
            self.data_ready.emit(data)
            
        except Exception as e:
            self.data_ready.emit({'error': str(e)})

# ============ FENÊTRE DE LOGS ============
class LogWindow(QDialog):
    def __init__(self, parent=None, title="Logs"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(1000, 600)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        
        layout.addWidget(self.log_text)
        self.setLayout(layout)
        
        self.setStyleSheet("QDialog { background-color: #161b22; }")
    
    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def log(self, text):
        """Alias pour compatibilité"""
        self.append_log(text)

# ============ BARRE DE PROGRESSION CUSTOM ============
class CustomProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMaximumHeight(22)
        
    def set_color_from_value(self, value):
        if value < 60:
            color = "#4CAF50"  # Vert
        elif value < 80:
            color = "#FF9800"  # Orange
        else:
            color = "#F44336"  # Rouge
        
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #333;
                border-radius: 8px;
                background-color: #2b2b2b;
                text-align: center;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

# ============ LISTE NOIRE - PROGRAMMES À PROTÉGER ============
PROTECTED_PROGRAMS = [
    # Composants Windows
    "windows", "microsoft edge", "microsoft store", "xbox",
    
    # Drivers
    "intel", "amd", "nvidia", "realtek", "driver",
    
    # Runtimes essentiels
    "visual c++", "microsoft visual c++", "vcredist",
    ".net framework", "directx", "java runtime",
    
    # Système
    "windows defender", "update", "security"
]

# ============ BLOATWARE CONNUS ============
KNOWN_BLOATWARE = [
    "mcafee", "norton trial", "avast free", "avg free",
    "pc cleaner", "driver updater", "registry cleaner",
    "toolbar", "browser hijacker", "adware"
]

# ============ BASE DE DONNÉES OUTILS ============
TOOLS_DATABASE = {
    "repair": [
        {
            "name": "MemTest86+",
            "type": "Open Source",
            "desc": "Test RAM complet - Détecte barrettes défectueuses",
            "url": "https://www.memtest.org/",
            "tutorial": """🔧 MEMTEST86+ - TESTER SA RAM

🎯 QUAND L'UTILISER ?
- PC freeze aléatoirement
- Écrans bleus (BSOD) fréquents
- Erreurs "memory management"
- Redémarrages intempestifs

🔥 TÉLÉCHARGEMENT
→ www.memtest.org
→ Cliquer "Download" (gratuit, open source)
→ Télécharger "USB installer"

📝 ÉTAPES DÉTAILLÉES

1️⃣ PRÉPARER LA CLÉ USB
   • Brancher clé USB VIDE (minimum 1 Go)
   • ⚠️ TOUT sera effacé sur la clé !
   • Lancer "imageUSB.exe" (téléchargé)
   • Sélectionner votre clé USB
   • Cliquer "Write"
   • Attendre 2-3 minutes

2️⃣ DÉMARRER SUR LA CLÉ
   • Redémarrer le PC
   • Appuyer répétitivement sur F12
     (ou Del, F2, Echap selon PC)
   • Chercher "Boot Menu" ou "Boot Order"
   • Sélectionner votre clé USB
   • Appuyer sur Entrée

3️⃣ LANCER LE TEST
   • Écran bleu avec texte qui défile
   • Le test démarre AUTOMATIQUEMENT
   • Ne rien toucher !
   • Laisser tourner 8 heures MINIMUM
   • Idéal: toute une nuit

4️⃣ LIRE LES RÉSULTATS
   ✅ "Pass: X, Errors: 0" = RAM parfaite !
   ❌ "Errors: X" (X > 0) = RAM défectueuse

5️⃣ SI ERREURS DÉTECTÉES
   • Éteindre le PC
   • Débrancher l'alimentation
   • Ouvrir le boîtier
   • Retirer toutes les barrettes RAM sauf une
   • Tester chaque barrette séparément
   • Celle qui fait des erreurs = à remplacer

💡 CONSEILS PRO
- Ne PAS utiliser le PC pendant le test
- Températures normales RAM: < 50°C
- Faire 2 passes complètes minimum
- Si plusieurs barrettes, tester une par une
- Noter les emplacements testés

⏱️ DURÉE: 8-12 heures (overnight)
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile)"""
        },
        {
            "name": "CrystalDiskInfo",
            "type": "Open Source",
            "desc": "Santé SSD/HDD/NVMe - Attributs SMART détaillés",
            "url": "https://crystalmark.info/en/software/crystaldiskinfo/",
            "tutorial": """💿 CRYSTALDISKINFO - VÉRIFIER SANTÉ DISQUE

🎯 QUAND L'UTILISER ?
- PC très lent
- Fichiers corrompus
- Bruits bizarres du disque
- Vérification avant achat occasion

🔥 TÉLÉCHARGEMENT
→ crystalmark.info
→ "CrystalDiskInfo Standard Edition"
→ Version portable (pas d'install)

📝 UTILISATION SIMPLE

1️⃣ LANCER LE PROGRAMME
   • Extraire le ZIP
   • Double-clic "DiskInfo64.exe"
   • S'ouvre en 2 secondes

2️⃣ LIRE L'ÉTAT DE SANTÉ
   🟦 BLEU "Good" = Disque sain ✅
   🟨 JAUNE "Caution" = Attention ⚠️
   🟥 ROUGE "Bad" = Critique ❌

3️⃣ COMPRENDRE LES INFOS

   TEMPÉRATURE
   • Normal: 30-45°C
   • Chaud: 45-55°C
   • Trop chaud: > 55°C

   HEURES D'UTILISATION
   • "Power On Hours"
   • Normal: varie selon âge
   • > 40,000h = disque vieux

   SECTEURS RÉALLOUÉS
   • "Reallocated Sectors"
   • 0 = parfait ✅
   • > 10 = attention ⚠️
   • > 100 = remplacer ❌

4️⃣ POUR SSD/NVMe

   WEAR LEVELING
   • "Pourcentage de vie"
   • 100% = neuf
   • < 10% = fin de vie

   TBW (Total Bytes Written)
   • Quantité écrite sur le SSD
   • Comparer avec garantie fabricant

5️⃣ SI PROBLÈME DÉTECTÉ
   🟨 JAUNE:
   • Sauvegarder données MAINTENANT
   • Surveiller évolution
   • Prévoir remplacement

   🟥 ROUGE:
   • SAUVEGARDER D'URGENCE
   • Remplacer IMMÉDIATEMENT
   • Ne plus stocker données importantes

💡 CONSEILS PRO
- Vérifier tous les 3 mois
- Activer notifications (Options)
- Comparer évolution dans le temps
- Screenshot des attributs SMART
- Garder toujours une sauvegarde

⏱️ DURÉE: 2 minutes
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐☆☆☆☆ (Très facile)"""
        },
        {
            "name": "HWiNFO64",
            "type": "Gratuit",
            "desc": "Monitoring complet - Températures, voltages, capteurs",
            "url": "https://www.hwinfo.com/",
            "tutorial": """📊 HWINFO64 - MONITORING AVANCÉ

🎯 UTILITÉ
- Voir TOUTES les températures
- Surveiller voltages CPU/GPU
- Détecter throttling
- Monitoring en temps réel

🔥 TÉLÉCHARGEMENT
→ www.hwinfo.com
→ "Free Download"
→ Version portable recommandée

📝 CONFIGURATION

1️⃣ PREMIER LANCEMENT
   • Double-clic HWiNFO64.exe
   • Cocher "Sensors-only"
   • Décocher "Summary-only"
   • Cliquer "Start"

2️⃣ COMPRENDRE L'INTERFACE
   Fenêtre avec plein de lignes:
   • CPU: températures par cœur
   • GPU: temp, usage, clock
   • Disques: températures
   • Carte mère: voltages

3️⃣ TEMPÉRATURES NORMALES

   CPU (au repos):
   • 30-45°C = normal
   • 45-60°C = acceptable
   • > 60°C = problème

   CPU (en charge):
   • 60-75°C = normal
   • 75-85°C = limite
   • > 85°C = throttling !

   GPU (en jeu):
   • 60-75°C = excellent
   • 75-85°C = normal
   • > 85°C = attention

   Disques:
   • < 45°C = parfait
   • 45-55°C = normal
   • > 55°C = mauvais

4️⃣ DÉTECTER PROBLÈMES

   THROTTLING:
   • Chercher "Thermal Throttling"
   • "Yes" = PC ralentit pour refroidir
   • Solution: améliorer refroidissement

   VOLTAGES ANORMAUX:
   • CPU Core: 1.0-1.4V normal
   • Si > 1.5V = danger
   • Si < 0.8V = instable

5️⃣ STRESS TEST
   • Menu: Tools > Sensors + MSI Afterburner
   • Lancer un jeu gourmand
   • Observer températures max
   • Si > 90°C = problème cooling

💡 FONCTIONS UTILES
- Logging: enregistrer historique
- Alerts: alertes si temp trop haute
- Overlay: afficher en jeu (avec RTSS)
- Export: sauvegarder rapport

⏱️ DURÉE: 5 minutes setup
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐⭐☆☆ (Moyen)"""
        },
        {
            "name": "Snappy Driver Installer",
            "type": "Open Source",
            "desc": "MAJ automatique drivers - Base hors ligne",
            "url": "https://sdi-tool.org/",
            "tutorial": """🔌 SNAPPY DRIVER INSTALLER - DRIVERS AUTO

🎯 QUAND L'UTILISER ?
- Après réinstall Windows
- Périphériques non reconnus
- Problèmes de performances
- Mise à jour complète drivers

🔥 TÉLÉCHARGEMENT
→ sdi-tool.org
→ Télécharger "SDI Full" (17 Go!)
→ OU "SDI Lite" + téléchargement auto

📝 UTILISATION

1️⃣ LANCER SDI
   • Extraire et lancer SDI.exe
   • Accepter UAC (admin requis)
   • Attendre scan (1-2 minutes)

2️⃣ SÉLECTION INTELLIGENTE
   ✅ Cocher:
   • Drivers manquants (rouge)
   • Mises à jour importantes
   
   ❌ Décocher:
   • Drivers qui fonctionnent déjà bien
   • Versions bêta
   • Pilotes très anciens

3️⃣ INSTALLATION
   • Cliquer "Install"
   • Ne PAS fermer pendant install
   • Redémarrer si demandé

4️⃣ VÉRIFICATION
   • Relancer SDI après reboot
   • Vérifier que tout est vert
   • Tester périphériques

💡 CONSEILS PRO
- Toujours créer point de restauration avant
- Ne PAS installer drivers GPU via SDI
  (préférer site NVIDIA/AMD)
- SDI Full = pas besoin internet
- Lancer tous les 6 mois

⚠️ ATTENTION
- Ne pas installer drivers audio si son OK
- Éviter drivers chipset si PC stable

⏱️ DURÉE: 15-30 minutes
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile)"""
        },
        {
            "name": "DDU (Display Driver Uninstaller)",
            "type": "Gratuit",
            "desc": "Nettoyage complet drivers GPU - NVIDIA/AMD",
            "url": "https://www.guru3d.com/files-details/display-driver-uninstaller-download.html",
            "tutorial": """🎮 DDU - NETTOYER DRIVERS GPU

🎯 QUAND L'UTILISER ?
- Avant changement carte graphique
- Crashes/freezes dans les jeux
- Passage NVIDIA ↔ AMD
- Drivers GPU corrompus

🔥 TÉLÉCHARGEMENT
→ www.guru3d.com
→ Chercher "DDU"
→ Télécharger dernière version

📝 ÉTAPES IMPORTANTES

1️⃣ PRÉPARATION
   • Télécharger NOUVEAUX drivers GPU
     (NVIDIA.com ou AMD.com)
   • Déconnecter internet (important!)
   • Créer point de restauration

2️⃣ MODE SANS ÉCHEC
   • Win + R → msconfig
   • Onglet "Démarrage"
   • Cocher "Démarrage sécurisé"
   • Redémarrer

3️⃣ UTILISER DDU
   • Lancer DDU (extraire ZIP d'abord)
   • Sélectionner fabricant (NVIDIA/AMD)
   • Cliquer "Clean and Restart"
   • Attendre nettoyage complet
   • PC redémarre automatiquement

4️⃣ APRÈS NETTOYAGE
   • Windows redémarre en mode normal
   • Reconnecter internet
   • Installer NOUVEAUX drivers
   • Redémarrer une dernière fois

5️⃣ VÉRIFICATION
   • Tester un jeu
   • Vérifier températures
   • Aucun artefact visuel = OK!

💡 CONSEILS PRO
- TOUJOURS mode sans échec
- TOUJOURS déconnecter internet avant
- Ne pas interrompre le processus
- Garder DDU pour dépannages futurs

⚠️ CAS SPÉCIAUX
- Passage NVIDIA → AMD:
  1. DDU NVIDIA
  2. Éteindre PC
  3. Changer carte physiquement
  4. Rallumer
  5. DDU AMD (au cas où)
  6. Installer drivers AMD

⏱️ DURÉE: 20 minutes
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐⭐☆☆ (Moyen)"""
        },
        {
            "name": "Victoria SSD/HDD",
            "type": "Gratuit",
            "desc": "Scan secteurs défectueux - Réparation disque",
            "url": "https://hdd.by/victoria/",
            "tutorial": """💾 VICTORIA - SCAN DISQUE AVANCÉ

🎯 QUAND L'UTILISER ?
- Disque très lent
- Erreurs de lecture/écriture
- Secteurs défectueux suspectés
- Avant de jeter un disque

🔥 TÉLÉCHARGEMENT
→ hdd.by/victoria
→ Version 5.x (Windows 10/11)
→ Gratuit, pas d'install

📝 UTILISATION

1️⃣ LANCER EN ADMIN
   • Extraire ZIP
   • Clic droit > Exécuter en admin
   • Sélectionner disque à tester

2️⃣ SCAN RAPIDE (SMART)
   • Onglet "SMART"
   • Voir état santé global
   • Noter attributs critiques

3️⃣ SCAN SURFACE (complet)
   • Onglet "Tests"
   • Sélectionner "Verify"
   • Cocher "Ignore errors"
   • Lancer le scan

4️⃣ LIRE RÉSULTATS
   Blocs colorés:
   🟦 Bleu = OK (< 50ms)
   🟩 Vert = OK (50-150ms)
   🟨 Jaune = Lent (150-500ms)
   🟧 Orange = Critique (> 500ms)
   🟥 Rouge = Secteur mort

5️⃣ ACTIONS SELON RÉSULTATS
   0-10 blocs rouges:
   → Sauvegarder et surveiller
   
   10-100 blocs rouges:
   → Remplacer sous 1 mois
   
   > 100 blocs rouges:
   → REMPLACER IMMÉDIATEMENT

💡 FONCTION REMAP
- Si < 50 secteurs morts
- Victoria peut les "remap"
- Onglet "Remap" > Start
- ⚠️ Perte des données dans secteurs!

⚠️ ATTENTION
- TOUJOURS sauvegarder avant scan
- Scan complet = 2-6 heures
- Ne pas utiliser PC pendant scan

⏱️ DURÉE: 2-6 heures (selon taille)
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐⭐⭐☆ (Avancé)"""
        },
        {
            "name": "Malwarebytes Free",
            "type": "Gratuit",
            "desc": "Anti-malware puissant - Détection PUP/Adware",
            "url": "https://www.malwarebytes.com/",
            "tutorial": """🛡️ MALWAREBYTES - ANTI-MALWARE

🎯 QUAND L'UTILISER ?
- PC lent subitement
- Popups publicitaires
- Page d'accueil modifiée
- Programmes inconnus installés

🔥 TÉLÉCHARGEMENT
→ malwarebytes.com
→ Version Free (gratuit)
→ Installer normalement

📝 UTILISATION

1️⃣ INSTALLATION
   • Installer Malwarebytes
   • Décliner version Premium (payante)
   • Laisser mettre à jour la base

2️⃣ SCAN COMPLET
   • Ouvrir Malwarebytes
   • Cliquer "Analyser"
   • Choisir "Analyse complète"
   • Lancer (30-60 minutes)

3️⃣ PENDANT LE SCAN
   • Ne pas utiliser le PC
   • Laisser tourner jusqu'au bout
   • Observer détections en temps réel

4️⃣ RÉSULTATS
   • Détections = en rouge
   • Tout cocher automatiquement
   • Cliquer "Mettre en quarantaine"
   • Redémarrer si demandé

5️⃣ VÉRIFICATION POST-SCAN
   • Vérifier programmes installés
   • Vérifier extensions navigateur
   • Reset page d'accueil si besoin

💡 CONSEILS PRO
- Scan mensuel recommandé
- Compléter avec Windows Defender
- Version gratuite = scan manuel
- Quarantaine conservée 30 jours

🧹 NETTOYAGE MANUEL APRÈS
1. Win + R → appwiz.cpl
2. Désinstaller programmes suspects
3. Reset navigateurs:
   • Chrome: chrome://settings/reset
   • Firefox: about:support > Reset
   • Edge: edge://settings/reset

⏱️ DURÉE: 30-60 minutes
💰 COÛT: 0€ (version Free)
🔧 DIFFICULTÉ: ⭐☆☆☆☆ (Très facile)"""
        }
    ],
    "gaming": [
        {
            "name": "MSI Afterburner",
            "type": "Gratuit",
            "desc": "Overclock GPU + Monitoring FPS en jeu",
            "url": "https://www.msi.com/Landing/afterburner",
            "tutorial": """🎮 MSI AFTERBURNER - OC GPU + MONITORING

🎯 FONCTIONS
- Overclocker carte graphique
- Afficher FPS en jeu
- Contrôler ventilateurs GPU
- Voir températures temps réel

🔥 TÉLÉCHARGEMENT
→ msi.com/Landing/afterburner
→ Télécharger + installer
→ ⚠️ Installer aussi RivaTuner (inclus)

📝 CONFIGURATION MONITORING

1️⃣ ACTIVER L'OVERLAY
   • Ouvrir Afterburner
   • Cliquer icône "Settings" (⚙️)
   • Onglet "Monitoring"

2️⃣ CHOISIR INFOS À AFFICHER
   Cocher ces éléments:
   ✅ GPU temperature
   ✅ GPU usage
   ✅ Framerate
   ✅ CPU temperature
   ✅ RAM usage

   Pour chaque, cocher:
   ✅ "Show in On-Screen Display"

3️⃣ POSITION ET STYLE
   • Onglet "On-Screen Display"
   • Hotkey toggle: Inser (ou autre)
   • Position: Top-left recommandé
   • Zoom: 100%

4️⃣ TESTER
   • Lancer un jeu
   • Appuyer sur la touche définie
   • L'overlay apparaît en jeu !

📈 OVERCLOCK SIMPLE (OPTIONNEL)

⚠️ À TES RISQUES - Suivre attentivement

1️⃣ PRÉPARATION
   • Installer Heaven Benchmark (test)
   • Noter performances de BASE
   • Fermer tous les programmes

2️⃣ OVERCLOCK CONSERVATEUR
   • Core Clock: +50 MHz
   • Memory Clock: +100 MHz
   • Power Limit: +10%
   • Temp Limit: 85°C

3️⃣ TESTER STABILITÉ
   • Lancer Heaven Benchmark
   • 30 minutes sans crash = stable
   • Noter nouveau score

4️⃣ AUGMENTER PROGRESSIVEMENT
   • +25 MHz Core à chaque fois
   • Retester 30 min
   • Si crash: revenir -25 MHz
   • Trouver le maximum stable

5️⃣ SI ARTEFACTS/CRASH
   • Artefacts visuels = trop haut
   • Crash = beaucoup trop haut
   • Revenir valeur précédente stable
   • Appliquer "Apply at startup"

💡 CONSEILS SÉCURITÉ
- Ne JAMAIS toucher voltage (danger)
- Températures < 85°C toujours
- Tester 1h avant valider
- Profil "Default" pour annuler
- Sauvegarder profils stables

⏱️ DURÉE: 15 min (monitoring) / 2h (OC)
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile monitoring)
                ⭐⭐⭐⭐☆ (OC avancé)"""
        },
        {
            "name": "GeForce Experience / AMD Software",
            "type": "Gratuit",
            "desc": "Drivers GPU + Optimisation jeux automatique",
            "url": "https://www.nvidia.com/en-us/geforce/geforce-experience/ | https://www.amd.com/en/technologies/software",
            "tutorial": """🎮 GEFORCE EXPERIENCE / AMD SOFTWARE

🎯 FONCTIONS
- MAJ automatique drivers GPU
- Optimisation automatique des jeux
- Enregistrement replays (ShadowPlay/ReLive)
- Streaming Twitch/YouTube

🔥 TÉLÉCHARGEMENT
NVIDIA:
→ nvidia.com/geforce/geforce-experience
→ Installer + compte NVIDIA

AMD:
→ amd.com/software
→ "AMD Software: Adrenalin Edition"

📝 CONFIGURATION NVIDIA

1️⃣ OPTIMISATION JEUX AUTO
   • Ouvrir GeForce Experience
   • Onglet "Accueil"
   • Voir liste jeux détectés
   • Cliquer "Optimiser" sur chaque jeu

2️⃣ SHADOWPLAY (ENREGISTREMENT)
   • Alt + Z (overlay)
   • Paramètres
   • Activer "Enregistrement en arrière-plan"
   • Qualité: Élevée
   • Résolution: 1080p 60fps

3️⃣ HOTKEYS UTILES
   • Alt + F9: Démarrer/arrêter enregistrement
   • Alt + F10: Sauvegarder replay (5 min)
   • Alt + Z: Ouvrir overlay

4️⃣ FILTRES FREESTYLE (BONUS)
   • Alt + F3 en jeu
   • Ajouter filtres:
     - Sharpen (netteté)
     - Color (saturation)
     - Brightness (contraste)
   • Gain: +10-20% visibilité

📝 CONFIGURATION AMD

1️⃣ OPTIMISATION AUTO
   • Ouvrir AMD Software
   • Onglet "Gaming"
   • Sélectionner jeu
   • "Optimisation automatique"

2️⃣ RADEON BOOST
   • Gaming > Paramètres globaux
   • Activer "Radeon Boost"
   • Résolution min: 85%
   • Gain: +10-30% FPS

3️⃣ ANTI-LAG & CHILL
   • Anti-Lag: ON (réduit input lag)
   • Radeon Chill: ON (économise batterie)
   • Cible FPS: 60-144 selon écran

4️⃣ RELIVE (ENREGISTREMENT)
   • Onglet "Enregistrer et diffuser"
   • Activer ReLive
   • Qualité: Élevée
   • Hotkey: Ctrl + Shift + R

💡 OPTIMISATIONS MANUELLES

Pour NVIDIA:
- Panneau NVIDIA > Gérer paramètres 3D
- Performances maximales:
  - Mode alimentation: Préférer perfs max
  - Pré-rendu d'images: 1
  - Texture filtering: Performances

Pour AMD:
- AMD Software > Gaming > Paramètres
- Performances maximales:
  - Tessellation: Override (x8)
  - Anti-Aliasing: Override
  - Texture filtering: Performances

⚠️ ATTENTION
- Optimisation auto = compromis qualité/perfs
- Pour e-sport: tout au minimum manuellement
- Enregistrement = -5 à -10% FPS

⏱️ DURÉE: 10-15 minutes setup
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile)"""
        },
        {
            "name": "Process Lasso",
            "type": "Gratuit",
            "desc": "Optimisation priorités processus - Anti-freeze",
            "url": "https://bitsum.com/",
            "tutorial": """⚡ PROCESS LASSO - OPTIMISATION CPU

🎯 UTILITÉ
- Empêcher processus de monopoliser CPU
- Prioriser jeux automatiquement
- Éviter freezes en multitâche
- Overclock automatique (si supporté)

🔥 TÉLÉCHARGEMENT
→ bitsum.com
→ Version Free (gratuite)
→ Toutes fonctions essentielles incluses

📝 CONFIGURATION GAMING

1️⃣ INSTALLATION
   • Installer Process Lasso
   • Laisser tourner en arrière-plan
   • Icône dans system tray

2️⃣ MODE JEU AUTO
   • Clic droit icône tray
   • "Gaming Mode" > "Automatic"
   • Détecte jeux et boost priorité

3️⃣ CONFIGURATION AVANCÉE
   • Ouvrir Process Lasso (GUI)
   • Options > General Settings
   • ✅ Enable ProBalance
   • ✅ Gaming Mode
   • ✅ IdleSaver

4️⃣ RÈGLES PERSONNALISÉES
   Pour un jeu spécifique:
   • Trouver processus du jeu
   • Clic droit > Priorité > Always > High
   • Clic droit > Affinité CPU > Tous les cœurs

5️⃣ ANTI-FREEZE
   • Options > ProBalance
   • Restraint: Default (automatic)
   • Agit automatiquement si CPU saturé

💡 FONCTIONS BONUS

IDLE SAVER:
- Réduit processus inactifs
- Libère ressources pour jeu
- Automatique, rien à faire

BITSUM HIGHEST PERFORMANCE:
- Menu > Power > Bitsum Highest Performance
- Plan d'alimentation custom optimisé
- Meilleur que "Hautes Performances" Windows

WATCHDOG:
- Tuer processus automatiquement
- Si dépasse % CPU trop longtemps
- Configuration: Options > Watchdog

📊 MONITORING
- Graphiques CPU temps réel
- Historique des actions ProBalance
- Log de toutes les interventions

⚠️ ATTENTION
- Version Free = pub au démarrage (skip)
- Pas obligatoire mais très efficace
- Impact: +5-15% stabilité FPS

💎 VERSION PRO (OPTIONNELLE)
- 0 pub
- Support prioritaire
- Fonctions extra (rarement utiles)
- Prix: ~35€ (lifetime)

⏱️ DURÉE: 5 minutes setup
💰 COÛT: 0€ (Free) ou 35€ (Pro)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile)"""
        },
        {
            "name": "Intelligent Standby List Cleaner",
            "type": "Gratuit",
            "desc": "Nettoie RAM standby - Réduit stuttering",
            "url": "https://www.wagnardsoft.com/content/intelligent-standby-list-cleaner-v1000-released",
            "tutorial": """🧹 ISLC - NETTOYEUR RAM STANDBY

🎯 PROBLÈME RÉSOLU
- Stuttering en jeu (micro-freezes)
- RAM "pleine" mais rien n'utilise
- Standby memory mal gérée par Windows

🔥 TÉLÉCHARGEMENT
→ wagnardsoft.com
→ "ISLC" (Intelligent Standby List Cleaner)
→ Gratuit, pas d'install

📝 CONFIGURATION OPTIMALE

1️⃣ LANCER ISLC
   • Extraire ZIP
   • Lancer ISLC.exe
   • Apparaît dans system tray

2️⃣ PARAMÈTRES RECOMMANDÉS
   Settings recommandés:
   
   ✅ Start ISLC minimized and auto-Start monitoring
   ✅ Enable custom timer resolution
   ✅ Enable custom timer resolution when resolution is equal or higher
   → Valeur: 0.50
   
   ✅ The list size is at least (in MegaBytes)
   → Si 16 Go RAM: 8000
   → Si 32 Go RAM: 16000
   → Si 64 Go RAM: 32000
   
   ✅ Free memory is lower than (in MegaBytes)
   → 4096 (4 Go)

3️⃣ MODE AUTO
   • Cocher "Start ISLC minimized"
   • Cocher "Launch on Windows startup"
   • Minimiser la fenêtre
   • Tourne en arrière-plan

4️⃣ VÉRIFICATION
   • En jeu: regarder RAM
   • ISLC nettoie automatiquement
   • Standby reste < valeur définie

💡 COMPRENDRE ISLC

STANDBY MEMORY:
- Cache Windows en RAM
- Normalement utile (apps récentes)
- Mais peut causer stuttering
- ISLC vide ce cache si trop plein

TIMER RESOLUTION:
- Réduit latence système
- 0.50ms = très réactif
- Gain: input lag réduit

📊 IMPACT PERFORMANCES
- Stuttering: -50 à -90%
- 1% Low FPS: +10-30%
- Frame time: plus stable

⚠️ ATTENTION
- Sur SSD: peu d'impact visible
- Sur HDD: ÉNORME différence
- 8 Go RAM: INDISPENSABLE
- 32+ Go RAM: moins utile

🎮 CAS D'USAGE TYPIQUES
- Warzone, Apex: stuttering réduit
- Star Citizen: loading times améliorés
- Tarkov: micro-freezes éliminés

⏱️ DURÉE: 2 minutes setup
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐☆☆☆☆ (Très facile)"""
        },
        {
            "name": "Latency Mon",
            "type": "Gratuit",
            "desc": "Détecte latence système - Trouve drivers problématiques",
            "url": "https://www.resplendence.com/latencymon",
            "tutorial": """⏱️ LATENCYMON - DIAGNOSTIQUER LATENCE

🎯 QUAND L'UTILISER ?
- Stuttering inexpliqué
- Audio qui craque/saute
- Input lag variable
- FPS instables

🔥 TÉLÉCHARGEMENT
→ resplendence.com/latencymon
→ Version gratuite suffisante
→ Installer normalement

📝 UTILISATION

1️⃣ LANCER LATENCYMON
   • Ouvrir en mode admin
   • Fermer tous les programmes
   • Laisser Windows "au repos"

2️⃣ DÉMARRER MONITORING
   • Onglet "Main"
   • Cliquer bouton vert "Start"
   • Laisser tourner 5-10 minutes

3️⃣ LIRE RÉSULTATS
   Zone "Conclusion":
   
   🟢 "Your system is suitable for real-time audio"
   → Aucun problème détecté
   
   🟡 "Your system has some interrupt latency"
   → Problème mineur
   
   🔴 "Your system is NOT suitable..."
   → Problème majeur de drivers

4️⃣ IDENTIFIER COUPABLE
   • Onglet "Drivers"
   • Trier par "Highest execution (µs)"
   • Top 3-5 = drivers problématiques

5️⃣ RÉSOUDRE PROBLÈMES

   DRIVERS COMMUNS PROBLÉMATIQUES:
   
   📡 WIFI/RÉSEAU:
   • Nom: "ndis.sys", "tcpip.sys", "nwifi.sys"
   • Solution: MAJ drivers réseau
   
   🎵 AUDIO:
   • Nom: "dpc.sys", "hal.dll"
   • Solution: Désactiver améliorations audio
     → Périphériques audio > Propriétés
     → Onglet Améliorations
     → Désactiver tout
   
   🔌 USB:
   • Nom: "USBXHCI.SYS", "storport.sys"
   • Solution: Désactiver USB Selective Suspend
     → Panneau config > Options alimentation
     → Paramètres avancés
     → USB > Désactiver

   🖱️ SOURIS/CLAVIER:
   • Nom: "mouclass.sys", "kbdclass.sys"
   • Solution: Désactiver Enhance Pointer Precision

💡 TESTS AVANCÉS

TEST SOUS CHARGE:
- Lancer LatencyMon
- Ouvrir YouTube, navigateur, Discord
- Observer si latence augmente
- Identifier quel programme cause pic

TEST GAMING:
- Lancer jeu en fenêtré
- LatencyMon en arrière-plan
- Jouer 10 minutes
- Analyser résultats après

📊 VALEURS CIBLES

DPC Latency:
- < 100 µs = Excellent
- 100-500 µs = Bon
- 500-1000 µs = Acceptable
- > 1000 µs = Problématique

ISR Latency:
- < 50 µs = Excellent
- > 200 µs = Problème

⚠️ ATTENTION
- Certains drivers = normaux (nvlddmkm.sys)
- Problème = si >> 1000 µs constamment
- Test à faire PC "propre" (sans jeu lancé)

⏱️ DURÉE: 15-30 minutes
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐⭐☆☆ (Moyen)"""
        }
    ],
    "network": [
        {
            "name": "Wireshark",
            "type": "Open Source",
            "desc": "Analyse trafic réseau - Diagnostic connexion",
            "url": "https://www.wireshark.org/",
            "tutorial": """🌐 WIRESHARK - ANALYSE RÉSEAU AVANCÉE

🎯 UTILITÉ
- Diagnostiquer problèmes réseau
- Voir quel programme utilise bande passante
- Détecter malwares réseau
- Analyser lag gaming

🔥 TÉLÉCHARGEMENT
→ wireshark.org
→ Version Windows stable
→ Installer avec WinPcap/Npcap

📝 UTILISATION BASIQUE

1️⃣ PREMIER LANCEMENT
   • Ouvrir Wireshark (admin)
   • Sélectionner interface réseau
     (WiFi = WLAN, Ethernet = Ethernet)
   • Double-clic pour démarrer capture

2️⃣ FILTRES UTILES

   Voir seulement trafic web:
   → http || https || dns

   Voir connexions à un IP:
   → ip.addr == 192.168.1.1

   Voir trafic d'un programme:
   → tcp.port == 27015 (exemple Steam)

3️⃣ ANALYSER LAG GAMING
   • Lancer capture avant de jouer
   • Jouer 5-10 minutes
   • Arrêter capture
   • Filtrer: icmp (pour ping)
   • Chercher "TTL exceeded" = packet loss

4️⃣ STATISTIQUES UTILES
   • Menu: Statistics > Conversations
   • Trier par "Bytes" (descendant)
   • Voir quel IP/programme utilise plus

💡 CAS D'USAGE

IDENTIFIER MALWARE:
- Capture pendant 10 min (PC idle)
- Statistics > Endpoints > IPv4
- Chercher connexions à pays suspects
- Chercher ports bizarres (> 10000)

VOIR BANDWIDTH PAR APP:
- Statistics > Protocol Hierarchy
- Voir % de chaque protocole
- Identifier app gourmande

PING ANALYSIS:
- Filter: icmp
- Voir temps de réponse
- > 100ms = lag
- Packet loss = jitter

⚠️ POUR DÉBUTANTS
- Interface intimidante au début
- Suivre tutos YouTube pour cas précis
- Pas toucher aux options avancées

⏱️ DURÉE: 30 min apprentissage
💰 COÛT: 0€ (open source)
🔧 DIFFICULTÉ: ⭐⭐⭐⭐☆ (Avancé)"""
        },
        {
            "name": "TCP Optimizer",
            "type": "Gratuit",
            "desc": "Optimisation paramètres TCP/IP - Meilleure latence",
            "url": "https://www.speedguide.net/downloads.php",
            "tutorial": """🚀 TCP OPTIMIZER - OPTIMISER CONNEXION

🎯 UTILITÉ
- Réduire latence (ping)
- Optimiser débit download/upload
- Paramètres TCP/IP automatiques
- Gaming + streaming

🔥 TÉLÉCHARGEMENT
→ speedguide.net/downloads.php
→ "SG TCP Optimizer"
→ Pas d'installation (portable)

📝 UTILISATION

1️⃣ LANCER EN ADMIN
   • Clic droit > Exécuter en admin
   • Interface simple avec sliders

2️⃣ CONFIGURATION GAMING

   Connection Speed:
   • Slider = votre vitesse internet
   • Test speed: speedtest.net
   • Exemple: 100 Mbps

   Network Adapter:
   • Sélectionner carte active
   • WiFi ou Ethernet

   Optimization:
   • Sélectionner "Gaming Tweaks"
   • OU "Optimal" si usage mixte

3️⃣ PARAMÈTRES AVANCÉS (ONGLET)
   Pour gaming compétitif:
   
   ✅ Increase receive window size
   ✅ Network throttling index (disabled)
   ✅ Disable Windows scaling heuristics
   ✅ Disable Network throttling (10Mbps+)

4️⃣ APPLIQUER
   • Bouton "Apply Changes"
   • Redémarrer PC obligatoire
   • Tester après reboot

5️⃣ TESTS AVANT/APRÈS
   AVANT d'appliquer:
   • speedtest.net: noter ping/speed
   • Test in-game: noter ping

   APRÈS reboot:
   • Refaire mêmes tests
   • Gain typique: -5 à -20ms ping

💡 PROFILS PRÉDÉFINIS

OPTIMAL:
- Recommandé pour 99% des cas
- Équilibre speed/latence
- Usage polyvalent

GAMING:
- Priorité latence minimale
- Sacrifice un peu de throughput
- Idéal FPS compétitif

CUSTOM:
- Mode avancé
- Modifier chaque paramètre
- Experts seulement

📊 IMPACT RÉEL
- Connexion déjà bonne: +5-10%
- Connexion mal configurée: +30-50%
- Old Windows install: ÉNORME diff

⚠️ RESTAURATION
- Menu: File > Reset Original
- Restaure tout par défaut Windows
- Utile si problèmes après

🌍 AUTRES OPTIMISATIONS
- Changer DNS: 1.1.1.1 ou 8.8.8.8
- QoS routeur: priorité gaming
- Cable ethernet > WiFi toujours

⏱️ DURÉE: 5 minutes
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐⭐☆☆☆ (Facile)"""
        }
    ],
    "benchmark": [
        {
            "name": "Cinebench R23",
            "type": "Gratuit",
            "desc": "Benchmark CPU - Single & Multi-thread",
            "url": "https://www.maxon.net/en/cinebench",
            "tutorial": """🏆 CINEBENCH R23 - BENCHMARK CPU

🎯 UTILITÉ
- Mesurer performances CPU pures
- Comparer avec autres configs
- Tester stabilité overclock
- Voir différence avant/après upgrade

🔥 TÉLÉCHARGEMENT
→ maxon.net/cinebench
→ Version R23 (dernière)
→ Gratuit, installation légère

📝 UTILISATION

1️⃣ PRÉPARATION
   • Fermer TOUS les programmes
   • Désactiver antivirus temporairement
   • Mode Hautes Performances activé
   • Laisser PC "refroidir" 5 min

2️⃣ TEST MULTI-CORE
   • Bouton "Start" Multi-Core
   • Attendre 10 minutes (long!)
   • Score apparaît à la fin
   • Noter le score

3️⃣ TEST SINGLE-CORE
   • Bouton "Start" Single-Core
   • Durée: ~10 minutes aussi
   • Note le score

4️⃣ COMPARER RÉSULTATS
   → cb23.tech/en/
   • Chercher ton CPU
   • Comparer ton score vs moyenne
   • ±5% = normal
   • > +10% = très bon
   • < -10% = problème (throttling?)

💡 INTERPRÉTER SCORES

MULTI-CORE (rendu 3D, export vidéo):
- Ryzen 5600X: ~11,000
- Ryzen 5800X3D: ~15,000
- Intel 12600K: ~17,000
- Ryzen 9 5950X: ~28,000

SINGLE-CORE (gaming, réactivité):
- Ryzen 5600X: ~1,550
- Intel 12600K: ~1,900
- Gaming = single-core important!

📊 TESTS ADDITIONNELS

TEST STABILITÉ:
- Lancer 5x multi-core d'affilée
- Score doit rester identique (±2%)
- Si baisse progressive = throttling

MONITORING PENDANT TEST:
- HWiNFO64 ouvert à côté
- Surveiller températures CPU
- > 90°C = problème cooling

⚠️ ATTENTION
- Benchmark ≠ performance gaming
- Score élevé utile pour:
  - Rendu 3D/vidéo
  - Compilation code
  - Streaming avec encodage CPU
- Gaming = GPU plus important

🎯 QUAND REFAIRE TEST?
- Après overclock CPU
- Après changement ventirad
- Après MAJ BIOS
- Si PC "moins rapide" qu'avant

⏱️ DURÉE: 25 minutes (complet)
💰 COÛT: 0€ (gratuit)
🔧 DIFFICULTÉ: ⭐☆☆☆☆ (Très facile)"""
        },
        {
            "name": "3DMark (Basic Edition)",
            "type": "Gratuit (limité)",
            "desc": "Benchmark GPU - Gaming performance",
            "url": "https://store.steampowered.com/app/223850/3DMark/",
            "tutorial": """🎮 3DMARK - BENCHMARK GPU GAMING

🎯 UTILITÉ
- Mesurer performances GPU gaming
- Stress test stabilité
- Comparer configs gaming
- Voir gain overclock

🔥 TÉLÉCHARGEMENT
→ Steam: "3DMark"
→ Version gratuite (Basic)
→ Suffit pour tests Time Spy

📝 TESTS DISPONIBLES

VERSION GRATUITE:
✅ Time Spy (DX12, 1440p)
✅ Fire Strike (DX11, 1080p)
✅ Night Raid (PC portables)

VERSION PAYANTE (~30€):
- Port Royal (Ray Tracing)
- Stress tests extended
- Loops customisables

📝 UTILISATION

1️⃣ PRÉPARATION
   • Fermer tous les jeux/programmes
   • Drivers GPU à jour
   • Mode Hautes Performances
   • Moniteur sur refresh rate max

2️⃣ LANCER TIME SPY
   • Sélectionner "Time Spy"
   • Cliquer "Run"
   • NE PAS TOUCHER pendant test
   • Durée: 5-7 minutes

3️⃣ LIRE RÉSULTATS
   Score Total:
   • Combine GPU + CPU score
   
   Graphics Score:
   • Performance GPU pure
   • Le plus important
   
   CPU Score:
   • Performances CPU en gaming

4️⃣ COMPARER
   • Cliquer "Compare results online"
   • Voir classement vs configs similaires
   • ±10% = variance normale

💡 SCORES RÉFÉRENCES (Time Spy)

RTX 3060: ~8,500
RTX 3070: ~13,000
RTX 3080: ~17,000
RTX 3090: ~19,000
RTX 4070: ~18,000
RTX 4080: ~28,000
RTX 4090: ~36,000

RX 6600 XT: ~9,000
RX 6700 XT: ~11,500
RX 6800 XT: ~17,000
RX 7900 XTX: ~28,000

📊 TESTS AVANCÉS

OVERCLOCK VALIDATION:
1. Test stock → noter score
2. Overclock GPU (+50 core)
3. Retest → comparer
4. +5% score = bon OC

STRESS TEST STABILITÉ:
- Version payante: "Stress Test"
- OU: Loop test 10x d'affilée
- Si crash = OC instable
- Si throttle = problème cooling

MONITORING:
- MSI Afterburner ouvert
- Voir temps GPU pendant test
- Max safe: 85°C
- > 90°C = revoir cooling

⚠️ VERSION GRATUITE LIMITÉE
- 1 run par test (pas de loops)
- Pas de custom settings
- Mais suffisant pour diagnostics
- Version payante utile si OC hardcore

🎯 AUTRES BENCHMARKS GPU
- Unigine Heaven (gratuit, vieux)
- Unigine Superposition (gratuit)
- Port Royal (Ray Tracing, payant)

⏱️ DURÉE: 10 minutes par test
💰 COÛT: 0€ (Basic) / 30€ (Advanced)
🔧 DIFFICULTÉ: ⭐☆☆☆☆ (Très facile)"""
        }
    ]
}

# ============ BASE DIAGNOSTIC SYMPTÔMES ============
# ============ BASE DIAGNOSTIC SYMPTÔMES ============
SYMPTOM_DATABASE = {
    "slow_boot": {
        "name": "🐌 PC lent au démarrage (> 2 minutes)",
        "solutions": [
            ("Trop d'apps au démarrage", 90, "Gestionnaire tâches > Démarrage > Désactiver apps inutiles"),
            ("Disque dur lent (HDD)", 80, "CrystalDiskInfo: vérifier santé + envisager SSD"),
            ("Mises à jour Windows", 60, "Paramètres > Windows Update > vérifier"),
            ("Drivers obsolètes", 40, "Boîte à outils > Snappy Driver Installer")
        ]
    },
    "freezes": {
        "name": "❄️ Freeze/blocages aléatoires",
        "solutions": [
            ("RAM défectueuse", 85, "MemTest86+ - Test RAM 8h minimum"),
            ("Disque en fin de vie", 75, "CrystalDiskInfo - Vérifier attributs SMART"),
            ("Surchauffe CPU/GPU", 65, "HWiNFO64 - Vérifier températures > 85°C"),
            ("Malwares/virus", 50, "Malwarebytes - Scan complet"),
            ("Drivers GPU corrompus", 45, "DDU puis réinstaller drivers")
        ]
    },
    "bsod": {
        "name": "💙 Écran bleu (BSOD) fréquent",
        "solutions": [
            ("RAM défectueuse", 90, "MemTest86+ URGENT - Tester chaque barrette"),
            ("Drivers incompatibles", 70, "DDU + réinstaller drivers GPU proprement"),
            ("Overclocking instable", 60, "BIOS: Reset paramètres par défaut"),
            ("SSD/HDD corrompu", 55, "CrystalDiskInfo + Victoria scan surface"),
            ("Windows corrompu", 50, "DISM + SFC via Wapinator")
        ]
    },
    "slow_general": {
        "name": "🐢 PC lent en général (toutes tâches)",
        "solutions": [
            ("Disque 100% utilisé", 85, "Gestionnaire tâches > Disque > Identifier processus + SSD upgrade"),
            ("RAM saturée (> 90%)", 80, "Fermer apps inutiles OU upgrade RAM"),
            ("Malwares/bloatware", 70, "Malwarebytes + Désinstaller apps inutiles"),
            ("HDD fragmenté", 60, "Défragmenteur Windows (HDD uniquement, PAS SSD)"),
            ("Processeur trop faible", 40, "Vérifier usage CPU > 80% constant = upgrade CPU")
        ]
    },
    "fps_drops": {
        "name": "🎮 FPS bas ou drops en jeu",
        "solutions": [
            ("GPU sous-performant", 85, "MSI Afterburner: vérifier usage GPU < 95% = bottleneck CPU"),
            ("Drivers GPU obsolètes", 75, "GeForce Experience / AMD Software - MAJ drivers"),
            ("Surchauffe GPU throttling", 70, "HWiNFO64: temp > 85°C = nettoyer ventilateurs"),
            ("CPU bottleneck", 60, "MSI Afterburner: CPU 100% + GPU 60% = upgrade CPU"),
            ("Pas assez de RAM", 55, "< 16 Go pour jeux AAA = upgrade RAM"),
            ("Background apps", 50, "Process Lasso + fermer Discord/Chrome/etc")
        ]
    },
    "stuttering": {
        "name": "⚡ Micro-freezes / Stuttering en jeu",
        "solutions": [
            ("RAM standby mal gérée", 85, "ISLC - Intelligent Standby List Cleaner"),
            ("Latence drivers élevée", 75, "LatencyMon - Identifier driver problématique"),
            ("Disque lent (loading assets)", 70, "CrystalDiskInfo + upgrade SSD NVMe"),
            ("XMP/DOCP désactivé", 60, "BIOS: Activer profil XMP pour RAM"),
            ("Température CPU/GPU throttle", 55, "HWiNFO64: monitoring températures")
        ]
    },
    "overheating": {
        "name": "🔥 Surchauffe (PC chaud/bruyant)",
        "solutions": [
            ("Poussière ventilateurs", 90, "Nettoyer PC avec bombe à air comprimé"),
            ("Pâte thermique sèche", 75, "Remplacer pâte thermique CPU (> 3 ans)"),
            ("Ventilateurs ne tournent pas", 70, "Vérifier câbles + BIOS fan curve"),
            ("Mauvais airflow boîtier", 60, "Vérifier flux: avant=entrée, arrière=sortie"),
            ("Ventirad sous-dimensionné", 50, "Upgrade ventirad si CPU > 85°C constant")
        ]
    },
    "no_internet": {
        "name": "🌐 Pas de connexion internet",
        "solutions": [
            ("Problème routeur/modem", 80, "Redémarrer box internet (débrancher 30s)"),
            ("Drivers réseau manquants", 70, "Gestionnaire périphériques > Carte réseau > MAJ driver"),
            ("DNS incorrect", 60, "Changer DNS: 1.1.1.1 ou 8.8.8.8"),
            ("Câble Ethernet débranché", 55, "Vérifier câble bien clipsé des 2 côtés"),
            ("Mode Avion activé", 50, "Paramètres > Réseau > Désactiver mode avion")
        ]
    },
    "high_ping": {
        "name": "📶 Ping élevé / Lag online",
        "solutions": [
            ("WiFi instable", 85, "Passer en Ethernet câblé (câble Cat6)"),
            ("Background downloads", 75, "Fermer Steam/Epic/Windows Update pendant jeu"),
            ("QoS routeur non configuré", 65, "Interface routeur: activer QoS pour gaming"),
            ("Drivers réseau obsolètes", 60, "Snappy Driver Installer - MAJ drivers réseau"),
            ("Trop loin du routeur WiFi", 55, "Rapprocher PC OU upgrade routeur WiFi 6"),
            ("TCP/IP mal configuré", 50, "TCP Optimizer - Profil Gaming")
        ]
    },
    "audio_issues": {
        "name": "🔊 Problèmes audio (crachements/coupures)",
        "solutions": [
            ("Drivers audio obsolètes", 80, "Snappy Driver Installer - MAJ drivers audio"),
            ("Latence DPC élevée", 75, "LatencyMon - Identifier driver coupable"),
            ("Trop d'améliorations audio", 70, "Panneau config > Son > Propriétés > Désactiver améliorations"),
            ("Sample rate incorrect", 60, "Panneau config > Son > Avancé > Changer à 48kHz 24-bit"),
            ("Périphérique USB défectueux", 50, "Tester autre port USB / autre câble")
        ]
    },
    "usb_not_working": {
        "name": "🔌 Périphériques USB non reconnus",
        "solutions": [
            ("Drivers USB manquants", 80, "Snappy Driver Installer - MAJ drivers USB"),
            ("Port USB défectueux", 75, "Tester autre port USB (préférer arrière PC)"),
            ("USB Selective Suspend", 70, "Panneau config > Alimentation > USB > Désactiver"),
            ("Périphérique nécessite + de puissance", 60, "Utiliser hub USB alimenté"),
            ("Drivers chipset obsolètes", 55, "Site fabricant carte mère: MAJ chipset")
        ]
    },
    "disk_100": {
        "name": "💿 Disque à 100% d'utilisation",
        "solutions": [
            ("Windows Search indexation", 85, "Désactiver indexation (temporaire via Wapinator)"),
            ("Superfetch/SysMain", 75, "Services > SysMain > Arrêter et désactiver"),
            ("Antivirus scan en cours", 70, "Attendre fin scan OU programmer autrement"),
            ("Fichier d'échange (pagefile)", 65, "Si < 16 Go RAM: laisser auto. Si 32+ Go: réduire"),
            ("Disque défaillant", 60, "CrystalDiskInfo + Victoria - Vérifier santé disque")
        ]
    },
    "cpu_100": {
        "name": "⚙️ CPU à 100% constant (hors gaming)",
        "solutions": [
            ("Processus malveillant", 85, "Malwarebytes scan + Gestionnaire tâches identifier processus"),
            ("Windows Update en cours", 70, "Attendre fin MAJ OU programmer autrement"),
            ("Antivirus scan", 65, "Windows Defender: planifier scan aux heures creuses"),
            ("Processus légitime mais lourd", 60, "Process Lasso - Limiter priorité processus"),
            ("Malware crypto-miner", 55, "Malwarebytes + vérifier Task Scheduler tâches suspectes")
        ]
    },
    "no_sound": {
        "name": "🔇 Aucun son",
        "solutions": [
            ("Périphérique audio incorrect", 85, "Barre des tâches > Son > Sélectionner bon périphérique"),
            ("Pilote audio manquant", 75, "Gestionnaire périphériques > Contrôleurs audio > MAJ"),
            ("Service audio arrêté", 70, "Services > Windows Audio > Démarrer"),
            ("Câble/jack mal branché", 65, "Vérifier câbles bien enfoncés (vert = sortie)"),
            ("Drivers Realtek corrompus", 60, "Désinstaller Realtek, redémarrer, réinstaller")
        ]
    },
    "battery_drain": {
        "name": "🔋 Batterie se vide rapidement (laptop)",
        "solutions": [
            ("Luminosité trop élevée", 80, "Réduire luminosité écran à 40-60%"),
            ("Background apps", 75, "Paramètres > Confidentialité > Apps en arrière-plan > Désactiver"),
            ("Mode performances élevées", 70, "Passer en mode 'Économie d'énergie'"),
            ("Batterie usée", 65, "CMD > powercfg /batteryreport > Vérifier capacité < 80% = usure"),
            ("Processus CPU intensif", 60, "Gestionnaire tâches > Identifier processus gourmand")
        ]
    },
    "cant_update_windows": {
        "name": "🔄 Impossible de mettre à jour Windows",
        "solutions": [
            ("Espace disque insuffisant", 85, "Libérer 20+ Go (Nettoyage via Wapinator)"),
            ("Windows Update corrompu", 75, "DISM + SFC via Wapinator Réparation"),
            ("Services WU arrêtés", 70, "Services > Windows Update > Démarrer (auto)"),
            ("Fichiers système corrompus", 65, "Wapinator > Réparation Windows"),
            ("Connexion internet coupée", 60, "Vérifier connexion stable pendant MAJ")
        ]
    },
    "wifi_keeps_disconnecting": {
        "name": "📡 WiFi se déconnecte sans arrêt",
        "solutions": [
            ("Économie d'énergie WiFi active", 85, "Gestionnaire périph > Carte réseau > Gestion alim > Décocher économie"),
            ("Drivers WiFi obsolètes", 75, "Snappy Driver Installer - MAJ drivers WiFi"),
            ("Interférences 2.4GHz", 70, "Passer routeur sur bande 5GHz"),
            ("Signal trop faible", 65, "Rapprocher routeur OU upgrade antenne WiFi"),
            ("Routeur surchargé", 60, "Redémarrer routeur + limiter nb appareils")
        ]
    },
    "blue_light_death": {
        "name": "💡 PC s'allume mais pas d'affichage",
        "solutions": [
            ("Câble moniteur débranché", 80, "Vérifier câble HDMI/DP bien clipsé"),
            ("RAM mal insérée", 75, "Retirer et réinsérer barrettes RAM (clic audible)"),
            ("GPU non détecté", 70, "Retirer et réinsérer carte graphique + câble 8-pin alim"),
            ("Moniteur sur mauvaise source", 65, "Bouton moniteur: changer source HDMI/DP"),
            ("CMOS à reset", 60, "Retirer pile CMOS 5min, remettre, redémarrer")
        ]
    },
    "pc_shuts_down": {
        "name": "🔴 PC s'éteint tout seul",
        "solutions": [
            ("Surchauffe critique", 90, "HWiNFO64: si > 95°C = nettoyer + pâte thermique"),
            ("Alimentation insuffisante", 75, "Vérifier wattage PSU vs consommation GPU+CPU"),
            ("RAM défectueuse", 70, "MemTest86+ - Test complet"),
            ("Câble alimentation loose", 65, "Vérifier tous câbles alim bien branchés"),
            ("Carte mère défectueuse", 50, "Si autres tests OK = probable CM défectueuse")
        ]
    },
    "windows_activation": {
        "name": "🔑 Windows non activé",
        "solutions": [
            ("Clé Windows invalide", 80, "Paramètres > Activation > Changer clé produit"),
            ("Clé OEM après changement CM", 75, "Contacter support Microsoft pour transfert licence"),
            ("Pas de clé Windows", 70, "Acheter licence Windows (éviter sites louches)"),
            ("Serveurs activation indisponibles", 60, "Réessayer activation dans quelques heures"),
            ("Windows installé sans clé", 55, "Paramètres > Activation > Entrer clé valide")
        ]
    }
}

# ============ FENÊTRE PARAMÈTRES ============
class SettingsWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Paramètres")
        self.setFixedSize(380, 850)
        self.setWindowFlags(Qt.WindowType.Dialog)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titre
        title = QLabel("⚙️ PARAMÈTRES")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Interval refresh
        interval_label = QLabel("⏱️  Interval rafraîchissement:")
        interval_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(interval_label)
        
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setMinimum(5)
        self.interval_slider.setMaximum(60)
        self.interval_slider.setValue(parent.refresh_interval // 1000)
        self.interval_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.interval_slider.setTickInterval(5)
        
        self.interval_value = QLabel(f"{parent.refresh_interval // 1000}s")
        self.interval_value.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.interval_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.interval_slider.valueChanged.connect(
            lambda v: self.interval_value.setText(f"{v}s")
        )
        
        layout.addWidget(self.interval_slider)
        layout.addWidget(self.interval_value)
        
        # Mode performance
        perf_label = QLabel("⚡ Mode performance:")
        perf_label.setFont(QFont("Segoe UI", 10))
        perf_label.setToolTip("Refresh plus lent (30s) pour économiser ressources")
        layout.addWidget(perf_label)
        
        # Boutons
        self.create_button(layout, "🎮 Mode Gaming", self.open_gaming_optimizer, "#FF6B00")
        self.create_button(layout, "🗑️ Désinstaller Apps", self.open_uninstaller, "#F44336")
        self.create_button(layout, "🧰 Boîte à outils", self.open_toolbox, "#00BCD4")
        self.create_button(layout, "🩺 Diagnostic", self.open_diagnostic, "#E91E63")
        self.create_button(layout, "🔧 Outils Avancés", self.open_advanced_tools, "#9C27B0")
        self.create_button(layout, "📸 Export rapport", self.export_report, "#9C27B0")
        self.create_button(layout, "🧹 Nettoyage", self.cleanup, "#2196F3")
        self.create_button(layout, "🔧 Réparer", self.repair, "#FF9800")
        self.create_button(layout, "📦 MAJ Winget", self.update, "#9C27B0")
        self.create_button(layout, "🌐 Test Réseau", self.network_test, "#00BCD4")
        self.create_button(layout, "❓ Aide", self.show_help, "#795548")
        self.create_button(layout, "❌ Quitter", self.quit_app, "#F44336")
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 10px;
                background: #2b2b2b;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                border: 2px solid #333;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
        """)
    
    def create_button(self, layout, text, callback, color):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.setMinimumHeight(42)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color}, stop:1 {self.adjust_color(color, -30)});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background: {self.adjust_color(color, -20)};
            }}
            QPushButton:pressed {{
                background: {self.adjust_color(color, -40)};
            }}
        """)
        btn.clicked.connect(callback)
        layout.addWidget(btn)
    
    def adjust_color(self, hex_color, amount):
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        l = max(0, min(255, l + amount))
        color.setHsl(h, s, l, a)
        return color.name()
    
    
    def cleanup(self):
        # Vérifier admin AVANT de fermer le dialog
        if not is_admin():
            reply = QMessageBox.question(
                self, "⚠️  Admin requis",
                "Le nettoyage nécessite les droits administrateur.\n\nRelancer l'application en mode admin ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Relancer en admin
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1
                    )
                    QApplication.quit()
                except:
                    QMessageBox.showerror("Erreur", "Impossible de relancer en mode admin")
            return
        
        # Si admin OK, continuer
        self.close()
        self.parent_window.run_task("cleanup", "🧹 Nettoyage Windows")
    
    def repair(self):
        # Vérifier admin AVANT de fermer le dialog
        if not is_admin():
            reply = QMessageBox.question(
                self, "⚠️  Admin requis",
                "La réparation nécessite les droits administrateur.\n\nRelancer l'application en mode admin ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Relancer en admin
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1
                    )
                    QApplication.quit()
                except:
                    QMessageBox.showerror("Erreur", "Impossible de relancer en mode admin")
            return
        
        # Si admin OK, continuer
        self.close()
        self.parent_window.run_task("repair", "🔧 Réparation Windows")
    
    def update(self):
        self.close()
        self.parent_window.run_task("update", "📦 Mise à jour Winget")
    
    def network_test(self):
        self.close()
        self.parent_window.run_task("network", "🌐 Test Réseau Complet")
    
    def open_toolbox(self):
        self.close()
        toolbox = ToolboxWindow(self.parent_window)
        toolbox.exec()
    
    def open_diagnostic(self):
        self.close()
        diagnostic = DiagnosticWindow(self.parent_window)
        diagnostic.exec()

    def open_advanced_tools(self):
        self.close()
        try:
            from modules.advanced_tools_window import AdvancedToolsWindow
            advanced = AdvancedToolsWindow(self.parent_window)
            advanced.exec()
        except ImportError:
            QMessageBox.warning(
                self,
                "⚠️ Modules non installés",
                "Les modules avancés ne sont pas installés.\n\nTéléchargez le dossier 'modules' depuis GitHub."
            )
    
    def export_report(self):
        self.close()
        self.parent_window.export_report()
    
    def open_uninstaller(self):
        self.close()
        uninstaller = UninstallerWindow(self.parent_window)
        uninstaller.exec()
    
    def open_gaming_optimizer(self):
        self.close()
        gaming = GamingOptimizerWindow(self.parent_window)
        gaming.exec()
    
    def show_help(self):
        help_text = """🔧 AIDE - PC WIDGET

📦 WINGET : Préinstallé Windows 10/11
   Si absent: Microsoft Store > "App Installer"

👤 MODE ADMIN : Clic droit exe > "Exécuter en admin"

⚙️  RACCOURCIS :
   • F5 : Refresh manuel
   • Echap : Fermer paramètres

Ouvrir documentation ?"""
        
        reply = QMessageBox.question(
            self, "Aide",
            help_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open("https://github.com")
    
    def quit_app(self):
        QApplication.quit()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

# ============ FENÊTRE BOÎTE À OUTILS ============
class ToolboxWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🧰 Boîte à outils")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        from PyQt6.QtWidgets import QTabWidget, QListWidget, QTextBrowser, QPushButton, QListWidgetItem
        
        tabs = QTabWidget()
        
        # Onglet Réparation
        repair_widget = QWidget()
        repair_layout = QHBoxLayout()
        
        repair_list = QListWidget()
        for tool in TOOLS_DATABASE["repair"]:
            item = QListWidgetItem(f"{tool['name']} ({tool['type']})")
            item.setData(Qt.ItemDataRole.UserRole, tool)
            repair_list.addItem(item)
        
        repair_info = QTextBrowser()
        repair_info.setOpenExternalLinks(True)
        
        def show_repair_info(item):
            tool = item.data(Qt.ItemDataRole.UserRole)
            html = f"""
            <h2>{tool['name']}</h2>
            <p><b>Type:</b> {tool['type']}</p>
            <p><b>Description:</b> {tool['desc']}</p>
            <p><b>📥 Téléchargement:</b> <a href='{tool['url']}'>{tool['url']}</a></p>
            <hr>
            <pre style='white-space: pre-wrap; font-family: Consolas;'>{tool['tutorial']}</pre>
            """
            repair_info.setHtml(html)
        
        repair_list.currentItemChanged.connect(lambda curr, prev: show_repair_info(curr) if curr else None)
        
        repair_layout.addWidget(repair_list, 1)
        repair_layout.addWidget(repair_info, 2)
        repair_widget.setLayout(repair_layout)
        
        tabs.addTab(repair_widget, "🔧 Réparation & Diagnostic")
        
        # Onglet Gaming (similaire)
        gaming_widget = QWidget()
        gaming_layout = QHBoxLayout()
        
        gaming_list = QListWidget()
        for tool in TOOLS_DATABASE["gaming"]:
            item = QListWidgetItem(f"{tool['name']} ({tool['type']})")
            item.setData(Qt.ItemDataRole.UserRole, tool)
            gaming_list.addItem(item)
        
        gaming_info = QTextBrowser()
        gaming_info.setOpenExternalLinks(True)
        
        def show_gaming_info(item):
            tool = item.data(Qt.ItemDataRole.UserRole)
            html = f"""
            <h2>{tool['name']}</h2>
            <p><b>Type:</b> {tool['type']}</p>
            <p><b>Description:</b> {tool['desc']}</p>
            <p><b>📥 Téléchargement:</b> <a href='{tool['url']}'>{tool['url']}</a></p>
            <hr>
            <pre style='white-space: pre-wrap; font-family: Consolas;'>{tool['tutorial']}</pre>
            """
            gaming_info.setHtml(html)
        
        gaming_list.currentItemChanged.connect(lambda curr, prev: show_gaming_info(curr) if curr else None)
        
        gaming_layout.addWidget(gaming_list, 1)
        gaming_layout.addWidget(gaming_info, 2)
        gaming_widget.setLayout(gaming_layout)
        
        tabs.addTab(gaming_widget, "🎮 Gaming & Performances")
		
		# Onglet Network
        network_widget = QWidget()
        network_layout = QHBoxLayout()
        
        network_list = QListWidget()
        for tool in TOOLS_DATABASE["network"]:
            item = QListWidgetItem(f"{tool['name']} ({tool['type']})")
            item.setData(Qt.ItemDataRole.UserRole, tool)
            network_list.addItem(item)
        
        network_info = QTextBrowser()
        network_info.setOpenExternalLinks(True)
        
        def show_network_info(item):
            tool = item.data(Qt.ItemDataRole.UserRole)
            html = f"""
            <h2>{tool['name']}</h2>
            <p><b>Type:</b> {tool['type']}</p>
            <p><b>Description:</b> {tool['desc']}</p>
            <p><b>🔥 Téléchargement:</b> <a href='{tool['url']}'>{tool['url']}</a></p>
            <hr>
            <pre style='white-space: pre-wrap; font-family: Consolas;'>{tool['tutorial']}</pre>
            """
            network_info.setHtml(html)
        
        network_list.currentItemChanged.connect(lambda curr, prev: show_network_info(curr) if curr else None)
        
        network_layout.addWidget(network_list, 1)
        network_layout.addWidget(network_info, 2)
        network_widget.setLayout(network_layout)
        
        tabs.addTab(network_widget, "🌐 Réseau & Connexion")
        
        # Onglet Benchmark
        benchmark_widget = QWidget()
        benchmark_layout = QHBoxLayout()
        
        benchmark_list = QListWidget()
        for tool in TOOLS_DATABASE["benchmark"]:
            item = QListWidgetItem(f"{tool['name']} ({tool['type']})")
            item.setData(Qt.ItemDataRole.UserRole, tool)
            benchmark_list.addItem(item)
        
        benchmark_info = QTextBrowser()
        benchmark_info.setOpenExternalLinks(True)
        
        def show_benchmark_info(item):
            tool = item.data(Qt.ItemDataRole.UserRole)
            html = f"""
            <h2>{tool['name']}</h2>
            <p><b>Type:</b> {tool['type']}</p>
            <p><b>Description:</b> {tool['desc']}</p>
            <p><b>🔥 Téléchargement:</b> <a href='{tool['url']}'>{tool['url']}</a></p>
            <hr>
            <pre style='white-space: pre-wrap; font-family: Consolas;'>{tool['tutorial']}</pre>
            """
            benchmark_info.setHtml(html)
        
        benchmark_list.currentItemChanged.connect(lambda curr, prev: show_benchmark_info(curr) if curr else None)
        
        benchmark_layout.addWidget(benchmark_list, 1)
        benchmark_layout.addWidget(benchmark_info, 2)
        benchmark_widget.setLayout(benchmark_layout)
        
        tabs.addTab(benchmark_widget, "📊 Benchmark & Tests")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTabWidget::pane { border: 1px solid #444; background: #2b2b2b; }
            QTabBar::tab { background: #2b2b2b; color: white; padding: 10px; }
            QTabBar::tab:selected { background: #4CAF50; }
            QListWidget { background: #2b2b2b; color: white; border: 1px solid #444; }
            QListWidget::item:selected { background: #4CAF50; }
            QTextBrowser { background: #1e1e1e; color: white; border: 1px solid #444; }
        """)

# ============ FENÊTRE MODE GAMING ============
class GamingOptimizerWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🎮 Optimiseur Mode Gaming")
        self.setMinimumSize(800, 700)
        
        from PyQt6.QtWidgets import QRadioButton, QCheckBox, QButtonGroup, QGroupBox
        
        self.parent_window = parent
        self.optimizations = {}
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("⚠️ Ces optimisations améliorent les performances gaming")
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(header)
        
        warning = QLabel("Toutes les modifications sont réversibles via le bouton 'Restaurer'")
        warning.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(warning)
        
        # Profils
        profile_group = QGroupBox("📋 PROFILS PRÉ-CONFIGURÉS")
        profile_layout = QVBoxLayout()
        
        self.profile_buttons = QButtonGroup()
        
        self.profile_none = QRadioButton("⚪ Aucun (Windows par défaut)")
        self.profile_light = QRadioButton("🟢 Gaming Léger (recommandé)")
        self.profile_full = QRadioButton("🟡 Gaming Complet")
        self.profile_competitive = QRadioButton("🔴 Compétitif / E-Sport")
        
        self.profile_buttons.addButton(self.profile_none, 0)
        self.profile_buttons.addButton(self.profile_light, 1)
        self.profile_buttons.addButton(self.profile_full, 2)
        self.profile_buttons.addButton(self.profile_competitive, 3)
        
        profile_layout.addWidget(self.profile_none)
        profile_layout.addWidget(self.profile_light)
        profile_layout.addWidget(QLabel("   → Souris, Hautes Perfs, Effets visuels, Game Bar"))
        profile_layout.addWidget(self.profile_full)
        profile_layout.addWidget(QLabel("   → Tout du Léger + Transparence, Indexation"))
        profile_layout.addWidget(self.profile_competitive)
        profile_layout.addWidget(QLabel("   → Tout du Complet + Ultimate Performance, Nagle off"))
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Optimisations détaillées
        details_group = QGroupBox("🔧 OPTIMISATIONS DÉTAILLÉES (personnaliser)")
        details_layout = QVBoxLayout()
        
        # Créer les checkboxes
        self.opt_mouse = QCheckBox("🖱️ Désactiver accélération souris")
        self.opt_power = QCheckBox("⚡ Mode alimentation Hautes Performances")
        self.opt_ultimate = QCheckBox("🚀 Mode Ultimate Performance (max)")
        self.opt_visual = QCheckBox("🎨 Désactiver effets visuels & animations")
        self.opt_transparency = QCheckBox("💎 Désactiver transparence")
        self.opt_gamebar = QCheckBox("🎮 Désactiver Game Bar & Game DVR")
        self.opt_indexing = QCheckBox("📁 Désactiver indexation (temporaire)")
        self.opt_screensaver = QCheckBox("🖥️ Désactiver économiseur d'écran")
        self.opt_nagle = QCheckBox("🌐 Désactiver Nagle's Algorithm (latence réseau)")
        
        for opt in [self.opt_mouse, self.opt_power, self.opt_ultimate, self.opt_visual,
                    self.opt_transparency, self.opt_gamebar, self.opt_indexing,
                    self.opt_screensaver, self.opt_nagle]:
            details_layout.addWidget(opt)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Connecter les profils
        self.profile_buttons.buttonClicked.connect(self.apply_profile)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        detect_btn = QPushButton("🔍 Détecter état actuel")
        detect_btn.clicked.connect(self.detect_current_state)
        detect_btn.setStyleSheet("background: #607D8B; color: white; padding: 10px;")
        btn_layout.addWidget(detect_btn)
        
        btn_layout.addStretch()
        
        restore_btn = QPushButton("🔄 RESTAURER DÉFAUT")
        restore_btn.clicked.connect(self.restore_defaults)
        restore_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                padding: 12px 20px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background: #F57C00; }
        """)
        btn_layout.addWidget(restore_btn)
        
        apply_btn = QPushButton("✅ APPLIQUER LES OPTIMISATIONS")
        apply_btn.clicked.connect(self.apply_optimizations)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                padding: 12px 30px;
                font-weight: bold;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QGroupBox {
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox, QRadioButton { color: white; padding: 4px; }
            QLabel { color: white; }
        """)
        
        # Détecter l'état au démarrage
        QTimer.singleShot(100, self.detect_current_state)
    
    def apply_profile(self, button):
        """Appliquer un profil pré-configuré"""
        profile_id = self.profile_buttons.id(button)
        
        # Décocher tout d'abord
        for opt in [self.opt_mouse, self.opt_power, self.opt_ultimate, self.opt_visual,
                    self.opt_transparency, self.opt_gamebar, self.opt_indexing,
                    self.opt_screensaver, self.opt_nagle]:
            opt.setChecked(False)
        
        if profile_id == 0:  # Aucun
            pass
        elif profile_id == 1:  # Léger
            self.opt_mouse.setChecked(True)
            self.opt_power.setChecked(True)
            self.opt_visual.setChecked(True)
            self.opt_gamebar.setChecked(True)
        elif profile_id == 2:  # Complet
            self.opt_mouse.setChecked(True)
            self.opt_power.setChecked(True)
            self.opt_visual.setChecked(True)
            self.opt_gamebar.setChecked(True)
            self.opt_transparency.setChecked(True)
            self.opt_indexing.setChecked(True)
            self.opt_screensaver.setChecked(True)
        elif profile_id == 3:  # Compétitif
            self.opt_mouse.setChecked(True)
            self.opt_ultimate.setChecked(True)
            self.opt_visual.setChecked(True)
            self.opt_gamebar.setChecked(True)
            self.opt_transparency.setChecked(True)
            self.opt_indexing.setChecked(True)
            self.opt_screensaver.setChecked(True)
            self.opt_nagle.setChecked(True)
    
    def detect_current_state(self):
        """Détecter l'état actuel des optimisations"""
        try:
            import winreg
            
            # Souris
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse")
                mouse_speed, _ = winreg.QueryValueEx(key, "MouseSpeed")
                self.opt_mouse.setChecked(mouse_speed == "0")
                winreg.CloseKey(key)
            except:
                pass
            
            # Game Bar
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR")
                app_capture, _ = winreg.QueryValueEx(key, "AppCaptureEnabled")
                self.opt_gamebar.setChecked(app_capture == 0)
                winreg.CloseKey(key)
            except:
                pass
            
            # Transparence
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                transparency, _ = winreg.QueryValueEx(key, "EnableTransparency")
                self.opt_transparency.setChecked(transparency == 0)
                winreg.CloseKey(key)
            except:
                pass
            
            # Effets visuels
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")
                visual_fx, _ = winreg.QueryValueEx(key, "VisualFXSetting")
                self.opt_visual.setChecked(visual_fx == 2)
                winreg.CloseKey(key)
            except:
                pass
        
        except Exception as e:
            print(f"Erreur détection: {e}")
    
    def apply_optimizations(self):
        """Appliquer les optimisations sélectionnées"""
        selected = []
        
        if self.opt_mouse.isChecked():
            selected.append("mouse")
        if self.opt_power.isChecked():
            selected.append("power")
        if self.opt_ultimate.isChecked():
            selected.append("ultimate")
        if self.opt_visual.isChecked():
            selected.append("visual")
        if self.opt_transparency.isChecked():
            selected.append("transparency")
        if self.opt_gamebar.isChecked():
            selected.append("gamebar")
        if self.opt_indexing.isChecked():
            selected.append("indexing")
        if self.opt_screensaver.isChecked():
            selected.append("screensaver")
        if self.opt_nagle.isChecked():
            selected.append("nagle")
        
        if not selected:
            QMessageBox.warning(self, "⚠️ Aucune sélection", "Veuillez cocher au moins une optimisation")
            return
        
        # Confirmation
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation",
            f"Appliquer {len(selected)} optimisation(s) ?\n\nVous pourrez restaurer les paramètres par défaut à tout moment.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Appliquer
        self.close()
        log_window = LogWindow("🎮 Optimisations Gaming")
        log_window.show()
        
        log_window.log("╔" + "═"*48 + "╗")
        log_window.log("║" + " "*10 + "🎮 OPTIMISATION GAMING" + " "*16 + "║")
        log_window.log("╚" + "═"*48 + "╝\n")
        
        success = 0
        failed = 0
        
        for opt in selected:
            log_window.log(f"\n📝 Application: {opt}")
            try:
                if self.apply_single_optimization(opt, log_window):
                    success += 1
                    log_window.log(f"✅ {opt} appliqué")
                else:
                    failed += 1
                    log_window.log(f"❌ {opt} échoué")
            except Exception as e:
                failed += 1
                log_window.log(f"❌ Erreur {opt}: {str(e)}")
            
            QApplication.processEvents()
        
        # Résumé
        log_window.log("\n" + "╔" + "═"*48 + "╗")
        log_window.log("║" + " "*15 + "✅ TERMINÉ" + " "*21 + "║")
        log_window.log("╚" + "═"*48 + "╝")
        log_window.log(f"\n✅ Succès: {success}")
        log_window.log(f"❌ Échecs: {failed}")
        log_window.log("\n💡 IMPORTANT: Redémarrez Windows pour que tous les changements prennent effet")
        
        QMessageBox.information(
            log_window,
            "✅ Terminé",
            f"Optimisations appliquées !\n\n✅ Succès: {success}\n❌ Échecs: {failed}\n\n💡 Redémarrez Windows"
        )
    
    def apply_single_optimization(self, opt_name, log_window):
        """Appliquer une optimisation spécifique"""
        import winreg
        
        try:
            if opt_name == "mouse":
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse")
                winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "0")
                winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "0")
                winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "0")
                winreg.CloseKey(key)
                return True
            
            elif opt_name == "power":
                subprocess.run(["powercfg", "-duplicatescheme", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], 
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                subprocess.run(["powercfg", "/s", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                return True
            
            elif opt_name == "ultimate":
                subprocess.run(["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                subprocess.run(["powercfg", "/s", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                return True
            
            elif opt_name == "visual":
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")
                winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
                winreg.CloseKey(key)
                
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics")
                winreg.SetValueEx(key, "MinAnimate", 0, winreg.REG_SZ, "0")
                winreg.CloseKey(key)
                return True
            
            elif opt_name == "transparency":
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                return True
            
            elif opt_name == "gamebar":
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR")
                winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
                winreg.SetValueEx(key, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                return True
            
            elif opt_name == "indexing":
                subprocess.run(["sc", "config", "WSearch", "start=disabled"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                subprocess.run(["net", "stop", "WSearch"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                return True
            
            elif opt_name == "screensaver":
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
                winreg.SetValueEx(key, "ScreenSaveActive", 0, winreg.REG_SZ, "0")
                winreg.CloseKey(key)
                return True
            
            elif opt_name == "nagle":
                # Cette optimisation est complexe, on la skip pour l'instant
                log_window.log("⚠️ Nagle: nécessite détection interfaces réseau")
                return False
            
            return False
        
        except Exception as e:
            log_window.log(f"Erreur: {str(e)}")
            return False
    
    def restore_defaults(self):
        """Restaurer les paramètres par défaut Windows"""
        reply = QMessageBox.question(
            self,
            "⚠️ Restaurer les défauts",
            "Restaurer TOUS les paramètres Windows par défaut ?\n\nCela annulera toutes les optimisations gaming.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.close()
        log_window = LogWindow("🔄 Restauration")
        log_window.show()
        
        log_window.log("🔄 Restauration des paramètres par défaut...\n")
        
        import winreg
        
        # Souris
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse")
            winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "6")
            winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "10")
            winreg.CloseKey(key)
            log_window.log("✅ Souris restaurée")
        except:
            log_window.log("❌ Souris erreur")
        
        # Alimentation
        try:
            subprocess.run(["powercfg", "/s", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                         capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            log_window.log("✅ Alimentation Équilibrée")
        except:
            log_window.log("❌ Alimentation erreur")
        
        # Effets visuels
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics")
            winreg.SetValueEx(key, "MinAnimate", 0, winreg.REG_SZ, "1")
            winreg.CloseKey(key)
            log_window.log("✅ Effets visuels restaurés")
        except:
            log_window.log("❌ Effets visuels erreur")
        
        # Transparence
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_window.log("✅ Transparence restaurée")
        except:
            log_window.log("❌ Transparence erreur")
        
        # Game Bar
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR")
            winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
            winreg.SetValueEx(key, "GameDVR_Enabled", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_window.log("✅ Game Bar restauré")
        except:
            log_window.log("❌ Game Bar erreur")
        
        # Indexation
        try:
            subprocess.run(["sc", "config", "WSearch", "start=auto"],
                         capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            subprocess.run(["net", "start", "WSearch"],
                         capture_output=True, creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            log_window.log("✅ Indexation restaurée")
        except:
            log_window.log("❌ Indexation erreur")
        
        log_window.log("\n✅ Restauration terminée !")
        log_window.log("💡 Redémarrez Windows pour finaliser")
        
        QMessageBox.information(log_window, "✅ Terminé", "Paramètres restaurés !\n\n💡 Redémarrez Windows")

# ============ FENÊTRE MODE GAMING ============
class GamingOptimizerWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🎮 Optimiseur Mode Gaming")
        self.setMinimumSize(950, 700)
        
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup, QCheckBox, QGroupBox, QScrollArea
        
        self.parent_window = parent
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("⚡ Optimisations Gaming - 100% Vérifiées et Sûres")
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(header)
        
        warning = QLabel("⚠️ Toutes les modifications sont réversibles • Cliquez 'Appliquer' pour activer")
        warning.setStyleSheet("color: #FF9800; font-size: 11px;")
        layout.addWidget(warning)
        
        # Profils
        profile_group = QGroupBox("📋 Profils Pré-configurés")
        profile_layout = QVBoxLayout()
        
        self.profile_buttons = QButtonGroup()
        
        self.profile_none = QRadioButton("⚪ Aucun (Windows par défaut)")
        self.profile_none.setToolTip("Aucune optimisation active")
        self.profile_buttons.addButton(self.profile_none, 0)
        profile_layout.addWidget(self.profile_none)
        
        self.profile_light = QRadioButton("⭐ Gaming Léger (Recommandé)")
        self.profile_light.setToolTip("Souris + Performances + Game Bar off\nImpact: +10-20% perfs")
        self.profile_buttons.addButton(self.profile_light, 1)
        profile_layout.addWidget(self.profile_light)
        
        self.profile_full = QRadioButton("⭐⭐ Gaming Complet")
        self.profile_full.setToolTip("Léger + Visuels + Transparence off\nImpact: +15-25% perfs")
        self.profile_buttons.addButton(self.profile_full, 2)
        profile_layout.addWidget(self.profile_full)
        
        self.profile_competitive = QRadioButton("⭐⭐⭐ Compétitif (E-Sport)")
        self.profile_competitive.setToolTip("Complet + Ultimate Performance\nImpact: +20-30% perfs, latence minimale")
        self.profile_buttons.addButton(self.profile_competitive, 3)
        profile_layout.addWidget(self.profile_competitive)
        
        self.profile_buttons.buttonClicked.connect(self.on_profile_selected)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Zone de scroll pour les checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Optimisations individuelles
        self.checkboxes = {}
        
        # SOURIS
        mouse_group = QGroupBox("🖱️ SOURIS & PRÉCISION")
        mouse_layout = QVBoxLayout()
        
        self.checkboxes['mouse_accel'] = QCheckBox("Désactiver accélération souris")
        self.checkboxes['mouse_accel'].setToolTip("Contrôle 1:1 pour gaming précis (FPS, MOBA)")
        mouse_layout.addWidget(self.checkboxes['mouse_accel'])
        
        self.checkboxes['sticky_keys'] = QCheckBox("Désactiver touches rémanentes")
        self.checkboxes['sticky_keys'].setToolTip("Évite les popups pendant le jeu")
        mouse_layout.addWidget(self.checkboxes['sticky_keys'])
        
        mouse_group.setLayout(mouse_layout)
        scroll_layout.addWidget(mouse_group)
        
        # PERFORMANCES
        perf_group = QGroupBox("⚡ PERFORMANCES")
        perf_layout = QVBoxLayout()
        
        self.checkboxes['high_performance'] = QCheckBox("Mode Alimentation Hautes Performances")
        self.checkboxes['high_performance'].setToolTip("CPU/GPU à pleine puissance")
        perf_layout.addWidget(self.checkboxes['high_performance'])
        
        self.checkboxes['ultimate_performance'] = QCheckBox("Mode Ultimate Performance (bonus)")
        self.checkboxes['ultimate_performance'].setToolTip("Plan caché Microsoft pour workstations")
        perf_layout.addWidget(self.checkboxes['ultimate_performance'])
        
        self.checkboxes['disable_sleep'] = QCheckBox("Désactiver mise en veille automatique")
        self.checkboxes['disable_sleep'].setToolTip("Empêche l'ordi de se mettre en veille pendant jeu")
        perf_layout.addWidget(self.checkboxes['disable_sleep'])
        
        perf_group.setLayout(perf_layout)
        scroll_layout.addWidget(perf_group)
        
        # VISUELS
        visual_group = QGroupBox("🎨 INTERFACE & VISUELS")
        visual_layout = QVBoxLayout()
        
        self.checkboxes['visual_effects'] = QCheckBox("Désactiver effets visuels (animations)")
        self.checkboxes['visual_effects'].setToolTip("Gain: +5-15% FPS, interface instantanée")
        visual_layout.addWidget(self.checkboxes['visual_effects'])
        
        self.checkboxes['transparency'] = QCheckBox("Désactiver transparence")
        self.checkboxes['transparency'].setToolTip("Gain: +1-3% FPS")
        visual_layout.addWidget(self.checkboxes['transparency'])
        
        self.checkboxes['game_bar'] = QCheckBox("Désactiver Xbox Game Bar")
        self.checkboxes['game_bar'].setToolTip("Gain: +3-8% FPS, plus de popup Win+G")
        visual_layout.addWidget(self.checkboxes['game_bar'])
        
        self.checkboxes['game_dvr'] = QCheckBox("Désactiver Game DVR (enregistrement)")
        self.checkboxes['game_dvr'].setToolTip("Stop l'enregistrement en arrière-plan")
        visual_layout.addWidget(self.checkboxes['game_dvr'])
        
        visual_group.setLayout(visual_layout)
        scroll_layout.addWidget(visual_group)
        
        # SYSTÈME
        system_group = QGroupBox("🔧 SYSTÈME")
        system_layout = QVBoxLayout()
        
        self.checkboxes['disable_indexing'] = QCheckBox("Désactiver indexation (temporaire)")
        self.checkboxes['disable_indexing'].setToolTip("⚠️ Recherche Windows plus lente")
        system_layout.addWidget(self.checkboxes['disable_indexing'])
        
        self.checkboxes['disable_prefetch'] = QCheckBox("Désactiver Prefetch/Superfetch")
        self.checkboxes['disable_prefetch'].setToolTip("Utile surtout sur SSD")
        system_layout.addWidget(self.checkboxes['disable_prefetch'])
        
        system_group.setLayout(system_layout)
        scroll_layout.addWidget(system_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # État actuel
        self.status_label = QLabel("📊 Détection de l'état actuel...")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        detect_btn = QPushButton("🔍 Détecter État Actuel")
        detect_btn.clicked.connect(self.detect_current_state)
        detect_btn.setStyleSheet("background: #2196F3; color: white; padding: 10px; border-radius: 5px;")
        btn_layout.addWidget(detect_btn)
        
        btn_layout.addStretch()
        
        self.apply_btn = QPushButton("✅ APPLIQUER LES OPTIMISATIONS")
        self.apply_btn.clicked.connect(self.apply_optimizations)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
        """)
        btn_layout.addWidget(self.apply_btn)
        
        self.restore_btn = QPushButton("🔄 RESTAURER PAR DÉFAUT")
        self.restore_btn.clicked.connect(self.restore_defaults)
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #F57C00; }
        """)
        btn_layout.addWidget(self.restore_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QGroupBox {
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox, QRadioButton {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        
        # Détecter l'état au démarrage
        QTimer.singleShot(100, self.detect_current_state)
    
    def on_profile_selected(self, button):
        """Cocher les cases selon le profil sélectionné"""
        profile_id = self.profile_buttons.id(button)
        
        # Décocher tout
        for cb in self.checkboxes.values():
            cb.setChecked(False)
        
        if profile_id == 0:  # Aucun
            pass
        
        elif profile_id == 1:  # Léger
            self.checkboxes['mouse_accel'].setChecked(True)
            self.checkboxes['sticky_keys'].setChecked(True)
            self.checkboxes['high_performance'].setChecked(True)
            self.checkboxes['game_bar'].setChecked(True)
            self.checkboxes['game_dvr'].setChecked(True)
        
        elif profile_id == 2:  # Complet
            # Tout du léger
            self.checkboxes['mouse_accel'].setChecked(True)
            self.checkboxes['sticky_keys'].setChecked(True)
            self.checkboxes['high_performance'].setChecked(True)
            self.checkboxes['game_bar'].setChecked(True)
            self.checkboxes['game_dvr'].setChecked(True)
            # Plus
            self.checkboxes['visual_effects'].setChecked(True)
            self.checkboxes['transparency'].setChecked(True)
            self.checkboxes['disable_sleep'].setChecked(True)
        
        elif profile_id == 3:  # Compétitif
            # Tout coché
            for cb in self.checkboxes.values():
                cb.setChecked(True)
            # Sauf ultimate perf (on met high perf à la place)
            self.checkboxes['ultimate_performance'].setChecked(True)
            self.checkboxes['high_performance'].setChecked(False)
    
    def detect_current_state(self):
        """Détecter quelles optimisations sont déjà actives"""
        self.status_label.setText("🔍 Détection en cours...")
        QApplication.processEvents()
        
        active = []
        
        try:
            import winreg
            
            # Mouse accel
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse")
                speed = winreg.QueryValueEx(key, "MouseSpeed")[0]
                if speed == "0":
                    active.append("Souris sans accélération")
                winreg.CloseKey(key)
            except:
                pass
            
            # Transparence
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                trans = winreg.QueryValueEx(key, "EnableTransparency")[0]
                if trans == 0:
                    active.append("Transparence désactivée")
                winreg.CloseKey(key)
            except:
                pass
            
            # Game Bar
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR")
                dvr = winreg.QueryValueEx(key, "AppCaptureEnabled")[0]
                if dvr == 0:
                    active.append("Game Bar désactivé")
                winreg.CloseKey(key)
            except:
                pass
            
        except Exception as e:
            self.status_label.setText(f"❌ Erreur détection: {str(e)}")
            return
        
        if active:
            self.status_label.setText(f"✅ Actif: {', '.join(active)}")
        else:
            self.status_label.setText("📊 Aucune optimisation détectée (Windows par défaut)")
    
    def apply_optimizations(self):
        """Appliquer les optimisations sélectionnées"""
        selected = [name for name, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not selected:
            QMessageBox.warning(self, "⚠️", "Aucune optimisation sélectionnée !")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Appliquer {len(selected)} optimisation(s) ?\n\nToutes les modifications sont réversibles.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Fenêtre de logs
        log_window = LogWindow(self, "🎮 Application des optimisations")
        log_window.show()
        
        success = 0
        failed = 0
        
        import winreg
        
        for opt_name in selected:
            log_window.log(f"\n⚙️ {opt_name}...")
            
            try:
                if opt_name == 'mouse_accel':
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "0")
                    winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "0")
                    winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "0")
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Accélération souris désactivée")
                    success += 1
                
                elif opt_name == 'sticky_keys':
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Accessibility\StickyKeys")
                    winreg.SetValueEx(key, "Flags", 0, winreg.REG_SZ, "506")
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Touches rémanentes désactivées")
                    success += 1
                
                elif opt_name == 'high_performance':
                    result = subprocess.run(
                        ["powercfg", "-duplicatescheme", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                        capture_output=True,
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    subprocess.run(
                        ["powercfg", "/s", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    log_window.log("  ✅ Mode Hautes Performances activé")
                    success += 1
                
                elif opt_name == 'ultimate_performance':
                    subprocess.run(
                        ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
                        capture_output=True,
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    subprocess.run(
                        ["powercfg", "/s", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    log_window.log("  ✅ Ultimate Performance activé")
                    success += 1
                
                elif opt_name == 'disable_sleep':
                    subprocess.run(
                        ["powercfg", "/change", "standby-timeout-ac", "0"],
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    log_window.log("  ✅ Veille désactivée")
                    success += 1
                
                elif opt_name == 'visual_effects':
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")
                    winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
                    winreg.CloseKey(key)
                    
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics")
                    winreg.SetValueEx(key, "MinAnimate", 0, winreg.REG_SZ, "0")
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Effets visuels désactivés")
                    success += 1
                
                elif opt_name == 'transparency':
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Transparence désactivée")
                    success += 1
                
                elif opt_name == 'game_bar':
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR")
                    winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Game Bar désactivé")
                    success += 1
                
                elif opt_name == 'game_dvr':
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
                    winreg.SetValueEx(key, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Game DVR désactivé")
                    success += 1
                
                elif opt_name == 'disable_indexing':
                    subprocess.run(["sc", "config", "WSearch", "start=disabled"], creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                    subprocess.run(["net", "stop", "WSearch"], creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
                    log_window.log("  ✅ Indexation désactivée")
                    success += 1
                
                elif opt_name == 'disable_prefetch':
                    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters")
                    winreg.SetValueEx(key, "EnablePrefetcher", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(key, "EnableSuperfetch", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    log_window.log("  ✅ Prefetch/Superfetch désactivés")
                    success += 1
                
            except Exception as e:
                log_window.log(f"  ❌ Erreur: {str(e)}")
                failed += 1
        
        log_window.log("\n" + "="*50)
        log_window.log(f"✅ Succès: {success} | ❌ Échecs: {failed}")
        log_window.log("="*50)
        log_window.log("\n💡 Redémarrez pour appliquer tous les changements")
        
        QMessageBox.information(
            self,
            "✅ Terminé",
            f"Optimisations appliquées !\n\n✅ Réussis: {success}\n❌ Échecs: {failed}\n\n💡 Redémarrage recommandé"
        )
        
        self.detect_current_state()
    
    def restore_defaults(self):
        """Restaurer les paramètres Windows par défaut"""
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation",
            "Restaurer TOUS les paramètres Windows par défaut ?\n\nCeci annulera toutes les optimisations gaming.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        log_window = LogWindow(self, "🔄 Restauration par défaut")
        log_window.show()
        
        import winreg
        
        try:
            # Mouse accel ON
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "6")
            winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "10")
            winreg.CloseKey(key)
            log_window.log("✅ Souris restaurée")
            
            # Transparence ON
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_window.log("✅ Transparence restaurée")
            
            # Visual effects ON
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_window.log("✅ Effets visuels restaurés")
            
            # Game Bar ON
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_window.log("✅ Game Bar restauré")
            
            # Power plan Balanced
            subprocess.run(["powercfg", "/s", "381b4222-f694-41f0-9685-ff5bb260df2e"], creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            log_window.log("✅ Mode Équilibré restauré")
            
            # Indexing ON
            subprocess.run(["sc", "config", "WSearch", "start=auto"], creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            subprocess.run(["net", "start", "WSearch"], creationflags=CREATE_NO_WINDOW, startupinfo=STARTUPINFO)
            log_window.log("✅ Indexation restaurée")
            
            log_window.log("\n✅ RESTAURATION TERMINÉE")
            log_window.log("💡 Redémarrez pour appliquer tous les changements")
            
            QMessageBox.information(self, "✅ Terminé", "Paramètres par défaut restaurés !\n\n💡 Redémarrage recommandé")
            
            self.detect_current_state()
            
        except Exception as e:
            log_window.log(f"❌ Erreur: {str(e)}")
            QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la restauration:\n{str(e)}")

# ============ FENÊTRE DÉSINSTALLATION ============
class UninstallerWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🗑️ Gestionnaire de désinstallation")
        self.setMinimumSize(900, 650)
        
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QProgressBar
        from PyQt6.QtCore import Qt
        
        self.programs = []
        self.selected_programs = []
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("⚠️ Sélectionnez les programmes à désinstaller")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Barre de recherche
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Rechercher un programme...")
        self.search_box.textChanged.connect(self.filter_programs)
        search_layout.addWidget(self.search_box)
        
        scan_btn = QPushButton("🔄 Recharger la liste")
        scan_btn.clicked.connect(self.scan_programs)
        scan_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px;")
        search_layout.addWidget(scan_btn)
        
        layout.addLayout(search_layout)
        
        # Table des programmes
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["☐", "Nom du programme", "Taille", "Type", "⚠️"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self.toggle_selection)
        layout.addWidget(self.table)
        
        # Info sélection
        self.info_label = QLabel("Aucun programme sélectionné")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("☑️ Tout sélectionner")
        select_all_btn.clicked.connect(self.select_all)
        btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ Tout désélectionner")
        deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(deselect_all_btn)
        
        btn_layout.addStretch()
        
        self.uninstall_btn = QPushButton("🗑️ DÉSINSTALLER LA SÉLECTION")
        self.uninstall_btn.clicked.connect(self.uninstall_selected)
        self.uninstall_btn.setStyleSheet("""
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
            QPushButton:disabled { background: #666; }
        """)
        self.uninstall_btn.setEnabled(False)
        btn_layout.addWidget(self.uninstall_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress bar (cachée par défaut)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTableWidget { 
                background: #2b2b2b; 
                color: white; 
                border: 1px solid #444;
                gridline-color: #444;
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
                padding: 8px;
            }
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        
        # Scanner les programmes au démarrage
        QTimer.singleShot(100, self.scan_programs)
    
    def scan_programs(self):
        """Scanner tous les programmes installés via le Registre Windows"""
        self.table.setRowCount(0)
        self.programs = []
        self.info_label.setText("🔄 Scan en cours...")
        QApplication.processEvents()
        
        try:
            import winreg
            
            # Clés de registre où sont stockés les programmes installés
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]
            
            for hkey, path in registry_paths:
                try:
                    key = winreg.OpenKey(hkey, path)
                    
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            
                            # Récupérer le nom du programme
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except:
                                continue
                            
                            # Ignorer entrées vides ou trop courtes
                            if not name or len(name) < 3:
                                continue
                            
                            # Récupérer la taille (optionnel)
                            try:
                                size_kb = winreg.QueryValueEx(subkey, "EstimatedSize")[0]
                                size_mb = size_kb / 1024
                                size_str = f"{size_mb:.1f} Mo" if size_mb < 1024 else f"{size_mb/1024:.1f} Go"
                            except:
                                size_str = "N/A"
                            
                            # Récupérer l'éditeur
                            try:
                                publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                            except:
                                publisher = "Inconnu"
                            
                            # Récupérer la commande de désinstallation
                            try:
                                uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0]
                            except:
                                uninstall_string = None
                            
                            # Vérifier si protégé
                            is_protected = any(p in name.lower() for p in PROTECTED_PROGRAMS)
                            is_bloatware = any(b in name.lower() for b in KNOWN_BLOATWARE)
                            
                            # Éviter doublons
                            if any(prog['name'] == name for prog in self.programs):
                                continue
                            
                            self.programs.append({
                                'name': name,
                                'size': size_str,
                                'type': publisher,
                                'protected': is_protected,
                                'bloatware': is_bloatware,
                                'uninstall_string': uninstall_string,
                                'registry_key': subkey_name
                            })
                            
                            winreg.CloseKey(subkey)
                        
                        except Exception as e:
                            continue
                    
                    winreg.CloseKey(key)
                
                except Exception as e:
                    continue
            
            # Trier par nom
            self.programs.sort(key=lambda x: x['name'].lower())
            
            # Afficher dans la table
            self.populate_table()
            
            self.info_label.setText(f"✅ {len(self.programs)} programmes trouvés")
        
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Impossible de scanner les programmes:\n{str(e)}")
            self.info_label.setText("❌ Erreur de scan")
    
    def populate_table(self):
        """Remplir la table avec les programmes"""
        self.table.setRowCount(len(self.programs))
        
        for i, prog in enumerate(self.programs):
            # Checkbox (colonne 0)
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, checkbox)
            
            # Nom (colonne 1)
            name_item = QTableWidgetItem(prog['name'])
            if prog['protected']:
                name_item.setForeground(QColor("#FF9800"))  # Orange pour protégé
            self.table.setItem(i, 1, name_item)
            
            # Taille (colonne 2)
            self.table.setItem(i, 2, QTableWidgetItem(prog['size']))
            
            # Type (colonne 3)
            self.table.setItem(i, 3, QTableWidgetItem(prog['type']))
            
            # Warning (colonne 4)
            warning = ""
            if prog['protected']:
                warning = "🛡️ Protégé"
            elif prog['bloatware']:
                warning = "⚠️ Bloatware"
            self.table.setItem(i, 4, QTableWidgetItem(warning))
    
    def filter_programs(self):
        """Filtrer les programmes selon la recherche"""
        search_text = self.search_box.text().lower()
        
        for i in range(self.table.rowCount()):
            name = self.table.item(i, 1).text().lower()
            self.table.setRowHidden(i, search_text not in name)
    
    def toggle_selection(self, item):
        """Toggle la checkbox quand on clique sur une ligne"""
        row = item.row()
        checkbox = self.table.item(row, 0)
        
        if checkbox.checkState() == Qt.CheckState.Checked:
            checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            # Vérifier si protégé
            if self.programs[row]['protected']:
                reply = QMessageBox.question(
                    self,
                    "⚠️ ATTENTION - Programme système",
                    f"{self.programs[row]['name']}\n\nCe programme est un composant système.\nLe supprimer peut causer des problèmes.\n\nVoulez-vous vraiment le sélectionner ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            checkbox.setCheckState(Qt.CheckState.Checked)
        
        self.update_selection_info()
    
    def select_all(self):
        """Sélectionner tous les programmes non protégés"""
        for i in range(self.table.rowCount()):
            if not self.table.isRowHidden(i) and not self.programs[i]['protected']:
                self.table.item(i, 0).setCheckState(Qt.CheckState.Checked)
        self.update_selection_info()
    
    def deselect_all(self):
        """Tout désélectionner"""
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.CheckState.Unchecked)
        self.update_selection_info()
    
    def update_selection_info(self):
        """Mettre à jour l'info de sélection"""
        count = 0
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                count += 1
        
        if count == 0:
            self.info_label.setText("Aucun programme sélectionné")
            self.uninstall_btn.setEnabled(False)
        else:
            self.info_label.setText(f"✅ {count} programme(s) sélectionné(s)")
            self.uninstall_btn.setEnabled(True)
    
    def uninstall_selected(self):
        """Désinstaller les programmes sélectionnés"""
        # Récupérer la sélection
        selected = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                selected.append(self.programs[i])
        
        if not selected:
            return
        
        # Confirmation
        prog_list = "\n".join([f"• {p['name']}" for p in selected[:10]])
        if len(selected) > 10:
            prog_list += f"\n... et {len(selected)-10} autres"
        
        reply = QMessageBox.question(
            self,
            "⚠️ Confirmation de désinstallation",
            f"Vous allez désinstaller {len(selected)} programme(s) :\n\n{prog_list}\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Désinstaller
        self.progress.setVisible(True)
        self.progress.setMaximum(len(selected))
        self.progress.setValue(0)
        
        log_window = LogWindow("🗑️ Désinstallation en cours")
        log_window.show()
        
        success = 0
        failed = 0
        
        for i, prog in enumerate(selected):
            log_window.log(f"\n{'='*50}")
            log_window.log(f"📦 Désinstallation: {prog['name']}")
            log_window.log(f"{'='*50}")
            
            try:
                # Désinstaller via Winget
                result = subprocess.run(
                    ["winget", "uninstall", prog['id'], "--silent", "--accept-source-agreements"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=STARTUPINFO,
                    encoding="utf-8",
                    errors="replace"
                )
                
                if result.returncode == 0:
                    log_window.log(f"✅ {prog['name']} désinstallé avec succès")
                    success += 1
                else:
                    log_window.log(f"❌ Échec: {prog['name']}")
                    log_window.log(result.stderr)
                    failed += 1
            
            except Exception as e:
                log_window.log(f"❌ Erreur: {str(e)}")
                failed += 1
            
        self.progress.setValue(i + 1)
        QApplication.processEvents()
        
        # Résumé
        log_window.log(f"\n{'='*50}")
        log_window.log("📊 RÉSUMÉ")
        log_window.log(f"{'='*50}")
        log_window.log(f"✅ Succès: {success}")
        log_window.log(f"❌ Échecs: {failed}")
        log_window.log(f"📁 Total: {len(selected)}")
        
        self.progress.setVisible(False)
        
        # Rescanner
        self.scan_programs()
        
        QMessageBox.information(
            self,
            "✅ Terminé",
            f"Désinstallation terminée !\n\n✅ Réussis: {success}\n❌ Échecs: {failed}"
        )

# ============ FENÊTRE DIAGNOSTIC ============
class DiagnosticWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🩺 Diagnostic par symptômes")
        self.setMinimumSize(800, 600)
        
        from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QTextBrowser
        
        layout = QVBoxLayout()
        
        # Titre
        title = QLabel("Cochez vos symptômes:")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Checkboxes
        self.checkboxes = {}
        for key, symptom in SYMPTOM_DATABASE.items():
            cb = QCheckBox(symptom["name"])
            self.checkboxes[key] = cb
            layout.addWidget(cb)
        
        # Bouton diagnostic
        diag_btn = QPushButton("🔍 Diagnostiquer")
        diag_btn.setMinimumHeight(45)
        diag_btn.clicked.connect(self.run_diagnostic)
        diag_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
        """)
        layout.addWidget(diag_btn)
        
        # Résultats
        self.results = QTextBrowser()
        self.results.setOpenExternalLinks(True)
        layout.addWidget(self.results)
        
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QCheckBox { color: white; font-size: 12px; }
            QTextBrowser { background: #2b2b2b; color: white; border: 1px solid #444; }
        """)
    
    def run_diagnostic(self):
        checked = [key for key, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not checked:
            self.results.setHtml("<h3 style='color: #FF9800;'>⚠️ Veuillez cocher au moins un symptôme</h3>")
            return
        
        html = "<h2>📋 PLAN D'ACTION</h2>"
        
        all_solutions = []
        for key in checked:
            symptom = SYMPTOM_DATABASE[key]
            for solution in symptom["solutions"]:
                all_solutions.append(solution)
        
        # Trier par probabilité
        all_solutions.sort(key=lambda x: x[1], reverse=True)
        
        # Enlever doublons
        seen = set()
        unique_solutions = []
        for sol in all_solutions:
            if sol[0] not in seen:
                seen.add(sol[0])
                unique_solutions.append(sol)
        
        for i, (problem, prob, action) in enumerate(unique_solutions[:5], 1):
            if prob >= 80:
                color = "#F44336"
                priority = "PRIORITÉ 1 - URGENT"
            elif prob >= 60:
                color = "#FF9800"
                priority = "PRIORITÉ 2 - Important"
            elif prob >= 40:
                color = "#FFC107"
                priority = "PRIORITÉ 3 - À vérifier"
            else:
                color = "#4CAF50"
                priority = "BONUS"
            
            html += f"""
            <div style='border-left: 4px solid {color}; padding-left: 10px; margin: 15px 0;'>
                <h3 style='color: {color};'>{priority}</h3>
                <p><b>Cause probable ({prob}% de chance):</b> {problem}</p>
                <p><b>Action:</b> {action}</p>
            </div>
            """
        
        html += "<hr><p><i>💡 Suivre les actions dans l'ordre de priorité</i></p>"
        
        self.results.setHtml(html)

# ============ FENÊTRE PRINCIPALE ============
class PCWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Paramètres par défaut (pas de sauvegarde)
        self.refresh_interval = 15000  # 15 secondes
        self.is_refreshing = True
        self.is_loading = True
        
        # WMI (juste pour cache CPU)
        try:
            self.w = wmi.WMI()
            cpu = self.w.Win32_Processor()[0]
            self.cpu_name = cpu.Name.strip()
        except:
            self.cpu_name = "N/A"
        
        # Historique
        self.cpu_history = deque(maxlen=10)
        self.ram_history = deque(maxlen=10)
        
        # UI
        self.init_ui()
        
        # Centrer la fenêtre sur l'écran
        self.center_on_screen()
        
        # Afficher message de chargement
        self.show_loading_message()
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_info)
        self.timer.start(self.refresh_interval)
        
        # Premier refresh immédiat (après 100ms)
        QTimer.singleShot(100, self.refresh_info)
        
        # Drag
        self.drag_position = QPoint()
    
    def center_on_screen(self):
        """Centrer la fenêtre sur l'écran principal"""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        window_geo = self.geometry()
        x = (screen.width() - window_geo.width()) // 2
        y = (screen.height() - window_geo.height()) // 2
        self.move(x, y)
    
    def show_loading_message(self):
        """Message de chargement initial"""
        self.info_text.setPlainText("""


        🔄  CHARGEMENT EN COURS...
        
        Récupération des informations système
        
        Veuillez patienter quelques secondes...
        
        
        """)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_info)
        self.timer.start(self.refresh_interval)
        
        # Premier refresh
        self.refresh_info()
        
        # Drag
        self.drag_position = QPoint()
    
    def init_ui(self):
        self.setWindowTitle("PC Widget")
        self.setMinimumSize(800, 800)  # Largeur doublée
        self.resize(800, 800)  # Taille par défaut plus grande
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Container
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(18, 18, 18, 18)
        container_layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        
        title = QLabel("💻 WAPINATOR")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        # Bouton refresh manuel
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(38, 38)
        refresh_btn.setToolTip("🔄 Actualiser les informations système\n(Raccourci: F5)")
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.clicked.connect(self.refresh_info)
        
        # Bouton paramètres
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(38, 38)
        settings_btn.setToolTip("⚙️ Ouvrir les paramètres et options\n(Nettoyage, Réparation, MAJ, etc.)")
        settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        settings_btn.clicked.connect(self.open_settings)
        
        # Bouton MAJ
        update_btn = QPushButton("📦")
        update_btn.setFixedSize(38, 38)
        update_btn.setToolTip("📦 Mettre à jour toutes les applications\nvia Winget (Windows Package Manager)")
        update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        update_btn.clicked.connect(lambda: self.run_task("update", "📦 Winget"))
        
        header.addWidget(refresh_btn)
        header.addWidget(settings_btn)
        header.addWidget(update_btn)
        
        container_layout.addLayout(header)
        
        # Barres de progression
        self.cpu_bar = CustomProgressBar()
        self.ram_bar = CustomProgressBar()
        
        container_layout.addWidget(QLabel("🔥 CPU:"))
        
        # Barre CPU cliquable
        self.cpu_bar = CustomProgressBar()
        self.cpu_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cpu_bar.setToolTip("🖱️ Cliquer pour ouvrir le Gestionnaire des tâches\net voir les processus utilisant le CPU")
        # Utiliser mouseReleaseEvent pour éviter les problèmes de clic
        def cpu_click(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.open_task_manager("cpu")
        self.cpu_bar.mouseReleaseEvent = cpu_click
        container_layout.addWidget(self.cpu_bar)
        
        container_layout.addWidget(QLabel("💾 RAM:"))
        
        # Barre RAM cliquable
        self.ram_bar = CustomProgressBar()
        self.ram_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ram_bar.setToolTip("🖱️ Cliquer pour ouvrir le Gestionnaire des tâches\net voir les processus utilisant la RAM")
        # Utiliser mouseReleaseEvent pour éviter les problèmes de clic
        def ram_click(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.open_task_manager("ram")
        self.ram_bar.mouseReleaseEvent = ram_click
        container_layout.addWidget(self.ram_bar)
        
        # Zone info
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Consolas", 9))
        self.info_text.setMinimumHeight(450)  # Plus grande pour tout voir
        
        container_layout.addWidget(self.info_text)
        
        # Version en bas
        version_label = QLabel("version: 1.2")
        version_label.setFont(QFont("Segoe UI", 7))
        version_label.setStyleSheet("color: #666666; background-color: transparent;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(version_label)
        
        container.setLayout(container_layout)
        main_layout.addWidget(container)
        central.setLayout(main_layout)
        
        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border-radius: 16px;
            }
            QLabel {
                background-color: transparent;
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 12px;
                padding: 12px;
            }
            QPushButton {
                background-color: #2d333b;
                color: #ffffff;
                border: 2px solid #444c56;
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #373e47;
                border-color: #58a6ff;
            }
            QPushButton:pressed {
                background-color: #22272e;
            }
        """)
    
    def refresh_info(self):
        """Lance le refresh dans un thread séparé"""
        if not self.is_refreshing:
            return
        
        # Empêcher les refresh multiples simultanés
        if hasattr(self, 'refresh_worker') and self.refresh_worker.isRunning():
            return
        
        # Lancer le worker (il créera ses propres instances WMI)
        self.refresh_worker = RefreshWorker(self.cpu_name, False)  # Toujours mode étendu
        self.refresh_worker.data_ready.connect(self.update_ui_with_data)
        self.refresh_worker.start()
    
    def update_ui_with_data(self, data):
        """Met à jour l'UI avec les données reçues du thread"""
        try:
            # Premier chargement terminé
            if self.is_loading:
                self.is_loading = False
            
            # Vérifier erreur
            if 'error' in data:
                self.info_text.setPlainText(f"❌ Erreur refresh:\n{data['error']}")
                return
            
            # Mettre à jour les barres
            cpu_percent = data.get('cpu_percent', 0)
            self.cpu_bar.setValue(int(cpu_percent))
            self.cpu_bar.set_color_from_value(cpu_percent)
            self.cpu_bar.setFormat(f"{cpu_percent:.1f}%")
            
            ram_info = data.get('ram', {})
            ram_percent = ram_info.get('percent', 0)
            self.ram_bar.setValue(int(ram_percent))
            self.ram_bar.set_color_from_value(ram_percent)
            self.ram_bar.setFormat(f"{ram_info.get('used', 0):.1f}/{ram_info.get('total', 0):.1f} Go ({ram_percent:.0f}%)")
            
            # Construire le texte (toujours mode étendu)
            info = f"""{'='*90}
🖥️  SYSTÈME
{'='*90}
OS: Windows {data.get('windows_version', 'N/A')}
Carte mère: {data.get('motherboard', 'N/A')}
BIOS: {data.get('bios', 'N/A')}

{'='*90}
⚡ PROCESSEUR
{'='*90}
Modèle: {self.cpu_name}
Cœurs: {data.get('cpu_cores', 'N/A')} | Threads: {data.get('cpu_threads', 'N/A')}
Charge actuelle: {cpu_percent:.1f}%

{'='*90}
💾 MÉMOIRE
{'='*90}
Totale: {ram_info.get('total', 0):.1f} Go
Utilisée: {ram_info.get('used', 0):.1f} Go
Disponible: {ram_info.get('available', 0):.1f} Go
XMP/Overclocking: {data.get('xmp', 'N/A')}

{'='*90}
🎮 CARTE GRAPHIQUE
{'='*90}
{data.get('gpu', 'N/A')}

{'='*90}
💿 STOCKAGE
{'='*90}
{data.get('disks', 'N/A')}

{'='*90}
🌐 RÉSEAU
{'='*90}
Ping (8.8.8.8): {data.get('ping', 'N/A')}
"""
            
            if data.get('top5'):
                info += f"""
{'='*90}
⚡ TOP 5 PROCESSUS
{'='*90}
{data.get('top5')}
"""
            
            self.info_text.setPlainText(info)
            
            # Alertes
            if cpu_percent > 90:
                self.show_alert("⚠️ CPU > 90%")
            if ram_percent > 90:
                self.show_alert("⚠️ RAM > 90%")
            
        except Exception as e:
            self.info_text.setPlainText(f"❌ Erreur mise à jour UI:\n{str(e)}")
    
    def show_alert(self, message):
        """Affiche une alerte non bloquante"""
        # Simple print pour l'instant, peut être remplacé par notification Windows
        print(f"ALERTE: {message}")
    
    def open_task_manager(self, tab="cpu"):
        """Ouvre le Gestionnaire des tâches Windows"""
        try:
            # Lancer le gestionnaire des tâches
            subprocess.Popen(
                ["taskmgr"],
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            # Note: Windows 10/11 ouvre automatiquement sur l'onglet Processus
            # Le tri CPU/RAM ne peut pas être contrôlé via ligne de commande
            # L'utilisateur devra cliquer sur la colonne CPU ou Mémoire pour trier
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Erreur",
                f"Impossible d'ouvrir le Gestionnaire des tâches:\n{str(e)}"
            )
    
    def get_cpu_percent_wmi(self):
        """Charge CPU via WMI - AUCUNE fenêtre CMD"""
        try:
            cpu_info = self.w.Win32_Processor()[0]
            return float(cpu_info.LoadPercentage) if cpu_info.LoadPercentage else 0.0
        except:
            return 0.0
    
    def get_cpu_cores(self):
        try:
            cpu = self.w.Win32_Processor()[0]
            return cpu.NumberOfCores
        except:
            return "N/A"
    
    def get_cpu_threads(self):
        try:
            cpu = self.w.Win32_Processor()[0]
            return cpu.NumberOfLogicalProcessors
        except:
            return "N/A"
    
    def get_ram_info(self):
        """RAM via WMI - AUCUNE fenêtre CMD"""
        try:
            os_info = self.w.Win32_OperatingSystem()[0]
            total = int(os_info.TotalVisibleMemorySize) / (1024**2)
            free = int(os_info.FreePhysicalMemory) / (1024**2)
            used = total - free
            percent = (used / total) * 100
            return {
                'total': total,
                'used': used,
                'available': free,
                'percent': percent
            }
        except:
            return {'total': 0, 'used': 0, 'available': 0, 'percent': 0}
    
    def get_windows_version(self):
        try:
            os_info = self.w.Win32_OperatingSystem()[0]
            return os_info.Caption.replace("Microsoft Windows ", "")
        except:
            return "N/A"
    
    def get_motherboard(self):
        try:
            board = self.w.Win32_BaseBoard()[0]
            return f"{board.Manufacturer} {board.Product}"
        except:
            return "N/A"
    
    def get_bios(self):
        try:
            bios = self.w.Win32_BIOS()[0]
            return bios.SMBIOSBIOSVersion
        except:
            return "N/A"
    
    def get_xmp_status(self):
        """XMP via WMI - AUCUNE fenêtre CMD"""
        try:
            chips = self.w.Win32_PhysicalMemory()
            states = []
            for c in chips:
                if c.Speed and c.ConfiguredClockSpeed:
                    states.append(int(c.ConfiguredClockSpeed) >= int(c.Speed) * 0.95)
            if not states:
                return "❓ Inconnu"
            return "✅ Activé" if all(states) else "❌ Désactivé"
        except:
            return "❓ Inconnu"
    
    def get_gpu_info(self):
        """GPU via WMI - AUCUNE fenêtre CMD"""
        try:
            gpus = self.w.Win32_VideoController()
            if not gpus:
                return "❌ Aucun GPU détecté"
            
            info = "="*45 + "\n🎮 CARTE GRAPHIQUE\n" + "="*45 + "\n"
            for gpu in gpus:
                name = gpu.Name
                # RAM GPU
                try:
                    ram_gb = int(gpu.AdapterRAM) / (1024**3) if gpu.AdapterRAM else 0
                    ram_str = f" | {ram_gb:.0f} Go" if ram_gb > 0 else ""
                except:
                    ram_str = ""
                
                info += f"{name}{ram_str}\n"
            
            return info
        except:
            return "❌ Erreur lecture GPU"
    
    def get_disk_info(self):
        """Disques via WMI - AUCUNE fenêtre CMD"""
        try:
            drives = self.w.Win32_LogicalDisk(DriveType=3)  # Type 3 = disque local
            if not drives:
                return "❌ Aucun disque"
            
            info = []
            for drive in drives:
                letter = drive.DeviceID
                total_gb = int(drive.Size) / (1024**3) if drive.Size else 0
                free_gb = int(drive.FreeSpace) / (1024**3) if drive.FreeSpace else 0
                used_gb = total_gb - free_gb
                percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
                
                # Alerte si < 10%
                alert = " ⚠️  CRITIQUE" if free_gb < (total_gb * 0.1) else ""
                
                info.append(f"{letter}\\ | {used_gb:.1f}/{total_gb:.1f} Go ({percent:.0f}%){alert}")
            
            return "\n".join(info)
        except:
            return "❌ Erreur lecture disques"
    
    def contextMenuEvent(self, event):
        """Menu clic droit"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: white;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 30px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
        """)
        
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.refresh_info)
        
        settings_action = QAction("⚙️ Paramètres", self)
        settings_action.triggered.connect(self.open_settings)
        
        copy_action = QAction("📋 Copier", self)
        copy_action.triggered.connect(self.copy_to_clipboard)
        
        quit_action = QAction("❌ Quitter", self)
        quit_action.triggered.connect(QApplication.quit)
        
        menu.addAction(refresh_action)
        menu.addAction(copy_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addAction(quit_action)
        
        menu.exec(event.globalPos())
    
    def copy_to_clipboard(self):
        """Copier les infos dans le presse-papier"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.info_text.toPlainText())
        # Mini notification
        QMessageBox.information(self, "✅", "Copié !", QMessageBox.StandardButton.Ok)
    
    def export_report(self):
        """Exporter un rapport système complet en .txt"""
        from datetime import datetime
        
        # Nom du fichier avec date/heure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Wapinator_Rapport_{timestamp}.txt"
        
        # Chemin Desktop
        desktop = Path.home() / "Desktop"
        filepath = desktop / filename
        
        try:
            # Contenu du rapport
            report = f"""╔═══════════════════════════════════════════════════╗
║         RAPPORT SYSTÈME WAPINATOR v1.0            ║
║         Généré le: {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}        ║
╚═══════════════════════════════════════════════════╝

{self.info_text.toPlainText()}

═══════════════════════════════════════════════════
INFORMATIONS COMPLÉMENTAIRES
═══════════════════════════════════════════════════

Généré par: Wapinator v1.0
Système d'exploitation: Windows
Format: UTF-8

═══════════════════════════════════════════════════
Ce rapport peut être partagé avec un technicien
pour diagnostic à distance.
═══════════════════════════════════════════════════
"""
            
            # Écrire le fichier
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # Confirmation
            reply = QMessageBox.question(
                self,
                "✅ Rapport exporté",
                f"Rapport sauvegardé sur le Bureau :\n{filename}\n\nOuvrir le fichier ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(filepath)
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Erreur",
                f"Impossible d'exporter le rapport:\n{str(e)}"
            )
    
    def open_settings(self):
        dialog = SettingsWindow(self)
        dialog.exec()
    
    def run_task(self, task_type, title):
        self.log_window = LogWindow(self, title)
        self.log_window.show()
        
        self.worker = WorkerThread(task_type)
        self.worker.log_signal.connect(self.log_window.append_log)
        self.worker.finished_signal.connect(self.on_task_finished)
        self.worker.start()
    
    def on_task_finished(self, message):
        QMessageBox.information(self, "✅ Terminé", message)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F5:
            self.refresh_info()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        # Plus de sauvegarde de position
        pass
    
    def closeEvent(self, event):
        # Fermeture propre
        event.accept()

# ============ MAIN ============
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Palette sombre
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(13, 17, 23))
    palette.setColor(QPalette.ColorRole.Text, QColor(88, 166, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 51, 59))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    widget = PCWidget()
    widget.show()
    
    sys.exit(app.exec())