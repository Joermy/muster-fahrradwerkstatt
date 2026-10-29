# Startseite „real life“: Recherche, Entscheidung, Plan

Stand: 29.10.2026 · betrifft die 3D-Werkstatt auf der Startseite (`vorlagen/seiten/start.html`, `public/assets/js/rad/`, `scripts/modell-bauen.py`)

## 1. Ausgangslage: warum es nach 2010 aussieht

Gemessen an Screenshots der Vorführfassung (Chromium, Stufe 2) und an einem Cycles-Testrender desselben Modells.

**Das Fahrrad selbst ist ein Rad von 2010–2015.**

- Akku als eigener Kasten unter dem Unterrohr, mit LED-Leiste – heute steckt er unsichtbar im dicken Unterrohr.
- Züge und Leitungen hängen in Bögen vor dem Lenker und laufen außen am Rahmen – heute laufen sie durch den Steuersatz innen.
- Display als Kästchen auf dem Lenker, Lampe am Vorbau, runde Standardrohre, 27,5"-Räder mit schmalen Reifen, kleine Bremsscheiben.
- Hardtail mit steilem Lenkwinkel (69,5°) – aktuelle E-MTBs fahren 63,5–65° Lenkwinkel, 76–77° Sitzwinkel, 445–450 mm Kettenstreben, 29 × 2,5" Reifen ([Orbea Wild 2025][orbea], [Cube Stereo Hybrid One77][cube], [Cannondale Moterra SL][moterra]).
- Schaltwerk mit Schaltauge – aktuell ist die hängerlose Montage direkt an der Achse ([SRAM T-Type][ttype]).
- Montageständer als rotes Dreibein aus dünnen Rohren – Werkstattständer stehen auf einem schweren Stahlteller (28–36 kg) mit Klemmkopf ([Unior][unior], [Park Tool][park]).

**Die Umgebung ist eine Kulisse, kein Raum.** Ein schwarzer Kasten mit drei Flächen: Lochwand und Beton als Canvas-Rauschen, Werkzeug als flache Extrusionen, gelbe Bodenlinien, ein harter Spot im Dunkeln. Kein Fenster, kein Tageslicht, keine Wandstruktur, nichts, was ein Mensch in einer Werkstatt erwarten würde.

**Das Licht ist ausgedacht.** Spiegelungen kommen aus einer künstlichen Umgebung aus ein paar leuchtenden Rechtecken, nicht aus dem Raum, in dem das Rad steht. Es gibt keine indirekte Beleuchtung, also auch keine weichen Schatten in Ecken und unter Teilen. Genau das ist der Hauptgrund für den „Computerspiel“-Eindruck: Rasterisierung kann globale Beleuchtung nur annähern ([Lin et al. 2024][pbrwebgpu], [Chalmers 2018][chalmers]).

**Materialien sind zu sauber.** Jede Fläche ist eine Farbe mit einem Glanzwert. Keine Fasen an Kanten, keine Gebrauchsspuren, keine Beschriftung auf Reifen und Rahmen. Praktiker nennen genau diese Punkte als Verräter: rasiermesserscharfe Kanten, fehlende Fertigungsspuren, nichts zum Spiegeln ([Will Gibbons][gibbons], [Solid Solutions][visualize], [Blender Artists][ba-style]).

**Technik:** Speichen sind dünner als ein Pixel und flimmern als gepunktete Linien; Reifenflanken-Beschriftung liegt außerhalb der UV-Fläche und ist nie zu sehen.

## 2. Was „real life“ technisch verlangt

| Merkmal | warum | wie |
| --- | --- | --- |
| Globale Beleuchtung | Licht prallt von Boden, Wänden, Holz ab und färbt das Rad – ohne das wirkt alles aufgeklebt | Pfadverfolgung (Cycles) |
| Ein echter Raum mit Lichtquellen | Lack und Chrom brauchen etwas, das sie spiegeln | Werkstatt komplett modellieren, Fenster mit Tageslicht, Pendelleuchte, Lichtbänder |
| Kamera wie ein Fotograf | Brennweite, Schärfentiefe, Vignette, Korn | Blender-Kamera mit echten Blendenwerten, leichte Objektivfehler |
| Fasen und Fertigungsspuren | Kanten fangen Licht | Fasen an allen Teilen, Schweißnähte oder Carbon-Übergänge |
| Beschriftung, Gebrauch, Staub | echte Dinge sind benutzt | Reifenflanken mit Prägung, Rahmendekor, Staub in Profil und Ecken, Kratzer an Kanten |
| Farbmanagement | Filmischer Kontrast statt flacher Sättigung | AgX mit Kontrast-Look, wie im Produktfoto |

