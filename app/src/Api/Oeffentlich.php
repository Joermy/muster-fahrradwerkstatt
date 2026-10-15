<?php

declare(strict_types=1);

namespace Radhaus\Api;

use Radhaus\App;
use Radhaus\Dienste\Einwilligungen;
use Radhaus\Http\Anfrage;
use Radhaus\Http\Antwort;
use Radhaus\Http\HttpFehler;
use Radhaus\Http\Wegweiser;
use Radhaus\Validierung;

/**
 * Schnittstelle für Besucher. Ohne Cookies: der Zugang zum eigenen Auftrag läuft über
 * den Link-Token im JSON-Körper, nie über die Adresse (sonst stünde er in Server-Logs).
 */
final class Oeffentlich
{
    /** Mindestzeit zwischen Laden des Formulars und Absenden, in Sekunden. */
    public const MINDESTZEIT = 4;

    public function __construct(private App $app)
    {
    }

    public function anmelden(Wegweiser $w): void
    {
        $w->weg('GET', '/api/termine', $this->termine(...));
        $w->weg('POST', '/api/anfragen', $this->anfrage(...));
        $w->weg('POST', '/api/status', $this->status(...));
        $w->weg('POST', '/api/status/absagen', $this->absagen(...));
        $w->weg('POST', '/api/status/freigabe', $this->freigabe(...));
        $w->weg('POST', '/api/status/auskunft', $this->auskunft(...));
        $w->weg('POST', '/api/status/loeschen', $this->loeschen(...));
        $w->weg('POST', '/api/status/link', $this->link(...));
        $w->weg('POST', '/api/widerruf', $this->widerruf(...));
        $w->weg('POST', '/api/einwilligung', $this->einwilligung(...));
    }

    private function termine(Anfrage $a): Antwort
    {
        $this->app->drossel->zaehlen('termine', $a->ip);
        return Antwort::json([
            'tage' => $this->app->kalender->tage(),
            // Signierter Zeitstempel: zu schnelles Absenden verrät Formular-Roboter, ohne Captcha.
            'formular' => $this->app->tresor->signieren((string) $this->app->uhr->zeitstempel()),
        ]);
    }

    private function anfrage(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('anfrage', $a->ip);
        $v = Validierung::nur($daten, ['leistung', 'rad', 'datum', 'zeit', 'name', 'email', 'telefon', 'nachricht', 'firma', 'formular']);

        // Lockfeld "firma" ist für Menschen unsichtbar.
        $falle = $daten['firma'] ?? '';
        $signiert = is_string($daten['formular'] ?? null) ? $this->app->tresor->signaturPruefen($daten['formular']) : null;
        $alter = $signiert === null ? -1 : $this->app->uhr->zeitstempel() - (int) $signiert;
        if ($falle !== '' || $alter < self::MINDESTZEIT || $alter > 7200) {
            $this->app->protokoll->eintragen(null, 'anfrage_verworfen', '', $falle !== '' ? 'lockfeld' : 'zeit');
            throw new HttpFehler(422, 'bitte_erneut', 'Das Formular ist abgelaufen. Bitte laden Sie die Seite neu und senden Sie es noch einmal.');
        }

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
        $ergebnis = $this->app->auftraege->anfragen($e);
        return Antwort::json($ergebnis, 201);
    }

    private function status(Anfrage $a): Antwort
    {
        $auftrag = $this->auftragAus($a);
        return Antwort::json($this->app->auftraege->kundenansicht($auftrag));
    }

    private function absagen(Anfrage $a): Antwort
    {
        $token = $this->token($a, ['token']);
        $this->app->auftraege->absagen($token);
        return Antwort::json(['ok' => true]);
    }

    private function freigabe(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('status', $a->ip);
        $v = Validierung::nur($daten, ['token', 'angebot', 'annehmen', 'vorzeitig']);
        $token = is_string($daten['token'] ?? null) ? $daten['token'] : '';
        $angebot = $v->ganzzahl('angebot', 1, PHP_INT_MAX);
        $annehmen = $v->wahrheit('annehmen');
        $vorzeitig = $v->wahrheit('vorzeitig');
        $v->pruefen();
        return Antwort::json($this->app->auftraege->angebotEntscheiden($token, (int) $angebot, $annehmen, $vorzeitig));
    }

