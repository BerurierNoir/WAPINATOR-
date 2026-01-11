# prompt_templates.py
# Templates de prompts optimisés pour chaque IA avec raisonnement approfondi

def build_claude_prompt_v2(symptoms, context, system_info):
    """
    Prompt optimisé pour Claude (Anthropic)
    - En français (langue native de Claude)
    - Demande explicite de raisonnement approfondi
    - Ton pédagogique pour débutants
    - Safety disclaimer
    """
    
    prompt = """Tu es un expert en diagnostic PC Windows avec 20 ans d'expérience en support technique, réparation hardware et optimisation système.

⚠️ INSTRUCTIONS IMPORTANTES AVANT DE RÉPONDRE :

1. **RÉFLEXION APPROFONDIE REQUISE** 
   - Prends le temps d'analyser TOUTES les informations fournies
   - Raisonne étape par étape (step-by-step thinking)
   - Considère TOUTES les causes possibles avant de conclure
   - Pèse les probabilités de chaque hypothèse
   - NE te précipite PAS sur une réponse rapide

2. **TON PÉDAGOGIQUE OBLIGATOIRE**
   - Explique comme si tu parlais à un DÉBUTANT
   - Définis TOUS les termes techniques
   - Fournis des tutoriels PAS-À-PAS ultra-détaillés
   - Utilise des analogies simples si nécessaire
   - Vérifie que chaque étape soit CLAIRE

3. **TUTORIELS ACTUALISÉS**
   - Fournis des instructions pour Windows 11/10 ACTUELS (2024-2025)
   - Mentionne les chemins d'accès EXACTS dans Windows
   - Donne les raccourcis clavier quand c'est pertinent
   - Ajoute des captures d'écran textuelles si utile

4. **SÉCURITÉ AVANT TOUT**
   - Insiste sur les BACKUPS avant toute manipulation
   - Avertis des RISQUES potentiels
   - Propose toujours la solution la PLUS SÛRE d'abord
   - Mentionne quand faire appel à un professionnel

Je rencontre des problèmes avec mon PC et j'ai besoin d'un diagnostic précis et de solutions concrètes.

═══════════════════════════════════════════════════════════
📊 INFORMATIONS SYSTÈME COMPLÈTES
═══════════════════════════════════════════════════════════

"""
    
    # Ajouter sections hardware/software/etc.
    prompt += format_system_info_section(system_info)
    
    # Ajouter symptômes
    prompt += f"""
═══════════════════════════════════════════════════════════
🔴 SYMPTÔMES RAPPORTÉS PAR L'UTILISATEUR
═══════════════════════════════════════════════════════════

**Problèmes rencontrés :**
"""
    for symptom in symptoms:
        prompt += f"- ✅ {symptom}\n"
    
    # Ajouter contexte
    prompt += f"""

**Contexte temporel :**
- Début des problèmes : {context['when']}
- Fréquence : {context['frequency']}
- Évolution : {"En aggravation" if context['frequency'] in ["Constamment", "Plusieurs fois par jour"] else "Stable"}

**Modifications récentes du système :**
- {context['modifications']}

**Utilisation principale du PC :**
- {context['usage']}
"""
    
    if context.get('notes'):
        prompt += f"""
**Notes additionnelles de l'utilisateur :**
{context['notes']}
"""
    
    # Demandes finales avec raisonnement
    prompt += """

═══════════════════════════════════════════════════════════
❓ CE QUE JE DEMANDE - RAISONNEMENT APPROFONDI REQUIS
═══════════════════════════════════════════════════════════

⚠️ **IMPORTANT : Prends le temps de bien réfléchir. Ne te précipite PAS.**

Fournis-moi une analyse COMPLÈTE et DÉTAILLÉE en suivant cette structure :

---

## 🧠 1. ANALYSE PRÉLIMINAIRE (Raisonnement étape par étape)

**Avant de diagnostiquer, explique ta réflexion :**

a) Quels sont les symptômes CLÉS que tu identifies ?
b) Quelles corrélations vois-tu entre les symptômes ?
c) Quelles informations système sont les PLUS pertinentes ?
d) Y a-t-il des "red flags" ou signaux d'alerte ?

*→ Raisonne à voix haute, montre ton cheminement de pensée*

---

## 🎯 2. DIAGNOSTIC DÉTAILLÉ (3 hypothèses classées)

Pour CHAQUE hypothèse, fournis :

### **Hypothèse 1 : [NOM DU PROBLÈME]** (Probabilité : XX%)

**Pourquoi cette hypothèse ?**
- Argument 1 (basé sur quelles infos ?)
- Argument 2
- Argument 3

**Éléments qui CONFIRMENT :**
- Point 1
- Point 2

**Éléments qui INFIRMENT :**
- Point 1 (si applicable)

**Gravité :** [Faible / Moyenne / Élevée / CRITIQUE]

---

*[Répéter pour Hypothèses 2 et 3]*

---

## 🔬 3. TESTS DE CONFIRMATION (Pas-à-pas DÉTAILLÉS)

Pour chaque hypothèse, fournis des tests de confirmation :

### Test pour Hypothèse 1 : [Nom du test]

**Objectif du test :** [Ce qu'on cherche à vérifier]

**Étapes EXACTES :**

**Étape 1 :** [Action précise]
- Appuie sur `Win + X`
- Clique sur "[Nom exact du menu]"
- [Capture d'écran textuelle si besoin]

**Étape 2 :** [...]

**Résultat attendu SI hypothèse correcte :**
- [Description précise]

**Résultat attendu SI hypothèse incorrecte :**
- [Description précise]

**⚠️ Précautions :**
- [Warnings éventuels]

---

## 🛠️ 4. SOLUTIONS (Du plus simple au plus complexe)

**⚠️ DISCLAIMER IMPORTANT :**
> Avant TOUTE manipulation :
> - Crée un point de restauration système
> - Sauvegarde tes données importantes
> - Si tu as le MOINDRE doute, demande de l'aide !

---

### 🟢 Solution 1 : [NOM SIMPLE] (Difficulté : Débutant)

**Ce que ça fait :** [Explication simple]

**Pourquoi ça peut marcher :** [Raison]

**Tutoriel PAS-À-PAS :**

**Étape 1 : [Titre étape]**
```
1. Appuie sur Win + I (Paramètres Windows)
2. Clique sur "Système" dans le menu de gauche
3. Descends jusqu'à "Récupération"
4. Clique sur "Créer un point de restauration"
[etc...]
```

**Temps estimé :** [X minutes]

**Risques :** [Aucun / Faibles / Moyens]

**Chance de succès :** [XX%]

---

### 🟡 Solution 2 : [NOM INTERMÉDIAIRE] (Difficulté : Intermédiaire)

[Même structure détaillée]

---

### 🔴 Solution 3 : [NOM AVANCÉ] (Difficulté : Avancé)

⚠️ **ATTENTION : Solution technique, faire appel à un ami/pro si pas sûr**

[Tutoriel ultra-détaillé]

---

## 🛡️ 5. PRÉVENTION FUTURE

**Comment éviter que ça se reproduise :**

1. **Maintenance préventive :**
   - [Action 1] → Fréquence recommandée
   - [Action 2] → Fréquence recommandée

2. **Bonnes pratiques :**
   - [Pratique 1]
   - [Pratique 2]

3. **Monitoring à mettre en place :**
   - [Outil 1] pour surveiller [métrique]
   - [Outil 2] pour surveiller [métrique]

---

## ⚠️ 6. NIVEAU D'URGENCE & RECOMMANDATIONS

**Gravité globale :** [🟢 Faible / 🟡 Moyenne / 🟠 Élevée / 🔴 CRITIQUE]

**Puis-je continuer à utiliser le PC ?**
- [OUI / NON / AVEC PRÉCAUTIONS]

**Si OUI avec précautions :**
- Évite : [Action à éviter]
- Limite : [Usage à limiter]

**Si NON :**
- Pourquoi c'est dangereux : [Explication]
- Que faire immédiatement : [Actions]

**Dois-je faire appel à un professionnel ?**
- [OUI / NON / SI les solutions simples échouent]

**Si OUI, pourquoi :**
- [Raison 1]
- [Raison 2]

---

## 💡 7. EXPLICATIONS POUR COMPRENDRE (Bonus pédagogique)

**Pour que tu COMPRENNES vraiment le problème :**

**Qu'est-ce qui s'est passé techniquement ?**
[Explication vulgarisée avec analogie simple]

**Pourquoi ça arrive ?**
[Causes racines expliquées simplement]

**Analogie du quotidien :**
> "C'est comme [analogie simple] : [explication]"

---

═══════════════════════════════════════════════════════════
⚠️ DISCLAIMER FINAL OBLIGATOIRE
═══════════════════════════════════════════════════════════

**AVERTISSEMENT IMPORTANT :**

✋ Je suis une IA et je peux faire des erreurs. 

**Avant d'appliquer MES solutions :**
1. ❌ NE les suis PAS aveuglément
2. ✅ Relis PLUSIEURS FOIS les instructions
3. ✅ Fais des recherches complémentaires si besoin
4. ✅ Crée TOUJOURS un backup/point de restauration
5. ✅ En cas de DOUTE : demande à un ami compétent ou un professionnel

**Si quelque chose ne va pas :**
- Arrête immédiatement
- Restaure le point de restauration
- Contacte un professionnel

**Je ne suis PAS responsable des dégâts potentiels.**

═══════════════════════════════════════════════════════════

💬 **Maintenant, fournis-moi ton analyse COMPLÈTE en suivant EXACTEMENT la structure ci-dessus.**

Prends ton temps, réfléchis profondément, et sois ULTRA-PÉDAGOGIQUE.

Merci ! 🙏
"""
    
    return prompt


