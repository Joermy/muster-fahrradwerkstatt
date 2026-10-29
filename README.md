# Radhaus Fuhse — Musterwebsite mit Terminbuchung und Verwaltung

Eine Musterwebsite für eine Fahrradwerkstatt in Peine. Der Betrieb ist frei erfunden: Name,
Inhaberin, Anschrift, Preise und alle Aufträge gibt es nicht. Domains enden auf `.example`,
die Telefonnummern stammen aus dem Bereich, den die Bundesnetzagentur für Filme und Werbung
freihält. Die Seite gehört zu keinem Kundenauftrag und bietet nichts an.

Anders als die übrigen Musterseiten arbeitet diese mit echten Kundendaten: Terminbuchung,
Reparaturstatus, Kostenvoranschläge mit Online-Freigabe, Widerrufsbutton und eine Verwaltung
mit Zwei-Faktor-Anmeldung, Rollen und Zugriffsprotokoll.

**Vorführfassung:** <https://joermy.github.io/muster-fahrradwerkstatt/>
Dort läuft die Schnittstelle im Browser nach, weil GitHub Pages kein PHP ausführt. Eingaben
bleiben im Tab. Zugang zur Verwaltung unter `/verwaltung/`: Benutzer `inhaberin`, Passwort
`Werkstatt-Vorfuehrung`, den Code der Authenticator-App zeigt die Anmeldeseite an.

## Das Besondere

Die Startseite ist eine fotorealistische Bildfolge statt Echtzeit-3D: ein vollgefedertes E-MTB
von 2026 im Montageständer einer hellen Werkstatt, gebaut per Skript in Blender und Bild für
Bild mit Cycles pfadverfolgt (globale Beleuchtung, Schärfentiefe, Bewegungsunschärfe). Beim
Scrollen zeichnet die Seite das passende Bild in ein Canvas und blendet zwischen zwei Bildern
über – wie bei den Produktseiten großer Hersteller.

- **Rad (erfunden, „TRAIL·E 9“):** Carbon-Rahmen mit verschmolzenen Rohren und Akku im
  Unterrohr, Horst-Link-Hinterbau mit Dämpfer, Federgabel mit Bronze-Standrohren, 29"-Reifen
  mit Stollenprofil und geprägter Flanke, Vierkolbenbremsen, Schaltwerk ohne Schaltauge,
  Leitungen durch den Steuersatz, Aufkleber, feiner Staub. Die Kette ist gelegt: 130 Glieder
  über Kettenblatt, Ritzel und Röllchen, der Käfig hält die Länge beim Schalten.
- **Werkstatt:** geschliffener Beton mit Fugen und Ölflecken, weiß gestrichener
  Kalksandstein, Stahlfensterband mit Sonnenflecken, Werkbank mit Eichenplatte,
  Werkzeugwand aus Birke-Multiplex, Regale, Laufräder an Haken, Montageständer mit Stahlteller.

Beim Scrollen geht das Rad einmal durch die Werkstatt:

1. **Diagnose** — eine Laserlinie tastet das Rad ab, Befunde erscheinen am Bauteil
2. **Zerlegen** — Laufräder, Antrieb, Cockpit, Dämpfer und Akku lösen sich
3. **Antrieb** — Schaltvorgang durch alle zwölf Gänge, Übersetzung live
4. **Bremse** — das Vorderrad dreht, die Scheibe glüht und läuft danach an
5. **Laufrad** — Seitenschlag sichtbar, Speichenspannung als Farbkarte, dann zentriert
6. **Akku** — der Akku gleitet aus dem Unterrohr
7. **Übergabe** — Scheinwerfer an, abholbereit

Es gibt keinen Ladebildschirm: Das erste Bild steht im HTML, die übrigen laden grob zu fein
nach (jedes 24., 8., 4., 2., dann alle), Scrollen geht vom ersten Moment an. Bauteile lassen
sich antippen; die Karte zeigt Preis und Leistung. Auf kleinen Bildschirmen und bei langsamer
Verbindung lädt eine kleinere Folge, mit „Daten sparen“ oder reduzierter Bewegung nur ein
Bild je Schritt. Ohne JavaScript bleibt das Standbild. Wie es dazu kam:
[`planung/realismus-werkstatt.md`](planung/realismus-werkstatt.md).

