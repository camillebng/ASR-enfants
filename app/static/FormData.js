let texteTranscriptionComplet = "";

const selectSystem = document.getElementById('model-type');
const selectModel = document.getElementById('model-size');
const selectLang = document.getElementById('lang');
const selectDevice = document.getElementById('device-type');
const selectCompute = document.getElementById('compute-type');
const selectBatch = document.getElementById('batch-size');
const selectTemp = document.getElementById('temperature');
const selectCompression = document.getElementById('compression');
const selectBeam = document.getElementById('beam-size');

const inputAudio = document.getElementById('sounds');
const fileList = document.getElementById('file-list-display');

const btnTranscrire = document.getElementById('transcr-btn');
const btnInterrupt = document.getElementById('interrupt-btn');
const btnVider = document.getElementById('clear-btn');
const btnScinder = document.getElementById('split-btn');

const consoleTextarea = document.getElementById('execution-console');

const zoneTranscription = document.getElementById('transcript-text');
const selectFormat = document.getElementById('export-format');
const btnExporter = document.getElementById('download-btn');

const limite_taille_audio = 100 * 1024 * 1024;

const inputRef = document.getElementById('transcr-ref');
const btnWer = document.getElementById('wer-btn');
const codes = document.getElementById('codage');
const zoneResultats = document.getElementById('wer-results');

function formaterTranscrParLignes(texte, maxMots, maxLignes) {
    let mots = texte.replace(/\s+/g, ' ').trim().split(' ');
    let lignes = [];

    if (mots.length === 1 && mots[0] === "") return "";

    for (let i = 0; i < mots.length; i += maxMots) {
        let morceau = mots.slice(i, i + maxMots).join(' ');
        lignes.push(morceau);
    }

    let lignesLimitees = lignes.slice(0, maxLignes);
    let resultat = lignesLimitees.join('\n');

    if (lignes.length > maxLignes) {
        resultat += '\n...';
    }

    return resultat;
}

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

        if (inputRef.files[0].size > limite_taille_audio) {
            alert(`Le fichier de référence est trop volumineux.`);
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

if (btnInterrupt) {
    btnInterrupt.addEventListener('click', async function (evenement) {
        evenement.preventDefault(); 
        btnInterrupt.disabled = true;

        try {
            const reponse = await fetch('/interrupt', {
                method: 'POST',
                });
            
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
                                    
                                    if (donnees.alignement_lignes) {
                                        let htmlAlignement = "";

                                        const maxLignes = 10;
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

if (btnTranscrire) {
    btnTranscrire.addEventListener('click', function(evenement) {
        evenement.preventDefault();

        if (!inputAudio || !inputAudio.files || inputAudio.files.length === 0) {
            alert("Veuillez sélectionner un fichier audio avant de lancer la transcription.");
            return;
        }

        const tropGrand = Array.from(inputAudio.files).some(fichier => fichier.size > limite_taille_audio);
        if (tropGrand) {
            alert("Un ou plusieurs fichiers audio dépassent la limite autorisée de 100 Mo par fichier.");
            return;
        }

        btnTranscrire.disabled = true;

        let formData = new FormData();
        if (selectSystem) formData.append('systeme', selectSystem.value);
        if (selectModel) formData.append('modele', selectModel.value);
        if (selectLang) formData.append('language', selectLang.value);
        if (selectDevice) formData.append('device', selectDevice.value);
        if (selectCompute) formData.append('compute-type', selectCompute.value);
        if (selectBatch) formData.append('batch-size', selectBatch.value);
        if (selectTemp) formData.append('temperature', selectTemp.value);
        if (selectCompression) formData.append('compression-ratio-threshold', selectCompression.value);
        if (selectBeam) formData.append('beam-size', selectBeam.value);

        const fichiersTries = Array.from(inputAudio.files).sort((a, b) => {
            return a.name.localeCompare(b.name, undefined, {numeric: true});
        });

        fichiersTries.forEach(fichier => {
            formData.append('audio', fichier);
        });
        
        if (inputRef && inputRef.files && inputRef.files.length > 0) {
            formData.append('texte', inputRef.files[0]);
        }

        lancerTranscription(formData);
    });
}

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
        if (btnScinder) {
            if (inputAudio.files.length === 1) {
                const urlTemporaire = URL.createObjectURL(inputAudio.files[0]);
                const audioVirtuel = new Audio(urlTemporaire);
                audioVirtuel.addEventListener('loadedmetadata', function() {
                    if (audioVirtuel.duration > 900) {
                        btnScinder.classList.remove("hidden");
                    } else {
                        btnScinder.classList.add("hidden");
                    }
                    URL.revokeObjectURL(urlTemporaire);
                });
            } else {
                btnScinder.classList.add("hidden");
            }
        }
    });
}

if (btnVider) {
    btnVider.addEventListener('click', function(evenement) {
        evenement.preventDefault();
        if (inputAudio) inputAudio.value = "";
        if (fileList) fileList.innerHTML = "";
        btnVider.classList.add("hidden");
        if (btnScinder) btnScinder.classList.add("hidden");
    });
}