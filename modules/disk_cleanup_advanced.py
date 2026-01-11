# modules/disk_cleanup_advanced.py
"""
Disk Cleanup Advanced - Nettoyage disque avancé avec analyse détaillée
Supporte : Navigateurs, Gaming, Windows.old, WinSxS, Fichiers volumineux, Doublons
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                            QTextEdit, QProgressBar, QMessageBox, QCheckBox, QGroupBox,
                            QScrollArea, QWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import hashlib
from collections import defaultdict

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


class DiskCleanupWorker(QThread):
    """Worker pour analyse et nettoyage disque"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    category_signal = pyqtSignal(str, int, int)  # category, files, size_mb
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, categories, mode="analyze"):
        super().__init__()
        self.categories = categories
        self.mode = mode  # "analyze" ou "clean"
        self.results = {}
    
    def run(self):
        """Exécuter l'analyse ou le nettoyage"""
        try:
            self.log_signal.emit("╔" + "═"*70 + "╗")
            if self.mode == "analyze":
                self.log_signal.emit("║" + " "*20 + "🔍 ANALYSE DISQUE" + " "*29 + "║")
            else:
                self.log_signal.emit("║" + " "*18 + "🧹 NETTOYAGE DISQUE" + " "*29 + "║")
            self.log_signal.emit("╚" + "═"*70 + "╝\n")
            
            total_categories = len(self.categories)
            
            for i, category in enumerate(self.categories):
                progress = int((i / total_categories) * 100)
                self.progress_signal.emit(progress)
                
                if category == "browsers":
                    self.handle_browsers()
                elif category == "gaming":
                    self.handle_gaming()
                elif category == "windows_old":
                    self.handle_windows_old()
                elif category == "winsxs":
                    self.handle_winsxs()
                elif category == "large_files":
                    self.handle_large_files()
                elif category == "duplicates":
                    self.handle_duplicates()
                elif category == "logs":
                    self.handle_logs()
                elif category == "windows_store":
                    self.handle_windows_store()
            
            self.progress_signal.emit(100)
            self.finished_signal.emit(self.results)
        
        except Exception as e:
            self.log_signal.emit(f"❌ Erreur: {str(e)}")
            self.finished_signal.emit({'error': str(e)})
    
    def handle_browsers(self):
        """Nettoyer cache navigateurs"""
        self.log_signal.emit("\n📁 NAVIGATEURS")
        self.log_signal.emit("─" * 70)
        
        browsers = {
            'Chrome': Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cache',
            'Edge': Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'Cache',
            'Firefox': Path(os.environ.get('APPDATA', '')) / 'Mozilla' / 'Firefox' / 'Profiles',
            'Brave': Path(os.environ.get('LOCALAPPDATA', '')) / 'BraveSoftware' / 'Brave-Browser' / 'User Data' / 'Default' / 'Cache'
        }
        
        total_files = 0
        total_size = 0
        
        for browser, cache_path in browsers.items():
            try:
                if not cache_path.exists():
                    self.log_signal.emit(f"  ○ {browser}: Non installé")
                    continue
                
                # Firefox a une structure différente
                if browser == "Firefox":
                    profile_dirs = list(cache_path.glob("*.default*"))
                    if not profile_dirs:
                        self.log_signal.emit(f"  ○ {browser}: Aucun profil trouvé")
                        continue
                    cache_path = profile_dirs[0] / 'cache2'
                
                if not cache_path.exists():
                    self.log_signal.emit(f"  ○ {browser}: Cache vide")
                    continue
                
                # Compter fichiers et taille
                files, size = self.count_items(cache_path)
                
                if files > 0:
                    size_mb = size / (1024**2)
                    self.log_signal.emit(f"  → {browser}: {files} fichiers ({size_mb:.1f} Mo)")
                    
                    if self.mode == "clean":
                        self.log_signal.emit(f"    🧹 Nettoyage en cours...")
                        deleted = self.delete_folder_contents(cache_path)
                        if deleted:
                            self.log_signal.emit(f"    ✅ {browser} nettoyé")
                            total_files += files
                            total_size += size
                        else:
                            self.log_signal.emit(f"    ⚠️ Certains fichiers en cours d'utilisation")
                    else:
                        total_files += files
                        total_size += size
                else:
                    self.log_signal.emit(f"  ○ {browser}: Cache vide")
            
            except Exception as e:
                self.log_signal.emit(f"  ❌ {browser}: Erreur - {str(e)}")
        
        self.results['browsers'] = {'files': total_files, 'size': total_size}
        self.category_signal.emit("Navigateurs", total_files, int(total_size / (1024**2)))
    
    def handle_gaming(self):
        """Nettoyer cache gaming"""
        self.log_signal.emit("\n🎮 GAMING")
        self.log_signal.emit("─" * 70)
        
        gaming_caches = {
            'Steam Shader Cache': Path(os.environ.get('LOCALAPPDATA', '')) / 'Steam' / 'htmlcache',
            'Epic Games Cache': Path(os.environ.get('LOCALAPPDATA', '')) / 'EpicGamesLauncher' / 'Saved' / 'webcache',
            'NVIDIA Shader Cache': Path(os.environ.get('LOCALAPPDATA', '')) / 'NVIDIA' / 'DXCache',
            'AMD Shader Cache': Path(os.environ.get('LOCALAPPDATA', '')) / 'AMD' / 'DxCache',
            'Origin Cache': Path(os.environ.get('APPDATA', '')) / 'Origin',
        }
        
        total_files = 0
        total_size = 0
        
        for name, cache_path in gaming_caches.items():
            try:
                if not cache_path.exists():
                    self.log_signal.emit(f"  ○ {name}: Non trouvé")
                    continue
                
                files, size = self.count_items(cache_path)
                
                if files > 0:
                    size_mb = size / (1024**2)
                    self.log_signal.emit(f"  → {name}: {files} fichiers ({size_mb:.1f} Mo)")
                    
                    if self.mode == "clean":
                        self.log_signal.emit(f"    🧹 Nettoyage en cours...")
                        deleted = self.delete_folder_contents(cache_path)
                        if deleted:
                            self.log_signal.emit(f"    ✅ {name} nettoyé")
                            total_files += files
                            total_size += size
                        else:
                            self.log_signal.emit(f"    ⚠️ Certains fichiers en cours d'utilisation")
                    else:
                        total_files += files
                        total_size += size
                else:
                    self.log_signal.emit(f"  ○ {name}: Cache vide")
            
            except Exception as e:
                self.log_signal.emit(f"  ❌ {name}: Erreur - {str(e)}")
        
        self.results['gaming'] = {'files': total_files, 'size': total_size}
        self.category_signal.emit("Gaming", total_files, int(total_size / (1024**2)))
    
    def handle_windows_old(self):
        """Nettoyer Windows.old"""
        self.log_signal.emit("\n🪟 WINDOWS.OLD")
        self.log_signal.emit("─" * 70)
        
        windows_old = Path("C:\\Windows.old")
        
        if not windows_old.exists():
            self.log_signal.emit("  ○ Aucun dossier Windows.old trouvé")
            self.results['windows_old'] = {'files': 0, 'size': 0}
            self.category_signal.emit("Windows.old", 0, 0)
            return
        
        try:
            files, size = self.count_items(windows_old)
            size_gb = size / (1024**3)
            
            self.log_signal.emit(f"  → Windows.old trouvé: {size_gb:.2f} Go")
            
            if self.mode == "clean":
                self.log_signal.emit(f"    🧹 Suppression en cours (peut prendre plusieurs minutes)...")
                
                # Utiliser cleanmgr pour supprimer proprement
                try:
                    # Méthode 1 : takeown + rmdir
                    subprocess.run(
                        ["takeown", "/F", str(windows_old), "/R", "/D", "Y"],
                        capture_output=True,
                        timeout=300,
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    
                    subprocess.run(
                        ["icacls", str(windows_old), "/grant", "administrators:F", "/T"],
                        capture_output=True,
                        timeout=300,
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO
                    )
                    
                    shutil.rmtree(windows_old, ignore_errors=True)
                    
                    if not windows_old.exists():
                        self.log_signal.emit(f"    ✅ Windows.old supprimé ({size_gb:.2f} Go libérés)")
                        self.results['windows_old'] = {'files': files, 'size': size}
                    else:
                        self.log_signal.emit(f"    ⚠️ Suppression partielle (redémarrage peut être nécessaire)")
                        self.results['windows_old'] = {'files': 0, 'size': 0}
                
                except Exception as e:
                    self.log_signal.emit(f"    ❌ Erreur: {str(e)}")
                    self.results['windows_old'] = {'files': 0, 'size': 0}
            else:
                self.results['windows_old'] = {'files': files, 'size': size}
            
            self.category_signal.emit("Windows.old", files, int(size / (1024**2)))
        
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
            self.results['windows_old'] = {'files': 0, 'size': 0}
            self.category_signal.emit("Windows.old", 0, 0)
    
    def handle_winsxs(self):
        """Nettoyer WinSxS"""
        self.log_signal.emit("\n📦 WINSXS CLEANUP")
        self.log_signal.emit("─" * 70)
        
        winsxs = Path("C:\\Windows\\WinSxS")
        
        if not winsxs.exists():
            self.log_signal.emit("  ○ WinSxS non trouvé (normal si Windows récent)")
            self.results['winsxs'] = {'files': 0, 'size': 0}
            self.category_signal.emit("WinSxS", 0, 0)
            return
        
        try:
            # Analyser taille WinSxS
            result = subprocess.run(
                ["Dism.exe", "/Online", "/Cleanup-Image", "/AnalyzeComponentStore"],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUPINFO,
                encoding="utf-8",
                errors="replace"
            )
            
            # Extraire la taille récupérable
            reclaimable_size = 0
            for line in result.stdout.split('\n'):
                if "Taille de nettoyage recommandée" in line or "recommended" in line.lower():
                    try:
                        # Extraire le nombre
                        import re
                        match = re.search(r'(\d+[\.,]?\d*)\s*(Mo|Go|MB|GB)', line, re.IGNORECASE)
                        if match:
                            value = float(match.group(1).replace(',', '.'))
                            unit = match.group(2).upper()
                            if 'G' in unit:
                                reclaimable_size = int(value * 1024)  # Convertir en Mo
                            else:
                                reclaimable_size = int(value)
                    except:
                        pass
            
            if reclaimable_size > 0:
                self.log_signal.emit(f"  → Espace récupérable: {reclaimable_size} Mo")
                
                if self.mode == "clean":
                    self.log_signal.emit(f"    🧹 Nettoyage WinSxS en cours (5-15 minutes)...")
                    self.log_signal.emit(f"    ⏳ Ne pas fermer cette fenêtre...")
                    
                    clean_result = subprocess.run(
                        ["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup", "/ResetBase"],
                        capture_output=True,
                        text=True,
                        timeout=900,  # 15 minutes max
                        creationflags=CREATE_NO_WINDOW,
                        startupinfo=STARTUPINFO,
                        encoding="utf-8",
                        errors="replace"
                    )
                    
                    if clean_result.returncode == 0:
                        self.log_signal.emit(f"    ✅ WinSxS nettoyé ({reclaimable_size} Mo libérés)")
                        self.results['winsxs'] = {'files': 0, 'size': reclaimable_size * (1024**2)}
                    else:
                        self.log_signal.emit(f"    ❌ Échec nettoyage WinSxS")
                        self.results['winsxs'] = {'files': 0, 'size': 0}
                else:
                    self.results['winsxs'] = {'files': 0, 'size': reclaimable_size * (1024**2)}
                
                self.category_signal.emit("WinSxS", 0, reclaimable_size)
            else:
                self.log_signal.emit("  ○ Aucun nettoyage WinSxS recommandé")
                self.results['winsxs'] = {'files': 0, 'size': 0}
                self.category_signal.emit("WinSxS", 0, 0)
        
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
            self.results['winsxs'] = {'files': 0, 'size': 0}
            self.category_signal.emit("WinSxS", 0, 0)
    
    def handle_large_files(self):
        """Scanner fichiers volumineux (>500 MB)"""
        self.log_signal.emit("\n📊 FICHIERS VOLUMINEUX (> 500 MB)")
        self.log_signal.emit("─" * 70)
        
        large_files = []
        min_size = 500 * 1024 * 1024  # 500 MB
        
        # Chercher dans Downloads, Documents, Desktop
        search_paths = [
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Videos",
        ]
        
        self.log_signal.emit("  → Scan en cours (peut prendre quelques minutes)...")
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            try:
                for file in search_path.rglob("*"):
                    if file.is_file():
                        try:
                            size = file.stat().st_size
                            if size > min_size:
                                size_mb = size / (1024**2)
                                large_files.append((str(file), size, size_mb))
                        except:
                            pass
            except:
                pass
        
        # Trier par taille
        large_files.sort(key=lambda x: x[1], reverse=True)
        
        total_size = sum(f[1] for f in large_files)
        
        if large_files:
            self.log_signal.emit(f"  → {len(large_files)} fichiers volumineux trouvés\n")
            
            # Afficher top 10
            for i, (filepath, size, size_mb) in enumerate(large_files[:10], 1):
                filename = Path(filepath).name
                if len(filename) > 50:
                    filename = filename[:47] + "..."
                self.log_signal.emit(f"    {i}. {filename}")
                self.log_signal.emit(f"       Taille: {size_mb:.1f} Mo")
                self.log_signal.emit(f"       Chemin: {filepath}\n")
            
            if len(large_files) > 10:
                self.log_signal.emit(f"    ... et {len(large_files) - 10} autres fichiers")
            
            self.log_signal.emit(f"\n  💡 Total: {len(large_files)} fichiers = {total_size / (1024**3):.2f} Go")
            self.log_signal.emit(f"  ℹ️ Vérifiez manuellement si ces fichiers sont nécessaires")
        else:
            self.log_signal.emit("  ○ Aucun fichier > 500 MB trouvé")
        
        self.results['large_files'] = {'files': len(large_files), 'size': total_size, 'list': large_files[:20]}
        self.category_signal.emit("Fichiers volumineux", len(large_files), int(total_size / (1024**2)))
    
    def handle_duplicates(self):
        """Détecter fichiers en double"""
        self.log_signal.emit("\n🔍 DÉTECTION DOUBLONS")
        self.log_signal.emit("─" * 70)
        
        # Chercher dans Downloads uniquement (plus rapide)
        search_path = Path.home() / "Downloads"
        
        if not search_path.exists():
            self.log_signal.emit("  ○ Dossier Downloads non trouvé")
            self.results['duplicates'] = {'files': 0, 'size': 0}
            self.category_signal.emit("Doublons", 0, 0)
            return
        
        self.log_signal.emit("  → Scan Downloads en cours...")
        
        # Dict: hash -> [liste de fichiers]
        hashes = defaultdict(list)
        
        try:
            for file in search_path.rglob("*"):
                if file.is_file() and file.stat().st_size > 1024:  # Ignorer fichiers < 1 KB
                    try:
                        # Hash rapide basé sur taille + premiers/derniers bytes
                        size = file.stat().st_size
                        with open(file, 'rb') as f:
                            # Lire premiers 8KB
                            first_chunk = f.read(8192)
                            # Sauter au milieu
                            if size > 16384:
                                f.seek(size // 2)
                                middle_chunk = f.read(8192)
                            else:
                                middle_chunk = b''
                            # Lire derniers 8KB
                            if size > 8192:
                                f.seek(-8192, 2)
                                last_chunk = f.read()
                            else:
                                last_chunk = b''
                        
                        # Hash combiné
                        quick_hash = hashlib.md5(
                            str(size).encode() + first_chunk + middle_chunk + last_chunk
                        ).hexdigest()
                        
                        hashes[quick_hash].append((str(file), size))
                    except:
                        pass
        except:
            pass
        
        # Trouver doublons
        duplicates = []
        wasted_space = 0
        
        for file_hash, files in hashes.items():
            if len(files) > 1:
                # Garder le premier, les autres sont doublons
                size = files[0][1]
                wasted_space += size * (len(files) - 1)
                duplicates.append((files, size))
        
        if duplicates:
            self.log_signal.emit(f"  → {len(duplicates)} groupes de doublons trouvés\n")
            
            # Afficher top 5
            duplicates.sort(key=lambda x: x[1], reverse=True)
            for i, (files, size) in enumerate(duplicates[:5], 1):
                size_mb = size / (1024**2)
                self.log_signal.emit(f"    {i}. {len(files)} copies ({size_mb:.1f} Mo chacune):")
                for filepath, _ in files[:3]:
                    filename = Path(filepath).name
                    self.log_signal.emit(f"       • {filename}")
                if len(files) > 3:
                    self.log_signal.emit(f"       ... et {len(files) - 3} autres")
                self.log_signal.emit("")
            
            if len(duplicates) > 5:
                self.log_signal.emit(f"    ... et {len(duplicates) - 5} autres groupes")
            
            waste_mb = wasted_space / (1024**2)
            self.log_signal.emit(f"\n  💡 Espace gaspillé: {waste_mb:.1f} Mo")
            self.log_signal.emit(f"  ℹ️ Supprimez manuellement les copies inutiles")
        else:
            self.log_signal.emit("  ○ Aucun doublon trouvé dans Downloads")
        
        self.results['duplicates'] = {'files': len(duplicates), 'size': wasted_space, 'list': duplicates[:10]}
        self.category_signal.emit("Doublons", len(duplicates), int(wasted_space / (1024**2)))
    
    def handle_logs(self):
        """Nettoyer logs système anciens"""
        self.log_signal.emit("\n📝 LOGS SYSTÈME")
        self.log_signal.emit("─" * 70)
        
        log_paths = [
            Path("C:\\Windows\\Logs"),
            Path("C:\\Windows\\Temp"),
            Path("C:\\ProgramData\\Microsoft\\Windows\\WER"),  # Windows Error Reporting
        ]
        
        total_files = 0
        total_size = 0
        
        for log_path in log_paths:
            if not log_path.exists():
                continue
            
            try:
                files, size = self.count_items(log_path, extensions=['.log', '.dmp', '.etl'])
                
                if files > 0:
                    size_mb = size / (1024**2)
                    self.log_signal.emit(f"  → {log_path.name}: {files} fichiers ({size_mb:.1f} Mo)")
                    
                    if self.mode == "clean":
                        self.log_signal.emit(f"    🧹 Nettoyage en cours...")
                        deleted = self.delete_folder_contents(log_path, extensions=['.log', '.dmp', '.etl'])
                        if deleted:
                            self.log_signal.emit(f"    ✅ Logs nettoyés")
                            total_files += files
                            total_size += size
                    else:
                        total_files += files
                        total_size += size
            
            except Exception as e:
                self.log_signal.emit(f"  ❌ {log_path.name}: Erreur - {str(e)}")
        
        self.results['logs'] = {'files': total_files, 'size': total_size}
        self.category_signal.emit("Logs", total_files, int(total_size / (1024**2)))
    
    def handle_windows_store(self):
        """Nettoyer cache Windows Store"""
        self.log_signal.emit("\n🏪 WINDOWS STORE CACHE")
        self.log_signal.emit("─" * 70)
        
        store_cache = Path(os.environ.get('LOCALAPPDATA', '')) / 'Packages' / 'Microsoft.WindowsStore_8wekyb3d8bbwe' / 'LocalCache'
        
        if not store_cache.exists():
            self.log_signal.emit("  ○ Cache Windows Store non trouvé")
            self.results['windows_store'] = {'files': 0, 'size': 0}
            self.category_signal.emit("Windows Store", 0, 0)
            return
        
        try:
            files, size = self.count_items(store_cache)
            
            if files > 0:
                size_mb = size / (1024**2)
                self.log_signal.emit(f"  → Cache trouvé: {files} fichiers ({size_mb:.1f} Mo)")
                
                if self.mode == "clean":
                    self.log_signal.emit(f"    🧹 Nettoyage en cours...")
                    
                    # Utiliser WSReset.exe (commande officielle)
                    try:
                        subprocess.run(
                            ["WSReset.exe"],
                            timeout=30,
                            creationflags=CREATE_NO_WINDOW,
                            startupinfo=STARTUPINFO
                        )
                        self.log_signal.emit(f"    ✅ Cache Windows Store nettoyé")
                        self.results['windows_store'] = {'files': files, 'size': size}
                    except Exception as e:
                        self.log_signal.emit(f"    ⚠️ Erreur: {str(e)}")
                        self.results['windows_store'] = {'files': 0, 'size': 0}
                else:
                    self.results['windows_store'] = {'files': files, 'size': size}
                
                self.category_signal.emit("Windows Store", files, int(size / (1024**2)))
            else:
                self.log_signal.emit("  ○ Cache vide")
                self.results['windows_store'] = {'files': 0, 'size': 0}
                self.category_signal.emit("Windows Store", 0, 0)
        
        except Exception as e:
            self.log_signal.emit(f"  ❌ Erreur: {str(e)}")
            self.results['windows_store'] = {'files': 0, 'size': 0}
            self.category_signal.emit("Windows Store", 0, 0)
    
    def count_items(self, path, extensions=None):
        """Compter fichiers et taille totale"""
        total_files = 0
        total_size = 0
        
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    # Filtrer par extension si spécifié
                    if extensions:
                        if item.suffix.lower() not in extensions:
                            continue
                    
                    try:
                        total_size += item.stat().st_size
                        total_files += 1
                    except:
                        pass
        except:
            pass
        
        return total_files, total_size
    
    def delete_folder_contents(self, folder, extensions=None):
        """Supprimer contenu d'un dossier"""
        try:
            for item in folder.iterdir():
                try:
                    if item.is_file():
                        # Filtrer par extension si spécifié
                        if extensions and item.suffix.lower() not in extensions:
                            continue
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                except:
                    pass
            return True
        except:
            return False


class DiskCleanupAdvancedWindow(QDialog):
    """Fenêtre Disk Cleanup Advanced"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🧹 Nettoyage Disque Avancé")
        self.setMinimumSize(1000, 800)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🧹 NETTOYAGE DISQUE AVANCÉ")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        help_btn = QPushButton("❓ Aide")
        help_btn.clicked.connect(self.show_help)
        help_btn.setFixedWidth(100)
        header_layout.addWidget(help_btn)
        
        layout.addLayout(header_layout)
        
        # Info
        info = QLabel("Sélectionnez les catégories à analyser/nettoyer")
        info.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(info)
        
        # Scroll area pour checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Checkboxes par catégorie
        self.checkboxes = {}
        
        categories = [
            ("browsers", "🌐 Navigateurs (Chrome, Edge, Firefox, Brave)", "Cache navigateurs web"),
            ("gaming", "🎮 Gaming (Steam, Epic, NVIDIA, AMD)", "Shader cache et fichiers temporaires"),
            ("windows_old", "🪟 Windows.old", "Ancienne installation Windows (peut être volumineux)"),
            ("winsxs", "📦 WinSxS Cleanup", "Nettoyage composants Windows (long)"),
            ("large_files", "📊 Fichiers volumineux (> 500 MB)", "Scan seulement, pas de suppression auto"),
            ("duplicates", "🔍 Doublons (Downloads)", "Détection fichiers en double"),
            ("logs", "📝 Logs système", "Fichiers .log, .dmp anciens"),
            ("windows_store", "🏪 Windows Store Cache", "Cache Microsoft Store"),
        ]
        
        for key, name, desc in categories:
            cb = QCheckBox(name)
            cb.setToolTip(desc)
            cb.setChecked(False)  # Décochées par défaut
            self.checkboxes[key] = cb
            scroll_layout.addWidget(cb)
        
        # Bouton "Tout sélectionner"
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("☑️ Tout sélectionner")
        select_all_btn.clicked.connect(self.select_all)
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ Tout désélectionner")
        deselect_all_btn.clicked.connect(self.deselect_all)
        select_layout.addWidget(deselect_all_btn)
        
        scroll_layout.addLayout(select_layout)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Boutons action
        btn_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 ANALYSER")
        self.analyze_btn.clicked.connect(lambda: self.start_operation("analyze"))
        self.analyze_btn.setStyleSheet("background: #2196F3;")
        btn_layout.addWidget(self.analyze_btn)
        
        self.clean_btn = QPushButton("🧹 NETTOYER")
        self.clean_btn.clicked.connect(lambda: self.start_operation("clean"))
        self.clean_btn.setStyleSheet("background: #4CAF50;")
        btn_layout.addWidget(self.clean_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Résultats
        results_label = QLabel("📄 RÉSULTATS")
        results_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(results_label)
        
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setFont(QFont("Consolas", 9))
        layout.addWidget(self.results)
        
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
            QTextEdit {
                background: #0d1117;
                color: #58a6ff;
                border: 2px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QScrollArea {
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.show_welcome()
        self.worker = None
    
    def show_welcome(self):
        """Message d'accueil"""
        text = """╔══════════════════════════════════════════════════════════════╗
║         🧹 NETTOYAGE DISQUE AVANCÉ - WAPINATOR              ║
╚══════════════════════════════════════════════════════════════╝

🎯 FONCTIONNALITÉS

MODE ANALYSE:
- Scan et estimation espace libérable
- Aucune suppression
- Rapport détaillé

MODE NETTOYAGE:
- Suppression effective des fichiers
- Logs détaillés
- Statistiques finales

═══════════════════════════════════════════════════════════════

📁 CATÉGORIES DISPONIBLES

🌐 NAVIGATEURS
- Cache Chrome, Edge, Firefox, Brave
- Peut libérer : 100 Mo - 2 Go

🎮 GAMING
- Shader cache (Steam, Epic, NVIDIA, AMD)
- Peut libérer : 500 Mo - 5 Go

🪟 WINDOWS.OLD
- Ancienne installation Windows
- Peut libérer : 10-30 Go (!!)

📦 WINSXS
- Composants Windows obsolètes
- Peut libérer : 1-5 Go
- ⚠️ Opération longue (5-15 min)

📊 FICHIERS VOLUMINEUX
- Scan fichiers > 500 MB
- Pas de suppression auto
- Vérification manuelle recommandée

🔍 DOUBLONS
- Détecte copies identiques
- Scan Downloads uniquement
- Suppression manuelle

📝 LOGS SYSTÈME
- Fichiers .log, .dmp anciens
- Peut libérer : 100 Mo - 1 Go

🏪 WINDOWS STORE
- Cache Microsoft Store
- Peut libérer : 50-500 Mo

═══════════════════════════════════════════════════════════════

💡 CONSEILS

1. Commencer par ANALYSE pour estimer
2. Fermer navigateurs/jeux avant nettoyage
3. Windows.old = gain maximal
4. WinSxS = long mais efficace
5. Toujours garder sauvegardes importantes

═══════════════════════════════════════════════════════════════

🚀 DÉMARRAGE

1. Cocher catégories souhaitées
2. Cliquer "ANALYSER" pour estimation
3. Si OK, cliquer "NETTOYER"
4. Attendre fin (ne pas fermer)

═══════════════════════════════════════════════════════════════
"""
        self.results.setPlainText(text)
    
    def select_all(self):
        """Sélectionner tout"""
        for cb in self.checkboxes.values():
            cb.setChecked(True)
    
    def deselect_all(self):
        """Désélectionner tout"""
        for cb in self.checkboxes.values():
            cb.setChecked(False)
    
    def start_operation(self, mode):
        """Démarrer analyse ou nettoyage"""
        selected = [key for key, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not selected:
            QMessageBox.warning(self, "⚠️", "Veuillez cocher au moins une catégorie !")
            return
        
        # Confirmation pour nettoyage
        if mode == "clean":
            # Vérifier admin
            import ctypes
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            except:
                is_admin = False
            
            if not is_admin:
                QMessageBox.warning(
                    self,
                    "⚠️ Admin requis",
                    "Le nettoyage nécessite les droits administrateur.\n\n"
                    "Relancez Wapinator en tant qu'administrateur."
                )
                return
            
            categories_text = "\n".join([f"• {self.checkboxes[k].text()}" for k in selected])
            
            reply = QMessageBox.question(
                self,
                "🧹 Confirmation",
                f"Nettoyer les catégories suivantes ?\n\n{categories_text}\n\n"
                "⚠️ Cette action supprimera des fichiers.\n"
                "Fermez navigateurs et jeux avant de continuer.\n\n"
                "Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Désactiver boutons
        self.analyze_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.results.clear()
        
        # Lancer worker
        self.worker = DiskCleanupWorker(selected, mode)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.category_signal.connect(self.show_category_result)
        self.worker.finished_signal.connect(lambda r: self.on_operation_finished(r, mode))
        self.worker.start()
    
    def append_log(self, text):
        """Ajouter au log"""
        self.results.append(text)
    
    def show_category_result(self, category, files, size_mb):
        """Afficher résultat d'une catégorie (inutilisé pour l'instant)"""
        pass
    
    def on_operation_finished(self, results, mode):
        """Opération terminée"""
        self.analyze_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if 'error' in results:
            self.append_log(f"\n❌ Erreur: {results['error']}")
            return
        
        # Calculer totaux
        total_files = 0
        total_size = 0
        
        for category, data in results.items():
            if isinstance(data, dict):
                total_files += data.get('files', 0)
                total_size += data.get('size', 0)
        
        # Résumé
        self.append_log("\n" + "╔" + "═"*70 + "╗")
        self.append_log("║" + " "*25 + "📊 RÉSUMÉ" + " "*33 + "║")
        self.append_log("╚" + "═"*70 + "╝\n")
        
        size_mb = total_size / (1024**2)
        size_gb = total_size / (1024**3)
        
        if mode == "analyze":
            self.append_log(f"📂 Fichiers analysés: {total_files}")
            self.append_log(f"💾 Espace libérable: {size_mb:.1f} Mo ({size_gb:.2f} Go)")
            self.append_log("\n💡 Cliquez 'NETTOYER' pour libérer cet espace")
        else:
            self.append_log(f"🗑️ Fichiers supprimés: {total_files}")
            self.append_log(f"✅ Espace libéré: {size_mb:.1f} Mo ({size_gb:.2f} Go)")
            self.append_log("\n🎉 Nettoyage terminé avec succès !")
        
        self.append_log("")
        
        QMessageBox.information(
            self,
            "✅ Terminé",
            f"{'Analyse' if mode == 'analyze' else 'Nettoyage'} terminé !\n\n"
            f"Fichiers: {total_files}\n"
            f"Taille: {size_gb:.2f} Go"
        )
    
    def show_help(self):
        """Aide"""
        help_text = """╔══════════════════════════════════════════════════════════════╗
║                   ❓ AIDE - NETTOYAGE AVANCÉ                ║
╚══════════════════════════════════════════════════════════════╝

🎯 CATÉGORIES EXPLIQUÉES

NAVIGATEURS:
- Cache = fichiers temporaires web
- Sûr à supprimer (se recréent)
- Gain typique: 100 Mo - 2 Go

GAMING:
- Shader cache = fichiers optimisation
- Sûr mais recréation lors prochain jeu
- Gain typique: 500 Mo - 5 Go

WINDOWS.OLD:
- Ancienne version Windows
- GROS gain (10-30 Go)
- Supprimable si Windows fonctionne bien

WINSXS:
- Composants Windows obsolètes
- Opération LONGUE (5-15 min)
- Gain moyen: 1-5 Go

FICHIERS VOLUMINEUX:
- Détection seulement
- Vérification manuelle recommandée
- Souvent vidéos, ISOs, etc.

DOUBLONS:
- Copies identiques
- Suppression MANUELLE requise
- Gain variable

LOGS SYSTÈME:
- Fichiers diagnostic anciens
- Sûr à supprimer
- Gain: 100 Mo - 1 Go

WINDOWS STORE:
- Cache apps Microsoft Store
- Sûr à vider
- Gain: 50-500 Mo

═══════════════════════════════════════════════════════════════

⚠️ PRÉCAUTIONS

1. TOUJOURS analyser avant nettoyer
2. Fermer navigateurs/jeux pendant nettoyage
3. Sauvegardes importantes avant Windows.old
4. WinSxS = créer point restauration avant

═══════════════════════════════════════════════════════════════
"""
        QMessageBox.information(self, "❓ Aide", help_text)


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = DiskCleanupAdvancedWindow(None)
    window.show()
    sys.exit(app.exec())
