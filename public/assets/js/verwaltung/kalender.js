import { va, el, leeren, seitenkopf, tafel, absenden, formularmeldung, hinweis, istInhaber, WOCHENTAGE, feldfehler } from "./gemeinsam.js";
import { datum } from "../dom.js";

export async function ansicht(_weg, ziel) {
  const k = await va("kapazitaet");
  zeichnen(ziel, k);
}

function zeichnen(ziel, k) {
  leeren(ziel).append(
    seitenkopf("Termine und Kapazität", "So viele Räder nimmt die Werkstatt je Zeitfenster an. Online buchbar ist ab morgen bis vier Wochen im Voraus."),
    belegung(k),
    istInhaber() ? planFormular(ziel, k) : planLesen(k),
  );
}

function belegung(k) {
  const wochen = [];
  let woche = [];
  const erster = k.tage[0];
  for (let i = 1; i < (erster?.wochentag || 1); i++) woche.push(null);
  for (const t of k.tage) {
    woche.push(t);
    if (woche.length === 7) {
      wochen.push(woche);
      woche = [];
    }
  }
  if (woche.length) {
    while (woche.length < 7) woche.push(null);
    wochen.push(woche);
  }
  let frei = 0;
  let gesamt = 0;
  const tabelle = el("table", { klasse: "belegung" },
    el("caption", { klasse: "unsichtbar", text: "Belegung der nächsten vier Wochen" }),
    el("thead", {}, el("tr", {}, WOCHENTAGE.slice(1).map((w) => el("th", { scope: "col", text: w.slice(0, 2) })))),
    el("tbody", {}, wochen.map((w) => el("tr", {}, w.map((t) => {
      if (!t) return el("td", { klasse: "belegung__leer" });
      const plaetze = k.plan[t.wochentag]?.plaetze || 0;
      const kopf = el("p", { klasse: "belegung__tag zahl", text: datum(t.datum, false).slice(0, 6) });
      if (t.grund || !t.zeiten.length) {
        return el("td", { klasse: "belegung__zu" }, kopf, el("p", { klasse: "belegung__grund", text: t.grund || "geschlossen" }));
      }
      return el("td", {}, kopf, el("ul", { klasse: "belegung__zeiten" }, t.zeiten.map((z) => {
        const belegt = Math.max(0, plaetze - z.frei);
        frei += z.frei;
        gesamt += plaetze;
        return el("li", { "aria-label": `${z.zeit} Uhr: ${belegt} von ${plaetze} belegt` },
          el("span", { klasse: "belegung__zeit zahl", "aria-hidden": "true", text: z.zeit }),
          el("span", { klasse: "belegung__plaetze", "aria-hidden": "true" }, Array.from({ length: plaetze }, (_, i) => el("span", { klasse: i < belegt ? "ist-belegt" : null }))),
        );
      })));
    })))),
  );
  return tafel("Belegung der nächsten vier Wochen",
    el("p", { klasse: "vw-still", text: `${frei} von ${gesamt} Plätzen frei. Gefüllte Kästchen sind vergebene Plätze.` }),
    el("div", { klasse: "belegung__huelle" }, tabelle),
  );
}

