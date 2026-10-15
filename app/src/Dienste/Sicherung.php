<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

use Radhaus\Daten\Datenbank;
use Radhaus\Sicherheit\Tresor;
use Radhaus\Uhr;
use RuntimeException;

/**
 * Verschlüsselte Sicherungen der Datenbank. Die Kopie entsteht mit VACUUM INTO (konsistent,
 * auch während Besucher buchen) und wird mit XChaCha20-Poly1305 als Strom verschlüsselt. Der
 * Schlüssel ist aus APP_SCHLUESSEL abgeleitet: Wer nur die Sicherung hat, kann nichts lesen,
 * und eine veränderte Datei fällt beim Zurückspielen auf.
 */
final class Sicherung
{
    private const KENNUNG = "RHSICH1\n";
    private const BLOCK = 65536;

    public function __construct(private Datenbank $db, private Tresor $tresor, private Uhr $uhr)
    {
    }

    /** Legt eine Sicherung an und löscht alte über die Anzahl hinaus. Liefert den Pfad. */
    public function erstellen(string $ordner, int $behalten = 14): string
    {
        if (!is_dir($ordner) && !mkdir($ordner, 0700, true) && !is_dir($ordner)) {
            throw new RuntimeException("Ordner $ordner lässt sich nicht anlegen.");
        }
        $roh = $ordner . '/.roh-' . bin2hex(random_bytes(6)) . '.sqlite';
        $ziel = $ordner . '/radhaus-' . $this->uhr->jetzt()->format('Y-m-d-His') . '-' . bin2hex(random_bytes(2)) . '.sqlite.enc';
        $alt = umask(0077);
        try {
            $this->db->sichernNach($roh);
            $this->verschluesseln($roh, $ziel);
        } finally {
            if (is_file($roh)) {
                // Klartext-Kopie sofort entfernen
                unlink($roh);
            }
            umask($alt);
        }
        $vorhanden = glob($ordner . '/radhaus-*.sqlite.enc') ?: [];
        sort($vorhanden);
        foreach (array_slice($vorhanden, 0, max(0, count($vorhanden) - $behalten)) as $weg) {
            unlink($weg);
        }
        return $ziel;
    }

    /** Entschlüsselt eine Sicherung in eine neue SQLite-Datei. Bricht bei jeder Veränderung ab. */
    public function entschluesseln(string $quelle, string $ziel): void
    {
        $ein = fopen($quelle, 'rb');
        if ($ein === false) {
            throw new RuntimeException("$quelle lässt sich nicht lesen.");
        }
        $alt = umask(0077);
        $aus = fopen($ziel, 'xb');
        umask($alt);
        if ($aus === false) {
            fclose($ein);
            throw new RuntimeException("$ziel gibt es schon oder lässt sich nicht anlegen.");
        }
        try {
            if (fread($ein, strlen(self::KENNUNG)) !== self::KENNUNG) {
                throw new RuntimeException('Das ist keine Sicherung dieser Software.');
            }
            $kopf = (string) fread($ein, SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_HEADERBYTES);
            $zustand = sodium_crypto_secretstream_xchacha20poly1305_init_pull($kopf, $this->tresor->sicherungsschluessel());
            $ende = false;
            while (!feof($ein)) {
                $block = (string) fread($ein, self::BLOCK + SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_ABYTES);
                if ($block === '') {
                    break;
                }
                $teil = sodium_crypto_secretstream_xchacha20poly1305_pull($zustand, $block);
                if ($teil === false) {
                    throw new RuntimeException('Sicherung beschädigt oder mit anderem Schlüssel erstellt.');
                }
                [$klar, $marke] = $teil;
                fwrite($aus, $klar);
                if ($marke === SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_TAG_FINAL) {
                    $ende = true;
                    break;
                }
            }
            if (!$ende || fread($ein, 1) !== '') {
                throw new RuntimeException('Sicherung unvollständig oder verlängert.');
            }
        } catch (RuntimeException $f) {
            fclose($aus);
            unlink($ziel);
            throw $f;
        } finally {
            fclose($ein);
        }
        fclose($aus);
    }

    private function verschluesseln(string $quelle, string $ziel): void
    {
        $ein = fopen($quelle, 'rb');
        $aus = fopen($ziel, 'xb');
        if ($ein === false || $aus === false) {
            throw new RuntimeException('Sicherung lässt sich nicht schreiben.');
        }
        [$zustand, $kopf] = sodium_crypto_secretstream_xchacha20poly1305_init_push($this->tresor->sicherungsschluessel());
        fwrite($aus, self::KENNUNG . $kopf);
        $groesse = (int) filesize($quelle);
        $gelesen = 0;
        do {
            $block = (string) fread($ein, self::BLOCK);
            $gelesen += strlen($block);
            $letzter = $gelesen >= $groesse || feof($ein);
            fwrite($aus, sodium_crypto_secretstream_xchacha20poly1305_push(
                $zustand,
                $block,
                '',
                $letzter ? SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_TAG_FINAL : SODIUM_CRYPTO_SECRETSTREAM_XCHACHA20POLY1305_TAG_MESSAGE,
            ));
        } while (!$letzter);
        fclose($ein);
        fclose($aus);
    }
}
