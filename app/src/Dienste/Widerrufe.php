<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Binaer;
use Radhaus\Daten\Datenbank;
use Radhaus\Konfiguration;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Uhr;

/**
 * Online-Widerrufsfunktion nach § 356a BGB. Jede Erklärung wird angenommen und sofort
 * mit Inhalt, Datum und Uhrzeit bestätigt – ob sie wirksam und rechtzeitig ist, prüft
 * danach die Werkstatt. Pflichtangaben sind nur Name, Auftragsnummer und E-Mail für die
 * Bestätigung; ein Grund ist freiwillig.
 */
final class Widerrufe
{
    public function __construct(
        private Datenbank $db,
        private Tresor $tresor,
        private Uhr $uhr,
        private Post $post,
        private Protokoll $protokoll,
        private Konfiguration $konfig,
    ) {
    }

    /** @return array{kennung: string, eingang: string} */
    public function einreichen(string $name, string $nummer, string $email, ?string $grund): array
    {
        $eingang = $this->uhr->iso();
        $kennung = 'W-' . strtoupper(substr(bin2hex(random_bytes(5)), 0, 8));
        $auftragId = $this->db->wert(
            'SELECT id FROM auftraege WHERE nummer = ? AND email_index = ?',
            [$nummer, new Binaer($this->tresor->index($email))],
        );
        $this->db->ausfuehren(
            'INSERT INTO widerrufe (eingang, auftragsnummer, name_vs, email_vs, grund_vs, auftrag_id, oeffentliche_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                $eingang,
                $nummer,
                new Binaer($this->tresor->verschluesseln($name, "widerruf:$kennung:name")),
                new Binaer($this->tresor->verschluesseln($email, "widerruf:$kennung:email")),
                Binaer::oder($this->tresor->verschluesselnOptional($grund, "widerruf:$kennung:grund")),
                $auftragId === null ? null : (int) $auftragId,
                $kennung,
            ],
        );
        $this->protokoll->eintragen(null, 'widerruf_eingegangen', $nummer, $kennung);

        $url = $this->konfig->url();
        $text = "Guten Tag,\n\nwir bestätigen den Eingang Ihres Widerrufs.\n\n"
            . "Eingang: " . Texte::zeit($eingang) . "\nVorgang: {$kennung}\n\n"
            . "Inhalt Ihrer Erklärung:\n"
            . "Hiermit widerrufe ich den über die Website geschlossenen Vertrag über Zusatzarbeiten zum Auftrag {$nummer}.\n"
            . "Name: {$name}\nE-Mail für diese Bestätigung: {$email}\n"
            // Der freiwillige Grund wird nicht zurückgeschickt, sonst ließe sich das Formular für Werbung an fremde Adressen nutzen.
            . ($grund !== null ? "Einen freiwilligen Grund haben Sie angegeben; er liegt uns vor.\n" : '')
            . "\nDiese Mail bestätigt den Eingang. Wir prüfen den Widerruf und melden uns.\n\n"
            . Texte::fusszeile($url);
        $this->post->senden($email, "Eingangsbestätigung Ihres Widerrufs {$kennung}", $text, 'widerruf');
        return ['kennung' => $kennung, 'eingang' => $eingang];
    }

    /** @return list<array<string, mixed>> */
    public function liste(): array
    {
        return array_map(function (array $w): array {
            $k = (string) $w['oeffentliche_id'];
            return [
                'id' => (int) $w['id'],
                'kennung' => $k,
                'eingang' => $w['eingang'],
                'auftragsnummer' => $w['auftragsnummer'],
                'zugeordnet' => $w['auftrag_id'] !== null,
                'auftrag_id' => $w['auftrag_id'],
                'name' => $this->tresor->entschluesseln((string) $w['name_vs'], "widerruf:$k:name"),
                'email' => $this->tresor->entschluesseln((string) $w['email_vs'], "widerruf:$k:email"),
                'grund' => $this->tresor->entschluesselnOptional($w['grund_vs'], "widerruf:$k:grund"),
                'bearbeitet' => $w['bearbeitet'],
            ];
        }, $this->db->zeilen('SELECT * FROM widerrufe ORDER BY id DESC LIMIT 200'));
    }

    public function erledigt(int $id, int $benutzerId): void
    {
        $this->db->ausfuehren('UPDATE widerrufe SET bearbeitet = ? WHERE id = ? AND bearbeitet IS NULL', [$this->uhr->iso(), $id]);
        $this->protokoll->eintragen($benutzerId, 'widerruf_bearbeitet', (string) $id);
    }

    /** Nachweise nach drei Jahren löschen (regelmäßige Verjährung). */
    public function fristenAnwenden(): int
    {
        $grenze = $this->uhr->jetzt()->modify('-36 month')->format('Y-m-d\TH:i:sP');
        return $this->db->ausfuehren('DELETE FROM widerrufe WHERE eingang < ?', [$grenze])->rowCount();
    }
}
