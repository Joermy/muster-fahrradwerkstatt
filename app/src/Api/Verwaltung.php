<?php

declare(strict_types=1);

namespace Radhaus\Api;

use Radhaus\App;
use Radhaus\Dienste\Auftraege;
use Radhaus\Dienste\Kalender;
use Radhaus\Http\Anfrage;
use Radhaus\Http\Antwort;
use Radhaus\Http\HttpFehler;
use Radhaus\Http\Wegweiser;
use Radhaus\Validierung;

/**
 * Schnittstelle der Verwaltung. Jede schreibende Anfrage braucht neben dem Sitzungs-Cookie
 * (HttpOnly, SameSite=Strict) den CSRF-Token der Sitzung im Kopf X-CSRF-Token.
 */
final class Verwaltung
{
    /** @var array{sitzung: array<string, mixed>, benutzer: array<string, mixed>}|null */
    private ?array $angemeldet = null;
    private string $kennung = '';

    public function __construct(private App $app)
    {
    }

    public function anmelden(Wegweiser $w): void
    {
        $p = '/api/verwaltung';
        $w->weg('POST', "$p/anmelden", $this->login(...));
        $w->weg('POST', "$p/code", $this->code(...));
        $w->weg('POST', "$p/abmelden", $this->abmelden(...));
        $w->weg('GET', "$p/ich", $this->ich(...));
        $w->weg('POST', "$p/passwort", $this->passwort(...));
        $w->weg('POST', "$p/zweifaktor/start", $this->zweifaktorStart(...));
        $w->weg('POST', "$p/zweifaktor/bestaetigen", $this->zweifaktorBestaetigen(...));

        $w->weg('GET', "$p/uebersicht", $this->uebersicht(...));
        $w->weg('GET', "$p/auftraege", $this->auftraege(...));
        $w->weg('POST', "$p/auftraege", $this->auftragAnlegen(...));
        $w->weg('GET', "$p/auftraege/{id}", $this->auftrag(...));
        $w->weg('POST', "$p/auftraege/{id}/status", $this->status(...));
        $w->weg('POST', "$p/auftraege/{id}/angebot", $this->angebot(...));
        $w->weg('POST', "$p/auftraege/{id}/notiz", $this->notiz(...));
        $w->weg('GET', "$p/auftraege/{id}/auskunft", $this->auskunft(...));
        $w->weg('POST', "$p/auftraege/{id}/anonymisieren", $this->anonymisieren(...));
        $w->weg('GET', "$p/kapazitaet", $this->kapazitaet(...));
        $w->weg('POST', "$p/kapazitaet", $this->kapazitaetSetzen(...));
        $w->weg('GET', "$p/widerrufe", $this->widerrufe(...));
        $w->weg('POST', "$p/widerrufe/{id}/erledigt", $this->widerrufErledigt(...));
        $w->weg('GET', "$p/protokoll", $this->protokoll(...));
        $w->weg('GET', "$p/benutzer", $this->benutzer(...));
        $w->weg('POST', "$p/benutzer", $this->benutzerAnlegen(...));
        $w->weg('POST', "$p/benutzer/{id}/sperren", $this->benutzerSperren(...));
        $w->weg('GET', "$p/post", $this->post(...));
    }

    // ------------------------------------------------------------ Anmeldung

    private function login(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('anmeldung', $a->ip);
        $v = Validierung::nur($daten, ['name', 'passwort']);
        $name = $v->text('name', 1, 64);
        $passwort = $daten['passwort'] ?? null;
        if (!is_string($passwort) || $passwort === '' || strlen($passwort) > 512) {
            $v->fehlerMelden('passwort', 'Bitte ausfüllen.');
        }
        $v->pruefen();
        $alte = $a->kekse[$this->app->keksName()] ?? '';
        if ($alte !== '') {
            $this->app->zugang->abmelden($alte);
        }
        $ergebnis = $this->app->zugang->anmelden((string) $name, (string) $passwort);
        $antwort = Antwort::json(['stufe' => $ergebnis['stufe']]);
        $this->keksSetzen($antwort, $ergebnis['kennung'], $ergebnis['stufe'] === 'passwort' ? 300 : 0);
        return $antwort;
    }

