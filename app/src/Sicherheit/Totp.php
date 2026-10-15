<?php

declare(strict_types=1);

namespace Radhaus\Sicherheit;

/**
 * Einmalcodes nach RFC 6238 (TOTP, SHA-1, 6 Stellen, 30 Sekunden), wie sie
 * Authenticator-Apps erzeugen.
 */
final class Totp
{
    private const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    public const SCHRITT = 30;

    public static function geheimnis(): string
    {
        return self::base32(random_bytes(20));
    }

    public static function code(string $geheimnisBase32, int $schritt): string
    {
        $schluessel = self::base32Lesen($geheimnisBase32);
        $zaehler = pack('N2', ($schritt >> 32) & 0xFFFFFFFF, $schritt & 0xFFFFFFFF);
        $hash = hash_hmac('sha1', $zaehler, $schluessel, true);
        $versatz = ord($hash[19]) & 0x0F;
        $zahl = ((ord($hash[$versatz]) & 0x7F) << 24)
            | (ord($hash[$versatz + 1]) << 16)
            | (ord($hash[$versatz + 2]) << 8)
            | ord($hash[$versatz + 3]);
        return str_pad((string) ($zahl % 1_000_000), 6, '0', STR_PAD_LEFT);
    }

    public static function aktuellerSchritt(?int $zeit = null): int
    {
        return intdiv($zeit ?? time(), self::SCHRITT);
    }

    /**
     * Prüft einen Code mit einem Schritt Toleranz in beide Richtungen und liefert den
     * getroffenen Schritt. Codes aus einem Schritt <= $letzterSchritt gelten nicht mehr,
     * damit ein abgefangener Code nicht ein zweites Mal funktioniert.
     */
    public static function pruefen(string $geheimnisBase32, string $code, int $letzterSchritt, ?int $zeit = null): ?int
    {
        $code = preg_replace('/\s+/', '', $code) ?? '';
        if (preg_match('/^[0-9]{6}$/', $code) !== 1) {
            return null;
        }
        $jetzt = self::aktuellerSchritt($zeit);
        $treffer = null;
        foreach ([-1, 0, 1] as $abweichung) {
            $schritt = $jetzt + $abweichung;
            if (hash_equals(self::code($geheimnisBase32, $schritt), $code) && $schritt > $letzterSchritt) {
                $treffer = $schritt;
            }
        }
        return $treffer;
    }

    public static function uri(string $geheimnisBase32, string $konto, string $aussteller): string
    {
        return 'otpauth://totp/' . rawurlencode($aussteller . ':' . $konto)
            . '?secret=' . $geheimnisBase32
            . '&issuer=' . rawurlencode($aussteller)
            . '&algorithm=SHA1&digits=6&period=' . self::SCHRITT;
    }

    public static function base32(string $roh): string
    {
        $bits = '';
        foreach (str_split($roh) as $zeichen) {
            $bits .= str_pad(decbin(ord($zeichen)), 8, '0', STR_PAD_LEFT);
        }
        $aus = '';
        foreach (str_split($bits, 5) as $gruppe) {
            $aus .= self::ALPHABET[(int) bindec(str_pad($gruppe, 5, '0'))];
        }
        return $aus;
    }

    public static function base32Lesen(string $text): string
    {
        $text = strtoupper(preg_replace('/[\s=-]+/', '', $text) ?? '');
        $bits = '';
        foreach (str_split($text) as $zeichen) {
            $wert = strpos(self::ALPHABET, $zeichen);
            if ($wert === false) {
                return '';
            }
            $bits .= str_pad(decbin($wert), 5, '0', STR_PAD_LEFT);
        }
        $roh = '';
        foreach (str_split($bits, 8) as $byte) {
            if (strlen($byte) === 8) {
                $roh .= chr((int) bindec($byte));
            }
        }
        return $roh;
    }
}
