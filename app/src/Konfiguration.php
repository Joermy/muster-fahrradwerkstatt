<?php

declare(strict_types=1);

namespace Radhaus;

use RuntimeException;

/**
 * Liest die .env im Projektordner. Umgebungsvariablen des Servers gehen vor.
 * Es wird nichts ausgewertet, nur KEY=WERT-Zeilen gelesen.
 */
final class Konfiguration
{
    /** @param array<string, string> $werte */
    private function __construct(private array $werte)
    {
    }

    public static function laden(string $wurzel): self
    {
        $werte = [];
        $datei = $wurzel . '/.env';
        if (is_file($datei)) {
            foreach (file($datei, FILE_IGNORE_NEW_LINES) ?: [] as $zeile) {
                $zeile = trim($zeile);
                if ($zeile === '' || $zeile[0] === '#' || !str_contains($zeile, '=')) {
                    continue;
                }
                [$name, $wert] = explode('=', $zeile, 2);
                $name = trim($name);
                $wert = trim($wert);
                if (strlen($wert) >= 2 && ($wert[0] === '"' || $wert[0] === "'") && $wert[-1] === $wert[0]) {
                    $wert = substr($wert, 1, -1);
                }
                if (preg_match('/^[A-Z][A-Z0-9_]*$/', $name)) {
                    $werte[$name] = $wert;
                }
            }
        }
        foreach (array_keys($werte + self::STANDARD) as $name) {
            $env = getenv($name);
            if ($env !== false) {
                $werte[$name] = $env;
            }
        }
        $werte['WURZEL'] = $wurzel;
        return new self($werte + self::STANDARD);
    }

    /** @param array<string, string> $werte */
    public static function aus(array $werte): self
    {
        return new self($werte + self::STANDARD);
    }

    private const STANDARD = [
        'APP_UMGEBUNG' => 'produktion',
        'APP_URL' => 'https://radhaus-fuhse.example',
        'APP_SCHLUESSEL' => '',
        'DATENBANK' => 'var/radhaus.sqlite',
        'POST_MODUS' => 'mail',
        'POST_ABSENDER' => 'werkstatt@radhaus-fuhse.example',
        'VERTRAUTE_PROXYS' => '',
        'WURZEL' => '.',
    ];

    public function text(string $name): string
    {
        return $this->werte[$name] ?? '';
    }

    public function entwicklung(): bool
    {
        return $this->text('APP_UMGEBUNG') === 'entwicklung';
    }

    public function url(): string
    {
        return rtrim($this->text('APP_URL'), '/');
    }

    public function herkunft(): string
    {
        $teile = parse_url($this->url());
        if (!is_array($teile) || !isset($teile['scheme'], $teile['host'])) {
            throw new RuntimeException('APP_URL ist ungültig.');
        }
        return $teile['scheme'] . '://' . $teile['host'] . (isset($teile['port']) ? ':' . $teile['port'] : '');
    }

    public function datenbankPfad(): string
    {
        $pfad = $this->text('DATENBANK');
        if ($pfad === ':memory:' || str_starts_with($pfad, '/')) {
            return $pfad;
        }
        return $this->text('WURZEL') . '/' . $pfad;
    }

    public function hauptschluessel(): string
    {
        $wert = $this->text('APP_SCHLUESSEL');
        if (str_starts_with($wert, 'base64:')) {
            $wert = substr($wert, 7);
        }
        $roh = base64_decode($wert, true);
        if ($roh === false || strlen($roh) !== SODIUM_CRYPTO_KDF_KEYBYTES) {
            throw new RuntimeException('APP_SCHLUESSEL fehlt oder hat nicht 32 Byte. Erzeugen mit: php bin/schluessel.php');
        }
        return $roh;
    }

    /** @return list<string> */
    public function vertrauteProxys(): array
    {
        return array_values(array_filter(array_map('trim', explode(',', $this->text('VERTRAUTE_PROXYS')))));
    }
}
