<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Http\HttpFehler;
use Radhaus\Tests\Fall;
use Radhaus\Validierung;

final class ValidierungTest extends Fall
{
    public function testUnbekannteFelder(): void
    {
        $f = $this->wirft(HttpFehler::class, fn () => Validierung::nur(['name' => 'x', 'status' => 'abgeschlossen'], ['name']));
        $this->gleich(400, $f->status);
    }

    public function testSteuerzeichenUndRichtungswechsel(): void
    {
        $this->gleich('Erika Mustermann', Validierung::saeubern("Erika\x00 \u{202E}Mustermann\u{200B}"));
        $this->gleich("Zeile 1\nZeile 2", Validierung::saeubern("Zeile 1\r\n\x07Zeile 2", true));
    }

    public function testNamen(): void
    {
        foreach (['Erika Mustermann', "Jean-Luc O'Neill", 'Mehmet Yıldız', 'Zoë Ångström'] as $n) {
            $v = new Validierung(['n' => $n]);
            $this->gleich($n, $v->name('n'), $n);
        }
        foreach (['<script>', "Robert'); DROP TABLE auftraege;--", '1234', 'x'] as $n) {
            $v = new Validierung(['n' => $n]);
            $this->gleich(null, $v->name('n'), $n);
        }
    }

    public function testEmailOhneKopfzeilenTrick(): void
    {
        $v = new Validierung(['a' => "opfer@beispiel.example\r\nBcc: viele@beispiel.example", 'b' => 'Erika@Beispiel.Example']);
        $this->gleich(null, $v->email('a'));
        $this->gleich('erika@beispiel.example', $v->email('b'));
    }

    public function testTypen(): void
    {
        $v = new Validierung(['t' => ['array'], 'w' => 'true', 'z' => '5', 'd' => '2026-02-30', 'u' => '24:00']);
        $this->gleich(null, $v->text('t', 1, 10));
        $this->gleich(false, $v->wahrheit('w'));
        $this->gleich(null, $v->ganzzahl('z', 1, 10));
        $this->gleich(null, $v->datum('d'));
        $this->gleich(null, $v->uhrzeit('u'));
        $this->wirft(HttpFehler::class, fn () => $v->pruefen());
    }

    public function testUngueltigesUtf8(): void
    {
        $v = new Validierung(['t' => "\xC3\x28"]);
        $this->gleich(null, $v->text('t', 1, 10));
    }
}