function planLesen(k) {
  return tafel("Wochenplan",
    el("table", { klasse: "vw-tabelle" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Tag" }), el("th", { scope: "col", text: "Zeiten" }), el("th", { scope: "col", klasse: "zahl", text: "Räder je Zeit" }))),
      el("tbody", {}, [1, 2, 3, 4, 5, 6, 7].map((t) => el("tr", {},
        el("th", { scope: "row", text: WOCHENTAGE[t] }),
        el("td", { text: k.plan[t]?.zeiten?.join(", ") || "geschlossen" }),
        el("td", { klasse: "zahl", text: String(k.plan[t]?.plaetze ?? 0) }),
      ))),
    ),
    el("h3", { text: "Schließtage" }),
    k.sperrtage.length
      ? el("ul", { klasse: "vw-liste" }, k.sperrtage.map((s) => el("li", { text: `${datum(s.datum)}: ${s.grund}` })))
      : el("p", { klasse: "vw-still", text: "Keine. Gesetzliche Feiertage in Niedersachsen sind automatisch gesperrt." }),
    el("p", { klasse: "vw-still", text: "Änderungen am Plan nimmt die Inhaberin vor." }),
  );
}

function planFormular(ziel, k) {
  const zeilen = [1, 2, 3, 4, 5, 6, 7].map((t) => el("tr", {},
    el("th", { scope: "row", text: WOCHENTAGE[t] }),
    el("td", {}, el("label", { klasse: "unsichtbar", for: `zeiten-${t}`, text: `Zeiten am ${WOCHENTAGE[t]}` }),
      el("input", { id: `zeiten-${t}`, name: `zeiten-${t}`, value: (k.plan[t]?.zeiten || []).join(", "), autocomplete: "off", spellcheck: "false", "aria-describedby": "zeiten-hilfe", inputmode: "numeric" }),
      el("p", { klasse: "fehlertext", daten: { fehler: `zeiten-${t}` } })),
    el("td", {}, el("label", { klasse: "unsichtbar", for: `plaetze-${t}`, text: `Räder je Zeit am ${WOCHENTAGE[t]}` }),
      el("input", { id: `plaetze-${t}`, name: `plaetze-${t}`, type: "number", min: "0", max: "20", value: String(k.plan[t]?.plaetze ?? 0), klasse: "zahl" })),
  ));
  const sperrListe = el("ul", { klasse: "sperrtage" });
  const sperrZeile = (d = "", g = "") => {
    const li = el("li", {},
      el("input", { type: "date", name: "sperr-datum", value: d, "aria-label": "Datum", min: new Date().toISOString().slice(0, 10) }),
      el("input", { name: "sperr-grund", value: g, maxlength: "60", "aria-label": "Grund, erscheint bei der Terminwahl", placeholder: "Grund, z. B. Betriebsurlaub" }),
      el("button", { klasse: "positionen__weg", type: "button", text: "Entfernen", onclick: () => li.remove() }),
    );
    sperrListe.append(li);
  };
  for (const s of k.sperrtage) sperrZeile(s.datum, s.grund);

  const form = el("form", { klasse: "vw-formular vw-formular--breit", novalidate: true },
    formularmeldung(),
    el("p", { klasse: "hilfe", id: "zeiten-hilfe", text: "Zeiten mit Komma trennen, zum Beispiel 08:30, 10:00. Leer lassen oder 0 Räder heißt: an diesem Tag geschlossen. Bereits gebuchte Termine bleiben bestehen." }),
    el("table", { klasse: "vw-tabelle plan" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Tag" }), el("th", { scope: "col", text: "Zeiten" }), el("th", { scope: "col", text: "Räder je Zeit" }))),
      el("tbody", {}, zeilen),
    ),
    el("h3", { text: "Schließtage" }),
    el("p", { klasse: "vw-still", text: "Gesetzliche Feiertage in Niedersachsen sind automatisch gesperrt." }),
    sperrListe,
    el("p", {}, el("button", { klasse: "knopf knopf--leise", type: "button", text: "Schließtag hinzufügen", onclick: () => sperrZeile() })),
    el("button", { klasse: "knopf", type: "submit", text: "Plan speichern" }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const plan = {};
    const fehler = {};
    for (let t = 1; t <= 7; t++) {
      const zeiten = form[`zeiten-${t}`].value.split(/[,;\s]+/).filter(Boolean).map((z) => (/^\d:\d\d$/.test(z) ? "0" + z : z));
      if (zeiten.some((z) => !/^([01]\d|2[0-3]):[0-5]\d$/.test(z))) fehler[`zeiten-${t}`] = "Format HH:MM, zum Beispiel 08:30.";
      if (zeiten.length > 16) fehler[`zeiten-${t}`] = "Höchstens 16 Zeiten.";
      plan[t] = { zeiten, plaetze: Math.max(0, Math.min(20, Number(form[`plaetze-${t}`].value) || 0)) };
    }
    if (Object.keys(fehler).length) {
      feldfehler(form, fehler);
      return;
    }
    const sperrtage = [...sperrListe.querySelectorAll("li")]
      .map((li) => ({ datum: li.querySelector("[name=sperr-datum]").value, grund: li.querySelector("[name=sperr-grund]").value.trim() || "Geschlossen" }))
      .filter((s) => s.datum);
    absenden(form, async () => {
      zeichnen(ziel, await va("kapazitaet", { methode: "POST", daten: { plan, sperrtage } }));
      hinweis("Plan gespeichert.");
    });
  });
  return tafel("Wochenplan", form);
}
