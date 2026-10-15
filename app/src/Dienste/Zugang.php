<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Binaer;
use Radhaus\Daten\Datenbank;
use Radhaus\Http\HttpFehler;
use Radhaus\Sicherheit\Passwort;
use Radhaus\Sicherheit\Totp;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Uhr;

/**
 * Anmeldung für die Verwaltung: Passwort (Argon2id), danach zweiter Faktor (TOTP).
 * Sitzungen liegen in der Datenbank, im Cookie steht nur eine Zufallskennung.
 */
final class Zugang
{
    public const LEERLAUF_SEK = 1800;
    public const HOECHSTDAUER_SEK = 36000;
    public const SPERRE_NACH = 5;

    public function __construct(
        private Datenbank $db,
        private Tresor $tresor,
        private Uhr $uhr,
        private Protokoll $protokoll,
    ) {
    }

    /**
     * Erster Schritt. Liefert eine Sitzung der Stufe "passwort", wenn TOTP aktiv ist,
     * sonst eine volle Sitzung, in der nur die Einrichtung von TOTP erlaubt ist.
     *
     * @return array{kennung: string, stufe: string, benutzer: array<string, mixed>}
     */
    public function anmelden(string $name, string $passwort): array
    {
        $b = $this->db->zeile('SELECT * FROM benutzer WHERE name = ? AND aktiv = 1', [mb_strtolower($name)]);
        $jetzt = $this->uhr->jetzt();
        if ($b !== null && $b['gesperrt_bis'] !== null && $jetzt->format('c') < (string) $b['gesperrt_bis']) {
            Passwort::pruefen($passwort, null);
            $this->protokoll->eintragen((int) $b['id'], 'anmeldung_gesperrt');
            throw $this->fehlgeschlagen();
        }
        if (!Passwort::pruefen($passwort, $b['passwort_hash'] ?? null) || $b === null) {
            if ($b !== null) {
                $versuche = (int) $b['fehlversuche'] + 1;
                $sperre = $versuche >= self::SPERRE_NACH
                    ? $jetzt->modify('+' . (15 * 2 ** min(4, $versuche - self::SPERRE_NACH)) . ' minutes')->format('c')
                    : null;
                $this->db->ausfuehren('UPDATE benutzer SET fehlversuche = ?, gesperrt_bis = ? WHERE id = ?', [$versuche, $sperre, $b['id']]);
                $this->protokoll->eintragen((int) $b['id'], 'anmeldung_falsch', '', "Versuch $versuche");
            }
            throw $this->fehlgeschlagen();
        }
        if (Passwort::neuHashenNoetig((string) $b['passwort_hash'])) {
            $this->db->ausfuehren('UPDATE benutzer SET passwort_hash = ? WHERE id = ?', [Passwort::hashen($passwort), $b['id']]);
        }
        $stufe = (int) $b['totp_aktiv'] === 1 ? 'passwort' : 'voll';
        if ($stufe === 'voll') {
            $this->erfolgreich((int) $b['id']);
        }
        return ['kennung' => $this->sitzungAnlegen((int) $b['id'], $stufe), 'stufe' => $stufe, 'benutzer' => $b];
    }