def build_chatgpt_prompt_v2(symptoms, context, system_info):
    """
    Prompt optimisé pour ChatGPT (OpenAI)
    - En anglais (meilleure performance GPT-4)
    - Mais demande réponse EN FRANÇAIS
    - Techniques CoT (Chain of Thought)
    """
    
    prompt = """You are a world-class PC diagnostic expert with 20 years of experience in Windows troubleshooting, hardware repair, and system optimization.

⚠️ CRITICAL INSTRUCTIONS BEFORE RESPONDING:

1. **DEEP REASONING REQUIRED**
   - Take time to analyze ALL provided information
   - Use step-by-step reasoning (Chain of Thought)
   - Consider ALL possible causes before concluding
   - Weigh probabilities carefully
   - DO NOT rush to a quick answer

2. **PEDAGOGICAL TONE MANDATORY**
   - Explain as if talking to a BEGINNER
   - Define ALL technical terms
   - Provide ULTRA-DETAILED step-by-step tutorials
   - Use simple analogies when helpful
   - Ensure each step is CRYSTAL CLEAR

3. **UP-TO-DATE TUTORIALS**
   - Provide instructions for CURRENT Windows 11/10 (2024-2025)
   - Mention EXACT paths in Windows
   - Include keyboard shortcuts when relevant

4. **SAFETY FIRST**
   - Emphasize BACKUPS before any manipulation
   - Warn about potential RISKS
   - Always suggest the SAFEST solution first
   - Mention when to call a professional

5. **RESPONSE LANGUAGE**
   - ⚠️ RESPOND ENTIRELY IN FRENCH despite this English prompt
   - French is required for user accessibility
   - Translate all technical terms to French

═══════════════════════════════════════════════════════════
📊 COMPLETE SYSTEM INFORMATION
═══════════════════════════════════════════════════════════

"""
    
    # Add system info
    prompt += format_system_info_section(system_info)
    
    # Add symptoms
    prompt += f"""
═══════════════════════════════════════════════════════════
🔴 REPORTED SYMPTOMS
═══════════════════════════════════════════════════════════

**Issues encountered:**
"""
    for symptom in symptoms:
        prompt += f"- ✅ {symptom}\n"
    
    # Add context
    prompt += f"""

**Timeline:**
- Problem started: {context['when']}
- Frequency: {context['frequency']}

**Recent changes:**
- {context['modifications']}

**Main PC usage:**
- {context['usage']}
"""
    
    if context.get('notes'):
        prompt += f"""
**Additional user notes:**
{context['notes']}
"""
    
    # Final requests with reasoning (in English but asking for French response)
    prompt += """

═══════════════════════════════════════════════════════════
❓ WHAT I'M ASKING - DEEP REASONING REQUIRED
═══════════════════════════════════════════════════════════

⚠️ **IMPORTANT: Take your time. DO NOT rush.**

⚠️ **RESPOND ENTIRELY IN FRENCH (despite this English prompt)**

Provide me with a COMPLETE and DETAILED analysis following this exact structure:

---

## 🧠 1. PRELIMINARY ANALYSIS (Step-by-step reasoning)

**Before diagnosing, explain your thinking process:**

a) What are the KEY symptoms you identify?
b) What correlations do you see between symptoms?
c) Which system information is MOST relevant?
d) Are there any red flags?

*→ Think out loud, show your reasoning process*

---

## 🎯 2. DETAILED DIAGNOSIS (3 ranked hypotheses)

For EACH hypothesis, provide:

### **Hypothesis 1: [PROBLEM NAME]** (Probability: XX%)

**Why this hypothesis?**
- Argument 1 (based on which info?)
- Argument 2
- Argument 3

**Elements that CONFIRM:**
- Point 1
- Point 2

**Elements that DISPROVE:**
- Point 1 (if applicable)

**Severity:** [Low / Medium / High / CRITICAL]

---

*[Repeat for Hypotheses 2 and 3]*

---

## 🔬 3. CONFIRMATION TESTS (Detailed step-by-step)

[Similar detailed structure as Claude prompt]

---

## 🛠️ 4. SOLUTIONS (From simplest to most complex)

**⚠️ IMPORTANT DISCLAIMER:**
> Before ANY manipulation:
> - Create a system restore point
> - Backup important data
> - If you have ANY doubt, ask for help!

### 🟢 Solution 1: [SIMPLE NAME] (Difficulty: Beginner)

[Ultra-detailed tutorial with exact steps]

---

[Continue with same detailed structure as Claude prompt]

---

## ⚠️ FINAL MANDATORY DISCLAIMER

**IMPORTANT WARNING:**

✋ I'm an AI and I can make mistakes.

**Before applying MY solutions:**
1. ❌ DO NOT follow them blindly
2. ✅ Reread instructions MULTIPLE TIMES
3. ✅ Do additional research if needed
4. ✅ ALWAYS create a backup/restore point
5. ✅ If in DOUBT: ask a competent friend or professional

**If something goes wrong:**
- Stop immediately
- Restore the restore point
- Contact a professional

**I am NOT responsible for potential damages.**

═══════════════════════════════════════════════════════════

💬 **Now provide your COMPLETE analysis following EXACTLY the structure above.**

**⚠️ REMEMBER: RESPOND ENTIRELY IN FRENCH**

Take your time, think deeply, and be ULTRA-PEDAGOGICAL.

Thank you! 🙏
"""
    
    return prompt


