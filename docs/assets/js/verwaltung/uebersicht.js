import { zustand, va, el, seitenkopf, tafel, statusMarke, leer, zahl } from "./gemeinsam.js";
import { zahlenAktualisieren } from "./app.js";

function begruessung() {
  const h = new Date().getHours();
  const name = zustand.ich.anzeigename.split(" ")[0];
  return (h < 11 ? "Guten Morgen, " : h < 18 ? "Guten Tag, " : "Guten Abend, ") + name;
}

const tagKurz = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" });

function kachel({ titel, wert, href, hinweis = null, betont = false }) {
  return el("a", { klasse: `kachel${betont ? " kachel--betont" : ""}`, href },
    el("span", { klasse: "kachel__titel", text: titel }),
    el("span", { klasse: "kachel__wert zahl", text: zahl(wert) }),
    hinweis ? el("span", { klasse: "kachel__hinweis", text: hinweis }) : null,
  );
}

export async function ansicht(_weg, ziel) {
  const u = (await zahlenAktualisieren()) || (await va("uebersicht"));
  const z = u.zahlen;
  const heute = new Date().toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  ziel.append(
    seitenkopf(begruessung(), heute, el("a", { klasse: "knopf", href: "#neu", text: "Anfrage eintragen" })),
    el("div", { klasse: "kacheln" },
      kachel({ titel: "Neue Anfragen", wert: z.angefragt, href: "#auftraege?status=angefragt", hinweis: z.angefragt ? "Termin bestätigen" : "Alles beantwortet", betont: z.angefragt > 0 }),
      kachel({ titel: "Bestätigte Termine", wert: z.bestaetigt, href: "#auftraege?status=bestaetigt" }),
      kachel({ titel: "Räder in der Werkstatt", wert: z.in_werkstatt, href: "#auftraege?offen=1" }),
      kachel({ titel: "Abholbereit", wert: z.abholbereit, href: "#auftraege?status=abholbereit" }),
      kachel({ titel: "Offene Widerrufe", wert: z.widerrufe_offen, href: "#widerrufe", hinweis: z.widerrufe_offen ? "Bitte bearbeiten" : null, betont: z.widerrufe_offen > 0 }),
    ),
  );

  const zeile = (a, mitTag) => el("li", {},
    el("a", { href: `#auftrag/${a.id}` },
      el("span", { klasse: "tagesliste__zeit zahl" }, mitTag ? el("small", { text: tagKurz(a.termin_datum) }) : null, el("span", { text: a.termin_zeit })),
      el("span", { klasse: "tagesliste__wer" }, el("strong", { text: a.name || "Personendaten gelöscht" }), el("span", { text: a.leistung_text })),
      el("span", { klasse: "tagesliste__nummer zahl", text: a.nummer }),
      statusMarke(a.status),
    ));

  const heuteSortiert = [...u.heute].sort((a, b) => a.termin_zeit.localeCompare(b.termin_zeit));
  const termine = heuteSortiert.length
    ? el("ol", { klasse: "tagesliste" }, heuteSortiert.map((a) => zeile(a, false)))
    : leer("Heute stehen keine Termine im Kalender.");
  const demnaechst = u.demnaechst.length
    ? el("ol", { klasse: "tagesliste tagesliste--tage" }, u.demnaechst.map((a) => zeile(a, true)))
    : leer("In den nächsten sieben Tagen ist nichts eingetragen.");

  ziel.append(
    el("div", { klasse: "raster-2" },
      tafel("Termine heute", termine),
      tafel("Die nächsten sieben Tage", demnaechst, el("p", { klasse: "vw-still vw-tafelfuss" }, el("a", { href: "#kalender", text: "Belegung und Wochenplan ansehen" }))),
    ),
  );
}
