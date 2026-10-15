<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Tests\Fall;

final class WiderrufTest extends Fall
{
    public function testEingangsbestaetigungMitInhaltUndZeit(): void
    {
        $b = $this->buchen();
        $a = $this->post('/api/widerruf', ['name' => 'Erika Mustermann', 'nummer' => strtolower($b['daten']['nummer']), 'email' => 'erika@beispiel.example', 'grund' => 'Hier klicken: https://werbung.example']);
        $this->status(201, $a);
        $d = $this->json($a);
        $this->gleich(1, preg_match('/^W-[0-9A-F]{8}$/', $d['kennung']));
        $mail = $this->postausgang()[0];
        $this->gleich('widerruf', $mail['art']);
        $this->enthaelt('13.10.2026, 10:00 Uhr', $mail['text'], 'Datum und Uhrzeit des Eingangs');
        $this->enthaelt('widerrufe ich', $mail['text'], 'Inhalt');
        $this->enthaelt($b['daten']['nummer'], $mail['text']);
        $this->enthaeltNicht('werbung.example', $mail['text'], 'Grund wird nicht zurückgeschickt');
        $this->gleich(1, (int) $this->app()->db->wert('SELECT COUNT(*) FROM widerrufe WHERE auftrag_id IS NOT NULL'), 'dem Auftrag zugeordnet');
    }

    public function testAuchOhnePassendenAuftragAngenommen(): void
    {
        $a = $this->post('/api/widerruf', ['name' => 'Erika Mustermann', 'nummer' => 'RF-AAAA-BBBB', 'email' => 'erika@beispiel.example']);
        $this->status(201, $a, 'Wirksamkeit prüft die Werkstatt, angenommen wird immer');
        $this->gleich(1, (int) $this->app()->db->wert('SELECT COUNT(*) FROM widerrufe WHERE auftrag_id IS NULL'));
    }

    public function testNurDreiPflichtfelder(): void
    {
        $a = $this->post('/api/widerruf', ['name' => '', 'nummer' => '', 'email' => '']);
        $this->status(422, $a);
        $this->gleich(['name', 'nummer', 'email'], array_keys($this->json($a)['felder']));
        $this->status(400, $this->post('/api/widerruf', ['name' => 'A B', 'nummer' => 'RF-AAAA-BBBB', 'email' => 'a@b.example', 'iban' => 'DE00']));
    }
}
