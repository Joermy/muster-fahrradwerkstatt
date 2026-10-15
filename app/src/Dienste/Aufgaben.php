<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Datenbank;
use Radhaus\Sicherheit\Drossel;
use Radhaus\Uhr;

/**
 * Wiederkehrende Arbeiten: Löschfristen und Aufräumen.
 * Läuft per Cronjob (bin/aufgaben.php) und ersatzweise einmal täglich beim ersten Aufruf
 * der Verwaltung, falls auf dem Server kein Cronjob eingerichtet werden kann.
 */
final class Aufgaben
{
    public function __construct(
        private Datenbank $db,
        private Uhr $uhr,
        private Auftraege $auftraege,
        private Widerrufe $widerrufe,
        private Drossel $drossel,
        private Zugang $zugang,
        private Protokoll $protokoll,
    ) {
    }

    public function faellig(): bool
    {
        $zuletzt = $this->db->wert("SELECT zuletzt FROM aufgaben WHERE name = 'taeglich'");
        return !is_string($zuletzt) || substr($zuletzt, 0, 10) < $this->uhr->heute();
    }

    /** @return array<string, int|string|null> */
    public function ausfuehren(bool $erzwingen = false): array
    {
        if (!$erzwingen && !$this->faellig()) {
            return [];
        }
        $this->db->ausfuehren(
            "INSERT INTO aufgaben (name, zuletzt) VALUES ('taeglich', ?) ON CONFLICT (name) DO UPDATE SET zuletzt = excluded.zuletzt",
            [$this->uhr->iso()],
        );
        $jetzt = $this->uhr->jetzt();
        $ergebnis = [
            'auftraege_anonymisiert' => $this->auftraege->fristenAnwenden(),
            'widerrufe_geloescht' => $this->widerrufe->fristenAnwenden(),
            'einwilligungen_geloescht' => $this->db->ausfuehren('DELETE FROM einwilligungen WHERE geaendert < ?', [$jetzt->modify('-36 month')->format('c')])->rowCount(),
            'protokoll_geloescht' => $this->db->ausfuehren('DELETE FROM protokoll WHERE zeit < ?', [$jetzt->modify('-12 month')->format('c')])->rowCount(),
            'post_geloescht' => $this->db->ausfuehren('DELETE FROM post WHERE erstellt < ?', [$jetzt->modify('-30 day')->format('c')])->rowCount(),
        ];
        $this->drossel->aufraeumen();
        $this->zugang->aufraeumen();
        $this->db->aufraeumen();
        $this->protokoll->eintragen(null, 'aufgaben', '', (string) json_encode($ergebnis));
        return $ergebnis;
    }
}
