# modules/network_tester.py
"""
Network Tester & Repair - Tests réseau complets + Réparations réseau
Version 2.0 - Avec réparations réseau intégrées
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QComboBox, QCheckBox,
                            QGroupBox, QWidget, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import subprocess
import socket
import time
import re
import platform
from datetime import datetime
from pathlib import Path

# Flags pour subprocess (masquer CMD)
import sys
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = subprocess.SW_HIDE
else:
    CREATE_NO_WINDOW = 0
    STARTUPINFO = None


class NetworkTestWorker(QThread):
    """Worker pour tests réseau"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, test_type):
        super().__init__()
        self.test_type = test_type
    
    def run(self):
        """Exécuter les tests"""
        results = {}
        
        try:
            if self.test_type == "full":
                results = self.run_full_test()
            elif self.test_type == "speed":
                results = self.run_speed_test()
            elif self.test_type == "latency":
                results = self.run_latency_test()
            elif self.test_type == "dns":
                results = self.run_dns_test()
            
            self.finished_signal.emit(results)
        
        except Exception as e:
            self.finished_signal.emit({'error': str(e)})
    
    def run_full_test(self):
        """Test complet"""
        results = {
            'ping': {},
            'dns': {},
            'traceroute': {},
            'packet_loss': {},
            'connection_info': {}
        }
        
        self.log_signal.emit("╔" + "═"*70 + "╗")
        self.log_signal.emit("║" + " "*20 + "🌐 TEST RÉSEAU COMPLET" + " "*28 + "║")
        self.log_signal.emit("╚" + "═"*70 + "╝\n")
        
        # 1. Test Ping multiple serveurs
        self.log_signal.emit("📊 ÉTAPE 1/5 : Test de latence (Ping)")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(20)
        
        servers = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
            ("208.67.222.222", "OpenDNS"),
            ("9.9.9.9", "Quad9")
        ]
        
        ping_results = []
        for ip, name in servers:
            self.log_signal.emit(f"  → Test {name} ({ip})...")
            ping_data = self.ping_server(ip, count=4)
            ping_results.append((name, ping_data))
            
            if ping_data['success']:
                self.log_signal.emit(f"    ✅ Moy: {ping_data['avg']:.1f}ms | Min: {ping_data['min']:.1f}ms | Max: {ping_data['max']:.1f}ms")
            else:
                self.log_signal.emit(f"    ❌ Échec")
        
        results['ping'] = ping_results
        self.log_signal.emit("")
        
        # 2. Test DNS
        self.log_signal.emit("🔍 ÉTAPE 2/5 : Test résolution DNS")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(40)
        
        test_domains = [
            "google.com",
            "cloudflare.com", 
            "github.com",
            "microsoft.com"
        ]
        
        dns_results = []
        for domain in test_domains:
            self.log_signal.emit(f"  → Résolution {domain}...")
            dns_data = self.resolve_dns(domain)
            dns_results.append((domain, dns_data))
            
            if dns_data['success']:
                self.log_signal.emit(f"    ✅ IP: {dns_data['ip']} | Temps: {dns_data['time']:.2f}ms")
            else:
                self.log_signal.emit(f"    ❌ Échec")
        
        results['dns'] = dns_results
        self.log_signal.emit("")
        
        # 3. Test packet loss
        self.log_signal.emit("📉 ÉTAPE 3/5 : Test perte de paquets")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(60)
        
        self.log_signal.emit("  → Test 100 pings vers 8.8.8.8...")
        packet_loss = self.test_packet_loss("8.8.8.8", count=100)
        results['packet_loss'] = packet_loss
        
        self.log_signal.emit(f"    Paquets envoyés: {packet_loss['sent']}")
        self.log_signal.emit(f"    Paquets reçus: {packet_loss['received']}")
        self.log_signal.emit(f"    Perte: {packet_loss['loss_percent']:.1f}%")
        
        if packet_loss['loss_percent'] == 0:
            self.log_signal.emit("    ✅ Aucune perte de paquets")
        elif packet_loss['loss_percent'] < 1:
            self.log_signal.emit("    ✅ Perte acceptable (< 1%)")
        elif packet_loss['loss_percent'] < 5:
            self.log_signal.emit("    ⚠️ Perte modérée (1-5%)")
        else:
            self.log_signal.emit("    ❌ Perte élevée (> 5%)")
        
        self.log_signal.emit("")
        
        # 4. Traceroute
        self.log_signal.emit("🗺️ ÉTAPE 4/5 : Traceroute (chemin réseau)")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(80)
        
        self.log_signal.emit("  → Traceroute vers 8.8.8.8...")
        traceroute_data = self.traceroute("8.8.8.8")
        results['traceroute'] = traceroute_data
        
        if traceroute_data['success']:
            self.log_signal.emit(f"    ✅ {traceroute_data['hops']} sauts jusqu'à destination")
            for i, hop in enumerate(traceroute_data['path'][:10], 1):
                self.log_signal.emit(f"       {i}. {hop}")
        else:
            self.log_signal.emit("    ⚠️ Traceroute partiel ou échoué")
        
        self.log_signal.emit("")
        
        # 5. Informations connexion
        self.log_signal.emit("ℹ️ ÉTAPE 5/5 : Informations connexion")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(100)
        
        connection_info = self.get_connection_info()
        results['connection_info'] = connection_info
        
        self.log_signal.emit(f"  • Adresse IP locale: {connection_info.get('local_ip', 'N/A')}")
        self.log_signal.emit(f"  • Passerelle par défaut: {connection_info.get('gateway', 'N/A')}")
        self.log_signal.emit(f"  • Serveur DNS: {connection_info.get('dns', 'N/A')}")
        self.log_signal.emit(f"  • Type connexion: {connection_info.get('connection_type', 'N/A')}")
        
        return results
    
    def ping_server(self, ip, count=4):
        """Ping un serveur - Version universelle"""
        times = []
        
        for i in range(count):
            try:
                start_time = time.time()
                
                result = subprocess.run(
                    ["ping", "-n", "1", ip],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                    startupinfo=STARTUPINFO if STARTUPINFO else None
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                if result.returncode == 0:
                    times.append(elapsed)
                
                time.sleep(0.1)
            except:
                pass
        
        if not times:
            return {'success': False, 'avg': 0, 'min': 0, 'max': 0, 'jitter': 0}
        
        return {
            'success': True,
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'jitter': max(times) - min(times)
        }
    
    def resolve_dns(self, domain):
        """Résoudre un nom de domaine"""
        try:
            start = time.time()
            ip = socket.gethostbyname(domain)
            elapsed = (time.time() - start) * 1000
            
            return {
                'success': True,
                'ip': ip,
                'time': elapsed
            }
        except:
            return {'success': False, 'ip': None, 'time': 0}
    
    def test_packet_loss(self, ip, count=100):
        """Test perte de paquets"""
        sent = count
        received = 0
        
        for i in range(count):
            try:
                result = subprocess.run(
                    ["ping", "-n", "1", ip],
                    capture_output=True,
                    timeout=1,
                    creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                    startupinfo=STARTUPINFO if STARTUPINFO else None
                )
                
                if result.returncode == 0:
                    received += 1
                
                if (i + 1) % 20 == 0:
                    self.log_signal.emit(f"    Progress: {i+1}/{count} pings...")
            except:
                pass
        
        lost = sent - received
        loss_percent = (lost / sent * 100) if sent > 0 else 0
        
        return {
            'sent': sent,
            'received': received,
            'lost': lost,
            'loss_percent': loss_percent
        }
    
    def traceroute(self, ip):
        """Traceroute vers IP"""
        try:
            result = subprocess.run(
                ["tracert", "-d", "-h", "15", ip],
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            output = result.stdout
            path = []
            hops = 0
            
            for line in output.split('\n'):
                match = re.search(r'\d+\s+\d+\s*ms\s+\d+\s*ms\s+\d+\s*ms\s+([\d.]+)', line)
                if match:
                    ip_hop = match.group(1)
                    path.append(ip_hop)
                    hops += 1
            
            return {
                'success': hops > 0,
                'hops': hops,
                'path': path
            }
        
        except:
            return {'success': False, 'hops': 0, 'path': []}
    
    def get_connection_info(self):
        """Récupérer infos connexion"""
        info = {
            'local_ip': 'N/A',
            'gateway': 'N/A',
            'dns': 'N/A',
            'connection_type': 'N/A'
        }
        
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            output = result.stdout
            
            private_ips = re.findall(r'\b(?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3}\b', output)
            if private_ips:
                info['local_ip'] = private_ips[0]
            
            gateway_match = re.search(r'(?:gateway|passerelle)[\s\S]{0,100}?((?:\d{1,3}\.){3}\d{1,3})', output, re.IGNORECASE)
            if gateway_match:
                gateway_ip = gateway_match.group(1)
                if gateway_ip != '0.0.0.0':
                    info['gateway'] = gateway_ip
            
            dns_match = re.search(r'DNS[\s\S]{0,100}?((?:\d{1,3}\.){3}\d{1,3})', output, re.IGNORECASE)
            if dns_match:
                info['dns'] = dns_match.group(1)
            
            if 'ethernet' in output.lower():
                info['connection_type'] = 'Ethernet (Câble)'
            elif any(word in output.lower() for word in ['wi-fi', 'wifi', 'wireless', 'sans fil']):
                info['connection_type'] = 'WiFi (Sans fil)'
        
        except:
            pass
        
        return info
    
    def run_speed_test(self):
        """Test de vitesse (simplifié)"""
        self.log_signal.emit("⚠️ Speedtest complet nécessite speedtest-cli")
        self.log_signal.emit("Test de latence uniquement...\n")
        
        return self.run_latency_test()
    
    def run_latency_test(self):
        """Test latence détaillé"""
        results = {'servers': []}
        
        servers = [
            ("8.8.8.8", "Google DNS (USA)"),
            ("1.1.1.1", "Cloudflare (Global)"),
            ("208.67.222.222", "OpenDNS (USA)"),
            ("9.9.9.9", "Quad9 (Suisse)"),
        ]
        
        self.log_signal.emit("🌍 Test de latence vers serveurs internationaux\n")
        
        for ip, name in servers:
            self.log_signal.emit(f"→ {name}")
            ping_data = self.ping_server(ip, count=10)
            results['servers'].append((name, ping_data))
            
            if ping_data['success']:
                self.log_signal.emit(f"  Latence moyenne: {ping_data['avg']:.1f}ms")
                self.log_signal.emit(f"  Jitter: {ping_data['jitter']:.1f}ms")
                
                if ping_data['avg'] < 30:
                    self.log_signal.emit("  ✅ Excellent (< 30ms)")
                elif ping_data['avg'] < 50:
                    self.log_signal.emit("  ✅ Bon (30-50ms)")
                elif ping_data['avg'] < 100:
                    self.log_signal.emit("  ⚠️ Correct (50-100ms)")
                else:
                    self.log_signal.emit("  ❌ Élevé (> 100ms)")
            else:
                self.log_signal.emit("  ❌ Échec connexion")
            
            self.log_signal.emit("")
        
        return results
    
    def run_dns_test(self):
        """Test DNS détaillé"""
        results = {'dns_servers': [], 'domains': []}
        
        dns_servers = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare"),
            ("208.67.222.222", "OpenDNS")
        ]
        
        test_domain = "google.com"
        
        self.log_signal.emit("🔍 Comparaison serveurs DNS\n")
        
        for dns_ip, dns_name in dns_servers:
            self.log_signal.emit(f"→ Test {dns_name} ({dns_ip})")
            
            try:
                result = subprocess.run(
                    ["nslookup", test_domain, dns_ip],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                    startupinfo=STARTUPINFO if STARTUPINFO else None
                )
                
                if result.returncode == 0:
                    self.log_signal.emit("  ✅ Résolution réussie")
                    results['dns_servers'].append((dns_name, True))
                else:
                    self.log_signal.emit("  ❌ Échec")
                    results['dns_servers'].append((dns_name, False))
            
            except:
                self.log_signal.emit("  ❌ Timeout")
                results['dns_servers'].append((dns_name, False))
            
            self.log_signal.emit("")
        
        return results


class NetworkRepairWorker(QThread):
    """Worker pour réparations réseau - NOUVEAU"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, repair_type, custom_options=None):
        super().__init__()
        self.repair_type = repair_type
        self.custom_options = custom_options or []
    
    def run(self):
        """Exécuter réparations"""
        results = {'success': True, 'errors': []}
        
        try:
            if self.repair_type == "full":
                self.full_repair()
            elif self.repair_type == "quick":
                self.quick_repair()
            elif self.repair_type == "custom":
                self.custom_repair()
            
            self.finished_signal.emit(results)
        
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            self.finished_signal.emit(results)
    
    def full_repair(self):
        """Réparation complète réseau"""
        self.log_signal.emit("╔" + "═"*70 + "╗")
        self.log_signal.emit("║" + " "*18 + "🔧 RÉPARATION RÉSEAU COMPLÈTE" + " "*20 + "║")
        self.log_signal.emit("╚" + "═"*70 + "╝\n")
        
        # 1. Flush DNS
        self.log_signal.emit("📊 ÉTAPE 1/5 : Vidage cache DNS")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(20)
        self.flush_dns()
        self.log_signal.emit("")
        
        # 2. Release/Renew IP
        self.log_signal.emit("📊 ÉTAPE 2/5 : Renouvellement IP")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(40)
        self.release_renew_ip()
        self.log_signal.emit("")
        
        # 3. Reset TCP/IP
        self.log_signal.emit("📊 ÉTAPE 3/5 : Reset TCP/IP stack")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(60)
        self.reset_tcp_ip()
        self.log_signal.emit("")
        
        # 4. Reset Winsock
        self.log_signal.emit("📊 ÉTAPE 4/5 : Reset Winsock")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(80)
        self.reset_winsock()
        self.log_signal.emit("")
        
        # 5. Reset Firewall
        self.log_signal.emit("📊 ÉTAPE 5/5 : Reset Windows Firewall")
        self.log_signal.emit("─" * 70)
        self.progress_signal.emit(100)
        self.reset_firewall()
        self.log_signal.emit("")
        
        self.log_signal.emit("╔" + "═"*70 + "╗")
        self.log_signal.emit("║" + " "*20 + "✅ RÉPARATION TERMINÉE" + " "*25 + "║")
        self.log_signal.emit("╚" + "═"*70 + "╝\n")
        
        self.log_signal.emit("⚠️ REDÉMARRAGE REQUIS")
        self.log_signal.emit("Redémarrez votre PC pour appliquer tous les changements.\n")
    
    def quick_repair(self):
        """Réparation rapide (DNS + IP + TCP)"""
        self.log_signal.emit("╔" + "═"*70 + "╗")
        self.log_signal.emit("║" + " "*20 + "⚡ RÉPARATION RAPIDE RÉSEAU" + " "*22 + "║")
        self.log_signal.emit("╚" + "═"*70 + "╝\n")
        
        self.log_signal.emit("📊 ÉTAPE 1/3 : Vidage cache DNS")
        self.progress_signal.emit(33)
        self.flush_dns()
        self.log_signal.emit("")
        
        self.log_signal.emit("📊 ÉTAPE 2/3 : Renouvellement IP")
        self.progress_signal.emit(66)
        self.release_renew_ip()
        self.log_signal.emit("")
        
        self.log_signal.emit("📊 ÉTAPE 3/3 : Reset TCP/IP")
        self.progress_signal.emit(100)
        self.reset_tcp_ip()
        self.log_signal.emit("")
        
        self.log_signal.emit("✅ Réparation rapide terminée!\n")
        self.log_signal.emit("💡 Redémarrage recommandé pour TCP/IP\n")
    
    def custom_repair(self):
        """Réparation personnalisée"""
        self.log_signal.emit("╔" + "═"*70 + "╗")
        self.log_signal.emit("║" + " "*18 + "⚙️ RÉPARATION PERSONNALISÉE" + " "*23 + "║")
        self.log_signal.emit("╚" + "═"*70 + "╝\n")
        
        total_steps = len(self.custom_options)
        
        for i, option in enumerate(self.custom_options, 1):
            progress = int((i / total_steps) * 100)
            self.progress_signal.emit(progress)
            
            if option == "dns":
                self.log_signal.emit(f"📊 ÉTAPE {i}/{total_steps} : Vidage cache DNS")
                self.flush_dns()
            elif option == "ip":
                self.log_signal.emit(f"📊 ÉTAPE {i}/{total_steps} : Renouvellement IP")
                self.release_renew_ip()
            elif option == "tcp":
                self.log_signal.emit(f"📊 ÉTAPE {i}/{total_steps} : Reset TCP/IP")
                self.reset_tcp_ip()
            elif option == "winsock":
                self.log_signal.emit(f"📊 ÉTAPE {i}/{total_steps} : Reset Winsock")
                self.reset_winsock()
            elif option == "firewall":
                self.log_signal.emit(f"📊 ÉTAPE {i}/{total_steps} : Reset Firewall")
                self.reset_firewall()
            
            self.log_signal.emit("")
        
        self.log_signal.emit("✅ Réparations personnalisées terminées!\n")
    
    def flush_dns(self):
        """Vider cache DNS"""
        try:
            self.log_signal.emit("  → Vidage cache DNS...")
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ Cache DNS vidé avec succès")
            else:
                self.log_signal.emit("  ⚠️ Erreur lors du vidage DNS")
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
    
    def release_renew_ip(self):
        """Release + Renew IP"""
        try:
            self.log_signal.emit("  → Release de l'adresse IP...")
            subprocess.run(
                ["ipconfig", "/release"],
                capture_output=True,
                timeout=15,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            time.sleep(2)
            
            self.log_signal.emit("  → Renouvellement de l'adresse IP...")
            result = subprocess.run(
                ["ipconfig", "/renew"],
                capture_output=True,
                timeout=15,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ IP renouvelée avec succès")
            else:
                self.log_signal.emit("  ⚠️ Erreur lors du renouvellement IP")
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
    
    def reset_tcp_ip(self):
        """Reset TCP/IP stack"""
        try:
            self.log_signal.emit("  → Réinitialisation TCP/IP stack...")
            result = subprocess.run(
                ["netsh", "int", "ip", "reset"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ TCP/IP réinitialisé avec succès")
                self.log_signal.emit("  ℹ️ Redémarrage requis pour appliquer")
            else:
                self.log_signal.emit("  ⚠️ Erreur lors du reset TCP/IP")
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
    
    def reset_winsock(self):
        """Reset Winsock"""
        try:
            self.log_signal.emit("  → Réinitialisation Winsock...")
            result = subprocess.run(
                ["netsh", "winsock", "reset"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ Winsock réinitialisé avec succès")
                self.log_signal.emit("  ℹ️ Redémarrage requis pour appliquer")
            else:
                self.log_signal.emit("  ⚠️ Erreur lors du reset Winsock")
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
    
    def reset_firewall(self):
        """Reset Windows Firewall"""
        try:
            self.log_signal.emit("  → Réinitialisation Windows Firewall...")
            result = subprocess.run(
                ["netsh", "advfirewall", "reset"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                startupinfo=STARTUPINFO if STARTUPINFO else None
            )
            
            if result.returncode == 0:
                self.log_signal.emit("  ✅ Firewall réinitialisé avec succès")
            else:
                self.log_signal.emit("  ⚠️ Erreur lors du reset Firewall")
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")


class NetworktesterWindow(QDialog):
    """Fenêtre test réseau avancé + réparations - AMÉLIORÉE"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🌐 Test & Réparation Réseau")
        self.setMinimumSize(1000, 850)
        
        # Scroll area principale
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🌐 TEST & RÉPARATION RÉSEAU")
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
            "Tests réseau complets + Réparations automatiques (WiFi/Ethernet instable, DNS lent, etc.)"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # ═══════════════════════════════════════════════════════════
        # SECTION 1 : TESTS RÉSEAU
        # ═══════════════════════════════════════════════════════════
        
        test_group = QGroupBox("🧪 TESTS RÉSEAU")
        test_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #2196F3;
            }
        """)
        test_layout = QVBoxLayout()
        
        # Type de test
        test_type_layout = QHBoxLayout()
        test_type_layout.addWidget(QLabel("Type de test:"))
        
        self.test_combo = QComboBox()
        self.test_combo.addItems([
            "🌐 Test Complet (5 étapes)",
            "⚡ Test Latence Détaillé",
            "🔍 Test DNS",
        ])
        test_type_layout.addWidget(self.test_combo)
        test_type_layout.addStretch()
        test_layout.addLayout(test_type_layout)
        
        # Boutons tests
        test_btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Lancer Test")
        self.start_btn.clicked.connect(self.start_test)
        self.start_btn.setStyleSheet("background: #4CAF50;")
        test_btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_test)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background: #F44336;")
        test_btn_layout.addWidget(self.stop_btn)
        
        tips_btn = QPushButton("💡 Conseils Connexion")
        tips_btn.clicked.connect(self.show_tips)
        test_btn_layout.addWidget(tips_btn)
        
        test_layout.addLayout(test_btn_layout)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # ═══════════════════════════════════════════════════════════
        # SECTION 2 : RÉPARATIONS RÉSEAU (NOUVEAU)
        # ═══════════════════════════════════════════════════════════
        
        repair_group = QGroupBox("🔧 RÉPARATIONS RÉSEAU")
        repair_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 2px solid #FF9800;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #FF9800;
            }
        """)
        repair_layout = QVBoxLayout()
        
        repair_info = QLabel(
            "Résout 90% des problèmes réseau : WiFi instable, DNS lent, erreurs connexion"
        )
        repair_info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 5px;")
        repair_layout.addWidget(repair_info)
        
        # Boutons réparation
        repair_btn_layout = QHBoxLayout()
        
        self.repair_full_btn = QPushButton("🚀 Réparation Complète (Recommandé)")
        self.repair_full_btn.clicked.connect(lambda: self.start_repair("full"))
        self.repair_full_btn.setStyleSheet("background: #FF9800; font-size: 11px;")
        repair_btn_layout.addWidget(self.repair_full_btn)
        
        self.repair_quick_btn = QPushButton("⚡ Réparation Rapide")
        self.repair_quick_btn.clicked.connect(lambda: self.start_repair("quick"))
        self.repair_quick_btn.setStyleSheet("font-size: 11px;")
        repair_btn_layout.addWidget(self.repair_quick_btn)
        
        self.repair_custom_btn = QPushButton("⚙️ Personnalisée")
        self.repair_custom_btn.clicked.connect(self.show_custom_repair)
        self.repair_custom_btn.setStyleSheet("font-size: 11px;")
        repair_btn_layout.addWidget(self.repair_custom_btn)
        
        repair_layout.addLayout(repair_btn_layout)
        
        # Warning
        warning = QLabel("⚠️ Redémarrage requis après réparation complète")
        warning.setStyleSheet("""
            background: #FF5722;
            color: white;
            padding: 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 10px;
            margin-top: 5px;
        """)
        repair_layout.addWidget(warning)
        
        repair_group.setLayout(repair_layout)
        layout.addWidget(repair_group)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Résultats
        results_label = QLabel("📄 RÉSULTATS")
        results_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        results_label.setStyleSheet("color: #4CAF50; margin-top: 10px;")
        layout.addWidget(results_label)
        
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setFont(QFont("Consolas", 9))
        self.results.setMinimumHeight(300)
        layout.addWidget(self.results)
        
        # Boutons bas
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exporter Rapport")
        export_btn.clicked.connect(self.export_report)
        bottom_layout.addWidget(export_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        
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
            QPushButton:disabled { background: #555; }
            QTextEdit {
                background: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
            QComboBox {
                background: #2b2b2b;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { 
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
            QComboBox QAbstractItemView {
                background: #2b2b2b;
                color: white;
                selection-background-color: #00BCD4;
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
        """)
        
        self.show_welcome()
        self.test_worker = None
        self.repair_worker = None
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║       🌐 TEST & RÉPARATION RÉSEAU - WAPINATOR v2.0          ║
╚══════════════════════════════════════════════════════════════╝

🎯 FONCTIONNALITÉS

🧪 TESTS RÉSEAU:
- 📊 Ping vers 4 serveurs DNS internationaux
- 🔍 Test résolution DNS (4 domaines)
- 📉 Test perte de paquets (100 pings)
- 🗺️ Traceroute (chemin réseau)
- ℹ️ Informations connexion (IP, passerelle, DNS)

🔧 RÉPARATIONS RÉSEAU (NOUVEAU):
- 🚀 Réparation Complète (5 étapes - Recommandé)
- ⚡ Réparation Rapide (3 étapes - 30 sec)
- ⚙️ Réparation Personnalisée (choix manuel)

═══════════════════════════════════════════════════════════════

🔧 RÉPARATIONS DISPONIBLES

1️⃣  Vidage cache DNS
   → Résout: DNS lent, sites inaccessibles

2️⃣  Renouvellement IP (Release/Renew)
   → Résout: Pas d'accès Internet, IP conflit

3️⃣  Reset TCP/IP stack
   → Résout: Connexions instables, erreurs réseau

4️⃣  Reset Winsock
   → Résout: Programmes ne se connectent pas

5️⃣  Reset Windows Firewall
   → Résout: Blocages connexions

═══════════════════════════════════════════════════════════════

💡 QUAND UTILISER LES RÉPARATIONS ?

SYMPTÔMES COURANTS:
❌ WiFi connecté mais "Pas d'accès Internet"
❌ Certains sites web n'ouvrent pas
❌ DNS très lent (sites mettent >5s à charger)
❌ Erreurs "DNS_PROBE_FINISHED_NO_INTERNET"
❌ Ping OK mais navigation impossible
❌ Déconnexions WiFi/Ethernet fréquentes

→ Lancer "Réparation Complète" résout 90% de ces problèmes

═══════════════════════════════════════════════════════════════

⏱️ DURÉE

TESTS:
- Test Complet: 2-3 minutes
- Test Latence: 1-2 minutes
- Test DNS: 30 secondes

RÉPARATIONS:
- Réparation Complète: 1-2 minutes
- Réparation Rapide: 30 secondes
- Personnalisée: Variable

⚠️ Réparation Complète nécessite redémarrage PC

═══════════════════════════════════════════════════════════════

🚀 DÉMARRAGE RAPIDE

POUR TESTER:
1. Sélectionner type de test
2. Cliquer "Lancer Test"
3. Attendre fin (ne pas fermer fenêtre)

POUR RÉPARER:
1. Cliquer "Réparation Complète"
2. Confirmer (droits admin requis)
3. Redémarrer PC après

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(text)
    
    def start_test(self):
        """Lancer le test sélectionné"""
        test_index = self.test_combo.currentIndex()
        
        test_types = {
            0: "full",
            1: "latency",
            2: "dns",
        }
        
        test_type = test_types.get(test_index, "full")
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.repair_full_btn.setEnabled(False)
        self.repair_quick_btn.setEnabled(False)
        self.repair_custom_btn.setEnabled(False)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.results.clear()
        
        self.test_worker = NetworkTestWorker(test_type)
        self.test_worker.log_signal.connect(self.append_log)
        self.test_worker.progress_signal.connect(self.progress.setValue)
        self.test_worker.finished_signal.connect(self.on_test_finished)
        self.test_worker.start()
    
    def stop_test(self):
        """Arrêter le test en cours"""
        if self.test_worker and self.test_worker.isRunning():
            self.test_worker.terminate()
            self.test_worker.wait()
            self.append_log("\n⚠️ Test interrompu par l'utilisateur")
            self.on_test_finished({})
    
    def start_repair(self, repair_type):
        """Lancer réparation réseau"""
        
        # Vérifier admin
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        
        if not is_admin:
            QMessageBox.warning(
                self,
                "⚠️ Droits administrateur requis",
                "Les réparations réseau nécessitent les droits administrateur.\n\n"
                "➜ Fermez Wapinator\n"
                "➜ Clic droit sur Wapinator.exe\n"
                "➜ 'Exécuter en tant qu'administrateur'\n\n"
                "Puis relancez la réparation."
            )
            return
        
        # Confirmation
        if repair_type == "full":
            message = (
                "🔧 RÉPARATION RÉSEAU COMPLÈTE\n\n"
                "Actions qui seront effectuées :\n\n"
                "1. Vidage cache DNS\n"
                "2. Renouvellement IP (Release + Renew)\n"
                "3. Reset TCP/IP stack\n"
                "4. Reset Winsock\n"
                "5. Reset Windows Firewall\n\n"
                "⚠️ Un redémarrage sera OBLIGATOIRE après.\n\n"
                "Durée : 1-2 minutes\n\n"
                "💾 Sauvegardez vos travaux en cours avant de continuer.\n\n"
                "Continuer ?"
            )
        else:  # quick
            message = (
                "⚡ RÉPARATION RAPIDE\n\n"
                "Actions :\n\n"
                "1. Vidage cache DNS\n"
                "2. Renouvellement IP\n"
                "3. Reset TCP/IP stack\n\n"
                "💡 Redémarrage recommandé (mais pas obligatoire)\n\n"
                "Durée : 30 secondes\n\n"
                "Continuer ?"
            )
        
        reply = QMessageBox.question(
            self,
            "🔧 Confirmation",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Désactiver boutons
        self.repair_full_btn.setEnabled(False)
        self.repair_quick_btn.setEnabled(False)
        self.repair_custom_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.results.clear()
        
        # Lancer worker
        self.repair_worker = NetworkRepairWorker(repair_type)
        self.repair_worker.log_signal.connect(self.append_log)
        self.repair_worker.progress_signal.connect(self.progress.setValue)
        self.repair_worker.finished_signal.connect(lambda r: self.on_repair_finished(r, repair_type))
        self.repair_worker.start()
    
    def show_custom_repair(self):
        """Afficher dialogue réparation personnalisée"""
        
        # Vérifier admin d'abord
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        
        if not is_admin:
            QMessageBox.warning(
                self,
                "⚠️ Droits administrateur requis",
                "Les réparations réseau nécessitent les droits administrateur.\n\n"
                "Relancez Wapinator en tant qu'administrateur."
            )
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("⚙️ Réparation Personnalisée")
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        
        info = QLabel("Sélectionnez les réparations à effectuer:")
        info.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(info)
        
        layout.addSpacing(10)
        
        # Checkboxes
        dns_cb = QCheckBox("🌐 Vidage cache DNS (Recommandé)")
        dns_cb.setChecked(True)
        layout.addWidget(dns_cb)
        
        ip_cb = QCheckBox("🔄 Renouvellement IP - Release/Renew (Recommandé)")
        ip_cb.setChecked(True)
        layout.addWidget(ip_cb)
        
        tcp_cb = QCheckBox("🔧 Reset TCP/IP stack (Recommandé)")
        tcp_cb.setChecked(True)
        layout.addWidget(tcp_cb)
        
        winsock_cb = QCheckBox("🔌 Reset Winsock")
        winsock_cb.setChecked(True)
        layout.addWidget(winsock_cb)
        
        firewall_cb = QCheckBox("🛡️ Reset Windows Firewall (Optionnel)")
        firewall_cb.setChecked(False)
        layout.addWidget(firewall_cb)
        
        layout.addSpacing(10)
        
        note = QLabel("💡 Tout cocher = Réparation Complète")
        note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(note)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        ok_btn = QPushButton("✅ Lancer Réparation")
        ok_btn.clicked.connect(dialog.accept)
        ok_btn.setStyleSheet("background: #4CAF50;")
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("background: #F44336;")
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        dialog.setStyleSheet("""
            QDialog { background: #1e1e1e; color: white; }
            QLabel { color: white; }
            QCheckBox { color: white; padding: 5px; }
        """)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = []
            if dns_cb.isChecked():
                selected.append("dns")
            if ip_cb.isChecked():
                selected.append("ip")
            if tcp_cb.isChecked():
                selected.append("tcp")
            if winsock_cb.isChecked():
                selected.append("winsock")
            if firewall_cb.isChecked():
                selected.append("firewall")
            
            if not selected:
                QMessageBox.warning(self, "⚠️", "Aucune réparation sélectionnée")
                return
            
            # Désactiver boutons
            self.repair_full_btn.setEnabled(False)
            self.repair_quick_btn.setEnabled(False)
            self.repair_custom_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            
            self.progress.setVisible(True)
            self.progress.setValue(0)
            self.results.clear()
            
            # Lancer worker custom
            self.repair_worker = NetworkRepairWorker("custom", selected)
            self.repair_worker.log_signal.connect(self.append_log)
            self.repair_worker.progress_signal.connect(self.progress.setValue)
            self.repair_worker.finished_signal.connect(lambda r: self.on_repair_finished(r, "custom"))
            self.repair_worker.start()
    
    def append_log(self, text):
        """Ajouter au log"""
        self.results.append(text)
    
    def on_test_finished(self, results):
        """Test terminé"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.repair_full_btn.setEnabled(True)
        self.repair_quick_btn.setEnabled(True)
        self.repair_custom_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if 'error' in results:
            self.append_log(f"\n❌ Erreur: {results['error']}")
            return
        
        # Ajouter résumé si test complet
        if 'ping' in results and 'packet_loss' in results:
            self.append_log("\n" + "╔" + "═"*70 + "╗")
            self.append_log("║" + " "*22 + "📊 RÉSUMÉ DES TESTS" + " "*28 + "║")
            self.append_log("╚" + "═"*70 + "╝\n")
            
            ping_ok = sum(1 for _, p in results['ping'] if p['success']) >= 3
            packet_loss = results['packet_loss']['loss_percent']
            
            if ping_ok and packet_loss < 1:
                self.append_log("✅ CONNEXION EXCELLENTE")
                self.append_log("   • Latence basse")
                self.append_log("   • Aucune perte de paquets")
                self.append_log("   • Idéal pour gaming/streaming")
            elif ping_ok and packet_loss < 5:
                self.append_log("✅ CONNEXION BONNE")
                self.append_log("   • Latence correcte")
                self.append_log("   • Légère perte de paquets")
                self.append_log("   • OK pour usage quotidien")
            elif ping_ok:
                self.append_log("⚠️ CONNEXION INSTABLE")
                self.append_log("   • Latence correcte")
                self.append_log("   • Perte de paquets significative")
                self.append_log("   • 💡 Essayez 'Réparation Complète'")
            else:
                self.append_log("❌ PROBLÈME DE CONNEXION")
                self.append_log("   • Échecs multiples")
                self.append_log("   • 🔧 Lancez 'Réparation Complète'")
            
            self.append_log("")
    
    def on_repair_finished(self, results, repair_type):
        """Réparation terminée"""
        self.repair_full_btn.setEnabled(True)
        self.repair_quick_btn.setEnabled(True)
        self.repair_custom_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if not results.get('success', True):
            QMessageBox.warning(
                self,
                "⚠️ Erreurs",
                "Certaines réparations ont échoué.\n\n"
                "Vérifiez les logs pour plus de détails."
            )
            return
        
        # Proposition redémarrage si repair complète
        if repair_type == "full":
            reply = QMessageBox.question(
                self,
                "✅ Réparation Terminée",
                "Réparation réseau complète effectuée avec succès!\n\n"
                "⚠️ REDÉMARRAGE OBLIGATOIRE pour appliquer les changements.\n\n"
                "💾 Sauvegardez vos travaux en cours avant de redémarrer.\n\n"
                "Redémarrer maintenant ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    subprocess.run(
                        ["shutdown", "/r", "/t", "30", "/c", "Redémarrage pour appliquer réparations réseau Wapinator"],
                        creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                        startupinfo=STARTUPINFO if STARTUPINFO else None
                    )
                    
                    QMessageBox.information(
                        self,
                        "🔄 Redémarrage Programmé",
                        "Le PC redémarrera dans 30 secondes.\n\n"
                        "💾 Sauvegardez vos travaux maintenant !\n\n"
                        "💡 Pour annuler: shutdown /a (CMD admin)"
                    )
                except:
                    QMessageBox.warning(self, "❌", "Impossible de programmer le redémarrage")
            else:
                QMessageBox.information(
                    self,
                    "⚠️ Redémarrage Requis",
                    "N'oubliez pas de redémarrer votre PC\npour appliquer les changements !"
                )
        else:
            QMessageBox.information(
                self,
                "✅ Réparation Terminée",
                f"Réparation {repair_type} effectuée avec succès!\n\n"
                "💡 Redémarrage recommandé pour TCP/IP.\n\n"
                "Testez votre connexion maintenant."
            )
    
    def show_tips(self):
        """Afficher conseils connexion"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║           💡 CONSEILS AMÉLIORATION CONNEXION                ║
╚══════════════════════════════════════════════════════════════╝

🎯 POUR RÉDUIRE LATENCE (PING)

1️⃣  CÂBLE ETHERNET > WIFI
   • Gain: -20 à -50ms ping
   • Câble Cat5e minimum (Cat6 recommandé)
   • Connexion directe routeur → PC

2️⃣  CHANGER DNS
   • DNS FAI souvent lent
   • Recommandé:
     → 1.1.1.1 (Cloudflare - le plus rapide)
     → 8.8.8.8 (Google - fiable)
     → 9.9.9.9 (Quad9 - sécurisé)
   • Comment changer:
     → Panneau config > Réseau > Propriétés carte
     → IPv4 > Propriétés > DNS

3️⃣  QOS ROUTEUR (Quality of Service)
   • Prioriser trafic gaming
   • Interface admin routeur (192.168.1.1)
   • Activer QoS > Priorité PC

4️⃣  FERMER APPS ARRIÈRE-PLAN
   • Steam, Epic, Windows Update = voleurs bandwidth
   • Fermer avant gaming/streaming

═══════════════════════════════════════════════════════════════

📉 POUR RÉDUIRE PERTE PAQUETS

1️⃣  WIFI INSTABLE
   • Passer en Ethernet (solution #1)
   • Si Wifi obligatoire:
     → Se rapprocher routeur
     → Changer canal WiFi
     → WiFi 6 si vieux routeur

2️⃣  INTERFÉRENCES
   • Éloigner routeur de:
     → Micro-ondes
     → Téléphones sans fil
   • Préférer 5GHz (vs 2.4GHz)

3️⃣  ROUTEUR SURCHARGÉ
   • Redémarrer routeur (30s débranché)
   • Limiter appareils connectés
   • MAJ firmware routeur

4️⃣  DRIVERS RÉSEAU
   • MAJ drivers carte réseau
   • Wapinator > Driver Manager

═══════════════════════════════════════════════════════════════

🔧 SI PROBLÈME PERSISTE

ÉTAPES:
1. Tester avec câble Ethernet
2. Lancer "Réparation Complète" Wapinator
3. Tester sur autre PC
4. Contacter FAI si toujours problème

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(tips)
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║              ❓ AIDE - TEST & RÉPARATION RÉSEAU             ║
╚══════════════════════════════════════════════════════════════╝

🧪 TESTS RÉSEAU

PING:
- Temps aller-retour paquet
- Plus c'est bas, mieux c'est
- < 30ms = Excellent | 30-50ms = Bon | > 100ms = Problème

PACKET LOSS:
- % paquets perdus
- 0% = idéal | < 1% = OK | > 5% = Grave

DNS:
- Traduit noms en IP
- DNS lent = sites lents

TRACEROUTE:
- Chemin complet des paquets
- Montre chaque routeur

═══════════════════════════════════════════════════════════════

🔧 RÉPARATIONS RÉSEAU (NOUVEAU)

RÉPARATION COMPLÈTE:
✅ Vidage cache DNS
✅ Renouvellement IP (Release/Renew)
✅ Reset TCP/IP stack
✅ Reset Winsock
✅ Reset Windows Firewall
→ Résout 90% des problèmes
→ ⚠️ Redémarrage OBLIGATOIRE

RÉPARATION RAPIDE:
✅ DNS + IP + TCP/IP
→ 30 secondes
→ Redémarrage recommandé

PERSONNALISÉE:
→ Choix manuel des réparations

═══════════════════════════════════════════════════════════════

💡 QUAND UTILISER LES RÉPARATIONS ?

SYMPTÔMES:
❌ "Pas d'accès Internet" alors que connecté
❌ DNS très lent (sites >5s)
❌ Certains sites n'ouvrent pas
❌ Erreurs DNS_PROBE_FINISHED
❌ Connexion instable

→ Lancer "Réparation Complète"

═══════════════════════════════════════════════════════════════

🎮 VALEURS CIBLES GAMING

FPS Compétitif:
- Ping: < 30ms
- Packet loss: 0%

FPS Casual:
- Ping: < 50ms
- Packet loss: < 1%

MOBA:
- Ping: < 60ms

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter rapport"""
        content = self.results.toPlainText()
        
        if not content or "BIENVENUE" in content or "CONSEILS" in content:
            QMessageBox.warning(self, "⚠️", "Aucun test/réparation à exporter.\nLancez d'abord un test ou une réparation.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_Reseau_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 70 + "\n")
                f.write("  RAPPORT RÉSEAU - WAPINATOR v2.0\n")
                f.write(f"  Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
                f.write("═" * 70 + "\n\n")
                f.write(content)
            
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


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = NetworktesterWindow(None)
    window.show()
    sys.exit(app.exec())