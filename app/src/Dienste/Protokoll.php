<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Datenbank;
use Radhaus\Uhr;

/**
 * Wer hat wann was getan. Enthält Kennungen (Auftragsnummer, Benutzer-ID), aber keine
 * Namen, Adressen oder Inhalte. Die Anwendung kann Einträge nur anlegen, nicht ändern.
 */
final class Protokoll
{
    public function __construct(private Datenbank $db, private Uhr $uhr)
    {
    }

    public function eintragen(?int $benutzerId, string $aktion, string $objekt = '', string $details = ''): void
    {
        $this->db->ausfuehren(
            'INSERT INTO protokoll (zeit, benutzer_id, aktion, objekt, details) VALUES (?, ?, ?, ?, ?)',
            [$this->uhr->iso(), $benutzerId, $aktion, mb_substr($objekt, 0, 80), mb_substr($details, 0, 200)],
        );
    }

    /** @return list<array<string, mixed>> */
    public function letzte(int $anzahl = 200, ?string $aktion = null): array
    {
        if ($aktion !== null) {
            return $this->db->zeilen(
                'SELECT p.id, p.zeit, p.aktion, p.objekt, p.details, b.anzeigename AS benutzer FROM protokoll p LEFT JOIN benutzer b ON b.id = p.benutzer_id WHERE p.aktion = ? ORDER BY p.id DESC LIMIT ?',
                [$aktion, $anzahl],
            );
        }
        return $this->db->zeilen(
            'SELECT p.id, p.zeit, p.aktion, p.objekt, p.details, b.anzeigename AS benutzer FROM protokoll p LEFT JOIN benutzer b ON b.id = p.benutzer_id ORDER BY p.id DESC LIMIT ?',
            [$anzahl],
        );
    }
}
