"""
ui.py – Componenti UI PySide6 per il Sistema di Accettazione Rinforzi.

Struttura:
  • CATEGORY_CONFIG  – dizionario di configurazione estensibile per categoria
  • PREFIX_RULES     – regole di rilevamento per prefisso codice
  • KEYWORD_RULES    – regole di rilevamento per parole chiave
  • detect_categoria – pipeline di auto-rilevamento categoria
  • MainWindow       – Finestra unica (single-screen, scan-first)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QDate, QTimer, QObject, QEvent
from PySide6.QtGui import QFont
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
)

from database import (
    get_all_codici,
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
# Finestra Principale – Single-screen, scan-first
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

        self._build_ui()
        # Focus sul campo scan all'avvio
        QTimer.singleShot(0, self._scan_input.setFocus)

    # ------------------------------------------------------------------
    # Costruzione layout
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Widget centrale con scroll per schermi piccoli
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #f5f5f5;")
        self.setCentralWidget(scroll)

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

        # ---- A) Titolo ----
        title = QLabel("ACCETTAZIONE RINFORZI")
        title.setFont(_FONT_TITLE)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a2e;")
        content_layout.addWidget(title)

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

        # ---- B) Campo OPERATORE (sticky – non resettato) ----
        op_label = QLabel("OPERATORE")
        op_label.setFont(_FONT_LABEL)
        op_label.setStyleSheet("color: #1a1a2e;")
        card_layout.addWidget(op_label)

        self._operatore_combo = QComboBox()
        self._operatore_combo.setFont(_FONT_FIELD)
        self._operatore_combo.setMinimumHeight(48)
        self._operatore_combo.setEditable(True)
        self._operatore_combo.addItems(["Operatore 1", "Operatore 2", "Operatore 3"])
        self._operatore_combo.setCurrentIndex(-1)
        self._operatore_combo.lineEdit().setPlaceholderText("Seleziona o digita il nome operatore...")
        self._operatore_combo.setStyleSheet(_field_style("#90a4ae"))
        card_layout.addWidget(self._operatore_combo)

        card_layout.addSpacing(12)

        # ---- C) Campo scansione ----
        scan_label = QLabel("CODICE ARTICOLO")
        scan_label.setFont(_FONT_LABEL)
        scan_label.setStyleSheet("color: #1a1a2e;")
        card_layout.addWidget(scan_label)

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
        card_layout.addWidget(self._scan_input)

        card_layout.addSpacing(4)

        # ---- C) Badge categoria ----
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

        # ---- D) Lotto + Data (stessa riga) ----
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

        # ---- E) Pulsante SALVA ----
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

    # ------------------------------------------------------------------
    # Auto-rilevamento e gestione badge
    # ------------------------------------------------------------------
    def _on_scan_enter(self) -> None:
        """Chiamato quando si preme Enter nel campo codice articolo."""
        if self._locked:
            return
        codice = self._scan_input.text().strip()
        cat = detect_categoria(codice)
        self._set_categoria(cat)
        # Sposta il focus sul campo lotto
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
        if self._cat_combo.isVisible():
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