## Funktionen

| Für Kundinnen und Kunden | Für die Werkstatt |
| --- | --- |
| Termin in vier Schritten, freie Zeiten live | Übersicht mit Tagesterminen und offenen Vorgängen |
| Status-Link per Mail, ohne Konto | Aufträge filtern, Status setzen, interne Notizen |
| Kostenvoranschlag online freigeben oder ablehnen | Kostenvoranschlag aus der Preisliste zusammenstellen |
| Vertragsbestätigung mit Widerrufsbelehrung | Wochenplan, Schließtage, Belegung der nächsten vier Wochen |
| Widerrufsbutton nach § 356a BGB | Widerrufe mit Eingangszeit und Zuordnung |
| Eigene Daten herunterladen oder löschen | Auskunft als Datei, Personendaten löschen |
| Cookie-Einstellungen jederzeit änderbar | Zugriffsprotokoll, Benutzer und Rollen |

## Sicherheit

- **Verschlüsselung:** Name, E-Mail, Telefon, Nachrichten, Notizen und der TOTP-Schlüssel
  liegen mit XChaCha20-Poly1305 (libsodium) in der Datenbank, jedes Feld an seinen Auftrag
  gebunden. Gesucht wird über einen HMAC-Index, nie über Klartext.
- **Anmeldung:** Argon2id, Zwei-Faktor (TOTP nach RFC 6238) mit Schutz vor Wiederverwendung,
  acht Ersatzcodes, Sperre nach fünf Fehlversuchen, gleiche Antwortzeit für unbekannte Namen.
  Startpasswort und Zwei-Faktor sind bei der ersten Anmeldung Pflicht.
- **Sitzungen:** Zufallskennung im Cookie `__Host-` mit HttpOnly, Secure und SameSite=Strict,
  Ablauf nach 30 Minuten ohne Aktivität, CSRF-Token für jede Änderung, Prüfung von Origin
  und Sec-Fetch-Site.
- **Eingaben:** nur JSON, höchstens 64 KB, unbekannte Felder werden abgelehnt, Steuer- und
  Richtungszeichen entfernt. Datenbankzugriffe nur mit Platzhaltern. Ausgaben im Browser nur
  über `textContent`.
- **Missbrauch:** Drosselung je Absender (Schlüssel aus IP und Tagesgeheimnis, die IP selbst
  wird nicht gespeichert), Lockfeld und signierte Mindestzeit statt Captcha.
- **Auslieferung:** strenge Content-Security-Policy ohne Inline-Skripte und -Stile, HSTS,
  `frame-ancestors 'none'`, nur `index.php` im Webroot, `.env` und Datenbank außerhalb.
- **Sicherungen:** täglich, verschlüsselt, Veränderungen fallen beim Zurückspielen auf.

## Datenschutz

Keine Fremdanbieter, keine Besucherzählung, keine Cookies außer der Sitzung der Verwaltung.
Die Karte von OpenStreetMap lädt erst nach Klick oder Einwilligung. Kontaktdaten werden 30 Tage
nach abgesagten Terminen und 24 Monate nach der Abholung automatisch gelöscht,
Widerrufsnachweise nach drei Jahren. Kundinnen und Kunden können ihre Daten selbst
herunterladen (Art. 15 und 20 DSGVO) und löschen (Art. 17 DSGVO).

## Aufbau

| Ordner | Inhalt |
| --- | --- |
| `app/src/` | PHP 8.3 ohne Framework: Schnittstelle, Dienste, Verschlüsselung, Datenbank |
| `app/migrationen/` | SQLite-Schema |
| `app/daten/` | Leistungen und Preise, erfundene Vorführdaten |
| `vorlagen/` | Seiten und Rahmen; `bin/bauen.php` macht daraus `public/` und `docs/` |
| `public/` | Webroot für den eigenen Server, einziges PHP: `index.php` |
| `public/assets/js/werkstatt/` | Bildfolgen-Spieler und Zeitleiste der Startseite |
| `public/assets/werkstatt/` | gerenderte Bildfolge (WebP, zwei Größen), Lage der Befunde und Markierungen |
| `public/assets/js/verwaltung/` | Verwaltung als Einzelseite |
| `vorlagen/vorfuehrung/` | nachgebaute Schnittstelle, landet nur in `docs/` |
| `docs/` | Vorführfassung für GitHub Pages, nicht für Suchmaschinen |
| `konfig/` | Sicherheitsköpfe, Beispiel für nginx |
| `scripts/szene/` | Blender-Szene per Skript: Rad, Werkstatt, Materialien, Kette, Zeitleiste |
| `scripts/rendern.py`, `scripts/kodieren.py` | Bildfolge rendern und für das Web kodieren |
| `planung/` | Recherche und Plan zur Startseite |
| `tests/` | eigener Testlauf ohne Abhängigkeiten |

