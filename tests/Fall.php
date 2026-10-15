<?php

declare(strict_types=1);

namespace Radhaus\Tests;

use Radhaus\App;
use Radhaus\Http\Anfrage;
use Radhaus\Http\Antwort;
use Radhaus\Konfiguration;
use Radhaus\Uhr;
use RuntimeException;
use Throwable;

/** Grundlage aller Tests: Prüfungen und eine App mit Datenbank im Arbeitsspeicher. */
abstract class Fall
{
    public static int $pruefungen = 0;

    protected ?App $app = null;
    protected Uhr $uhr;
    /** @var array<string, string> */
    protected array $kekse = [];
    protected string $csrf = '';

    public function vorher(): void
    {
    }

    public function nachher(): void
    {
    }

    protected function app(string $umgebung = 'produktion'): App
    {
        if ($this->app === null) {
            $this->uhr = new Uhr();
            $this->uhr->festhalten('2026-10-13 10:00:00');
            $this->app = new App(Konfiguration::aus([
                'APP_UMGEBUNG' => $umgebung,
                'APP_URL' => 'https://radhaus-fuhse.example',
                'APP_SCHLUESSEL' => 'base64:' . base64_encode(str_repeat("\x2a", 32)),
                'DATENBANK' => ':memory:',
                'POST_MODUS' => 'ausgang',
                'POST_INHABER' => 'inhaberin@radhaus-fuhse.example',
                'WURZEL' => RADHAUS_WURZEL,
            ]), $this->uhr);
        }
        return $this->app;
    }

    /**
     * @param array<string, mixed>|string|null $koerper
     * @param array<string, string> $kopf
     */
    protected function anfrage(string $methode, string $pfad, array|string|null $koerper = null, array $kopf = [], string $ip = '203.0.113.7'): Antwort
    {
        $abfrage = [];
        if (str_contains($pfad, '?')) {
            [$pfad, $q] = explode('?', $pfad, 2);
            parse_str($q, $abfrage);
        }
        $roh = is_array($koerper) ? (string) json_encode($koerper) : (string) $koerper;
        $kopf = array_change_key_case($kopf + ($koerper !== null ? ['content-type' => 'application/json'] : []) + ($this->csrf !== '' ? ['x-csrf-token' => $this->csrf] : []), CASE_LOWER);
        $kopf += $methode === 'POST' ? ['origin' => 'https://radhaus-fuhse.example', 'sec-fetch-site' => 'same-origin'] : [];
        $antwort = $this->app()->beantworten(new Anfrage($methode, $pfad, $kopf, $abfrage, $this->kekse, $roh, $ip));
        foreach ($antwort->kekse as $keks) {
            [$paar] = explode(';', $keks, 2);
            [$name, $wert] = explode('=', $paar, 2);
            if (str_contains($keks, 'Max-Age=0')) {
                unset($this->kekse[rawurldecode($name)]);
            } else {
                $this->kekse[rawurldecode($name)] = rawurldecode($wert);
            }
        }
        return $antwort;
    }

    /** @param array<string, mixed> $koerper */
    protected function post(string $pfad, array $koerper = [], array $kopf = []): Antwort
    {
        return $this->anfrage('POST', $pfad, $koerper, $kopf);
    }

    protected function get(string $pfad): Antwort
    {
        return $this->anfrage('GET', $pfad);
    }

    /** @return array<string, mixed> */
    protected function json(Antwort $a): array
    {
        $d = json_decode($a->koerper, true);
        if (!is_array($d)) {
            throw new RuntimeException('Keine JSON-Antwort: ' . substr($a->koerper, 0, 200));
        }
        return $d;
    }

    /** Eine gültige Terminanfrage auf den ersten freien Termin. */
    protected function buchen(array $ueberschreiben = []): array
    {
        $termine = $this->json($this->get('/api/termine'));
        $this->uhr->vorstellen('+10 seconds');
        foreach ($termine['tage'] as $tag) {
            foreach ($tag['zeiten'] as $z) {
                if ($z['frei'] > 0) {
                    $a = $this->post('/api/anfragen', $ueberschreiben + [
                        'leistung' => 'bremsen', 'rad' => 'e-bike', 'datum' => $tag['datum'], 'zeit' => $z['zeit'],
                        'name' => 'Erika Mustermann', 'email' => 'erika@beispiel.example', 'telefon' => '030 23125 400',
                        'nachricht' => 'Bremse quietscht.', 'firma' => '', 'formular' => $termine['formular'],
                    ]);
                    return ['antwort' => $a, 'daten' => $this->json($a), 'datum' => $tag['datum'], 'zeit' => $z['zeit'], 'formular' => $termine['formular']];
                }
            }
        }
        throw new RuntimeException('Kein freier Termin.');
    }

