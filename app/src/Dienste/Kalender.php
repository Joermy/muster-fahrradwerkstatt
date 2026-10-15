<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use DateTimeImmutable;
use Radhaus\Daten\Datenbank;
use Radhaus\Uhr;

/**
 * Freie Annahmezeiten. Ein Zeitfenster hat so viele Plätze, wie für den Wochentag
 * eingestellt sind; Feiertage in Niedersachsen und Sperrtage fallen aus.
 */
final class Kalender
{
    public const VORLAUF_TAGE = 1;
    public const HORIZONT_TAGE = 28;

    /** Status, die einen Platz belegen. */
    public const BELEGEND = ['angefragt', 'bestaetigt', 'angenommen', 'in_arbeit', 'wartet_auf_freigabe', 'abholbereit'];

    public function __construct(private Datenbank $db, private Uhr $uhr)
    {
    }

    /** @return list<array{datum: string, wochentag: int, zeiten: list<array{zeit: string, frei: int}>, grund: ?string}> */
    public function tage(?string $von = null, int $anzahl = self::HORIZONT_TAGE): array
    {
        $start = $von !== null
            ? new DateTimeImmutable($von, Uhr::zone())
            : $this->uhr->jetzt()->setTime(0, 0)->modify('+' . self::VORLAUF_TAGE . ' day');
        $erster = $this->uhr->jetzt()->setTime(0, 0)->modify('+' . self::VORLAUF_TAGE . ' day');
        $letzter = $this->uhr->jetzt()->setTime(0, 0)->modify('+' . self::HORIZONT_TAGE . ' day');
        if ($start < $erster) {
            $start = $erster;
        }

        $kapazitaet = $this->kapazitaet();
        $sperren = [];
        foreach ($this->db->zeilen('SELECT datum, grund FROM sperrtage WHERE datum >= ?', [$start->format('Y-m-d')]) as $z) {
            $sperren[(string) $z['datum']] = (string) $z['grund'];
        }
        $belegt = [];
        $platzhalter = implode(',', array_fill(0, count(self::BELEGEND), '?'));
        foreach ($this->db->zeilen(
            "SELECT termin_datum, termin_zeit, COUNT(*) AS n FROM auftraege WHERE termin_datum BETWEEN ? AND ? AND status IN ($platzhalter) GROUP BY termin_datum, termin_zeit",
            [$start->format('Y-m-d'), $letzter->format('Y-m-d'), ...self::BELEGEND],
        ) as $z) {
            $belegt[$z['termin_datum'] . ' ' . $z['termin_zeit']] = (int) $z['n'];
        }

        $tage = [];
        for ($i = 0; $i < $anzahl; $i++) {
            $tag = $start->modify("+{$i} day");
            if ($tag > $letzter) {
                break;
            }
            $datum = $tag->format('Y-m-d');
            $wochentag = (int) $tag->format('N');
            $grund = self::feiertag($datum) ?? ($sperren[$datum] ?? null);
            $zeiten = [];
            $k = $kapazitaet[$wochentag] ?? ['zeiten' => [], 'plaetze' => 0];
            if ($grund === null) {
                foreach ($k['zeiten'] as $zeit) {
                    $zeiten[] = ['zeit' => $zeit, 'frei' => max(0, $k['plaetze'] - ($belegt[$datum . ' ' . $zeit] ?? 0))];
                }
            }
            $tage[] = ['datum' => $datum, 'wochentag' => $wochentag, 'zeiten' => $zeiten, 'grund' => $grund];
        }
        return $tage;
    }

    /** Muss innerhalb einer Schreib-Transaktion aufgerufen werden. */
    public function platzFrei(string $datum, string $zeit): bool
    {
        $erster = $this->uhr->jetzt()->setTime(0, 0)->modify('+' . self::VORLAUF_TAGE . ' day')->format('Y-m-d');
        $letzter = $this->uhr->jetzt()->setTime(0, 0)->modify('+' . self::HORIZONT_TAGE . ' day')->format('Y-m-d');
        if ($datum < $erster || $datum > $letzter || self::feiertag($datum) !== null) {
            return false;
        }
        if ($this->db->wert('SELECT 1 FROM sperrtage WHERE datum = ?', [$datum]) !== null) {
            return false;
        }
        $wochentag = (int) (new DateTimeImmutable($datum, Uhr::zone()))->format('N');
        $k = $this->kapazitaet()[$wochentag] ?? null;
        if ($k === null || !in_array($zeit, $k['zeiten'], true)) {
            return false;
        }
        $platzhalter = implode(',', array_fill(0, count(self::BELEGEND), '?'));
        $n = (int) $this->db->wert(
            "SELECT COUNT(*) FROM auftraege WHERE termin_datum = ? AND termin_zeit = ? AND status IN ($platzhalter)",
            [$datum, $zeit, ...self::BELEGEND],
        );
        return $n < $k['plaetze'];
    }

