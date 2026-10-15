<?php

declare(strict_types=1);

/*
 * Testlauf ohne Fremdbibliotheken:
 *
 *     php tests/lauf.php            alle Tests
 *     php tests/lauf.php Totp       nur Klassen, deren Name "Totp" enthält
 *
 * Jede Klasse in tests/Einheit und tests/Schnittstelle, deren Name auf "Test" endet, wird
 * geladen; jede öffentliche Methode, die mit "test" beginnt, läuft in einer frischen Instanz.
 */

require __DIR__ . '/../app/bootstrap.php';
require __DIR__ . '/Fall.php';

$filter = $argv[1] ?? '';
$dateien = array_merge(glob(__DIR__ . '/Einheit/*Test.php') ?: [], glob(__DIR__ . '/Schnittstelle/*Test.php') ?: []);
sort($dateien);

$gesamt = 0;
$fehler = [];
$start = microtime(true);
foreach ($dateien as $datei) {
    require_once $datei;
    $klasse = 'Radhaus\\Tests\\' . basename(dirname($datei)) . '\\' . basename($datei, '.php');
    if ($filter !== '' && !str_contains($klasse, $filter)) {
        continue;
    }
    foreach ((new ReflectionClass($klasse))->getMethods(ReflectionMethod::IS_PUBLIC) as $m) {
        if (!str_starts_with($m->getName(), 'test')) {
            continue;
        }
        $gesamt++;
        try {
            $fall = new $klasse();
            $fall->vorher();
            $fall->{$m->getName()}();
            $fall->nachher();
            echo '.';
        } catch (Throwable $f) {
            echo 'F';
            $fehler[] = sprintf("%s::%s\n  %s: %s\n  %s:%d", basename($datei, '.php'), $m->getName(), $f::class, $f->getMessage(), basename($f->getFile()), $f->getLine());
        }
    }
}
$dauer = round(microtime(true) - $start, 2);
echo "\n\n";
foreach ($fehler as $f) {
    echo $f, "\n\n";
}
printf("%d Tests, %d fehlgeschlagen, %d Prüfungen, %.2f s\n", $gesamt, count($fehler), Radhaus\Tests\Fall::$pruefungen, $dauer);
exit($fehler === [] && $gesamt > 0 ? 0 : 1);