    private function code(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('anmeldung', $a->ip);
        Validierung::nur($daten, ['code']);
        $kennung = $a->kekse[$this->app->keksName()] ?? '';
        $neu = $this->app->zugang->zweiterFaktor($kennung, is_string($daten['code'] ?? null) ? $daten['code'] : '');
        $antwort = Antwort::json(['stufe' => 'voll']);
        $this->keksSetzen($antwort, $neu, 0);
        return $antwort;
    }

    private function abmelden(Anfrage $a): Antwort
    {
        $this->pruefen($a, true, false);
        $this->app->zugang->abmelden($this->kennung);
        $antwort = Antwort::json(['ok' => true]);
        $antwort->keks($this->app->keksName(), '', -1, $this->app->sicheresKeks());
        return $antwort;
    }

    private function ich(Anfrage $a): Antwort
    {
        $this->pruefen($a, false, false);
        $b = $this->angemeldet['benutzer'] ?? [];
        // Ersatz für den Cronjob: tägliche Aufgaben beim ersten Aufruf am Tag.
        if ($this->app->aufgaben->faellig()) {
            $this->app->aufgaben->ausfuehren();
        }
        return Antwort::json([
            'name' => $b['name'],
            'anzeigename' => $b['anzeigename'],
            'rolle' => $b['rolle'],
            'zweifaktor' => (bool) $b['totp_aktiv'],
            'passwort_wechseln' => (bool) $b['passwort_wechseln'],
            'csrf' => $this->angemeldet['sitzung']['csrf'] ?? '',
            'entwicklung' => $this->app->konfig->entwicklung(),
        ]);
    }

    private function passwort(Anfrage $a): Antwort
    {
        $daten = $this->pruefen($a, true, false);
        Validierung::nur($daten, ['alt', 'neu']);
        $this->app->zugang->passwortAendern($this->benutzerId(), (string) ($daten['alt'] ?? ''), (string) ($daten['neu'] ?? ''));
        $antwort = Antwort::json(['ok' => true, 'meldung' => 'Passwort geändert. Bitte neu anmelden.']);
        $antwort->keks($this->app->keksName(), '', -1, $this->app->sicheresKeks());
        return $antwort;
    }

    private function zweifaktorStart(Anfrage $a): Antwort
    {
        $this->pruefen($a, true, false);
        return Antwort::json($this->app->zugang->totpVorbereiten($this->benutzerId()));
    }

    private function zweifaktorBestaetigen(Anfrage $a): Antwort
    {
        $daten = $this->pruefen($a, true, false);
        Validierung::nur($daten, ['code']);
        $codes = $this->app->zugang->totpBestaetigen($this->benutzerId(), (string) ($daten['code'] ?? ''));
        return Antwort::json(['ersatzcodes' => $codes]);
    }

    // ------------------------------------------------------------ Aufträge

    private function uebersicht(Anfrage $a): Antwort
    {
        $this->pruefen($a, false);
        $db = $this->app->db;
        $heute = $this->app->uhr->heute();
        $zaehlen = static fn (string $status): int => (int) $db->wert('SELECT COUNT(*) FROM auftraege WHERE status = ?', [$status]);
        $bis = $this->app->uhr->jetzt()->modify('+7 day')->format('Y-m-d');
        $offen = $this->app->auftraege->liste(['offen' => true]);
        $demnaechst = array_values(array_filter($offen, static fn (array $z): bool => $z['termin_datum'] > $heute && $z['termin_datum'] <= $bis));
        usort($demnaechst, static fn (array $x, array $y): int => [$x['termin_datum'], $x['termin_zeit']] <=> [$y['termin_datum'], $y['termin_zeit']]);
        return Antwort::json([
            'heute' => array_values(array_filter($offen, static fn (array $z): bool => $z['termin_datum'] === $heute)),
            'demnaechst' => array_slice($demnaechst, 0, 8),
            'zahlen' => [
                'angefragt' => $zaehlen('angefragt'),
                'bestaetigt' => $zaehlen('bestaetigt'),
                'in_werkstatt' => (int) $db->wert("SELECT COUNT(*) FROM auftraege WHERE status IN ('angenommen', 'in_arbeit', 'wartet_auf_freigabe')"),
                'abholbereit' => $zaehlen('abholbereit'),
                'widerrufe_offen' => (int) $db->wert('SELECT COUNT(*) FROM widerrufe WHERE bearbeitet IS NULL'),
            ],
        ]);
    }

