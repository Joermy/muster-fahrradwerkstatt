<?php

declare(strict_types=1);

namespace Radhaus\Sicherheit;

/**
 * Passwörter mit Argon2id. Die Kosten entsprechen den PHP-Vorgaben (64 MiB, 4 Durchläufe)
 * und liegen damit über der OWASP-Mindestempfehlung.
 */
final class Passwort
{
    private const OPTIONEN = ['memory_cost' => 65536, 'time_cost' => 4, 'threads' => 1];

    /** Für Anmeldungen mit unbekanntem Namen, damit die Antwortzeit nichts verrät. */
    private static ?string $attrappe = null;

    public static function hashen(string $klartext): string
    {
        return password_hash($klartext, PASSWORD_ARGON2ID, self::OPTIONEN);
    }

    public static function pruefen(string $klartext, ?string $hash): bool
    {
        if ($hash === null) {
            self::$attrappe ??= self::hashen(random_bytes(16));
            password_verify($klartext, self::$attrappe);
            return false;
        }
        return password_verify($klartext, $hash);
    }

    public static function neuHashenNoetig(string $hash): bool
    {
        return password_needs_rehash($hash, PASSWORD_ARGON2ID, self::OPTIONEN);
    }

    /** Liefert eine Meldung, wenn das Passwort nicht taugt, sonst null. */
    public static function schwaeche(string $passwort, string $benutzername): ?string
    {
        $laenge = mb_strlen($passwort);
        if ($laenge < 12) {
            return 'Mindestens 12 Zeichen.';
        }
        if ($laenge > 128) {
            return 'Höchstens 128 Zeichen.';
        }
        $klein = mb_strtolower($passwort);
        if ($benutzername !== '' && str_contains($klein, mb_strtolower($benutzername))) {
            return 'Das Passwort darf den Benutzernamen nicht enthalten.';
        }
        $ohneZiffern = rtrim($klein, '0123456789!.?');
        foreach (self::HAEUFIG as $wort) {
            if ($klein === $wort || $ohneZiffern === $wort) {
                return 'Dieses Passwort steht auf Listen häufiger Passwörter.';
            }
        }
        if (count(array_unique(mb_str_split($klein))) < 5) {
            return 'Zu wenige verschiedene Zeichen.';
        }
        return null;
    }

    private const HAEUFIG = [
        '123456789012', 'passwort', 'password', 'passwort123', 'password123', 'qwertzuiop', 'qwertyuiop',
        'hallo', 'hallohallo', 'sommer', 'winter', 'fruehling', 'herbst', 'fussball', 'schalke', 'dortmund',
        'bayern', 'werder', 'eintracht', 'hannover', 'braunschweig', 'peine', 'deutschland', 'berlin',
        'iloveyou', 'ichliebedich', 'schatz', 'schatzi', 'admin', 'administrator', 'werkstatt', 'fahrrad',
        'fahrradwerkstatt', 'radhaus', 'radhausfuhse', 'willkommen', 'welcome', 'geheim', 'geheimnis',
        'letmein', 'monkey', 'dragon', 'master', 'superman', 'batman', 'starwars', 'pokemon', 'sunshine',
        'princess', 'football', 'baseball', 'trustno1', 'abcdefghijkl', 'abc123abc123', 'asdfghjkl',
        'yxcvbnm', 'mausi', 'hase', 'blume', 'sonne', 'mond', 'sterne', 'computer', 'internet', 'telekom',
        'changeme', 'changeme123', 'default', 'zugang', 'anmelden', 'login', 'kennwort', 'benutzer',
        'inhaber', 'inhaberin', 'mitarbeiter', 'verwaltung', 'januar', 'februar', 'dezember', 'weihnachten',
    ];
}
