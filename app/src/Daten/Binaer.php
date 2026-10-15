<?php

declare(strict_types=1);

namespace Radhaus\Daten;

/** Kennzeichnet einen Wert als Binärdaten (BLOB) für Datenbank-Parameter. */
final class Binaer
{
    public function __construct(public readonly string $roh)
    {
    }

    public static function oder(?string $roh): ?self
    {
        return $roh === null ? null : new self($roh);
    }
}