    private function auftraege(Anfrage $a): Antwort
    {
        $this->pruefen($a, false);
        $status = $a->abfrage['status'] ?? null;
        if ($status !== null && !isset(Auftraege::STATUS[$status])) {
            $status = null;
        }
        return Antwort::json(['auftraege' => $this->app->auftraege->liste([
            'status' => $status,
            'offen' => ($a->abfrage['offen'] ?? '') === '1',
            'suche' => isset($a->abfrage['suche']) ? mb_substr($a->abfrage['suche'], 0, 12) : null,
        ])]);
    }

    /** Telefonische oder persönliche Anfrage, von der Werkstatt eingetragen. */
    private function auftragAnlegen(Anfrage $a): Antwort
    {
        $daten = $this->pruefen($a, true);
        $v = Validierung::nur($daten, ['leistung', 'rad', 'datum', 'zeit', 'name', 'email', 'telefon', 'nachricht']);
        $e = [
            'leistung' => $v->auswahl('leistung', $this->app->katalog->leistungen()),
            'rad' => $v->auswahl('rad', $this->app->katalog->raeder()),
            'datum' => $v->datum('datum'),
            'zeit' => $v->uhrzeit('zeit'),
            'name' => $v->name('name'),
            'email' => $v->email('email'),
            'telefon' => $v->telefon('telefon'),
            'nachricht' => $v->text('nachricht', 0, 1000, false, true),
        ];
        $v->pruefen();
        /** @var array{leistung: string, rad: string, datum: string, zeit: string, name: string, email: string, telefon: ?string, nachricht: ?string} $e */
        $ergebnis = $this->app->auftraege->anfragen($e, 'werkstatt');
        $this->app->protokoll->eintragen($this->benutzerId(), 'auftrag_angelegt', $ergebnis['nummer']);
        return Antwort::json(['nummer' => $ergebnis['nummer']], 201);
    }

    private function auftrag(Anfrage $a, string $id): Antwort
    {
        $this->pruefen($a, false);
        return Antwort::json($this->app->auftraege->detail((int) $id, $this->benutzerId()));
    }

    private function status(Anfrage $a, string $id): Antwort
    {
        $daten = $this->pruefen($a, true);
        $v = Validierung::nur($daten, ['status', 'hinweis']);
        $status = $v->auswahl('status', array_keys(Auftraege::STATUS));
        $hinweis = $v->text('hinweis', 0, 300, false, true);
        $v->pruefen();
        $this->app->auftraege->statusSetzen((int) $id, (string) $status, $hinweis, $this->benutzerId());
        return Antwort::json($this->app->auftraege->detail((int) $id, $this->benutzerId()));
    }

    private function angebot(Anfrage $a, string $id): Antwort
    {
        $daten = $this->pruefen($a, true);
        Validierung::nur($daten, ['positionen']);
        $positionen = $daten['positionen'] ?? null;
        if (!is_array($positionen) || $positionen === [] || count($positionen) > 12 || !array_is_list($positionen)) {
            throw HttpFehler::ungueltig(['positionen' => 'Ein bis zwölf Positionen.']);
        }
        $sauber = [];
        foreach ($positionen as $i => $p) {
            if (!is_array($p)) {
                throw HttpFehler::ungueltig(["positionen.$i" => 'Ungültig.']);
            }
            $v = Validierung::nur($p, ['text', 'cent']);
            $text = $v->text('text', 2, 120);
            $cent = $v->ganzzahl('cent', 0, 500000);
            $v->pruefen();
            $sauber[] = ['text' => (string) $text, 'cent' => (int) $cent];
        }
        $this->app->auftraege->angebotErstellen((int) $id, $sauber, $this->benutzerId());
        return Antwort::json($this->app->auftraege->detail((int) $id, $this->benutzerId()), 201);
    }

    private function notiz(Anfrage $a, string $id): Antwort
    {
        $daten = $this->pruefen($a, true);
        $v = Validierung::nur($daten, ['text']);
        $text = $v->text('text', 1, 2000, true, true);
        $v->pruefen();
        $this->app->auftraege->notizHinzufuegen((int) $id, (string) $text, $this->benutzerId());
        return Antwort::json($this->app->auftraege->detail((int) $id, $this->benutzerId()), 201);
    }

