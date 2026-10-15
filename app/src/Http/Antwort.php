<?php

declare(strict_types=1);

namespace Radhaus\Http;

final class Antwort
{
    /** @var array<string, string> */
    public array $kopf = [];

    /** @var list<string> */
    public array $kekse = [];

    public function __construct(public int $status = 200, public string $koerper = '')
    {
    }

    /** @param array<mixed> $daten */
    public static function json(array $daten, int $status = 200): self
    {
        $a = new self($status, (string) json_encode(
            $daten,
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_THROW_ON_ERROR,
        ));
        $a->kopf['Content-Type'] = 'application/json; charset=utf-8';
        return $a;
    }

    public static function fehler(HttpFehler $f): self
    {
        $a = self::json(['fehler' => $f->kennung, 'meldung' => $f->getMessage()] + $f->zusatz, $f->status);
        if ($f->wartenSek !== null) {
            $a->kopf['Retry-After'] = (string) $f->wartenSek;
        }
        return $a;
    }

    public function keks(string $name, string $wert, int $lebensdauer, bool $sicher, string $pfad = '/'): void
    {
        $teile = [rawurlencode($name) . '=' . rawurlencode($wert), 'Path=' . $pfad, 'HttpOnly', 'SameSite=Strict'];
        if ($lebensdauer > 0) {
            $teile[] = 'Max-Age=' . $lebensdauer;
        } elseif ($lebensdauer < 0) {
            $teile[] = 'Max-Age=0';
            $teile[] = 'Expires=Thu, 01 Jan 1970 00:00:00 GMT';
        }
        if ($sicher) {
            $teile[] = 'Secure';
        }
        $this->kekse[] = implode('; ', $teile);
    }

    public function senden(): void
    {
        http_response_code($this->status);
        header_remove('X-Powered-By');
        foreach ($this->kopf as $name => $wert) {
            header($name . ': ' . $wert);
        }
        foreach ($this->kekse as $keks) {
            header('Set-Cookie: ' . $keks, false);
        }
        echo $this->koerper;
    }
}
