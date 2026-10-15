<?php

declare(strict_types=1);

/*
 * Baut die statischen Seiten aus vorlagen/ in zwei Fassungen:
 *
 *     php bin/bauen.php
 *
 *   public/  für den eigenen Server (mit PHP-Schnittstelle, indexierbar)
 *   docs/    Vorführmodus für GitHub Pages: dieselben Seiten, die Schnittstelle läuft im
 *            Browser, Daten bleiben im Tab, Suchmaschinen sollen nichts aufnehmen
 *
 * Inhalte (Preise, Adresse, Widerrufsbelehrung) kommen aus app/daten/leistungen.json und
 * app/src/Dienste/Texte.php, damit sie überall gleich lauten.
 */

require __DIR__ . '/../app/bootstrap.php';

use Radhaus\Dienste\Texte;
use Radhaus\Konfiguration;

$wurzel = RADHAUS_WURZEL;
$konfig = Konfiguration::laden($wurzel);
$katalog = json_decode((string) file_get_contents($wurzel . '/app/daten/leistungen.json'), true, 16, JSON_THROW_ON_ERROR);
$kopfzeilen = require $wurzel . '/konfig/kopfzeilen.php';
$rahmen = (string) file_get_contents($wurzel . '/vorlagen/rahmen.html');
$betrieb = Texte::BETRIEB;

$fassungen = [
    'public' => [
        'url' => 'https://radhaus-fuhse.example',
        'robots' => 'index, follow',
        'modus' => 'server',
        'muster' => '',
        'hosting' => '<p>Die Website liegt auf einem verwalteten Server in Deutschland bei der Hetzner Online GmbH, Industriestraße 25, 91710 Gunzenhausen. Mit ihr haben wir einen Vertrag zur Auftragsverarbeitung nach Art. 28 DSGVO geschlossen. Beim Aufruf einer Seite verarbeitet der Server technisch nötige Daten: IP-Adresse, Zeitpunkt, aufgerufene Adresse, übertragene Datenmenge, Statuscode und Browserkennung. Das ist nötig, um die Seite auszuliefern und Angriffe zu erkennen (Art. 6 Abs. 1 lit. f DSGVO). Die Protokolle werden nach sieben Tagen gelöscht.</p>',
        'speicher' => '',
    ],
    'docs' => [
        'url' => 'https://joermy.github.io/muster-fahrradwerkstatt',
        'robots' => 'noindex, nofollow',
        'modus' => 'vorfuehrung',
        'muster' => 'Vorführmodus: Eingaben bleiben in diesem Browser-Tab und werden nirgendwohin gesendet. ',
        'hosting' => '<p><strong>Diese Vorführfassung</strong> liegt bei GitHub Pages, einem Dienst der GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA. Verantwortlich für sie ist der Betreiber des Portfolios, siehe <a href="https://joermy.github.io/impressum/">Impressum des Portfolios</a>. Beim Aufruf verarbeitet GitHub Ihre IP-Adresse und technische Angaben in Server-Protokollen, um die Seite auszuliefern und zu schützen. GitHub ist nach dem EU-US Data Privacy Framework zertifiziert (Art. 45 DSGVO). Rechtsgrundlage ist das berechtigte Interesse, die Arbeitsprobe öffentlich zu zeigen (Art. 6 Abs. 1 lit. f DSGVO). Mehr in der <a href="https://docs.github.com/de/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">Datenschutzerklärung von GitHub</a>.</p><p>Die Schnittstelle der Werkstatt läuft in dieser Fassung vollständig in Ihrem Browser. Terminanfragen, Freigaben und Widerrufe werden nicht übertragen, sondern nur im Speicher des Tabs nachgestellt. Die Abschnitte 4 bis 12 beschreiben, wie die echte Website mit eigenem Server arbeitet.</p>',
        'speicher' => '<p>In der Vorführfassung kommt <strong>rh_vorfuehrung</strong> (sessionStorage) dazu: Dort liegen die erfundenen Aufträge und Ihre Eingaben, damit Terminbuchung und Verwaltung im Browser funktionieren. Nichts davon verlässt Ihren Rechner; der Eintrag verschwindet, wenn Sie den Tab schließen.</p>',
    ],
];

