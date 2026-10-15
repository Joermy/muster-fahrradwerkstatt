<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Dienste\Kalender;
use Radhaus\Tests\Fall;

final class KalenderTest extends Fall
{
    public function testOstern(): void
    {
        foreach ([2024 => '2024-03-31', 2025 => '2025-04-20', 2026 => '2026-04-05', 2027 => '2027-03-28', 2038 => '2038-04-25'] as $jahr => $datum) {
            $this->gleich($datum, Kalender::ostersonntag($jahr)->format('Y-m-d'), (string) $jahr);
        }
    }

    public function testFeiertageNiedersachsen(): void
    {
        $this->gleich('Karfreitag', Kalender::feiertag('2026-04-03'));
        $this->gleich('Ostermontag', Kalender::feiertag('2026-04-06'));
        $this->gleich('Christi Himmelfahrt', Kalender::feiertag('2026-05-14'));
        $this->gleich('Pfingstmontag', Kalender::feiertag('2026-05-25'));
        $this->gleich('Reformationstag', Kalender::feiertag('2026-10-31'));
        $this->gleich(null, Kalender::feiertag('2026-06-04'), 'Fronleichnam gilt in Niedersachsen nicht');
        $this->gleich(null, Kalender::feiertag('2026-10-14'));
    }

    public function testZeitraumUndSonntag(): void
    {
        $tage = $this->app()->kalender->tage();
        $this->gleich('2026-10-14', $tage[0]['datum'], 'frühestens morgen');
        $this->gleich('2026-11-10', end($tage)['datum'], 'höchstens 28 Tage');
        foreach ($tage as $t) {
            if ($t['wochentag'] === 7) {
                $this->gleich([], $t['zeiten'], 'Sonntag geschlossen');
            }
            if ($t['datum'] === '2026-10-31') {
                $this->gleich('Reformationstag', $t['grund']);
                $this->gleich([], $t['zeiten']);
            }
        }
    }

    public function testPlatzFrei(): void
    {
        $k = $this->app()->kalender;
        $this->wahr($k->platzFrei('2026-10-14', '08:30'));
        $this->wahr(!$k->platzFrei('2026-10-13', '17:00'), 'heute nicht');
        $this->wahr(!$k->platzFrei('2026-10-14', '08:31'), 'keine Annahmezeit');
        $this->wahr(!$k->platzFrei('2026-10-18', '10:00'), 'Sonntag');
        $this->wahr(!$k->platzFrei('2026-11-11', '10:00'), 'zu weit');
        $this->wahr(!$k->platzFrei('2026-10-31', '09:00'), 'Feiertag');
    }
}
