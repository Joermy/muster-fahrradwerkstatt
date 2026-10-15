<?php

declare(strict_types=1);

// Für den Cronjob, einmal täglich, z. B.: 15 3 * * * php /pfad/bin/aufgaben.php
require __DIR__ . '/../app/bootstrap.php';

$app = new Radhaus\App(Radhaus\Konfiguration::laden(RADHAUS_WURZEL));
$ergebnis = $app->aufgaben->ausfuehren(in_array('--jetzt', $argv, true));
echo $ergebnis === [] ? "Heute schon erledigt.\n" : json_encode($ergebnis, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