    private function auskunft(Anfrage $a): Antwort
    {
        $auftrag = $this->auftragAus($a);
        $this->app->protokoll->eintragen(null, 'kunde_auskunft', (string) $auftrag['nummer']);
        $antwort = Antwort::json($this->app->auftraege->auskunft($auftrag));
        $antwort->kopf['Content-Disposition'] = 'attachment; filename="radhaus-' . $auftrag['nummer'] . '.json"';
        return $antwort;
    }

    private function loeschen(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('status', $a->ip);
        Validierung::nur($daten, ['token', 'bestaetigung']);
        if (($daten['bestaetigung'] ?? null) !== 'LÖSCHEN') {
            throw HttpFehler::ungueltig(['bestaetigung' => 'Bitte LÖSCHEN eintippen.']);
        }
        return Antwort::json($this->app->auftraege->loeschenDurchKunde(is_string($daten['token'] ?? null) ? $daten['token'] : ''));
    }

    private function link(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('link', $a->ip);
        $v = Validierung::nur($daten, ['nummer', 'email']);
        $nummer = strtoupper((string) $v->text('nummer', 12, 12));
        $email = $v->email('email');
        if (preg_match('/^RF-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/', $nummer) !== 1) {
            $v->fehlerMelden('nummer', 'Die Nummer hat die Form RF-XXXX-XXXX.');
        }
        $v->pruefen();
        $this->app->auftraege->linkErneuern($nummer, (string) $email);
        return Antwort::json(['ok' => true, 'meldung' => 'Wenn Nummer und E-Mail-Adresse zusammenpassen, ist ein neuer Link unterwegs.']);
    }

    private function widerruf(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('widerruf', $a->ip);
        $v = Validierung::nur($daten, ['name', 'nummer', 'email', 'grund']);
        $name = $v->name('name');
        $nummer = strtoupper((string) $v->text('nummer', 6, 20));
        $email = $v->email('email');
        $grund = $v->text('grund', 0, 500, false, true);
        if ($nummer !== '' && preg_match('/^[A-Z0-9-]{6,20}$/', $nummer) !== 1) {
            $v->fehlerMelden('nummer', 'Bitte die Auftragsnummer aus Ihrer Mail angeben, z. B. RF-ABCD-EFGH.');
        }
        $v->pruefen();
        return Antwort::json($this->app->widerrufe->einreichen((string) $name, $nummer, (string) $email, $grund), 201);
    }

    private function einwilligung(Anfrage $a): Antwort
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('einwilligung', $a->ip);
        $v = Validierung::nur($daten, ['id', 'fassung', 'medien']);
        $medien = $v->wahrheit('medien');
        if (!Einwilligungen::gueltigeId($daten['id'] ?? null) || ($daten['fassung'] ?? null) !== Einwilligungen::FASSUNG) {
            throw HttpFehler::ungueltig(['id' => 'Ungültige Kennung oder Fassung.']);
        }
        $v->pruefen();
        $this->app->einwilligungen->speichern((string) $daten['id'], Einwilligungen::FASSUNG, $medien);
        return Antwort::json(['ok' => true]);
    }

    // ------------------------------------------------------------------

    /** @param list<string> $erlaubt */
    private function token(Anfrage $a, array $erlaubt): string
    {
        $daten = $a->json();
        $this->app->drossel->zaehlen('status', $a->ip);
        Validierung::nur($daten, $erlaubt);
        $token = $daten['token'] ?? null;
        if (!is_string($token)) {
            throw new HttpFehler(404, 'unbekannter_link', 'Dieser Link ist ungültig oder abgelaufen.');
        }
        return $token;
    }

    /** @return array<string, mixed> */
    private function auftragAus(Anfrage $a): array
    {
        return $this->app->auftraege->perTokenOderFehler($this->token($a, ['token']));
    }
}
