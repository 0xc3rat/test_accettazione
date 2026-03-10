"""
database.py – Logica SQLite per il Sistema di Accettazione Rinforzi.
Gestisce: creazione tabelle, seed dati, lettura anagrafica, scrittura flussi.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "accettazione.db"

# ---------------------------------------------------------------------------
# Seed data: almeno 5 codici per categoria
# ---------------------------------------------------------------------------
_SEED_DATA = [
    # (categoria, codice_articolo)
    ("TESSUTI TESSILI",   "TT-001"),
    ("TESSUTI TESSILI",   "TT-002"),
    ("TESSUTI TESSILI",   "TT-003"),
    ("TESSUTI TESSILI",   "TT-004"),
    ("TESSUTI TESSILI",   "TT-005"),
    ("TESSUTI METALLICI", "TM-001"),
    ("TESSUTI METALLICI", "TM-002"),
    ("TESSUTI METALLICI", "TM-003"),
    ("TESSUTI METALLICI", "TM-004"),
    ("TESSUTI METALLICI", "TM-005"),
    ("BANDINE",           "BA-001"),
    ("BANDINE",           "BA-002"),
    ("BANDINE",           "BA-003"),
    ("BANDINE",           "BA-004"),
    ("BANDINE",           "BA-005"),
    ("ALTRO",             "AL-001"),
    ("ALTRO",             "AL-002"),
    ("ALTRO",             "AL-003"),
    ("ALTRO",             "AL-004"),
    ("ALTRO",             "AL-005"),
]


def get_connection() -> sqlite3.Connection:
    """Apre (o crea) il database e restituisce la connessione."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """
    Crea le tabelle se non esistono e inserisce i dati seed
    nella Materiali_Anagrafica solo se vuota.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # ---- Tabella principale log ingressi ----
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Flussi_Ingresso (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_accettazione TEXT    NOT NULL,
                categoria              TEXT    NOT NULL,
                codice_articolo        TEXT    NOT NULL,
                lotto_id               TEXT    NOT NULL,
                data_produzione        TEXT    NOT NULL
            )
        """)

        # ---- Tabella anagrafica materiali ----
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Materiali_Anagrafica (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria       TEXT NOT NULL,
                codice_articolo TEXT NOT NULL
            )
        """)

        # Seed solo se vuota
        cursor.execute("SELECT COUNT(*) FROM Materiali_Anagrafica")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Materiali_Anagrafica (categoria, codice_articolo) VALUES (?, ?)",
                _SEED_DATA,
            )

        conn.commit()


def get_codici_by_categoria(categoria: str) -> list[str]:
    """
    Restituisce la lista dei codici articolo per la categoria indicata,
    usata per popolare il QComboBox con auto-completamento.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT codice_articolo FROM Materiali_Anagrafica WHERE categoria = ? ORDER BY codice_articolo",
            (categoria,),
        )
        return [row["codice_articolo"] for row in cursor.fetchall()]


def insert_flusso(
    categoria: str,
    codice_articolo: str,
    lotto_id: str,
    data_produzione: str,
) -> int:
    """
    Inserisce un nuovo record in Flussi_Ingresso.
    Restituisce l'ID del record appena creato.

    :param data_produzione: stringa in formato ISO (YYYY-MM-DD)
    """
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Flussi_Ingresso
                (timestamp_accettazione, categoria, codice_articolo, lotto_id, data_produzione)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, categoria, codice_articolo, lotto_id, data_produzione),
        )
        conn.commit()
        return cursor.lastrowid