## 3. Optionen

| | A: Echtzeit-WebGL verbessern | B: Pfadverfolgte Bildfolge (Cycles), per Scrollen abgespielt | C: Echtzeit mit gebackenem Licht |
| --- | --- | --- | --- |
| Realismus | mittel – Echtzeit-Licht bleibt Annäherung | **fotoreal** – jedes Bild voll pfadverfolgt, mit Schärfentiefe und weichen Schatten | gut für die Werkstatt, das Rad bleibt Echtzeit |
| Speichen, Kette | flimmern | sauber, weil jedes Pixel hunderte Strahlen bekommt | flimmern |
| Handy | schwer (WebGL, Shader-Kompilierung, Hitze) | leicht: Bilder in ein Canvas zeichnen | mittel |
| Ladegröße | ~2 MB + Three.js | 12–20 MB Bilder (Desktop), 6–8 MB (Handy), stufenweise geladen | 5–8 MB |
| Interaktion | Drehen, Antippen | Antippen über Markierungen (Lage pro Bild vorberechnet), kein freies Drehen | Drehen, Antippen |
| Aufwand | gering | hoch: Modell, Raum, Animation, Rendern (Stunden) | mittel |

Bildfolgen statt Video, weil Video-Scrubben ruckelt: Browser springen nur zu Schlüsselbildern, und das Suchen ist asynchron ([CSS-Tricks][csstricks], [hontran][hontran], [Maglr][maglr]). Bildfolgen, die im Canvas gezeichnet werden, sind die übliche Lösung für fotoreale Scroll-Strecken; WebP statt PNG spart dabei ein Vielfaches ([GSAP-Forum][gsap]).

**Entscheidung: B.** Nur Pfadverfolgung liefert „real life“. Die Interaktion bleibt über Markierungen und die Knöpfe unter dem Rad erhalten; das freie Drehen mit der Maus entfällt. Three.js fliegt ganz raus – die Seite wird auf dem Handy leichter, nicht schwerer.

## 4. Konzept

### 4.1 Das Rad: ein E-MTB von 2026

Kein Markenrad, keine echten Logos. Name auf dem Rahmen: **„TRAIL·E 9“** (erfunden).

- **Rahmen:** Vollgefedert, vier Gelenke (Horst-Link), Carbon-Optik: Rohre werden zu einem Körper verschmolzen (Voxel-Remesh + Glätten), ohne sichtbare Nähte. Dickes Unterrohr mit integriertem Akku (800 Wh, nach unten entnehmbar, Deckel mit Schloss), Display im Oberrohr, Ladebuchse mit Gummikappe, Kettenstrebenschutz.
- **Geometrie (Größe L):** Lenkwinkel 64,5°, Sitzwinkel 76,5°, Reach ~480 mm, Kettenstreben 448 mm, Radstand ~1250 mm, 29" vorn und hinten.
- **Antrieb:** kompakter Mittelmotor mit Motorschutz, 34er Kettenblatt, 12-fach-Kassette 10–52, Schaltwerk direkt an der Achse (ohne Schaltauge), kabellos.
- **Fahrwerk:** Federgabel 160 mm mit Standrohren in Bronze, Dämpfer mit Ausgleichsbehälter, Steckachsen.
- **Bremsen:** Vierkolben-Sättel, Scheiben 220/203 mm mit Ausfräsungen und Schleifspuren.
- **Laufräder:** Alu-Felgen 30 mm innen, 32 Speichen schwarz, Reifen 29 × 2,5" mit echtem Stollenprofil (Mittelstollen mit Rampen, Übergangs- und Schulterstollen), Flankenprägung „TRAILGRIP 29 × 2.50 · 63-622 · E-25“.
- **Cockpit:** Lenker 780 mm mit 25 mm Rise, kurzer Vorbau, Lock-on-Griffe mit Profil, Fernbedienung statt Lenker-Display, Leitungen verschwinden im Steuersatz, Vario-Sattelstütze.
- **Oberflächen:** Lack seidenmatt in tiefem Petrol (Hausfarbe der Werkstatt), Logos glänzend; Alu-Teile schwarz eloxiert mit hellen Kanten; leichter Staub an Reifen, Gabelfüßen, Kettenstreben – ein Kundenrad, kein Katalogfoto.

