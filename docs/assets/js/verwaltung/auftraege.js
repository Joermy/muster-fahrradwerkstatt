import {
  va, el, leeren, seitenkopf, tafel, feld, absenden, formularmeldung, hinweis, rueckfrage,
  statusMarke, STATUS, leer, istInhaber, alsDatei, katalog, WOCHENTAGE, ereignisse,
} from "./gemeinsam.js";
import { api } from "../api.js";
import { euro, datum, zeitpunkt } from "../dom.js";

export async function ansicht(weg, ziel, kontext) {
  if (weg === "neu") return neu(ziel);
  if (weg === "auftrag") return detail(ziel, Number(kontext.teile[0]));
  return liste(ziel, kontext);
}

const FILTER = [
  ["offen", "Alle offenen"],
  ["angefragt", "Neue Anfragen"],
  ["bestaetigt", "Termin bestätigt"],
  ["angenommen", "Rad angenommen"],
  ["in_arbeit", "In Arbeit"],
  ["wartet_auf_freigabe", "Wartet auf Freigabe"],
  ["abholbereit", "Abholbereit"],
  ["abgeschlossen", "Abgeholt"],
  ["storniert", "Abgesagt"],
  ["nicht_erschienen", "Nicht erschienen"],
  ["alle", "Alle"],
];

async function liste(ziel, { abfrage }) {
  const status = abfrage.get("status");
  const suche = (abfrage.get("suche") || "").toUpperCase();
  const auswahl = status && STATUS[status] ? status : abfrage.get("alle") === "1" ? "alle" : "offen";
  const q = new URLSearchParams();
  if (auswahl === "offen") q.set("offen", "1");
  else if (auswahl !== "alle") q.set("status", auswahl);
  if (suche) q.set("suche", suche);
  const { auftraege } = await va("auftraege?" + q);

  const filter = el("form", { klasse: "vw-filter", role: "search", "aria-label": "Aufträge filtern" },
    feld({ name: "status", label: "Anzeigen", typ: "select", wert: auswahl, freiwilligZeigen: false, attribute: { optionen: FILTER } }),
    feld({ name: "suche", label: "Auftragsnummer", wert: suche, freiwilligZeigen: false, attribute: { placeholder: "RF-…", autocomplete: "off", spellcheck: "false", maxlength: "12", inputmode: "text" } }),
    el("button", { klasse: "knopf knopf--leise", type: "submit", text: "Filtern" }),
  );
  filter.status.addEventListener("change", () => filter.requestSubmit());
  filter.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = new URLSearchParams();
    const s = filter.status.value;
    if (s === "alle") p.set("alle", "1");
    else if (s !== "offen") p.set("status", s);
    const n = filter.suche.value.trim().toUpperCase();
    if (n) p.set("suche", n);
    location.hash = "auftraege" + (p.toString() ? "?" + p : "");
  });

  ziel.append(
    seitenkopf("Aufträge", `${auftraege.length} ${auftraege.length === 1 ? "Auftrag" : "Aufträge"} · sortiert nach Termin, neueste zuerst`, el("a", { klasse: "knopf", href: "#neu", text: "Anfrage eintragen" })),
    filter,
  );
  if (!auftraege.length) {
    ziel.append(leer(suche ? `Keine Aufträge mit der Nummer ${suche}.` : "Hier ist gerade nichts offen."));
    return;
  }
  ziel.append(el("div", { klasse: "tafel tafel--tabelle" },
    el("table", { klasse: "vw-tabelle vw-tabelle--auftraege" },
      el("caption", { klasse: "unsichtbar", text: "Aufträge" }),
      el("thead", {}, el("tr", {},
        el("th", { scope: "col", text: "Termin" }),
        el("th", { scope: "col", text: "Auftrag" }),
        el("th", { scope: "col", text: "Kundin / Kunde" }),
        el("th", { scope: "col", text: "Leistung" }),
        el("th", { scope: "col", text: "Stand" }),
      )),
      el("tbody", {}, auftraege.map((a) => el("tr", { klasse: a.status === "angefragt" ? "ist-neu" : null },
        el("td", { "data-titel": "Termin", klasse: "zahl" }, el("span", { text: datum(a.termin_datum, false) }), el("span", { klasse: "vw-tabelle__neben", text: a.termin_zeit + " Uhr" })),
        el("td", { "data-titel": "Auftrag" }, el("a", { klasse: "vw-nummer zahl", href: `#auftrag/${a.id}`, text: a.nummer })),
        el("td", { "data-titel": "Kundin / Kunde", text: a.name || "– gelöscht –" }),
        el("td", { "data-titel": "Leistung", text: a.leistung_text }),
        el("td", { "data-titel": "Stand" }, statusMarke(a.status), a.offene_angebote ? el("span", { klasse: "vw-tabelle__neben", text: "Kostenvoranschlag offen" }) : null),
      ))),
    ),
  ));
}