    /** Zweiter Schritt mit Code aus der App oder einem Ersatzcode. Liefert eine neue Sitzungskennung. */
    public function zweiterFaktor(string $kennung, string $code): string
    {
        $s = $this->sitzung($kennung, 'passwort');
        $b = $this->benutzer((int) $s['benutzer_id']);
        $geheimnis = $this->tresor->entschluesseln((string) $b['totp_vs'], 'totp:' . $b['id']);
        $schritt = Totp::pruefen($geheimnis, $code, (int) $b['totp_letzter_schritt'], $this->uhr->zeitstempel());
        if ($schritt !== null) {
            $this->db->ausfuehren('UPDATE benutzer SET totp_letzter_schritt = ? WHERE id = ?', [$schritt, $b['id']]);
        } elseif (!$this->ersatzcodeEinloesen((int) $b['id'], $code)) {
            $versuche = (int) $b['fehlversuche'] + 1;
            $this->db->ausfuehren('UPDATE benutzer SET fehlversuche = ?, gesperrt_bis = ? WHERE id = ?', [
                $versuche,
                $versuche >= self::SPERRE_NACH ? $this->uhr->jetzt()->modify('+15 minutes')->format('c') : null,
                $b['id'],
            ]);
            $this->protokoll->eintragen((int) $b['id'], 'code_falsch');
            if ($versuche >= self::SPERRE_NACH) {
                $this->abmelden($kennung);
            }
            throw new HttpFehler(401, 'code_falsch', 'Der Code stimmt nicht.');
        }
        $this->abmelden($kennung);
        $this->erfolgreich((int) $b['id']);
        return $this->sitzungAnlegen((int) $b['id'], 'voll');
    }

    /** @return array{sitzung: array<string, mixed>, benutzer: array<string, mixed>} */
    public function pruefen(string $kennung): array
    {
        $s = $this->sitzung($kennung, 'voll');
        $b = $this->benutzer((int) $s['benutzer_id']);
        $this->db->ausfuehren('UPDATE sitzungen SET zuletzt = ? WHERE id_hash = ?', [$this->uhr->zeitstempel(), new Binaer(Tresor::tokenHash($kennung))]);
        return ['sitzung' => $s, 'benutzer' => $b];
    }

    public function abmelden(string $kennung): void
    {
        $this->db->ausfuehren('DELETE FROM sitzungen WHERE id_hash = ?', [new Binaer(Tresor::tokenHash($kennung))]);
    }

    /** @return array{geheimnis: string, uri: string} */
    public function totpVorbereiten(int $benutzerId): array
    {
        $b = $this->benutzer($benutzerId);
        if ((int) $b['totp_aktiv'] === 1) {
            throw new HttpFehler(409, 'schon_aktiv', 'Die Zwei-Faktor-Anmeldung ist bereits eingerichtet.');
        }
        $geheimnis = Totp::geheimnis();
        $this->db->ausfuehren('UPDATE benutzer SET totp_vs = ? WHERE id = ?', [new Binaer($this->tresor->verschluesseln($geheimnis, 'totp:' . $benutzerId)), $benutzerId]);
        return ['geheimnis' => $geheimnis, 'uri' => Totp::uri($geheimnis, (string) $b['name'], 'Radhaus Fuhse')];
    }

    /** @return list<string> Ersatzcodes, nur dieses eine Mal im Klartext */
    public function totpBestaetigen(int $benutzerId, string $code): array
    {
        $b = $this->benutzer($benutzerId);
        if ((int) $b['totp_aktiv'] === 1 || !is_string($b['totp_vs'])) {
            throw new HttpFehler(409, 'nicht_vorbereitet', 'Bitte zuerst einen neuen Schlüssel anfordern.');
        }
        $geheimnis = $this->tresor->entschluesseln($b['totp_vs'], 'totp:' . $benutzerId);
        $schritt = Totp::pruefen($geheimnis, $code, 0, $this->uhr->zeitstempel());
        if ($schritt === null) {
            throw new HttpFehler(422, 'code_falsch', 'Der Code stimmt nicht. Bitte die Uhrzeit des Telefons prüfen.');
        }
        $codes = [];
        $this->db->transaktion(function () use ($benutzerId, $schritt, &$codes): void {
            $this->db->ausfuehren('UPDATE benutzer SET totp_aktiv = 1, totp_letzter_schritt = ? WHERE id = ?', [$schritt, $benutzerId]);
            $this->db->ausfuehren('DELETE FROM ersatzcodes WHERE benutzer_id = ?', [$benutzerId]);
            for ($i = 0; $i < 8; $i++) {
                $code = self::ersatzcode();
                $codes[] = $code;
                $this->db->ausfuehren('INSERT INTO ersatzcodes (benutzer_id, code_hash) VALUES (?, ?)', [$benutzerId, new Binaer($this->tresor->index('ersatz|' . $benutzerId . '|' . $code))]);
            }
        });
        $this->protokoll->eintragen($benutzerId, 'zweifaktor_eingerichtet');
        return $codes;
    }

