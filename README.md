# Prérequis

## 1. Miniconda
Il est nécessaire d'installer l'environnement Python via Miniconda.
* Téléchargez l'installeur 64-bits pour Windows ici : https://www.anaconda.com/download/success
* Lancez l'installation et choisissez votre dossier utilisateur comme emplacement du dossier miniconda3. Si miniconda3 s'est téléchargé dans le dossier Utilisateurs/nom_user/AppData/Local par défaut, affichez les dossiers masqués et déplacez-le simplement dans votre dossier utilisateur personnel. Pour le reste, laissez toutes les options par défaut.

## 2. Pilotes et librairies NVIDIA (Optionnel mais recommandé)
Si vous possédez une carte graphique NVIDIA, cela permettra de réduire les temps de calculs.
1. Mettez vos pilotes graphiques à jour : https://www.nvidia.com/fr-fr/drivers/
2. Installez le toolkit CUDA 12.6 : https://developer.nvidia.com/cuda-12-6-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local

# Installation et Lancement

1. Dans le dossier de l'application, lancez le fichier `installer.bat` et laissez le script s'exécuter jusqu'au bout.
2. Lancez ensuite `start.bat` pour démarrer le serveur de l'application dans le navigateur.

*Note : si la page s'ouvre sur une erreur, essayez de rafraîchir la page.*

# Prétraitement des fichiers à transcrire
La présence de longs silences dans les fichiers audio a tendance à générer des hallucinations avec WhisperX. Il est donc conseillé de les diviser en plus petits fichiers pour chaque prise de parole grâce à l'option "Scinder les fichiers".

Cependant, il faut au préalable segmenter les prises de parole à transcrire dans un fichier textgrid. 
* Seuls les segments **non-vides** seront extraits en .wav séparés : il suffit par exemple d'y insérer une simple lettre pour valider l'extraction.
* La segmentation doit impérativement se trouver sur le **Tier 1**. 

