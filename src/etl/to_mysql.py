# Export data to MySQL

import csv
import mysql.connector

from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from itertools import islice


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "olist_db"
}

BATCH_SIZE = 5000
GEO_DECIMAL_PLACES = Decimal("0.0000001")


# ============================================================
# 2. CONFIGURATION DES 9 TABLES
# ============================================================

TABLES = [
    {
        "table": "customers",
        "file": "olist_customers_clean.csv",
        "columns": [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state"
        ],
        "key": ["customer_id"]
    },
    {
        "table": "geolocation",
        "file": "olist_geolocation_clean.csv",
        "columns": [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state"
        ],
        "key": None
    },
    {
        "table": "sellers",
        "file": "olist_sellers_clean.csv",
        "columns": [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state"
        ],
        "key": ["seller_id"]
    },
    {
        "table": "category_translation",
        "file": "product_category_name_translation_clean.csv",
        "columns": [
            "product_category_name",
            "product_category_name_english"
        ],
        "key": ["product_category_name"],
        "preserve_extra": True
    },
    {
        "table": "products",
        "file": "olist_products_clean.csv",
        "columns": [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm"
        ],
        "key": ["product_id"]
    },
    {
        "table": "orders",
        "file": "olist_orders_clean.csv",
        "columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ],
        "key": ["order_id"]
    },
    {
        "table": "order_items",
        "file": "olist_order_items_clean.csv",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value"
        ],
        "key": ["order_id", "order_item_id"]
    },
    {
        "table": "order_payments",
        "file": "olist_order_payments_clean.csv",
        "columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value"
        ],
        "key": ["order_id", "payment_sequential"]
    },
    {
        "table": "order_reviews",
        "file": "olist_order_reviews_clean.csv",
        "columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp"
        ],
        "key": ["review_id", "order_id"]
    }
]


# ============================================================
# 3. CONNEXION MYSQL
# ============================================================

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# 4. VALIDATION DES FICHIERS CSV
# ============================================================

def validate_files():

    print("\nVALIDATION DES FICHIERS CSV")

    for config in TABLES:

        file_path = DATA_DIR / config["file"]

        if not file_path.exists():
            raise FileNotFoundError(
                f"Fichier introuvable : {file_path}"
            )

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.reader(file)
            header = next(reader, None)

            if header != config["columns"]:
                raise ValueError(
                    f"Colonnes incorrectes dans {config['file']}\n"
                    f"Attendu : {config['columns']}\n"
                    f"Trouvé : {header}"
                )

        print(f"OK : {config['file']}")


# ============================================================
# 5. NETTOYAGE DES VALEURS
# ============================================================

def clean_value(value):

    value = value.strip()

    if value == "":
        return None

    return value


# ============================================================
# 6. LECTURE DES CSV PAR BATCH
# ============================================================

def read_batches(file_path, columns):

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)
        header = next(reader, None)

        if header != columns:
            raise ValueError(
                f"En-tête incorrect dans {file_path.name}"
            )

        while True:

            rows = list(islice(reader, BATCH_SIZE))

            if not rows:
                break

            batch = []

            for row in rows:

                if len(row) != len(columns):
                    raise ValueError(
                        f"Ligne CSV invalide : {row}"
                    )

                batch.append(
                    tuple(clean_value(v) for v in row)
                )

            yield batch


# ============================================================
# 7. COMPTAGE DES LIGNES
# ============================================================

def get_table_count(cursor, table):

    cursor.execute(
        f"SELECT COUNT(*) FROM `{table}`"
    )

    return cursor.fetchone()[0]


def count_csv_rows(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)
        next(reader, None)

        return sum(1 for row in reader if row)


# ============================================================
# 8. NORMALISATION DES VALEURS
# ============================================================

def normalize_value(value):

    if value is None:
        return None

    if isinstance(value, (Decimal, int, float)):

        try:
            return Decimal(str(value)).quantize(
                GEO_DECIMAL_PLACES,
                rounding=ROUND_HALF_UP
            )

        except InvalidOperation:
            return str(value)

    if isinstance(value, str):

        try:
            return Decimal(value).quantize(
                GEO_DECIMAL_PLACES,
                rounding=ROUND_HALF_UP
            )

        except InvalidOperation:
            return value.strip()

    return str(value)


# ============================================================
# 9. VERIFICATION DE GEOLOCATION
# ============================================================

