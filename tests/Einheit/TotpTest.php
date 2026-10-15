<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Sicherheit\Totp;
use Radhaus\Tests\Fall;

final class TotpTest extends Fall
{
    /** Testwerte aus RFC 6238, Anhang B (SHA-1), auf 6 Stellen gekürzt. */
    public function testRfc6238(): void
    {
        $geheimnis = Totp::base32('12345678901234567890');
        foreach ([59 => '287082', 1111111109 => '081804', 1111111111 => '050471', 1234567890 => '005924', 2000000000 => '279037', 20000000000 => '353130'] as $zeit => $code) {
            $this->gleich($code, Totp::code($geheimnis, intdiv($zeit, 30)), "T=$zeit");
        }
    }

    public function testBase32HinUndZurueck(): void
    {
        $roh = random_bytes(20);
        $this->gleich($roh, Totp::base32Lesen(Totp::base32($roh)));
        $this->gleich(32, strlen(Totp::geheimnis()));
    }

    public function testToleranzEinSchritt(): void
    {
        $g = Totp::geheimnis();
        $zeit = 1_760_000_000;
        $vorher = Totp::code($g, Totp::aktuellerSchritt($zeit) - 1);
        $this->wahr(Totp::pruefen($g, $vorher, 0, $zeit) !== null, 'vorheriger Schritt');
        $alt = Totp::code($g, Totp::aktuellerSchritt($zeit) - 3);
        $this->gleich(null, Totp::pruefen($g, $alt, 0, $zeit), 'zu alter Code');
    }

    public function testKeinZweitesMal(): void
    {
        $g = Totp::geheimnis();
        $zeit = 1_760_000_000;
        $code = Totp::code($g, Totp::aktuellerSchritt($zeit));
        $schritt = Totp::pruefen($g, $code, 0, $zeit);
        $this->wahr($schritt !== null);
        $this->gleich(null, Totp::pruefen($g, $code, (int) $schritt, $zeit), 'abgefangener Code');
    }

    public function testUnsinnigeEingaben(): void
    {
        $g = Totp::geheimnis();
        foreach (['', '12345', '1234567', 'abcdef', "123456\n"] as $code) {
            $this->gleich(null, Totp::pruefen($g, $code, 0, 1_760_000_000), var_export($code, true));
        }
    }

    public function testUri(): void
    {
        $u = Totp::uri('JBSWY3DPEHPK3PXP', 'mira', 'Radhaus Fuhse');
        $this->enthaelt('otpauth://totp/Radhaus%20Fuhse%3Amira?secret=JBSWY3DPEHPK3PXP', $u);
        $this->enthaelt('period=30', $u);
    }
}
