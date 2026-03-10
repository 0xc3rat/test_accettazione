<p align="center">
  <img src="https://raw.githubusercontent.com/0xc3rat/test_accettazione/main/logo.png" width="120" alt="Project Logo"/>
</p>

<h1 align="center">Accettazione Rinforzi</h1>
<p align="center"><em>Ideato e Realizzato da Pierpaolo Careddu</em></p>

<p align="center">
  <img src="https://img.shields.io/github/languages/top/0xc3rat/test_accettazione?color=blue" alt="Top Language"/>
  <img src="https://img.shields.io/github/license/0xc3rat/test_accettazione" alt="License"/>
  <img src="https://img.shields.io/github/repo-size/0xc3rat/test_accettazione" alt="Repo Size"/>
  <img src="https://img.shields.io/github/issues/0xc3rat/test_accettazione" alt="Issues"/>
  <img src="https://img.shields.io/github/last-commit/0xc3rat/test_accettazione" alt="Last Commit"/>
</p>

---

# 🚀 Overview

**Accettazione Rinforzi** is a **desktop application built with Python and PySide6** designed to digitize and streamline the **acceptance and traceability of reinforcement materials** in industrial environments.

The system allows operators to:

- Scan or manually enter **material barcodes**
- Automatically detect the **material category**
- Register **lot number and production date**
- Track **operator information**
- Store and manage entries in a **SQLite database**
- View and manage historical records through a **Registro (log viewer)**

The application is optimized for **barcode scanner workflows**, enabling fast and reliable data entry on the production floor.

---

# 📦 Features

## ⚡ Fast Barcode Workflow

- Scan a barcode → press **Enter**
- Automatic **category detection**
- Optimized for **keyboard-emulating barcode scanners**

---

## 🏷 Intelligent Category Detection

Detection pipeline:

1. Exact lookup in SQLite database  
2. Prefix rules (`STT`, `STM`, `STR`, `ALT`)  
3. Keyword detection  
4. Manual fallback selection  

---

## 🧠 Smart Barcode Parsing

Composite barcodes can automatically extract:

- **Codice Articolo**
- **Lotto**

Supported separators:

- TAB  
- `|`  
- `;`  
- `-`

Example:

```
STT0962A0-LOT123
```

Automatically becomes:

```
Codice articolo: STT0962A0
Lotto: LOT123
```

---

## 🗃 Integrated SQLite Database

The database is automatically created at first launch:

```
accettazione.db
```

Tables:

- `Materiali_Anagrafica`
- `Flussi_Ingresso`

---

## 📋 Registro (Log Viewer)

The **Registro screen** allows users to:

- View recent records
- Search across all fields
- Delete selected entries
- Display total number of records

---

## 👨‍🏭 Operator Tracking

Operators can:

- Select predefined names
- Type custom names
- Persist across multiple scans during a shift

---

## 📝 Manual Mode

Allows manual entry when no barcode is available.

Toggle with:

```
Ctrl + M
```

---

## ⌨ Productivity Shortcuts

| Shortcut | Action |
|--------|--------|
| Ctrl + R | Open Registro |
| F2 | Open Registro |
| Ctrl + M | Toggle Manual Mode |
| Enter | Move to next field / confirm |

---

# 🛠️ Installation

Clone the repository:

```bash
git clone https://github.com/0xc3rat/test_accettazione.git
cd test_accettazione
```

Install dependencies:

```bash
pip install PySide6
```

(Optional) Use a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
pip install PySide6
```

---

# ⚡ Usage

Run the application:

```bash
python main.py
```

At the first run the system will automatically create:

```
accettazione.db
```

---

# 🖥 Application Workflow

Typical operator workflow:

```
1 Scan Codice Articolo
2 Categoria detected automatically
3 Insert Lotto
4 Confirm Data Produzione
5 Press Enter → SALVA
```

Result:

```
Record saved to SQLite database
Confirmation toast appears
Form resets ready for next scan
```

---

# 🗂 Project Structure

```
test_accettazione/
│
├── main.py
│   Entry point of the application
│
├── ui.py
│   PySide6 GUI and application workflow
│
├── database.py
│   SQLite data layer and database initialization
│
├── accettazione.db
│   Auto-generated SQLite database
│
└── README.md
```

---

# 🗄 Database Schema

## Materiali_Anagrafica

| Field | Type |
|-----|-----|
| id | INTEGER |
| categoria | TEXT |
| codice_articolo | TEXT |

Used for **material lookup and category detection**.

---

## Flussi_Ingresso

| Field | Type |
|-----|-----|
| id | INTEGER |
| timestamp_accettazione | TEXT |
| categoria | TEXT |
| codice_articolo | TEXT |
| lotto_id | TEXT |
| data_produzione | TEXT |
| operatore | TEXT |

Stores **all acceptance records**.

---

# 🏷 Supported Material Categories

| Category | Example Prefix |
|--------|--------|
| TESSUTI TESSILI | STT |
| TESSUTI METALLICI | STM |
| BANDINE | STR |
| ALTRO | ALT |

The system is **configuration-driven**, meaning categories can be extended easily.

---

# 🔧 Extending the System

To add a new category:

1️⃣ Add seed data in `database.py`

```python
_SEED_DATA = [
("NEW_CATEGORY", "ABC123")
]
```

2️⃣ Add configuration in `ui.py`

```python
CATEGORY_CONFIG = {
    "NEW_CATEGORY": {...}
}
```

---

# 💬 Contributing

Contributions are welcome!

Possible improvements:

- CSV / Excel export
- Dashboard analytics
- Multi-user network database
- Barcode label printing

---

# 📄 License

MIT.

---

<p align="center">
<strong>Ideato e Realizzato da Pierpaolo Careddu</strong>
</p>
