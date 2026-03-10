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
    ("TESSUTI TESSILI",   "STT0962A0"),
    ("TESSUTI TESSILI",   "STT0845B1"),
    ("TESSUTI TESSILI",   "STT1120C3"),
    ("TESSUTI TESSILI",   "STT0500D2"),
    ("TESSUTI TESSILI",   "STT0773E4"),
    ("TESSUTI METALLICI", "STM0210A0"),
    ("TESSUTI METALLICI", "STM0315B1"),
    ("TESSUTI METALLICI", "STM0428C2"),
    ("TESSUTI METALLICI", "STM0590D3"),
    ("TESSUTI METALLICI", "STM0102E4"),
    ("BANDINE",           "STR0100A0"),
    ("BANDINE",           "STR0250B1"),
    ("BANDINE",           "STR0375C2"),
    ("BANDINE",           "STR0480D3"),
    ("BANDINE",           "STR0620E4"),
    ("ALTRO",             "ALT0010A0"),
    ("ALTRO",             "ALT0020B1"),
    ("ALTRO",             "ALT0030C2"),
    ("ALTRO",             "ALT0040D3"),
    ("ALTRO",             "ALT0050E4"),
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
                data_produzione        TEXT    NOT NULL,
                operatore              TEXT    NOT NULL DEFAULT ''
            )
        """)
        # Aggiunge la colonna operatore se il database esiste già senza di essa
        try:
            cursor.execute("ALTER TABLE Flussi_Ingresso ADD COLUMN operatore TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise

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


def lookup_categoria_by_codice(codice: str) -> str | None:
    """
    Cerca il codice articolo esatto in Materiali_Anagrafica e
    restituisce la categoria corrispondente, o None se non trovata.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT categoria FROM Materiali_Anagrafica WHERE codice_articolo = ? LIMIT 1",
            (codice,),
        )
        row = cursor.fetchone()
        return row["categoria"] if row else None


def get_all_codici() -> list[str]:
    """
    Restituisce tutti i codici articolo presenti in Materiali_Anagrafica
    (usato per popolare il completatore nella schermata di scansione).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT codice_articolo FROM Materiali_Anagrafica ORDER BY codice_articolo")
        return [row["codice_articolo"] for row in cursor.fetchall()]


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
    operatore: str = "",
) -> int:
    """
    Inserisce un nuovo record in Flussi_Ingresso.
    Restituisce l'ID del record appena creato.

    :param data_produzione: stringa in formato ISO (YYYY-MM-DD)
    :param operatore: nome dell'operatore che effettua l'accettazione
    """
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Flussi_Ingresso
                (timestamp_accettazione, categoria, codice_articolo, lotto_id, data_produzione, operatore)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, categoria, codice_articolo, lotto_id, data_produzione, operatore),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_flussi(limit: int = 500) -> list[dict]:
    """
    Restituisce i `limit` record più recenti da Flussi_Ingresso,
    ordinati per timestamp_accettazione DESC (più recenti prima).
    Ogni riga è restituita come dizionario.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp_accettazione, operatore, categoria,
                   codice_articolo, lotto_id, data_produzione
            FROM Flussi_Ingresso
            ORDER BY timestamp_accettazione DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_flusso(record_id: int) -> bool:
    """
    Elimina un singolo record da Flussi_Ingresso per ID.
    Restituisce True se una riga è stata eliminata, False altrimenti.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Flussi_Ingresso WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_flussi_count() -> int:
    """Restituisce il conteggio totale dei record in Flussi_Ingresso."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Flussi_Ingresso")
        return cursor.fetchone()[0]