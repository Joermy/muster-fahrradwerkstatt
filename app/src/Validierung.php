<?php

declare(strict_types=1);

namespace Radhaus;

use Radhaus\Http\HttpFehler;

/**
 * Prüft Eingaben feldweise. Unbekannte Felder werden abgelehnt, damit niemand
 * zusätzliche Spalten mitschicken kann.
 */
final class Validierung
{
    /** @var array<string, string> */
    private array $fehler = [];

    /** @param array<string, mixed> $daten */
    public function __construct(private array $daten)
    {
    }

    /**
     * @param array<string, mixed> $daten
     * @param list<string> $erlaubt
     */
    public static function nur(array $daten, array $erlaubt): self
    {
        $fremd = array_diff(array_keys($daten), $erlaubt);
        if ($fremd !== []) {
            throw new HttpFehler(400, 'unbekannte_felder', 'Die Anfrage enthält unbekannte Felder.');
        }
        return new self($daten);
    }

    public function text(string $feld, int $min, int $max, bool $pflicht = true, bool $mehrzeilig = false): ?string
    {
        $wert = $this->daten[$feld] ?? null;
        if ($wert === null || $wert === '') {
            if ($pflicht) {
                $this->fehler[$feld] = 'Bitte ausfüllen.';
            }
            return null;
        }
        if (!is_string($wert) || !mb_check_encoding($wert, 'UTF-8')) {
            $this->fehler[$feld] = 'Ungültige Eingabe.';
            return null;
        }
        $wert = self::saeubern($wert, $mehrzeilig);
        $laenge = mb_strlen($wert);
        if ($laenge < $min) {
            $this->fehler[$feld] = $pflicht || $laenge > 0 ? "Mindestens {$min} Zeichen." : 'Bitte ausfüllen.';
            return null;
        }
        if ($laenge > $max) {
            $this->fehler[$feld] = "Höchstens {$max} Zeichen.";
            return null;
        }
        return $wert;
    }

    public function name(string $feld): ?string
    {
        $wert = $this->text($feld, 2, 80);
        if ($wert !== null && preg_match("/^[\\p{L}][\\p{L}\\p{M} .'\\-]*$/u", $wert) !== 1) {
            $this->fehler[$feld] = 'Bitte nur Buchstaben, Leerzeichen, Punkt, Bindestrich oder Apostroph.';
            return null;
        }
        return $wert;
    }

    public function email(string $feld): ?string
    {
        $wert = $this->text($feld, 6, 254);
        if ($wert === null) {
            return null;
        }
        $wert = mb_strtolower($wert);
        if (filter_var($wert, FILTER_VALIDATE_EMAIL) === false || preg_match('/[\r\n,;<>"]/', $wert) === 1) {
            $this->fehler[$feld] = 'Bitte eine gültige E-Mail-Adresse angeben.';
            return null;
        }
        return $wert;
    }

    public function telefon(string $feld): ?string
    {
        $wert = $this->text($feld, 6, 25, false);
        if ($wert !== null && preg_match('#^\+?[0-9][0-9 ()/\-]{4,23}$#', $wert) !== 1) {
            $this->fehler[$feld] = 'Bitte nur Ziffern, Leerzeichen, +, -, / und Klammern.';
            return null;
        }
        return $wert;
    }

    /** @param list<string> $werte */
    public function auswahl(string $feld, array $werte, bool $pflicht = true): ?string
    {
        $wert = $this->daten[$feld] ?? null;
        if ($wert === null || $wert === '') {
            if ($pflicht) {
                $this->fehler[$feld] = 'Bitte auswählen.';
            }
            return null;
        }
        if (!is_string($wert) || !in_array($wert, $werte, true)) {
            $this->fehler[$feld] = 'Ungültige Auswahl.';
            return null;
        }
        return $wert;
    }

    public function datum(string $feld): ?string
    {
        $wert = $this->daten[$feld] ?? null;
        if (!is_string($wert) || preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $wert, $t) !== 1 || !checkdate((int) $t[2], (int) $t[3], (int) $t[1])) {
            $this->fehler[$feld] = 'Bitte ein gültiges Datum wählen.';
            return null;
        }
        return $wert;
    }

    public function uhrzeit(string $feld): ?string
    {
        $wert = $this->daten[$feld] ?? null;
        if (!is_string($wert) || preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', $wert) !== 1) {
            $this->fehler[$feld] = 'Bitte eine gültige Uhrzeit wählen.';
            return null;
        }
        return $wert;
    }

    public function wahrheit(string $feld): bool
    {
        $wert = $this->daten[$feld] ?? false;
        if (!is_bool($wert)) {
            $this->fehler[$feld] = 'Ungültige Eingabe.';
            return false;
        }
        return $wert;
    }

    public function ganzzahl(string $feld, int $min, int $max): ?int
    {
        $wert = $this->daten[$feld] ?? null;
        if (!is_int($wert) || $wert < $min || $wert > $max) {
            $this->fehler[$feld] = "Bitte eine Zahl von {$min} bis {$max}.";
            return null;
        }
        return $wert;
    }

    public function roh(string $feld): mixed
    {
        return $this->daten[$feld] ?? null;
    }

    public function fehlerMelden(string $feld, string $meldung): void
    {
        $this->fehler[$feld] = $meldung;
    }

    public function pruefen(): void
    {
        if ($this->fehler !== []) {
            throw HttpFehler::ungueltig($this->fehler);
        }
    }

    /** Entfernt Steuerzeichen, unsichtbare Richtungswechsel und doppelte Leerzeichen. */
    public static function saeubern(string $wert, bool $mehrzeilig = false): string
    {
        $wert = str_replace(["\r\n", "\r"], "\n", $wert);
        $wert = preg_replace('/[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2066}-\x{2069}\x{FEFF}]/u', '', $wert) ?? '';
        $wert = $mehrzeilig
            ? preg_replace('/[^\P{C}\n]/u', '', $wert) ?? ''
            : preg_replace('/\p{C}/u', '', $wert) ?? '';
        if ($mehrzeilig) {
            $wert = preg_replace("/\n{3,}/", "\n\n", $wert) ?? '';
            $zeilen = array_map(static fn (string $z): string => trim(preg_replace('/[ \t]+/', ' ', $z) ?? ''), explode("\n", $wert));
            return trim(implode("\n", $zeilen));
        }
        return trim(preg_replace('/\s+/u', ' ', $wert) ?? '');
    }
}
