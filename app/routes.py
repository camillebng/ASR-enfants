
# ***** ***** LIBRAIRIES ***** *****

import torch
import os
# Module spécifique désactivé pour éviter des conflits d'encodage audio
os.environ["USE_TORCHCODEC"] = "0"
import time
from flask import request, jsonify, send_from_directory, Response
from app import app
import whisperx
from .calcul_wer import fusionner_transcriptions, calculer_wer
from threading import Thread, Event
import signal
import json
import re
from parselmouth.praat import run_file
import parselmouth

# Contrôles pour suivre le statut de la transcription
processus_transcription = None
interruption_evenement = Event()



# ***** ***** MOTEUR DE TRANSCRIPTION ***** *****


def transcribe(chemins_audios, chemin_tg, system_type, model_size, language, device, compute_type, batch_size, temperature, compression_ratio_threshold, beam_size, dossier_temp, activer_decoupage):
    try:
        # Vérifie la présence du .textgrid si le découpage a été sélectionné 
        if activer_decoupage and (not chemin_tg or not os.path.exists(chemin_tg)):
            raise FileNotFoundError("Le fichier TextGrid est requis pour le découpage.")

        # Ajustement si le calcul est fait sur le processeur
        if device == "cpu":
            batch_size = 1

        # Options WhisperX sélectionnées par l'utilisateur
        options_asr = {
            "temperatures": [temperature],
            "beam_size": beam_size,
            "compression_ratio_threshold": compression_ratio_threshold
        }

        intervalles_originaux = []
        
        # Découpage des grands fichiers audio en petit chunks
        if activer_decoupage:
            fichiers_initiaux = set(os.listdir(dossier_temp))
            for chemin_audio in chemins_audios:
                # Arrêt si l'utilisateur a cliqué sur "Interrompre"
                if interruption_evenement.is_set():
                    return
                
                chemin_script_save = os.path.join(app.root_path, "save_labeled_intervals_to_wav_sound_files.praat").replace("\\", "/")
                audio_praat = chemin_audio.replace("\\", "/")
                tg_praat = chemin_tg.replace("\\", "/")
                dossier_praat = dossier_temp.replace("\\", "/")

                # Exécution du script de découpage Praat
                run_file(chemin_script_save, str(audio_praat), str(tg_praat), "1", "1", "0", str(dossier_praat), "", "")
            
            # Récupération et tri des nouveaux petits fichiers audio générés
            fichiers_actuels = set(os.listdir(dossier_temp))
            nouveaux_fichiers = fichiers_actuels - fichiers_initiaux
            chemins_decoupes = sorted([os.path.join(dossier_temp, f) for f in nouveaux_fichiers if f.endswith(".wav")])
            
            if chemins_decoupes:
                chemins_audios = chemins_decoupes
            
            # Lecture des repères temporels d'origine
            intervalles_originaux = extraire_intervalles_tg(chemin_tg)

        # Chargement de WhisperX
        model = whisperx.load_model(
            whisper_arch=model_size, 
            device=device, 
            compute_type=compute_type,
            asr_options=options_asr
        )
        
        texte_final = ""
        resultats_tg = []
        
        # Chaque fichier audio est transcrit (transformé en texte)
        for i, chemin_audio in enumerate(chemins_audios):
            if interruption_evenement.is_set():
                return
            
            # Chargement du son 
            audio = whisperx.load_audio(chemin_audio)

            # Transcription du son
            result = model.transcribe(
                audio, 
                language=language, 
                batch_size=batch_size
            )
            
            # "Recollage" des morceaux de transcription en un seul texte
            texte_chunk = ""
            for segment in result["segments"]:
                texte_chunk += segment["text"] + " "
            
            texte_chunk = texte_chunk.strip()
            texte_final += texte_chunk + " "

            # Si le découpage était actif, on associe le texte avec les timestamps d'origine
            if activer_decoupage and i < len(intervalles_originaux):
                resultats_tg.append({
                    "xmin": intervalles_originaux[i]["xmin"],
                    "xmax": intervalles_originaux[i]["xmax"],
                    "text": texte_chunk
                })

        # Sauvegarde finale des résultats dans des fichiers temporaires 
        if not interruption_evenement.is_set():
            # Texte brut complet
            chemin_resultat = os.path.join(dossier_temp, 'resultat.txt')
            with open(chemin_resultat, "w", encoding="utf-8") as f:
                f.write(texte_final.strip())

            # Fichier textgrid aligné
            if activer_decoupage and resultats_tg:
                chemin_tg_out = os.path.join(dossier_temp, 'resultat.TextGrid')
                xmax_total = resultats_tg[-1]["xmax"] if resultats_tg else 0
                with open(chemin_tg_out, "w", encoding="utf-8") as f:
                    f.write('File type = "ooTextFile"\nObject class = "TextGrid"\n\n')
                    f.write(f'xmin = 0\nxmax = {xmax_total}\n')
                    f.write('tiers? <exists>\nsize = 1\n')
                    f.write('item []:\n    item [1]:\n        class = "IntervalTier"\n')
                    f.write('        name = "transcription"\n')
                    f.write(f'        xmin = 0\n        xmax = {xmax_total}\n')
                    f.write(f'        intervals: size = {len(resultats_tg)}\n')
                    for idx, seg in enumerate(resultats_tg, 1):
                        f.write(f'        intervals [{idx}]:\n')
                        f.write(f'            xmin = {seg["xmin"]:.3f}\n')
                        f.write(f'            xmax = {seg["xmax"]:.3f}\n')
                        f.write(f'            text = "{seg["text"].replace(chr(34), chr(34)+chr(34))}"\n')

    except Exception as e:
        if not interruption_evenement.is_set():
            chemin_erreur = os.path.join(dossier_temp, 'erreur.txt')
            with open(chemin_erreur, "w", encoding="utf-8") as f:
                f.write(str(e))

