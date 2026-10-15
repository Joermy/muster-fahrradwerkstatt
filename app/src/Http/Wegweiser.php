<?php

declare(strict_types=1);

namespace Radhaus\Http;

/**
 * Ordnet Methode und Pfad einer Funktion zu. Platzhalter {id} passt nur auf Ziffern,
 * {nr} nur auf Auftragsnummern.
 */
final class Wegweiser
{
    /** @var list<array{string, string, callable}> */
    private array $wege = [];

    private const MUSTER = [
        '{id}' => '([1-9][0-9]{0,9})',
        '{nr}' => '(RF-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4})',
        '{monat}' => '(20[0-9]{2}-(?:0[1-9]|1[0-2]))',
    ];

    public function weg(string $methode, string $muster, callable $ziel): void
    {
        $regex = '#^' . strtr(preg_quote($muster, '#'), array_combine(
            array_map(static fn (string $k): string => preg_quote($k, '#'), array_keys(self::MUSTER)),
            array_values(self::MUSTER),
        )) . '$#D';
        $this->wege[] = [$methode, $regex, $ziel];
    }

    public function leiten(Anfrage $a): Antwort
    {
        $pfadGefunden = false;
        foreach ($this->wege as [$methode, $regex, $ziel]) {
            if (preg_match($regex, $a->pfad, $treffer) !== 1) {
                continue;
            }
            $pfadGefunden = true;
            if ($methode !== $a->methode) {
                continue;
            }
            array_shift($treffer);
            /** @var Antwort */
            return $ziel($a, ...$treffer);
        }
        if ($pfadGefunden) {
            throw new HttpFehler(405, 'methode', 'Diese Methode ist hier nicht erlaubt.');
        }
        throw new HttpFehler(404, 'nicht_gefunden', 'Diese Adresse gibt es nicht.');
    }
}
