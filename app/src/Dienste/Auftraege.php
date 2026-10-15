<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Binaer;
use Radhaus\Daten\Datenbank;
use Radhaus\Http\HttpFehler;
use Radhaus\Konfiguration;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Uhr;

/**
 * Terminanfragen und Aufträge. Kunden haben kein Konto: Zugang zum eigenen Auftrag gibt
 * ein zufälliger Link (256 Bit), von dem nur der SHA-256-Wert gespeichert ist.
 */
final class Auftraege
{
    public const STATUS = [
        'angefragt' => 'Anfrage eingegangen',
        'bestaetigt' => 'Termin bestätigt',
        'angenommen' => 'Rad angenommen',
        'in_arbeit' => 'In Arbeit',
        'wartet_auf_freigabe' => 'Wartet auf Ihre Freigabe',
        'abholbereit' => 'Abholbereit',
        'abgeschlossen' => 'Abgeholt',
        'storniert' => 'Abgesagt',
        'nicht_erschienen' => 'Nicht erschienen',
    ];

    /** Erlaubte Wechsel durch die Werkstatt. */
    public const UEBERGAENGE = [
        'angefragt' => ['bestaetigt', 'storniert'],
        'bestaetigt' => ['angenommen', 'storniert', 'nicht_erschienen'],
        'angenommen' => ['in_arbeit', 'abholbereit'],
        'in_arbeit' => ['abholbereit'],
        'wartet_auf_freigabe' => ['in_arbeit'],
        'abholbereit' => ['abgeschlossen', 'in_arbeit'],
        'abgeschlossen' => [],
        'storniert' => [],
        'nicht_erschienen' => [],
    ];

    /** Solange das Rad in der Werkstatt ist, lassen sich die Daten nicht sofort löschen. */
    public const IN_DER_WERKSTATT = ['angenommen', 'in_arbeit', 'wartet_auf_freigabe', 'abholbereit'];

    public const WIDERRUFSFRIST_TAGE = 14;

    private const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

    public function __construct(
        private Datenbank $db,
        private Tresor $tresor,
        private Uhr $uhr,
        private Kalender $kalender,
        private Katalog $katalog,
        private Post $post,
        private Protokoll $protokoll,
        private Konfiguration $konfig,
    ) {
    }

    /**
     * @param array{leistung: string, rad: string, datum: string, zeit: string, name: string, email: string, telefon: ?string, nachricht: ?string} $e
     * @return array{nummer: string, token: string}
     */
    public function anfragen(array $e, string $quelle = 'website'): array
    {
        $token = Tresor::zufallsToken();
        $nummer = $this->db->transaktion(function () use ($e, $token, $quelle): string {
            if (!$this->kalender->platzFrei($e['datum'], $e['zeit'])) {
                throw new HttpFehler(409, 'termin_belegt', 'Dieser Termin ist gerade vergeben worden. Bitte wählen Sie einen anderen.');
            }
            do {
                $nummer = self::neueNummer();
            } while ($this->db->wert('SELECT 1 FROM auftraege WHERE nummer = ?', [$nummer]) !== null);

            $jetzt = $this->uhr->iso();
            $this->db->ausfuehren(
                'INSERT INTO auftraege (nummer, token_hash, leistung, rad, termin_datum, termin_zeit, status, name_vs, email_vs, email_index, telefon_vs, nachricht_vs, quelle, erstellt, geaendert)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [
                    $nummer,
                    new Binaer(Tresor::tokenHash($token)),
                    $e['leistung'],
                    $e['rad'],
                    $e['datum'],
                    $e['zeit'],
                    'angefragt',
                    new Binaer($this->tresor->verschluesseln($e['name'], "auftrag:$nummer:name")),
                    new Binaer($this->tresor->verschluesseln($e['email'], "auftrag:$nummer:email")),
                    new Binaer($this->tresor->index($e['email'])),
                    Binaer::oder($this->tresor->verschluesselnOptional($e['telefon'], "auftrag:$nummer:telefon")),
                    Binaer::oder($this->tresor->verschluesselnOptional($e['nachricht'], "auftrag:$nummer:nachricht")),
                    $quelle,
                    $jetzt,
                    $jetzt,
                ],
            );
            $id = $this->db->letzteId();
            $this->verlaufEintragen($id, $nummer, 'angefragt', null);
            return $nummer;
        });

