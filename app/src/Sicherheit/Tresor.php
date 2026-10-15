<?php

declare(strict_types=1);

namespace Radhaus\Sicherheit;

use RuntimeException;

/**
 * Verschlüsselung personenbezogener Felder mit libsodium (XChaCha20-Poly1305).
 *
 * Aus einem Hauptschlüssel werden getrennte Unterschlüssel abgeleitet, damit ein
 * Schlüssel nie für zwei Zwecke dient. Der Kontext (z. B. "auftrag:RF-ABCD-EFGH:email")
 * geht als zusätzliche Authentifizierung ein: ein Wert lässt sich nicht unbemerkt in
 * eine andere Zeile oder Spalte kopieren.
 */
final class Tresor
{
    private const VERSION = "\x01";
    private const KONTEXT = 'RadhausF';

    private string $daten;
    private string $index;
    private string $drossel;
    private string $sicherung;
    private string $signatur;

    public function __construct(string $hauptschluessel)
    {
        if (strlen($hauptschluessel) !== SODIUM_CRYPTO_KDF_KEYBYTES) {
            throw new RuntimeException('Hauptschlüssel muss 32 Byte lang sein.');
        }
        $this->daten = sodium_crypto_kdf_derive_from_key(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_KEYBYTES, 1, self::KONTEXT, $hauptschluessel);
        $this->index = sodium_crypto_kdf_derive_from_key(32, 2, self::KONTEXT, $hauptschluessel);
        $this->drossel = sodium_crypto_kdf_derive_from_key(32, 3, self::KONTEXT, $hauptschluessel);
        $this->sicherung = sodium_crypto_kdf_derive_from_key(SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_KEYBYTES, 4, self::KONTEXT, $hauptschluessel);
        $this->signatur = sodium_crypto_kdf_derive_from_key(32, 5, self::KONTEXT, $hauptschluessel);
        sodium_memzero($hauptschluessel);
    }

    public function verschluesseln(string $klartext, string $kontext): string
    {
        $nonce = random_bytes(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
        return self::VERSION . $nonce . sodium_crypto_aead_xchacha20poly1305_ietf_encrypt($klartext, $kontext, $nonce, $this->daten);
    }

    public function entschluesseln(string $blob, string $kontext): string
    {
        $kopf = 1 + SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES;
        if (strlen($blob) <= $kopf || $blob[0] !== self::VERSION) {
            throw new RuntimeException('Unbekanntes Format.');
        }
        $klar = sodium_crypto_aead_xchacha20poly1305_ietf_decrypt(substr($blob, $kopf), $kontext, substr($blob, 1, $kopf - 1), $this->daten);
        if ($klar === false) {
            throw new RuntimeException('Entschlüsselung fehlgeschlagen.');
        }
        return $klar;
    }

    public function verschluesselnOptional(?string $klartext, string $kontext): ?string
    {
        return $klartext === null || $klartext === '' ? null : $this->verschluesseln($klartext, $kontext);
    }

    public function entschluesselnOptional(mixed $blob, string $kontext): ?string
    {
        return is_string($blob) && $blob !== '' ? $this->entschluesseln($blob, $kontext) : null;
    }

    /** Blinder Index: erlaubt das Suchen nach einem Wert, ohne ihn zu speichern. */
    public function index(string $wert): string
    {
        return hash_hmac('sha256', mb_strtolower(trim($wert)), $this->index, true);
    }

    /** Schlüssel für die Drosselung. Wechselt täglich, damit Einträge nicht über Tage verknüpfbar sind. */
    public function drosselSchluessel(string $ip, string $tag): string
    {
        return hash_hmac('sha256', $tag . '|' . $ip, $this->drossel, true);
    }

    /** Signiert kurze Werte, etwa den Zeitstempel im Buchungsformular. */
    public function signieren(string $wert): string
    {
        return $wert . '.' . self::b64(hash_hmac('sha256', $wert, $this->signatur, true));
    }

    public function signaturPruefen(string $signiert): ?string
    {
        $punkt = strrpos($signiert, '.');
        if ($punkt === false) {
            return null;
        }
        $wert = substr($signiert, 0, $punkt);
        return hash_equals($this->signieren($wert), $signiert) ? $wert : null;
    }

    public function sicherungsschluessel(): string
    {
        return $this->sicherung;
    }

    public static function b64(string $roh): string
    {
        return rtrim(strtr(base64_encode($roh), '+/', '-_'), '=');
    }

    /** @param int<1, max> $bytes */
    public static function zufallsToken(int $bytes = 32): string
    {
        return self::b64(random_bytes($bytes));
    }

    public static function tokenHash(string $token): string
    {
        return hash('sha256', $token, true);
    }
}
