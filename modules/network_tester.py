# modules/network_tester.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QProgressBar, QMessageBox, QComboBox)
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
            for i, hop in enumerate(traceroute_data['path'][:10], 1):  # Max 10 premiers
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
                
                # Lancer ping et mesurer le temps nous-mêmes
                result = subprocess.run(
                    ["ping", "-n", "1", ip],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=CREATE_NO_WINDOW if CREATE_NO_WINDOW else 0,
                    startupinfo=STARTUPINFO if STARTUPINFO else None
                )
                
                elapsed = (time.time() - start_time) * 1000  # ms
                
                # Si returncode == 0 → succès
                if result.returncode == 0:
                    times.append(elapsed)
                
                time.sleep(0.1)  # Pause entre pings
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
            elapsed = (time.time() - start) * 1000  # ms
            
            return {
                'success': True,
                'ip': ip,
                'time': elapsed
            }
        except:
            return {'success': False, 'ip': None, 'time': 0}
    
    def test_packet_loss(self, ip, count=100):
        """Test perte de paquets - Version universelle"""
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
                
                # Log progress tous les 20 pings
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
                # Chercher lignes avec IP
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
        """Récupérer infos connexion - Version universelle"""
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
            
            # IP locale - Chercher toute IP privée (192.168.x.x, 10.x.x.x, etc.)
            private_ips = re.findall(r'\b(?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3}\b', output)
            if private_ips:
                info['local_ip'] = private_ips[0]
            
            # Passerelle - Chercher IP après mot "gateway" ou "passerelle" (toute langue)
            gateway_match = re.search(r'(?:gateway|passerelle)[\s\S]{0,100}?((?:\d{1,3}\.){3}\d{1,3})', output, re.IGNORECASE)
            if gateway_match:
                gateway_ip = gateway_match.group(1)
                if gateway_ip != '0.0.0.0':
                    info['gateway'] = gateway_ip
            
            # DNS - Chercher IP après "DNS"
            dns_match = re.search(r'DNS[\s\S]{0,100}?((?:\d{1,3}\.){3}\d{1,3})', output, re.IGNORECASE)
            if dns_match:
                info['dns'] = dns_match.group(1)
            
            # Type connexion - Chercher mots-clés (toute langue)
            if 'ethernet' in output.lower():
                info['connection_type'] = 'Ethernet (Câble)'
            elif any(word in output.lower() for word in ['wi-fi', 'wifi', 'wireless', 'sans fil']):
                info['connection_type'] = 'WiFi (Sans fil)'
        
        except:
            pass
        
        return info
    
    def run_speed_test(self):
        """Test de vitesse (simplifié)"""
        # Note: Un vrai speedtest nécessiterait une librairie externe (speedtest-cli)
        # Ici on fait juste un test de download basique
        
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
                self.log_signal.emit(f"  Jitter: {ping_data['jitter']}ms")
                
                # Évaluation
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
        
        # Test différents DNS
        dns_servers = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare"),
            ("208.67.222.222", "OpenDNS")
        ]
        
        test_domain = "google.com"
        
        self.log_signal.emit("🔍 Comparaison serveurs DNS\n")
        
        for dns_ip, dns_name in dns_servers:
            self.log_signal.emit(f"→ Test {dns_name} ({dns_ip})")
            
            # Test résolution via nslookup
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

class NetworktesterWindow(QDialog):
    """Fenêtre test réseau avancé"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🌐 Test Réseau Avancé")
        self.setMinimumSize(1000, 750)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🌐 TEST RÉSEAU AVANCÉ")
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
            "Tests réseau complets : Latence, DNS, Packet Loss, Traceroute, Informations connexion"
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Type de test
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("Type de test:"))
        
        self.test_combo = QComboBox()
        self.test_combo.addItems([
            "🌐 Test Complet (5 étapes)",
            "⚡ Test Latence Détaillé",
            "🔍 Test DNS",
        ])
        test_layout.addWidget(self.test_combo)
        test_layout.addStretch()
        
        layout.addLayout(test_layout)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Lancer Test")
        self.start_btn.clicked.connect(self.start_test)
        self.start_btn.setStyleSheet("background: #4CAF50;")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_test)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background: #F44336;")
        btn_layout.addWidget(self.stop_btn)
        
        tips_btn = QPushButton("💡 Conseils Connexion")
        tips_btn.clicked.connect(self.show_tips)
        btn_layout.addWidget(tips_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Résultats
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setFont(QFont("Consolas", 9))
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
        """)
        
        self.show_welcome()
        self.worker = None
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║              🌐 TEST RÉSEAU AVANCÉ - WAPINATOR               ║
╚══════════════════════════════════════════════════════════════╝

