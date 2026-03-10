"""
main.py – Entry-point del Sistema di Accettazione Rinforzi.

Esecuzione:
    python main.py

Al primo avvio crea automaticamente il database SQLite (accettazione.db)
nella stessa directory dello script.
"""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from database import initialize_database
from ui import MainWindow


def main() -> None:
    # 1. Inizializza il database (crea tabelle e seed data se necessario)
    initialize_database()

    # 2. Avvia l'applicazione Qt
    app = QApplication(sys.argv)

    # Font di default per tutta l'applicazione
    default_font = QFont("Segoe UI", 11)
    app.setFont(default_font)

    # 3. Crea e mostra la finestra principale
    window = MainWindow()
    window.show()

    # 4. Avvia il loop degli eventi
    sys.exit(app.exec())


if __name__ == "__main__":
    main()