### 4.2 Die Werkstatt

Vorbilder: helle, aufgeräumte Werkstätten mit Beton, Holz, Aluminium und Stahl ([Siech Zürich][dezeen], [Pedal Dubai][pedal], [Twenty3C][retail]).

- **Raum:** 7 × 7 m, 3,6 m hoch. Boden geschliffener Beton mit Fugenschnitt, Kellenspuren, Ölflecken, Reifenabrieb. Rückwand Kalksandstein weiß gestrichen, Fensterwand mit Stahlsprossenfenstern (Tageslicht, Sonnenflecken auf dem Boden), rechte Wand verputzt mit petrolfarbenem Sockel, vorn ein Sektionaltor.
- **Arbeitsplatz:** Werkbank 3,9 m mit Schubladenschränken (anthrazit), Arbeitsplatte Eiche, Werkzeugwand aus Birke-Multiplex mit Schienen und Werkzeug in echten Formen, Regal mit Kartons, Zentrierständer mit Laufrad, Schraubstock, Laptop mit Diagnose-Software, Teileschalen, Tasse.
- **Rundum:** Schwerlastregal mit Reifen und Kisten, Laufräder an Wandhaken, Pinnwand mit Auftragszetteln, Werkzeugwagen, Standpumpe, Gummimatte unter dem Ständer, Kabeltrommel, Lappen, Mülleimer, Wanduhr.
- **Montageständer:** Stahlteller ⌀ 600 mm, Säule mit Schnellspanner, Drehkopf mit Rändelrad, Klemme mit Gummibacken an der Sattelstütze.

### 4.3 Licht und Kamera

- **Licht:** Tageslicht durchs Fensterband (Sonne + Himmel), drei LED-Lichtbänder an der Decke, Pendelleuchte über dem Montageplatz als Hauptlicht, warme Leuchte über der Werkbank.
- **Kamera:** die acht Einstellungen der bisherigen Regie (Ankunft, Diagnose, Zerlegen, Antrieb, Bremse, Laufrad, Akku, Übergabe) bleiben als Drehbuch, werden aber mit echten Brennweiten (35–85 mm), Blende f/2,8–f/5,6 und Fokus auf das jeweilige Bauteil umgesetzt.
- **Bildlook:** AgX mit Kontrast, leichte Vignette, minimale chromatische Aberration, feines Korn.

### 4.4 Die Geschichte bleibt

Alle sieben Schritte bleiben, nur echt gerendert:

1. **Diagnose** – Lichtvorhang tastet ab, Befunde erscheinen am Bauteil (Lage pro Bild vorberechnet)
2. **Zerlegen** – Laufräder, Antrieb, Cockpit, Akku lösen sich
3. **Antrieb** – Schaltwerk läuft durch alle Gänge, Kette mit echter Gliederzahl über Blatt, Ritzel, Röllchen
4. **Bremse** – Rad dreht (Bewegungsunschärfe), Scheibe glüht, läuft danach an
5. **Laufrad** – Seitenschlag, Speichenspannung als Farbkarte, dann zentriert
6. **Akku** – Akku gleitet nach unten aus dem Unterrohr, Display zeigt Kapazität
7. **Übergabe** – Licht an, Rad abholbereit

Die Anzeige-Werte (Gang, Temperatur, Drehzahl …) rechnet die Seite aus derselben Zeitleiste wie Blender, damit Bild und Zahlen zusammenpassen.

## 5. Technischer Plan

### 5.1 Pipeline

```
scripts/rad/          Rad als Modul (Geometrie, Materialien, Dekor)
scripts/werkstatt/    Raum, Möbel, Werkzeug, Licht
scripts/regie.py      Zeitleiste p = 0 … 8: Kamera, Zerlegen, Kette, Effekte
scripts/rendern.py    rendert Bild für Bild (fortsetzbar), entrauscht, schreibt Markierungen
scripts/kodieren.py   WebP in zwei Größen, Vorschaubilder, Manifest
```

- **Zeitleiste:** 32 Bilder je Kapitel, 8 Kapitel → 257 Bilder (`p = i / 32`).
- **Rendern:** Cycles CPU, 1600 × 900, adaptive Abtastung (Rauschschwelle 0,03, höchstens 96 Proben), OIDN mit Albedo und Normalen, feste Zufallssaat gegen Flimmern, Bewegungsunschärfe nur im Bremskapitel. Persistente Daten, damit die Szene nur einmal aufgebaut wird. Fortsetzbar: fertige Bilder werden übersprungen.
- **Vorher:** Probebilder aller acht Einstellungen in voller Qualität, prüfen, nachbessern, erst dann die ganze Folge.

