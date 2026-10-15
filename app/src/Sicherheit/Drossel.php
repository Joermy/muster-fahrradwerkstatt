<?php

declare(strict_types=1);

namespace Radhaus\Sicherheit;

use Radhaus\Daten\Binaer;
use Radhaus\Daten\Datenbank;
use Radhaus\Http\HttpFehler;
use Radhaus\Uhr;

/**
 * Begrenzt Anfragen je Absender. Gespeichert wird nur ein täglich wechselnder HMAC der
 * IP-Adresse, nie die Adresse selbst. Einträge verschwinden nach einem Tag.
 */
final class Drossel
{
    /** Eimer => [Anzahl, Fenster in Sekunden] */
    public const GRENZEN = [
        'anfrage' => [5, 3600],
        'status' => [30, 600],
        'link' => [3, 3600],
        'widerruf' => [10, 3600],
        'einwilligung' => [30, 3600],
        'anmeldung' => [20, 900],
        'termine' => [120, 600],
    ];

    public function __construct(private Datenbank $db, private Tresor $tresor, private Uhr $uhr)
    {
    }

    public function zaehlen(string $eimer, string $ip): void
    {
        [$grenze, $fenster] = self::GRENZEN[$eimer];
        $jetzt = $this->uhr->zeitstempel();
        $start = $jetzt - $jetzt % $fenster;
        $schluessel = new Binaer($this->tresor->drosselSchluessel($ip, $this->uhr->heute()));
        $this->db->ausfuehren(
            'INSERT INTO drossel (schluessel, eimer, fenster, anzahl) VALUES (?, ?, ?, 1) ON CONFLICT (schluessel, eimer, fenster) DO UPDATE SET anzahl = anzahl + 1',
            [$schluessel, $eimer, $start],
        );
        $anzahl = (int) $this->db->wert('SELECT anzahl FROM drossel WHERE schluessel = ? AND eimer = ? AND fenster = ?', [$schluessel, $eimer, $start]);
        if ($anzahl > $grenze) {
            throw new HttpFehler(429, 'zu_viele', 'Zu viele Anfragen. Bitte versuchen Sie es später noch einmal.', [], $start + $fenster - $jetzt);
        }
    }

    public function aufraeumen(): void
    {
        $this->db->ausfuehren('DELETE FROM drossel WHERE fenster < ?', [$this->uhr->zeitstempel() - 86400]);
    }
}
