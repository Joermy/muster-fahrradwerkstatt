<?php

declare(strict_types=1);

namespace Radhaus\Dienste;

/**
 * Texte für Mails und Vertragsbestätigungen. Die Widerrufsbelehrung folgt dem
 * gesetzlichen Muster (Anlage 1 zu Art. 246a § 1 Abs. 2 EGBGB) für Dienstleistungen
 * mit dem Hinweis auf die Online-Widerrufsfunktion (§ 356a BGB).
 * Musterseite: vor Verwendung für einen echten Betrieb rechtlich prüfen lassen.
 */
final class Texte
{
    public const BELEHRUNG_FASSUNG = '2026-06-19';

    public const BETRIEB = [
        'name' => 'Radhaus Fuhse',
        'inhaberin' => 'Mira Ohlendorf',
        'strasse' => 'Speichenweg 7',
        'ort' => '31224 Peine',
        'telefon' => '030 23125 417',
        'email' => 'werkstatt@radhaus-fuhse.example',
    ];

    public static function anschrift(): string
    {
        $b = self::BETRIEB;
        return "{$b['name']}, Inhaberin {$b['inhaberin']}, {$b['strasse']}, {$b['ort']}, Telefon {$b['telefon']}, E-Mail {$b['email']}";
    }

    public static function widerrufsbelehrung(string $url): string
    {
        $anschrift = self::anschrift();
        return <<<TXT
        WIDERRUFSBELEHRUNG
        (gilt für Zusatzaufträge, die Sie über unsere Website erteilen)

        Widerrufsrecht

        Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen diesen Vertrag zu widerrufen.

        Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag des Vertragsabschlusses.

        Um Ihr Widerrufsrecht auszuüben, müssen Sie uns ({$anschrift}) mittels einer eindeutigen Erklärung (z. B. ein mit der Post versandter Brief oder eine E-Mail) über Ihren Entschluss, diesen Vertrag zu widerrufen, informieren. Sie können dafür das beigefügte Muster-Widerrufsformular verwenden, das jedoch nicht vorgeschrieben ist.

        Sie können Ihr Widerrufsrecht auch online unter {$url}/widerruf/ ausüben. Wenn Sie diese Online-Funktion nutzen, übermitteln wir Ihnen auf einem dauerhaften Datenträger (z. B. per E-Mail) unverzüglich eine Bestätigung über den Eingang Ihres Widerrufs mit dessen Inhalt sowie Datum und Uhrzeit des Eingangs.

        Zur Wahrung der Widerrufsfrist reicht es aus, dass Sie die Mitteilung über die Ausübung des Widerrufsrechts vor Ablauf der Widerrufsfrist absenden.

        Folgen des Widerrufs

        Wenn Sie diesen Vertrag widerrufen, haben wir Ihnen alle Zahlungen, die wir von Ihnen erhalten haben, unverzüglich und spätestens binnen vierzehn Tagen ab dem Tag zurückzuzahlen, an dem die Mitteilung über Ihren Widerruf dieses Vertrags bei uns eingegangen ist. Für diese Rückzahlung verwenden wir dasselbe Zahlungsmittel, das Sie bei der ursprünglichen Transaktion eingesetzt haben, es sei denn, mit Ihnen wurde ausdrücklich etwas anderes vereinbart; in keinem Fall werden Ihnen wegen dieser Rückzahlung Entgelte berechnet.

        Haben Sie verlangt, dass die Dienstleistungen während der Widerrufsfrist beginnen sollen, so haben Sie uns einen angemessenen Betrag zu zahlen, der dem Anteil der bis zu dem Zeitpunkt, zu dem Sie uns von der Ausübung des Widerrufsrechts hinsichtlich dieses Vertrags unterrichten, bereits erbrachten Dienstleistungen im Vergleich zum Gesamtumfang der im Vertrag vorgesehenen Dienstleistungen entspricht.

        Hinweis zum Erlöschen

        Ihr Widerrufsrecht erlischt, wenn wir die Dienstleistung vollständig erbracht haben und Sie vorher ausdrücklich zugestimmt haben, dass wir vor Ablauf der Widerrufsfrist beginnen, und Sie Ihre Kenntnis davon bestätigt haben, dass Sie Ihr Widerrufsrecht bei vollständiger Vertragserfüllung verlieren.

        Ende der Widerrufsbelehrung
        TXT;
    }

    public static function widerrufsformular(): string
    {
        $anschrift = self::anschrift();
        return <<<TXT
        MUSTER-WIDERRUFSFORMULAR
        (Wenn Sie den Vertrag widerrufen wollen, dann füllen Sie bitte dieses Formular aus und senden Sie es zurück.)

        An {$anschrift}:

        Hiermit widerrufe(n) ich/wir (*) den von mir/uns (*) abgeschlossenen Vertrag über die Erbringung der folgenden Dienstleistung (*)
        Bestellt am (*):
        Name des/der Verbraucher(s):
        Anschrift des/der Verbraucher(s):
        Unterschrift des/der Verbraucher(s) (nur bei Mitteilung auf Papier):
        Datum:

        (*) Unzutreffendes streichen.
        TXT;
    }

    public static function fusszeile(string $url): string
    {
        $b = self::BETRIEB;
        return "--\n{$b['name']} · Inhaberin {$b['inhaberin']} · {$b['strasse']} · {$b['ort']}\nTelefon {$b['telefon']} · {$url}\nImpressum: {$url}/impressum/ · Datenschutz: {$url}/datenschutz/\n\nMUSTERSEITE: Diesen Betrieb gibt es nicht.";
    }

    public static function euro(int $cent): string
    {
        return number_format($cent / 100, 2, ',', '.') . ' €';
    }

    public static function datum(string $iso): string
    {
        $t = date_create($iso);
        return $t ? $t->format('d.m.Y') : $iso;
    }

    public static function zeit(string $iso): string
    {
        $t = date_create($iso);
        return $t ? $t->format('d.m.Y, H:i') . ' Uhr' : $iso;
    }
}