    private function auskunft(Anfrage $a, string $id): Antwort
    {
        $this->pruefen($a, false, true, 'inhaber');
        $auftrag = $this->app->auftraege->perId((int) $id);
        if ($auftrag['anonymisiert'] !== null) {
            throw new HttpFehler(409, 'anonymisiert', 'Zu diesem Auftrag sind keine Personendaten mehr gespeichert.');
        }
        $this->app->protokoll->eintragen($this->benutzerId(), 'auskunft_erstellt', (string) $auftrag['nummer']);
        $antwort = Antwort::json($this->app->auftraege->auskunft($auftrag));
        $antwort->kopf['Content-Disposition'] = 'attachment; filename="auskunft-' . $auftrag['nummer'] . '.json"';
        return $antwort;
    }

    private function anonymisieren(Anfrage $a, string $id): Antwort
    {
        $daten = $this->pruefen($a, true, true, 'inhaber');
        Validierung::nur($daten, ['bestaetigung']);
        $auftrag = $this->app->auftraege->perId((int) $id);
        if (($daten['bestaetigung'] ?? null) !== $auftrag['nummer']) {
            throw HttpFehler::ungueltig(['bestaetigung' => 'Zur Bestätigung die Auftragsnummer eintippen.']);
        }
        $this->app->auftraege->anonymisieren((int) $id, $this->benutzerId(), 'verwaltung');
        return Antwort::json($this->app->auftraege->detail((int) $id, $this->benutzerId()));
    }

    // ------------------------------------------------------------ Kapazität

    private function kapazitaet(Anfrage $a): Antwort
    {
        $this->pruefen($a, false);
        return Antwort::json([
            'plan' => $this->app->kalender->kapazitaet(),
            'sperrtage' => $this->app->db->zeilen('SELECT datum, grund FROM sperrtage WHERE datum >= ? ORDER BY datum', [$this->app->uhr->heute()]),
            'tage' => $this->app->kalender->tage(),
        ]);
    }

    private function kapazitaetSetzen(Anfrage $a): Antwort
    {
        $daten = $this->pruefen($a, true, true, 'inhaber');
        Validierung::nur($daten, ['plan', 'sperrtage']);
        $plan = [];
        foreach (is_array($daten['plan'] ?? null) ? $daten['plan'] : [] as $tag => $k) {
            if (!is_numeric($tag) || (int) $tag < 1 || (int) $tag > 7 || !is_array($k)) {
                throw HttpFehler::ungueltig(['plan' => 'Ungültiger Wochentag.']);
            }
            $v = Validierung::nur($k, ['zeiten', 'plaetze']);
            $plaetze = $v->ganzzahl('plaetze', 0, 20);
            $zeiten = $k['zeiten'] ?? [];
            if (!is_array($zeiten) || count($zeiten) > 16) {
                $v->fehlerMelden('zeiten', 'Höchstens 16 Zeiten.');
                $zeiten = [];
            }
            foreach ($zeiten as $z) {
                if (!is_string($z) || preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', $z) !== 1) {
                    $v->fehlerMelden('zeiten', 'Zeiten im Format HH:MM.');
                }
            }
            $v->pruefen();
            $zeiten = array_values(array_unique(array_filter($zeiten, 'is_string')));
            sort($zeiten);
            $plan[(int) $tag] = ['zeiten' => $zeiten, 'plaetze' => (int) $plaetze];
        }
        $sperren = [];
        foreach (is_array($daten['sperrtage'] ?? null) ? $daten['sperrtage'] : [] as $s) {
            if (!is_array($s)) {
                continue;
            }
            $v = Validierung::nur($s, ['datum', 'grund']);
            $datum = $v->datum('datum');
            $grund = $v->text('grund', 1, 60);
            $v->pruefen();
            $sperren[] = [(string) $datum, (string) $grund];
        }
        $this->app->kalender->kapazitaetSetzen($plan);
        if (array_key_exists('sperrtage', $daten)) {
            $this->app->db->transaktion(function () use ($sperren): void {
                $this->app->db->ausfuehren('DELETE FROM sperrtage WHERE datum >= ?', [$this->app->uhr->heute()]);
                foreach ($sperren as [$datum, $grund]) {
                    $this->app->db->ausfuehren('INSERT OR REPLACE INTO sperrtage (datum, grund) VALUES (?, ?)', [$datum, $grund]);
                }
            });
        }
        $this->app->protokoll->eintragen($this->benutzerId(), 'kapazitaet_geaendert');
        return $this->kapazitaet($a);
    }

    // ------------------------------------------------------------ Verwaltung