def build_gemini_prompt_v2(symptoms, context, system_info):
    """
    Prompt optimisé pour Gemini (Google)
    - En français
    - Format similaire à Claude mais adapté
    """
    # Structure similaire à Claude mais légèrement adaptée pour Gemini
    return build_claude_prompt_v2(symptoms, context, system_info)


def build_generic_prompt_v2(symptoms, context, system_info):
    """
    Prompt générique compatible toutes IA
    - En français
    - Format universel
    """
    return build_claude_prompt_v2(symptoms, context, system_info)


def format_system_info_section(system_info):
    """Formate la section informations système de manière détaillée"""
    
    section = ""
    
    # Hardware
    if system_info.get('hardware'):
        hw = system_info['hardware']
        section += """
## 🖥️ CONFIGURATION MATÉRIELLE

"""
        
        # CPU
        if 'cpu' in hw:
            cpu = hw['cpu']
            section += f"""**💻 Processeur (CPU)**
- Modèle : {cpu.get('model', 'Unknown')}
- Cœurs physiques : {cpu.get('cores_physical', '?')}
- Cœurs logiques (threads) : {cpu.get('cores_logical', '?')}
- Fréquence maximale : {cpu.get('frequency', '?')} MHz
- Fréquence actuelle : {cpu.get('current_freq', '?')} MHz

"""
        
        # RAM
        if 'ram' in hw:
            ram = hw['ram']
            section += f"""**💾 Mémoire RAM**
- Quantité totale : {ram.get('total_gb', '?')} GB
- Type : {ram.get('type', 'Unknown')}
- Vitesse : {ram.get('speed', 'Unknown')}

"""
        
        # GPU
        if 'gpu' in hw:
            gpu = hw['gpu']
            section += f"""**🎮 Carte Graphique (GPU)**
- Modèle : {gpu.get('model', 'Unknown')}
- VRAM : {gpu.get('vram_gb', '?')} GB
- Driver version : {gpu.get('driver', 'Unknown')}
- Date du driver : {gpu.get('driver_date', 'Unknown')}

"""
        
        # Storage
        if 'storage' in hw and hw['storage']:
            section += "**💿 Stockage (Disques)**\n"
            for disk in hw['storage']:
                health_status = "✅ Bon" if disk['percent'] < 80 else "⚠️ Plein" if disk['percent'] < 95 else "🔴 CRITIQUE"
                section += f"""- {disk['device']} : {disk['total_gb']} GB ({disk['fstype']})
  • Utilisé : {disk['used_gb']} GB ({disk['percent']}%)
  • Libre : {disk['free_gb']} GB
  • État : {health_status}
"""
            section += "\n"
        
        # Motherboard
        if 'motherboard' in hw:
            mb = hw['motherboard']
            section += f"""**🔌 Carte Mère**
- Fabricant : {mb.get('manufacturer', 'Unknown')}
- Modèle : {mb.get('model', 'Unknown')}

"""
    
    # Software
    if system_info.get('software'):
        sw = system_info['software']
        section += """
## 💻 CONFIGURATION LOGICIELLE

"""
        
        # OS
        if 'os' in sw:
            os_info = sw['os']
            section += f"""**🪟 Système d'Exploitation**
- OS : {os_info.get('name', 'Unknown')} {os_info.get('release', '')}
- Version : {os_info.get('version', 'Unknown')}
- Build : {os_info.get('build', 'Unknown')}
- Architecture : {os_info.get('architecture', 'Unknown')}

"""
        
        # BIOS
        if 'bios' in sw:
            bios = sw['bios']
            section += f"""**⚙️ BIOS/UEFI**
- Fabricant : {bios.get('manufacturer', 'Unknown')}
- Version : {bios.get('version', 'Unknown')}
- Date : {bios.get('date', 'Unknown')}

"""
        
        # Windows Updates - Historique complet
        if 'last_update' in sw:
            section += "**🔄 Historique Mises à Jour Windows (10 dernières)**\n"
            updates = sw['last_update']
            if isinstance(updates, list):
                for i, update in enumerate(updates[:10], 1):
                    section += f"{i}. {update}\n"
            else:
                section += f"- {updates}\n"
            section += "\n"
    
    # Current State
    if system_info.get('current_state'):
        state = system_info['current_state']
        section += """
## 📊 ÉTAT ACTUEL DU SYSTÈME (Au moment du scan)

"""
        
        # Usage
        if 'usage' in state:
            usage = state['usage']
            cpu_status = "✅ Normal" if usage.get('cpu_percent', 0) < 70 else "⚠️ Élevé" if usage.get('cpu_percent', 0) < 90 else "🔴 CRITIQUE"
            ram_status = "✅ Normal" if usage.get('ram_percent', 0) < 70 else "⚠️ Élevé" if usage.get('ram_percent', 0) < 90 else "🔴 CRITIQUE"
            
            section += f"""**Utilisation Ressources**
- CPU : {usage.get('cpu_percent', '?')}% {cpu_status}
- RAM : {usage.get('ram_used_gb', '?')} GB / {usage.get('ram_total_gb', '?')} GB ({usage.get('ram_percent', '?')}%) {ram_status}

"""
        
        # Temperatures (if available)
        if 'temperatures' in state and state['temperatures'] and 'note' not in state['temperatures']:
            section += "**🌡️ Températures**\n"
            for sensor, readings in state['temperatures'].items():
                section += f"- {sensor}:\n"
                for reading in readings:
                    temp = reading['temp']
                    temp_status = "✅" if temp < 70 else "⚠️" if temp < 85 else "🔴"
                    section += f"  • {reading['label']}: {temp}°C {temp_status}\n"
            section += "\n"
        
        # Top processes
        if 'top_processes' in state and state['top_processes']:
            section += "**🔝 Processus les Plus Gourmands (Top 5 par RAM)**\n"
            for i, proc in enumerate(state['top_processes'][:5], 1):
                section += f"{i}. {proc['name']} - {proc['memory_mb']} MB\n"
            section += "\n"
        
        # Uptime
        if 'uptime' in state:
            section += f"**⏱️ Uptime Système** : {state['uptime']}\n\n"
    
    # Logs & Errors
    if system_info.get('logs'):
        logs = system_info['logs']
        section += """
## 📝 LOGS & ERREURS SYSTÈME

"""
        
        # Event Viewer
        if 'event_viewer' in logs:
            ev = logs['event_viewer']
            count = ev.get('count', 'N/A')
            status = "✅ Peu d'erreurs" if isinstance(count, int) and count < 10 else "⚠️ Erreurs fréquentes" if isinstance(count, int) and count < 50 else "🔴 Nombreuses erreurs"
            section += f"""**Event Viewer (7 derniers jours)**
- Nombre d'erreurs critiques détectées : {count} {status}

"""
        
        # BSOD dumps
        if 'bsod' in logs:
            bsod = logs['bsod']
            if bsod.get('recent_dumps'):
                section += "**💙 Écrans Bleus (BSOD) Récents**\n"
                for i, dump in enumerate(bsod['recent_dumps'][:5], 1):
                    section += f"{i}. {dump['filename']} - Date : {dump['date']}\n"
                section += f"\n📁 Emplacement des dumps : `{bsod.get('location', 'Unknown')}`\n\n"
            else:
                section += "**💙 Écrans Bleus (BSOD)** : ✅ Aucun dump récent trouvé\n\n"
        
        # Windows Update errors
        if 'windows_update' in logs:
            wu_status = logs['windows_update']
            wu_icon = "✅" if "Aucune erreur" in wu_status else "⚠️"
            section += f"**Windows Update** : {wu_icon} {wu_status}\n\n"
    
    # Tests performed
    if system_info.get('tests'):
        tests = system_info['tests']
        section += """
## 🔧 TESTS & DIAGNOSTICS DÉJÀ EFFECTUÉS

"""
        
        for test_name, test_result in tests.items():
            test_icon = "✅" if "Dernier scan" in test_result else "❌" if "Non" in test_result else "⚠️"
            section += f"**{test_name.upper()}** : {test_icon} {test_result}\n"
        
        section += "\n"
    
    return section


