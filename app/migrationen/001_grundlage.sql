-- Personenbezogene Felder (*_vs) sind mit dem Tresor verschlüsselt.
-- Zeiten sind ISO 8601 in Europe/Berlin, Datumsangaben YYYY-MM-DD.

CREATE TABLE auftraege (
    id              INTEGER PRIMARY KEY,
    nummer          TEXT    NOT NULL UNIQUE,
    token_hash      BLOB    NOT NULL UNIQUE,
    leistung        TEXT    NOT NULL,
    rad             TEXT    NOT NULL,
    termin_datum    TEXT    NOT NULL,
    termin_zeit     TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'angefragt',
    name_vs         BLOB,
    email_vs        BLOB,
    email_index     BLOB,
    telefon_vs      BLOB,
    nachricht_vs    BLOB,
    quelle          TEXT    NOT NULL DEFAULT 'website',
    erstellt        TEXT    NOT NULL,
    geaendert       TEXT    NOT NULL,
    abgeschlossen   TEXT,
    anonymisiert    TEXT
);
CREATE INDEX auftraege_termin ON auftraege (termin_datum, termin_zeit);
CREATE INDEX auftraege_status ON auftraege (status);
CREATE INDEX auftraege_email ON auftraege (email_index);

CREATE TABLE verlauf (
    id          INTEGER PRIMARY KEY,
    auftrag_id  INTEGER NOT NULL REFERENCES auftraege (id) ON DELETE CASCADE,
    status      TEXT    NOT NULL,
    hinweis_vs  BLOB,
    zeit        TEXT    NOT NULL
);
CREATE INDEX verlauf_auftrag ON verlauf (auftrag_id);

CREATE TABLE angebote (
    id                  INTEGER PRIMARY KEY,
    auftrag_id          INTEGER NOT NULL REFERENCES auftraege (id) ON DELETE CASCADE,
    positionen          TEXT    NOT NULL,
    summe_cent          INTEGER NOT NULL,
    erstellt            TEXT    NOT NULL,
    entscheidung        TEXT,
    entschieden         TEXT,
    vorzeitiger_beginn  INTEGER NOT NULL DEFAULT 0,
    belehrung_fassung   TEXT,
    vertrag_pruefsumme  TEXT
);
CREATE INDEX angebote_auftrag ON angebote (auftrag_id);

CREATE TABLE widerrufe (
    id              INTEGER PRIMARY KEY,
    eingang         TEXT    NOT NULL,
    auftragsnummer  TEXT    NOT NULL,
    name_vs         BLOB    NOT NULL,
    email_vs        BLOB    NOT NULL,
    grund_vs        BLOB,
    auftrag_id      INTEGER REFERENCES auftraege (id) ON DELETE SET NULL,
    bearbeitet      TEXT,
    oeffentliche_id TEXT    NOT NULL UNIQUE
);

CREATE TABLE notizen (
    id          INTEGER PRIMARY KEY,
    auftrag_id  INTEGER NOT NULL REFERENCES auftraege (id) ON DELETE CASCADE,
    benutzer_id INTEGER REFERENCES benutzer (id) ON DELETE SET NULL,
    text_vs     BLOB    NOT NULL,
    zeit        TEXT    NOT NULL
);

CREATE TABLE benutzer (
    id                  INTEGER PRIMARY KEY,
    name                TEXT    NOT NULL UNIQUE,
    anzeigename         TEXT    NOT NULL,
    rolle               TEXT    NOT NULL CHECK (rolle IN ('inhaber', 'werkstatt')),
    passwort_hash       TEXT    NOT NULL,
    passwort_wechseln   INTEGER NOT NULL DEFAULT 0,
    totp_vs             BLOB,
    totp_aktiv          INTEGER NOT NULL DEFAULT 0,
    totp_letzter_schritt INTEGER NOT NULL DEFAULT 0,
    fehlversuche        INTEGER NOT NULL DEFAULT 0,
    gesperrt_bis        TEXT,
    aktiv               INTEGER NOT NULL DEFAULT 1,
    erstellt            TEXT    NOT NULL,
    letzte_anmeldung    TEXT
);

CREATE TABLE ersatzcodes (
    id          INTEGER PRIMARY KEY,
    benutzer_id INTEGER NOT NULL REFERENCES benutzer (id) ON DELETE CASCADE,
    code_hash   BLOB    NOT NULL,
    verwendet   TEXT
);

CREATE TABLE sitzungen (
    id_hash     BLOB    PRIMARY KEY,
    benutzer_id INTEGER NOT NULL REFERENCES benutzer (id) ON DELETE CASCADE,
    stufe       TEXT    NOT NULL CHECK (stufe IN ('passwort', 'voll')),
    csrf        TEXT    NOT NULL,
    erstellt    INTEGER NOT NULL,
    zuletzt     INTEGER NOT NULL
);

CREATE TABLE kapazitaet (
    wochentag   INTEGER PRIMARY KEY CHECK (wochentag BETWEEN 1 AND 7),
    zeiten      TEXT    NOT NULL,
    plaetze     INTEGER NOT NULL CHECK (plaetze BETWEEN 0 AND 20)
);

CREATE TABLE sperrtage (
    datum   TEXT PRIMARY KEY,
    grund   TEXT NOT NULL
);

CREATE TABLE einwilligungen (
    id          TEXT    PRIMARY KEY,
    fassung     TEXT    NOT NULL,
    medien      INTEGER NOT NULL,
    erstellt    TEXT    NOT NULL,
    geaendert   TEXT    NOT NULL
);

CREATE TABLE protokoll (
    id          INTEGER PRIMARY KEY,
    zeit        TEXT    NOT NULL,
    benutzer_id INTEGER,
    aktion      TEXT    NOT NULL,
    objekt      TEXT    NOT NULL DEFAULT '',
    details     TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX protokoll_zeit ON protokoll (zeit);

CREATE TABLE drossel (
    schluessel  BLOB    NOT NULL,
    eimer       TEXT    NOT NULL,
    fenster     INTEGER NOT NULL,
    anzahl      INTEGER NOT NULL,
    PRIMARY KEY (schluessel, eimer, fenster)
);

CREATE TABLE post (
    id          INTEGER PRIMARY KEY,
    an_vs       BLOB    NOT NULL,
    betreff     TEXT    NOT NULL,
    text_vs     BLOB    NOT NULL,
    art         TEXT    NOT NULL,
    erstellt    TEXT    NOT NULL,
    versendet   TEXT,
    fehler      TEXT
);

CREATE TABLE aufgaben (
    name        TEXT PRIMARY KEY,
    zuletzt     TEXT NOT NULL
);
