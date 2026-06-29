import torch
import os
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

app.config['max_content_length'] = 505 * 1024 * 1024

processus_transcription = None
interruption_evenement = Event()

def transcribe(chemins_audios, modele, device, compute, language, dossier_temp):
    try:
        model = whisperx.load_model(modele, device, compute_type=compute)
        
        texte_final = ""
        for chemin_audio in chemins_audios:
            if interruption_evenement.is_set():
                return
            audio = whisperx.load_audio(chemin_audio)
            result = model.transcribe(audio, language=language)
            
            nom_fichier = os.path.basename(chemin_audio)
            texte_final += f"[{nom_fichier}]\n"
            for segment in result["segments"]:
                texte_final += segment["text"] + " "
            texte_final += "\n\n"

        if not interruption_evenement.is_set():
            chemin_resultat = os.path.join(dossier_temp, 'resultat.txt')
            with open(chemin_resultat, "w", encoding="utf-8") as f:
                f.write(texte_final.strip())
    except Exception as e:
        if not interruption_evenement.is_set():
            chemin_erreur = os.path.join(dossier_temp, 'erreur.txt')
            with open(chemin_erreur, "w", encoding="utf-8") as f:
                f.write(str(e))

@app.route('/')
def index():
    return send_from_directory(app.root_path, 'site.html')

@app.route('/transcribe', methods=['POST'])
def route_transcribe_stream():
    global processus_transcription

    modele = request.form.get('modele')
    device = request.form.get('device')
    compute = request.form.get('compute')
    language = request.form.get('language')

    dossier_temp = os.path.join(app.root_path, 'temp')
    os.makedirs(dossier_temp, exist_ok=True)
    
    fichiers_audios = request.files.getlist('audio')
    chemins_audios = []
    
    for fichier in fichiers_audios:
        if fichier.filename != '':
            chemin = os.path.join(dossier_temp, fichier.filename)
            fichier.save(chemin)
            chemins_audios.append(chemin)

    def generer_logs():
        global processus_transcription

        yield f"data: 📁 {len(chemins_audios)} fichier(s) audio sauvegardé(s)\n\n"
        time.sleep(0.5)

        yield "data: 🤖 Chargement du modèle WhisperX en cours\n\n"

        interruption_evenement.clear()
        processus_transcription = Thread(
            target=transcribe, 
            args=(chemins_audios, modele, device, compute, language, dossier_temp)
        )
        processus_transcription.start()

        yield "data: ⏳ Transcription du lot en cours...\n\n"

        while processus_transcription.is_alive():
            time.sleep(1)

        chemin_resultat = os.path.join(dossier_temp, 'resultat.txt')
        chemin_erreur = os.path.join(dossier_temp, 'erreur.txt')
        
        if os.path.exists(chemin_resultat):
            yield "data: ✍️ Assemblage du texte\n\n"
            time.sleep(0.5)
            with open(chemin_resultat, "r", encoding="utf-8") as f:
                texte_recupere = f.read()
            os.remove(chemin_resultat) 
            
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)

            donnees_json = json.dumps({"statut": "FIN_TRANSCRIPTION", "texte": texte_recupere})
            yield f"data: {donnees_json}\n\n"
            
        elif os.path.exists(chemin_erreur):
            with open(chemin_erreur, "r", encoding="utf-8") as f:
                texte_erreur = f.read()
            os.remove(chemin_erreur)
            
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            yield f"data: ❌ Erreur : {texte_erreur}\n\n"
        else:
            for chemin in chemins_audios:
                if os.path.exists(chemin):
                    os.remove(chemin)
            yield "data: > ⚠️ Transcription interrompue par l'utilisateur\n\n"

    return Response(generer_logs(), mimetype='text/event-stream')

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

@app.route('/calcul-wer', methods=['POST'])
def calculer_wer_route():
    codages_bruts = request.form.get('codes_users', '')
    fichier_ref = request.files.get('reference_file')
    fichier_prediction = request.files.get('prediction_files')

    if not fichier_ref or not fichier_prediction :
        return jsonify({"erreur": "Fichiers manquants pour le calcul"}), 400

    liste_codages = [c.strip() for c in codages_bruts.split(' ') if c.strip()]
    texte_reference = fichier_ref.read().decode('utf-8')
    texte_pred = re.sub('\[.*?\.wav\]', "", fichier_prediction.read().decode('utf-8')) 
    
    print(liste_codages)
    print(texte_reference)
    print(texte_pred)
    # Calcul brut des scores
    resultats_bruts = calculer_wer(texte_reference, texte_pred, liste_codages)

    wer, cer = 0.0, 0.0
    details = {"sub": 0, "del": 0, "ins": 0}

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