### 5.2 Auf der Seite

- `<canvas>` zeichnet das Bild zur Scrollposition; ohne Ladebildschirm: sofort sichtbar ist das erste Bild (liegt im HTML), dann lädt jedes 8. Bild, danach jedes 4., 2., alle – Scrollen funktioniert vom ersten Moment an, wird nur feiner.
- Handy: eigene Folge in 960 × 540; `saveData` oder reduzierte Bewegung: nur die acht Schlüsselbilder, gewechselt pro Kapitel.
- Markierungen zum Antippen und Befunde: Bildschirmlage jedes Bauteils pro Bild als JSON aus Blender (`world_to_camera_view`).
- Three.js, GLB, Shader, Ladebalken und WebGL-Wächter entfallen.

### 5.3 Budgets

| | Desktop | Handy |
| --- | --- | --- |
| Bildgröße | 1600 × 900 | 960 × 540 |
| je Bild | ~60–80 KB WebP | ~25–35 KB |
| gesamt | ~16–20 MB, gestaffelt | ~7–9 MB |
| erstes Bild | ~120 KB, im HTML vorgeladen | ~50 KB |

## 6. Ablauf

1. ✅ Recherche, dieses Dokument
2. ✅ Rad neu: Geometrie 2026, Carbon-Rahmen, integrierter Akku, Cockpit, Reifenprofil, Dekor, neuer Montageständer (`scripts/szene/rad.py`)
3. ✅ Werkstatt: Raum, Kleinteile, Außenansicht, Lichtportal im Fenster (`scripts/szene/werkstatt.py`)
4. ✅ Materialien: Lack, Eloxal, Gummi mit Prägung, Staub, Glut, Speichenspannung (`scripts/szene/materialien.py`)
5. ✅ Licht, Kamera, Bildlook; Probebilder aller acht Einstellungen (`scripts/rendern.py --probe`)
6. ✅ Zeitleiste: Zerlegen, Kette, Bremse mit Bewegungsunschärfe, Laufrad, Akku, Licht (`scripts/szene/regie.py`)
7. Ganze Folge rendern (rund 2 Minuten je Bild auf vier Kernen, 193 Bilder)
8. ✅ Seite umbauen: Canvas-Spieler, Markierungen, Lademodus entfernt, Three.js entfernt
9. Prüfen (Desktop, Handy, ohne JS, reduzierte Bewegung), README

### Abweichungen vom Plan

- **24 statt 32 Bilder je Kapitel**, weil ein Bild rund zwei Minuten braucht; der Spieler blendet zwischen Nachbarbildern über.
- **1280 × 720 statt 1600 × 900** aus demselben Grund. Auf großen Bildschirmen wird leicht hochskaliert.
- **Kein Korn in der Nachbearbeitung:** Korn vergrößert jede WebP-Datei deutlich; Vignette, minimaler Farbsaum und etwas Schärfe bleiben.
- **Hochkant** zeigt die Seite das Bild in der oberen Hälfte, zentriert auf den Bildschwerpunkt jedes Bildes (`f` in `lagen.json`), statt eine eigene Hochkant-Folge zu rendern.

## 7. Risiken

- **Renderzeit:** 4 CPU-Kerne. Gegenmaßnahme: adaptive Abtastung, OIDN, fortsetzbares Rendern in Blöcken; notfalls 1440 × 810.
- **Flimmern zwischen Bildern** durch den Entrauscher: feste Saat, genug Proben, Bewegungsunschärfe nur, wo sie hingehört.
- **Ladegröße:** gestaffeltes Laden, Handy-Folge, Schlüsselbilder für `saveData`.
- **Keine fremden Assets erreichbar** (Poly Haven, ambientCG sind aus der Arbeitsumgebung gesperrt): alles wird prozedural in Blender gebaut – Lizenzfrage erledigt sich damit.

## Quellen

