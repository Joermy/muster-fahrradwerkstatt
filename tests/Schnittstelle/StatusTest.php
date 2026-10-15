<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Tests\Fall;

final class StatusTest extends Fall
{
    public function testKundeSiehtStandOhneVolleAdresse(): void
    {
        $b = $this->buchen();
        $s = $this->json($this->post('/api/status', ['token' => $b['daten']['token']]));
        $this->gleich('angefragt', $s['status']);
        $this->gleich('Erika', $s['vorname']);
        $this->gleich('e••••@beispiel.example', $s['email']);
        $this->wahr(!isset($s['telefon']) && !isset($s['nachricht']), 'nur das Nötigste');
        $this->gleich(true, $s['absagen_moeglich']);
    }

    public function testFalscherOderFehlenderToken(): void
    {
        $this->buchen();
        foreach (['', 'abc', str_repeat('A', 43), str_repeat('A', 44)] as $t) {
            $this->status(404, $this->post('/api/status', ['token' => $t]), var_export($t, true));
        }
        $this->status(404, $this->post('/api/status', []));
        $this->status(404, $this->post('/api/status', ['token' => ['$ne' => '']]));
    }

    public function testAbsagenGibtPlatzFrei(): void
    {
        $b = $this->buchen();
        $this->status(200, $this->post('/api/status/absagen', ['token' => $b['daten']['token']]));
        $s = $this->json($this->post('/api/status', ['token' => $b['daten']['token']]));
        $this->gleich('storniert', $s['status']);
        $this->status(409, $this->post('/api/status/absagen', ['token' => $b['daten']['token']]), 'zweimal');
        $this->wahr($this->app()->kalender->platzFrei($b['datum'], $b['zeit']));
    }

    public function testAuskunftEnthaeltAlles(): void
    {
        $b = $this->buchen();
        $a = $this->post('/api/status/auskunft', ['token' => $b['daten']['token']]);
        $d = $this->json($a);
        $this->gleich('erika@beispiel.example', $d['kontaktdaten']['email']);
        $this->gleich('030 23125 400', $d['kontaktdaten']['telefon']);
        $this->gleich('Bremse quietscht.', $d['kontaktdaten']['nachricht']);
        $this->enthaelt('attachment', $a->kopf['Content-Disposition']);
        $this->enthaelt('Radhaus Fuhse', $d['verantwortlich']);
    }

    public function testLoeschen(): void
    {
        $b = $this->buchen();
        $this->status(422, $this->post('/api/status/loeschen', ['token' => $b['daten']['token'], 'bestaetigung' => 'ja']));
        $d = $this->json($this->post('/api/status/loeschen', ['token' => $b['daten']['token'], 'bestaetigung' => 'LÖSCHEN']));
        $this->gleich(true, $d['geloescht']);
        $this->status(404, $this->post('/api/status', ['token' => $b['daten']['token']]), 'Link danach ungültig');
        $z = $this->app()->db->zeile('SELECT * FROM auftraege');
        foreach (['name_vs', 'email_vs', 'email_index', 'telefon_vs', 'nachricht_vs'] as $s) {
            $this->gleich(null, $z[$s], $s);
        }
        $this->gleich('bremsen', $z['leistung'], 'Leistung bleibt für die Buchhaltung');
    }

    public function testLoeschenNichtWaehrendDasRadDaIst(): void
    {
        $b = $this->buchen();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $this->app()->db->ausfuehren("UPDATE auftraege SET status = 'in_arbeit' WHERE id = ?", [$id]);
        $a = $this->post('/api/status/loeschen', ['token' => $b['daten']['token'], 'bestaetigung' => 'LÖSCHEN']);
        $this->status(409, $a);
        $this->gleich('rad_in_werkstatt', $this->json($a)['fehler']);
    }

    public function testNeuerLinkMachtAltenUngueltig(): void
    {
        $b = $this->buchen();
        $nummer = $b['daten']['nummer'];
        $falsch = $this->json($this->post('/api/status/link', ['nummer' => $nummer, 'email' => 'fremd@beispiel.example']));
        $richtig = $this->json($this->post('/api/status/link', ['nummer' => $nummer, 'email' => 'Erika@Beispiel.example']));
        $this->gleich($falsch, $richtig, 'gleiche Antwort, kein Ausforschen');
        $this->status(404, $this->post('/api/status', ['token' => $b['daten']['token']]), 'alter Link');
        $mail = $this->postausgang()[0];
        $this->gleich('erika@beispiel.example', $mail['an']);
        preg_match('/#t=([A-Za-z0-9_-]{43})/', $mail['text'], $t);
        $this->status(200, $this->post('/api/status', ['token' => $t[1]]), 'neuer Link');
        $this->gleich(2, count($this->postausgang()), 'keine Mail an die fremde Adresse');
    }
}
