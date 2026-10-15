<?php

declare(strict_types=1);

/*
 * Verschlüsselte Sicherung der Datenbank:
 *
 *     php bin/sicherung.php                         neue Sicherung in var/sicherungen/ (die letzten 14 bleiben)
 *     php bin/sicherung.php --pruefen DATEI         Sicherung entschlüsseln und auf Fehler prüfen
 *     php bin/sicherung.php --zurueck DATEI ZIEL    Sicherung als neue SQLite-Datei ZIEL auspacken
 *
 * Für den Cronjob, einmal täglich nach den Aufgaben, z. B.: 30 3 * * * php /pfad/bin/sicherung.php
 * Die Dateien regelmäßig vom Server wegkopieren. Ohne APP_SCHLUESSEL aus der .env lassen sie
 * sich nicht öffnen; den Schlüssel deshalb getrennt aufbewahren (Passwort-Manager, Papier im Tresor).
 */

require __DIR__ . '/../app/bootstrap.php';

use Radhaus\App;
use Radhaus\Konfiguration;

$app = new App(Konfiguration::laden(RADHAUS_WURZEL));
$befehl = $argv[1] ?? '';

try {
    if ($befehl === '--pruefen' && isset($argv[2])) {
        $tmp = sys_get_temp_dir() . '/radhaus-pruefen-' . bin2hex(random_bytes(6)) . '.sqlite';
        try {
            $app->sicherung->entschluesseln($argv[2], $tmp);
            $pdo = new PDO('sqlite:' . $tmp, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
            $abfrage = static fn (string $sql): string => (string) ($pdo->query($sql) ?: throw new RuntimeException('Abfrage fehlgeschlagen.'))->fetchColumn();
            $ok = $abfrage('PRAGMA integrity_check');
            $auftraege = $abfrage('SELECT COUNT(*) FROM auftraege');
            echo "Sicherung lesbar. Integrität: {$ok}. Aufträge: {$auftraege}.\n";
        } finally {
            if (is_file($tmp)) {
                unlink($tmp);
            }
        }
    } elseif ($befehl === '--zurueck' && isset($argv[2], $argv[3])) {
        $app->sicherung->entschluesseln($argv[2], $argv[3]);
        echo "Ausgepackt nach {$argv[3]}. Zum Zurückspielen den Server anhalten und DATENBANK in der .env darauf zeigen lassen.\n";
    } elseif ($befehl === '') {
        echo $app->sicherung->erstellen(RADHAUS_WURZEL . '/var/sicherungen') . "\n";
    } else {
        fwrite(STDERR, "Aufruf: php bin/sicherung.php [--pruefen DATEI | --zurueck DATEI ZIEL]\n");
        exit(2);
    }
} catch (RuntimeException $f) {
    fwrite(STDERR, $f->getMessage() . "\n");
    exit(1);
}