    /** Legt ein Konto an und meldet es vollständig an (Passwort geändert, TOTP aktiv). */
    protected function alsVerwaltung(string $rolle = 'inhaber', string $name = 'mira'): array
    {
        $app = $this->app();
        $start = $app->zugang->benutzerAnlegen($name, 'Mira Ohlendorf', $rolle, null);
        $neu = 'Kettenblatt-Speiche-42';
        $this->post('/api/verwaltung/anmelden', ['name' => $name, 'passwort' => $start['passwort']]);
        $this->csrf = (string) $this->json($this->get('/api/verwaltung/ich'))['csrf'];
        $this->post('/api/verwaltung/passwort', ['alt' => $start['passwort'], 'neu' => $neu]);
        $this->csrf = '';
        $this->post('/api/verwaltung/anmelden', ['name' => $name, 'passwort' => $neu]);
        $this->csrf = (string) $this->json($this->get('/api/verwaltung/ich'))['csrf'];
        $g = $this->json($this->post('/api/verwaltung/zweifaktor/start'));
        $code = \Radhaus\Sicherheit\Totp::code($g['geheimnis'], \Radhaus\Sicherheit\Totp::aktuellerSchritt($this->uhr->zeitstempel()));
        $ersatz = $this->json($this->post('/api/verwaltung/zweifaktor/bestaetigen', ['code' => $code]))['ersatzcodes'];
        return ['name' => $name, 'passwort' => $neu, 'geheimnis' => $g['geheimnis'], 'ersatz' => $ersatz, 'id' => $start['id']];
    }

    // ------------------------------------------------------------ Prüfungen

    protected function gleich(mixed $erwartet, mixed $ist, string $hinweis = ''): void
    {
        self::$pruefungen++;
        if ($erwartet !== $ist) {
            throw new RuntimeException(($hinweis !== '' ? $hinweis . ': ' : '') . 'erwartet ' . var_export($erwartet, true) . ', ist ' . var_export($ist, true));
        }
    }

    protected function wahr(bool $wert, string $hinweis = 'Bedingung nicht erfüllt'): void
    {
        self::$pruefungen++;
        if (!$wert) {
            throw new RuntimeException($hinweis);
        }
    }

    protected function status(int $erwartet, Antwort $a, string $hinweis = ''): void
    {
        $this->gleich($erwartet, $a->status, ($hinweis !== '' ? $hinweis . ' ' : '') . 'HTTP-Status (' . substr($a->koerper, 0, 160) . ')');
    }

    protected function enthaelt(string $nadel, string $heuhaufen, string $hinweis = ''): void
    {
        self::$pruefungen++;
        if (!str_contains($heuhaufen, $nadel)) {
            throw new RuntimeException(($hinweis !== '' ? $hinweis . ': ' : '') . "'$nadel' fehlt");
        }
    }

    protected function enthaeltNicht(string $nadel, string $heuhaufen, string $hinweis = ''): void
    {
        self::$pruefungen++;
        if (str_contains($heuhaufen, $nadel)) {
            throw new RuntimeException(($hinweis !== '' ? $hinweis . ': ' : '') . "'$nadel' darf nicht vorkommen");
        }
    }

    /** @param callable(): mixed $f */
    protected function wirft(string $klasse, callable $f, string $hinweis = ''): Throwable
    {
        self::$pruefungen++;
        try {
            $f();
        } catch (Throwable $t) {
            if ($t instanceof $klasse) {
                return $t;
            }
            throw new RuntimeException(($hinweis !== '' ? $hinweis . ': ' : '') . "erwartet $klasse, kam " . $t::class . ': ' . $t->getMessage());
        }
        throw new RuntimeException(($hinweis !== '' ? $hinweis . ': ' : '') . "erwartet $klasse, aber nichts geworfen");
    }

    /** @return list<array{id: int, an: string, betreff: string, text: string, art: string, erstellt: string}> */
    protected function postausgang(): array
    {
        return $this->app()->post->ausgang(100);
    }
}
