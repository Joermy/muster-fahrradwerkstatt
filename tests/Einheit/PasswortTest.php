<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Sicherheit\Passwort;
use Radhaus\Tests\Fall;

final class PasswortTest extends Fall
{
    public function testArgon2id(): void
    {
        $h = Passwort::hashen('Kettenblatt-Speiche-42');
        $this->wahr(str_starts_with($h, '$argon2id$v=19$m=65536,t=4,p=1$'));
        $this->wahr(Passwort::pruefen('Kettenblatt-Speiche-42', $h));
        $this->wahr(!Passwort::pruefen('kettenblatt-speiche-42', $h));
        $this->wahr(!Passwort::neuHashenNoetig($h));
    }

    public function testUnbekannterBenutzerDauertGleichLang(): void
    {
        $h = Passwort::hashen('irgendwas-langes-1');
        Passwort::pruefen('x', null);
        $t = microtime(true);
        Passwort::pruefen('x', $h);
        $mitHash = microtime(true) - $t;
        $t = microtime(true);
        $this->wahr(!Passwort::pruefen('x', null));
        $ohne = microtime(true) - $t;
        $this->wahr($ohne > $mitHash * 0.5, 'Attrappe rechnet nicht mit');
    }

    public function testSchwachePasswoerter(): void
    {
        foreach (['kurz', 'passwort1234', 'Werkstatt123', 'aaaaaaaaaaaaaaaa', 'mira-ist-toll-2026'] as $p) {
            $this->wahr(Passwort::schwaeche($p, 'mira') !== null, $p);
        }
        $this->gleich(null, Passwort::schwaeche('Kettenblatt-Speiche-42', 'mira'));
    }
}
