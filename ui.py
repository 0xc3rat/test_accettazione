"""
ui.py – Componenti UI PySide6 per il Sistema di Accettazione Rinforzi.

Struttura:
  • CATEGORY_CONFIG  – dizionario di configurazione estensibile per categoria
  • HomeScreen       – Schermata 1: 4 grandi pulsanti di selezione categoria
  • FormScreen       – Schermata 2: form di inserimento dati dinamico
  • MainWindow       – Finestra principale con QStackedWidget
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCompleter,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QMainWindow,
    QStackedWidget,
    QSpacerItem,
)

from database import get_codici_by_categoria, insert_flusso

# ---------------------------------------------------------------------------
# CATEGORY_CONFIG
# ---------------------------------------------------------------------------
# Struttura:
#   "NOME CATEGORIA": {
#       "colore":      colore hex del pulsante nella home screen,
#       "fields":      lista di descrittori di campo (usati per generare il form),
#   }
#
# Ogni campo ha:
#   "id":        identificatore interno (stringa snake_case)
#   "label":     etichetta mostrata all'utente (italiano)
#   "tipo":      "combo_articolo" | "lineedit" | "dateedit"
#   "obbligatorio": bool  (True = la validazione lo richiede non vuoto)
#
# Per aggiungere una nuova categoria in futuro:
#   1. Aggiungere una nuova chiave in CATEGORY_CONFIG con i suoi campi
#   2. (Facoltativo) aggiungere seed data in database.py
#   → Nessun'altra modifica è richiesta.
# ---------------------------------------------------------------------------

CATEGORY_CONFIG: dict[str, dict] = {
    "TESSUTI TESSILI": {
        "colore": "#1a3a6b",   # blu navy
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo:", "tipo": "combo_articolo", "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°:",        "tipo": "lineedit",       "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione:", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "TESSUTI METALLICI": {
        "colore": "#2d5a27",   # verde scuro
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo:", "tipo": "combo_articolo", "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°:",        "tipo": "lineedit",       "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione:", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "BANDINE": {
        "colore": "#7a3b00",   # arancione scuro
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo:", "tipo": "combo_articolo", "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°:",        "tipo": "lineedit",       "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione:", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
    "ALTRO": {
        "colore": "#3a3a3a",   # grigio scuro
        "fields": [
            {"id": "codice_articolo", "label": "Codice Articolo:", "tipo": "combo_articolo", "obbligatorio": True},
            {"id": "lotto_id",        "label": "Lotto N°:",        "tipo": "lineedit",       "obbligatorio": True},
            {"id": "data_produzione", "label": "Data di Produzione:", "tipo": "dateedit",    "obbligatorio": False},
        ],
    },
}

# ---------------------------------------------------------------------------
# Costanti di stile
# ---------------------------------------------------------------------------
_FONT_TITLE    = QFont("Segoe UI", 28, QFont.Bold)
_FONT_SUBTITLE = QFont("Segoe UI", 13)
_FONT_CATEGORY = QFont("Segoe UI", 20, QFont.Bold)
_FONT_LABEL    = QFont("Segoe UI", 14, QFont.Bold)
_FONT_FIELD    = QFont("Segoe UI", 14)
_FONT_SAVE     = QFont("Segoe UI", 18, QFont.Bold)
_FONT_BACK     = QFont("Segoe UI", 12)
_FONT_FORM_TITLE = QFont("Segoe UI", 22, QFont.Bold)


# ===========================================================================
# Schermata 1 – Home / Selezione Categoria
# ===========================================================================
class HomeScreen(QWidget):
    """Schermata principale con 4 grandi pulsanti di categoria."""

    def __init__(self, on_category_selected, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_category_selected = on_category_selected
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(10)

        # ---- Titolo ----
        title = QLabel("ACCETTAZIONE RINFORZI")
        title.setFont(_FONT_TITLE)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a2e;")
        root.addWidget(title)

        subtitle = QLabel("Seleziona la categoria del materiale in arrivo")
        subtitle.setFont(_FONT_SUBTITLE)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #555555;")
        root.addWidget(subtitle)

        # ---- Separatore ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #cccccc;")
        root.addWidget(sep)
        root.addSpacing(10)

        # ---- Griglia 2×2 dei pulsanti ----
        grid = QGridLayout()
        grid.setSpacing(20)

        categories = list(CATEGORY_CONFIG.keys())
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

        for cat, (row, col) in zip(categories, positions):
            btn = self._make_category_button(cat, CATEGORY_CONFIG[cat]["colore"])
            grid.addWidget(btn, row, col)

        root.addLayout(grid)
        root.addStretch()

    def _make_category_button(self, categoria: str, colore: str) -> QPushButton:
        btn = QPushButton(categoria)
        btn.setFont(_FONT_CATEGORY)
        btn.setMinimumSize(220, 130)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colore};
                color: white;
                border-radius: 12px;
                border: none;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {_lighten_hex(colore, 30)};
            }}
            QPushButton:pressed {{
                background-color: {_darken_hex(colore, 20)};
            }}
        """)
        btn.clicked.connect(lambda checked=False, c=categoria: self._on_category_selected(c))
        return btn


