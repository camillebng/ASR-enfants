// ***** ***** STOCKAGE DES TRANSCRIPTIONS ***** *****
let texteTranscriptionComplet = "";
let textGridTranscriptionComplet = ""; 



// ***** ***** SELECTEUR D'ELEMENTS ***** *****

// Paramètres du modèle
const selectSystem = document.getElementById('model-type');
const selectModel = document.getElementById('model-size');
const selectDevice = document.getElementById('device-type');
const selectTemp = document.getElementById('temperature');
const selectCompression = document.getElementById('compression');
const selectBeam = document.getElementById('beam-size');

// Gestion des fichiers 
const inputAudio = document.getElementById('sounds');
const fileList = document.getElementById('file-list-display');

// Commandes de transcription et d'outils
const btnTranscrire = document.getElementById('transcr-btn');
const btnInterrupt = document.getElementById('interrupt-btn');
const btnVider = document.getElementById('clear-btn');
const btnScinder = document.getElementById('split-btn');
const inputTextGrid = document.getElementById('textgrid'); 
const conteneurPraat = document.getElementById('praat-scripts');

// Affichage de l'exécution et de la transcription
const consoleTextarea = document.getElementById('execution-console');
const zoneTranscription = document.getElementById('transcript-text');

// Exportation des résultats
const selectFormat = document.getElementById('export-format');
const btnExporter = document.getElementById('download-btn');

// Evaluation des résultats (CER/CER)
const inputRef = document.getElementById('transcr-ref');
const btnWer = document.getElementById('wer-btn');
const codes = document.getElementById('codage');
const zoneResultats = document.getElementById('wer-results');




// ***** ***** ECHANGES AVEC LE SERVEUR ***** *****

