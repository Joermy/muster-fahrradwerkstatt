import { api, ApiFehler, BASIS, VORFUEHRUNG } from "../api.js";
import { el, leeren, feldfehler } from "../dom.js";

export const zustand = {
  ich: null,
  csrf: "",
  katalog: null,
  letzteAnfrage: Date.now(),
};

export { el, leeren, feldfehler, VORFUEHRUNG, BASIS, ApiFehler };

export const ereignisse = new EventTarget();

export async function va(pfad, { methode = "GET", daten = null } = {}) {
  zustand.letzteAnfrage = Date.now();
  try {
    return await api("verwaltung/" + pfad, { methode, daten, csrf: methode === "GET" ? "" : zustand.csrf });
  } catch (f) {
    if (f instanceof ApiFehler && f.status === 401 && !pfad.startsWith("anmelden") && !pfad.startsWith("code")) {
      ereignisse.dispatchEvent(new CustomEvent("abgemeldet", { detail: "Die Sitzung ist abgelaufen. Bitte melden Sie sich neu an." }));
    } else if (f instanceof ApiFehler && f.status === 403 && f.kennung === "einrichtung_noetig") {
      ereignisse.dispatchEvent(new CustomEvent("einrichten"));
    } else if (f instanceof ApiFehler && f.status === 403 && f.kennung === "csrf") {
      ereignisse.dispatchEvent(new CustomEvent("abgemeldet", { detail: f.message }));
    }
    throw f;
  }
}

export const istInhaber = () => zustand.ich?.rolle === "inhaber";

export async function katalog() {
  if (!zustand.katalog) {
    const r = await fetch(new URL("assets/daten/leistungen.json", BASIS), { cache: "no-cache" });
    zustand.katalog = await r.json();
  }
  return zustand.katalog;
}

export const STATUS = {
  angefragt: { text: "Anfrage eingegangen", kurz: "Neu", art: "neu" },
  bestaetigt: { text: "Termin bestätigt", kurz: "Bestätigt", art: "geplant" },
  angenommen: { text: "Rad angenommen", kurz: "Angenommen", art: "werkstatt" },
  in_arbeit: { text: "In Arbeit", kurz: "In Arbeit", art: "werkstatt" },
  wartet_auf_freigabe: { text: "Wartet auf Freigabe", kurz: "Freigabe offen", art: "warten" },
  abholbereit: { text: "Abholbereit", kurz: "Abholbereit", art: "fertig" },
  abgeschlossen: { text: "Abgeholt", kurz: "Abgeholt", art: "ende" },
  storniert: { text: "Abgesagt", kurz: "Abgesagt", art: "aus" },
  nicht_erschienen: { text: "Nicht erschienen", kurz: "Nicht erschienen", art: "aus" },
};

const ZEICHEN = {
  neu: "M8 4.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6z",
  geplant: "M3 4h10v9H3zM3 7h10M6 2.5v3M10 2.5v3",
  werkstatt: "M10.5 2.5a3 3 0 0 0-3.6 3.9L2.8 10.5l2.7 2.7 4.1-4.1A3 3 0 0 0 13.5 5.5l-1.8 1.8-1.9-.6-.6-1.9z",
  warten: "M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM8 5v3.3l2.2 1.4",
  fertig: "M3 8.5l3.2 3.2L13 4.8",
  ende: "M3 8h10",
  aus: "M4 4l8 8M12 4l-8 8",
};

function zeichen(art) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("aria-hidden", "true");
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", ZEICHEN[art] || ZEICHEN.ende);
  p.setAttribute("fill", "none");
  p.setAttribute("stroke", "currentColor");
  p.setAttribute("stroke-width", "1.8");
  p.setAttribute("stroke-linecap", "round");
  p.setAttribute("stroke-linejoin", "round");
  svg.append(p);
  return svg;
}

export function statusMarke(status, lang = false) {
  const s = STATUS[status] || { text: status, kurz: status, art: "ende" };
  return el("span", { klasse: `marke marke--${s.art}` }, zeichen(s.art), el("span", { text: lang ? s.text : s.kurz }));
}

export function seitenkopf(titel, text = null, ...aktionen) {
  return el("div", { klasse: "vw-seitenkopf" },
    el("div", {}, el("h1", { text: titel, tabindex: "-1", daten: { titel: "" } }), text ? el("p", { text }) : null),
    aktionen.length ? el("div", { klasse: "vw-seitenkopf__aktionen" }, aktionen) : null,
  );
}

export function tafel(titel, ...inhalt) {
  const id = "t-" + Math.random().toString(36).slice(2, 9);
  return el("section", { klasse: "tafel", "aria-labelledby": id }, el("h2", { id, text: titel }), ...inhalt);
}

