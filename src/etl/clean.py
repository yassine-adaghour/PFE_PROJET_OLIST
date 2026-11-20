# Data cleaning module
"""
Module de nettoyage et préparation des données Olist.

Ce module centralise les fonctions réutilisables pour :
- Le diagnostic de qualité des données
- Le traitement des valeurs manquantes
- La déduplication contrôlée
- La conversion des types de données
- La vérification des valeurs numériques
- Le contrôle d'intégrité référentielle
- La préparation principale des tables
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES ET CONFIGURATION
# =============================================================================

COLONNES_DATES = {
    "olist_orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_items": ["shipping_limit_date"],
    "olist_order_reviews": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}

COLONNES_NUMERIQUES_METIER = {
    "olist_order_items": ["price", "freight_value"],
    "olist_order_payments": ["payment_value", "payment_installments"],
    "olist_order_reviews": ["review_score"],
    "olist_products": [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
    ],
}

CLES_PRIMAIRES_ATTENDUES = {
    "olist_customers": ["customer_id"],
    "olist_orders": ["order_id"],
    "olist_products": ["product_id"],
    "olist_sellers": ["seller_id"],
    "product_category_name_translation": ["product_category_name"],
}

RELATIONS_REFERENTIELLES = [
    ("olist_orders", "customer_id", "olist_customers", "customer_id"),
    ("olist_order_items", "order_id", "olist_orders", "order_id"),
    ("olist_order_items", "product_id", "olist_products", "product_id"),
    ("olist_order_items", "seller_id", "olist_sellers", "seller_id"),
    ("olist_order_payments", "order_id", "olist_orders", "order_id"),
    ("olist_order_reviews", "order_id", "olist_orders", "order_id"),
]


# =============================================================================
# FONCTIONS DE DIAGNOSTIC
# =============================================================================

def diagnostiquer_qualite(df: pd.DataFrame, nom_table: str) -> pd.DataFrame:
    """
    Produit un diagnostic complet de qualité pour un DataFrame.

    Args:
        df: DataFrame à analyser
        nom_table: Nom de la table pour l'affichage

    Returns:
        DataFrame avec les métriques de qualité par colonne
    """
    lignes = []

    for col in df.columns:
        nb_total = len(df)
        nb_manquants = int(df[col].isna().sum())
        pct_manquants = round(100 * nb_manquants / nb_total, 2) if nb_total else 0.0
        nb_distincts = int(df[col].nunique(dropna=True))
        type_donnee = str(df[col].dtype)

        ligne = {
            "table": nom_table,
            "colonne": col,
            "type": type_donnee,
            "lignes_total": nb_total,
            "valeurs_manquantes": nb_manquants,
            "pct_manquantes": pct_manquants,
            "valeurs_distinctes": nb_distincts,
            "pct_distinctes": round(100 * nb_distincts / nb_total, 2) if nb_total else 0.0,
        }

        # Statistiques pour les colonnes numériques
        if pd.api.types.is_numeric_dtype(df[col]):
            serie = df[col].dropna()
            if not serie.empty:
                ligne.update({
                    "min": serie.min(),
                    "max": serie.max(),
                    "mean": round(serie.mean(), 4),
                    "median": round(serie.median(), 4),
                    "std": round(serie.std(), 4),
                    "q25": round(serie.quantile(0.25), 4),
                    "q75": round(serie.quantile(0.75), 4),
                })

        lignes.append(ligne)

    return pd.DataFrame(lignes)


def resumer_valeurs_manquantes(df: pd.DataFrame, nom_table: str) -> pd.DataFrame:
    """
    Résume les valeurs manquantes par colonne pour une table.

    Args:
        df: DataFrame à analyser
        nom_table: Nom de la table

    Returns:
        DataFrame trié par pourcentage de valeurs manquantes décroissant
    """
    rows = []
    for col in df.columns:
        nb = int(df[col].isna().sum())
        pct = round(100 * nb / len(df), 2) if len(df) else 0.0
        rows.append({
            "table": nom_table,
            "colonne": col,
            "valeurs_manquantes": nb,
            "pourcentage_manquant": pct
        })

    result = pd.DataFrame(rows)
    return result.sort_values("pourcentage_manquant", ascending=False)


def compter_doublons_complets(df: pd.DataFrame, nom_table: str) -> dict[str, Any]:
    """
    Compte les doublons complets dans un DataFrame.

    Args:
        df: DataFrame à analyser
        nom_table: Nom de la table

    Returns:
        Dictionnaire avec le nombre et pourcentage de doublons
    """
    nb_doublons = int(df.duplicated().sum())
    pct = round(100 * nb_doublons / len(df), 3) if len(df) else 0.0

    return {
        "table": nom_table,
        "doublons_complets": nb_doublons,
        "pourcentage_doublons": pct,
        "lignes_apres_dedup": len(df) - nb_doublons
    }


def verifier_cle_primaire(df: pd.DataFrame, colonnes_cle: list[str], nom_table: str) -> pd.DataFrame:
    """
    Vérifie l'unicité des clés primaires candidates.

    Args:
        df: DataFrame à vérifier
        colonnes_cle: Liste des colonnes qui devraient être uniques
        nom_table: Nom de la table

    Returns:
        DataFrame avec les résultats de vérification par clé
    """
    rows = []
    for col in colonnes_cle:
        if col not in df.columns:
            rows.append({
                "table": nom_table,
                "colonne": col,
                "statut": "COLONNE_ABSENTE",
                "valeurs_manquantes": None,
                "valeurs_distinctes": None,
                "doublons": None,
                "est_unique": False
            })
            continue

        serie = df[col].dropna()
        nb_manquants = int(df[col].isna().sum())
        nb_distincts = int(serie.nunique())
        nb_doublons = int(serie.duplicated().sum())
        est_unique = nb_doublons == 0 and nb_manquants == 0

        rows.append({
            "table": nom_table,
            "colonne": col,
            "statut": "OK" if est_unique else "DOUBLONS_OU_MANQUANTS",
            "valeurs_manquantes": nb_manquants,
            "valeurs_distinctes": nb_distincts,
            "doublons": nb_doublons,
            "est_unique": est_unique
        })

    return pd.DataFrame(rows)


def verifier_integrite_referentielle(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Vérifie l'intégrité référentielle entre les tables.

    Args:
        tables: Dictionnaire {nom_table: DataFrame}

    Returns:
        DataFrame avec les résultats de vérification par relation
    """
    rows = []

    for table_source, col_source, table_cible, col_cible in RELATIONS_REFERENTIELLES:
        src = tables.get(table_source)
        dst = tables.get(table_cible)

        if src is None or dst is None:
            rows.append({
                "table_source": table_source,
                "colonne_source": col_source,
                "table_cible": table_cible,
                "colonne_cible": col_cible,
                "statut": "TABLE_MANQUANTE",
                "references_orphelines": None
            })
            continue

        if col_source not in src.columns or col_cible not in dst.columns:
            rows.append({
                "table_source": table_source,
                "colonne_source": col_source,
                "table_cible": table_cible,
                "colonne_cible": col_cible,
                "statut": "COLONNE_MANQUANTE",
                "references_orphelines": None
            })
            continue

        valeurs_cibles = set(dst[col_cible].dropna().unique())
        source_non_null = src[col_source].dropna()
        orphelines = int((~source_non_null.isin(valeurs_cibles)).sum())

        rows.append({
            "table_source": table_source,
            "colonne_source": col_source,
            "table_cible": table_cible,
            "colonne_cible": col_cible,
            "statut": "OK" if orphelines == 0 else "ORPHELINES_DETECTEES",
            "references_orphelines": orphelines
        })

    return pd.DataFrame(rows)