async function neu(ziel) {
  const [k, t] = await Promise.all([katalog(), api("termine")]);
  const tage = t.tage.filter((d) => d.zeiten.some((z) => z.frei > 0));
  const form = el("form", { klasse: "vw-formular vw-formular--breit", novalidate: true },
    formularmeldung(),
    el("fieldset", { klasse: "vw-gruppe" },
      el("legend", { text: "Auftrag" }),
      el("div", { klasse: "raster-2 raster-2--eng" },
        feld({ name: "leistung", label: "Leistung", typ: "select", pflicht: true, attribute: { optionen: k.leistungen.map((l) => [l.kennung, `${l.titel} (${euro(l.preis_cent)} ${l.einheit})`]) } }),
        feld({ name: "rad", label: "Rad", typ: "select", pflicht: true, attribute: { optionen: k.raeder.map((r) => [r.kennung, r.titel]) } }),
        feld({ name: "datum", label: "Tag", typ: "select", pflicht: true, attribute: { optionen: tage.map((d) => [d.datum, `${WOCHENTAGE[d.wochentag]}, ${datum(d.datum, false)}`]) } }),
        feld({ name: "zeit", label: "Uhrzeit", typ: "select", pflicht: true, attribute: { optionen: [] } }),
      ),
    ),
    el("fieldset", { klasse: "vw-gruppe" },
      el("legend", { text: "Kontakt" }),
      el("div", { klasse: "raster-2 raster-2--eng" },
        feld({ name: "name", label: "Name", pflicht: true, attribute: { autocomplete: "off", maxlength: "80" } }),
        feld({ name: "telefon", label: "Telefon", typ: "tel", attribute: { autocomplete: "off", maxlength: "30" } }),
        feld({ name: "email", label: "E-Mail", typ: "email", pflicht: true, hilfe: "Dorthin gehen Bestätigung, Status-Link und Kostenvoranschläge.", attribute: { autocomplete: "off", maxlength: "160" } }),
      ),
      feld({ name: "nachricht", label: "Was ist am Rad?", typ: "textarea", attribute: { maxlength: "1000", rows: "3" } }),
    ),
    el("div", { klasse: "meldung" }, el("p", { text: "Bitte am Telefon sagen: Wir speichern Name und Kontaktdaten verschlüsselt für diesen Auftrag und löschen sie nach den gesetzlichen Fristen. Mehr steht in der Datenschutzerklärung, die mit der Bestätigungsmail kommt." })),
    el("button", { klasse: "knopf", type: "submit", text: "Auftrag anlegen" }),
  );
  const zeitenFuellen = () => {
    const tag = tage.find((d) => d.datum === form.datum.value);
    leeren(form.zeit).append(...(tag ? tag.zeiten.filter((z) => z.frei > 0).map((z) => el("option", { value: z.zeit, text: `${z.zeit} Uhr (${z.frei} frei)` })) : []));
  };
  form.datum.addEventListener("change", zeitenFuellen);
  zeitenFuellen();

  ziel.append(seitenkopf("Anfrage eintragen", "Für Anfragen am Telefon oder am Tresen. Die Kundin oder der Kunde bekommt eine Mail mit dem Link zum Reparaturstatus; bestätigen Sie den Termin danach wie jede Anfrage."), el("div", { klasse: "tafel" }, form));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const wert = (n) => form[n].value.trim();
      const r = await va("auftraege", {
        methode: "POST",
        daten: { leistung: wert("leistung"), rad: wert("rad"), datum: wert("datum"), zeit: wert("zeit"), name: wert("name"), email: wert("email"), telefon: wert("telefon") || null, nachricht: wert("nachricht") || null },
      });
      hinweis(`Auftrag ${r.nummer} angelegt.`);
      ereignisse.dispatchEvent(new Event("zahlen"));
      const { auftraege } = await va("auftraege?suche=" + encodeURIComponent(r.nummer));
      location.hash = auftraege[0] ? `auftrag/${auftraege[0].id}` : "auftraege";
    });
  });
}

