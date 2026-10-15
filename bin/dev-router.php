<?php

declare(strict_types=1);

/*
 * Router für den eingebauten PHP-Server, nur zur Entwicklung:
 *
 *     php -S 127.0.0.1:8094 -t public bin/dev-router.php
 *
 * Liefert Dateien aus public/ mit denselben Sicherheitsköpfen wie die .htaccess
 * und gibt /api/ an public/index.php weiter.
 */

$wurzel = (string) realpath(__DIR__ . '/../public');
$pfad = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));

if (str_starts_with($pfad, '/api/')) {
    require $wurzel . '/index.php';
    return true;
}

header_remove('X-Powered-By');
$kopf = require __DIR__ . '/../konfig/kopfzeilen.php';
foreach ($kopf as $name => $wert) {
    header($name . ': ' . $wert);
}

$datei = realpath($wurzel . $pfad);
if ($datei !== false && is_dir($datei)) {
    $datei = realpath($datei . '/index.html');
}
$verboten = $datei === false
    || !str_starts_with($datei, $wurzel . DIRECTORY_SEPARATOR)
    || preg_match('#/\.(?!well-known/)|\.php$#', substr($datei, strlen($wurzel))) === 1;

if ($verboten || !is_file($datei)) {
    http_response_code(404);
    header('Content-Type: text/html; charset=utf-8');
    readfile($wurzel . '/404.html');
    return true;
}

$typen = [
    'html' => 'text/html; charset=utf-8', 'css' => 'text/css; charset=utf-8', 'js' => 'text/javascript; charset=utf-8',
    'json' => 'application/json; charset=utf-8', 'svg' => 'image/svg+xml', 'png' => 'image/png', 'jpg' => 'image/jpeg',
    'webp' => 'image/webp', 'avif' => 'image/avif', 'woff2' => 'font/woff2', 'glb' => 'model/gltf-binary', 'txt' => 'text/plain; charset=utf-8',
    'xml' => 'application/xml; charset=utf-8', 'ico' => 'image/x-icon', 'webmanifest' => 'application/manifest+json',
];
$endung = strtolower(pathinfo($datei, PATHINFO_EXTENSION));
header('Content-Type: ' . ($typen[$endung] ?? 'application/octet-stream'));
header('Cache-Control: ' . ($endung === 'html' ? 'no-cache' : 'public, max-age=3600'));
readfile($datei);
return true;