def verify_geolocation_prefix(
    cursor,
    file_path,
    columns,
    existing_count
):

    if existing_count == 0:
        return

    print(
        "\nVérification des lignes geolocation existantes..."
    )

    column_names = ", ".join(
        f"`{column}`" for column in columns
    )

    checked = 0

    for batch in read_batches(file_path, columns):

        if checked >= existing_count:
            break

        number_to_check = min(
            len(batch),
            existing_count - checked
        )

        expected_rows = batch[:number_to_check]

        cursor.execute(
            f"""
            SELECT {column_names}
            FROM geolocation
            WHERE id BETWEEN %s AND %s
            ORDER BY id
            """,
            (
                checked + 1,
                checked + number_to_check
            )
        )

        actual_rows = cursor.fetchall()

        if len(actual_rows) != number_to_check:
            raise RuntimeError(
                "Nombre de lignes incorrect pendant "
                "la vérification de geolocation."
            )

        for index, (expected, actual) in enumerate(
            zip(expected_rows, actual_rows)
        ):

            expected_normalized = tuple(
                normalize_value(v) for v in expected
            )

            actual_normalized = tuple(
                normalize_value(v) for v in actual
            )

            if expected_normalized != actual_normalized:

                raise RuntimeError(
                    "Les données geolocation existantes "
                    "ne correspondent pas au début du CSV. "
                    f"Différence à la ligne ID "
                    f"{checked + index + 1}. "
                    "Importation arrêtée."
                )

        checked += number_to_check

    if checked != existing_count:
        raise RuntimeError(
            "Le nombre de lignes vérifiées est incorrect."
        )

    print(
        f"OK : {checked:,} lignes existantes correspondent au CSV."
    )


# ============================================================
# 10. VERIFICATION DE CATEGORY_TRANSLATION
# ============================================================

def verify_category_translation(
    cursor,
    file_path,
    columns
):

    print(
        "\nVérification de category_translation..."
    )

    expected_rows = set()

    for batch in read_batches(file_path, columns):
        expected_rows.update(batch)

    column_names = ", ".join(
        f"`{column}`" for column in columns
    )

    cursor.execute(
        f"""
        SELECT {column_names}
        FROM category_translation
        """
    )

    actual_rows = set(cursor.fetchall())

    missing = expected_rows - actual_rows

    if missing:

        raise RuntimeError(
            f"Catégories CSV manquantes : {len(missing)}. "
            "Vérification manuelle nécessaire."
        )

    print(
        f"OK : {len(expected_rows):,} catégories CSV vérifiées."
    )


# ============================================================
# 11. VERIFICATION DE L'EXISTANT
# ============================================================

def compare_existing_table(cursor, config):

    table = config["table"]
    file_path = DATA_DIR / config["file"]

    existing_count = get_table_count(cursor, table)
    csv_count = count_csv_rows(file_path)

    print(f"\nTable : {table}")
    print(f"MySQL : {existing_count:,}")
    print(f"CSV   : {csv_count:,}")

    if existing_count == 0:
        return "EMPTY"

    # CATEGORY_TRANSLATION

    if table == "category_translation":

        verify_category_translation(
            cursor,
            file_path,
            config["columns"]
        )

        if existing_count < csv_count:
            raise RuntimeError(
                "category_translation contient moins de lignes "
                "que le CSV."
            )

        return "PRESERVE_EXTRA"

    # GEOLOCATION

    if table == "geolocation":

        cursor.execute(
            "SELECT MIN(id), MAX(id) FROM geolocation"
        )

        min_id, max_id = cursor.fetchone()

        if min_id != 1 or max_id != existing_count:
            raise RuntimeError(
                "Les IDs de geolocation ne sont pas continus."
            )

        if existing_count > csv_count:
            raise RuntimeError(
                "La table geolocation contient plus de lignes "
                "que le CSV."
            )

        verify_geolocation_prefix(
            cursor,
            file_path,
            config["columns"],
            existing_count
        )

        if existing_count == csv_count:
            return "COMPLETE"

        return "PARTIAL"

    # AUTRES TABLES

    if existing_count != csv_count:

        raise RuntimeError(
            f"Nombre de lignes différent pour {table}. "
            "Arrêt pour éviter une importation incorrecte."
        )

    return "COMPLETE"


