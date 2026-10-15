<?php

declare(strict_types=1);

namespace Radhaus\Http;

use RuntimeException;

/**
 * Fehler, der so an den Aufrufer gehen darf. Die Meldung ist für Menschen gedacht
 * und enthält nie interne Einzelheiten.
 */
final class HttpFehler extends RuntimeException
{
    /** @param array<string, mixed> $zusatz */
    public function __construct(
        public readonly int $status,
        public readonly string $kennung,
        string $meldung,
        public readonly array $zusatz = [],
        public readonly ?int $wartenSek = null,
    ) {
        parent::__construct($meldung);
    }

    /** @param array<string, string> $felder Feldname => Meldung */
    public static function ungueltig(array $felder): self
    {
        return new self(422, 'ungueltig', 'Bitte prüfen Sie die markierten Angaben.', ['felder' => $felder]);
    }
}