    public function passwortAendern(int $benutzerId, string $alt, string $neu): void
    {
        $b = $this->benutzer($benutzerId);
        if (!Passwort::pruefen($alt, (string) $b['passwort_hash'])) {
            throw new HttpFehler(422, 'ungueltig', 'Bitte prüfen Sie die markierten Angaben.', ['felder' => ['alt' => 'Das bisherige Passwort stimmt nicht.']]);
        }
        $schwaeche = Passwort::schwaeche($neu, (string) $b['name']);
        if ($schwaeche !== null) {
            throw new HttpFehler(422, 'ungueltig', 'Bitte prüfen Sie die markierten Angaben.', ['felder' => ['neu' => $schwaeche]]);
        }
        $this->db->transaktion(function () use ($benutzerId, $neu): void {
            $this->db->ausfuehren('UPDATE benutzer SET passwort_hash = ?, passwort_wechseln = 0 WHERE id = ?', [Passwort::hashen($neu), $benutzerId]);
            // Alle anderen Sitzungen beenden.
            $this->db->ausfuehren('DELETE FROM sitzungen WHERE benutzer_id = ?', [$benutzerId]);
        });
        $this->protokoll->eintragen($benutzerId, 'passwort_geaendert');
    }

    /** @return array{id: int, passwort: string} */
    public function benutzerAnlegen(string $name, string $anzeigename, string $rolle, ?int $durch, ?string $passwort = null): array
    {
        $name = mb_strtolower($name);
        if (preg_match('/^[a-z][a-z0-9.\-]{2,31}$/', $name) !== 1) {
            throw HttpFehler::ungueltig(['name' => '3 bis 32 Zeichen: Kleinbuchstaben, Ziffern, Punkt, Bindestrich.']);
        }
        if ($this->db->wert('SELECT 1 FROM benutzer WHERE name = ?', [$name]) !== null) {
            throw HttpFehler::ungueltig(['name' => 'Diesen Namen gibt es schon.']);
        }
        $passwort ??= self::startpasswort();
        $this->db->ausfuehren(
            'INSERT INTO benutzer (name, anzeigename, rolle, passwort_hash, passwort_wechseln, erstellt) VALUES (?, ?, ?, ?, 1, ?)',
            [$name, $anzeigename, $rolle, Passwort::hashen($passwort), $this->uhr->iso()],
        );
        $id = $this->db->letzteId();
        $this->protokoll->eintragen($durch, 'benutzer_angelegt', $name, $rolle);
        return ['id' => $id, 'passwort' => $passwort];
    }

    public function benutzerSperren(int $id, int $durch): void
    {
        if ($id === $durch) {
            throw new HttpFehler(409, 'selbst', 'Sie können sich nicht selbst sperren.');
        }
        $this->db->transaktion(function () use ($id): void {
            $this->db->ausfuehren('UPDATE benutzer SET aktiv = 0 WHERE id = ?', [$id]);
            $this->db->ausfuehren('DELETE FROM sitzungen WHERE benutzer_id = ?', [$id]);
        });
        $this->protokoll->eintragen($durch, 'benutzer_gesperrt', (string) $id);
    }

    /** @return list<array<string, mixed>> */
    public function benutzerListe(): array
    {
        return $this->db->zeilen('SELECT id, name, anzeigename, rolle, totp_aktiv, aktiv, letzte_anmeldung, erstellt FROM benutzer ORDER BY id');
    }

    public function aufraeumen(): void
    {
        $jetzt = $this->uhr->zeitstempel();
        $this->db->ausfuehren('DELETE FROM sitzungen WHERE zuletzt < ? OR erstellt < ?', [$jetzt - self::LEERLAUF_SEK, $jetzt - self::HOECHSTDAUER_SEK]);
    }

