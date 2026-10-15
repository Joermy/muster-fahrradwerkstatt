<?php

declare(strict_types=1);

namespace Radhaus\Tests\Schnittstelle;

use Radhaus\Dienste\Einwilligungen;
use Radhaus\Tests\Fall;

final class FristenTest extends Fall
{
    public function testAbgesagtNach30Tagen(): void
    {
        $b = $this->buchen();
        $this->post('/api/status/absagen', ['token' => $b['daten']['token']]);
        $this->uhr->vorstellen('+20 day');
        $this->app()->aufgaben->ausfuehren(true);
        $this->wahr($this->app()->db->wert('SELECT name_vs FROM auftraege') !== null, 'noch nicht');
        $this->uhr->vorstellen('+15 day');
        $this->app()->aufgaben->ausfuehren(true);
        $this->gleich(null, $this->app()->db->wert('SELECT name_vs FROM auftraege'), 'nach 30 Tagen');
    }

    public function testAbgeschlossenNach24Monaten(): void
    {
        $this->buchen();
        $id = (int) $this->app()->db->wert('SELECT id FROM auftraege');
        $this->app()->db->ausfuehren("UPDATE auftraege SET status = 'abgeschlossen', abgeschlossen = ? WHERE id = ?", [$this->uhr->iso(), $id]);
        $this->uhr->vorstellen('+23 month');
        $this->app()->aufgaben->ausfuehren(true);
        $this->wahr($this->app()->db->wert('SELECT email_vs FROM auftraege') !== null, 'innerhalb der Gewährleistung');
        $this->uhr->vorstellen('+2 month');
        $this->app()->aufgaben->ausfuehren(true);
        $this->gleich(null, $this->app()->db->wert('SELECT email_vs FROM auftraege'));
        $this->gleich('bremsen', $this->app()->db->wert('SELECT leistung FROM auftraege'), 'Leistung bleibt');
    }

    public function testEinwilligungsnachweisUndPostLoeschen(): void
    {
        $id = '2f1c9a3e-8b7d-4c6a-9e5f-1a2b3c4d5e6f';
        $r = $this->post('/api/einwilligung', ['id' => $id, 'fassung' => Einwilligungen::FASSUNG, 'medien' => true]);
        $this->status(200, $r);
        $this->gleich(1, (int) $this->app()->db->wert('SELECT medien FROM einwilligungen WHERE id = ?', [$id]), 'Nachweis gespeichert');
        // Felder, die es nicht gibt, werden abgelehnt
        $r = $this->post('/api/einwilligung', ['id' => $id, 'fassung' => Einwilligungen::FASSUNG, 'medien' => true, 'werbung' => true]);
        $this->status(400, $r, 'unbekanntes Feld');
        $this->buchen();
        $this->uhr->vorstellen('+31 day');
        $this->app()->aufgaben->ausfuehren(true);
        $this->gleich(0, (int) $this->app()->db->wert('SELECT COUNT(*) FROM post'), 'Post nach 30 Tagen');
        $this->gleich(1, (int) $this->app()->db->wert('SELECT COUNT(*) FROM einwilligungen'), 'Nachweis bleibt');
        $this->uhr->vorstellen('+36 month');
        $this->app()->aufgaben->ausfuehren(true);
        $this->gleich(0, (int) $this->app()->db->wert('SELECT COUNT(*) FROM einwilligungen'), 'Nachweis nach drei Jahren gelöscht');
    }

    public function testAufgabenNurEinmalAmTag(): void
    {
        $this->gleich(true, $this->app()->aufgaben->faellig());
        $this->app()->aufgaben->ausfuehren();
        $this->gleich(false, $this->app()->aufgaben->faellig());
        $this->gleich([], $this->app()->aufgaben->ausfuehren());
        $this->uhr->vorstellen('+1 day');
        $this->gleich(true, $this->app()->aufgaben->faellig());
    }
}
