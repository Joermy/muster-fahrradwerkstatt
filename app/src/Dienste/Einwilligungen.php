<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Datenbank;
use Radhaus\Uhr;

/**
 * Nachweis der Einwilligungen (Art. 7 Abs. 1 DSGVO). Gespeichert werden eine zufällige
 * Kennung aus dem Browser, die Fassung des Banners, die Auswahl und die Zeit – keine
 * IP-Adresse, kein Browserkennzeichen.
 */
final class Einwilligungen
{
    public const FASSUNG = '2026-10';

    public function __construct(private Datenbank $db, private Uhr $uhr)
    {
    }

    public function speichern(string $id, string $fassung, bool $medien): void
    {
        $jetzt = $this->uhr->iso();
        $this->db->ausfuehren(
            'INSERT INTO einwilligungen (id, fassung, medien, erstellt, geaendert) VALUES (?, ?, ?, ?, ?)
             ON CONFLICT (id) DO UPDATE SET fassung = excluded.fassung, medien = excluded.medien, geaendert = excluded.geaendert',
            [$id, $fassung, $medien, $jetzt, $jetzt],
        );
    }

    public static function gueltigeId(mixed $id): bool
    {
        return is_string($id) && preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/', $id) === 1;
    }
}