## Ansehen

Doppelklick auf `Start Website.bat`. Mit PHP startet die echte Fassung samt Datenbank und
Verwaltung, ohne PHP die Vorführfassung. Oder von Hand:

```bash
php bin/einrichten.php --vorfuehrdaten   # .env mit eigenem Schlüssel, Konto, erfundene Aufträge
php bin/bauen.php
php -S 127.0.0.1:8094 -t public bin/dev-router.php
```

Dann `http://127.0.0.1:8094/` öffnen, die Verwaltung liegt unter `/verwaltung/`. Mails landen
im Testbetrieb im Postausgang der Verwaltung. Benötigt PHP 8.3 mit `sodium`, `pdo_sqlite` und
`mbstring`.

## Auf einen Server bringen

Gedacht für einen verwalteten Server (z. B. Hetzner Managed Server mit Apache) oder einen
eigenen Server mit nginx und PHP-FPM.

1. Alles außer `docs/`, `tests/` und `scripts/` hochladen, z. B. nach `/srv/radhaus/`.
2. Webroot auf `public/` stellen. Apache liest `public/.htaccess`, für nginx liegt
   `konfig/nginx.conf` bei.
3. `php bin/einrichten.php` legt die `.env` mit einem neuen Schlüssel und das Konto der
   Inhaberin an. In der `.env` Adresse und Mailempfänger eintragen.
4. Den Schlüssel `APP_SCHLUESSEL` getrennt aufbewahren. Ohne ihn sind Datenbank und
   Sicherungen nicht lesbar.
5. Cronjobs anlegen:

   ```
   15 3 * * * php /srv/radhaus/bin/aufgaben.php
   30 3 * * * php /srv/radhaus/bin/sicherung.php
   ```

6. `php bin/pruefen.php` prüft Köpfe, Webroot und `.env`.
7. Server-Protokolle nach sieben Tagen löschen lassen; bei Apache zusätzlich
   `ServerTokens Prod`, falls der Anbieter das erlaubt.

## Prüfen

```bash
php tests/lauf.php                      # 84 Tests: Verschlüsselung, Anmeldung, Fristen, Schnittstelle
phpstan analyse -c phpstan.neon         # Stufe 8
php bin/pruefen.php                     # Auslieferung
```

## Bildfolge neu rendern

Braucht Python 3.13 mit Blender als Modul (oder Blender 5.2 selbst) und etwas Geduld: auf vier
CPU-Kernen etwa zwei Minuten je Bild, 193 Bilder.

```bash
pip install bpy==5.2.3 pillow fonttools brotli
python scripts/studio-test.py seite antrieb       # nur das Rad im Studio, zum Prüfen von Änderungen
python scripts/rendern.py --probe                 # ein Bild je Kapitel nach var/szene/proben/
python scripts/rendern.py                         # ganze Folge, fortsetzbar, grob zu fein
python scripts/kodieren.py                        # WebP, Manifest, Standbilder nach public/ und docs/
```

In der Blender-Oberfläche oder über Blender MCP laufen dieselben Skripte im Hintergrund:
`blender -b -P scripts/rendern.py -- --probe`. Die Formeln der Zeitleiste stehen zweimal, in
`scripts/szene/regie.py` und `public/assets/js/werkstatt/zeitleiste.js`; wer eine ändert,
ändert beide.

## Lizenzen

qrcode-generator von Kazuhiko Arase (MIT), Schrift Barlow (SIL Open Font License, auch in
den gerenderten Aufklebern). Die Lizenztexte liegen neben den Dateien in `public/assets/`.
Rad, Werkstatt, Materialien, die gerenderten Bilder und alle Texte sind für diese Seite
entstanden; es stecken keine fremden Modelle, Texturen oder Fotos darin.