# Outil extraire les zones de début/fin dans un fichier textgrid 
def extraire_intervalles_tg(chemin_tg):
    tg = parselmouth.praat.call("Read from file", chemin_tg)
    nb_intervalles = parselmouth.praat.call(tg, "Get number of intervals", 1)
    
    intervalles = []
    for i in range(1, nb_intervalles + 1):
        label = parselmouth.praat.call(tg, "Get label of interval", 1, i)
        xmin = parselmouth.praat.call(tg, "Get start time of interval", 1, i)
        xmax = parselmouth.praat.call(tg, "Get end time of interval", 1, i)
        
        # On ne garde que les zones qui contiennent du texte (on ignore les parties vides)
        if label.strip() != "":
            intervalles.append({"text": label, "xmin": xmin, "xmax": xmax})
            
    return intervalles


# =========================================================================
# ***** ***** LIAISON FRONTEND ***** *****
# =========================================================================

# Page d'accueil
@app.route('/')
def index():
    return send_from_directory(app.root_path, 'site.html')

# Réception des fichiers et gestion du suivi d'exécution
@app.route('/transcribe', methods=['POST'])
def route_transcribe_stream():
    global processus_transcription

    # Paramètres par défaut  
    compute_type = "int8"
    batch_size = 4
    language = "fr"

    # Paramètres choisis par l'utilisateur
    system_type = request.form.get('systeme')
    model_size = request.form.get('modele')
    device = request.form.get('device')
    temperature = float(request.form.get('temperature') or 0.0)
    compression_ratio_threshold = float(request.form.get('compression-ratio-threshold') or 3.5)
    beam_size = int(request.form.get('beam-size') or 5)
    activer_decoupage = request.form.get('activer_decoupage') == 'true'
    
    # Préparation du dossier de stockage temporaire
    dossier_temp = os.path.join(app.root_path, 'temp')
    os.makedirs(dossier_temp, exist_ok=True)
    
    # Enregistrement des fichiers audios 
    fichiers_audios = request.files.getlist('audio')
    chemins_audios = []
    for fichier in fichiers_audios:
        if fichier.filename != '':
            chemin = os.path.join(dossier_temp, fichier.filename)
            fichier.save(chemin)
            chemins_audios.append(chemin)

    # Enregistrement du fichier textgrid s'il existe
    fichier_tg = request.files.get('textgrid')
    chemin_tg = ""
    if fichier_tg and fichier_tg.filename != '':
        chemin_tg = os.path.join(dossier_temp, fichier_tg.filename)
        fichier_tg.save(chemin_tg)

    # Enregistrement et lecture de la transcription de référence
    fichier_ref = request.files.get('texte')
    texte_reference = None
    if fichier_ref and fichier_ref.filename != '':
        texte_reference = fichier_ref.read().decode('utf-8')

    # Notifications d'exécution
    def generer_logs():
        global processus_transcription

        # Empêche de lancer deux transcriptions en même temps
        if processus_transcription != None and processus_transcription.is_alive():
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            if chemin_tg and os.path.exists(chemin_tg):
                os.remove(chemin_tg)
            yield "data: ❌ Erreur : Une transcription est déjà en cours \n\n"
            return

        yield f"data: 📁 {len(chemins_audios)} fichier(s) audio sauvegardé(s)\n\n"
        time.sleep(0.5)

        if activer_decoupage:
            yield "data: ✂️ Prise en compte du découpage Praat en cours...\n\n"
            time.sleep(0.5)

        yield "data: 🤖 Chargement du modèle WhisperX en cours\n\n"

        # Lancement de la transcription en arrière-plan 
        interruption_evenement.clear()
        processus_transcription = Thread(
            target=transcribe, 
            args=(chemins_audios, chemin_tg, system_type, model_size, language, device, compute_type, batch_size, temperature, compression_ratio_threshold, beam_size, dossier_temp, activer_decoupage)
        )
        processus_transcription.start()

        yield "data: ⏳ Transcription du lot en cours...\n\n"

        while processus_transcription.is_alive():
            time.sleep(1)

        # Vérification des fichiers de sortie 
        chemin_resultat = os.path.join(dossier_temp, 'resultat.txt')
        chemin_erreur = os.path.join(dossier_temp, 'erreur.txt')
        chemin_tg_resultat = os.path.join(dossier_temp, 'resultat.TextGrid')
        
        # On lit les fichiers créés et on renvoie le résultat complet
        if os.path.exists(chemin_resultat):
            yield "data: ✍️ Assemblage du texte\n\n"
            time.sleep(0.5)
            with open(chemin_resultat, "r", encoding="utf-8") as f:
                texte_recupere = f.read()
            os.remove(chemin_resultat) 

            textgrid_contenant = ""
            if os.path.exists(chemin_tg_resultat):
                with open(chemin_tg_resultat, "r", encoding="utf-8") as f:
                    textgrid_contenant = f.read()
                os.remove(chemin_tg_resultat)
            
            # Flush des fichiers audio d'origine qui ne sont plus utiles
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            if chemin_tg and os.path.exists(chemin_tg):
                os.remove(chemin_tg)

            # Préparation des données finales à envoyer au navigateur
            reponse_dict = {"statut": "FIN_TRANSCRIPTION", "texte": texte_recupere, "textgrid": textgrid_contenant}
            
            # Si l'utilisateur a chargé une transcription de référence, on calcule le WER
            if texte_reference:
                resultats_bruts = calculer_wer(texte_reference, texte_recupere, [])
                if isinstance(resultats_bruts, dict) and 'alignement_lignes' in resultats_bruts:
                    reponse_dict["alignement_lignes"] = resultats_bruts['alignement_lignes']

            donnees_json = json.dumps(reponse_dict)
            yield f"data: {donnees_json}\n\n"
            
        # Gestion des erreurs
        elif os.path.exists(chemin_erreur):
            with open(chemin_erreur, "r", encoding="utf-8") as f:
                texte_erreur = f.read()
            os.remove(chemin_erreur)
            
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            if chemin_tg and os.path.exists(chemin_tg):
                os.remove(chemin_tg)
            yield f"data: ❌ Erreur : {texte_erreur}\n\n"
            
        # En cas d'interruption par l'utilisateur
        else:
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            if chemin_tg and os.path.exists(chemin_tg):
                os.remove(chemin_tg)
            yield "data: > ⚠️ Transcription interrompue par l'utilisateur\n\n"
            
    # Suivi en direct des étapes d'exécution
    return Response(generer_logs(), mimetype='text/event-stream')

