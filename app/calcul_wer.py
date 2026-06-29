import os
import re
from pathlib import Path
import jiwer

def fusionner_transcriptions(liste_pred):
    """Prend une liste de chaînes de caractère et les fusionne en une seule chaîne"""
    clean_txt = [texte.strip() if texte.strip() else "" for texte in liste_pred]
    return " ".join(clean_txt)


def calculer_wer(reference,prediction,codes_users=None):
    if codes_users is None:
        codes_users = []

    reference = reference.lower()
    prediction  =prediction.lower()
    
    clean_ref = re.sub("[.,?!;:']", " ", reference)
    clean_pred = re.sub("[.,?!;:']", " ", prediction)

    # Pour les espaces multiples
    clean_ref = re.sub(r"\s+", " ", clean_ref).strip()
    clean_pred = re.sub(r"\s+", " ", clean_pred).strip()

    # Nettoyage identique des codages
    codages = [c.lower().strip() for c in codes_users if c.strip()]

    # Préparation du pattern regex pour le CER
    if codages:
        pattern_codages = r"\b(" + "|".join(map(re.escape, codages)) + r")\b"
        global_clean_ref_cer = re.sub(pattern_codages, "*", clean_ref)
        global_clean_pred_cer = re.sub(pattern_codages, "*", clean_pred)
    else:
        global_clean_ref_cer = clean_ref
        global_clean_pred_cer = clean_pred

    global_clean_ref_cer = re.sub(r"\s+", " ", global_clean_ref_cer).strip()
    global_clean_pred_cer = re.sub(r"\s+", " ", global_clean_pred_cer).strip()

    # Préparation des listes pour les matrices 
    ref_wer = clean_ref.split()
    pred_wer = clean_pred.split()
    ref_cer = list(global_clean_ref_cer)
    pred_cer = list(global_clean_pred_cer)


    # ***** CALCUL DU WER *****

    # Créer matrice à deux dimensions
    len_ref_wer = len(ref_wer)
    len_pred_wer = len(pred_wer)

    ligne_precedente = [[0, 0, 0, 0] for _ in range(len_pred_wer + 1)]
    ligne_courante = [[0, 0, 0, 0] for _ in range(len_pred_wer + 1)]

    # Remplissage initial de la ligne 0 (Insertions)
    for j in range(1, len_pred_wer + 1):
        ligne_precedente[j] = [j, 0, 0, j]

    for i in range(1, len_ref_wer + 1):
        # Remplissage initial de la colonne 0 (Suppressions)
        ligne_courante[0] = [i, 0, i, 0]
        mot_ref = ref_wer[i-1]

        for j in range(1, len_pred_wer + 1):
            mot_pred = pred_wer[j-1]
            # Calcul de la diagonale (substitution ou identique)
            cout_diag_prec = ligne_precedente[j-1][0]

            if mot_ref == mot_pred:
                diagonale = cout_diag_prec + 0

            # Substitutions tolérées
            elif mot_ref in codages:
                diagonale = cout_diag_prec + 0

            else:
                diagonale = cout_diag_prec + 1

            # Calcul de la verticale (suppression)
            verticale = ligne_precedente[j][0] + 1

            # Calcul de l'horizontale (insertion)
            horizontale = ligne_courante[j-1][0] + 1

            # Choix du chemin le plus court
            cout_minimal = min(diagonale, verticale, horizontale)

            # Mise à jour des compteurs
            if cout_minimal == diagonale:
                if mot_ref != mot_pred and mot_ref not in codages:
                    substitution = ligne_precedente[j-1][1] + 1
                else:
                    substitution = ligne_precedente[j-1][1]
                deletion = ligne_precedente[j-1][2]
                insertion = ligne_precedente[j-1][3]

            elif cout_minimal == verticale:
                substitution = ligne_precedente[j][1]
                deletion = ligne_precedente[j][2] + 1
                insertion = ligne_precedente[j][3]

            else:
                substitution = ligne_courante[j-1][1]
                deletion = ligne_courante[j-1][2]
                insertion = ligne_courante[j-1][3] + 1

            # Sauvegarde finale de toutes les valeurs dans la case courante
            ligne_courante[j] = [cout_minimal, substitution, deletion, insertion]

        ligne_precedente = list(ligne_courante)


    len_ref_cer = len(ref_cer)
    len_pred_cer = len(pred_cer)

    # Extraction des résultats finaux
    resultat_final = ligne_courante[len_pred_wer]
    total_sub = resultat_final[1]
    total_del = resultat_final[2]
    total_ins = resultat_final[3]

    # Calcul final du WER
    wer = (total_sub + total_del + total_ins) / len_ref_wer if len_ref_wer > 0 else 0

    print(f"--- RÉSULTATS WER ---")
    print(f"Substitutions : {total_sub}")
    print(f"Suppressions  : {total_del}")
    print(f"Insertions    : {total_ins}")
    print(f"Score WER final : {wer:.2%}")



    # ***** CALCUL DU CER *****

    ligne_precedente_cer = [[0, 0, 0, 0] for _ in range(len_pred_cer + 1)]
    ligne_courante_cer = [[0, 0, 0, 0] for _ in range(len_pred_cer + 1)]

    for j in range(1, len_pred_cer + 1):
        ligne_precedente_cer[j] = [j, 0, 0, j]

    for i in range(1, len_ref_cer + 1):
        ligne_courante_cer[0] = [i, 0, i, 0]
        char_ref = ref_cer[i-1]

        for j in range(1, len_pred_cer + 1):
            char_pred = pred_cer[j-1]
            cout_diag_prec_cer = ligne_precedente_cer[j-1][0]

            if char_ref == char_pred:
                diagonale_cer = cout_diag_prec_cer + 0
            else:
                diagonale_cer = cout_diag_prec_cer + 1

            verticale_cer = ligne_precedente_cer[j][0] + 1
            horizontale_cer = ligne_courante_cer[j-1][0] + 1

            cout_minimal_cer = min(diagonale_cer, verticale_cer, horizontale_cer)

            if cout_minimal_cer == diagonale_cer:
                if char_ref != char_pred:
                    substitution_cer = ligne_precedente_cer[j-1][1] + 1
                else:
                    substitution_cer = ligne_precedente_cer[j-1][1]
                deletion_cer = ligne_precedente_cer[j-1][2]
                insertion_cer = ligne_precedente_cer[j-1][3]
            elif cout_minimal_cer == verticale_cer:
                substitution_cer = ligne_precedente_cer[j][1]
                deletion_cer = ligne_precedente_cer[j][2] + 1
                insertion_cer = ligne_precedente_cer[j][3]
            else:
                substitution_cer = ligne_courante_cer[j-1][1]
                deletion_cer = ligne_courante_cer[j-1][2]
                insertion_cer = ligne_courante_cer[j-1][3] + 1

            ligne_courante_cer[j] = [cout_minimal_cer, substitution_cer, deletion_cer, insertion_cer]

        ligne_precedente_cer = list(ligne_courante_cer)

    resultat_final_cer = ligne_courante_cer[len_pred_cer]
    total_sub_cer = resultat_final_cer[1]
    total_del_cer = resultat_final_cer[2]
    total_ins_cer = resultat_final_cer[3]

    cer = (total_sub_cer + total_del_cer + total_ins_cer) / len_ref_cer if len_ref_cer > 0 else 0

    print(f"\n--- RÉSULTATS CER ---")
    print(f"Substitutions : {total_sub_cer}")
    print(f"Suppressions  : {total_del_cer}")
    print(f"Insertions    : {total_ins_cer}")
    print(f"Score CER final : {cer:.2%}")

    return {
        "wer": wer,
        "cer": cer,
        "details_wer": {"sub": total_sub, "del": total_del, "ins": total_ins},
        "details_cer": {"sub": total_sub_cer, "del": total_del_cer, "ins": total_ins_cer}
    }