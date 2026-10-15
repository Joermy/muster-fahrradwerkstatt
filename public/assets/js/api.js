import { MODUS } from "./konfig.js";

export const BASIS = new URL(document.documentElement.dataset.basis || "./", location.href);

export class ApiFehler extends Error {
  constructor(status, daten) {
    super(daten.meldung || "Da ist etwas schiefgegangen. Bitte versuchen Sie es später noch einmal.");
    this.status = status;
    this.kennung = daten.fehler || "unbekannt";
    this.felder = daten.felder || {};
    this.daten = daten;
  }
}

let vorfuehrung = null;

export async function api(pfad, { methode = "GET", daten = null, csrf = "" } = {}) {
  let status;
  let antwort;
  if (MODUS === "vorfuehrung") {
    vorfuehrung ??= import("./vorfuehrung/server.js");
    const server = await vorfuehrung;
    ({ status, daten: antwort } = await server.anfrage(methode, pfad, daten, { csrf }));
  } else {
    const kopf = { Accept: "application/json" };
    if (daten !== null) kopf["Content-Type"] = "application/json";
    if (csrf) kopf["X-CSRF-Token"] = csrf;
    let r;
    try {
      r = await fetch(new URL("api/" + pfad, BASIS), {
        method: methode,
        headers: kopf,
        body: daten !== null ? JSON.stringify(daten) : undefined,
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
      });
    } catch (e) {
      throw new ApiFehler(0, { fehler: "netz", meldung: "Keine Verbindung. Bitte prüfen Sie Ihre Internetverbindung." });
    }
    status = r.status;
    antwort = await r.json().catch(() => ({}));
  }
  if (status < 200 || status >= 300) throw new ApiFehler(status, antwort || {});
  return antwort;
}

export const VORFUEHRUNG = MODUS === "vorfuehrung";
