<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Tests\Fall;

final class AnfrageTest extends Fall
{
    public function testBuchungKlappt(): void
    {
        $b = $this->buchen();
        $this->status(201, $b['antwort']);
        $this->gleich(1, preg_match('/^RF-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/', $b['daten']['nummer']));
        $this->gleich(1, preg_match('/^[A-Za-z0-9_-]{43}$/', $b['daten']['token']));
        $mail = $this->postausgang()[0];
        $this->gleich('erika@beispiel.example', $mail['an']);
        $this->enthaelt('/status/#t=' . $b['daten']['token'], $mail['text'], 'Link mit Token im Fragment');
        $this->enthaeltNicht('Bremse quietscht', $mail['text'], 'Nachricht wird nicht zurückgeschickt');
    }

    public function testDatenLiegenVerschluesseltInDerDatenbank(): void
    {
        $b = $this->buchen();
        $z = $this->app()->db->zeile('SELECT * FROM auftraege WHERE nummer = ?', [$b['daten']['nummer']]);
        $roh = implode('|', array_map('strval', $z));
        foreach (['Erika', 'Mustermann', 'erika@beispiel.example', '030 23125 400', 'quietscht', $b['daten']['token']] as $klar) {
            $this->enthaeltNicht($klar, $roh, 'Klartext in der Datenbank');
        }
        $post = implode('|', array_map('strval', $this->app()->db->zeile('SELECT an_vs, text_vs FROM post')));
        $this->enthaeltNicht('erika@', $post, 'Postausgang verschlüsselt');
    }

    public function testZuSchnellAbgeschickt(): void
    {
        $t = $this->json($this->get('/api/termine'));
        $a = $this->post('/api/anfragen', ['leistung' => 'bremsen', 'rad' => 'city', 'datum' => '2026-10-14', 'zeit' => '08:30', 'name' => 'Erika Mustermann', 'email' => 'erika@beispiel.example', 'firma' => '', 'formular' => $t['formular']]);
        $this->status(422, $a);
        $this->gleich('bitte_erneut', $this->json($a)['fehler']);
    }

    public function testLockfeld(): void
    {
        $b = $this->buchen(['firma' => 'Spam GmbH']);
        $this->status(422, $b['antwort']);
        $this->gleich(0, (int) $this->app()->db->wert('SELECT COUNT(*) FROM auftraege'));
    }

    public function testGefaelschterZeitstempel(): void
    {
        $b = $this->buchen(['formular' => '1000000000.gefaelscht']);
        $this->status(422, $b['antwort']);
    }

    public function testUnbekanntesFeldWirdAbgelehnt(): void
    {
        $b = $this->buchen(['status' => 'abgeschlossen']);
        $this->status(400, $b['antwort'], 'Mass Assignment');
    }

    public function testNurJson(): void
    {
        $a = $this->anfrage('POST', '/api/anfragen', 'leistung=bremsen', ['content-type' => 'application/x-www-form-urlencoded']);
        $this->status(415, $a, 'Formular von fremder Seite');
        $a = $this->anfrage('POST', '/api/anfragen', '{kaputt', ['content-type' => 'application/json']);
        $this->status(400, $a);
        $a = $this->anfrage('POST', '/api/anfragen', '[1,2]', ['content-type' => 'application/json']);
        $this->status(400, $a);
        $a = $this->anfrage('POST', '/api/anfragen', str_repeat('x', 70000), ['content-type' => 'application/json']);
        $this->status(413, $a);
    }

    public function testFremdeHerkunft(): void
    {
        $this->status(403, $this->post('/api/anfragen', [], ['origin' => 'https://boese.example']));
        $this->status(403, $this->post('/api/anfragen', [], ['sec-fetch-site' => 'cross-site']));
        $this->status(405, $this->anfrage('DELETE', '/api/status'));
    }