        $this->post->senden($e['email'], "Ihre Terminanfrage {$nummer}", $this->mailAnfrage($nummer, $token, $e), 'anfrage');
        return ['nummer' => $nummer, 'token' => $token];
    }

    /** @return array<string, mixed>|null */
    public function perToken(string $token): ?array
    {
        if (preg_match('/^[A-Za-z0-9_-]{43}$/', $token) !== 1) {
            return null;
        }
        return $this->db->zeile('SELECT * FROM auftraege WHERE token_hash = ? AND anonymisiert IS NULL', [new Binaer(Tresor::tokenHash($token))]);
    }

    /** @return array<string, mixed> */
    public function perTokenOderFehler(string $token): array
    {
        $a = $this->perToken($token);
        if ($a === null) {
            throw new HttpFehler(404, 'unbekannter_link', 'Dieser Link ist ungültig oder abgelaufen.');
        }
        return $a;
    }

    /** @return array<string, mixed> */
    public function perId(int $id): array
    {
        $a = $this->db->zeile('SELECT * FROM auftraege WHERE id = ?', [$id]);
        if ($a === null) {
            throw new HttpFehler(404, 'nicht_gefunden', 'Auftrag nicht gefunden.');
        }
        return $a;
    }

    /**
     * Was Kunden auf der Statusseite sehen. Die E-Mail-Adresse erscheint gekürzt, damit ein
     * weitergeleiteter Link nicht die ganze Adresse verrät.
     *
     * @param array<string, mixed> $a
     * @return array<string, mixed>
     */
    public function kundenansicht(array $a): array
    {
        $nummer = (string) $a['nummer'];
        $email = $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email");
        $name = $this->tresor->entschluesseln((string) $a['name_vs'], "auftrag:$nummer:name");
        $status = (string) $a['status'];
        return [
            'nummer' => $nummer,
            'status' => $status,
            'status_text' => self::STATUS[$status] ?? $status,
            'leistung' => $this->katalog->titel('leistung', (string) $a['leistung']),
            'rad' => $this->katalog->titel('rad', (string) $a['rad']),
            'termin' => ['datum' => $a['termin_datum'], 'zeit' => $a['termin_zeit']],
            'vorname' => explode(' ', $name)[0],
            'email' => self::emailKuerzen($email),
            'verlauf' => $this->verlauf((int) $a['id'], $nummer),
            'angebote' => $this->angebote((int) $a['id']),
            'absagen_moeglich' => in_array($status, ['angefragt', 'bestaetigt'], true),
            'loeschen_sofort' => !in_array($status, self::IN_DER_WERKSTATT, true),
            'erstellt' => $a['erstellt'],
        ];
    }

    public function absagen(string $token): void
    {
        $a = $this->perTokenOderFehler($token);
        if (!in_array($a['status'], ['angefragt', 'bestaetigt'], true)) {
            throw new HttpFehler(409, 'nicht_absagbar', 'Ihr Rad ist schon bei uns. Bitte rufen Sie uns an.');
        }
        $this->statusAendern((int) $a['id'], (string) $a['nummer'], 'storniert', 'Vom Kunden online abgesagt.');
        $this->protokoll->eintragen(null, 'kunde_abgesagt', (string) $a['nummer']);
    }

    /**
     * @param list<array{text: string, cent: int}> $positionen
     */
    public function angebotErstellen(int $auftragId, array $positionen, int $benutzerId): int
    {
        $a = $this->perId($auftragId);
        if (!in_array($a['status'], ['angenommen', 'in_arbeit'], true)) {
            throw new HttpFehler(409, 'falscher_status', 'Ein Kostenvoranschlag ist nur möglich, solange das Rad in Arbeit ist.');
        }
        if ($this->db->wert('SELECT 1 FROM angebote WHERE auftrag_id = ? AND entscheidung IS NULL', [$auftragId]) !== null) {
            throw new HttpFehler(409, 'offenes_angebot', 'Es gibt bereits einen offenen Kostenvoranschlag.');
        }
        $summe = array_sum(array_column($positionen, 'cent'));
        $nummer = (string) $a['nummer'];
        $id = $this->db->transaktion(function () use ($auftragId, $positionen, $summe, $nummer): int {
            $this->db->ausfuehren(
                'INSERT INTO angebote (auftrag_id, positionen, summe_cent, erstellt) VALUES (?, ?, ?, ?)',
                [$auftragId, json_encode($positionen, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR), $summe, $this->uhr->iso()],
            );
            $id = $this->db->letzteId();
            $this->statusAendern($auftragId, $nummer, 'wartet_auf_freigabe', null);
            return $id;
        });
        $this->protokoll->eintragen($benutzerId, 'angebot_erstellt', $nummer, Texte::euro($summe));
        $this->post->senden(
            $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email"),
            "Kostenvoranschlag zu {$nummer}",
            $this->mailAngebot($a, $positionen, $summe),
            'angebot',
        );
        return $id;
    }

    /** @return array{entscheidung: string, frist_bis: ?string} */
    public function angebotEntscheiden(string $token, int $angebotId, bool $annehmen, bool $vorzeitigerBeginn): array
    {
        $a = $this->perTokenOderFehler($token);
        $nummer = (string) $a['nummer'];
        $angebot = $this->db->zeile('SELECT * FROM angebote WHERE id = ? AND auftrag_id = ?', [$angebotId, $a['id']]);
        if ($angebot === null) {
            throw new HttpFehler(404, 'nicht_gefunden', 'Kostenvoranschlag nicht gefunden.');
        }
        if ($angebot['entscheidung'] !== null) {
            throw new HttpFehler(409, 'schon_entschieden', 'Über diesen Kostenvoranschlag ist schon entschieden.');
        }
        $jetzt = $this->uhr->iso();
        $entscheidung = $annehmen ? 'angenommen' : 'abgelehnt';
        $pruefsumme = hash('sha256', $nummer . '|' . $angebot['positionen'] . '|' . $angebot['summe_cent'] . '|' . $jetzt . '|' . ($vorzeitigerBeginn ? '1' : '0') . '|' . Texte::BELEHRUNG_FASSUNG);
        $this->db->transaktion(function () use ($a, $angebotId, $entscheidung, $jetzt, $vorzeitigerBeginn, $annehmen, $pruefsumme, $nummer): void {
            $this->db->ausfuehren(
                'UPDATE angebote SET entscheidung = ?, entschieden = ?, vorzeitiger_beginn = ?, belehrung_fassung = ?, vertrag_pruefsumme = ? WHERE id = ? AND entscheidung IS NULL',
                [$entscheidung, $jetzt, $annehmen && $vorzeitigerBeginn, $annehmen ? Texte::BELEHRUNG_FASSUNG : null, $annehmen ? $pruefsumme : null, $angebotId],
            );
            $this->statusAendern((int) $a['id'], $nummer, 'in_arbeit', $annehmen ? 'Zusatzarbeiten freigegeben.' : 'Zusatzarbeiten abgelehnt.');
        });
        $this->protokoll->eintragen(null, $annehmen ? 'angebot_angenommen' : 'angebot_abgelehnt', $nummer);

        $fristBis = null;
        if ($annehmen) {
            $fristBis = $this->uhr->jetzt()->modify('+' . self::WIDERRUFSFRIST_TAGE . ' day')->format('Y-m-d');
            $positionen = json_decode((string) $angebot['positionen'], true);
            $this->post->senden(
                $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email"),
                "Vertragsbestätigung Zusatzarbeiten {$nummer}",
                $this->mailVertrag($a, is_array($positionen) ? $positionen : [], (int) $angebot['summe_cent'], $jetzt, $vorzeitigerBeginn, $pruefsumme),
                'vertrag',
            );
        }
        return ['entscheidung' => $entscheidung, 'frist_bis' => $fristBis];
    }

    /**
     * Alle gespeicherten Daten zum Auftrag (Art. 15 und 20 DSGVO).
     *
     * @param array<string, mixed> $a
     * @return array<string, mixed>
     */
    public function auskunft(array $a): array
    {
        $nummer = (string) $a['nummer'];
        $id = (int) $a['id'];
        return [
            'erstellt' => $this->uhr->iso(),
            'verantwortlich' => Texte::anschrift(),
            'auftrag' => [
                'nummer' => $nummer,
                'leistung' => $this->katalog->titel('leistung', (string) $a['leistung']),
                'rad' => $this->katalog->titel('rad', (string) $a['rad']),
                'termin' => $a['termin_datum'] . ' ' . $a['termin_zeit'],
                'status' => self::STATUS[(string) $a['status']] ?? $a['status'],
                'angefragt_am' => $a['erstellt'],
                'zuletzt_geaendert' => $a['geaendert'],
                'abgeschlossen_am' => $a['abgeschlossen'],
            ],
            'kontaktdaten' => [
                'name' => $this->tresor->entschluesseln((string) $a['name_vs'], "auftrag:$nummer:name"),
                'email' => $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email"),
                'telefon' => $this->tresor->entschluesselnOptional($a['telefon_vs'], "auftrag:$nummer:telefon"),
                'nachricht' => $this->tresor->entschluesselnOptional($a['nachricht_vs'], "auftrag:$nummer:nachricht"),
            ],
            'verlauf' => $this->verlauf($id, $nummer),
            'kostenvoranschlaege' => $this->angebote($id),
            'interne_notizen' => array_map(
                fn (array $n): array => ['zeit' => $n['zeit'], 'text' => $this->tresor->entschluesseln((string) $n['text_vs'], "notiz:$nummer")],
                $this->db->zeilen('SELECT zeit, text_vs FROM notizen WHERE auftrag_id = ? ORDER BY id', [$id]),
            ),
            'speicherdauer' => $this->loeschdatumText($a),
        ];
    }

    /** @return array{geloescht: bool, meldung: string} */
    public function loeschenDurchKunde(string $token): array
    {
        $a = $this->perTokenOderFehler($token);
        $nummer = (string) $a['nummer'];
        if (in_array($a['status'], self::IN_DER_WERKSTATT, true)) {
            throw new HttpFehler(409, 'rad_in_werkstatt', 'Ihr Rad ist gerade bei uns. Solange wir es haben, brauchen wir Ihre Kontaktdaten. Wir löschen sie nach der gesetzlichen Frist automatisch; vorher können Sie uns jederzeit anrufen.');
        }
        $offeneVertraege = (int) $this->db->wert("SELECT COUNT(*) FROM angebote WHERE auftrag_id = ? AND entscheidung = 'angenommen'", [$a['id']]);
        if ($a['status'] === 'abgeschlossen' && $offeneVertraege > 0) {
            // Bei ausgeführten Arbeiten gilt die Gewährleistungsfrist; dann wird nur der Link entwertet.
            $this->db->ausfuehren('UPDATE auftraege SET token_hash = ?, geaendert = ? WHERE id = ?', [new Binaer(random_bytes(32)), $this->uhr->iso(), $a['id']]);
            $this->protokoll->eintragen(null, 'kunde_loeschung_eingeschraenkt', $nummer);
            return ['geloescht' => false, 'meldung' => 'Für ausgeführte Arbeiten müssen wir die Angaben bis zum Ende der Gewährleistung aufbewahren. Ihr Link ist jetzt gesperrt, die Daten werden danach automatisch gelöscht.'];
        }
        $this->anonymisieren((int) $a['id'], null, 'kunde');
        return ['geloescht' => true, 'meldung' => 'Ihre Kontaktdaten und Nachrichten sind gelöscht.'];
    }

    /** Neuer Link per Mail. Antwort ist immer gleich, damit sich nicht prüfen lässt, ob es eine Nummer gibt. */
    public function linkErneuern(string $nummer, string $email): void
    {
        $a = $this->db->zeile('SELECT * FROM auftraege WHERE nummer = ? AND email_index = ? AND anonymisiert IS NULL', [$nummer, new Binaer($this->tresor->index($email))]);
        if ($a === null) {
            return;
        }
        $token = Tresor::zufallsToken();
        $this->db->ausfuehren('UPDATE auftraege SET token_hash = ?, geaendert = ? WHERE id = ?', [new Binaer(Tresor::tokenHash($token)), $this->uhr->iso(), $a['id']]);
        $this->protokoll->eintragen(null, 'link_erneuert', $nummer);
        $url = $this->konfig->url();
        $this->post->senden(
            $email,
            "Neuer Link zu {$nummer}",
            "Guten Tag,\n\nhier ist der neue Link zu Ihrem Auftrag {$nummer}. Der alte Link funktioniert nicht mehr.\n\n{$url}/status/#t={$token}\n\nWenn Sie keinen neuen Link angefordert haben, können Sie diese Mail ignorieren.\n\n" . Texte::fusszeile($url),
            'link',
        );
    }

    public function statusSetzen(int $id, string $neu, ?string $hinweis, int $benutzerId): void
    {
        $a = $this->perId($id);
        $alt = (string) $a['status'];
        if (!in_array($neu, self::UEBERGAENGE[$alt] ?? [], true)) {
            throw new HttpFehler(409, 'falscher_wechsel', 'Dieser Statuswechsel ist nicht möglich.');
        }
        if ($a['anonymisiert'] !== null) {
            throw new HttpFehler(409, 'anonymisiert', 'Dieser Auftrag ist bereits anonymisiert.');
        }
        $nummer = (string) $a['nummer'];
        $this->statusAendern($id, $nummer, $neu, $hinweis);
        $this->protokoll->eintragen($benutzerId, 'status', $nummer, "$alt -> $neu");

        $email = $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email");
        $url = $this->konfig->url();
        $text = match ($neu) {
            'bestaetigt' => "Ihr Termin am " . Texte::datum((string) $a['termin_datum']) . " um {$a['termin_zeit']} Uhr ist bestätigt.",
            'abholbereit' => 'Ihr Rad ist fertig und kann abgeholt werden.',
            'storniert' => 'Ihr Termin ist leider abgesagt.',
            default => null,
        };
        if ($text !== null) {
            $this->post->senden($email, self::STATUS[$neu] . " – {$nummer}", "Guten Tag,\n\n{$text}" . ($hinweis ? "\n\nHinweis der Werkstatt: {$hinweis}" : '') . "\n\nDen aktuellen Stand sehen Sie über den Link aus Ihrer ersten Mail.\n\n" . Texte::fusszeile($url), 'status');
        }
    }

    public function notizHinzufuegen(int $id, string $text, int $benutzerId): void
    {
        $a = $this->perId($id);
        $nummer = (string) $a['nummer'];
        $this->db->ausfuehren('INSERT INTO notizen (auftrag_id, benutzer_id, text_vs, zeit) VALUES (?, ?, ?, ?)', [
            $id, $benutzerId, new Binaer($this->tresor->verschluesseln($text, "notiz:$nummer")), $this->uhr->iso(),
        ]);
        $this->protokoll->eintragen($benutzerId, 'notiz', $nummer);
    }

    /**
     * @param array{status?: ?string, suche?: ?string, offen?: bool} $filter
     * @return list<array<string, mixed>>
     */
    public function liste(array $filter = []): array
    {
        $bedingungen = ['1 = 1'];
        $werte = [];
        if (!empty($filter['status'])) {
            $bedingungen[] = 'status = ?';
            $werte[] = $filter['status'];
        }
        if (!empty($filter['offen'])) {
            $bedingungen[] = "status NOT IN ('abgeschlossen', 'storniert', 'nicht_erschienen')";
        }
        if (!empty($filter['suche']) && preg_match('/^RF-[A-Z0-9-]{1,9}$/i', (string) $filter['suche']) === 1) {
            $bedingungen[] = 'nummer LIKE ?';
            $werte[] = strtoupper((string) $filter['suche']) . '%';
        }
        $zeilen = $this->db->zeilen(
            'SELECT id, nummer, leistung, rad, termin_datum, termin_zeit, status, name_vs, erstellt, geaendert, anonymisiert,
                    (SELECT COUNT(*) FROM angebote g WHERE g.auftrag_id = auftraege.id AND g.entscheidung IS NULL) AS offene_angebote
             FROM auftraege WHERE ' . implode(' AND ', $bedingungen) . ' ORDER BY termin_datum DESC, termin_zeit DESC LIMIT 300',
            $werte,
        );
        return array_map(fn (array $z): array => [
            'id' => (int) $z['id'],
            'nummer' => $z['nummer'],
            'leistung' => $z['leistung'],
            'leistung_text' => $this->katalog->titel('leistung', (string) $z['leistung']),
            'rad' => $z['rad'],
            'termin_datum' => $z['termin_datum'],
            'termin_zeit' => $z['termin_zeit'],
            'status' => $z['status'],
            'name' => $z['anonymisiert'] === null && is_string($z['name_vs']) ? $this->tresor->entschluesseln($z['name_vs'], "auftrag:{$z['nummer']}:name") : null,
            'offene_angebote' => (int) $z['offene_angebote'],
            'geaendert' => $z['geaendert'],
        ], $zeilen);
    }

    /** @return array<string, mixed> */
    public function detail(int $id, int $benutzerId): array
    {
        $a = $this->perId($id);
        $nummer = (string) $a['nummer'];
        $this->protokoll->eintragen($benutzerId, 'auftrag_angesehen', $nummer);
        $offen = $a['anonymisiert'] === null;
        return [
            'id' => $id,
            'nummer' => $nummer,
            'status' => $a['status'],
            'status_text' => self::STATUS[(string) $a['status']] ?? $a['status'],
            'naechste' => array_map(static fn (string $s): array => ['status' => $s, 'text' => self::STATUS[$s]], self::UEBERGAENGE[(string) $a['status']] ?? []),
            'leistung' => $a['leistung'],
            'leistung_text' => $this->katalog->titel('leistung', (string) $a['leistung']),
            'rad' => $a['rad'],
            'rad_text' => $this->katalog->titel('rad', (string) $a['rad']),
            'termin_datum' => $a['termin_datum'],
            'termin_zeit' => $a['termin_zeit'],
            'name' => $offen ? $this->tresor->entschluesseln((string) $a['name_vs'], "auftrag:$nummer:name") : null,
            'email' => $offen ? $this->tresor->entschluesseln((string) $a['email_vs'], "auftrag:$nummer:email") : null,
            'telefon' => $offen ? $this->tresor->entschluesselnOptional($a['telefon_vs'], "auftrag:$nummer:telefon") : null,
            'nachricht' => $offen ? $this->tresor->entschluesselnOptional($a['nachricht_vs'], "auftrag:$nummer:nachricht") : null,
            'verlauf' => $this->verlauf($id, $nummer),
            'angebote' => $this->angebote($id),
            'notizen' => array_map(fn (array $n): array => [
                'zeit' => $n['zeit'],
                'von' => $n['von'],
                'text' => $this->tresor->entschluesseln((string) $n['text_vs'], "notiz:$nummer"),
            ], $this->db->zeilen('SELECT n.zeit, n.text_vs, b.anzeigename AS von FROM notizen n LEFT JOIN benutzer b ON b.id = n.benutzer_id WHERE n.auftrag_id = ? ORDER BY n.id', [$id])),
            'widerrufe' => $this->db->zeilen('SELECT oeffentliche_id, eingang, bearbeitet FROM widerrufe WHERE auftrag_id = ? ORDER BY id', [$id]),
            'erstellt' => $a['erstellt'],
            'anonymisiert' => $a['anonymisiert'],
            'loeschung' => $this->loeschdatumText($a),
        ];
    }

    /** Entfernt alle Angaben zur Person. Leistung, Termin, Status und Beträge bleiben für die Buchhaltung. */
    public function anonymisieren(int $id, ?int $benutzerId, string $anlass): void
    {
        $a = $this->perId($id);
        if ($a['anonymisiert'] !== null) {
            return;
        }
        $this->db->transaktion(function () use ($id): void {
            $jetzt = $this->uhr->iso();
            $this->db->ausfuehren(
                'UPDATE auftraege SET name_vs = NULL, email_vs = NULL, email_index = NULL, telefon_vs = NULL, nachricht_vs = NULL, token_hash = ?, anonymisiert = ?, geaendert = ? WHERE id = ?',
                [new Binaer(random_bytes(32)), $jetzt, $jetzt, $id],
            );
            $this->db->ausfuehren('UPDATE verlauf SET hinweis_vs = NULL WHERE auftrag_id = ?', [$id]);
            $this->db->ausfuehren('DELETE FROM notizen WHERE auftrag_id = ?', [$id]);
        });
        $this->protokoll->eintragen($benutzerId, 'anonymisiert', (string) $a['nummer'], $anlass);
    }

    /** @param array<string, mixed> $a */
    public function loeschdatumText(array $a): string
    {
        return match ((string) $a['status']) {
            'abgeschlossen' => 'Kontaktdaten werden 24 Monate nach der Abholung gelöscht (Gewährleistung).',
            'storniert', 'nicht_erschienen' => 'Kontaktdaten werden 30 Tage nach dem Termin gelöscht.',
            default => 'Kontaktdaten werden gelöscht, sobald der Auftrag abgeschlossen ist und die Fristen abgelaufen sind.',
        };
    }

    /** Wendet die Löschfristen an. Läuft täglich. */
    public function fristenAnwenden(): int
    {
        $jetzt = $this->uhr->jetzt();
        $vor30 = $jetzt->modify('-30 day')->format('Y-m-d');
        $vor24m = $jetzt->modify('-24 month')->format('Y-m-d\TH:i:sP');
        $ids = array_merge(
            array_column($this->db->zeilen("SELECT id FROM auftraege WHERE anonymisiert IS NULL AND status IN ('storniert', 'nicht_erschienen') AND termin_datum < ? AND geaendert < ?", [$vor30, $vor30]), 'id'),
            array_column($this->db->zeilen("SELECT id FROM auftraege WHERE anonymisiert IS NULL AND status IN ('angefragt', 'bestaetigt') AND termin_datum < ?", [$vor30]), 'id'),
            array_column($this->db->zeilen("SELECT id FROM auftraege WHERE anonymisiert IS NULL AND status = 'abgeschlossen' AND abgeschlossen < ?", [$vor24m]), 'id'),
        );
        foreach (array_unique($ids) as $id) {
            $this->anonymisieren((int) $id, null, 'frist');
        }
        return count(array_unique($ids));
    }

    // ------------------------------------------------------------------ intern

    private function statusAendern(int $id, string $nummer, string $status, ?string $hinweis): void
    {
        $jetzt = $this->uhr->iso();
        $this->db->ausfuehren(
            'UPDATE auftraege SET status = ?, geaendert = ?, abgeschlossen = CASE WHEN ? = \'abgeschlossen\' THEN ? ELSE abgeschlossen END WHERE id = ?',
            [$status, $jetzt, $status, $jetzt, $id],
        );
        $this->verlaufEintragen($id, $nummer, $status, $hinweis);
    }

    private function verlaufEintragen(int $id, string $nummer, string $status, ?string $hinweis): void
    {
        $this->db->ausfuehren('INSERT INTO verlauf (auftrag_id, status, hinweis_vs, zeit) VALUES (?, ?, ?, ?)', [
            $id, $status, Binaer::oder($this->tresor->verschluesselnOptional($hinweis, "verlauf:$nummer")), $this->uhr->iso(),
        ]);
    }

    /** @return list<array{status: string, text: string, hinweis: ?string, zeit: string}> */
    private function verlauf(int $id, string $nummer): array
    {
        return array_map(fn (array $v): array => [
            'status' => (string) $v['status'],
            'text' => self::STATUS[(string) $v['status']] ?? (string) $v['status'],
            'hinweis' => $this->tresor->entschluesselnOptional($v['hinweis_vs'], "verlauf:$nummer"),
            'zeit' => (string) $v['zeit'],
        ], $this->db->zeilen('SELECT status, hinweis_vs, zeit FROM verlauf WHERE auftrag_id = ? ORDER BY id', [$id]));
    }

    /** @return list<array<string, mixed>> */
    private function angebote(int $id): array
    {
        return array_map(function (array $g): array {
            $fristBis = null;
            $widerrufbar = false;
            if ($g['entscheidung'] === 'angenommen' && is_string($g['entschieden'])) {
                $ende = (new \DateTimeImmutable($g['entschieden']))->modify('+' . self::WIDERRUFSFRIST_TAGE . ' day');
                $fristBis = $ende->format('Y-m-d');
                $widerrufbar = $this->uhr->jetzt() < $ende;
            }
            return [
                'id' => (int) $g['id'],
                'positionen' => json_decode((string) $g['positionen'], true),
                'summe_cent' => (int) $g['summe_cent'],
                'erstellt' => $g['erstellt'],
                'entscheidung' => $g['entscheidung'],
                'entschieden' => $g['entschieden'],
                'vorzeitiger_beginn' => (bool) $g['vorzeitiger_beginn'],
                'widerruf_bis' => $fristBis,
                'widerrufbar' => $widerrufbar,
            ];
        }, $this->db->zeilen('SELECT * FROM angebote WHERE auftrag_id = ? ORDER BY id', [$id]));
    }

    public static function neueNummer(): string
    {
        $teil = static function (): string {
            $s = '';
            for ($i = 0; $i < 4; $i++) {
                $s .= self::ALPHABET[random_int(0, 31)];
            }
            return $s;
        };
        return 'RF-' . $teil() . '-' . $teil();
    }

    public static function emailKuerzen(string $email): string
    {
        [$lokal, $domain] = array_pad(explode('@', $email, 2), 2, '');
        return mb_substr($lokal, 0, 1) . str_repeat('•', max(2, min(6, mb_strlen($lokal) - 1))) . '@' . $domain;
    }

    /** @param array<string, mixed> $e */
    private function mailAnfrage(string $nummer, string $token, array $e): string
    {
        $url = $this->konfig->url();
        $leistung = $this->katalog->titel('leistung', (string) $e['leistung']);
        $datum = Texte::datum((string) $e['datum']);
        return "Guten Tag,\n\nvielen Dank für Ihre Anfrage. Wir melden uns, sobald der Termin bestätigt ist.\n\n"
            . "Auftragsnummer: {$nummer}\nLeistung: {$leistung}\nWunschtermin: {$datum}, {$e['zeit']} Uhr\n\n"
            . "Hier sehen Sie jederzeit den Stand, können absagen, Ihre Daten herunterladen oder löschen:\n{$url}/status/#t={$token}\n\n"
            . "Bitte geben Sie diesen Link nicht weiter. Wer ihn hat, sieht den Stand Ihres Auftrags.\n\n"
            . "Die Anfrage ist noch kein Auftrag. Den Reparaturauftrag besprechen wir bei der Annahme in der Werkstatt.\n\n"
            . Texte::fusszeile($url);
    }

    /**
     * @param array<string, mixed> $a
     * @param list<array{text: string, cent: int}> $positionen
     */
    private function mailAngebot(array $a, array $positionen, int $summe): string
    {
        $url = $this->konfig->url();
        $zeilen = implode("\n", array_map(static fn (array $p): string => '- ' . $p['text'] . ': ' . Texte::euro($p['cent']), $positionen));
        return "Guten Tag,\n\nbei Ihrem Rad ({$a['nummer']}) haben wir weitere Arbeiten gefunden:\n\n{$zeilen}\n\nSumme: " . Texte::euro($summe) . " inkl. 19 % USt.\n\n"
            . "Über den Link aus Ihrer ersten Mail können Sie die Arbeiten freigeben oder ablehnen. Ohne Ihre Freigabe machen wir nur die vereinbarten Arbeiten.\n\n"
            . Texte::fusszeile($url);
    }

    /**
     * @param array<string, mixed> $a
     * @param array<mixed> $positionen
     */
    private function mailVertrag(array $a, array $positionen, int $summe, string $zeit, bool $vorzeitig, string $pruefsumme): string
    {
        $url = $this->konfig->url();
        $zeilen = implode("\n", array_map(static fn (array $p): string => '- ' . ($p['text'] ?? '') . ': ' . Texte::euro((int) ($p['cent'] ?? 0)), array_filter($positionen, 'is_array')));
        $beginn = $vorzeitig
            ? "Sie haben ausdrücklich verlangt, dass wir vor Ablauf der Widerrufsfrist beginnen, und bestätigt, dass Sie Ihr Widerrufsrecht bei vollständiger Vertragserfüllung verlieren."
            : "Sie haben nicht verlangt, dass wir vor Ablauf der Widerrufsfrist beginnen. Wir beginnen mit den Zusatzarbeiten deshalb erst nach Ablauf der Frist, außer Sie teilen uns etwas anderes mit.";
        return "Guten Tag,\n\nhiermit bestätigen wir Ihren Auftrag über folgende Zusatzarbeiten an Ihrem Rad ({$a['nummer']}):\n\n{$zeilen}\n\nGesamtpreis: " . Texte::euro($summe) . " inkl. 19 % USt.\n"
            . "Zahlung bei Abholung in bar oder mit Karte.\nAuftrag erteilt am: " . Texte::zeit($zeit) . "\n\n{$beginn}\n\n"
            . "Vertrag widerrufen: {$url}/widerruf/\n\n"
            . Texte::widerrufsbelehrung($url) . "\n\n" . Texte::widerrufsformular() . "\n\n"
            . "Prüfsumme dieses Vertrags: {$pruefsumme}\n\n" . Texte::fusszeile($url);
    }
}