function aktionText(von, nach) {
  if (nach === "in_arbeit") return von === "wartet_auf_freigabe" ? "Ohne Freigabe weiterarbeiten" : von === "abholbereit" ? "Zurück in Arbeit" : "Arbeit beginnen";
  return {
    bestaetigt: "Termin bestätigen",
    storniert: "Termin absagen",
    angenommen: "Rad angenommen",
    nicht_erschienen: "Nicht erschienen",
    abholbereit: "Fertig, abholbereit melden",
    abgeschlossen: "Abgeholt, Auftrag schließen",
  }[nach] || nach;
}

const HINWEIS_MAIL = {
  bestaetigt: "Die Kundin oder der Kunde bekommt eine Bestätigung per Mail.",
  abholbereit: "Die Kundin oder der Kunde bekommt eine Mail, dass das Rad fertig ist.",
  storniert: "Die Kundin oder der Kunde bekommt eine Absage per Mail.",
};

async function detail(ziel, id) {
  if (!Number.isInteger(id) || id < 1) {
    location.hash = "auftraege";
    return;
  }
  zeichnen(ziel, await va(`auftraege/${id}`));
}

function zeichnen(ziel, a) {
  const neuZeichnen = (d) => {
    leeren(ziel);
    zeichnen(ziel, d);
    ziel.querySelector("h1")?.focus({ preventScroll: true });
  };
  const anonym = a.anonymisiert !== null;

  const anhaenger = el("div", { klasse: "anhaenger-karte" },
    el("span", { klasse: "anhaenger-karte__loch", "aria-hidden": "true" }),
    el("p", { klasse: "anhaenger-karte__nummer zahl", text: a.nummer }),
    el("p", { klasse: "anhaenger-karte__zeile" }, statusMarke(a.status, true)),
    el("dl", { klasse: "anhaenger-karte__daten" },
      el("dt", { text: "Leistung" }), el("dd", { text: a.leistung_text }),
      el("dt", { text: "Rad" }), el("dd", { text: a.rad_text }),
      el("dt", { text: "Termin" }), el("dd", { text: `${datum(a.termin_datum)}, ${a.termin_zeit} Uhr` }),
      el("dt", { text: "Angefragt" }), el("dd", { text: zeitpunkt(a.erstellt) }),
    ),
  );

  const aktionen = el("div", { klasse: "statuswechsel" });
  if (a.naechste.length && !anonym) {
    aktionen.append(
      el("h2", { text: "Nächster Schritt" }),
      el("div", { klasse: "statuswechsel__knoepfe" }, a.naechste.map((n) => el("button", {
        klasse: `knopf ${["storniert", "nicht_erschienen"].includes(n.status) ? "knopf--leise" : ""}`,
        type: "button",
        text: aktionText(a.status, n.status),
        onclick: () => statusDialog(a, n, neuZeichnen),
      }))),
    );
  } else if (!anonym) {
    aktionen.append(el("p", { klasse: "vw-still", text: a.status === "wartet_auf_freigabe" ? "Wartet auf die Entscheidung zum Kostenvoranschlag." : "Dieser Auftrag ist abgeschlossen." }));
  }
  if (a.status === "wartet_auf_freigabe" && a.naechste.length) {
    aktionen.append(el("p", { klasse: "vw-still", text: "Ohne Freigabe weiterarbeiten heißt: nur die ursprünglich beauftragte Leistung ausführen." }));
  }

  const kontakt = anonym
    ? tafel("Kontakt", el("p", { text: `Die Personendaten wurden am ${zeitpunkt(a.anonymisiert)} gelöscht. Leistung, Termin und Beträge bleiben für die Buchhaltung.` }))
    : tafel("Kontakt",
      el("dl", { klasse: "vw-daten" },
        el("dt", { text: "Name" }), el("dd", { text: a.name }),
        el("dt", { text: "E-Mail" }), el("dd", {}, el("a", { href: "mailto:" + a.email, text: a.email })),
        el("dt", { text: "Telefon" }), el("dd", {}, a.telefon ? el("a", { href: "tel:" + a.telefon.replace(/[^\d+]/g, ""), text: a.telefon }) : el("span", { klasse: "vw-still", text: "nicht angegeben" })),
      ),
      a.nachricht ? el("blockquote", { klasse: "vw-zitat" }, el("p", { text: a.nachricht })) : null,
    );

  const verlauf = tafel("Verlauf",
    el("ol", { klasse: "verlauf" }, a.verlauf.map((v) => el("li", {},
      el("strong", { text: v.text }),
      v.hinweis ? el("span", { text: " – " + v.hinweis }) : null,
      el("time", { datetime: v.zeit, text: zeitpunkt(v.zeit) }),
    ))),
  );

  const datenschutz = tafel("Daten dieses Auftrags",
    el("p", { text: anonym ? "Es sind keine Personendaten mehr gespeichert." : a.loeschung }),
    !anonym && istInhaber() ? el("div", { klasse: "vw-knopfreihe" },
      el("button", {
        klasse: "knopf knopf--leise", type: "button", text: "Auskunft herunterladen",
        onclick: async () => {
          try {
            alsDatei(await va(`auftraege/${a.id}/auskunft`), `auskunft-${a.nummer}.json`);
            hinweis("Auskunft erstellt. Bitte nur verschlüsselt weitergeben.");
          } catch (f) {
            hinweis(f.message, "fehler");
          }
        },
      }),
      el("button", {
        klasse: "knopf knopf--gefahr", type: "button", text: "Personendaten löschen",
        onclick: async () => {
          const ja = await rueckfrage({
            titel: "Personendaten löschen?",
            text: [
              "Name, E-Mail, Telefon, Nachricht, Hinweise und interne Notizen werden endgültig entfernt. Der Status-Link der Kundin oder des Kunden funktioniert danach nicht mehr.",
              "Leistung, Termin und Beträge bleiben ohne Personenbezug für die Buchhaltung. Das lässt sich nicht rückgängig machen.",
            ],
            knopf: "Endgültig löschen",
            gefahr: true,
            eintippen: a.nummer,
            feldLabel: `Zur Bestätigung die Auftragsnummer ${a.nummer} eintippen`,
          });
          if (!ja) return;
          try {
            neuZeichnen(await va(`auftraege/${a.id}/anonymisieren`, { methode: "POST", daten: { bestaetigung: a.nummer } }));
            hinweis("Personendaten gelöscht.");
          } catch (f) {
            hinweis(f.message, "fehler");
          }
        },
      }),
    ) : null,
    !anonym && !istInhaber() ? el("p", { klasse: "vw-still", text: "Auskunft und Löschung erledigt die Inhaberin." }) : null,
  );

  const widerrufe = a.widerrufe.length
    ? tafel("Widerruf eingegangen", el("ul", { klasse: "vw-liste" }, a.widerrufe.map((w) => el("li", {},
      el("strong", { klasse: "zahl", text: w.oeffentliche_id }),
      el("span", { text: ` vom ${zeitpunkt(w.eingang)} · ` }),
      el("span", { text: w.bearbeitet ? "bearbeitet" : "noch offen" }),
    ))), el("p", {}, el("a", { href: "#widerrufe", text: "Zu den Widerrufen" })))
    : null;

  ziel.append(
    el("p", { klasse: "vw-zurueck" }, el("a", { href: "#auftraege", text: "Alle Aufträge" })),
    seitenkopf(anonym ? `Auftrag ${a.nummer}` : a.name, `${a.leistung_text} · ${a.rad_text}`),
    el("div", { klasse: "detail" },
      el("div", { klasse: "detail__haupt" },
        el("div", { klasse: "detail__kopf" }, anhaenger, aktionen),
        angeboteTafel(a, neuZeichnen),
        anonym ? null : notizenTafel(a, neuZeichnen),
      ),
      el("div", { klasse: "detail__seite" }, kontakt, widerrufe, verlauf, datenschutz),
    ),
  );
}