# Arrêt immédiat si l'utilisateur a cliqué sur "Interrompre"
@app.route('/interrupt', methods=['POST'])
def interrupt_script():
    global processus_transcription

    if processus_transcription is not None and processus_transcription.is_alive():
        interruption_evenement.set()  
        processus_transcription.join()
        processus_transcription = None
        return jsonify({"message": "Transcription arrêtée avec succès"}), 200
    else:
        return jsonify({"message": "Aucune transcription en cours à arrêter"}), 400

# Comparaison entre la transcription de référence et la prédiction pour calculer le WER/CER
@app.route('/calcul-wer', methods=['POST'])
def calculer_wer_route():
    codages_bruts = request.form.get('codes_users', '')
    fichier_ref = request.files.get('reference_file')
    fichier_prediction = request.files.get('prediction_files')

    if not fichier_ref or not fichier_prediction :
        return jsonify({"erreur": "Fichiers manquants pour le calcul"}), 400

    # Lecture et nettoyage des données textuelles reçues 
    liste_codages = [c.strip() for c in codages_bruts.split(' ') if c.strip()]
    texte_reference = fichier_ref.read().decode('utf-8')
    texte_pred = re.sub('\[.*?\.wav\]', "", fichier_prediction.read().decode('utf-8')) 
    
    # Calcul du WER/CER
    resultats_bruts = calculer_wer(texte_reference, texte_pred, liste_codages)

    wer, cer = 0.0, 0.0
    details = {"sub": 0, "del": 0, "ins": 0}

    # Extraction des scores
    if isinstance(resultats_bruts, dict):
        wer = resultats_bruts.get('wer', 0.0)
        cer = resultats_bruts.get('cer', 0.0)

        if 'details_wer' in resultats_bruts and isinstance(resultats_bruts['details_wer'], dict):
            details = resultats_bruts['details_wer']
        else:
            details["sub"] = resultats_bruts.get('sub', resultats_bruts.get('substitutions', 0))
            details["del"] = resultats_bruts.get('del', resultats_bruts.get('suppressions', 0))
            details["ins"] = resultats_bruts.get('ins', resultats_bruts.get('insertions', 0))
            
    elif isinstance(resultats_bruts, (tuple, list)) and len(resultats_bruts) >= 2:
        wer = resultats_bruts[0]
        cer = resultats_bruts[1]
        if len(resultats_bruts) > 2 and isinstance(resultats_bruts[2], dict):
            details = resultats_bruts[2]

    # Structuration de la réponse au format JSON pour l'affichage des résultats
    reponse_formatee = {
        "wer": wer,
        "cer": cer,
        "details_wer": {
            "sub": details.get("sub", 0),
            "del": details.get("del", 0),
            "ins": details.get("ins", 0)
        }
    }

    return jsonify(reponse_formatee), 200