# =============================================================================
# FONCTIONS DE TRAITEMENT
# =============================================================================

def convertir_dates(
    df: pd.DataFrame,
    colonnes: list[str],
    nom_table: str,
    format_date: str | None = None
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Convertit les colonnes de dates au type datetime.

    Args:
        df: DataFrame à modifier
        colonnes: Liste des noms de colonnes à convertir
        nom_table: Nom de la table (pour logging)
        format_date: Format de date optionnel (ex: "%Y-%m-%d %H:%M:%S")

    Returns:
        Tuple (DataFrame modifié, dictionnaire {colonne: nb_echecs})
    """
    df = df.copy()
    echecs = {}

    for col in colonnes:
        if col not in df.columns:
            logger.warning(f"[{nom_table}] Colonne de date absente : {col}")
            echecs[col] = -1
            continue

        avant = df[col].notna().sum()
        if format_date:
            df[col] = pd.to_datetime(df[col], format=format_date, errors="coerce")
        else:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        apres = df[col].notna().sum()
        nb_echecs = int(avant - apres)
        echecs[col] = nb_echecs

        if nb_echecs > 0:
            logger.warning(f"[{nom_table}] {col}: {nb_echecs} dates invalides converties en NaT")

    return df, echecs


def traiter_valeurs_manquantes_produits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Traite les valeurs manquantes dans la table produits.

    Stratégie :
    - product_category_name : imputé par "inconnu" (catégorie métier)
    - Colonnes numériques (longueur, description, photos, poids, dimensions) :
      imputées par la médiane de la catégorie si dispo, sinon médiane globale

    Args:
        df: DataFrame olist_products

    Returns:
        DataFrame avec valeurs manquantes traitées
    """
    df = df.copy()

    # product_category_name : imputation métier
    if "product_category_name" in df.columns:
        nb_avant = df["product_category_name"].isna().sum()
        df["product_category_name"] = df["product_category_name"].fillna("inconnu")
        logger.info(f"[olist_products] product_category_name: {nb_avant} valeurs manquantes imputées par 'inconnu'")

    # Colonnes numériques : imputation par médiane
    cols_numeriques = [
        "product_name_lenght", "product_description_lenght", "product_photos_qty",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"
    ]

    for col in cols_numeriques:
        if col in df.columns:
            nb_avant = df[col].isna().sum()
            if nb_avant > 0:
                # Essayer médiane par catégorie d'abord
                if "product_category_name" in df.columns:
                    medianes_par_cat = df.groupby("product_category_name")[col].transform("median")
                    df[col] = df[col].fillna(medianes_par_cat)

                # Puis médiane globale pour le reste
                mediane_globale = df[col].median()
                df[col] = df[col].fillna(mediane_globale)

                logger.info(f"[olist_products] {col}: {nb_avant} valeurs manquantes imputées (médiane)")

    return df


def traiter_valeurs_manquantes_commandes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Traite les valeurs manquantes dans la table commandes.

    Stratégie :
    - order_approved_at : manquants = commandes non approuvées (conservés en NaT)
    - order_delivered_carrier_date / order_delivered_customer_date :
      manquants = commandes non livrées (conservés en NaT)
    - order_estimated_delivery_date : pas de manquants détectés

    Args:
        df: DataFrame olist_orders

    Returns:
        DataFrame (inchangé, les NaT sont conservés intentionnellement)
    """
    # Les valeurs manquantes dans les dates de livraison/approuvation
    # correspondent à des états de commande légitimes (non livré, non approuvé)
    # On les conserve en NaT pour préserver l'information métier.
    logger.info("[olist_orders] Valeurs manquantes dans les dates conservées (états légitimes)")
    return df


def traiter_valeurs_manquantes_avis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Traite les valeurs manquantes dans la table avis.

    Stratégie :
    - review_comment_title / review_comment_message : facultatifs, conservés en NaN
    - review_score, review_creation_date, review_answer_timestamp : pas de manquants

    Args:
        df: DataFrame olist_order_reviews

    Returns:
        DataFrame (inchangé, commentaires facultatifs conservés)
    """
    logger.info("[olist_order_reviews] Commentaires facultatifs conservés en NaN")
    return df


def dedupliquer_geolocalisation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime les doublons complets de la table géolocalisation.

    La table géolocalisation contient de nombreux doublons complets
    (même code postal, même lat/lng, même ville, même état).
    La suppression est justifiée car ces doublons n'apportent aucune
    information supplémentaire pour les analyses géographiques.

    Args:
        df: DataFrame olist_geolocation

    Returns:
        DataFrame dédoublonné
    """
    nb_avant = len(df)
    df = df.drop_duplicates()
    nb_apres = len(df)
    nb_supprimes = nb_avant - nb_apres

    logger.info(f"[olist_geolocation] Doublons complets supprimés : {nb_supprimes} ({round(100*nb_supprimes/nb_avant, 2)}%)")
    return df


def verifier_valeurs_numeriques(
    df: pd.DataFrame,
    colonnes: list[str],
    nom_table: str,
    regles: dict[str, dict] | None = None
) -> dict[str, dict]:
    """
    Vérifie les valeurs numériques selon des règles métier.

    Args:
        df: DataFrame à vérifier
        colonnes: Liste des colonnes numériques à vérifier
        nom_table: Nom de la table
        regles: Dictionnaire de règles par colonne (min, max, etc.)

    Returns:
        Dictionnaire avec les anomalies détectées par colonne
    """
    regles_defaut = {
        "price": {"min": 0, "max": None},
        "freight_value": {"min": 0, "max": None},
        "payment_value": {"min": 0, "max": None},
        "payment_installments": {"min": 0, "max": 24},
        "review_score": {"min": 1, "max": 5},
        "product_weight_g": {"min": 0, "max": None},
        "product_length_cm": {"min": 0, "max": None},
        "product_height_cm": {"min": 0, "max": None},
        "product_width_cm": {"min": 0, "max": None},
        "product_name_lenght": {"min": 0, "max": None},
        "product_description_lenght": {"min": 0, "max": None},
        "product_photos_qty": {"min": 0, "max": None},
    }

    if regles:
        regles_defaut.update(regles)

    resultats = {}

    for col in colonnes:
        if col not in df.columns:
            continue

        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        serie = df[col].dropna()
        if serie.empty:
            continue

        regle = regles_defaut.get(col, {"min": None, "max": None})
        anomalies = {}

        # Valeurs négatives ou en dessous du min
        if regle.get("min") is not None:
            nb_inf = int((serie < regle["min"]).sum())
            if nb_inf > 0:
                anomalies[f"inf_{regle['min']}"] = nb_inf

        # Valeurs au-dessus du max
        if regle.get("max") is not None:
            nb_sup = int((serie > regle["max"]).sum())
            if nb_sup > 0:
                anomalies[f"sup_{regle['max']}"] = nb_sup

        # Valeurs nulles (si min > 0)
        if regle.get("min", 0) > 0:
            nb_nul = int((serie == 0).sum())
            if nb_nul > 0:
                anomalies["nulles"] = nb_nul

        # Quantiles pour détecter valeurs extrêmes (IQR)
        q25 = serie.quantile(0.25)
        q75 = serie.quantile(0.75)
        iqr = q75 - q25
        borne_sup = q75 + 1.5 * iqr
        nb_extremes = int((serie > borne_sup).sum())
        if nb_extremes > 0:
            anomalies["extremes_IQR"] = nb_extremes

        if anomalies:
            resultats[col] = anomalies
            logger.warning(f"[{nom_table}] {col}: anomalies détectées - {anomalies}")

    return resultats


def verifier_coherence_dates_commandes(df: pd.DataFrame) -> dict[str, int]:
    """
    Vérifie la cohérence logique des dates de commande.

    Règles :
    - order_approved_at >= order_purchase_timestamp
    - order_delivered_carrier_date >= order_approved_at
    - order_delivered_customer_date >= order_delivered_carrier_date
    - order_estimated_delivery_date >= order_purchase_timestamp

    Args:
        df: DataFrame olist_orders avec colonnes de dates en datetime

    Returns:
        Dictionnaire avec le nombre d'incohérences par règle
    """
    incoherences = {}

    # Approuvé après achat
    if all(c in df.columns for c in ["order_approved_at", "order_purchase_timestamp"]):
        mask = (df["order_approved_at"].notna() & df["order_purchase_timestamp"].notna() &
                (df["order_approved_at"] < df["order_purchase_timestamp"]))
        incoherences["approuve_avant_achat"] = int(mask.sum())

    # Livré transporteur après approuvé
    if all(c in df.columns for c in ["order_delivered_carrier_date", "order_approved_at"]):
        mask = (df["order_delivered_carrier_date"].notna() & df["order_approved_at"].notna() &
                (df["order_delivered_carrier_date"] < df["order_approved_at"]))
        incoherences["livre_transporteur_avant_approuve"] = int(mask.sum())

    # Livré client après transporteur
    if all(c in df.columns for c in ["order_delivered_customer_date", "order_delivered_carrier_date"]):
        mask = (df["order_delivered_customer_date"].notna() & df["order_delivered_carrier_date"].notna() &
                (df["order_delivered_customer_date"] < df["order_delivered_carrier_date"]))
        incoherences["livre_client_avant_transporteur"] = int(mask.sum())

    # Estimée après achat
    if all(c in df.columns for c in ["order_estimated_delivery_date", "order_purchase_timestamp"]):
        mask = (df["order_estimated_delivery_date"].notna() & df["order_purchase_timestamp"].notna() &
                (df["order_estimated_delivery_date"] < df["order_purchase_timestamp"]))
        incoherences["estimee_avant_achat"] = int(mask.sum())

    # Livré client après estimée (retard)
    if all(c in df.columns for c in ["order_delivered_customer_date", "order_estimated_delivery_date"]):
        mask = (df["order_delivered_customer_date"].notna() & df["order_estimated_delivery_date"].notna() &
                (df["order_delivered_customer_date"] > df["order_estimated_delivery_date"]))
        incoherences["retard_livraison"] = int(mask.sum())

    for regle, nb in incoherences.items():
        if nb > 0:
            logger.warning(f"[olist_orders] Incohérence '{regle}': {nb} cas")

    return incoherences


def preparer_table(
    df: pd.DataFrame,
    nom_table: str,
    tables_ref: dict[str, pd.DataFrame] | None = None
) -> tuple[pd.DataFrame, dict]:
    """
    Fonction principale de préparation d'une table.

    Args:
        df: DataFrame brut
        nom_table: Nom de la table
        tables_ref: Dictionnaire des autres tables pour vérifications croisées

    Returns:
        Tuple (DataFrame nettoyé, dictionnaire de métriques)
    """
    logger.info(f"=== Préparation de {nom_table} ===")
    metrics = {"table": nom_table, "lignes_initial": len(df), "colonnes_initial": len(df.columns)}

    df_clean = df.copy()

    # 1. Conversion des dates
    if nom_table in COLONNES_DATES:
        df_clean, echecs_dates = convertir_dates(df_clean, COLONNES_DATES[nom_table], nom_table)
        metrics["dates_conversion_echecs"] = echecs_dates

    # 2. Traitement spécifique par table
    if nom_table == "olist_products":
        df_clean = traiter_valeurs_manquantes_produits(df_clean)
    elif nom_table == "olist_orders":
        df_clean = traiter_valeurs_manquantes_commandes(df_clean)
        # Vérification cohérence dates après conversion
        if tables_ref is None or "olist_orders" in tables_ref:
            incoherences = verifier_coherence_dates_commandes(df_clean)
            metrics["incoherences_dates"] = incoherences
    elif nom_table == "olist_order_reviews":
        df_clean = traiter_valeurs_manquantes_avis(df_clean)
    elif nom_table == "olist_geolocation":
        df_clean = dedupliquer_geolocalisation(df_clean)

    # 3. Vérification valeurs numériques
    if nom_table in COLONNES_NUMERIQUES_METIER:
        anomalies = verifier_valeurs_numeriques(
            df_clean, COLONNES_NUMERIQUES_METIER[nom_table], nom_table
        )
        metrics["anomalies_numeriques"] = anomalies

    # 4. Vérification clés primaires
    if nom_table in CLES_PRIMAIRES_ATTENDUES:
        cles_df = verifier_cle_primaire(df_clean, CLES_PRIMAIRES_ATTENDUES[nom_table], nom_table)
        metrics["verification_cles"] = cles_df.to_dict("records")

    metrics["lignes_final"] = len(df_clean)
    metrics["colonnes_final"] = len(df_clean.columns)
    metrics["lignes_supprimees"] = metrics["lignes_initial"] - metrics["lignes_final"]

    logger.info(f"=== {nom_table} terminé : {metrics['lignes_initial']} -> {metrics['lignes_final']} lignes ===")
    return df_clean, metrics


def preparer_toutes_tables(tables: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """
    Prépare toutes les tables du dataset.

    Args:
        tables: Dictionnaire {nom_table: DataFrame_brut}

    Returns:
        Tuple (dictionnaire tables nettoyées, liste des métriques)
    """
    tables_clean = {}
    all_metrics = []

    # Ordre de traitement : tables de référence d'abord
    ordre_traitement = [
        "olist_customers",
        "olist_products",
        "olist_sellers",
        "product_category_name_translation",
        "olist_orders",
        "olist_order_items",
        "olist_order_payments",
        "olist_order_reviews",
        "olist_geolocation",
    ]

    for nom in ordre_traitement:
        if nom in tables:
            df_clean, metrics = preparer_table(tables[nom], nom, tables_clean)
            tables_clean[nom] = df_clean
            all_metrics.append(metrics)

    return tables_clean, all_metrics


# =============================================================================
# FONCTIONS D'EXPORT ET VALIDATION
# =============================================================================

def exporter_tables_propres(
    tables: dict[str, pd.DataFrame],
    dossier_sortie: Path,
    suffixe: str = "_clean",
    encoding: str = "utf-8"
) -> list[Path]:
    """
    Exporte les tables nettoyées en CSV.

    Args:
        tables: Dictionnaire {nom_table: DataFrame}
        dossier_sortie: Chemin du dossier de sortie
        suffixe: Suffixe à ajouter aux noms de fichiers
        encoding: Encodage du CSV

    Returns:
        Liste des chemins des fichiers créés
    """
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    fichiers_crees = []

    for nom, df in tables.items():
        nom_fichier = f"{nom}{suffixe}.csv"
        chemin = dossier_sortie / nom_fichier
        df.to_csv(chemin, index=False, encoding=encoding)
        fichiers_crees.append(chemin)
        logger.info(f"Exporté : {chemin} ({len(df):,} lignes × {len(df.columns)} colonnes)")

    return fichiers_crees


def valider_export(
    tables: dict[str, pd.DataFrame],
    dossier_sortie: Path,
    suffixe: str = "_clean"
) -> pd.DataFrame:
    """
    Valide que les fichiers exportés sont lisibles et cohérents.

    Args:
        tables: Dictionnaire original des tables nettoyées
        dossier_sortie: Dossier des exports
        suffixe: Suffixe utilisé à l'export

    Returns:
        DataFrame avec les résultats de validation
    """
    rows = []

    for nom, df_original in tables.items():
        chemin = dossier_sortie / f"{nom}{suffixe}.csv"

        if not chemin.exists():
            rows.append({
                "table": nom,
                "statut": "FICHIER_MANQUANT",
                "lignes_original": len(df_original),
                "lignes_rechargees": None,
                "colonnes_original": len(df_original.columns),
                "colonnes_rechargees": None,
                "identique": False
            })
            continue

        try:
            df_recharge = pd.read_csv(chemin, encoding="utf-8")
            identiques = (
                len(df_recharge) == len(df_original) and
                list(df_recharge.columns) == list(df_original.columns) and
                df_recharge.dtypes.equals(df_original.dtypes)
            )

            rows.append({
                "table": nom,
                "statut": "OK" if identiques else "DIFFERENT",
                "lignes_original": len(df_original),
                "lignes_rechargees": len(df_recharge),
                "colonnes_original": len(df_original.columns),
                "colonnes_rechargees": len(df_recharge.columns),
                "identique": identiques
            })
        except Exception as e:
            rows.append({
                "table": nom,
                "statut": f"ERREUR_LECTURE: {e}",
                "lignes_original": len(df_original),
                "lignes_rechargees": None,
                "colonnes_original": len(df_original.columns),
                "colonnes_rechargees": None,
                "identique": False
            })

    return pd.DataFrame(rows)


def generer_rapport_comparaison(
    tables_brutes: dict[str, pd.DataFrame],
    tables_propres: dict[str, pd.DataFrame],
    metrics: list[dict]
) -> pd.DataFrame:
    """
    Génère un tableau comparatif avant/après nettoyage.

    Args:
        tables_brutes: Tables originales
        tables_propres: Tables nettoyées
        metrics: Liste des métriques de préparation

    Returns:
        DataFrame comparatif
    """
    rows = []

    for m in metrics:
        nom = m["table"]
        df_brut = tables_brutes.get(nom)
        df_propre = tables_propres.get(nom)

        if df_brut is None or df_propre is None:
            continue

        # Doublons complets avant/après
        doublons_avant = int(df_brut.duplicated().sum())
        doublons_apres = int(df_propre.duplicated().sum())

        # Valeurs manquantes avant/après
        missing_avant = int(df_brut.isna().sum().sum())
        missing_apres = int(df_propre.isna().sum().sum())

        rows.append({
            "table": nom,
            "lignes_avant": m["lignes_initial"],
            "lignes_apres": m["lignes_final"],
            "lignes_supprimees": m["lignes_supprimees"],
            "colonnes_avant": m["colonnes_initial"],
            "colonnes_apres": m["colonnes_final"],
            "doublons_complets_avant": doublons_avant,
            "doublons_complets_apres": doublons_apres,
            "valeurs_manquantes_avant": missing_avant,
            "valeurs_manquantes_apres": missing_apres,
            "dates_conversion_echecs": m.get("dates_conversion_echecs", {}),
            "anomalies_numeriques": m.get("anomalies_numeriques", {}),
            "incoherences_dates": m.get("incoherences_dates", {}),
        })

    return pd.DataFrame(rows)