🎯 FONCTIONNALITÉS

TEST COMPLET (recommandé):
- 📊 Ping vers 4 serveurs DNS internationaux
- 🔍 Test résolution DNS (4 domaines)
- 📉 Test perte de paquets (100 pings)
- 🗺️ Traceroute (chemin réseau jusqu'à Google DNS)
- ℹ️ Informations connexion (IP, passerelle, DNS actuel)

TEST LATENCE DÉTAILLÉ:
- 🌍 Ping vers serveurs internationaux (10 pings chacun)
- 📊 Statistiques : Moyenne, Min, Max, Jitter
- 🎯 Évaluation qualité connexion

TEST DNS:
- 🔍 Comparaison 3 serveurs DNS (Google, Cloudflare, OpenDNS)
- ⚡ Temps de résolution
- ✅ Fiabilité

═══════════════════════════════════════════════════════════════

💡 INTERPRÉTATION RÉSULTATS

LATENCE (Ping):
- < 30ms = Excellent (gaming compétitif possible)
- 30-50ms = Bon (gaming casual OK)
- 50-100ms = Correct (navigation web fluide)
- > 100ms = Problème (lag visible)

PERTE PAQUETS:
- 0% = Parfait
- < 1% = Acceptable
- 1-5% = Problématique (micro-lags)
- > 5% = Critique (connexion instable)

JITTER:
- < 10ms = Stable
- 10-30ms = Correct
- > 30ms = Instable (variation latence)

═══════════════════════════════════════════════════════════════

⏱️ DURÉE DES TESTS

- Test Complet: 2-3 minutes
- Test Latence: 1-2 minutes
- Test DNS: 30 secondes

═══════════════════════════════════════════════════════════════

🚀 DÉMARRAGE

1. Sélectionner type de test (menu déroulant)
2. Cliquer "Lancer Test"
3. Attendre fin du test (ne pas fermer fenêtre)
4. Analyser résultats

💡 Pour problèmes connexion: Bouton "Conseils Connexion"

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(text)
    
    def start_test(self):
        """Lancer le test sélectionné"""
        test_index = self.test_combo.currentIndex()
        
        test_types = {
            0: "full",      # Test complet
            1: "latency",   # Latence
            2: "dns",       # DNS
        }
        
        test_type = test_types.get(test_index, "full")
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.results.clear()
        
        # Lancer worker
        self.worker = NetworkTestWorker(test_type)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_test_finished)
        self.worker.start()
    
    def stop_test(self):
        """Arrêter le test en cours"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.append_log("\n⚠️ Test interrompu par l'utilisateur")
            self.on_test_finished({})
    
    def append_log(self, text):
        """Ajouter au log"""
        self.results.append(text)
    
    def on_test_finished(self, results):
        """Test terminé"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(False)
        
        if 'error' in results:
            self.append_log(f"\n❌ Erreur: {results['error']}")
            return
        
        # Ajouter résumé si test complet
        if 'ping' in results and 'packet_loss' in results:
            self.append_log("\n" + "╔" + "═"*70 + "╗")
            self.append_log("║" + " "*22 + "📊 RÉSUMÉ DES TESTS" + " "*28 + "║")
            self.append_log("╚" + "═"*70 + "╝\n")
            
            # Évaluation globale
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
                self.append_log("   • Problème de stabilité")
            else:
                self.append_log("❌ PROBLÈME DE CONNEXION")
                self.append_log("   • Échecs multiples")
                self.append_log("   • Vérifier configuration réseau")
            
            self.append_log("")
    
    def show_tips(self):
        """Afficher conseils connexion"""
        tips = """╔══════════════════════════════════════════════════════════════╗
║           💡 CONSEILS AMÉLIORATION CONNEXION                ║
╚══════════════════════════════════════════════════════════════╝

🎯 POUR RÉDUIRE LATENCE (PING)

1️⃣  CÂBLE ETHERNET > WIFI
   • Gain: -20 à -50ms ping
   • Câble Cat5e minimum (Cat6 recommandé)
   • Connexion directe routeur → PC (pas de switch si possible)

2️⃣  CHANGER DNS
   • DNS par défaut FAI souvent lent
   • Recommandé:
     → 1.1.1.1 (Cloudflare - le plus rapide)
     → 8.8.8.8 (Google - fiable)
     → 9.9.9.9 (Quad9 - sécurisé)
   • Comment changer:
     → Panneau config > Réseau > Adapter > Propriétés
     → IPv4 > Propriétés > DNS

3️⃣  QOS ROUTEUR (Quality of Service)
   • Prioriser trafic gaming
   • Interface admin routeur (192.168.1.1 souvent)
   • Activer QoS > Priorité élevée pour PC

4️⃣  FERMER APPS ARRIÈRE-PLAN
   • Steam, Epic, Windows Update = voleurs bandwidth
   • Fermer avant gaming/streaming

5️⃣  TCP OPTIMIZER
   • Boîte à Outils Wapinator > Réseau > TCP Optimizer
   • Optimise paramètres TCP/IP Windows
   • Gain: -5 à -20ms

═══════════════════════════════════════════════════════════════

📉 POUR RÉDUIRE PERTE PAQUETS

1️⃣  WIFI INSTABLE
   • Passer en Ethernet (solution #1)
   • Si Wifi obligatoire:
     → Se rapprocher routeur
     → Changer canal WiFi (moins encombré)
     → Upgrade routeur WiFi 6 (si vieux)

2️⃣  INTERFÉRENCES
   • Éloigner routeur de:
     → Micro-ondes
     → Téléphones sans fil
     → Baby monitors
   • Préférer bande 5GHz (moins encombrée que 2.4GHz)

3️⃣  ROUTEUR SURCHARGÉ
   • Redémarrer routeur (débrancher 30s)
   • Limiter nombre appareils connectés
   • MAJ firmware routeur

4️⃣  DRIVERS RÉSEAU
   • MAJ drivers carte réseau
   • Boîte à Outils > Snappy Driver Installer
   • Ou site fabricant carte mère

═══════════════════════════════════════════════════════════════

🌐 SI PROBLÈME PERSISTE

ÉTAPES DE DÉPANNAGE:

1. Tester avec câble Ethernet (éliminer WiFi)
2. Tester sur autre PC (éliminer matériel)
3. Contacter FAI (possible problème ligne)
4. Vérifier débit souscrit vs débit réel (speedtest.net)

OUTILS DIAGNOSTIC:
- Boîte à Outils > Wireshark (analyse trafic)
- Boîte à Outils > TCP Optimizer

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(tips)
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║                    ❓ AIDE - TEST RÉSEAU                    ║
╚══════════════════════════════════════════════════════════════╝

🤔 COMPRENDRE LES TESTS

PING:
- Temps aller-retour d'un paquet vers serveur
- Unité: millisecondes (ms)
- Plus c'est bas, mieux c'est

PACKET LOSS:
- Pourcentage de paquets perdus en transit
- 0% = idéal
- > 1% = problème

JITTER:
- Variation de latence entre paquets
- Latence instable = jitter élevé
- Cause micro-freezes en jeu/visio

DNS:
- Traduit noms (google.com) en IP (142.250.x.x)
- DNS lent = sites web lents à charger

TRACEROUTE:
- Chemin complet des paquets
- Montre chaque "saut" (routeur)
- Utile pour identifier où ça lag

═══════════════════════════════════════════════════════════════

💡 QUAND UTILISER CET OUTIL

✅ Avant d'acheter un jeu online (vérifier latence)
✅ Problèmes de lag inexpliqués
✅ Micro-freezes en visioconférence
✅ Comparer WiFi vs Ethernet
✅ Après changement FAI/routeur
✅ Diagnostiquer perte de paquets

═══════════════════════════════════════════════════════════════

🎮 VALEURS CIBLES GAMING

FPS Compétitif (Valorant, CS:GO):
- Ping: < 30ms obligatoire
- Packet loss: 0%
- Jitter: < 5ms

FPS Casual (CoD, Battlefield):
- Ping: < 50ms
- Packet loss: < 1%
- Jitter: < 15ms

MOBA (LoL, Dota):
- Ping: < 60ms
- Packet loss: < 2%

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)
    
    def export_report(self):
        """Exporter rapport"""
        content = self.results.toPlainText()
        
        if not content or "BIENVENUE" in content or "CONSEILS" in content:
            QMessageBox.warning(self, "⚠️", "Aucun test à exporter.\nLancez d'abord un test.")
            return
        
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_TestReseau_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 70 + "\n")
                f.write("  RAPPORT TEST RÉSEAU - WAPINATOR\n")
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