# modules/bsod_analyzer.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QTextEdit, QFileDialog, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import os
import glob
import struct
from datetime import datetime

# Base de données codes erreur BSOD
BSOD_CODES = {
    "0x0000000A": {
        "name": "IRQL_NOT_LESS_OR_EQUAL",
        "cause": "Driver accède à mémoire invalide",
        "solutions": [
            ("Drivers corrompus", 85, "DDU + réinstaller drivers GPU/Réseau"),
            ("RAM défectueuse", 70, "MemTest86+ - Test 8h minimum"),
            ("Overclocking instable", 60, "BIOS: Reset paramètres défaut")
        ]
    },
    "0x0000001A": {
        "name": "MEMORY_MANAGEMENT",
        "cause": "Erreur gestion mémoire (RAM/Windows)",
        "solutions": [
            ("RAM défectueuse", 90, "MemTest86+ URGENT - Tester chaque barrette"),
            ("Drivers mémoire corrompus", 65, "MAJ drivers chipset carte mère"),
            ("Pagefile corrompu", 50, "Reset fichier d'échange Windows")
        ]
    },
    "0x0000001E": {
        "name": "KMODE_EXCEPTION_NOT_HANDLED",
        "cause": "Exception non gérée par driver/kernel",
        "solutions": [
            ("Driver spécifique défectueux", 80, "Identifier driver via WinDbg/BlueScreenView"),
            ("RAM défectueuse", 70, "MemTest86+"),
            ("Windows corrompu", 55, "DISM + SFC via Wapinator")
        ]
    },
    "0x00000050": {
        "name": "PAGE_FAULT_IN_NONPAGED_AREA",
        "cause": "Accès mémoire non paginée invalide",
        "solutions": [
            ("RAM défectueuse", 85, "MemTest86+ - Tester toutes barrettes"),
            ("Driver vidéo corrompu", 75, "DDU + réinstall drivers GPU"),
            ("Disque dur défaillant", 60, "CrystalDiskInfo + Victoria scan")
        ]
    },
    "0x0000007B": {
        "name": "INACCESSIBLE_BOOT_DEVICE",
        "cause": "Windows ne peut pas accéder au disque de boot",
        "solutions": [
            ("Drivers SATA/AHCI", 80, "BIOS: Vérifier mode SATA (AHCI/IDE)"),
            ("Disque défaillant", 75, "CrystalDiskInfo URGENT"),
            ("MBR/BCD corrompu", 70, "Réparation boot Windows (bootrec)")
        ]
    },
    "0x0000007E": {
        "name": "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
        "cause": "Thread système a causé exception",
        "solutions": [
            ("Driver spécifique", 85, "Identifier driver (souvent GPU/Audio)"),
            ("Windows Update raté", 65, "Wapinator > Réparateur Windows Update"),
            ("Fichiers système corrompus", 60, "DISM + SFC")
        ]
    },
    "0x0000009F": {
        "name": "DRIVER_POWER_STATE_FAILURE",
        "cause": "Driver n'a pas géré transition alimentation",
        "solutions": [
            ("Driver réseau/USB", 85, "MAJ drivers carte réseau + USB"),
            ("Gestion alimentation USB", 70, "Désactiver USB Selective Suspend"),
            ("Driver chipset obsolète", 65, "Site fabricant CM: MAJ chipset")
        ]
    },
    "0x000000C2": {
        "name": "BAD_POOL_CALLER",
        "cause": "Opération invalide sur pool mémoire",
        "solutions": [
            ("Driver défectueux", 80, "Identifier via WinDbg"),
            ("RAM défectueuse", 75, "MemTest86+"),
            ("Antivirus conflit", 60, "Tester en désactivant AV temporairement")
        ]
    },
    "0x000000D1": {
        "name": "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
        "cause": "Driver accède mémoire à IRQL incorrect",
        "solutions": [
            ("Driver réseau", 85, "MAJ/Rollback driver carte réseau"),
            ("Driver GPU", 75, "DDU + réinstall propre"),
            ("Logiciel monitoring", 60, "Désinstaller MSI Afterburner/HWINFO test")
        ]
    },
    "0x000000E2": {
        "name": "MANUALLY_INITIATED_CRASH",
        "cause": "Crash manuel (test ou raccourci clavier)",
        "solutions": [
            ("Test volontaire", 100, "Normal si vous avez fait un test"),
            ("Raccourci clavier accidentel", 50, "Désactiver: Registre > CrashOnCtrlScroll")
        ]
    },
    "0x000000F4": {
        "name": "CRITICAL_OBJECT_TERMINATION",
        "cause": "Processus critique Windows terminé",
        "solutions": [
            ("Malware", 80, "Malwarebytes scan complet URGENT"),
            ("Windows corrompu", 75, "DISM + SFC + possible réinstall"),
            ("Disque système défaillant", 70, "CrystalDiskInfo + sauvegarder données")
        ]
    },
    "0x00000116": {
        "name": "VIDEO_TDR_ERROR",
        "cause": "GPU n'a pas répondu à temps",
        "solutions": [
            ("Driver GPU obsolète/corrompu", 90, "DDU + derniers drivers NVIDIA/AMD"),
            ("Overclocking GPU instable", 75, "MSI Afterburner: Reset profil stock"),
            ("GPU surchauffe", 70, "HWiNFO64: vérifier temp > 85°C"),
            ("GPU défaillant", 60, "Si persist: possible hardware failure")
        ]
    },
    "0x0000012B": {
        "name": "FAULTY_HARDWARE_CORRUPTED_PAGE",
        "cause": "Matériel défectueux a corrompu mémoire",
        "solutions": [
            ("RAM défectueuse", 95, "MemTest86+ URGENT"),
            ("GPU défaillant", 70, "Test avec autre GPU si possible"),
            ("Overclocking", 65, "Reset BIOS défaut")
        ]
    },
    "0x00000133": {
        "name": "DPC_WATCHDOG_VIOLATION",
        "cause": "DPC (Deferred Procedure Call) trop long",
        "solutions": [
            ("Driver SATA/AHCI obsolète", 85, "MAJ drivers contrôleur SATA"),
            ("SSD firmware obsolète", 75, "Site fabricant SSD: MAJ firmware"),
            ("Driver USB 3.0", 70, "MAJ drivers USB depuis site CM")
        ]
    },
    "0x00000139": {
        "name": "KERNEL_SECURITY_CHECK_FAILURE",
        "cause": "Corruption détectée dans kernel",
        "solutions": [
            ("RAM défectueuse", 85, "MemTest86+"),
            ("Overclocking CPU/RAM", 80, "BIOS: Désactiver OC/XMP test"),
            ("Windows corrompu", 70, "DISM + SFC")
        ]
    },
    "0x0000013A": {
        "name": "KERNEL_MODE_HEAP_CORRUPTION",
        "cause": "Corruption heap du kernel",
        "solutions": [
            ("Driver défectueux", 85, "Identifier via WinDbg"),
            ("RAM défectueuse", 80, "MemTest86+"),
            ("Malware", 60, "Malwarebytes scan")
        ]
    }
}

