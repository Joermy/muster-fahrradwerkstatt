<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use RuntimeException;

/** Leistungen, Preise und Radtypen aus app/daten/leistungen.json. */
final class Katalog
{
    /** @var array<string, mixed> */
    private array $daten;

    public function __construct(string $datei)
    {
        $daten = json_decode((string) file_get_contents($datei), true);
        if (!is_array($daten)) {
            throw new RuntimeException('Leistungskatalog fehlt.');
        }
        $this->daten = $daten;
    }

    /** @return list<string> */
    public function leistungen(): array
    {
        return array_map(static fn (array $l): string => (string) $l['kennung'], $this->roh('leistungen'));
    }

    /** @return list<string> */
    public function raeder(): array
    {
        return array_map(static fn (array $r): string => (string) $r['kennung'], $this->roh('raeder'));
    }

    public function titel(string $art, string $kennung): string
    {
        foreach ($this->roh($art === 'rad' ? 'raeder' : 'leistungen') as $e) {
            if ($e['kennung'] === $kennung) {
                return (string) $e['titel'];
            }
        }
        return $kennung;
    }

    /** @return list<array<string, mixed>> */
    private function roh(string $schluessel): array
    {
        $liste = $this->daten[$schluessel] ?? [];
        return is_array($liste) ? array_values(array_filter($liste, 'is_array')) : [];
    }

    /** @return array<string, mixed> */
    public function alles(): array
    {
        return $this->daten;
    }
}