function h(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE | ENT_HTML5, 'UTF-8');
}

function euro(int $cent): string
{
    return number_format($cent / 100, 2, ',', '.') . ' €';
}

/** @param array<string, mixed> $katalog */
function preisliste(array $katalog, string $basis, bool $kurz): string
{
    $zeilen = '';
    $liste = $kurz ? array_slice($katalog['leistungen'], 0, 5) : $katalog['leistungen'];
    foreach ($liste as $l) {
        $umfang = '<ul>' . implode('', array_map(static fn ($u) => '<li>' . h($u) . '</li>', $l['umfang'])) . '</ul>';
        $zeilen .= '<tr><th scope="row">' . h($l['titel']) . '<small>' . h($l['kurz']) . '</small></th>'
            . ($kurz ? '' : '<td class="umfang">' . $umfang . '</td>')
            . '<td class="preis"><b>' . h(euro($l['preis_cent'])) . '</b><span>' . h($l['einheit']) . '</span></td>'
            . ($kurz ? '' : '<td class="aktion"><a href="' . $basis . 'termin/?leistung=' . rawurlencode($l['kennung']) . '">Termin anfragen</a></td>')
            . '</tr>';
    }
    $kopf = $kurz
        ? '<thead><tr><th scope="col">Leistung</th><th scope="col" class="preis">Preis</th></tr></thead>'
        : '<thead><tr><th scope="col">Leistung</th><th scope="col">Umfang</th><th scope="col" class="preis">Preis</th><th scope="col" class="aktion"><span class="unsichtbar">Termin</span></th></tr></thead>';
    return '<table class="preistafel">' . $kopf . '<tbody>' . $zeilen . '</tbody>'
        . ($kurz ? '' : '<caption>' . h($katalog['hinweis']) . ' Arbeitszeit über den genannten Umfang hinaus: ' . h(euro(1800)) . ' je angefangene 15 Minuten, nur nach Ihrer Freigabe.</caption>')
        . '</table>';
}

/**
 * Verwaltung: eine Seite, die Ansichten baut das Skript. Nie in Suchmaschinen.
 *
 * @param array<string, string> $kopfzeilen
 * @param array<string, string> $f
 */
function verwaltungSchreiben(string $wurzel, string $aus, array $kopfzeilen, array $f): void
{
    $csp = trim((string) preg_replace("/\\s*frame-ancestors[^;]*;?/", '', $kopfzeilen['Content-Security-Policy']), '; ');
    // Die Verwaltung bettet keine Karten ein
    $csp = (string) preg_replace("/frame-src [^;]*/", "frame-src 'none'", $csp);
    $html = strtr((string) file_get_contents($wurzel . '/vorlagen/verwaltung.html'), [
        '{{csp}}' => h($csp),
        '{{muster_zusatz}}' => h($f['muster']),
    ]);
    file_put_contents($aus . '/verwaltung/index.html', $html);
}

/** @param array<string, string> $betrieb */
function jsonld(array $betrieb, string $url): string
{
    [$plz, $stadt] = explode(' ', $betrieb['ort'], 2);
    $daten = [
        '@context' => 'https://schema.org',
        '@type' => 'BicycleStore',
        'name' => $betrieb['name'],
        'description' => 'Fahrradwerkstatt für Inspektion, Bremsen, Laufräder und E-Bikes. Musterseite, der Betrieb ist erfunden.',
        'url' => $url . '/',
        'telephone' => '+49 ' . ltrim(str_replace(' ', ' ', $betrieb['telefon']), '0'),
        'email' => $betrieb['email'],
        'image' => $url . '/assets/bilder/vorschau-1200.jpg',
        'priceRange' => '15 € – 139 €',
        'currenciesAccepted' => 'EUR',
        'paymentAccepted' => 'Bargeld, Girocard, Kreditkarte',
        'address' => [
            '@type' => 'PostalAddress',
            'streetAddress' => $betrieb['strasse'],
            'postalCode' => $plz,
            'addressLocality' => $stadt,
            'addressRegion' => 'Niedersachsen',
            'addressCountry' => 'DE',
        ],
        'openingHoursSpecification' => [
            ['@type' => 'OpeningHoursSpecification', 'dayOfWeek' => ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], 'opens' => '08:00', 'closes' => '18:00'],
            ['@type' => 'OpeningHoursSpecification', 'dayOfWeek' => 'Saturday', 'opens' => '09:00', 'closes' => '13:00'],
        ],
        'potentialAction' => ['@type' => 'ReserveAction', 'target' => $url . '/termin/', 'name' => 'Termin anfragen'],
    ];
    return '<script type="application/ld+json">' . json_encode($daten, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG) . "</script>\n";
}

