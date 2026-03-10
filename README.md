# Sistema di Accettazione Digitale — Rinforzi
*Registrazione ultra-rapida per materiali semi-lavorati in ingresso al laboratorio.*

## Descrizione
Un'applicazione desktop moderna e veloce, progettata per ottimizzare la fase di accettazione nel laboratorio industriale. Il sistema permette agli operatori di registrare l'ingresso di materiali come tessuti tessili, tessuti metallici e bandine in meno di 10 secondi per articolo. 

L'interfaccia è pensata in ottica "keyboard-first" ed è altamente ottimizzata per l'utilizzo in accoppiata con scanner barcode USB (in emulazione tastiera HID), offrendo al contempo una robusta modalità manuale per le etichette sprovviste di codice a barre. Sviluppata in Python sfruttando PySide6 per la UI e SQLite3 per la persistenza dei dati.

---

## Funzionalità principali
* **Scansione barcode USB (HID) con auto-rilevamento:** Identificazione istantanea della categoria del materiale tramite prefissi noti (es. `STT` → Tessuti Tessili, `STM` → Tessuti Metallici, `STR` → Bandine, `ALT` → Altro).
* **Smart Split Barcode:** Divisione automatica di codice articolo e numero di lotto se il barcode scansionato contiene separatori standard (`\t`, `|`, `;`).
* **Modalità Manuale:** Un'interfaccia di fallback per l'inserimento libero dei dati in caso di etichette compilate a mano.
* **Campo Operatore Persistente:** L'operatore imposta il proprio identificativo a inizio turno; il campo rimane memorizzato tra una scansione e l'altra.
* **Registro Accettazioni:** Una schermata dedicata per visualizzare lo storico dei flussi in ingresso, completa di barra di ricerca in tempo reale ed eliminazione sicura dei record errati.
* **Feedback visivo non bloccante:** Notifiche "Toast" a comparsa rapida per conferme o errori di validazione (nessun popup bloccante che rallenta il flusso).
* **Debounce anti-doppia scansione:** Blocco temporaneo di 500ms dopo ogni salvataggio per ignorare keystroke ridondanti e prevenire duplicati nel database.
* **Database SQLite:** Auto-creazione delle tabelle `Flussi_Ingresso` e `Materiali_Anagrafica` al primo avvio, con inserimento automatico dei dati di test (seed).

---

## Requisiti
- **Python 3.10+**
- **PySide6**

## Installazione ed esecuzione

1. Clona il repository e posizionati nella cartella del progetto:
   ```bash
   git clone [https://github.com/0xc3rat/test_accettazione.git](https://github.com/0xc3rat/test_accettazione.git)
   cd test_accettazione
