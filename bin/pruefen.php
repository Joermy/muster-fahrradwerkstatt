<?php

declare(strict_types=1);

/*
 * Prüft vor dem Hochladen, ob die Auslieferung sicher eingestellt ist:
 *
 *     php bin/pruefen.php
 *
 *   - gleiche Sicherheitsköpfe in konfig/kopfzeilen.php, public/.htaccess und konfig/nginx.conf
 *   - keine geheimen oder ausführbaren Dateien im Webroot außer index.php
 *   - die Verwaltung und die Vorführfassung stehen nicht in Suchmaschinen
 *   - .env ist nur für den Besitzer lesbar
 *
 * Endet mit Code 1, wenn etwas nicht stimmt.
 */

$wurzel = dirname(__DIR__);
$fehler = [];
$kopf = require $wurzel . '/konfig/kopfzeilen.php';
$htaccess = (string) file_get_contents($wurzel . '/public/.htaccess');
$nginx = (string) file_get_contents($wurzel . '/konfig/nginx.conf');

foreach ($kopf as $name => $wert) {
    if (!str_contains($htaccess, "Header always set {$name} \"{$wert}\"")) {
        $fehler[] = "public/.htaccess: {$name} fehlt oder weicht ab";
    }
    if (!str_contains($nginx, "add_header {$name} \"{$wert}\" always;")) {
        $fehler[] = "konfig/nginx.conf: {$name} fehlt oder weicht ab";
    }
}

$it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($wurzel . '/public', FilesystemIterator::SKIP_DOTS));
foreach ($it as $datei) {
    /** @var SplFileInfo $datei */
    $rel = substr($datei->getPathname(), strlen($wurzel) + 1);
    $name = $datei->getFilename();
    if (preg_match('/\.(php|phtml|phar|sqlite|sqlite-wal|sqlite-shm|db|env|bak|sql|log|zip)$/i', $name) === 1 && $rel !== 'public/index.php') {
        $fehler[] = "{$rel}: gehört nicht in den Webroot";
    }
    if ($name === '.env' || str_starts_with($name, '.env.')) {
        $fehler[] = "{$rel}: Konfiguration mit Schlüssel im Webroot";
    }
}

foreach (['public', 'docs'] as $ordner) {
    $verwaltung = $wurzel . "/{$ordner}/verwaltung/index.html";
    if (is_file($verwaltung) && !str_contains((string) file_get_contents($verwaltung), 'name="robots" content="noindex, nofollow"')) {
        $fehler[] = "{$ordner}/verwaltung: noindex fehlt";
    }
}
foreach (glob($wurzel . '/docs/{,*/}index.html', GLOB_BRACE) ?: [] as $seite) {
    if (!str_contains((string) file_get_contents($seite), 'content="noindex, nofollow"')) {
        $fehler[] = substr($seite, strlen($wurzel) + 1) . ': Vorführfassung ohne noindex';
    }
}
if (!str_contains((string) @file_get_contents($wurzel . '/public/robots.txt'), 'Disallow: /verwaltung/')) {
    $fehler[] = 'public/robots.txt: /verwaltung/ nicht ausgeschlossen';
}

$env = $wurzel . '/.env';
if (is_file($env) && DIRECTORY_SEPARATOR === '/' && (fileperms($env) & 0o077) !== 0) {
    $fehler[] = '.env ist für andere lesbar (chmod 600 .env)';
}

if ($fehler !== []) {
    fwrite(STDERR, "Nicht in Ordnung:\n  - " . implode("\n  - ", $fehler) . "\n");
    exit(1);
}
echo "Alles in Ordnung: Köpfe gleich, Webroot sauber, Verwaltung nicht indexierbar.\n";