function kopieren(string $von, string $nach): void
{
    if (is_dir($von)) {
        @mkdir($nach, 0755, true);
        foreach (scandir($von) ?: [] as $e) {
            if ($e === '.' || $e === '..') {
                continue;
            }
            kopieren("$von/$e", "$nach/$e");
        }
        return;
    }
    copy($von, $nach);
}

function leeren(string $ordner): void
{
    if (!is_dir($ordner)) {
        return;
    }
    foreach (scandir($ordner) ?: [] as $e) {
        if ($e === '.' || $e === '..') {
            continue;
        }
        $p = "$ordner/$e";
        if (is_dir($p)) {
            leeren($p);
            rmdir($p);
        } else {
            unlink($p);
        }
    }
}

$seiten = glob($wurzel . '/vorlagen/seiten/*.html') ?: [];
sort($seiten);

foreach ($fassungen as $ziel => $f) {
    $aus = $wurzel . '/' . $ziel;
    if ($ziel === 'docs') {
        leeren($aus);
        @mkdir($aus, 0755, true);
        kopieren($wurzel . '/public/assets', $aus . '/assets');
        // Nachgebaute Schnittstelle nur in der Vorführfassung, nie im Webroot des echten Servers
        @mkdir($aus . '/assets/js/vorfuehrung', 0755, true);
        copy($wurzel . '/vorlagen/vorfuehrung/server.js', $aus . '/assets/js/vorfuehrung/server.js');
        @unlink($aus . '/assets/modelle/rad-roh.glb');
        touch($aus . '/.nojekyll');
        file_put_contents($aus . '/robots.txt', "User-agent: *\nDisallow: /\n");
        // Vorführdaten für die Schnittstelle im Browser
        copy($wurzel . '/app/daten/vorfuehrdaten.json', $aus . '/assets/daten/vorfuehrdaten.json');
        // Mailtexte für den nachgebauten Server, damit der Postausgang dieselben Texte zeigt
        file_put_contents($aus . '/assets/daten/texte.json', json_encode([
            'betrieb' => Texte::BETRIEB,
            'anschrift' => Texte::anschrift(),
            'fusszeile' => Texte::fusszeile($f['url']),
            'widerrufsbelehrung' => Texte::widerrufsbelehrung($f['url']),
            'widerrufsformular' => Texte::widerrufsformular(),
            'belehrung_fassung' => Texte::BELEHRUNG_FASSUNG,
            'url' => $f['url'],
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR));
        @mkdir($aus . '/verwaltung', 0755, true);
        verwaltungSchreiben($wurzel, $aus, $kopfzeilen, $f);
    }
    @mkdir($aus . '/assets/daten', 0755, true);
    copy($wurzel . '/app/daten/leistungen.json', $aus . '/assets/daten/leistungen.json');
    file_put_contents($aus . '/assets/js/konfig.js', "// Wird von bin/bauen.php geschrieben.\nexport const MODUS = " . json_encode($f['modus']) . ";\n");

    $csp = $kopfzeilen['Content-Security-Policy'];
    $csp = trim((string) preg_replace("/\\s*frame-ancestors[^;]*;?/", '', $csp), '; ');
    $karte = [];
    foreach ($seiten as $datei) {
        $roh = (string) file_get_contents($datei);
        if (preg_match('/^<!--(\{.*?\})-->\s*/s', $roh, $m) !== 1) {
            throw new RuntimeException('Kopfzeile fehlt: ' . basename($datei));
        }
        $meta = json_decode($m[1], true, 8, JSON_THROW_ON_ERROR);
        $inhalt = substr($roh, strlen($m[0]));
        $pfad = $meta['pfad'];
        $tiefe = $pfad === '' ? 0 : substr_count(rtrim($pfad, '/'), '/') + 1;
        $basis = $pfad === '404' ? ($ziel === 'docs' ? '/muster-fahrradwerkstatt/' : '/') : str_repeat('../', $tiefe);
        $kanonisch = $f['url'] . '/' . ($pfad === '404' ? '' : $pfad);

        $ersetzen = [
            '{{preise_auszug}}' => preisliste($katalog, $basis, true),
            '{{preisliste}}' => preisliste($katalog, $basis, false),
            '{{widerrufsbelehrung}}' => h(Texte::widerrufsbelehrung($f['url'])),
            '{{widerrufsformular}}' => h(Texte::widerrufsformular()),
            '{{hosting}}' => $f['hosting'],
            '{{speicher_zusatz}}' => $f['speicher'],
        ];
        $inhalt = strtr($inhalt, $ersetzen);
        $skripte = '';
        foreach ($meta['skripte'] ?? [] as $s) {
            $skripte .= '<script type="module" src="' . $basis . 'assets/js/' . h($s) . '"></script>' . "\n";
        }
        $werte = [
            '{{basis}}' => $basis,
            '{{kennung}}' => h($meta['kennung']),
            '{{titel}}' => h($meta['titel']),
            '{{beschreibung}}' => h($meta['beschreibung']),
            '{{robots}}' => $pfad === '404' ? 'noindex, nofollow' : $f['robots'],
            '{{kanonisch}}' => h($kanonisch),
            '{{url}}' => $f['url'],
            '{{csp}}' => h($csp),
            '{{referrer}}' => $meta['referrer'] ?? 'strict-origin-when-cross-origin',
            '{{jsonld}}' => !empty($meta['jsonld']) ? jsonld($betrieb, $f['url']) : '',
            '{{kopf_zusatz}}' => '',
            '{{muster_zusatz}}' => h($f['muster']),
            '{{skripte}}' => $skripte,
            '{{strasse}}' => h($betrieb['strasse']),
            '{{ort}}' => h($betrieb['ort']),
            '{{telefon}}' => h($betrieb['telefon']),
            '{{telefon_link}}' => '+49' . str_replace(' ', '', ltrim($betrieb['telefon'], '0')),
            '{{email}}' => h($betrieb['email']),
        ];
        foreach (['leistungen', 'termin', 'status', 'kontakt'] as $n) {
            $werte["{{aktiv_$n}}"] = $meta['kennung'] === $n ? ' aria-current="page"' : '';
        }
        $html = strtr(strtr($rahmen, ['{{inhalt}}' => $inhalt]), $werte);
        $html = strtr($html, $werte);
        if (preg_match('/\{\{[a-z_]+\}\}/', $html, $rest) === 1) {
            throw new RuntimeException('Platzhalter übrig in ' . basename($datei) . ': ' . $rest[0]);
        }
        $datei_aus = $pfad === '404' ? "$aus/404.html" : "$aus/{$pfad}index.html";
        @mkdir(dirname($datei_aus), 0755, true);
        file_put_contents($datei_aus, $html);
        if ($pfad !== '404' && empty($meta['nicht_in_sitemap'])) {
            $karte[] = $kanonisch;
        }
    }
    if ($ziel === 'public') {
        $heute = date('Y-m-d');
        $xml = '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
        foreach ($karte as $u) {
            $xml .= "  <url><loc>" . h($u) . "</loc><lastmod>$heute</lastmod></url>\n";
        }
        file_put_contents("$aus/sitemap.xml", $xml . "</urlset>\n");
        file_put_contents("$aus/robots.txt", "User-agent: *\nDisallow: /verwaltung/\nDisallow: /api/\nDisallow: /status/\n\nSitemap: {$f['url']}/sitemap.xml\n");
        @mkdir("$aus/verwaltung", 0755, true);
        verwaltungSchreiben($wurzel, $aus, $kopfzeilen, $f);
    }
    echo "$ziel: " . count($seiten) . " Seiten\n";
}