# ===========================================================================
# Schermata 2 – Form Dinamico
# ===========================================================================
class FormScreen(QWidget):
    """Form di inserimento dati per una categoria specifica."""

    def __init__(self, on_back, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._categoria: str = ""
        self._field_widgets: list[QWidget] = []   # ordine di tab-focus
        self._build_ui()

    # ------------------------------------------------------------------
    # Costruzione layout (una volta sola)
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(50, 25, 50, 25)
        self._root.setSpacing(12)

        # ---- Riga superiore: indietro + titolo ----
        top_row = QHBoxLayout()
        self._btn_back = QPushButton("← INDIETRO")
        self._btn_back.setFont(_FONT_BACK)
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.setFixedHeight(40)
        self._btn_back.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #222;
                border-radius: 6px;
                border: none;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #bdbdbd; }
        """)
        self._btn_back.clicked.connect(self._on_back)

        self._lbl_title = QLabel()
        self._lbl_title.setFont(_FONT_FORM_TITLE)
        self._lbl_title.setStyleSheet("color: #1a1a2e;")
        self._lbl_title.setAlignment(Qt.AlignCenter)

        top_row.addWidget(self._btn_back, 0, Qt.AlignLeft)
        top_row.addWidget(self._lbl_title, 1, Qt.AlignCenter)
        top_row.addSpacerItem(QSpacerItem(self._btn_back.sizeHint().width(), 1))
        self._root.addLayout(top_row)

        # ---- Separatore ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #cccccc;")
        self._root.addWidget(sep)
        self._root.addSpacing(8)

        # ---- Contenitore campi (riempito dinamicamente) ----
        self._fields_container = QWidget()
        self._fields_layout = QGridLayout(self._fields_container)
        self._fields_layout.setSpacing(16)
        self._fields_layout.setContentsMargins(0, 0, 0, 0)
        self._fields_layout.setColumnStretch(1, 1)
        self._root.addWidget(self._fields_container)

        self._root.addSpacing(20)

        # ---- Pulsante SALVA ----
        save_row = QHBoxLayout()
        self._btn_save = QPushButton("💾  SALVA")
        self._btn_save.setFont(_FONT_SAVE)
        self._btn_save.setMinimumSize(320, 75)
        self._btn_save.setCursor(Qt.PointingHandCursor)
        self._btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:pressed { background-color: #1b5e20; }
        """)
        self._btn_save.clicked.connect(self._salva)
        save_row.addStretch()
        save_row.addWidget(self._btn_save)
        save_row.addStretch()
        self._root.addLayout(save_row)
        self._root.addStretch()

    # ------------------------------------------------------------------
    # Caricamento di una categoria (chiamato da MainWindow)
    # ------------------------------------------------------------------
    def load_categoria(self, categoria: str) -> None:
        self._categoria = categoria
        self._lbl_title.setText(f"ACCETTAZIONE – {categoria}")

        # Svuota il layout dei campi
        while self._fields_layout.count():
            item = self._fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._field_widgets.clear()

        config = CATEGORY_CONFIG[categoria]
        codici = get_codici_by_categoria(categoria)

        # Raggruppa "lotto_id" e "data_produzione" sulla stessa riga
        field_defs = config["fields"]
        row_idx = 0
        i = 0
        while i < len(field_defs):
            fd = field_defs[i]
            next_fd = field_defs[i + 1] if i + 1 < len(field_defs) else None

            # Coppia lotto + data_produzione → stessa riga
            if fd["id"] == "lotto_id" and next_fd and next_fd["id"] == "data_produzione":
                widget_lotto = self._create_widget(fd, codici)
                widget_data  = self._create_widget(next_fd, codici)

                lbl_lotto = _make_label(fd["label"])
                lbl_data  = _make_label(next_fd["label"])

                pair_widget = QWidget()
                pair_layout = QHBoxLayout(pair_widget)
                pair_layout.setContentsMargins(0, 0, 0, 0)
                pair_layout.setSpacing(20)
                pair_layout.addWidget(lbl_lotto)
                pair_layout.addWidget(widget_lotto, 2)
                pair_layout.addSpacing(30)
                pair_layout.addWidget(lbl_data)
                pair_layout.addWidget(widget_data, 1)

                self._fields_layout.addWidget(pair_widget, row_idx, 0, 1, 2)
                self._field_widgets.append(widget_lotto)
                self._field_widgets.append(widget_data)
                row_idx += 1
                i += 2
                continue

            # Campo singolo
            lbl    = _make_label(fd["label"])
            widget = self._create_widget(fd, codici)
            self._fields_layout.addWidget(lbl,    row_idx, 0, Qt.AlignRight | Qt.AlignVCenter)
            self._fields_layout.addWidget(widget, row_idx, 1)
            self._field_widgets.append(widget)
            row_idx += 1
            i += 1

        # Collega Enter sull'ultimo campo all'azione SALVA
        self._setup_enter_navigation()

        # Focus automatico al primo campo
        if self._field_widgets:
            self._field_widgets[0].setFocus()
            if isinstance(self._field_widgets[0], QComboBox):
                self._field_widgets[0].lineEdit().selectAll()

    # ------------------------------------------------------------------
    # Creazione widget in base al tipo
    # ------------------------------------------------------------------
    def _create_widget(self, field_def: dict, codici: list[str]) -> QWidget:
        tipo = field_def["tipo"]

        if tipo == "combo_articolo":
            combo = QComboBox()
            combo.setEditable(True)
            combo.setFont(_FONT_FIELD)
            combo.setMinimumHeight(44)
            combo.addItem("")
            combo.addItems(codici)
            combo.setCurrentIndex(0)

            # Auto-completamento case-insensitive
            completer = QCompleter(codici)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            combo.setCompleter(completer)
            combo.setStyleSheet(_field_style())
            return combo

        elif tipo == "lineedit":
            le = QLineEdit()
            le.setFont(_FONT_FIELD)
            le.setMinimumHeight(44)
            le.setPlaceholderText(field_def["label"].rstrip(":"))
            le.setStyleSheet(_field_style())
            return le

        elif tipo == "dateedit":
            de = QDateEdit()
            de.setFont(_FONT_FIELD)
            de.setMinimumHeight(44)
            de.setCalendarPopup(True)
            de.setDisplayFormat("dd/MM/yyyy")
            de.setDate(QDate.currentDate())
            de.setStyleSheet(_field_style())
            return de

        raise ValueError(f"Tipo campo sconosciuto: {tipo}")

    # ------------------------------------------------------------------
    # Navigazione Enter tra campi
    # ------------------------------------------------------------------
    def _setup_enter_navigation(self) -> None:
        for idx, widget in enumerate(self._field_widgets):
            is_last = (idx == len(self._field_widgets) - 1)

            if isinstance(widget, QComboBox):
                le = widget.lineEdit()
                if is_last:
                    le.returnPressed.connect(self._salva)
                else:
                    next_w = self._field_widgets[idx + 1]
                    le.returnPressed.connect(lambda nw=next_w: self._focus_next(nw))

            elif isinstance(widget, QLineEdit):
                if is_last:
                    widget.returnPressed.connect(self._salva)
                else:
                    next_w = self._field_widgets[idx + 1]
                    widget.returnPressed.connect(lambda nw=next_w: self._focus_next(nw))

            # QDateEdit: Enter non genera returnPressed standard,
            # ma il Tab nativo di Qt funziona correttamente.

    @staticmethod
    def _focus_next(widget: QWidget) -> None:
        widget.setFocus()
        if isinstance(widget, QComboBox):
            widget.lineEdit().selectAll()
        elif isinstance(widget, QLineEdit):
            widget.selectAll()

    # ------------------------------------------------------------------
    # Raccolta valori dal form
    # ------------------------------------------------------------------
    def _get_field_value(self, field_id: str) -> str:
        config = CATEGORY_CONFIG[self._categoria]
        for idx, fd in enumerate(config["fields"]):
            if fd["id"] == field_id:
                widget = self._field_widgets[idx]
                if isinstance(widget, QComboBox):
                    return widget.currentText().strip()
                elif isinstance(widget, QLineEdit):
                    return widget.text().strip()
                elif isinstance(widget, QDateEdit):
                    return widget.date().toString("yyyy-MM-dd")
        return ""

    # ------------------------------------------------------------------
    # Salvataggio
    # ------------------------------------------------------------------
    def _salva(self) -> None:
        codice   = self._get_field_value("codice_articolo")
        lotto    = self._get_field_value("lotto_id")
        data_str = self._get_field_value("data_produzione")

        # Validazione campi obbligatori
        if not codice:
            self._mostra_avviso("Il campo «Codice Articolo» è obbligatorio.")
            self._field_widgets[0].setFocus()
            return
        if not lotto:
            self._mostra_avviso("Il campo «Lotto N°» è obbligatorio.")
            # trova il widget lotto
            for idx, fd in enumerate(CATEGORY_CONFIG[self._categoria]["fields"]):
                if fd["id"] == "lotto_id":
                    self._field_widgets[idx].setFocus()
                    break
            return

        # Inserimento in DB
        try:
            record_id = insert_flusso(
                categoria=self._categoria,
                codice_articolo=codice,
                lotto_id=lotto,
                data_produzione=data_str,
            )
        except Exception as exc:
            self._mostra_avviso(f"Errore durante il salvataggio:\n{exc}")
            return

        # Messaggio di successo
        msg = QMessageBox(self)
        msg.setWindowTitle("Registrazione completata")
        msg.setText(f"✅  Registrato con successo!\n\nID: {record_id}  |  Categoria: {self._categoria}\nCodice: {codice}  |  Lotto: {lotto}")
        msg.setIcon(QMessageBox.Information)
        msg.setFont(_FONT_FIELD)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

        # Torna alla home
        self._on_back()

    # ------------------------------------------------------------------
    def _mostra_avviso(self, testo: str) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Attenzione")
        msg.setText(testo)
        msg.setIcon(QMessageBox.Warning)
        msg.setFont(_FONT_FIELD)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()


