<?php

declare(strict_types=1);

/*
 * Ersteinrichtung:
 *
 *     php bin/einrichten.php                     .env anlegen, Datenbank, erstes Konto
 *     php bin/einrichten.php --entwicklung       dasselbe für den eigenen Rechner (http://127.0.0.1:8094)
 *     php bin/einrichten.php --vorfuehrdaten     zusätzlich erfundene Aufträge
 */

require __DIR__ . '/../app/bootstrap.php';

use Radhaus\App;
use Radhaus\Daten\Binaer;
use Radhaus\Dienste\Kalender;
use Radhaus\Konfiguration;
use Radhaus\Sicherheit\Tresor;

$entwicklung = in_array('--entwicklung', $argv, true) || in_array('--vorfuehrdaten', $argv, true);
$vorfuehrung = in_array('--vorfuehrdaten', $argv, true);
$env = RADHAUS_WURZEL . '/.env';

if (!is_file($env)) {
    $vorlage = (string) file_get_contents(RADHAUS_WURZEL . '/.env.beispiel');
    $ersetzen = ['APP_SCHLUESSEL=' => 'APP_SCHLUESSEL=base64:' . base64_encode(random_bytes(32))];
    if ($entwicklung) {
        $ersetzen += [
            'APP_UMGEBUNG=produktion' => 'APP_UMGEBUNG=entwicklung',
            'APP_URL=https://radhaus-fuhse.example' => 'APP_URL=http://127.0.0.1:8094',
            'POST_MODUS=mail' => 'POST_MODUS=ausgang',
        ];
    }
    $alt = umask(0077);
    file_put_contents($env, strtr($vorlage, $ersetzen));
    umask($alt);
    echo "Neue .env mit eigenem Schlüssel angelegt. Den Schlüssel getrennt sichern!\n";
}

$app = new App(Konfiguration::laden(RADHAUS_WURZEL));
if ($vorfuehrung && !$app->konfig->entwicklung()) {
    fwrite(STDERR, "Vorführdaten nur mit APP_UMGEBUNG=entwicklung.\n");
    exit(1);
}
echo "Datenbank bereit: {$app->konfig->datenbankPfad()}\n";

if ((int) $app->db->wert('SELECT COUNT(*) FROM benutzer') === 0) {
    $vorgabe = $vorfuehrung ? 'Vorfuehrung-2026!' : null;
    $neu = $app->zugang->benutzerAnlegen('inhaberin', 'Mira Ohlendorf', 'inhaber', null, $vorgabe);
    echo "\nKonto angelegt\n  Benutzer: inhaberin\n  Startpasswort: {$neu['passwort']}\n";
    echo "Bei der ersten Anmeldung werden ein neues Passwort und die Zwei-Faktor-Anmeldung verlangt.\n";
}

if (!$vorfuehrung) {
    exit(0);
}
if ((int) $app->db->wert('SELECT COUNT(*) FROM auftraege') > 0) {
    echo "Es gibt schon Aufträge, Vorführdaten werden nicht noch einmal angelegt.\n";
    exit(0);
}

// Erfundene Aufträge aus derselben Datei, die auch der Vorführmodus im Browser nutzt.
$daten = json_decode((string) file_get_contents(RADHAUS_WURZEL . '/app/daten/vorfuehrdaten.json'), true, 16, JSON_THROW_ON_ERROR);
$heute = $app->uhr->jetzt()->setTime(0, 0);
$jetzt = $app->uhr->jetzt();
// Vorführtermine relativ zu heute: nie auf Sonntage oder Feiertage, samstags nur Samstagszeiten,
// und nichts, was erst in der Zukunft passiert sein kann.
$termin = static function (int $tag, string $zeit) use ($heute): array {
    $d = $heute->modify(($tag >= 0 ? '+' : '') . $tag . ' day');
    while ((int) $d->format('N') === 7 || Kalender::feiertag($d->format('Y-m-d')) !== null) {
        $d = $d->modify($tag > 0 ? '+1 day' : '-1 day');
    }
    $samstag = ['09:00', '10:30', '12:00'];
    if ((int) $d->format('N') === 6 && !in_array($zeit, $samstag, true)) {
        $zeit = $samstag[crc32($zeit) % 3];
    }
    return [$d->format('Y-m-d'), $zeit];
};
$frueher = static fn (DateTimeImmutable $t, int $schritt): string => ($t < $jetzt ? $t : $jetzt->modify('-' . (5 + $schritt * 7) . ' minutes'))->format('c');
foreach ($daten['auftraege'] as $e) {
    $nummer = $e['nummer'];
    [$datum, $e['zeit']] = $termin((int) $e['tag'], (string) $e['zeit']);
    $anfang = min((int) $e['tag'] - 3, -1 - (crc32($nummer) % 3));
    $erstellt = $heute->modify($anfang . ' day')->setTime(9, 12)->format('c');
    $app->db->ausfuehren(
        'INSERT INTO auftraege (nummer, token_hash, leistung, rad, termin_datum, termin_zeit, status, name_vs, email_vs, email_index, telefon_vs, nachricht_vs, quelle, erstellt, geaendert, abgeschlossen)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            $nummer, new Binaer(Tresor::tokenHash($e['token'])), $e['leistung'], $e['rad'], $datum, $e['zeit'], $e['status'],
            new Binaer($app->tresor->verschluesseln($e['name'], "auftrag:$nummer:name")),
            new Binaer($app->tresor->verschluesseln($e['email'], "auftrag:$nummer:email")),
            new Binaer($app->tresor->index($e['email'])),
            Binaer::oder($app->tresor->verschluesselnOptional($e['telefon'] ?? null, "auftrag:$nummer:telefon")),
            Binaer::oder($app->tresor->verschluesselnOptional($e['nachricht'] ?? null, "auftrag:$nummer:nachricht")),
            $e['quelle'] ?? 'website', $erstellt, $erstellt,
            $e['status'] === 'abgeschlossen' ? $heute->modify(($e['tag'] + 2) . ' day')->setTime(16, 40)->format('c') : null,
        ],
    );
    $id = $app->db->letzteId();
    $anzahl = count($e['verlauf']);
    foreach ($e['verlauf'] as $i => $status) {
        $app->db->ausfuehren('INSERT INTO verlauf (auftrag_id, status, zeit) VALUES (?, ?, ?)', [
            $id, $status, $frueher($heute->modify(($anfang + $i) . ' day')->setTime(9 + $i, 12 + $i), $anzahl - $i),
        ]);
    }
    if (isset($e['angebot'])) {
        $summe = array_sum(array_column($e['angebot']['positionen'], 'cent'));
        $app->db->ausfuehren('INSERT INTO angebote (auftrag_id, positionen, summe_cent, erstellt, entscheidung, entschieden) VALUES (?, ?, ?, ?, ?, ?)', [
            $id, json_encode($e['angebot']['positionen'], JSON_UNESCAPED_UNICODE), $summe, $heute->modify(($e['tag'] + 1) . ' day')->setTime(11, 0)->format('c'),
            $e['angebot']['entscheidung'] ?? null, isset($e['angebot']['entscheidung']) ? $heute->modify(($e['tag'] + 1) . ' day')->setTime(12, 30)->format('c') : null,
        ]);
    }
}

echo "Vorführdaten angelegt: " . count($daten['auftraege']) . " Aufträge.\n";
echo "Demo-Status-Link: /status/#t={$daten['auftraege'][0]['token']}\n";