[orbea]: https://blisterreview.com/gear-reviews/2025-orbea-wild
[cube]: https://flowmountainbike.com/tests/cube-stereo-hybrid-one77-review-the-brands-new-long-travel-emtb-thats-hilariously-stable-in-the-roughest-terrain/
[moterra]: https://www.emtbforums.com/bike-finder/Cannondale/Moterra%20SL/2025
[ttype]: https://worldwidecyclery.com/products/sram-x0-eagle-t-type-axs-rear-derailleur-12-speed-52t-max-batterynot-included-wheel-axle-mount-aluminum-cage-black-silver
[unior]: https://uniortools.com/ar/product/1693BS-US-pro-repair-stand-with-single-clamp-manually-adjustable
[park]: https://www.parktool.com/en-int/blog/repair-help/repair-stand-comparison-guide
[pbrwebgpu]: https://arxiv.org/html/2407.19977v1
[chalmers]: https://odr.chalmers.se/handle/20.500.12380/256137?locale=en
[gibbons]: https://www.willgibbons.com/realistic-rendering/
[visualize]: https://www.solidsolutions.co.uk/3-Easy-Ways-to-Make-Your-Renders-More-Realistic-with-SOLIDWORKS-Visualize
[ba-style]: https://blenderartists.org/t/how-do-they-achieve-this-style/1615675
[csstricks]: https://css-tricks.com/?p=308477
[hontran]: https://www.hontran.dev/blog/scroll-scrubbed-video-stutters-fix
[maglr]: https://help.maglr.com/en/article/preparing-your-video-for-scrub-on-scroll-1o5jbvr/
[gsap]: https://gsap.com/community/forums/topic/31234-scrolltrigger-image-sequence-performance/
[dezeen]: https://www.dezeen.com/?p=1821305
[pedal]: https://design-middleeast.com/pedal-by-niu-is-a-unique-concept-bicycle-workshop-cum-coffee-bar-in-dubai/
[retail]: https://retail-focus.co.uk/?p=9022

- Orbea Wild 2025 (Geometrie): <https://blisterreview.com/gear-reviews/2025-orbea-wild>
- Cube Stereo Hybrid One77: <https://flowmountainbike.com/tests/cube-stereo-hybrid-one77-review-the-brands-new-long-travel-emtb-thats-hilariously-stable-in-the-roughest-terrain/>
- Cannondale Moterra SL 2025: <https://www.emtbforums.com/bike-finder/Cannondale/Moterra%20SL/2025>
- SRAM T-Type, hängerlose Montage: <https://worldwidecyclery.com/products/sram-x0-eagle-t-type-axs-rear-derailleur-12-speed-52t-max-batterynot-included-wheel-axle-mount-aluminum-cage-black-silver>
- Montageständer: <https://uniortools.com/ar/product/1693BS-US-pro-repair-stand-with-single-clamp-manually-adjustable>, <https://www.parktool.com/en-int/blog/repair-help/repair-stand-comparison-guide>
- Rasterisierung vs. Pfadverfolgung: <https://arxiv.org/html/2407.19977v1>, <https://odr.chalmers.se/handle/20.500.12380/256137?locale=en>
- Warum Renderings unecht wirken: <https://www.willgibbons.com/realistic-rendering/>, <https://www.solidsolutions.co.uk/3-Easy-Ways-to-Make-Your-Renders-More-Realistic-with-SOLIDWORKS-Visualize>, <https://blenderartists.org/t/how-do-they-achieve-this-style/1615675>
- Bildfolgen und Video-Scrubben: <https://css-tricks.com/?p=308477>, <https://www.hontran.dev/blog/scroll-scrubbed-video-stutters-fix>, <https://help.maglr.com/en/article/preparing-your-video-for-scrub-on-scroll-1o5jbvr/>, <https://gsap.com/community/forums/topic/31234-scrolltrigger-image-sequence-performance/>
- Flimmern beim Entrauschen: <https://devtalk.blender.org/t/taking-a-look-at-optix-7-3-temporal-denoising-for-cycles/18656/106>, <https://www.cgchannel.com/2026/01/open-image-denoise-3-will-support-temporal-denoising/>
- Werkstatt-Vorbilder: <https://www.dezeen.com/?p=1821305>, <https://design-middleeast.com/pedal-by-niu-is-a-unique-concept-bicycle-workshop-cum-coffee-bar-in-dubai/>, <https://retail-focus.co.uk/?p=9022>
- E-MTB 2026: <https://www.bike-magazin.de/en/bicycles/mountain-bike/top-10-the-most-exciting-e-mtb-innovations-for-2025/>, <https://upway.de/blogs/news/e-bike-trends-2026-was-sich-wirklich-durchsetzen-wird>