export function feld({ name, label, typ = "text", wert = "", hilfe = null, pflicht = false, freiwilligZeigen = true, attribute = {} }) {
  const id = "f-" + name.replace(/[^a-z0-9]/gi, "-") + "-" + Math.random().toString(36).slice(2, 6);
  const hilfeId = hilfe ? id + "-h" : null;
  const fehlerId = id + "-e";
  let eingabe;
  if (typ === "textarea") {
    eingabe = el("textarea", { id, name, required: pflicht, "aria-describedby": [hilfeId, fehlerId].filter(Boolean).join(" "), ...attribute });
    eingabe.value = wert;
  } else if (typ === "select") {
    const { optionen = [], ...rest } = attribute;
    eingabe = el("select", { id, name, required: pflicht, "aria-describedby": [hilfeId, fehlerId].filter(Boolean).join(" "), ...rest },
      optionen.map(([w, t]) => el("option", { value: w, text: t, selected: w === wert })));
  } else {
    eingabe = el("input", { id, name, type: typ, value: wert, required: pflicht, "aria-describedby": [hilfeId, fehlerId].filter(Boolean).join(" "), ...attribute });
  }
  return el("div", { klasse: "feld" },
    el("label", { for: id, text: label + (pflicht || !freiwilligZeigen ? "" : " (freiwillig)") }),
    hilfe ? el("p", { klasse: "hilfe", id: hilfeId, text: hilfe }) : null,
    eingabe,
    el("p", { klasse: "fehlertext", id: fehlerId, daten: { fehler: name } }),
  );
}

export async function absenden(formular, aufgabe) {
  const knopf = formular.querySelector("[type=submit]");
  const meldung = formular.querySelector("[data-formularmeldung]");
  if (knopf) knopf.disabled = true;
  if (meldung) {
    meldung.hidden = true;
    meldung.textContent = "";
  }
  try {
    feldfehler(formular, {});
    return await aufgabe();
  } catch (f) {
    if (f instanceof ApiFehler && Object.keys(f.felder).length) {
      feldfehler(formular, f.felder);
    }
    if (meldung) {
      meldung.hidden = false;
      meldung.textContent = f.message;
    } else {
      hinweis(f.message, "fehler");
    }
    return undefined;
  } finally {
    if (knopf) knopf.disabled = false;
  }
}

export function formularmeldung() {
  return el("div", { klasse: "meldung meldung--fehler", role: "alert", hidden: true, daten: { formularmeldung: "" } });
}

let hinweisZeit = 0;
export function hinweis(text, art = "gut") {
  const ziel = document.querySelector("[data-hinweis]");
  leeren(ziel).append(el("p", { klasse: `vw-hinweis__text vw-hinweis__text--${art}`, text }));
  ziel.classList.add("ist-sichtbar");
  clearTimeout(hinweisZeit);
  hinweisZeit = setTimeout(() => ziel.classList.remove("ist-sichtbar"), art === "fehler" ? 8000 : 4000);
}

export function rueckfrage({ titel, text, knopf, gefahr = false, eintippen = null, feldLabel = null }) {
  return new Promise((fertig) => {
    const eingabe = eintippen ? el("input", { type: "text", autocomplete: "off", spellcheck: "false", id: "rf-eingabe" }) : null;
    const bestaetigen = el("button", { klasse: `knopf ${gefahr ? "knopf--gefahr" : ""}`, type: "submit", value: "ja", text: knopf, disabled: !!eintippen });
    const dialog = el("dialog", { klasse: "vw-dialog", "aria-labelledby": "rf-titel" },
      el("form", { method: "dialog" },
        el("h2", { id: "rf-titel", text: titel }),
        ...(Array.isArray(text) ? text : [text]).map((t) => el("p", { text: t })),
        eingabe ? el("div", { klasse: "feld" }, el("label", { for: "rf-eingabe", text: feldLabel || `Zur Bestätigung „${eintippen}“ eintippen` }), eingabe) : null,
        el("div", { klasse: "vw-dialog__knoepfe" },
          el("button", { klasse: "knopf knopf--leise", type: "submit", value: "nein", text: "Abbrechen" }),
          bestaetigen,
        ),
      ),
    );
    if (eingabe) {
      eingabe.addEventListener("input", () => {
        bestaetigen.disabled = eingabe.value.trim() !== eintippen;
      });
    }
    dialog.addEventListener("close", () => {
      const ja = dialog.returnValue === "ja";
      dialog.remove();
      fertig(ja);
    });
    document.body.append(dialog);
    dialog.showModal();
    (eingabe || bestaetigen.previousElementSibling).focus();
  });
}

export function alsDatei(daten, name) {
  const blob = new Blob([JSON.stringify(daten, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function leer(text, ...aktion) {
  return el("div", { klasse: "vw-leer" }, el("p", { text }), ...aktion);
}

export function ladefehler(ziel, f) {
  leeren(ziel).append(el("div", { klasse: "meldung meldung--fehler", role: "alert" }, el("p", { text: f.message || "Laden fehlgeschlagen." })));
}

export const zahl = (n) => Number(n).toLocaleString("de-DE");
export const WOCHENTAGE = ["", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];