function statusDialog(a, n, neuZeichnen) {
  const id = "sd-" + n.status;
  const hinweisFeld = el("textarea", { id, name: "hinweis", maxlength: "300", rows: "3" });
  const dialog = el("dialog", { klasse: "vw-dialog", "aria-labelledby": id + "-t" },
    el("form", { method: "dialog" },
      el("h2", { id: id + "-t", text: `${aktionText(a.status, n.status)}?` }),
      el("p", { text: `${a.nummer}: Stand ändert sich von „${STATUS[a.status]?.text || a.status}“ zu „${n.text}“.` }),
      HINWEIS_MAIL[n.status] ? el("p", { text: HINWEIS_MAIL[n.status] }) : null,
      el("div", { klasse: "feld" },
        el("label", { for: id, text: "Hinweis für die Kundin oder den Kunden (freiwillig)" }),
        el("p", { klasse: "hilfe", text: "Erscheint auf der Statusseite" + (HINWEIS_MAIL[n.status] ? " und in der Mail." : ".") }),
        hinweisFeld,
      ),
      el("div", { klasse: "vw-dialog__knoepfe" },
        el("button", { klasse: "knopf knopf--leise", type: "submit", value: "nein", text: "Abbrechen" }),
        el("button", { klasse: "knopf", type: "submit", value: "ja", text: aktionText(a.status, n.status) }),
      ),
    ),
  );
  dialog.addEventListener("close", async () => {
    const ja = dialog.returnValue === "ja";
    const text = hinweisFeld.value.trim();
    dialog.remove();
    if (!ja) return;
    try {
      neuZeichnen(await va(`auftraege/${a.id}/status`, { methode: "POST", daten: { status: n.status, hinweis: text || null } }));
      hinweis(`Neuer Stand: ${n.text}.`);
      ereignisse.dispatchEvent(new Event("zahlen"));
    } catch (f) {
      hinweis(f.message, "fehler");
    }
  });
  document.body.append(dialog);
  dialog.showModal();
}