    public function testPflichtfelderUndFehlermeldungen(): void
    {
        $b = $this->buchen(['name' => '', 'email' => 'keine-adresse', 'leistung' => 'ölwechsel', 'telefon' => 'ruf an']);
        $this->status(422, $b['antwort']);
        $felder = $b['daten']['felder'];
        foreach (['name', 'email', 'leistung', 'telefon'] as $f) {
            $this->wahr(isset($felder[$f]), "Fehler für $f");
        }
    }

    public function testTerminVoll(): void
    {
        $erste = $this->buchen();
        $zweite = $this->buchen();
        $this->gleich($erste['datum'] . $erste['zeit'], $zweite['datum'] . $zweite['zeit'], 'zwei Plätze je Zeit');
        $t = $this->json($this->get('/api/termine'));
        $this->uhr->vorstellen('+10 seconds');
        $a = $this->post('/api/anfragen', ['leistung' => 'bremsen', 'rad' => 'city', 'datum' => $erste['datum'], 'zeit' => $erste['zeit'], 'name' => 'Dritte Person', 'email' => 'dritte@beispiel.example', 'firma' => '', 'formular' => $t['formular']]);
        $this->status(409, $a, 'dritter Platz');
        $frei = array_values(array_filter($t['tage'][0]['zeiten'], fn ($z) => $z['zeit'] === $erste['zeit']))[0]['frei'];
        $this->gleich(0, $frei);
    }

    public function testDrosselung(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->status(201, $this->buchen(['email' => "kunde$i@beispiel.example"])['antwort']);
        }
        $a = $this->buchen(['email' => 'sechs@beispiel.example'])['antwort'];
        $this->status(429, $a);
        $this->wahr((int) ($a->kopf['Retry-After'] ?? 0) > 0, 'Retry-After');
        $roh = implode('|', array_map(fn ($z) => bin2hex((string) $z['schluessel']), $this->app()->db->zeilen('SELECT schluessel FROM drossel')));
        $this->enthaeltNicht(bin2hex('203.0.113.7'), $roh, 'IP im Klartext');
    }

    public function testSqlInjectionBleibtWirkungslos(): void
    {
        $b = $this->buchen(['nachricht' => "x'); DELETE FROM auftraege; --"]);
        $this->status(201, $b['antwort']);
        $this->gleich(1, (int) $this->app()->db->wert('SELECT COUNT(*) FROM auftraege'));
        $a = $this->post('/api/status', ['token' => "' OR '1'='1"]);
        $this->status(404, $a);
        $a = $this->get("/api/verwaltung/auftraege?status=angefragt' OR 1=1--");
        $this->status(401, $a);
    }

    public function testSkriptInNachrichtKommtNurMaskiertZurueck(): void
    {
        $b = $this->buchen(['nachricht' => '<img src=x onerror=alert(1)><script>alert(2)</script>']);
        $a = $this->post('/api/status/auskunft', ['token' => $b['daten']['token']]);
        $this->status(200, $a);
        $this->enthaeltNicht('<script>', $a->koerper);
        $this->enthaeltNicht('<img', $a->koerper);
        $this->enthaelt("\x5Cu003Cscript\x5Cu003E", $a->koerper, 'als JSON-Escape');
        $this->gleich('application/json; charset=utf-8', $a->kopf['Content-Type']);
    }

    public function testSicherheitskopf(): void
    {
        $a = $this->get('/api/termine');
        foreach (['Cache-Control' => 'no-store', 'X-Content-Type-Options' => 'nosniff', 'X-Frame-Options' => 'DENY', 'Referrer-Policy' => 'no-referrer'] as $k => $v) {
            $this->gleich($v, $a->kopf[$k] ?? null, $k);
        }
        $this->enthaelt("default-src 'none'", $a->kopf['Content-Security-Policy']);
        $this->enthaelt('max-age=63072000', $a->kopf['Strict-Transport-Security']);
    }

    public function testUnbekannteAdresse(): void
    {
        $this->status(404, $this->get('/api/../app/daten/leistungen.json'));
        $this->status(404, $this->get('/api/gibtsnicht'));
    }
}
