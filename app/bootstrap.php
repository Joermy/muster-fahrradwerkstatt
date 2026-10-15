<?php

declare(strict_types=1);

define('RADHAUS_WURZEL', dirname(__DIR__));

spl_autoload_register(static function (string $klasse): void {
    $vorsilbe = 'Radhaus\\';
    if (!str_starts_with($klasse, $vorsilbe)) {
        return;
    }
    $datei = __DIR__ . '/src/' . str_replace('\\', '/', substr($klasse, strlen($vorsilbe))) . '.php';
    if (is_file($datei)) {
        require $datei;
    }
});

date_default_timezone_set('Europe/Berlin');
mb_internal_encoding('UTF-8');

ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('expose_php', '0');
error_reporting(E_ALL);

set_error_handler(static function (int $nr, string $text, string $datei, int $zeile): bool {
    if (!(error_reporting() & $nr)) {
        return false;
    }
    throw new ErrorException($text, 0, $nr, $datei, $zeile);
});