    // ------------------------------------------------------------------ intern

    private function sitzungAnlegen(int $benutzerId, string $stufe): string
    {
        $kennung = Tresor::zufallsToken();
        $jetzt = $this->uhr->zeitstempel();
        $this->db->ausfuehren('INSERT INTO sitzungen (id_hash, benutzer_id, stufe, csrf, erstellt, zuletzt) VALUES (?, ?, ?, ?, ?, ?)', [
            new Binaer(Tresor::tokenHash($kennung)), $benutzerId, $stufe, Tresor::zufallsToken(), $jetzt, $jetzt,
        ]);
        return $kennung;
    }

    /** @return array<string, mixed> */
    private function sitzung(string $kennung, string $stufe): array
    {
        if (preg_match('/^[A-Za-z0-9_-]{43}$/', $kennung) !== 1) {
            throw $this->nichtAngemeldet();
        }
        $s = $this->db->zeile('SELECT * FROM sitzungen WHERE id_hash = ?', [new Binaer(Tresor::tokenHash($kennung))]);
        $jetzt = $this->uhr->zeitstempel();
        $leerlauf = $stufe === 'passwort' ? 300 : self::LEERLAUF_SEK;
        if ($s === null || $s['stufe'] !== $stufe || (int) $s['zuletzt'] < $jetzt - $leerlauf || (int) $s['erstellt'] < $jetzt - self::HOECHSTDAUER_SEK) {
            if ($s !== null && $s['stufe'] === $stufe) {
                $this->abmelden($kennung);
            }
            throw $this->nichtAngemeldet();
        }
        return $s;
    }

    /** @return array<string, mixed> */
    private function benutzer(int $id): array
    {
        $b = $this->db->zeile('SELECT * FROM benutzer WHERE id = ? AND aktiv = 1', [$id]);
        if ($b === null) {
            throw $this->nichtAngemeldet();
        }
        return $b;
    }

    private function erfolgreich(int $id): void
    {
        $this->db->ausfuehren('UPDATE benutzer SET fehlversuche = 0, gesperrt_bis = NULL, letzte_anmeldung = ? WHERE id = ?', [$this->uhr->iso(), $id]);
        $this->protokoll->eintragen($id, 'anmeldung');
    }

    private function ersatzcodeEinloesen(int $benutzerId, string $code): bool
    {
        $code = strtoupper(trim($code));
        if (preg_match('/^[A-Z2-9]{4}-[A-Z2-9]{4}$/', $code) !== 1) {
            return false;
        }
        $treffer = $this->db->ausfuehren(
            'UPDATE ersatzcodes SET verwendet = ? WHERE benutzer_id = ? AND code_hash = ? AND verwendet IS NULL',
            [$this->uhr->iso(), $benutzerId, new Binaer($this->tresor->index('ersatz|' . $benutzerId . '|' . $code))],
        )->rowCount();
        if ($treffer === 1) {
            $this->protokoll->eintragen($benutzerId, 'ersatzcode_verwendet');
            return true;
        }
        return false;
    }

    private function fehlgeschlagen(): HttpFehler
    {
        return new HttpFehler(401, 'anmeldung_fehlgeschlagen', 'Benutzername oder Passwort stimmen nicht, oder das Konto ist vorübergehend gesperrt.');
    }

    private function nichtAngemeldet(): HttpFehler
    {
        return new HttpFehler(401, 'nicht_angemeldet', 'Bitte melden Sie sich an.');
    }

    private static function ersatzcode(): string
    {
        $a = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        $s = '';
        for ($i = 0; $i < 8; $i++) {
            $s .= $a[random_int(0, 31)] . ($i === 3 ? '-' : '');
        }
        return $s;
    }

    public static function startpasswort(): string
    {
        $a = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        $s = '';
        for ($i = 0; $i < 20; $i++) {
            $s .= $a[random_int(0, strlen($a) - 1)];
        }
        return implode('-', str_split($s, 5));
    }
}
