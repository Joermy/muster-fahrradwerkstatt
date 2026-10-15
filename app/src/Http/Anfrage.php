<?php

declare(strict_types=1);

namespace Radhaus\Http;

use JsonException;

final class Anfrage
{
    public const MAX_KOERPER = 65536;

    /**
     * @param array<string, string> $kopf    Namen klein geschrieben
     * @param array<string, string> $abfrage
     * @param array<string, string> $kekse
     */
    public function __construct(
        public readonly string $methode,
        public readonly string $pfad,
        public readonly array $kopf = [],
        public readonly array $abfrage = [],
        public readonly array $kekse = [],
        public readonly string $koerper = '',
        public readonly string $ip = '0.0.0.0',
    ) {
    }

    /** @param list<string> $vertrauteProxys */
    public static function ausGlobalen(array $vertrauteProxys = []): self
    {
        $kopf = [];
        foreach ($_SERVER as $name => $wert) {
            if (!is_string($wert)) {
                continue;
            }
            if (str_starts_with($name, 'HTTP_')) {
                $kopf[strtolower(str_replace('_', '-', substr($name, 5)))] = $wert;
            } elseif ($name === 'CONTENT_TYPE' || $name === 'CONTENT_LENGTH') {
                $kopf[strtolower(str_replace('_', '-', $name))] = $wert;
            }
        }
        $pfad = parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH);
        $pfad = is_string($pfad) ? rawurldecode($pfad) : '/';

        $laenge = (int) ($kopf['content-length'] ?? 0);
        $koerper = '';
        if ($laenge > self::MAX_KOERPER) {
            $koerper = str_repeat(' ', self::MAX_KOERPER + 1);
        } elseif ($laenge > 0) {
            $koerper = (string) file_get_contents('php://input', false, null, 0, self::MAX_KOERPER + 1);
        }

        $ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '0.0.0.0');
        if ($vertrauteProxys !== [] && in_array($ip, $vertrauteProxys, true) && isset($kopf['x-forwarded-for'])) {
            $kette = array_map('trim', explode(',', $kopf['x-forwarded-for']));
            $letzte = end($kette);
            if (is_string($letzte) && filter_var($letzte, FILTER_VALIDATE_IP)) {
                $ip = $letzte;
            }
        }

        $abfrage = [];
        foreach ($_GET as $k => $v) {
            if (is_string($k) && is_string($v)) {
                $abfrage[$k] = $v;
            }
        }
        $kekse = [];
        foreach ($_COOKIE as $k => $v) {
            if (is_string($k) && is_string($v)) {
                $kekse[$k] = $v;
            }
        }

        return new self(
            strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET')),
            $pfad,
            $kopf,
            $abfrage,
            $kekse,
            $koerper,
            $ip,
        );
    }

    public function kopf(string $name): string
    {
        return $this->kopf[strtolower($name)] ?? '';
    }

    /**
     * JSON-Körper als Objekt. Wirft HttpFehler bei falschem Typ, zu großem Körper oder kaputtem JSON.
     *
     * @return array<string, mixed>
     */
    public function json(): array
    {
        if (strlen($this->koerper) > self::MAX_KOERPER) {
            throw new HttpFehler(413, 'zu_gross', 'Die Anfrage ist zu groß.');
        }
        $typ = strtolower(trim(explode(';', $this->kopf('content-type'))[0]));
        if ($typ !== 'application/json') {
            throw new HttpFehler(415, 'falscher_typ', 'Erwartet wird application/json.');
        }
        if ($this->koerper === '') {
            return [];
        }
        try {
            $daten = json_decode($this->koerper, true, 8, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new HttpFehler(400, 'kaputtes_json', 'Die Anfrage ist kein gültiges JSON.');
        }
        if (!is_array($daten) || array_is_list($daten) && $daten !== []) {
            throw new HttpFehler(400, 'kein_objekt', 'Erwartet wird ein JSON-Objekt.');
        }
        /** @var array<string, mixed> $daten */
        return $daten;
    }
}
