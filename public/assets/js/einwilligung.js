import { api } from "./api.js";
import { el } from "./dom.js";

export const FASSUNG = "2026-10";
const SCHLUESSEL = "rh_einwilligung";

function lesen() {
  try {
    const w = JSON.parse(localStorage.getItem(SCHLUESSEL) || "null");
    return w && w.fassung === FASSUNG ? w : null;
  } catch (e) {
    return null;
  }
}

function kennung() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

let stand = lesen();
const hoerer = new Set();

export function zustand() {
  return stand;
}

export function erlaubt(zweck) {
  return !!(stand && stand[zweck]);
}

export function beobachten(f) {
  hoerer.add(f);
  return () => hoerer.delete(f);
}

export function speichern(medien) {
  stand = { id: stand?.id || kennung(), fassung: FASSUNG, medien: !!medien, zeit: new Date().toISOString() };
  try {
    localStorage.setItem(SCHLUESSEL, JSON.stringify(stand));
  } catch (e) {
  }
  api("einwilligung", { methode: "POST", daten: { id: stand.id, fassung: FASSUNG, medien: stand.medien } }).catch(() => {});
  for (const f of hoerer) f(stand);
  return stand;
}

let fenster = null;
let vorherFokus = null;

function schliessen() {
  if (!fenster) return;
  fenster.remove();
  fenster = null;
  if (vorherFokus && document.contains(vorherFokus)) vorherFokus.focus();
}

export function oeffnen({ fokus = false } = {}) {
  if (fenster) schliessen();
  vorherFokus = document.activeElement;
  const datenschutz = new URL("datenschutz/", new URL(document.documentElement.dataset.basis || "./", location.href)).href;
  const aktuell = stand ? (stand.medien ? "Zurzeit erlaubt." : "Zurzeit abgelehnt.") : null;

  fenster = el("section", { klasse: "einwilligung", role: "region", "aria-labelledby": "ew-titel" },
    el("h2", { id: "ew-titel", text: "Karten von OpenStreetMap laden?" }),
    el("p", {}, "Diese Website zählt keine Besuche und setzt keine Werbe-Cookies. Auf der Kontaktseite können wir eine Karte von OpenStreetMap zeigen; dabei geht Ihre IP-Adresse an die OpenStreetMap Foundation im Vereinigten Königreich. Ohne Zustimmung lädt die Karte erst, wenn Sie sie anklicken. Ändern können Sie das jederzeit unter „Cookie-Einstellungen“ unten auf jeder Seite. ",
      el("a", { href: datenschutz + "#einwilligung", text: "Mehr in der Datenschutzerklärung" }), "."),
    aktuell ? el("p", { klasse: "einwilligung__stand" }, el("strong", { text: aktuell })) : null,
    el("div", { klasse: "einwilligung__knoepfe" },
      el("button", { klasse: "knopf knopf--leise", type: "button", text: "Ablehnen", "data-ablehnen": true,
        onclick: () => { speichern(false); schliessen(); } }),
      el("button", { klasse: "knopf knopf--leise", type: "button", text: "Erlauben", "data-akzeptieren": true,
        onclick: () => { speichern(true); schliessen(); } }),
    ),
  );
  document.body.append(fenster);
  if (fokus) fenster.querySelector("button").focus();
}

export function einrichten() {
  if (!stand) oeffnen();
  for (const k of document.querySelectorAll("[data-einwilligung-oeffnen]")) {
    k.addEventListener("click", () => oeffnen({ fokus: true }));
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && fenster && stand) schliessen();
  });
}