function inCent(text) {
  const t = text.trim().replace(/\s|€/g, "");
  if (!/^\d{1,4}([.,]\d{1,2})?$/.test(t)) return null;
  const [ganz, rest = ""] = t.split(/[.,]/);
  return Number(ganz) * 100 + Number(rest.padEnd(2, "0"));
}

function angeboteTafel(a, neuZeichnen) {
  const teile = [];
  for (const g of a.angebote) {
    const entscheidung = g.entscheidung === "angenommen"
      ? `Freigegeben am ${zeitpunkt(g.entschieden)}${g.vorzeitiger_beginn ? ", sofortiger Beginn gewünscht" : ""}. ${g.widerrufbar ? `Widerruf möglich bis ${datum(g.widerruf_bis, false)}.` : "Widerrufsfrist abgelaufen."}`
      : g.entscheidung === "abgelehnt" ? `Abgelehnt am ${zeitpunkt(g.entschieden)}.` : "Wartet auf Antwort.";
    teile.push(el("div", { klasse: "angebot" },
      el("table", { klasse: "vw-tabelle vw-tabelle--angebot" },
        el("caption", { text: `Kostenvoranschlag vom ${zeitpunkt(g.erstellt)}` }),
        el("tbody", {}, g.positionen.map((p) => el("tr", {}, el("td", { text: p.text }), el("td", { klasse: "zahl", text: euro(p.cent) })))),
        el("tfoot", {}, el("tr", {}, el("th", { scope: "row", text: "Summe" }), el("td", { klasse: "zahl" }, el("strong", { text: euro(g.summe_cent) })))),
      ),
      el("p", { klasse: `angebot__stand angebot__stand--${g.entscheidung || "offen"}`, text: entscheidung }),
    ));
  }
  const moeglich = ["angenommen", "in_arbeit"].includes(a.status) && !a.angebote.some((g) => !g.entscheidung) && a.anonymisiert === null;
  if (moeglich) teile.push(angebotFormular(a, neuZeichnen));
  if (!teile.length) return null;
  return tafel("Kostenvoranschläge", ...teile);
}