# ============================================================
# 12. IMPORTATION D'UNE TABLE
# ============================================================

def import_table(cursor, conn, config):

    table = config["table"]
    file_path = DATA_DIR / config["file"]
    columns = config["columns"]

    status = compare_existing_table(cursor, config)

    if status == "COMPLETE":

        print(
            "Table déjà complète : aucune importation."
        )

        return

    if status == "PRESERVE_EXTRA":

        print(
            "Catégories supplémentaires conservées. "
            "Aucune importation effectuée."
        )

        return

    if status == "PARTIAL" and table != "geolocation":

        raise RuntimeError(
            f"Import partiel non pris en charge pour {table}."
        )

    column_names = ", ".join(
        f"`{column}`" for column in columns
    )

    placeholders = ", ".join(
        ["%s"] * len(columns)
    )

    sql = (
        f"INSERT INTO `{table}` ({column_names}) "
        f"VALUES ({placeholders})"
    )

    imported = 0
    existing_rows = 0

    if table == "geolocation" and status == "PARTIAL":
        existing_rows = get_table_count(cursor, table)

    print("Début de l'importation...")

    try:

        for batch in read_batches(file_path, columns):

            # Ignorer les lignes déjà importées
            if table == "geolocation" and status == "PARTIAL":

                if existing_rows >= len(batch):

                    existing_rows -= len(batch)
                    continue

                if existing_rows > 0:

                    batch = batch[existing_rows:]
                    existing_rows = 0

            if not batch:
                continue

            cursor.executemany(sql, batch)

            conn.commit()

            imported += len(batch)

            print(
                f"{imported:,} nouvelles lignes importées..."
            )

        print(
            f"Import terminé : {imported:,} lignes."
        )

    except Exception:

        conn.rollback()
        raise

    final_count = get_table_count(cursor, table)

    print(
        f"Total MySQL : {final_count:,}"
    )

    expected_count = count_csv_rows(file_path)

    if final_count != expected_count:

        raise RuntimeError(
            f"Nombre final incorrect pour {table}. "
            f"Attendu : {expected_count:,}, "
            f"Trouvé : {final_count:,}."
        )


# ============================================================
# 13. VERIFICATION FINALE
# ============================================================

def final_verification(cursor):

    print("\n" + "=" * 65)
    print("VERIFICATION FINALE DES TABLES")
    print("=" * 65)

    for config in TABLES:

        table = config["table"]
        file_path = DATA_DIR / config["file"]

        mysql_count = get_table_count(cursor, table)
        csv_count = count_csv_rows(file_path)

        # CATEGORY_TRANSLATION

        if table == "category_translation":

            verify_category_translation(
                cursor,
                file_path,
                config["columns"]
            )

            valid = mysql_count >= csv_count

        else:

            valid = mysql_count == csv_count

        # GEOLOCATION

        if table == "geolocation" and valid:

            cursor.execute(
                "SELECT MIN(id), MAX(id) FROM geolocation"
            )

            min_id, max_id = cursor.fetchone()

            valid = (
                min_id == 1
                and max_id == mysql_count
            )

        status = "OK" if valid else "ERREUR"

        print(
            f"{table:25} | "
            f"CSV: {csv_count:>9,} | "
            f"MySQL: {mysql_count:>9,} | "
            f"{status}"
        )

        if not valid:

            raise RuntimeError(
                f"Vérification échouée pour {table}."
            )


# ============================================================
# 14. MAIN
# ============================================================

def main():

    conn = None
    cursor = None

    try:

        print("=" * 65)
        print("ETL OLIST - CSV VERS MYSQL")
        print("=" * 65)

        # Validation des fichiers
        validate_files()

        # Connexion
        print("\nConnexion à MySQL...")

        conn = get_connection()
        cursor = conn.cursor()

        print(
            "Connexion réussie à olist_db."
        )

        # Importation des 9 tables
        for config in TABLES:

            import_table(
                cursor,
                conn,
                config
            )

        # Vérification finale
        final_verification(cursor)

        print("\n" + "=" * 65)
        print("ETL TERMINÉ AVEC SUCCÈS.")
        print("=" * 65)

    except Exception as error:

        if conn is not None:
            conn.rollback()

        print(
            "\nERREUR ETL :",
            error
        )

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()

        print(
            "\nConnexion MySQL fermée."
        )


if __name__ == "__main__":
    main()