// Lance la transcription et met à jour l'interface
async function lancerTranscription(formData) {
    if (!consoleTextarea) return;
    consoleTextarea.value = "$ python mon_script.py\n";

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Erreur serveur (${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while(true) {
            const {value, done} = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lignes = chunk.split('\n');

            lignes.forEach(ligne => {
                if (ligne.startsWith('data: ')) {
                    const message = ligne.replace('data: ', '').trim();

                    if (message.startsWith('{')) {
                        try {
                            const donnees = JSON.parse(message);
                            
                            if (donnees.statut === 'FIN_TRANSCRIPTION') {
                                if (zoneTranscription) {
                                    let texteOriginal = donnees.texte;
                                    texteTranscriptionComplet = texteOriginal;
                                    textGridTranscriptionComplet = donnees.textgrid || ""; 
                                    
                                    if (donnees.alignement_lignes) {
                                        let htmlAlignement = "";
                                        const maxLignes = 20;
                                        const lignesAAfficher = donnees.alignement_lignes.slice(0, maxLignes);

                                        lignesAAfficher.forEach(ligne => {
                                            htmlAlignement += `
                                            <div class="bloc-alignement">
                                                <div><strong>Ligne ${ligne.num_ligne}</strong></div>
                                                <div class="ligne-ref">REF : ${ligne.ref}</div>
                                                <div class="ligne-pred">PRED: ${ligne.pred}</div>
                                            </div>
                                            <hr>`;
                                        });

                                        zoneTranscription.innerHTML = `
                                        <h3>Visualisation de la transcription</h3>
                                        <div class="zone-defilement-alignement">
                                            ${htmlAlignement}
                                        </div>`;
                                    } else {
                                        zoneTranscription.innerHTML = `
                                        <h3>Visualisation de la transcription</h3>
                                        <div class="zone-texte-simple">
                                            <p>${texteOriginal}</p>
                                        </div>`;
                                    }
                                }
                                
                                consoleTextarea.value += "> ✨ Transcription terminée avec succès\n";
                            }
                        } 
                        catch (e) {
                            console.error("Erreur lors du traitement du JSON :", e);
                            consoleTextarea.value += `> ${message}\n`;
                        }
                    } else {
                        consoleTextarea.value += `> ${message}\n`;
                    }

                    consoleTextarea.scrollTop = consoleTextarea.scrollHeight;
                }
            });
        }
        if (btnTranscrire) btnTranscrire.disabled = false;
    } 
    catch(erreur) {
        consoleTextarea.value += `❌ Erreur : ${erreur.message}\n`;
        if (btnTranscrire) btnTranscrire.disabled = false;
    }
}





// ***** ***** GESTIONNAIRES D'ÉVÉNEMENTS ***** *****

// Activation de l'option de découpage des fichiers sons
if (btnScinder) {
    btnScinder.addEventListener('click', function (evenement) {
        evenement.preventDefault();
        btnScinder.classList.toggle('active');

        if (btnScinder.classList.contains('active')) {
            btnScinder.style.border = "2px solid #b87458"; 
        } else {
            btnScinder.style.border = ""; 
        }
    });
}

// Calcul des scores WER/CER
if (btnWer) {
    btnWer.addEventListener('click', async function (evenement) {
        evenement.preventDefault(); 

        if (consoleTextarea) {
            consoleTextarea.value += "> 📊 Requête de calcul WER envoyée...\n";
            consoleTextarea.scrollTop = consoleTextarea.scrollHeight;
        }

        const textePred = texteTranscriptionComplet.trim();

        if (!inputRef || inputRef.files.length === 0 || textePred === "") {
            alert("Veuillez sélectionner un fichier de référence ET vous assurer qu'une transcription a été générée.");
            return;
        }

        try {
            const paquetWer = new FormData();
            paquetWer.append('reference_file', inputRef.files[0]);
            
            if (codes) {
                paquetWer.append('codes_users', codes.value);
            }

            const fichierPrediction = new File([textePred], "prediction.txt", { type: "text/plain;charset=utf-8" });
            paquetWer.append('prediction_files', fichierPrediction);

            if (zoneResultats) {
                zoneResultats.innerHTML = "<p>⏳ Calcul des scores en cours...</p> ";
            }

            const reponse = await fetch('/calcul-wer', {
                method: 'POST',
                body: paquetWer
            });

            if (!reponse.ok) {
                throw new Error(`Erreur serveur : ${reponse.status}`);
            }

            const resultats = await reponse.json();

            if (zoneResultats) {
                zoneResultats.innerHTML = `
                <h3>📊 Résultats du Calcul</h3>
                <p><strong>Score WER final :</strong> ${(resultats.wer * 100).toFixed(2)}%</p>
                <p><strong>Score CER final :</strong> ${(resultats.cer * 100).toFixed(2)}%</p>
                <ul>
                    <li>Substitutions (WER) : ${resultats.details_wer.sub}</li>
                    <li>Suppressions (WER) : ${resultats.details_wer.del}</li>
                    <li>Insertions (WER) : ${resultats.details_wer.ins}</li>
                </ul>
                `;
            }
        }
        catch (erreur) {
            console.error("Erreur lors du calcul :", erreur);
            if (zoneResultats) {
                zoneResultats.innerHTML = `<p style="color: red;">❌ Une erreur est survenue : ${erreur.message}</p>`;
            }
        }
    });
}

// Interruption de la transcription
if (btnInterrupt) {
    btnInterrupt.addEventListener('click', async function (evenement) {
        evenement.preventDefault(); 
        btnInterrupt.disabled = true;

        try {
            await fetch('/interrupt', { method: 'POST' });
            
            if (consoleTextarea) {
                consoleTextarea.value += "⚠️ Transcription interrompue\n";
            }
            btnInterrupt.disabled = false;
        }
        catch (erreur) {
            if (consoleTextarea) {
                consoleTextarea.value += `❌ Erreur : ${erreur.message}\n`;
            }
            btnInterrupt.disabled = false;
        }
    });
}

// Déclenchement de la transcription globale
if (btnTranscrire) {
    btnTranscrire.addEventListener('click', function(evenement) {
        evenement.preventDefault();

        if (!inputAudio || !inputAudio.files || inputAudio.files.length === 0) {
            alert("Veuillez sélectionner un fichier audio avant de lancer la transcription.");
            return;
        }

        const decoupageActif = btnScinder && btnScinder.classList.contains('active');
        if (decoupageActif && (!inputTextGrid || inputTextGrid.files.length === 0)) {
            alert("Veuillez sélectionner un fichier TextGrid pour effectuer le découpage.");
            return;
        }

        btnTranscrire.disabled = true;

        let formData = new FormData();
        if (selectSystem) formData.append('systeme', selectSystem.value);
        if (selectModel) formData.append('modele', selectModel.value);
        if (selectDevice) formData.append('device', selectDevice.value);
        if (selectTemp) formData.append('temperature', selectTemp.value);
        if (selectCompression) formData.append('compression-ratio-threshold', selectCompression.value);
        if (selectBeam) formData.append('beam-size', selectBeam.value);

        if (btnScinder) {
            formData.append('activer_decoupage', btnScinder.classList.contains('active'));
        }

        const fichiersTries = Array.from(inputAudio.files).sort((a, b) => {
            return a.name.localeCompare(b.name, undefined, {numeric: true});
        });

        fichiersTries.forEach(fichier => {
            formData.append('audio', fichier);
        });
        
        if (inputRef && inputRef.files && inputRef.files.length > 0) {
            formData.append('texte', inputRef.files[0]);
        }

        if (inputTextGrid && inputTextGrid.files && inputTextGrid.files.length > 0) {
            formData.append('textgrid', inputTextGrid.files[0]);
        }

        lancerTranscription(formData);
    });
}

// Génération des fichiers d'export
if (btnExporter) {
    btnExporter.addEventListener('click', function() {
        if (!zoneTranscription || !selectFormat) return;

        const texteBrut = texteTranscriptionComplet.trim() || zoneTranscription.innerText.trim();

        if (texteBrut === "La transcription apparaîtra ici" || texteBrut === "Transcription en cours..." || texteBrut === "") {
            alert("Il n'y a aucune transcription valide à exporter pour le moment.");
            return;
        }

        const formatChoisi = selectFormat.value;
        let contenuFichier = "";
        let typeMime = "text/plain;charset=utf-8";
        let nomExtension = "txt";

        if (formatChoisi === "txt") {
            contenuFichier = texteBrut;
            typeMime = "text/plain;charset=utf-8";
            nomExtension = "txt";
        } 
        else if (formatChoisi === "json") {
            const objetJson = {
                programme: "Transcription via WhisperX",
                date: new Date().toLocaleString(),
                format_export: "json",
                texte_transcrit: texteBrut
            };
            contenuFichier = JSON.stringify(objetJson, null, 4);
            typeMime = "application/json;charset=utf-8";
            nomExtension = "json";
        } 
        else if (formatChoisi === "srt") {
            contenuFichier = "1\n00:00:00,000 --> 00:05:00,000\n" + texteBrut + "\n";
            typeMime = "text/srt;charset=utf-8";
            nomExtension = "srt";
        }
        else if (formatChoisi === "textgrid") { 
            if (!textGridTranscriptionComplet) {
                alert("Aucune donnée TextGrid disponible. Le découpage était-il bien activé ?");
                return;
            }
            contenuFichier = textGridTranscriptionComplet;
            typeMime = "text/plain;charset=utf-8";
            nomExtension = "TextGrid";
        }

        const blob = new Blob([contenuFichier], { type: typeMime });
        const url = URL.createObjectURL(blob);
        const lienTemporaire = document.createElement('a');
        
        lienTemporaire.href = url;
        lienTemporaire.download = `transcription.${nomExtension}`;
        
        document.body.appendChild(lienTemporaire);
        lienTemporaire.click();
        
        document.body.removeChild(lienTemporaire);
        URL.revokeObjectURL(url);
    });
}

// Affichage et tri de la liste des fichiers, gestion des boutons "Vider" et "Scinder"
if (inputAudio) {
    inputAudio.addEventListener('change', function() {
        if (fileList) {
            fileList.innerHTML = "";
            const fichiersAffichageTries = Array.from(inputAudio.files).sort((a, b) => {
                return a.name.localeCompare(b.name, undefined, {numeric: true});
            });
            fichiersAffichageTries.forEach(fichier => {
                fileList.innerHTML += `<li>📄 ${fichier.name}</li>`;
            });
        }
        if (btnVider) {
            if (inputAudio.files.length > 0) {
                btnVider.classList.remove("hidden");
            } else {
                btnVider.classList.add("hidden");
            }
        }

        if (conteneurPraat) {
            if (inputAudio.files.length > 0) {
                conteneurPraat.classList.remove("hidden");
            } else {
                conteneurPraat.classList.add("hidden");
                if (btnScinder) {
                    btnScinder.classList.remove("active");
                    btnScinder.style.border = "";
                }
            }
        }
    });
}

// Nettoyage des fichiers chargés 
if (btnVider) {
    btnVider.addEventListener('click', function(evenement) {
        evenement.preventDefault();
        if (inputAudio) inputAudio.value = "";
        if (fileList) fileList.innerHTML = "";
        btnVider.classList.add("hidden");

        if (conteneurPraat) {
            conteneurPraat.classList.add("hidden");
        }
        if (btnScinder) {
            btnScinder.classList.remove("active");
            btnScinder.style.border = "";
        }
    });
}