function angebotFormular(a, neuZeichnen) {
  const zeilen = el("ol", { klasse: "positionen" });
  const summe = el("output", { klasse: "positionen__summe zahl", text: euro(0) });
  const rechnen = () => {
    let s = 0;
    for (const z of zeilen.querySelectorAll("li")) s += inCent(z.querySelector("[name=cent]").value) || 0;
    summe.textContent = euro(s);
  };
  const zeile = (text = "", cent = null) => {
    const nr = zeilen.children.length;
    if (nr >= 12) return;
    const li = el("li", { klasse: "positionen__zeile" },
      el("div", { klasse: "feld" }, el("label", { for: `p-text-${nr}`, text: "Position" }), el("input", { id: `p-text-${nr}`, name: "text", value: text, maxlength: "120", required: true, daten: { pos: nr } }), el("p", { klasse: "fehlertext", daten: { fehler: `positionen.${nr}.text` } })),
      el("div", { klasse: "feld feld--betrag" }, el("label", { for: `p-cent-${nr}`, text: "Betrag in Euro" }), el("input", { id: `p-cent-${nr}`, name: "cent", inputmode: "decimal", value: cent === null ? "" : (cent / 100).toFixed(2).replace(".", ","), required: true, autocomplete: "off" }), el("p", { klasse: "fehlertext", daten: { fehler: `positionen.${nr}.cent` } })),
      el("button", { klasse: "positionen__weg", type: "button", "aria-label": "Position entfernen", text: "Entfernen", onclick: () => { li.remove(); rechnen(); } }),
    );
    li.querySelector("[name=cent]").addEventListener("input", rechnen);
    zeilen.append(li);
    rechnen();
  };
  zeile();

  const vorlage = el("select", { id: "pos-vorlage", "aria-describedby": "pos-vorlage-h" }, el("option", { value: "", text: "Position aus der Preisliste …" }));
  katalog().then((k) => {
    for (const l of k.leistungen) vorlage.append(el("option", { value: l.kennung, text: `${l.titel} – ${euro(l.preis_cent)} ${l.einheit}` }));
    vorlage.addEventListener("change", () => {
      const l = k.leistungen.find((x) => x.kennung === vorlage.value);
      if (!l) return;
      const leer = [...zeilen.querySelectorAll("li")].find((z) => !z.querySelector("[name=text]").value && !z.querySelector("[name=cent]").value);
      if (leer) leer.remove();
      zeile(`${l.titel} (${l.einheit})`, l.preis_cent);
      vorlage.value = "";
    });
  });

  const form = el("form", { klasse: "vw-formular angebot-formular", novalidate: true },
    el("h3", { text: "Neuer Kostenvoranschlag" }),
    el("p", { klasse: "vw-still", text: "Für Arbeiten über den beauftragten Umfang hinaus. Die Kundin oder der Kunde bekommt ihn per Mail und gibt ihn online frei oder lehnt ab. Preise inklusive Umsatzsteuer." }),
    formularmeldung(),
    zeilen,
    el("div", { klasse: "positionen__fuss" },
      el("button", { klasse: "knopf knopf--leise", type: "button", text: "Position hinzufügen", onclick: () => zeile() }),
      el("div", { klasse: "feld feld--inline" }, el("label", { for: "pos-vorlage", klasse: "unsichtbar", text: "Position aus der Preisliste übernehmen" }), vorlage),
      el("p", { klasse: "positionen__gesamt" }, el("span", { text: "Summe " }), summe),
    ),
    el("button", { klasse: "knopf", type: "submit", text: "Kostenvoranschlag senden" }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const positionen = [];
    const fehler = {};
    [...zeilen.querySelectorAll("li")].forEach((z, i) => {
      const text = z.querySelector("[name=text]").value.trim();
      const cent = inCent(z.querySelector("[name=cent]").value);
      if (text.length < 2) fehler[`positionen.${i}.text`] = "Bitte beschreiben.";
      if (cent === null) fehler[`positionen.${i}.cent`] = "Betrag wie 49,80 eingeben.";
      positionen.push({ text, cent: cent ?? 0 });
    });
    for (const p of zeilen.querySelectorAll("[data-fehler]")) p.textContent = "";
    if (Object.keys(fehler).length || !positionen.length) {
      for (const [k, m] of Object.entries(fehler)) {
        const p = zeilen.querySelector(`[data-fehler="${CSS.escape(k)}"]`);
        if (p) p.textContent = m;
      }
      zeilen.querySelector("[data-fehler]:not(:empty)")?.parentElement.querySelector("input")?.focus();
      return;
    }
    absenden(form, async () => {
      const ok = await rueckfrage({
        titel: "Kostenvoranschlag senden?",
        text: `${positionen.length} ${positionen.length === 1 ? "Position" : "Positionen"}, zusammen ${euro(positionen.reduce((s, p) => s + p.cent, 0))}. Der Auftrag wartet danach auf die Freigabe.`,
        knopf: "Senden",
      });
      if (!ok) return;
      neuZeichnen(await va(`auftraege/${a.id}/angebot`, { methode: "POST", daten: { positionen } }));
      hinweis("Kostenvoranschlag gesendet.");
    });
  });
  return form;
}

function notizenTafel(a, neuZeichnen) {
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    feld({ name: "text", label: "Neue Notiz", typ: "textarea", pflicht: true, hilfe: "Nur für das Team. Wird verschlüsselt gespeichert und mit den Kontaktdaten gelöscht.", attribute: { maxlength: "2000", rows: "3" } }),
    el("button", { klasse: "knopf knopf--leise", type: "submit", text: "Notiz speichern" }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      neuZeichnen(await va(`auftraege/${a.id}/notiz`, { methode: "POST", daten: { text: form.text.value.trim() } }));
      hinweis("Notiz gespeichert.");
    });
  });
  return tafel("Interne Notizen",
    a.notizen.length
      ? el("ol", { klasse: "notizen" }, a.notizen.map((n) => el("li", {},
        el("p", { klasse: "notizen__text", text: n.text }),
        el("p", { klasse: "notizen__von", text: `${n.von || "Unbekannt"}, ${zeitpunkt(n.zeit)}` }),
      )))
      : null,
    form,
  );
}