# Disclaimer à afficher dans l'interface AVANT de copier le prompt
DISCLAIMER_UI = """
⚠️ ═══════════════════════════════════════════════════════════ ⚠️
                    AVERTISSEMENT IMPORTANT
⚠️ ═══════════════════════════════════════════════════════════ ⚠️

Ce prompt va générer un diagnostic via Intelligence Artificielle.

RÈGLES ESSENTIELLES :

✋ NE SUIVEZ PAS LES SOLUTIONS AVEUGLÉMENT
   → Les IA peuvent faire des erreurs
   → Lisez ATTENTIVEMENT chaque étape
   → Comprenez ce que vous faites AVANT de le faire

🛡️ TOUJOURS CRÉER UN BACKUP
   → Point de restauration système OBLIGATOIRE
   → Sauvegarde de vos données importantes
   → Test sur une VM si possible

🤝 EN CAS DE DOUTE → DEMANDEZ DE L'AIDE
   → Ami compétent en informatique
   → Professionnel (technicien, magasin)
   → Forum spécialisé (avec précautions)

🔴 SI QUELQUE CHOSE NE VA PAS
   → Arrêtez IMMÉDIATEMENT
   → Restaurez le point de restauration
   → Ne continuez PAS si vous ne comprenez pas

💡 L'IA EST UN OUTIL D'AIDE, PAS UN REMPLACEMENT
   → Elle analyse des données
   → Elle propose des pistes
   → VOUS décidez et prenez la responsabilité

═══════════════════════════════════════════════════════════════

❓ Avez-vous bien compris ces avertissements ?

[ ] OUI, j'ai compris et j'accepte la responsabilité
[ ] NON, je veux plus d'informations avant de continuer

═══════════════════════════════════════════════════════════════
"""
