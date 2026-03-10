"""
ui.py – Componenti UI PySide6 per il Sistema di Accettazione Rinforzi.

Struttura:
  • CATEGORY_CONFIG  – dizionario di configurazione estensibile per categoria
  • PREFIX_RULES     – regole di rilevamento per prefisso codice
  • KEYWORD_RULES    – regole di rilevamento per parole chiave
  • detect_categoria – pipeline di auto-rilevamento categoria
  • RegistroScreen   – Schermata visualizzazione/eliminazione registrazioni
  • MainWindow       – Finestra unica con QStackedWidget (accettazione + registro)
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QDate, QTimer, QObject, QEvent
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCompleter,
    QMessageBox,
    QFrame,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from database import (
    get_all_codici,
    get_all_flussi,
    get_flussi_count,
    delete_flusso,
    insert_flusso,
    lookup_categoria_by_codice,
)

# ---------------------------------------------------------------------------
# CATEGORY_CONFIG – estensibile: aggiungere una nuova categoria = aggiungere
# una chiave qui + seed data in database.py, nessun'altra modifica richiesta.
# ---------------------------------------------------------------------------
CATEGORY_CONFIG: dict[str, dict] = {
    "TESSUTI TESSILI": {
        "colore": "#1565C0",   # blu
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo",    "tipo": "scan_input",  "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°",           "tipo": "lineedit",    "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "TESSUTI METALLICI": {
        "colore": "#2E7D32",   # verde
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo",    "tipo": "scan_input",  "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°",           "tipo": "lineedit",    "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "BANDINE": {
        "colore": "#E65100",   # arancione
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo",    "tipo": "scan_input",  "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°",           "tipo": "lineedit",    "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "ALTRO": {
        "colore": "#424242",   # grigio scuro
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo",    "tipo": "scan_input",  "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°",           "tipo": "lineedit",    "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
}

# ---------------------------------------------------------------------------
# Regole di rilevamento automatico (config-driven)
# ---------------------------------------------------------------------------

# Prefissi: il codice inizia con questo prefisso → categoria
PREFIX_RULES: list[tuple[str, str]] = [
    ("STT", "TESSUTI TESSILI"),
    ("STM", "TESSUTI METALLICI"),
    ("STR", "BANDINE"),
    ("ALT", "ALTRO"),
]

# Parole chiave: se il testo contiene questa stringa → categoria
KEYWORD_RULES: dict[str, str] = {
    "tessile": "TESSUTI TESSILI",
    "tessuto tessile": "TESSUTI TESSILI",
    "metallico": "TESSUTI METALLICI",
    "tessuto metallico": "TESSUTI METALLICI",
    "bandina": "BANDINE",
    "bandine": "BANDINE",
}

# ---------------------------------------------------------------------------
# Separatori barcode (ordine di priorità per lo split automatico)
# ---------------------------------------------------------------------------
# Regex per split "sicuro" sul trattino: almeno 4 char prima del separatore,
# e il separatore deve essere l'ULTIMO trattino → evita "STT-001" split errato.
_DASH_SPLIT_RE = re.compile(r'^(.{4,})-([^-]+)$')


def _parse_barcode(text: str) -> tuple[str, str | None]:
    """
    Prova a splittare il testo del barcode in (codice, lotto).
    Ordine di priorità:
      1. TAB  (\t) → split sul primo tab
      2. PIPE (|)  → split sul primo pipe
      3. SEMICOLONNA (;) → split sul primo punto-e-virgola
      4. TRATTINO (-) → split sull'ultimo trattino, solo se ≥4 char prima
    Restituisce (codice, None) se nessun separatore rilevato.
    """
    if '\t' in text:
        parts = text.split('\t', 1)
        return parts[0].strip(), parts[1].strip()
    if '|' in text:
        parts = text.split('|', 1)
        return parts[0].strip(), parts[1].strip()
    if ';' in text:
        parts = text.split(';', 1)
        return parts[0].strip(), parts[1].strip()
    m = _DASH_SPLIT_RE.match(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, None


def detect_categoria(codice: str) -> str | None:
    """
    Pipeline di auto-rilevamento categoria (priorità decrescente):
    1. Lookup esatto in Materiali_Anagrafica (SQLite)
    2. Regole prefisso (case-insensitive)
    3. Regole parole chiave (case-insensitive contains)
    4. None → fallback manuale nell'UI
    """
    if not codice:
        return None

    # 1. Lookup esatto nel database
    cat = lookup_categoria_by_codice(codice)
    if cat:
        return cat

    # 2. Regole prefisso (PREFIX_RULES usa già maiuscole)
    upper = codice.upper()
    for prefix, categoria in PREFIX_RULES:
        if upper.startswith(prefix):
            return categoria

    # 3. Regole parole chiave (KEYWORD_RULES usa già minuscole)
    lower = codice.lower()
    for keyword, categoria in KEYWORD_RULES.items():
        if keyword in lower:
            return categoria

    return None


# ---------------------------------------------------------------------------
# Costanti di stile
# ---------------------------------------------------------------------------
_FONT_TITLE    = QFont("Segoe UI", 26, QFont.Bold)
_FONT_SUBTITLE = QFont("Segoe UI", 12)
_FONT_LABEL    = QFont("Segoe UI", 14, QFont.Bold)
_FONT_FIELD    = QFont("Segoe UI", 16)
_FONT_SCAN     = QFont("Segoe UI", 18)
_FONT_SAVE     = QFont("Segoe UI", 18, QFont.Bold)
_FONT_BADGE    = QFont("Segoe UI", 13, QFont.Bold)
_FONT_TOAST    = QFont("Segoe UI", 15, QFont.Bold)
_FONT_TABLE    = QFont("Segoe UI", 12)
_FONT_TABLE_HDR = QFont("Segoe UI", 12, QFont.Bold)

_TOAST_SUCCESS_DURATION_MS = 2500
_TOAST_ERROR_DURATION_MS   = 3000


def _field_style(border_color: str = "#90a4ae") -> str:
    return f"""
        background-color: #ffffff;
        border: 2px solid {border_color};
        border-radius: 6px;
        padding: 4px 8px;
        color: #1a1a2e;
    """


# ---------------------------------------------------------------------------
# Event filter per catturare Enter su QDateEdit
# ---------------------------------------------------------------------------
class _DateEditEnterFilter(QObject):
    """Installa un event filter su QDateEdit per catturare Return/Enter."""

    def __init__(self, callback, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._callback()
                return True
        return super().eventFilter(obj, event)


# ===========================================================================
# RegistroScreen – Schermata visualizzazione e gestione registrazioni
# ===========================================================================
class RegistroScreen(QWidget):
    """
    Schermata di sola lettura per visualizzare, filtrare ed eliminare
    le registrazioni presenti in Flussi_Ingresso.
    """

    # Colonne della tabella (label visibile, chiave nel dict del record)
    _COLUMNS = [
        ("ID",              "id"),
        ("Data / Ora",      "timestamp_accettazione"),
        ("Operatore",       "operatore"),
        ("Categoria",       "categoria"),
        ("Codice Articolo", "codice_articolo"),
        ("Lotto N°",        "lotto_id"),
        ("Data Produzione", "data_produzione"),
    ]

    def __init__(self, on_back, show_toast_fn, parent=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._show_toast = show_toast_fn
        self._all_records: list[dict] = []
        self._build_ui()

        # Shortcut Escape per tornare all'accettazione
        sc_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        sc_esc.activated.connect(self._on_back)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setStyleSheet("background-color: #f5f5f5;")
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 20, 40, 20)
        root.setSpacing(12)

        # ---- Toast (condiviso tramite callback, ma ne serve uno locale) ----
        self._toast = QLabel()
        self._toast.setFont(_FONT_TOAST)
        self._toast.setAlignment(Qt.AlignCenter)
        self._toast.setMinimumHeight(50)
        self._toast.setStyleSheet("background-color: #1B5E20; color: white; padding: 8px 16px;")
        self._toast.hide()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)
        root.addWidget(self._toast)

        # ---- Titolo + pulsante torna ----
        top_row = QHBoxLayout()
        title = QLabel("REGISTRO ACCETTAZIONI")
        title.setFont(_FONT_TITLE)
        title.setStyleSheet("color: #1a1a2e;")
        top_row.addWidget(title)
        top_row.addStretch()

        btn_back = QPushButton("← TORNA ALL'ACCETTAZIONE")
        btn_back.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_back.setMinimumHeight(44)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #37474f;
                color: white;
                border-radius: 8px;
                padding: 6px 18px;
                border: none;
            }
            QPushButton:hover { background-color: #546e7a; }
        """)
        btn_back.clicked.connect(self._on_back)
        top_row.addWidget(btn_back)
        root.addLayout(top_row)

        # ---- Barra di ricerca + contatore + pulsanti ----
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self._search_input = QLineEdit()
        self._search_input.setFont(QFont("Segoe UI", 13))
        self._search_input.setMinimumHeight(42)
        self._search_input.setPlaceholderText("🔍  Cerca per codice, lotto, categoria, operatore...")
        self._search_input.setStyleSheet(_field_style("#1565C0"))
        self._search_input.textChanged.connect(self._filter_table)
        bar_row.addWidget(self._search_input, 3)

        self._count_label = QLabel("Totale registrazioni: 0")
        self._count_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._count_label.setStyleSheet("color: #1a1a2e;")
        bar_row.addWidget(self._count_label, 1)

        btn_refresh = QPushButton("🔄  AGGIORNA")
        btn_refresh.setFont(QFont("Segoe UI", 12, QFont.Bold))
        btn_refresh.setMinimumHeight(42)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
                border-radius: 8px;
                padding: 6px 14px;
                border: none;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        btn_refresh.clicked.connect(self._load_data)
        bar_row.addWidget(btn_refresh)

        self._btn_delete = QPushButton("🗑  ELIMINA SELEZIONATO")
        self._btn_delete.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._btn_delete.setMinimumHeight(42)
        self._btn_delete.setCursor(Qt.PointingHandCursor)
        self._btn_delete.setEnabled(False)
        self._btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                border-radius: 8px;
                padding: 6px 14px;
                border: none;
            }
            QPushButton:hover { background-color: #d32f2f; }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #9e9e9e;
            }
        """)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        bar_row.addWidget(self._btn_delete)

        root.addLayout(bar_row)

        # ---- Tabella ----
        self._table = QTableWidget()
        self._table.setFont(_FONT_TABLE)
        self._table.setColumnCount(len(self._COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in self._COLUMNS])
        self._table.horizontalHeader().setFont(_FONT_TABLE_HDR)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f5f5f5;
                gridline-color: #e0e0e0;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #1a1a2e;
            }
            QHeaderView::section {
                background-color: #1565C0;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self._table.setColumnWidth(0, 60)   # ID
        self._table.setColumnWidth(1, 180)  # Data/Ora
        self._table.setColumnWidth(2, 130)  # Operatore
        self._table.setColumnWidth(3, 160)  # Categoria
        self._table.setColumnWidth(4, 150)  # Codice Articolo
        self._table.setColumnWidth(5, 130)  # Lotto
        # Data Produzione → stretchLastSection
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        root.addWidget(self._table)

    # ------------------------------------------------------------------
    def _local_toast(self, msg: str, error: bool = False) -> None:
        bg = "#c62828" if error else "#1B5E20"
        self._toast.setStyleSheet(
            f"background-color: {bg}; color: white; padding: 8px 16px;"
        )
        self._toast.setText(msg)
        self._toast.show()
        self._toast_timer.start(3000 if error else 2500)

    # ------------------------------------------------------------------
    def _load_data(self) -> None:
        """Ricarica i dati dal database e aggiorna la tabella."""
        self._all_records = get_all_flussi(limit=500)
        self._search_input.clear()
        self._populate_table(self._all_records)
        total = get_flussi_count()
        self._count_label.setText(f"Totale registrazioni: {total}")

    # ------------------------------------------------------------------
    def _populate_table(self, records: list[dict]) -> None:
        self._table.setRowCount(0)
        self._table.setRowCount(len(records))
        for row_idx, rec in enumerate(records):
            for col_idx, (_, key) in enumerate(self._COLUMNS):
                val = str(rec.get(key, ""))
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                item.setFont(_FONT_TABLE)
                self._table.setItem(row_idx, col_idx, item)
        self._table.resizeRowsToContents()
        self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    def _filter_table(self, text: str) -> None:
        """Filtra la tabella in tempo reale (case-insensitive, qualsiasi colonna)."""
        query = text.strip().lower()
        if not query:
            self._populate_table(self._all_records)
            return
        filtered = [
            rec for rec in self._all_records
            if any(query in str(v).lower() for v in rec.values())
        ]
        self._populate_table(filtered)

    # ------------------------------------------------------------------
    def _on_selection_changed(self) -> None:
        has_sel = bool(self._table.selectedItems())
        self._btn_delete.setEnabled(has_sel)

    # ------------------------------------------------------------------
    def _on_delete_clicked(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            return
        row = self._table.currentRow()
        id_item = self._table.item(row, 0)
        if id_item is None:
            return
        record_id = int(id_item.text())

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Conferma eliminazione")
        dlg.setText(f"Sei sicuro di voler eliminare la registrazione ID #{record_id}?")
        dlg.setIcon(QMessageBox.Question)
        dlg.setFont(_FONT_FIELD)
        btn_si = dlg.addButton("Sì", QMessageBox.YesRole)
        dlg.addButton("No", QMessageBox.NoRole)
        dlg.exec()

        if dlg.clickedButton() is btn_si:
            ok = delete_flusso(record_id)
            if ok:
                self._table.removeRow(row)
                # Aggiorna anche la lista in memoria
                self._all_records = [r for r in self._all_records if r["id"] != record_id]
                total = get_flussi_count()
                self._count_label.setText(f"Totale registrazioni: {total}")
                self._local_toast(f"✅  Registrazione #{record_id} eliminata con successo.")
            else:
                self._local_toast(f"⚠  Impossibile eliminare la registrazione #{record_id}.", error=True)


# ===========================================================================
# Finestra Principale – QStackedWidget con schermata accettazione + registro
# ===========================================================================
class MainWindow(QMainWindow):
    """
    Finestra unica ottimizzata per scanner barcode e inserimento rapido.

    Flusso:
        Scansiona/digita codice → Enter → categoria rilevata →
        inserisci lotto → Enter → (data produzione →) Enter → SALVA →
        toast success → reset → focus su scan input → pronto per il prossimo
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Accettazione Rinforzi – Sistema Digitale")
        self.setMinimumSize(1024, 700)
        self.setStyleSheet("QMainWindow { background-color: #f5f5f5; }")

        self._categoria: str | None = None
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._hide_toast)

        # Debounce: prevents double-submissions from scanner trailing keystrokes
        self._locked: bool = False
        self._lock_timer = QTimer(self)
        self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self._unlock)

        # Modalità manuale (toggle)
        self._manual_mode: bool = False

        # Warning operatore (mostrato una sola volta per sessione)
        self._op_warning_shown: bool = False

        self._build_ui()
        self._setup_shortcuts()
        # Focus sul campo scan all'avvio
        QTimer.singleShot(0, self._scan_input.setFocus)

    # ------------------------------------------------------------------
    # Shortcut globali
    # ------------------------------------------------------------------
    def _setup_shortcuts(self) -> None:
        # Ctrl+R / F2 → apri Registro
        sc_r = QShortcut(QKeySequence("Ctrl+R"), self)
        sc_r.activated.connect(self._go_to_registro)
        sc_f2 = QShortcut(QKeySequence(Qt.Key_F2), self)
        sc_f2.activated.connect(self._go_to_registro)
        # Ctrl+M → toggle modalità manuale
        sc_m = QShortcut(QKeySequence("Ctrl+M"), self)
        sc_m.activated.connect(self._toggle_manual_mode)

    # ------------------------------------------------------------------
    # Costruzione layout
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # QStackedWidget: pagina 0 = accettazione, pagina 1 = registro
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # ---- Pagina 0: schermata di accettazione ----
        self._page_entry = self._build_entry_page()
        self._stack.addWidget(self._page_entry)

        # ---- Pagina 1: schermata registro ----
        self._registro = RegistroScreen(
            on_back=self._go_to_entry,
            show_toast_fn=self._show_toast,
        )
        self._stack.addWidget(self._registro)

        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    def _build_entry_page(self) -> QWidget:
        """Costruisce e restituisce la pagina di accettazione (pagina 0)."""
        # Widget con scroll per schermi piccoli
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #f5f5f5;")

        central = QWidget()
        central.setStyleSheet("background-color: #f5f5f5;")
        scroll.setWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Toast notification (inizialmente nascosto) ----
        self._toast = QLabel()
        self._toast.setFont(_FONT_TOAST)
        self._toast.setAlignment(Qt.AlignCenter)
        self._toast.setMinimumHeight(60)
        self._toast.setStyleSheet("""
            background-color: #1B5E20;
            color: white;
            padding: 10px 20px;
        """)
        self._toast.hide()
        root.addWidget(self._toast)

        # ---- Area contenuto principale ----
        content = QWidget()
        content.setStyleSheet("background-color: #f5f5f5;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 30, 60, 30)
        content_layout.setSpacing(0)
        root.addWidget(content)

        # ---- A) Titolo + pulsante REGISTRO ----
        title_row = QHBoxLayout()

        title = QLabel("ACCETTAZIONE RINFORZI")
        title.setFont(_FONT_TITLE)
        title.setStyleSheet("color: #1a1a2e;")
        title_row.addWidget(title)
        title_row.addStretch()

        btn_registro = QPushButton("📋  REGISTRO")
        btn_registro.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_registro.setMinimumHeight(44)
        btn_registro.setCursor(Qt.PointingHandCursor)
        btn_registro.setToolTip("Apri il Registro Accettazioni (Ctrl+R / F2)")
        btn_registro.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
                border-radius: 8px;
                padding: 6px 18px;
                border: none;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        btn_registro.clicked.connect(self._go_to_registro)
        title_row.addWidget(btn_registro)

        content_layout.addLayout(title_row)

        subtitle = QLabel("Scansiona il codice a barre o digita manualmente")
        subtitle.setFont(_FONT_SUBTITLE)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666666;")
        content_layout.addWidget(subtitle)

        content_layout.addSpacing(20)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #cccccc;")
        content_layout.addWidget(sep)

        content_layout.addSpacing(20)

        # ---- Card form ----
        card = QWidget()
        card.setStyleSheet("""
            QWidget#formCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }
        """)
        card.setObjectName("formCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 32, 40, 32)
        card_layout.setSpacing(20)
        content_layout.addWidget(card)

        # ---- B) Campo OPERATORE (sticky) + toggle modalità manuale ----
        op_row = QHBoxLayout()
        op_row.setSpacing(16)

        op_col = QVBoxLayout()
        op_label = QLabel("OPERATORE")
        op_label.setFont(_FONT_LABEL)
        op_label.setStyleSheet("color: #1a1a2e;")
        op_col.addWidget(op_label)

        self._operatore_combo = QComboBox()
        self._operatore_combo.setFont(_FONT_FIELD)
        self._operatore_combo.setMinimumHeight(48)
        self._operatore_combo.setEditable(True)
        self._operatore_combo.addItems(["Operatore 1", "Operatore 2", "Operatore 3"])
        self._operatore_combo.setCurrentIndex(-1)
        self._operatore_combo.lineEdit().setPlaceholderText("Seleziona o digita il nome operatore...")
        self._operatore_combo.setStyleSheet(_field_style("#90a4ae"))
        op_col.addWidget(self._operatore_combo)
        op_row.addLayout(op_col, 3)

        # Toggle modalità manuale
        manual_col = QVBoxLayout()
        manual_col.setSpacing(6)
        manual_spacer = QLabel("")
        manual_col.addWidget(manual_spacer)
        self._btn_manual = QPushButton("📝  Modalità Manuale")
        self._btn_manual.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._btn_manual.setMinimumHeight(48)
        self._btn_manual.setCheckable(True)
        self._btn_manual.setCursor(Qt.PointingHandCursor)
        self._btn_manual.setToolTip("Abilita inserimento manuale per etichette senza barcode (Ctrl+M)")
        self._btn_manual.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #37474f;
                border: 2px solid #90a4ae;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #eceff1; }
            QPushButton:checked {
                background-color: #e65100;
                color: white;
                border: 2px solid #e65100;
            }
        """)
        self._btn_manual.toggled.connect(self._on_manual_mode_toggled)
        manual_col.addWidget(self._btn_manual)
        op_row.addLayout(manual_col, 1)

        card_layout.addLayout(op_row)

        card_layout.addSpacing(12)

        # ---- C) Campo scansione ----
        self._scan_label = QLabel("CODICE ARTICOLO")
        self._scan_label.setFont(_FONT_LABEL)
        self._scan_label.setStyleSheet("color: #1a1a2e;")
        card_layout.addWidget(self._scan_label)

        self._scan_input = QLineEdit()
        self._scan_input.setFont(_FONT_SCAN)
        self._scan_input.setMinimumHeight(56)
        self._scan_input.setPlaceholderText("Scansiona o digita il codice articolo...")
        self._scan_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 3px solid #1565C0;
                border-radius: 8px;
                padding: 6px 12px;
                color: #1a1a2e;
            }
            QLineEdit:focus {
                border: 3px solid #0d47a1;
            }
        """)
        # Completamento automatico con tutti i codici
        all_codici = get_all_codici()
        completer = QCompleter(all_codici)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self._scan_input.setCompleter(completer)
        self._scan_input.returnPressed.connect(self._on_scan_enter)
        self._scan_input.textChanged.connect(self._on_scan_text_changed)
        card_layout.addWidget(self._scan_input)

        card_layout.addSpacing(4)

        # ---- Preview categoria (real-time, sotto il campo scan) ----
        self._preview_label = QLabel("")
        self._preview_label.setFont(QFont("Segoe UI", 11))
        self._preview_label.setStyleSheet("color: #757575; padding-left: 4px;")
        self._preview_label.hide()
        card_layout.addWidget(self._preview_label)

        # ---- D) Badge categoria ----
        badge_row = QHBoxLayout()
        badge_row.setSpacing(12)

        self._badge = QLabel("— Scansiona un codice per rilevare la categoria —")
        self._badge.setFont(_FONT_BADGE)
        self._badge.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._badge.setMinimumHeight(40)
        self._badge.setStyleSheet("""
            background-color: #eeeeee;
            color: #555555;
            border-radius: 6px;
            padding: 6px 14px;
        """)
        badge_row.addWidget(self._badge, 1)

        # Dropdown manuale (visibile solo quando il rilevamento fallisce)
        self._cat_combo = QComboBox()
        self._cat_combo.setFont(_FONT_BADGE)
        self._cat_combo.setMinimumHeight(40)
        self._cat_combo.addItems(list(CATEGORY_CONFIG.keys()))
        self._cat_combo.setStyleSheet("""
            QComboBox {
                background-color: #fff3e0;
                border: 2px solid #e65100;
                border-radius: 6px;
                padding: 4px 10px;
                color: #1a1a2e;
            }
        """)
        self._cat_combo.currentTextChanged.connect(self._on_manual_cat_change)
        self._cat_combo.hide()
        badge_row.addWidget(self._cat_combo)

        card_layout.addLayout(badge_row)

        card_layout.addSpacing(8)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #e0e0e0;")
        card_layout.addWidget(sep2)

        card_layout.addSpacing(8)

        # ---- E) Lotto + Data (stessa riga) ----
        fields_row = QHBoxLayout()
        fields_row.setSpacing(30)

        # Lotto
        lotto_col = QVBoxLayout()
        lotto_col.setSpacing(6)
        lotto_label = QLabel("Lotto N°")
        lotto_label.setFont(_FONT_LABEL)
        lotto_label.setStyleSheet("color: #1a1a2e;")
        lotto_col.addWidget(lotto_label)

        self._lotto_input = QLineEdit()
        self._lotto_input.setFont(_FONT_FIELD)
        self._lotto_input.setMinimumHeight(48)
        self._lotto_input.setPlaceholderText("Inserisci numero lotto...")
        self._lotto_input.setStyleSheet(_field_style())
        self._lotto_input.returnPressed.connect(self._on_lotto_enter)
        lotto_col.addWidget(self._lotto_input)

        fields_row.addLayout(lotto_col, 2)

        # Data di produzione
        data_col = QVBoxLayout()
        data_col.setSpacing(6)
        data_label = QLabel("Data di Produzione")
        data_label.setFont(_FONT_LABEL)
        data_label.setStyleSheet("color: #1a1a2e;")
        data_col.addWidget(data_label)

        self._data_edit = QDateEdit()
        self._data_edit.setFont(_FONT_FIELD)
        self._data_edit.setMinimumHeight(48)
        self._data_edit.setCalendarPopup(True)
        self._data_edit.setDisplayFormat("dd/MM/yyyy")
        self._data_edit.setDate(QDate.currentDate())
        self._data_edit.setStyleSheet(_field_style())
        # Event filter per catturare Enter su QDateEdit
        self._date_enter_filter = _DateEditEnterFilter(self._salva, self._data_edit)
        self._data_edit.installEventFilter(self._date_enter_filter)
        data_col.addWidget(self._data_edit)

        fields_row.addLayout(data_col, 1)

        card_layout.addLayout(fields_row)

        card_layout.addSpacing(20)

        # ---- F) Pulsante SALVA ----
        save_row = QHBoxLayout()
        self._btn_save = QPushButton("SALVA")
        self._btn_save.setFont(_FONT_SAVE)
        self._btn_save.setMinimumSize(320, 70)
        self._btn_save.setCursor(Qt.PointingHandCursor)
        self._btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover  { background-color: #388e3c; }
            QPushButton:pressed { background-color: #1b5e20; }
        """)
        self._btn_save.clicked.connect(self._salva)
        save_row.addStretch()
        save_row.addWidget(self._btn_save)
        save_row.addStretch()
        card_layout.addLayout(save_row)

        content_layout.addStretch()

        return scroll

    # ------------------------------------------------------------------
    # Navigazione tra schermate
    # ------------------------------------------------------------------
    def _go_to_registro(self) -> None:
        self._registro._load_data()
        self._stack.setCurrentIndex(1)

    def _go_to_entry(self) -> None:
        self._stack.setCurrentIndex(0)
        QTimer.singleShot(0, self._scan_input.setFocus)

    # ------------------------------------------------------------------
    # Modalità Manuale
    # ------------------------------------------------------------------
    def _toggle_manual_mode(self) -> None:
        self._btn_manual.setChecked(not self._btn_manual.isChecked())

    def _on_manual_mode_toggled(self, checked: bool) -> None:
        self._manual_mode = checked
        if checked:
            # Modalità manuale: etichetta scan diventa semplice campo testo
            self._scan_label.setText("CODICE ARTICOLO (manuale)")
            # Mostra sempre il combo categoria (non solo in caso di fallimento rilevamento)
            self._badge.hide()
            self._cat_combo.show()
            # Imposta la categoria al valore corrente del combo
            self._categoria = self._cat_combo.currentText()
            # Nascondi la preview
            self._preview_label.hide()
        else:
            # Ripristina modalità scan
            self._scan_label.setText("CODICE ARTICOLO")
            self._badge.show()
            # Rilevamento automatico dal testo corrente
            codice = self._scan_input.text().strip()
            cat = detect_categoria(codice) if codice else None
            self._set_categoria(cat)

    # ------------------------------------------------------------------
    # Preview categoria in tempo reale (textChanged)
    # ------------------------------------------------------------------
    def _on_scan_text_changed(self, text: str) -> None:
        if self._manual_mode:
            return
        codice = text.strip()
        if not codice:
            self._preview_label.hide()
            return
        cat = detect_categoria(codice)
        if cat:
            color = CATEGORY_CONFIG.get(cat, {}).get("colore", "#2e7d32")
            self._preview_label.setText(f"🏷  Categoria rilevata: {cat}")
            self._preview_label.setStyleSheet(f"color: {color}; padding-left: 4px; font-weight: bold;")
        else:
            self._preview_label.setText("🏷  Categoria non rilevata (verrà richiesta conferma)")
            self._preview_label.setStyleSheet("color: #e65100; padding-left: 4px;")
        self._preview_label.show()

    # ------------------------------------------------------------------
    # Auto-rilevamento e gestione badge
    # ------------------------------------------------------------------
    def _on_scan_enter(self) -> None:
        """Chiamato quando si preme Enter nel campo codice articolo."""
        if self._locked:
            return

        # Modalità manuale: Enter sposta semplicemente al campo successivo
        if self._manual_mode:
            self._lotto_input.setFocus()
            self._lotto_input.selectAll()
            return

        raw_text = self._scan_input.text().strip()
        if not raw_text:
            return

        # Smart barcode parsing: prova a splittare codice + lotto
        codice, lotto = _parse_barcode(raw_text)

        if lotto is not None:
            # Barcode composito: imposta codice e lotto automaticamente
            self._scan_input.setText(codice)
            self._lotto_input.setText(lotto)
            cat = detect_categoria(codice)
            self._set_categoria(cat)
            # Salta direttamente alla data produzione (lotto già compilato)
            self._data_edit.setFocus()
            self._show_toast(
                "✅  Codice e Lotto rilevati automaticamente dal barcode",
                durata_ms=2000,
            )
        else:
            # Nessun separatore: comportamento standard
            cat = detect_categoria(codice)
            self._set_categoria(cat)
            self._lotto_input.setFocus()
            self._lotto_input.selectAll()

    def _on_lotto_enter(self) -> None:
        """Chiamato quando si preme Enter nel campo lotto."""
        self._data_edit.setFocus()

    def _on_manual_cat_change(self, cat: str) -> None:
        """Aggiorna la categoria quando l'operatore sceglie manualmente."""
        if cat:
            self._categoria = cat

    def _set_categoria(self, cat: str | None) -> None:
        self._categoria = cat
        if cat:
            color = CATEGORY_CONFIG.get(cat, {}).get("colore", "#2e7d32")
            self._badge.setText(f"✅  CATEGORIA: {cat}")
            self._badge.setStyleSheet(f"""
                background-color: {color};
                color: white;
                border-radius: 6px;
                padding: 6px 14px;
            """)
            self._cat_combo.hide()
            self._badge.show()
            # Sincronizza il combo per coerenza
            idx = self._cat_combo.findText(cat)
            if idx >= 0:
                self._cat_combo.setCurrentIndex(idx)
        else:
            self._badge.setText("⚠  CATEGORIA NON RILEVATA – seleziona manualmente:")
            self._badge.setStyleSheet("""
                background-color: #e65100;
                color: white;
                border-radius: 6px;
                padding: 6px 14px;
            """)
            self._cat_combo.show()
            self._categoria = self._cat_combo.currentText()

    # ------------------------------------------------------------------
    # Salvataggio
    # ------------------------------------------------------------------
    def _salva(self) -> None:
        # Debounce: ignore calls during the 500ms lock window
        if self._locked:
            return

        codice = self._scan_input.text().strip()
        lotto  = self._lotto_input.text().strip()
        data_str = self._data_edit.date().toString("yyyy-MM-dd")
        operatore = self._operatore_combo.currentText().strip()

        # Determina la categoria finale (manuale o rilevata)
        if self._manual_mode or self._cat_combo.isVisible():
            self._categoria = self._cat_combo.currentText()

        # Validazione
        if not codice:
            self._show_toast("⚠  Il campo «Codice Articolo» è obbligatorio.", error=True)
            self._scan_input.setFocus()
            return
        if not lotto:
            self._show_toast("⚠  Il campo «Lotto N°» è obbligatorio.", error=True)
            self._lotto_input.setFocus()
            return
        if not self._categoria:
            self._show_toast(
                "⚠  Categoria non rilevata. Scansiona un codice o seleziona la categoria manualmente.",
                error=True,
            )
            self._scan_input.setFocus()
            return

        # Warning operatore (una sola volta per sessione, non bloccante)
        if not operatore and not self._op_warning_shown:
            self._op_warning_shown = True
            self._show_toast(
                "⚠  Nessun operatore selezionato — il campo verrà lasciato vuoto",
                error=False,
                durata_ms=3500,
            )
            # Continua comunque il salvataggio
            # (non ritorna qui)

        # Inserimento in DB
        try:
            record_id = insert_flusso(
                categoria=self._categoria,
                codice_articolo=codice,
                lotto_id=lotto,
                data_produzione=data_str,
                operatore=operatore,
            )
        except Exception as exc:
            self._mostra_avviso(f"Errore durante il salvataggio:\n{exc}")
            return

        # ---- Toast di successo (non bloccante) ----
        self._show_toast(
            f"✅  Registrato: {codice}  |  Lotto: {lotto}  |  ID: {record_id}"
        )

        # Attiva il debounce per 500ms dopo il salvataggio
        self._locked = True
        self._lock_timer.start(500)

        # Reset form (operatore NON viene resettato)
        self._reset_form()

    # ------------------------------------------------------------------
    # Toast notification
    # ------------------------------------------------------------------
    def _show_toast(self, messaggio: str, durata_ms: int = _TOAST_SUCCESS_DURATION_MS, error: bool = False) -> None:
        bg_color = "#C62828" if error else "#1B5E20"
        self._toast.setStyleSheet(f"""
            background-color: {bg_color};
            color: white;
            padding: 10px 20px;
        """)
        self._toast.setText(messaggio)
        self._toast.show()
        self._toast_timer.start(_TOAST_ERROR_DURATION_MS if error else durata_ms)

    def _hide_toast(self) -> None:
        self._toast.hide()

    def _unlock(self) -> None:
        """Chiamato dal timer 500ms dopo un salvataggio per riabilitare l'input."""
        self._locked = False

    # ------------------------------------------------------------------
    # Reset form
    # ------------------------------------------------------------------
    def _reset_form(self) -> None:
        self._scan_input.clear()
        self._lotto_input.clear()
        self._data_edit.setDate(QDate.currentDate())
        self._preview_label.hide()
        if not self._manual_mode:
            self._categoria = None
            self._badge.setText("— Scansiona un codice per rilevare la categoria —")
            self._badge.setStyleSheet("""
                background-color: #eeeeee;
                color: #555555;
                border-radius: 6px;
                padding: 6px 14px;
            """)
            self._cat_combo.hide()
        # OPERATORE non viene resettato: rimane impostato per tutto il turno
        # Focus torna al campo scan
        self._scan_input.setFocus()

    # ------------------------------------------------------------------
    def _mostra_avviso(self, testo: str) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Attenzione")
        msg.setText(testo)
        msg.setIcon(QMessageBox.Warning)
        msg.setFont(_FONT_FIELD)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
