<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Sicherheit\Totp;
use Radhaus\Tests\Fall;

final class VerwaltungTest extends Fall
{
    public function testOhneAnmeldungNichts(): void
    {
        foreach (['/api/verwaltung/uebersicht', '/api/verwaltung/auftraege', '/api/verwaltung/auftraege/1', '/api/verwaltung/protokoll', '/api/verwaltung/benutzer'] as $p) {
            $this->status(401, $this->get($p), $p);
        }
        $this->kekse['__Host-rh_sitzung'] = str_repeat('A', 43);
        $this->status(401, $this->get('/api/verwaltung/ich'), 'erfundene Sitzung');
    }

    public function testGleicheMeldungFuerUnbekanntUndFalsch(): void
    {
        $this->app()->zugang->benutzerAnlegen('mira', 'Mira Ohlendorf', 'inhaber', null, 'Kettenblatt-Speiche-42');
        $a = $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => 'falsch']);
        $b = $this->post('/api/verwaltung/anmelden', ['name' => 'niemand', 'passwort' => 'falsch']);
        $this->status(401, $a);
        $this->gleich($a->koerper, $b->koerper);
    }

    public function testSperreNachFuenfFehlversuchen(): void
    {
        $this->app()->zugang->benutzerAnlegen('mira', 'Mira Ohlendorf', 'inhaber', null, 'Kettenblatt-Speiche-42');
        for ($i = 0; $i < 5; $i++) {
            $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => "falsch$i"]);
        }
        $this->status(401, $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => 'Kettenblatt-Speiche-42']), 'gesperrt trotz richtigem Passwort');
        $this->uhr->vorstellen('+16 minutes');
        $this->status(200, $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => 'Kettenblatt-Speiche-42']), 'nach Ablauf');
    }

    public function testDrosselungJeAbsender(): void
    {
        for ($i = 0; $i < 20; $i++) {
            $this->post('/api/verwaltung/anmelden', ['name' => "n$i", 'passwort' => 'x']);
        }
        $this->status(429, $this->post('/api/verwaltung/anmelden', ['name' => 'n', 'passwort' => 'x']));
    }

    public function testErstanmeldungErzwingtPasswortUndZweiFaktor(): void
    {
        $start = $this->app()->zugang->benutzerAnlegen('mira', 'Mira Ohlendorf', 'inhaber', null);
        $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => $start['passwort']]);
        $ich = $this->json($this->get('/api/verwaltung/ich'));
        $this->gleich(true, $ich['passwort_wechseln']);
        $this->status(403, $this->get('/api/verwaltung/uebersicht'), 'vor der Einrichtung');
        $this->csrf = $ich['csrf'];
        $this->status(422, $this->post('/api/verwaltung/passwort', ['alt' => $start['passwort'], 'neu' => 'passwort1234']), 'schwaches Passwort');
    }

    public function testKeksIstGeschuetzt(): void
    {
        $this->app()->zugang->benutzerAnlegen('mira', 'Mira Ohlendorf', 'inhaber', null, 'Kettenblatt-Speiche-42');
        $a = $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => 'Kettenblatt-Speiche-42']);
        $keks = $a->kekse[0];
        foreach (['__Host-rh_sitzung=', 'Path=/', 'HttpOnly', 'SameSite=Strict', 'Secure'] as $teil) {
            $this->enthaelt($teil, $keks);
        }
        $this->enthaeltNicht('Domain=', $keks);
        $kennung = $this->kekse['__Host-rh_sitzung'];
        $this->gleich(0, (int) $this->app()->db->wert('SELECT COUNT(*) FROM sitzungen WHERE id_hash = ?', [$kennung]), 'nur der Hash liegt in der Datenbank');
    }

    public function testZweiFaktorAnmeldung(): void
    {
        $z = $this->alsVerwaltung();
        $this->status(200, $this->get('/api/verwaltung/uebersicht'));
        $this->post('/api/verwaltung/abmelden');
        $this->csrf = '';
        $this->status(401, $this->get('/api/verwaltung/uebersicht'), 'nach Abmelden');

        $a = $this->json($this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => $z['passwort']]));
        $this->gleich('passwort', $a['stufe']);
        $this->status(401, $this->get('/api/verwaltung/uebersicht'), 'nur Passwort reicht nicht');
        $this->status(401, $this->post('/api/verwaltung/code', ['code' => '000000']));

        $this->uhr->vorstellen('+60 seconds');
        $code = Totp::code($z['geheimnis'], Totp::aktuellerSchritt($this->uhr->zeitstempel()));
        $vorher = $this->kekse['__Host-rh_sitzung'];
        $this->status(200, $this->post('/api/verwaltung/code', ['code' => $code]));
        $this->wahr($this->kekse['__Host-rh_sitzung'] !== $vorher, 'neue Sitzungskennung nach dem zweiten Faktor');
        $this->status(200, $this->get('/api/verwaltung/uebersicht'));

        // Derselbe Code ein zweites Mal
        $this->post('/api/verwaltung/abmelden');
        $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => $z['passwort']]);
        $this->status(401, $this->post('/api/verwaltung/code', ['code' => $code]), 'Wiederholung');
    }

    public function testErsatzcodeNurEinmal(): void
    {
        $z = $this->alsVerwaltung();
        $this->post('/api/verwaltung/abmelden');
        $this->csrf = '';
        $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => $z['passwort']]);
        $this->status(200, $this->post('/api/verwaltung/code', ['code' => strtolower($z['ersatz'][0])]));
        $this->post('/api/verwaltung/abmelden');
        $this->post('/api/verwaltung/anmelden', ['name' => 'mira', 'passwort' => $z['passwort']]);
        $this->status(401, $this->post('/api/verwaltung/code', ['code' => $z['ersatz'][0]]));
    }

    public function testCsrf(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $echt = $this->csrf;
        $this->csrf = '';
        $this->status(403, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => 'bestaetigt']), 'ohne Token');
        $this->csrf = 'falsch';
        $this->status(403, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => 'bestaetigt']), 'falscher Token');
        $this->csrf = $echt;
        $this->status(200, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => 'bestaetigt']));
    }

    public function testLeerlaufBeendetSitzung(): void
    {
        $this->alsVerwaltung();
        $this->uhr->vorstellen('+31 minutes');
        $this->status(401, $this->get('/api/verwaltung/uebersicht'));
    }

    public function testRollen(): void
    {
        $this->alsVerwaltung('werkstatt', 'tom');
        $this->status(200, $this->get('/api/verwaltung/auftraege'));
        foreach (['/api/verwaltung/protokoll', '/api/verwaltung/benutzer', '/api/verwaltung/auftraege/1/auskunft'] as $p) {
            $this->status(403, $this->get($p), $p);
        }
        $this->status(403, $this->post('/api/verwaltung/kapazitaet', ['plan' => []]));
    }

    public function testUnerlaubterStatuswechsel(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $this->status(409, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => 'abgeschlossen']));
        $this->status(422, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => 'erfunden']));
        $this->status(404, $this->get('/api/verwaltung/auftraege/999'));
        $this->status(404, $this->get('/api/verwaltung/auftraege/0'));
        $this->status(404, $this->get('/api/verwaltung/auftraege/1%20OR%201=1'));
    }

    public function testDetailWirdProtokolliertOhnePersonendaten(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $d = $this->json($this->get("/api/verwaltung/auftraege/$id"));
        $this->gleich('erika@beispiel.example', $d['email']);
        $this->post("/api/verwaltung/auftraege/$id/notiz", ['text' => 'Kunde will Rückruf an 030 23125 400']);
        $roh = json_encode($this->app()->db->zeilen('SELECT * FROM protokoll'));
        $this->enthaelt('auftrag_angesehen', $roh);
        foreach (['Erika', 'erika@', '23125 400'] as $klar) {
            $this->enthaeltNicht($klar, $roh, 'Protokoll');
        }
    }

    public function testAnonymisierenNurMitBestaetigung(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $nummer = (string) $this->app()->db->wert('SELECT nummer FROM auftraege');
        $this->status(422, $this->post("/api/verwaltung/auftraege/$id/anonymisieren", ['bestaetigung' => 'ja']));
        $d = $this->json($this->post("/api/verwaltung/auftraege/$id/anonymisieren", ['bestaetigung' => $nummer]));
        $this->gleich(null, $d['name']);
        $this->wahr($d['anonymisiert'] !== null);
    }

    public function testKapazitaetPruefen(): void
    {
        $this->alsVerwaltung();
        $this->status(422, $this->post('/api/verwaltung/kapazitaet', ['plan' => ['1' => ['zeiten' => ['25:00'], 'plaetze' => 2]]]));
        $this->status(422, $this->post('/api/verwaltung/kapazitaet', ['plan' => ['8' => ['zeiten' => [], 'plaetze' => 2]]]));
        $d = $this->json($this->post('/api/verwaltung/kapazitaet', ['plan' => ['3' => ['zeiten' => ['09:00', '08:00', '09:00'], 'plaetze' => 1]], 'sperrtage' => [['datum' => '2026-10-21', 'grund' => 'Betriebsausflug']]]));
        $this->gleich(['08:00', '09:00'], $d['plan'][3]['zeiten']);
        $tag = array_values(array_filter($d['tage'], fn ($t) => $t['datum'] === '2026-10-21'))[0];
        $this->gleich('Betriebsausflug', $tag['grund']);
    }

    public function testUebersichtZeigtDieNaechstenTage(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $u = $this->json($this->get('/api/verwaltung/uebersicht'));
        $this->gleich(1, count($u['demnaechst']), 'gebuchter Termin in den nächsten Tagen');
        $this->gleich(1, $u['zahlen']['angefragt']);
    }

    public function testPostausgangNurInEntwicklung(): void
    {
        $this->alsVerwaltung();
        $this->status(404, $this->get('/api/verwaltung/post'));
    }
}
