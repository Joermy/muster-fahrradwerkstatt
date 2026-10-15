<?php

declare(strict_types=1);

// Einziger PHP-Einstieg im Webroot. Alles andere liegt außerhalb von public/.
require __DIR__ . '/../app/bootstrap.php';

try {
    $konfig = Radhaus\Konfiguration::laden(RADHAUS_WURZEL);
    $anfrage = Radhaus\Http\Anfrage::ausGlobalen($konfig->vertrauteProxys());
    if (!str_starts_with($anfrage->pfad, '/api/')) {
        http_response_code(404);
        exit;
    }
    $app = new Radhaus\App($konfig);
} catch (Throwable $f) {
    error_log('radhaus: Start fehlgeschlagen: ' . $f->getMessage());
    http_response_code(503);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo '{"fehler":"wartung","meldung":"Die Werkstatt-Software ist gerade nicht erreichbar."}';
    exit;
}

$app->beantworten($anfrage)->senden();