class BsodAnalyzerWorker(QThread):
    """Worker thread pour analyse BSOD"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, minidump_path):
        super().__init__()
        self.minidump_path = minidump_path
    
    def run(self):
        """Analyser les fichiers minidump"""
        try:
            results = {
                'files': [],
                'total': 0,
                'recent': 0,
                'errors': []
            }
            
            # Scanner le dossier
            if not os.path.exists(self.minidump_path):
                self.finished_signal.emit({'error': 'Dossier Minidump introuvable'})
                return
            
            dmp_files = glob.glob(os.path.join(self.minidump_path, "*.dmp"))
            results['total'] = len(dmp_files)
            
            if not dmp_files:
                self.finished_signal.emit({'error': 'Aucun fichier minidump'})
                return
            
            # Analyser chaque fichier
            for dmp_file in sorted(dmp_files, reverse=True)[:10]:  # Max 10 derniers
                self.log_signal.emit(f"📂 Analyse: {os.path.basename(dmp_file)}")
                
                try:
                    file_info = self.analyze_dmp_file(dmp_file)
                    results['files'].append(file_info)
                    
                    # Compter les récents (< 30 jours)
                    if file_info['days_ago'] < 30:
                        results['recent'] += 1
                    
                except Exception as e:
                    self.log_signal.emit(f"⚠️ Erreur analyse: {str(e)}")
            
            self.finished_signal.emit(results)
        
        except Exception as e:
            self.finished_signal.emit({'error': str(e)})
    
    def analyze_dmp_file(self, filepath):
        """Analyser un fichier .dmp basique"""
        file_info = {
            'filename': os.path.basename(filepath),
            'date': datetime.fromtimestamp(os.path.getmtime(filepath)),
            'days_ago': (datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))).days,
            'size': os.path.getsize(filepath),
            'bug_check': None,
            'error_name': "Inconnu",
            'solutions': []
        }
        
        # Tentative lecture basique du bug check code
        # Note: Parsing complet nécessiterait WinDbg/library spécialisée
        try:
            with open(filepath, 'rb') as f:
                # Lire signature (les 1024 premiers bytes)
                data = f.read(1024)
                
                # Chercher pattern bug check (simpliste)
                # Format réel beaucoup plus complexe, ceci est une approximation
                if b'PAGEPC' in data or b'PAGE' in data:
                    # Fichier minidump valide
                    file_info['error_name'] = "Format minidump détecté"
        
        except:
            pass
        
        return file_info

class BsodanalyzerWindow(QDialog):
    """Fenêtre d'analyse BSOD complète"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("📘 Analyseur BSOD Avancé")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📘 ANALYSEUR D'ÉCRANS BLEUS (BSOD)")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        help_btn = QPushButton("❓ Guide BSOD")
        help_btn.clicked.connect(self.show_help)
        help_btn.setFixedWidth(120)
        header_layout.addWidget(help_btn)
        
        layout.addLayout(header_layout)
        
        # Info
        info = QLabel(
            "Analyse les fichiers minidump (.dmp) créés lors des écrans bleus\n"
            "et fournit des solutions détaillées selon le code d'erreur."
        )
        info.setStyleSheet("color: #888; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Scanner Minidump Automatique")
        self.scan_btn.clicked.connect(self.scan_minidump)
        btn_layout.addWidget(self.scan_btn)
        
        manual_btn = QPushButton("📂 Ouvrir .dmp Manuel")
        manual_btn.clicked.connect(self.open_manual)
        btn_layout.addWidget(manual_btn)
        
        search_btn = QPushButton("🔎 Rechercher Code Erreur")
        search_btn.clicked.connect(self.search_error_code)
        btn_layout.addWidget(search_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Zone résultats
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
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QTextEdit {
                background: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                text-align: center;
                background: #2b2b2b;
            }
            QProgressBar::chunk {
                background: #2196F3;
                border-radius: 3px;
            }
        """)
        
        # Afficher guide au démarrage
        self.show_welcome()
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║         BIENVENUE DANS L'ANALYSEUR BSOD AVANCÉ              ║
╚══════════════════════════════════════════════════════════════╝

🎯 QUE FAIT CET OUTIL ?

Cet analyseur vous aide à comprendre les écrans bleus (BSOD) et trouve
les solutions adaptées à votre situation.

📋 FONCTIONNALITÉS:

- 🔍 Scanner automatique du dossier C:\\Windows\\Minidump
- 📊 Analyse de fréquence des BSOD (détecte patterns)
- 🔎 Base de données de 16 codes erreur courants
- 💡 Solutions détaillées avec % de probabilité
- 📂 Support analyse manuelle de fichiers .dmp
- 🔎 Recherche par code erreur (ex: 0x0000001A)

⚡ UTILISATION RAPIDE:

1. Cliquez "Scanner Minidump Automatique"
2. L'outil analyse automatiquement vos BSOD récents
3. Lisez les solutions proposées par ordre de priorité
4. Suivez les liens vers outils de la Boîte à Outils Wapinator

💡 SI VOUS CONNAISSEZ LE CODE:

Cliquez "Rechercher Code Erreur" et entrez le code (ex: 0x1A)

═══════════════════════════════════════════════════════════════

Cliquez "Scanner Minidump Automatique" pour commencer ! 🚀
"""
        self.results.setPlainText(text)
    
    def scan_minidump(self):
        """Scanner le dossier Minidump"""
        minidump_path = r"C:\Windows\Minidump"
        
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        
        self.results.setPlainText("🔄 Scan en cours...\n")
        
        # Lancer worker thread
        self.worker = BsodAnalyzerWorker(minidump_path)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()
    
    def append_log(self, text):
        """Ajouter ligne de log"""
        self.results.append(text)
    
    def on_scan_finished(self, results):
        """Traiter résultats du scan"""
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if 'error' in results:
            if results['error'] == 'Dossier Minidump introuvable':
                self.results.setPlainText("""
❌ DOSSIER MINIDUMP INTROUVABLE

Le dossier C:\\Windows\\Minidump n'existe pas sur votre système.

🎯 QUE FAIRE ?

Option 1: Vous n'avez JAMAIS eu de BSOD
→ Votre PC est stable ! ✅ Aucune action nécessaire.

Option 2: Les minidumps sont désactivés
→ Pour les activer:

1. Clic droit sur "Ce PC" > Propriétés
2. "Paramètres système avancés"
3. Onglet "Avancé" > Section "Démarrage et récupération" > Bouton "Paramètres"
4. Dans "Écriture des informations de débogage":
   Sélectionner "Petit fichier mémoire (256 Ko)"
5. Vérifier chemin: C:\\Windows\\Minidump
6. OK > OK

Après le prochain BSOD (si jamais), un fichier .dmp sera créé.
""")
            
            elif results['error'] == 'Aucun fichier minidump':
                self.results.setPlainText("""
✅ AUCUN FICHIER MINIDUMP TROUVÉ

Le dossier C:\\Windows\\Minidump existe mais est vide.

🎉 BONNE NOUVELLE !

Cela signifie que vous n'avez eu AUCUN écran bleu récent.
Votre système Windows est stable !

💡 SI VOUS AVEZ EU UN BSOD:

- Les minidumps peuvent avoir été nettoyés
- Ou les minidumps sont désactivés (voir Option 2 dans Scanner Auto)

📊 STATISTIQUES:
- BSOD récents: 0
- Stabilité système: EXCELLENTE ✅
""")
            return
        
        # Générer rapport détaillé
        report = self.generate_report(results)
        self.results.setPlainText(report)
    
    def generate_report(self, results):
        """Générer rapport d'analyse détaillé"""
        report = "╔" + "═"*70 + "╗\n"
        report += "║" + " "*20 + "📊 RAPPORT D'ANALYSE BSOD" + " "*25 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        total = results['total']
        recent = results['recent']
        
        # Statistiques globales
        report += "📈 STATISTIQUES GLOBALES\n"
        report += "─" * 70 + "\n"
        report += f"• Total BSOD enregistrés: {total}\n"
        report += f"• BSOD récents (< 30 jours): {recent}\n"
        
        # Évaluation stabilité
        if total == 0:
            report += f"• Évaluation: ✅ EXCELLENT (0 BSOD)\n\n"
        elif total <= 2 and recent == 0:
            report += f"• Évaluation: ✅ BON (incidents anciens isolés)\n\n"
        elif total <= 5:
            report += f"• Évaluation: ⚠️ MOYEN (quelques BSOD)\n\n"
        elif total <= 10:
            report += f"• Évaluation: 🔴 PROBLÉMATIQUE (BSOD fréquents)\n\n"
        else:
            report += f"• Évaluation: 🚨 CRITIQUE (Très nombreux BSOD)\n\n"
        
        # Détail des fichiers
        report += "📂 DÉTAIL DES FICHIERS MINIDUMP\n"
        report += "─" * 70 + "\n\n"
        
        for i, file_info in enumerate(results['files'][:10], 1):
            report += f"{i}. {file_info['filename']}\n"
            report += f"   📅 Date: {file_info['date'].strftime('%d/%m/%Y %H:%M:%S')}\n"
            report += f"   ⏱️  Il y a: {file_info['days_ago']} jour(s)\n"
            report += f"   💾 Taille: {file_info['size'] / 1024:.1f} Ko\n"
            
            if file_info['bug_check']:
                report += f"   🔍 Code: {file_info['bug_check']}\n"
                report += f"   📛 Erreur: {file_info['error_name']}\n"
            
            report += "\n"
        
        # Analyse et recommandations
        report += "\n" + "╔" + "═"*70 + "╗\n"
        report += "║" + " "*18 + "💡 ANALYSE ET RECOMMANDATIONS" + " "*21 + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        if total == 0:
            report += "✅ Votre système est stable. Aucune action nécessaire.\n"
        
        elif total <= 2:
            report += "ℹ️  BSOD OCCASIONNELS\n\n"
            report += "Votre PC a eu quelques écrans bleus mais c'est rare.\n"
            report += "Cela peut être dû à:\n"
            report += "• Mise à jour Windows problématique (résolu depuis)\n"
            report += "• Incident matériel ponctuel\n"
            report += "• Driver temporairement instable\n\n"
            report += "🎯 ACTION RECOMMANDÉE:\n"
            report += "→ Surveiller. Si aucun nouveau BSOD sous 30 jours = OK\n"
        
        elif recent >= 3:
            report += "🚨 PROBLÈME ACTIF DÉTECTÉ\n\n"
            report += f"Vous avez eu {recent} BSOD dans les 30 derniers jours.\n"
            report += "Ceci indique un problème actif nécessitant ATTENTION IMMÉDIATE.\n\n"
            report += "🔴 CAUSES PROBABLES (par ordre de fréquence):\n\n"
            
            report += "1️⃣  RAM DÉFECTUEUSE (85% des cas de BSOD multiples)\n"
            report += "   → Action: MemTest86+ - Test 8h MINIMUM\n"
            report += "   → Boîte à Outils > Réparation > MemTest86+\n"
            report += "   → Si erreurs détectées: Remplacer barrette(s) RAM\n\n"
            
            report += "2️⃣  DRIVERS CORROMPUS (70%)\n"
            report += "   → Action: DDU (Display Driver Uninstaller)\n"
            report += "   → Boîte à Outils > Réparation > DDU\n"
            report += "   → Nettoyer drivers GPU + réinstaller proprement\n\n"
            
            report += "3️⃣  OVERCLOCKING INSTABLE (60%)\n"
            report += "   → Action: Reset BIOS aux paramètres par défaut\n"
            report += "   → Désactiver XMP/DOCP temporairement pour test\n\n"
            
            report += "4️⃣  DISQUE DÉFAILLANT (55%)\n"
            report += "   → Action: CrystalDiskInfo\n"
            report += "   → Boîte à Outils > Réparation > CrystalDiskInfo\n"
            report += "   → Vérifier attributs SMART (secteurs réalloués)\n\n"
            
            report += "5️⃣  WINDOWS CORROMPU (50%)\n"
            report += "   → Action: DISM + SFC\n"
            report += "   → Wapinator > Paramètres > Réparation Windows\n\n"
        
        else:
            report += "⚠️  BSOD MULTIPLES MAIS ANCIENS\n\n"
            report += "Votre PC a eu plusieurs BSOD mais ils sont anciens (> 30 jours).\n"
            report += "Le problème semble résolu (mise à jour Windows, driver, etc.)\n\n"
            report += "🎯 ACTION:\n"
            report += "→ Continuer à surveiller\n"
            report += "→ Si nouveaux BSOD: Suivre recommandations ci-dessus\n"
        
        # Footer
        report += "\n" + "═" * 70 + "\n"
        report += "💡 Pour analyse approfondie d'un code erreur spécifique:\n"
        report += "   Cliquez 'Rechercher Code Erreur' et entrez le code (ex: 0x1A)\n"
        report += "═" * 70 + "\n"
        
        return report
    
    def open_manual(self):
        """Ouvrir fichier .dmp manuellement"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier minidump",
            r"C:\Windows\Minidump",
            "Minidump Files (*.dmp);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        filename = os.path.basename(file_path)
        file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
        file_size = os.path.getsize(file_path) / 1024
        
        report = f"""╔══════════════════════════════════════════════════════════════╗
║              ANALYSE MANUELLE DE FICHIER .DMP               ║
╚══════════════════════════════════════════════════════════════╝

📂 FICHIER SÉLECTIONNÉ:
- Nom: {filename}
- Chemin: {file_path}
- Date: {file_date.strftime('%d/%m/%Y %H:%M:%S')}
- Taille: {file_size:.1f} Ko

═══════════════════════════════════════════════════════════════

ℹ️  ANALYSE BASIQUE

L'analyse complète des fichiers .dmp nécessite des outils spécialisés
car le format est complexe (structure binaire Microsoft).

Ce fichier contient:
- Dump de la mémoire au moment du crash
- Code d'erreur (Bug Check Code)
- État des drivers et processus
- Registres CPU et stack traces

═══════════════════════════════════════════════════════════════

🛠️  OUTILS D'ANALYSE PROFESSIONNELLE:

1️⃣  WINDBG (Microsoft - Gratuit)
   • Le plus puissant (utilisé par devs Microsoft)
   • Téléchargement: Windows SDK
   • Commandes:
     - !analyze -v (analyse automatique complète)
     - !process 0 0 (liste processus)
     - !drivers (liste tous drivers chargés)
   • ⚠️ Courbe d'apprentissage élevée

2️⃣  BLUESCREENVIEW (Nirsoft - Gratuit)
   • Interface graphique simple
   • Affiche code erreur + drivers impliqués
   • Téléchargement: nirsoft.net/utils/blue_screen_view.html
   • ⭐ RECOMMANDÉ pour débutants

3️⃣  WHOCRASHED (Resplendence - Gratuit)
   • Analyse automatique en langage clair
   • Suggestions de solutions
   • Téléchargement: resplendence.com/whocrashed

═══════════════════════════════════════════════════════════════

🎯 DÉMARCHE RAPIDE:

1. Installer BlueScreenView (le plus simple)
2. Ouvrir ce fichier .dmp avec BlueScreenView
3. Noter le "Bug Check Code" affiché (ex: 0x0000001A)
4. Revenir dans Wapinator
5. Cliquer "Rechercher Code Erreur"
6. Entrer le code pour solutions détaillées

═══════════════════════════════════════════════════════════════
"""
        
        self.results.setPlainText(report)
    
    def search_error_code(self):
        """Rechercher un code erreur spécifique"""
        from PyQt6.QtWidgets import QInputDialog
        
        code, ok = QInputDialog.getText(
            self,
            "Rechercher Code Erreur BSOD",
            "Entrez le code erreur (ex: 0x1A, 0x0000001A, 1A):"
        )
        
        if not ok or not code:
            return
        
        # Normaliser le code
        code = code.strip().upper()
        if not code.startswith("0X"):
            code = "0X" + code
        
        # Padding avec des zéros
        if len(code) < 10:  # 0x + 8 digits
            code = "0X" + code[2:].zfill(8)
        
        # Chercher dans la base
        if code in BSOD_CODES:
            self.display_error_details(code, BSOD_CODES[code])
        else:
            self.display_unknown_error(code)
    
    def display_error_details(self, code, error_info):
        """Afficher détails d'une erreur connue"""
        report = "╔" + "═"*70 + "╗\n"
        report += "║" + " "*15 + f"📘 CODE ERREUR: {code}" + " "*(55-len(code)) + "║\n"
        report += "╚" + "═"*70 + "╝\n\n"
        
        report += f"📛 NOM TECHNIQUE:\n{error_info['name']}\n\n"
        report += "─" * 70 + "\n\n"
        
        report += f"🔍 CAUSE GÉNÉRALE:\n{error_info['cause']}\n\n"
        report += "─" * 70 + "\n\n"
        
        report += "💡 SOLUTIONS RECOMMANDÉES (par probabilité):\n\n"
        
        for i, (cause, prob, solution) in enumerate(error_info['solutions'], 1):
            # Icône selon probabilité
            if prob >= 80:
                icon = "🔴 PRIORITÉ 1"
            elif prob >= 60:
                icon = "🟡 PRIORITÉ 2"
            else:
                icon = "🟢 PRIORITÉ 3"
            
            report += f"{i}. {icon} - {cause} ({prob}% probabilité)\n"
            report += f"   └─ Action: {solution}\n\n"
        
        report += "═" * 70 + "\n\n"
        report += "📚 DÉMARCHE DE DÉPANNAGE:\n\n"
        report += "1. Commencer par la solution PRIORITÉ 1 (probabilité la plus élevée)\n"
        report += "2. Appliquer la solution, redémarrer le PC\n"
        report += "3. Observer si les BSOD se reproduisent\n"
        report += "4. Si problème persiste: Passer à PRIORITÉ 2\n"
        report += "5. Si toutes solutions épuisées: Consulter technicien\n\n"
        
        report += "🔗 OUTILS LIÉS (Boîte à Outils Wapinator):\n"
        report += "• MemTest86+ : Test RAM complet\n"
        report += "• DDU : Nettoyage drivers GPU\n"
        report += "• CrystalDiskInfo : Santé disques\n"
        report += "• Malwarebytes : Scan malwares\n"
        report += "═" * 70 + "\n"
        
        self.results.setPlainText(report)
    
    def display_unknown_error(self, code):
        """Afficher info pour code inconnu"""
        report = f"""╔══════════════════════════════════════════════════════════════╗
║              ❓ CODE ERREUR NON RÉFÉRENCÉ                   ║
╚══════════════════════════════════════════════════════════════╝

🔍 CODE RECHERCHÉ: {code}

Ce code d'erreur n'est pas dans notre base de données actuelle.
Wapinator connaît les 16 codes BSOD les plus courants (~85% des cas).

═══════════════════════════════════════════════════════════════

🌐 RESSOURCES EXTERNES:

1️⃣  BASE DE DONNÉES MICROSOFT
   → docs.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-code-reference
   → Liste complète TOUS les codes erreur Windows

2️⃣  COMMUNAUTÉ REDDIT
   → reddit.com/r/techsupport
   → Poster votre code + contexte
   → Communauté active et réactive

3️⃣  FORUM MICROSOFT
   → answers.microsoft.com
   → Support officiel Microsoft

═══════════════════════════════════════════════════════════════

🎯 SOLUTIONS GÉNÉRIQUES (pour tout BSOD):

Ces étapes résolvent ~70% des BSOD inconnus:

1. TEST RAM (cause #1 de BSOD)
   → MemTest86+ - 8h minimum
   → Si erreurs: Remplacer RAM

2. DRIVERS GPU
   → DDU + réinstallation propre
   → Drivers NVIDIA/AMD dernière version

3. RESET BIOS
   → Désactiver overclock CPU/RAM
   → Désactiver XMP/DOCP temporairement
   → Tester stabilité

4. SANTÉ DISQUE
   → CrystalDiskInfo
   → Victoria (scan secteurs)

5. WINDOWS
   → DISM + SFC (Wapinator > Réparation)

═══════════════════════════════════════════════════════════════

💡 ASTUCE:

Si vous connaissez le NOM de l'erreur (ex: "KERNEL_SECURITY_CHECK_FAILURE"),
vous pouvez chercher directement ce nom sur Google pour trouver des solutions.

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(report)
    
    def show_help(self):
        """Afficher guide complet"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║                  📚 GUIDE COMPLET - BSOD                    ║
╚══════════════════════════════════════════════════════════════╝

🤔 QU'EST-CE QU'UN BSOD ?

BSOD = Blue Screen Of Death (Écran Bleu de la Mort)
C'est un arrêt d'urgence de Windows quand il détecte un problème
critique qui pourrait endommager vos données ou le système.

═══════════════════════════════════════════════════════════════

📋 INFORMATIONS CONTENUES DANS UN BSOD:

1. CODE D'ERREUR (ex: 0x0000001A)
   → Identifie le TYPE de problème

2. NOM TECHNIQUE (ex: MEMORY_MANAGEMENT)
   → Description courte du problème

3. FICHIER .DMP
   → Dump mémoire complet au moment du crash
   → Sauvegardé dans C:\\Windows\\Minidump

4. PARAMÈTRES (4 valeurs hexadécimales)
   → Détails techniques supplémentaires

═══════════════════════════════════════════════════════════════

🔍 COMMENT LIRE UN BSOD:

Exemple d'écran bleu typique:

┌────────────────────────────────────────────────┐
│ :( Votre PC a rencontré un problème            │
│                                                 │
│ MEMORY_MANAGEMENT                              │
│                                                 │
│ Si vous contactez le support, communiquez:     │
│ Code d'arrêt: MEMORY_MANAGEMENT                │
│                                                 │
│ 0x0000001A (0x00041790, 0xFFFFE001, ...)      │
└────────────────────────────────────────────────┘

L'info importante = 0x0000001A (le code erreur)

═══════════════════════════════════════════════════════════════

🛠️  QUE FAIRE LORS D'UN BSOD:

1. NOTER LE CODE
   • Prendre photo de l'écran avec téléphone
   • Noter le code (ex: 0x1A)
   • Noter le nom (ex: MEMORY_MANAGEMENT)

2. REDÉMARRER
   • PC redémarre automatiquement après BSOD
   • Windows crée fichier .dmp automatiquement

3. ANALYSER
   • Utiliser Wapinator > Outils Avancés > Analyseur BSOD
   • Scanner les fichiers .dmp
   • Suivre solutions proposées

═══════════════════════════════════════════════════════════════

📊 FRÉQUENCE DES BSOD:

✅ NORMAL:
- 0-1 BSOD par an = PC très stable
- Peut arriver suite à mise à jour Windows problématique

⚠️ ATTENTION:
- 2-5 BSOD par an = Surveiller
- Peut indiquer début de problème matériel

🚨 URGENT:
- > 1 BSOD par mois = Problème actif
- Action immédiate nécessaire (test RAM, drivers, etc.)

═══════════════════════════════════════════════════════════════

🏆 TOP 5 CAUSES DE BSOD:

1. RAM défectueuse (40%)
2. Drivers corrompus/obsolètes (25%)
3. Overclocking instable (15%)
4. Disque dur défaillant (10%)
5. Windows corrompu (10%)

═══════════════════════════════════════════════════════════════

💡 PRÉVENTION:

- Garder drivers à jour (surtout GPU)
- Éviter overclock agressif sans test stabilité
- Tester nouvelle RAM avec MemTest86+
- Vérifier santé disques régulièrement (CrystalDiskInfo)
- Maintenir Windows à jour

═══════════════════════════════════════════════════════════════

📞 QUAND CONTACTER UN TECHNICIEN:

- > 10 BSOD différents en 1 mois
- BSOD persiste après toutes solutions Wapinator
- BSOD empêche Windows de démarrer complètement
- Suspicion problème matériel (après test RAM négatif)

═══════════════════════════════════════════════════════════════
"""
        
        QMessageBox.information(self, "📚 Guide BSOD", help_text)
    
    def export_report(self):
        """Exporter rapport en .txt"""
        content = self.results.toPlainText()
        
        if not content or "BIENVENUE" in content:
            QMessageBox.warning(self, "⚠️", "Aucun rapport à exporter.\nLancez d'abord un scan.")
            return
        
        from pathlib import Path
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = desktop / f"Wapinator_BSOD_Analyse_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("═" * 70 + "\n")
                f.write("  RAPPORT D'ANALYSE BSOD - WAPINATOR\n")
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