    private function widerrufe(Anfrage $a): Antwort
    {
        $this->pruefen($a, false);
        return Antwort::json(['widerrufe' => $this->app->widerrufe->liste()]);
    }

    private function widerrufErledigt(Anfrage $a, string $id): Antwort
    {
        $this->pruefen($a, true);
        $this->app->widerrufe->erledigt((int) $id, $this->benutzerId());
        return $this->widerrufe($a);
    }

    private function protokoll(Anfrage $a): Antwort
    {
        $this->pruefen($a, false, true, 'inhaber');
        return Antwort::json(['eintraege' => $this->app->protokoll->letzte(300)]);
    }

    private function benutzer(Anfrage $a): Antwort
    {
        $this->pruefen($a, false, true, 'inhaber');
        return Antwort::json(['benutzer' => $this->app->zugang->benutzerListe()]);
    }

    private function benutzerAnlegen(Anfrage $a): Antwort
    {
        $daten = $this->pruefen($a, true, true, 'inhaber');
        $v = Validierung::nur($daten, ['name', 'anzeigename', 'rolle']);
        $name = $v->text('name', 3, 32);
        $anzeige = $v->name('anzeigename');
        $rolle = $v->auswahl('rolle', ['inhaber', 'werkstatt']);
        $v->pruefen();
        $neu = $this->app->zugang->benutzerAnlegen((string) $name, (string) $anzeige, (string) $rolle, $this->benutzerId());
        return Antwort::json(['id' => $neu['id'], 'startpasswort' => $neu['passwort'], 'hinweis' => 'Das Startpasswort wird nur jetzt angezeigt und muss bei der ersten Anmeldung geändert werden.'], 201);
    }

    private function benutzerSperren(Anfrage $a, string $id): Antwort
    {
        $this->pruefen($a, true, true, 'inhaber');
        $this->app->zugang->benutzerSperren((int) $id, $this->benutzerId());
        return $this->benutzer($a);
    }

    /** Postausgang nur in der Entwicklung, damit sich Mails ohne Mailserver prüfen lassen. */
    private function post(Anfrage $a): Antwort
    {
        $this->pruefen($a, false, true, 'inhaber');
        if (!$this->app->konfig->entwicklung()) {
            throw new HttpFehler(404, 'nicht_gefunden', 'Diese Adresse gibt es nicht.');
        }
        return Antwort::json(['post' => $this->app->post->ausgang()]);
    }

    // ------------------------------------------------------------ Prüfungen

    /**
     * Prüft Sitzung, CSRF-Token und Rolle. Ohne eingerichtete Zwei-Faktor-Anmeldung oder mit
     * Startpasswort sind nur Anmeldung, Passwort und Einrichtung erlaubt.
     *
     * @return array<string, mixed> JSON-Körper bei schreibenden Anfragen
     */
    private function pruefen(Anfrage $a, bool $schreibend, bool $vollerZugang = true, ?string $rolle = null): array
    {
        $this->kennung = $a->kekse[$this->app->keksName()] ?? '';
        $this->angemeldet = $this->app->zugang->pruefen($this->kennung);
        $b = $this->angemeldet['benutzer'];
        if ($schreibend) {
            $token = $a->kopf('x-csrf-token');
            if ($token === '' || !hash_equals((string) $this->angemeldet['sitzung']['csrf'], $token)) {
                throw new HttpFehler(403, 'csrf', 'Die Sitzung ist abgelaufen. Bitte laden Sie die Seite neu.');
            }
        }
        if ($vollerZugang && ((int) $b['totp_aktiv'] !== 1 || (int) $b['passwort_wechseln'] === 1)) {
            throw new HttpFehler(403, 'einrichtung_noetig', 'Bitte zuerst Passwort ändern und Zwei-Faktor-Anmeldung einrichten.');
        }
        if ($rolle !== null && $b['rolle'] !== $rolle) {
            throw new HttpFehler(403, 'keine_berechtigung', 'Dafür fehlt die Berechtigung.');
        }
        return $schreibend ? $a->json() : [];
    }

    private function benutzerId(): int
    {
        return (int) ($this->angemeldet['benutzer']['id'] ?? 0);
    }

    private function keksSetzen(Antwort $antwort, string $kennung, int $lebensdauer): void
    {
        $antwort->keks($this->app->keksName(), $kennung, $lebensdauer, $this->app->sicheresKeks());
    }
}
