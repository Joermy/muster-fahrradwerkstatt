<?php

declare(strict_types=1);

namespace Radhaus\Daten;

use PDO;
use PDOStatement;
use RuntimeException;
use Throwable;

/**
 * Dünne Hülle um PDO/SQLite. Werte gehen ausschließlich als Parameter in Abfragen,
 * nie als Teil des SQL-Textes.
 */
final class Datenbank
{
    private PDO $pdo;

    public function __construct(string $pfad)
    {
        if ($pfad !== ':memory:') {
            $ordner = dirname($pfad);
            if (!is_dir($ordner) && !mkdir($ordner, 0700, true) && !is_dir($ordner)) {
                throw new RuntimeException('Datenordner lässt sich nicht anlegen.');
            }
            $neu = !is_file($pfad);
            if ($neu) {
                $alt = umask(0077);
                touch($pfad);
                umask($alt);
            }
        }
        $this->pdo = new PDO('sqlite:' . $pfad, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
            PDO::ATTR_STRINGIFY_FETCHES => false,
        ]);
        $this->pdo->exec('PRAGMA foreign_keys = ON');
        $this->pdo->exec('PRAGMA busy_timeout = 5000');
        // Gelöschte Inhalte werden in der Datei überschrieben statt nur freigegeben.
        $this->pdo->exec('PRAGMA secure_delete = ON');
        if ($pfad !== ':memory:') {
            $this->pdo->exec('PRAGMA journal_mode = WAL');
            $this->pdo->exec('PRAGMA synchronous = NORMAL');
        }
    }

    /** @param array<string|int, mixed> $werte */
    public function ausfuehren(string $sql, array $werte = []): PDOStatement
    {
        $befehl = $this->pdo->prepare($sql);
        foreach ($werte as $name => $wert) {
            $schluessel = is_int($name) ? $name + 1 : ':' . ltrim($name, ':');
            $typ = match (true) {
                $wert === null => PDO::PARAM_NULL,
                is_int($wert) => PDO::PARAM_INT,
                is_bool($wert) => PDO::PARAM_INT,
                $wert instanceof Binaer => PDO::PARAM_LOB,
                default => PDO::PARAM_STR,
            };
            $befehl->bindValue($schluessel, $wert instanceof Binaer ? $wert->roh : (is_bool($wert) ? (int) $wert : $wert), $typ);
        }
        $befehl->execute();
        return $befehl;
    }

    /**
     * @param array<string|int, mixed> $werte
     * @return array<string, mixed>|null
     */
    public function zeile(string $sql, array $werte = []): ?array
    {
        $z = $this->ausfuehren($sql, $werte)->fetch();
        return is_array($z) ? $z : null;
    }

    /**
     * @param array<string|int, mixed> $werte
     * @return list<array<string, mixed>>
     */
    public function zeilen(string $sql, array $werte = []): array
    {
        /** @var list<array<string, mixed>> */
        return $this->ausfuehren($sql, $werte)->fetchAll();
    }

    /** @param array<string|int, mixed> $werte */
    public function wert(string $sql, array $werte = []): mixed
    {
        $z = $this->ausfuehren($sql, $werte)->fetch(PDO::FETCH_NUM);
        return is_array($z) ? $z[0] : null;
    }

    public function letzteId(): int
    {
        return (int) $this->pdo->lastInsertId();
    }

    /**
     * Führt $arbeit in einer Transaktion aus. IMMEDIATE sperrt sofort zum Schreiben,
     * damit zwei gleichzeitige Buchungen denselben letzten Platz nicht beide bekommen.
     *
     * @template T
     * @param callable(): T $arbeit
     * @return T
     */
    public function transaktion(callable $arbeit): mixed
    {
        $this->pdo->exec('BEGIN IMMEDIATE');
        try {
            $ergebnis = $arbeit();
            $this->pdo->exec('COMMIT');
            return $ergebnis;
        } catch (Throwable $f) {
            $this->pdo->exec('ROLLBACK');
            throw $f;
        }
    }

    public function migrieren(string $ordner): int
    {
        $this->pdo->exec('CREATE TABLE IF NOT EXISTS schema_version (nummer INTEGER PRIMARY KEY, eingespielt TEXT NOT NULL)');
        $stand = (int) $this->wert('SELECT COALESCE(MAX(nummer), 0) FROM schema_version');
        $dateien = glob($ordner . '/*.sql') ?: [];
        sort($dateien);
        $neu = 0;
        foreach ($dateien as $datei) {
            $nummer = (int) basename($datei);
            if ($nummer <= $stand) {
                continue;
            }
            $sql = (string) file_get_contents($datei);
            $this->pdo->exec('BEGIN IMMEDIATE');
            try {
                $this->pdo->exec($sql);
                $this->ausfuehren('INSERT INTO schema_version (nummer, eingespielt) VALUES (?, ?)', [$nummer, date('c')]);
                $this->pdo->exec('COMMIT');
            } catch (Throwable $f) {
                $this->pdo->exec('ROLLBACK');
                throw $f;
            }
            $neu++;
        }
        return $neu;
    }

    /** Schreibt das Write-Ahead-Log zurück, damit gelöschte Daten auch dort verschwinden. */
    public function aufraeumen(): void
    {
        $this->pdo->exec('PRAGMA wal_checkpoint(TRUNCATE)');
    }

    public function sichernNach(string $ziel): void
    {
        $this->ausfuehren('VACUUM INTO ?', [$ziel]);
    }
}
