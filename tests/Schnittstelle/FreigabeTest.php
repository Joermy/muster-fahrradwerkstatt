<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Tests\Fall;

final class FreigabeTest extends Fall
{
    /** @return array{token: string, id: int, angebot: int} */
    private function radInArbeitMitAngebot(): array
    {
        $b = $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        foreach (['bestaetigt', 'angenommen', 'in_arbeit'] as $s) {
            $this->status(200, $this->post("/api/verwaltung/auftraege/$id/status", ['status' => $s]), $s);
        }
        $d = $this->json($this->post("/api/verwaltung/auftraege/$id/angebot", ['positionen' => [
            ['text' => 'Bremsbeläge (Material)', 'cent' => 2490],
            ['text' => 'Beläge wechseln', 'cent' => 1900],
        ]]));
        $this->gleich('wartet_auf_freigabe', $d['status']);
        return ['token' => $b['daten']['token'], 'id' => $id, 'angebot' => (int) $d['angebote'][0]['id']];
    }

    public function testAnnehmenMitVertragsbestaetigung(): void
    {
        $f = $this->radInArbeitMitAngebot();
        $this->csrf = '';
        $s = $this->json($this->post('/api/status', ['token' => $f['token']]));
        $this->gleich(4390, $s['angebote'][0]['summe_cent']);
        $d = $this->json($this->post('/api/status/freigabe', ['token' => $f['token'], 'angebot' => $f['angebot'], 'annehmen' => true, 'vorzeitig' => true]));
        $this->gleich('angenommen', $d['entscheidung']);
        $this->gleich('2026-10-27', $d['frist_bis']);
        $vertrag = array_values(array_filter($this->postausgang(), fn ($m) => $m['art'] === 'vertrag'))[0];
        $this->enthaelt('43,90 €', $vertrag['text']);
        $this->enthaelt('WIDERRUFSBELEHRUNG', $vertrag['text']);
        $this->enthaelt('MUSTER-WIDERRUFSFORMULAR', $vertrag['text']);
        $this->enthaelt('/widerruf/', $vertrag['text'], 'Hinweis auf Online-Widerruf');
        $this->enthaelt('ausdrücklich verlangt', $vertrag['text']);
        $s = $this->json($this->post('/api/status', ['token' => $f['token']]));
        $this->gleich(true, $s['angebote'][0]['widerrufbar']);
        $this->gleich('in_arbeit', $s['status']);
        $this->uhr->vorstellen('+15 day');
        $s = $this->json($this->post('/api/status', ['token' => $f['token']]));
        $this->gleich(false, $s['angebote'][0]['widerrufbar'], 'nach Fristende');
    }

    public function testOhneVorzeitigenBeginn(): void
    {
        $f = $this->radInArbeitMitAngebot();
        $this->csrf = '';
        $this->post('/api/status/freigabe', ['token' => $f['token'], 'angebot' => $f['angebot'], 'annehmen' => true, 'vorzeitig' => false]);
        $vertrag = array_values(array_filter($this->postausgang(), fn ($m) => $m['art'] === 'vertrag'))[0];
        $this->enthaelt('erst nach Ablauf der Frist', $vertrag['text']);
    }

    public function testNurEinmalEntscheiden(): void
    {
        $f = $this->radInArbeitMitAngebot();
        $this->csrf = '';
        $this->status(200, $this->post('/api/status/freigabe', ['token' => $f['token'], 'angebot' => $f['angebot'], 'annehmen' => false, 'vorzeitig' => false]));
        $this->status(409, $this->post('/api/status/freigabe', ['token' => $f['token'], 'angebot' => $f['angebot'], 'annehmen' => true, 'vorzeitig' => false]));
        $this->gleich(0, count(array_filter($this->postausgang(), fn ($m) => $m['art'] === 'vertrag')), 'kein Vertrag bei Ablehnung');
    }

    public function testFremdesAngebotNichtErreichbar(): void
    {
        $f = $this->radInArbeitMitAngebot();
        $this->csrf = '';
        $zweite = $this->buchen(['email' => 'zweite@beispiel.example']);
        $a = $this->post('/api/status/freigabe', ['token' => $zweite['daten']['token'], 'angebot' => $f['angebot'], 'annehmen' => true, 'vorzeitig' => true]);
        $this->status(404, $a, 'Angebot eines anderen Auftrags');
        $this->status(422, $this->post('/api/status/freigabe', ['token' => $f['token'], 'angebot' => '1', 'annehmen' => 'ja', 'vorzeitig' => false]), 'falsche Typen');
    }

    public function testAngebotNurInArbeit(): void
    {
        $this->buchen();
        $this->alsVerwaltung();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $this->status(409, $this->post("/api/verwaltung/auftraege/$id/angebot", ['positionen' => [['text' => 'Etwas', 'cent' => 100]]]));
        $this->status(422, $this->post("/api/verwaltung/auftraege/$id/angebot", ['positionen' => [['text' => 'Etwas', 'cent' => -5]]]));
    }
}
