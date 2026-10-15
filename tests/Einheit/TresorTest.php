<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Sicherheit\Tresor;
use Radhaus\Tests\Fall;
use RuntimeException;

final class TresorTest extends Fall
{
    private Tresor $t;

    public function vorher(): void
    {
        $this->t = new Tresor(str_repeat("\x07", 32));
    }

    public function testHinUndZurueck(): void
    {
        $blob = $this->t->verschluesseln('erika@beispiel.example', 'auftrag:RF-AAAA-BBBB:email');
        $this->enthaeltNicht('erika', $blob);
        $this->gleich('erika@beispiel.example', $this->t->entschluesseln($blob, 'auftrag:RF-AAAA-BBBB:email'));
    }

    public function testJedesMalAndererGeheimtext(): void
    {
        $this->wahr($this->t->verschluesseln('x', 'k') !== $this->t->verschluesseln('x', 'k'));
    }

    public function testFalscherKontextScheitert(): void
    {
        $blob = $this->t->verschluesseln('geheim', 'auftrag:RF-AAAA-BBBB:email');
        $this->wirft(RuntimeException::class, fn () => $this->t->entschluesseln($blob, 'auftrag:RF-CCCC-DDDD:email'), 'in andere Zeile kopiert');
        $this->wirft(RuntimeException::class, fn () => $this->t->entschluesseln($blob, 'auftrag:RF-AAAA-BBBB:name'), 'in andere Spalte kopiert');
    }

    public function testVeraenderterGeheimtextScheitert(): void
    {
        $blob = $this->t->verschluesseln('geheim', 'k');
        $blob[30] = chr(ord($blob[30]) ^ 1);
        $this->wirft(RuntimeException::class, fn () => $this->t->entschluesseln($blob, 'k'));
    }

    public function testAndererSchluesselScheitert(): void
    {
        $blob = $this->t->verschluesseln('geheim', 'k');
        $this->wirft(RuntimeException::class, fn () => (new Tresor(str_repeat("\x08", 32)))->entschluesseln($blob, 'k'));
    }

    public function testFalscheSchluessellaenge(): void
    {
        $this->wirft(RuntimeException::class, fn () => new Tresor('zu kurz'));
    }

    public function testIndexIgnoriertGrossschreibung(): void
    {
        $this->gleich($this->t->index('Erika@Beispiel.example '), $this->t->index('erika@beispiel.example'));
        $this->wahr($this->t->index('a@b.example') !== $this->t->index('c@b.example'));
    }

    public function testSignatur(): void
    {
        $s = $this->t->signieren('1760342400');
        $this->gleich('1760342400', $this->t->signaturPruefen($s));
        $this->gleich(null, $this->t->signaturPruefen('1760342401' . substr($s, 10)), 'veränderter Wert');
        $this->gleich(null, $this->t->signaturPruefen('ohne-punkt'));
    }

    public function testDrosselSchluesselWechseltTaeglich(): void
    {
        $this->wahr($this->t->drosselSchluessel('203.0.113.7', '2026-10-13') !== $this->t->drosselSchluessel('203.0.113.7', '2026-10-14'));
        $this->enthaeltNicht('203.0.113.7', $this->t->drosselSchluessel('203.0.113.7', '2026-10-13'));
    }

    public function testTokenFormat(): void
    {
        $this->gleich(1, preg_match('/^[A-Za-z0-9_-]{43}$/', Tresor::zufallsToken()));
        $this->gleich(32, strlen(Tresor::tokenHash('x')));
    }
}
