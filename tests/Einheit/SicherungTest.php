<?php

declare(strict_types=1);

namespace Radhaus\Tests\Einheit;

use Radhaus\Dienste\Sicherung;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Tests\Fall;
use RuntimeException;

final class SicherungTest extends Fall
{
    private string $ordner = '';

    public function vorher(): void
    {
        parent::vorher();
        $this->ordner = sys_get_temp_dir() . '/radhaus-sicherung-' . bin2hex(random_bytes(4));
    }

    public function nachher(): void
    {
        foreach (glob($this->ordner . '/{,.}*', GLOB_BRACE) ?: [] as $d) {
            if (is_file($d)) {
                unlink($d);
            }
        }
        if (is_dir($this->ordner)) {
            rmdir($this->ordner);
        }
        parent::nachher();
    }

    public function testVerschluesseltUndZurueck(): void
    {
        $this->buchen(['name' => 'Gesine Probst', 'email' => 'gesine@beispiel.example']);
        $datei = $this->app()->sicherung->erstellen($this->ordner);
        $inhalt = (string) file_get_contents($datei);
        $this->enthaeltNicht('SQLite format 3', $inhalt, 'kein Klartext-Kopf');
        $this->enthaeltNicht('auftraege', $inhalt, 'keine Tabellennamen');
        $this->gleich(0, count(glob($this->ordner . '/.roh-*') ?: []), 'Klartext-Kopie entfernt');
        $this->gleich(0o600, fileperms($datei) & 0o777, 'nur für den Besitzer lesbar');

        $ziel = $this->ordner . '/zurueck.sqlite';
        $this->app()->sicherung->entschluesseln($datei, $ziel);
        $pdo = new \PDO('sqlite:' . $ziel);
        $this->gleich('ok', $pdo->query('PRAGMA integrity_check')?->fetchColumn());
        $this->gleich(1, (int) $pdo->query('SELECT COUNT(*) FROM auftraege')?->fetchColumn());
        unlink($ziel);
    }

    public function testVeraenderteSicherungFaelltAuf(): void
    {
        $datei = $this->app()->sicherung->erstellen($this->ordner);
        $roh = (string) file_get_contents($datei);
        $roh[strlen($roh) - 40] = chr(ord($roh[strlen($roh) - 40]) ^ 1);
        file_put_contents($datei, $roh);
        $this->wirft(RuntimeException::class, fn () => $this->app()->sicherung->entschluesseln($datei, $this->ordner . '/x.sqlite'));
        $this->wahr(!is_file($this->ordner . '/x.sqlite'), 'halbe Datei wird entfernt');

        // Abgeschnitten
        $datei2 = $this->app()->sicherung->erstellen($this->ordner);
        file_put_contents($datei2, substr((string) file_get_contents($datei2), 0, -100));
        $this->wirft(RuntimeException::class, fn () => $this->app()->sicherung->entschluesseln($datei2, $this->ordner . '/y.sqlite'));
    }

    public function testAndererSchluesselKannNichtLesen(): void
    {
        $datei = $this->app()->sicherung->erstellen($this->ordner);
        $fremd = new Sicherung($this->app()->db, new Tresor(random_bytes(32)), $this->uhr);
        $this->wirft(RuntimeException::class, fn () => $fremd->entschluesseln($datei, $this->ordner . '/z.sqlite'));
    }

    public function testNurDieLetztenBleiben(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->app()->sicherung->erstellen($this->ordner, 3);
            $this->uhr->vorstellen('+1 day');
        }
        $this->gleich(3, count(glob($this->ordner . '/radhaus-*.sqlite.enc') ?: []));
    }
}