# ===========================================================================
# Finestra Principale
# ===========================================================================
class MainWindow(QMainWindow):
    """Finestra principale con QStackedWidget per la navigazione tra schermate."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Accettazione Rinforzi – Sistema Digitale")
        self.setMinimumSize(950, 680)
        self.setStyleSheet("QMainWindow { background-color: #f5f5f5; }")

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._home   = HomeScreen(on_category_selected=self._apri_form)
        self._form   = FormScreen(on_back=self._torna_home)

        self._stack.addWidget(self._home)   # indice 0
        self._stack.addWidget(self._form)   # indice 1

        self._stack.setCurrentIndex(0)

    def _apri_form(self, categoria: str) -> None:
        self._form.load_categoria(categoria)
        self._stack.setCurrentIndex(1)

    def _torna_home(self) -> None:
        self._stack.setCurrentIndex(0)


# ===========================================================================
# Helper functions
# ===========================================================================

def _make_label(testo: str) -> QLabel:
    lbl = QLabel(testo)
    lbl.setFont(_FONT_LABEL)
    lbl.setStyleSheet("color: #1a1a2e;")
    return lbl


def _field_style() -> str:
    return """
        background-color: #ffffff;
        border: 2px solid #90a4ae;
        border-radius: 6px;
        padding: 4px 8px;
        color: #1a1a2e;
    """


def _lighten_hex(hex_color: str, amount: int) -> str:
    """Schiarisce un colore hex RGB di `amount` per ogni canale."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, r + amount)
    g = min(255, g + amount)
    b = min(255, b + amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken_hex(hex_color: str, amount: int) -> str:
    """Scurisce un colore hex RGB di `amount` per ogni canale."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = max(0, r - amount)
    g = max(0, g - amount)
    b = max(0, b - amount)
    return f"#{r:02x}{g:02x}{b:02x}"