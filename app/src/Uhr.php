<?php

declare(strict_types=1);

namespace Radhaus;

use DateTimeImmutable;
use DateTimeZone;

/** Zeitquelle. In Tests lässt sie sich festhalten und vorstellen. */
final class Uhr
{
    private ?DateTimeImmutable $fest = null;

    public static function zone(): DateTimeZone
    {
        return new DateTimeZone('Europe/Berlin');
    }

    public function jetzt(): DateTimeImmutable
    {
        return $this->fest ?? new DateTimeImmutable('now', self::zone());
    }

    public function festhalten(string $zeit): void
    {
        $this->fest = new DateTimeImmutable($zeit, self::zone());
    }

    public function vorstellen(string $abstand): void
    {
        $this->fest = $this->jetzt()->modify($abstand);
    }

    public function zeitstempel(): int
    {
        return $this->jetzt()->getTimestamp();
    }

    public function iso(): string
    {
        return $this->jetzt()->format('Y-m-d\TH:i:sP');
    }

    public function heute(): string
    {
        return $this->jetzt()->format('Y-m-d');
    }
}
