<?php

declare(strict_types=1);

namespace Radhaus;

use Radhaus\Api\Oeffentlich;
use Radhaus\Api\Verwaltung;
use Radhaus\Daten\Datenbank;
use Radhaus\Dienste\Aufgaben;
use Radhaus\Dienste\Auftraege;
use Radhaus\Dienste\Einwilligungen;
use Radhaus\Dienste\Kalender;
use Radhaus\Dienste\Katalog;
use Radhaus\Dienste\Post;
use Radhaus\Dienste\Protokoll;
use Radhaus\Dienste\Sicherung;
use Radhaus\Dienste\Widerrufe;
use Radhaus\Dienste\Zugang;
use Radhaus\Http\Anfrage;
use Radhaus\Http\Antwort;
use Radhaus\Http\HttpFehler;
use Radhaus\Http\Wegweiser;
use Radhaus\Sicherheit\Drossel;
use Radhaus\Sicherheit\Tresor;
use Throwable;

/** Baut alle Dienste zusammen und beantwortet Anfragen an /api/. */
final class App
{
    public readonly Datenbank $db;
    public readonly Tresor $tresor;
    public readonly Katalog $katalog;
    public readonly Kalender $kalender;
    public readonly Protokoll $protokoll;
    public readonly Post $post;
    public readonly Drossel $drossel;
    public readonly Auftraege $auftraege;
    public readonly Widerrufe $widerrufe;
    public readonly Einwilligungen $einwilligungen;
    public readonly Zugang $zugang;
    public readonly Aufgaben $aufgaben;
    public readonly Sicherung $sicherung;
    private Wegweiser $wege;

    public function __construct(public readonly Konfiguration $konfig, public readonly Uhr $uhr = new Uhr())
    {
        $wurzel = $konfig->text('WURZEL');
        $this->db = new Datenbank($konfig->datenbankPfad());
        $this->db->migrieren($wurzel . '/app/migrationen');
        $this->tresor = new Tresor($konfig->hauptschluessel());
        $this->katalog = new Katalog($wurzel . '/app/daten/leistungen.json');
        $this->kalender = new Kalender($this->db, $uhr);
        $this->protokoll = new Protokoll($this->db, $uhr);
        $this->post = new Post($this->db, $this->tresor, $uhr, $konfig);
        $this->drossel = new Drossel($this->db, $this->tresor, $uhr);
        $this->auftraege = new Auftraege($this->db, $this->tresor, $uhr, $this->kalender, $this->katalog, $this->post, $this->protokoll, $konfig);
        $this->widerrufe = new Widerrufe($this->db, $this->tresor, $uhr, $this->post, $this->protokoll, $konfig);
        $this->einwilligungen = new Einwilligungen($this->db, $uhr);
        $this->zugang = new Zugang($this->db, $this->tresor, $uhr, $this->protokoll);
        $this->sicherung = new Sicherung($this->db, $this->tresor, $uhr);
        $this->aufgaben = new Aufgaben($this->db, $uhr, $this->auftraege, $this->widerrufe, $this->drossel, $this->zugang, $this->protokoll);

        if ($this->db->wert('SELECT COUNT(*) FROM kapazitaet') === 0) {
            $this->kalender->kapazitaetSetzen(Kalender::standardKapazitaet());
        }

        $this->wege = new Wegweiser();
        (new Oeffentlich($this))->anmelden($this->wege);
        (new Verwaltung($this))->anmelden($this->wege);
    }

    public function beantworten(Anfrage $a): Antwort
    {
        try {
            $this->herkunftPruefen($a);
            $antwort = $this->wege->leiten($a);
        } catch (HttpFehler $f) {
            $antwort = Antwort::fehler($f);
        } catch (Throwable $f) {
            // Ins Server-Log nur Art und Ort, keine Inhalte der Anfrage.
            error_log('radhaus: ' . $f::class . ' in ' . basename($f->getFile()) . ':' . $f->getLine());
            $antwort = Antwort::fehler(new HttpFehler(500, 'serverfehler', 'Da ist etwas schiefgegangen. Bitte versuchen Sie es später noch einmal.'));
        }
        $this->sicherheitskopf($antwort);
        return $antwort;
    }

    /**
     * Schreibende Anfragen nur von der eigenen Seite. Browser schicken bei fetch() immer
     * Origin mit; fehlt er, kommt die Anfrage nicht aus einem Browser und kann kein
     * fremdes Cookie mitbringen.
     */
    private function herkunftPruefen(Anfrage $a): void
    {
        if ($a->methode === 'GET' || $a->methode === 'HEAD') {
            return;
        }
        if ($a->methode !== 'POST') {
            throw new HttpFehler(405, 'methode', 'Diese Methode ist hier nicht erlaubt.');
        }
        $herkunft = $a->kopf('origin');
        $seite = $a->kopf('sec-fetch-site');
        if ($seite !== '' && !in_array($seite, ['same-origin', 'none'], true)) {
            throw new HttpFehler(403, 'fremde_herkunft', 'Anfrage von einer fremden Seite abgelehnt.');
        }
        if ($herkunft !== '' && $herkunft !== $this->konfig->herkunft() && !$this->lokaleEntwicklung($herkunft)) {
            throw new HttpFehler(403, 'fremde_herkunft', 'Anfrage von einer fremden Seite abgelehnt.');
        }
    }

    private function lokaleEntwicklung(string $herkunft): bool
    {
        return $this->konfig->entwicklung() && preg_match('#^http://(127\.0\.0\.1|localhost)(:\d+)?$#', $herkunft) === 1;
    }

    private function sicherheitskopf(Antwort $a): void
    {
        $a->kopf += [
            'Cache-Control' => 'no-store',
            'X-Content-Type-Options' => 'nosniff',
            'Content-Security-Policy' => "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            'Referrer-Policy' => 'no-referrer',
            'Cross-Origin-Resource-Policy' => 'same-origin',
            'Cross-Origin-Opener-Policy' => 'same-origin',
            'X-Frame-Options' => 'DENY',
            'Permissions-Policy' => 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
        ];
        if (!$this->konfig->entwicklung()) {
            $a->kopf['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains';
        }
    }

    public function sicheresKeks(): bool
    {
        return str_starts_with($this->konfig->url(), 'https://');
    }

    public function keksName(): string
    {
        return $this->sicheresKeks() ? '__Host-rh_sitzung' : 'rh_sitzung';
    }
}
