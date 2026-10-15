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

Die Startseite zeigt ein E-Bike im Montageständer, vollständig als 3D-Modell gebaut (Blender
per Skript, rund 255 000 Dreiecke): Rahmen mit Metallic-Lack unter Klarlack, Federgabel mit
goldenen Standrohren, 12-fach-Antrieb, Scheibenbremsen, Mittelmotor und herausnehmbarer Akku.
Die Kette ist physikalisch gelegt: 132 Glieder laufen über Kettenblatt, Ritzel und die beiden
Schaltröllchen, der Käfig des Schaltwerks hält die Länge beim Schalten.

Beim Scrollen geht das Rad einmal durch die Werkstatt:

1. **Diagnose** — ein Lichtvorhang tastet das Rad ab, Befunde erscheinen am Bauteil
2. **Zerlegen** — Laufräder, Antrieb, Cockpit und Akku lösen sich nacheinander
3. **Antrieb** — Schaltvorgang durch alle zwölf Gänge, Übersetzung live
4. **Bremse** — Prüfstand, die Scheibe glüht und läuft danach blau an
5. **Laufrad** — Seitenschlag sichtbar, Speichenspannung als Farbkarte, dann zentriert
6. **Akku** — der Akku kommt heraus, Energie fließt zum Motor
7. **Übergabe** — Scheinwerfer an, abholbereit

Bauteile lassen sich antippen; die Karte zeigt Preis und Leistung dazu. Ziehen dreht die
Ansicht. Ein Wächter senkt Schärfe, Auflösung, Glühen und Schatten, wenn die Bildrate fällt.
Ohne WebGL 2 steht ein Standbild, bei reduzierter Bewegung entfällt die Kamerafahrt.

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
| `public/assets/js/rad/` | 3D-Werkstatt (Three.js): Bühne, Licht, Materialien, Kette, Regie, Effekte |
| `public/assets/js/verwaltung/` | Verwaltung als Einzelseite |
| `vorlagen/vorfuehrung/` | nachgebaute Schnittstelle, landet nur in `docs/` |
| `docs/` | Vorführfassung für GitHub Pages, nicht für Suchmaschinen |
| `konfig/` | Sicherheitsköpfe, Beispiel für nginx |
| `scripts/modell-bauen.py` | baut das E-Bike in Blender (`pip install bpy`) |
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

## Modell neu bauen

```bash
pip install bpy
python scripts/modell-bauen.py
npx gltfpack -i var/rad-roh.glb -o public/assets/modelle/rad.glb -cc -kn -km -ke -kv -vtf
```

## Lizenzen

Three.js (MIT), qrcode-generator von Kazuhiko Arase (MIT), Schrift Barlow
(SIL Open Font License). Die Lizenztexte liegen neben den Dateien in `public/assets/`.
Das 3D-Modell, die Texturen und alle Texte sind für diese Seite entstanden.
