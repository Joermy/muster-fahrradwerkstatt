<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Binaer;
use Radhaus\Daten\Datenbank;
use Radhaus\Konfiguration;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Uhr;
use RuntimeException;

/**
 * Ausgehende Mails, nur Klartext. Jede Mail liegt verschlüsselt im Postausgang, damit
 * sich Versand und Eingangsbestätigungen nachweisen lassen; nach 30 Tagen wird sie gelöscht.
 */
final class Post
{
    public function __construct(
        private Datenbank $db,
        private Tresor $tresor,
        private Uhr $uhr,
        private Konfiguration $konfig,
    ) {
    }

    public function senden(string $an, string $betreff, string $text, string $art): int
    {
        if (preg_match('/[\r\n]/', $an . $betreff) === 1 || filter_var($an, FILTER_VALIDATE_EMAIL) === false) {
            throw new RuntimeException('Ungültige Empfängerangaben.');
        }
        $this->db->ausfuehren(
            'INSERT INTO post (an_vs, betreff, text_vs, art, erstellt) VALUES (?, ?, ?, ?, ?)',
            [new Binaer($this->tresor->verschluesseln($an, 'post:an')), $betreff, new Binaer($this->tresor->verschluesseln($text, 'post:text')), $art, $this->uhr->iso()],
        );
        $id = $this->db->letzteId();

        if ($this->konfig->text('POST_MODUS') === 'mail') {
            $absender = $this->konfig->text('POST_ABSENDER');
            $kopf = [
                'From' => 'Radhaus Fuhse <' . $absender . '>',
                'Reply-To' => $absender,
                'MIME-Version' => '1.0',
                'Content-Type' => 'text/plain; charset=UTF-8',
                'Content-Transfer-Encoding' => '8bit',
                'Auto-Submitted' => 'auto-generated',
            ];
            $ok = mail($an, mb_encode_mimeheader($betreff, 'UTF-8', 'Q'), str_replace("\n", "\r\n", $text), $kopf, '-f' . $absender);
            $this->db->ausfuehren('UPDATE post SET versendet = ?, fehler = ? WHERE id = ?', [$ok ? $this->uhr->iso() : null, $ok ? null : 'mail() fehlgeschlagen', $id]);
        } else {
            $this->db->ausfuehren('UPDATE post SET versendet = ? WHERE id = ?', [$this->uhr->iso(), $id]);
        }
        return $id;
    }

    /** @return list<array{id: int, an: string, betreff: string, text: string, art: string, erstellt: string}> */
    public function ausgang(int $anzahl = 50): array
    {
        $aus = [];
        foreach ($this->db->zeilen('SELECT id, an_vs, betreff, text_vs, art, erstellt FROM post ORDER BY id DESC LIMIT ?', [$anzahl]) as $z) {
            $aus[] = [
                'id' => (int) $z['id'],
                'an' => $this->tresor->entschluesseln((string) $z['an_vs'], 'post:an'),
                'betreff' => (string) $z['betreff'],
                'text' => $this->tresor->entschluesseln((string) $z['text_vs'], 'post:text'),
                'art' => (string) $z['art'],
                'erstellt' => (string) $z['erstellt'],
            ];
        }
        return $aus;
    }
}