    /** @return array<int, array{zeiten: list<string>, plaetze: int}> */
    public function kapazitaet(): array
    {
        $aus = [];
        foreach ($this->db->zeilen('SELECT wochentag, zeiten, plaetze FROM kapazitaet') as $z) {
            $zeiten = json_decode((string) $z['zeiten'], true);
            $aus[(int) $z['wochentag']] = [
                'zeiten' => is_array($zeiten) ? array_values(array_filter($zeiten, 'is_string')) : [],
                'plaetze' => (int) $z['plaetze'],
            ];
        }
        return $aus;
    }

    /** @param array<int, array{zeiten: list<string>, plaetze: int}> $plan */
    public function kapazitaetSetzen(array $plan): void
    {
        $this->db->transaktion(function () use ($plan): void {
            foreach ($plan as $wochentag => $k) {
                $this->db->ausfuehren(
                    'INSERT INTO kapazitaet (wochentag, zeiten, plaetze) VALUES (?, ?, ?) ON CONFLICT (wochentag) DO UPDATE SET zeiten = excluded.zeiten, plaetze = excluded.plaetze',
                    [$wochentag, json_encode(array_values($k['zeiten'])), $k['plaetze']],
                );
            }
        });
    }

    /** @return array<int, array{zeiten: list<string>, plaetze: int}> */
    public static function standardKapazitaet(): array
    {
        $werktag = ['zeiten' => ['08:30', '10:00', '11:30', '14:00', '15:30', '17:00'], 'plaetze' => 2];
        return [
            1 => $werktag, 2 => $werktag, 3 => $werktag, 4 => $werktag, 5 => $werktag,
            6 => ['zeiten' => ['09:00', '10:30', '12:00'], 'plaetze' => 2],
            7 => ['zeiten' => [], 'plaetze' => 0],
        ];
    }

    /** Gesetzliche Feiertage in Niedersachsen. */
    public static function feiertag(string $datum): ?string
    {
        $jahr = (int) substr($datum, 0, 4);
        $md = substr($datum, 5);
        $fest = [
            '01-01' => 'Neujahr',
            '05-01' => 'Tag der Arbeit',
            '10-03' => 'Tag der Deutschen Einheit',
            '10-31' => 'Reformationstag',
            '12-25' => '1. Weihnachtstag',
            '12-26' => '2. Weihnachtstag',
        ];
        if (isset($fest[$md])) {
            return $fest[$md];
        }
        $ostern = self::ostersonntag($jahr);
        $beweglich = [
            '-2' => 'Karfreitag',
            '1' => 'Ostermontag',
            '39' => 'Christi Himmelfahrt',
            '50' => 'Pfingstmontag',
        ];
        foreach ($beweglich as $abstand => $name) {
            if ($ostern->modify("{$abstand} day")->format('Y-m-d') === $datum) {
                return $name;
            }
        }
        return null;
    }

    /** Gaußsche Osterformel in der Form von Lichtenberg. */
    public static function ostersonntag(int $jahr): DateTimeImmutable
    {
        $k = intdiv($jahr, 100);
        $m = 15 + intdiv(3 * $k + 3, 4) - intdiv(8 * $k + 13, 25);
        $s = 2 - intdiv(3 * $k + 3, 4);
        $a = $jahr % 19;
        $d = (19 * $a + $m) % 30;
        $r = intdiv($d + intdiv($a, 11), 29);
        $og = 21 + $d - $r;
        $sz = 7 - ($jahr + intdiv($jahr, 4) + $s) % 7;
        $oe = 7 - ($og - $sz) % 7;
        $os = $og + $oe;
        return (new DateTimeImmutable("{$jahr}-03-01", Uhr::zone()))->modify('+' . ($os - 1) . ' day');
    }
}
