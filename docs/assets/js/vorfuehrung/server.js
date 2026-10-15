import { BASIS } from "../api.js";

const SPEICHER = "rh_vorfuehrung";
const FASSUNG_SPEICHER = 4;
const MINDESTZEIT = 4;
const LEERLAUF_SEK = 1800;
const HOECHSTDAUER_SEK = 36000;
const VORLAUF_TAGE = 1;
const HORIZONT_TAGE = 28;
const WIDERRUFSFRIST_TAGE = 14;
const EINWILLIGUNG_FASSUNG = "2026-10";
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

const DEMO_PASSWORT = "Werkstatt-Vorfuehrung";
const DEMO_GEHEIMNIS = "KRSXG5DFOJWWC3TOMVZGQZLJOR2A";

const STATUS = {
  angefragt: "Anfrage eingegangen",
  bestaetigt: "Termin bestätigt",
  angenommen: "Rad angenommen",
  in_arbeit: "In Arbeit",
  wartet_auf_freigabe: "Wartet auf Ihre Freigabe",
  abholbereit: "Abholbereit",
  abgeschlossen: "Abgeholt",
  storniert: "Abgesagt",
  nicht_erschienen: "Nicht erschienen",
};
const UEBERGAENGE = {
  angefragt: ["bestaetigt", "storniert"],
  bestaetigt: ["angenommen", "storniert", "nicht_erschienen"],
  angenommen: ["in_arbeit", "abholbereit"],
  in_arbeit: ["abholbereit"],
  wartet_auf_freigabe: ["in_arbeit"],
  abholbereit: ["abgeschlossen", "in_arbeit"],
  abgeschlossen: [],
  storniert: [],
  nicht_erschienen: [],
};
const IN_DER_WERKSTATT = ["angenommen", "in_arbeit", "wartet_auf_freigabe", "abholbereit"];
const BELEGEND = ["angefragt", "bestaetigt", ...IN_DER_WERKSTATT];

class Fehler extends Error {
  constructor(status, fehler, meldung, felder = null) {
    super(meldung);
    this.status = status;
    this.fehler = fehler;
    this.felder = felder;
  }
}
const ungueltig = (felder) => new Fehler(422, "ungueltig", "Bitte prüfen Sie die markierten Angaben.", felder);

class Pruefung {
  constructor(daten) {
    this.d = daten || {};
    this.f = {};
  }

  static nur(daten, erlaubt) {
    if (daten === null || typeof daten !== "object" || Array.isArray(daten)) throw new Fehler(400, "kein_json", "Die Anfrage ist kein gültiges JSON-Objekt.");
    if (Object.keys(daten).some((k) => !erlaubt.includes(k))) throw new Fehler(400, "unbekannte_felder", "Die Anfrage enthält unbekannte Felder.");
    return new Pruefung(daten);
  }

  static saeubern(w, mehrzeilig) {
    w = w.replace(/\r\n?/g, "\n").replace(/[​-‏‪-‮⁦-⁩﻿]/g, "");
    if (mehrzeilig) {
      w = w.replace(/[\u0000-\u0009\u000B-\u001F\u007F-\u009F]/g, "").replace(/\n{3,}/g, "\n\n");
      return w.split("\n").map((z) => z.replace(/[ \t]+/g, " ").trim()).join("\n").trim();
    }
    return w.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").replace(/\s+/g, " ").trim();
  }

  text(feld, min, max, pflicht = true, mehrzeilig = false) {
    let w = this.d[feld];
    if (w === undefined || w === null || w === "") {
      if (pflicht) this.f[feld] = "Bitte ausfüllen.";
      return null;
    }
    if (typeof w !== "string") {
      this.f[feld] = "Ungültige Eingabe.";
      return null;
    }
    w = Pruefung.saeubern(w, mehrzeilig);
    const n = [...w].length;
    if (n < min) {
      this.f[feld] = pflicht || n > 0 ? `Mindestens ${min} Zeichen.` : "Bitte ausfüllen.";
      return null;
    }
    if (n > max) {
      this.f[feld] = `Höchstens ${max} Zeichen.`;
      return null;
    }
    return w;
  }

  name(feld) {
    const w = this.text(feld, 2, 80);
    if (w !== null && !/^\p{L}[\p{L}\p{M} .'-]*$/u.test(w)) {
      this.f[feld] = "Bitte nur Buchstaben, Leerzeichen, Punkt, Bindestrich oder Apostroph.";
      return null;
    }
    return w;
  }

  email(feld) {
    let w = this.text(feld, 6, 254);
    if (w === null) return null;
    w = w.toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(w) || /[\r\n,;<>"]/.test(w)) {
      this.f[feld] = "Bitte eine gültige E-Mail-Adresse angeben.";
      return null;
    }
    return w;
  }

  telefon(feld) {
    const w = this.text(feld, 6, 25, false);
    if (w !== null && !/^\+?[0-9][0-9 ()/-]{4,23}$/.test(w)) {
      this.f[feld] = "Bitte nur Ziffern, Leerzeichen, +, -, / und Klammern.";
      return null;
    }
    return w;
  }

  auswahl(feld, werte, pflicht = true) {
    const w = this.d[feld];
    if (w === undefined || w === null || w === "") {
      if (pflicht) this.f[feld] = "Bitte auswählen.";
      return null;
    }
    if (typeof w !== "string" || !werte.includes(w)) {
      this.f[feld] = "Ungültige Auswahl.";
      return null;
    }
    return w;
  }

  datum(feld) {
    const w = this.d[feld];
    const m = typeof w === "string" ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(w) : null;
    const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
    if (!m || d.getMonth() !== Number(m[2]) - 1 || d.getDate() !== Number(m[3])) {
      this.f[feld] = "Bitte ein gültiges Datum wählen.";
      return null;
    }
    return w;
  }

  uhrzeit(feld) {
    const w = this.d[feld];
    if (typeof w !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(w)) {
      this.f[feld] = "Bitte eine gültige Uhrzeit wählen.";
      return null;
    }
    return w;
  }

  wahrheit(feld) {
    const w = this.d[feld] ?? false;
    if (typeof w !== "boolean") {
      this.f[feld] = "Ungültige Eingabe.";
      return false;
    }
    return w;
  }

  ganzzahl(feld, min, max) {
    const w = this.d[feld];
    if (!Number.isInteger(w) || w < min || w > max) {
      this.f[feld] = `Bitte eine Zahl von ${min} bis ${max}.`;
      return null;
    }
    return w;
  }

  melden(feld, m) {
    this.f[feld] = m;
  }

  pruefen() {
    if (Object.keys(this.f).length) throw ungueltig(this.f);
  }
}

const z2 = (n) => String(n).padStart(2, "0");
const tagIso = (d) => `${d.getFullYear()}-${z2(d.getMonth() + 1)}-${z2(d.getDate())}`;
function iso(d = new Date()) {
  const o = -d.getTimezoneOffset();
  const v = o >= 0 ? "+" : "-";
  return `${tagIso(d)}T${z2(d.getHours())}:${z2(d.getMinutes())}:${z2(d.getSeconds())}${v}${z2(Math.floor(Math.abs(o) / 60))}:${z2(Math.abs(o) % 60)}`;
}
const heute = () => tagIso(new Date());
function tagPlus(t, n) {
  const d = new Date(t + "T12:00:00");
  d.setDate(d.getDate() + n);
  return tagIso(d);
}
const wochentag = (t) => ((new Date(t + "T12:00:00").getDay() + 6) % 7) + 1;
const sekunden = () => Math.floor(Date.now() / 1000);
const datumText = (t) => `${t.slice(8, 10)}.${t.slice(5, 7)}.${t.slice(0, 4)}`;
const zeitText = (i) => {
  const d = new Date(i);
  return `${z2(d.getDate())}.${z2(d.getMonth() + 1)}.${d.getFullYear()}, ${z2(d.getHours())}:${z2(d.getMinutes())} Uhr`;
};
const euroText = (c) => (c / 100).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";

function ostersonntag(j) {
  const k = Math.floor(j / 100);
  const m = 15 + Math.floor((3 * k + 3) / 4) - Math.floor((8 * k + 13) / 25);
  const s = 2 - Math.floor((3 * k + 3) / 4);
  const a = j % 19;
  const d = (19 * a + m) % 30;
  const r = Math.floor((d + Math.floor(a / 11)) / 29);
  const og = 21 + d - r;
  const sz = 7 - ((j + Math.floor(j / 4) + s) % 7);
  const oe = 7 - ((og - sz) % 7);
  return tagPlus(`${j}-03-01`, og + oe - 1);
}
function feiertag(t) {
  const fest = { "01-01": "Neujahr", "05-01": "Tag der Arbeit", "10-03": "Tag der Deutschen Einheit", "10-31": "Reformationstag", "12-25": "1. Weihnachtstag", "12-26": "2. Weihnachtstag" };
  if (fest[t.slice(5)]) return fest[t.slice(5)];
  const o = ostersonntag(Number(t.slice(0, 4)));
  for (const [ab, n] of [[-2, "Karfreitag"], [1, "Ostermontag"], [39, "Christi Himmelfahrt"], [50, "Pfingstmontag"]]) if (tagPlus(o, ab) === t) return n;
  return null;
}

function zufallsToken(bytes = 32) {
  const b = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function neueNummer() {
  const b = crypto.getRandomValues(new Uint8Array(8));
  const t = [...b].map((x) => ALPHABET[x % 32]).join("");
  return `RF-${t.slice(0, 4)}-${t.slice(4)}`;
}
const crc = (s) => [...s].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) >>> 0, 7);

async function sha256(text) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function base32(s) {
  const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of s.replace(/=+$/, "").toUpperCase()) bits += a.indexOf(c).toString(2).padStart(5, "0");
  const out = new Uint8Array(Math.floor(bits.length / 8));
  for (let i = 0; i < out.length; i++) out[i] = parseInt(bits.slice(i * 8, i * 8 + 8), 2);
  return out;
}
function neuesGeheimnis() {
  const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  return [...crypto.getRandomValues(new Uint8Array(32))].map((b) => a[b % 32]).join("");
}
async function totpCode(geheimnis, schritt) {
  const key = await crypto.subtle.importKey("raw", base32(geheimnis), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const z = new ArrayBuffer(8);
  new DataView(z).setUint32(4, schritt);
  new DataView(z).setUint32(0, Math.floor(schritt / 2 ** 32));
  const h = new Uint8Array(await crypto.subtle.sign("HMAC", key, z));
  const o = h[19] & 15;
  const n = ((h[o] & 0x7f) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3];
  return String(n % 1000000).padStart(6, "0");
}
async function totpPruefen(geheimnis, code, letzter) {
  if (!/^\d{6}$/.test(code)) return null;
  const jetzt = Math.floor(Date.now() / 30000);
  for (const v of [0, -1, 1]) {
    const s = jetzt + v;
    if (s > letzter && (await totpCode(geheimnis, s)) === code) return s;
  }
  return null;
}

let zustand = null;
let katalog = null;
let texte = null;

async function json(pfad) {
  const r = await fetch(new URL(pfad, BASIS), { cache: "no-cache" });
  if (!r.ok) throw new Error("Vorführdaten fehlen: " + pfad);
  return r.json();
}

function speichern() {
  try {
    sessionStorage.setItem(SPEICHER, JSON.stringify(zustand));
  } catch {
  }
}

async function laden() {
  if (zustand) return;
  [katalog, texte] = await Promise.all([json("assets/daten/leistungen.json"), json("assets/daten/texte.json")]);
  try {
    const roh = JSON.parse(sessionStorage.getItem(SPEICHER) || "null");
    if (roh && roh.fassung === FASSUNG_SPEICHER && roh.tag === heute()) zustand = roh;
  } catch {
    zustand = null;
  }
  if (!zustand) {
    zustand = await anlegen(await json("assets/daten/vorfuehrdaten.json"));
    speichern();
  }
}

async function anlegen(daten) {
  const t0 = heute();
  const jetzt = new Date();
  const z = {
    fassung: FASSUNG_SPEICHER, tag: t0, naechste: 1,
    auftraege: [], verlauf: [], angebote: [], notizen: [], widerrufe: [], protokoll: [], post: [], einwilligungen: {},
    sperrtage: [], sitzung: null,
    kapazitaet: {
      1: { zeiten: ["08:30", "10:00", "11:30", "14:00", "15:30", "17:00"], plaetze: 2 },
      2: { zeiten: ["08:30", "10:00", "11:30", "14:00", "15:30", "17:00"], plaetze: 2 },
      3: { zeiten: ["08:30", "10:00", "11:30", "14:00", "15:30", "17:00"], plaetze: 2 },
      4: { zeiten: ["08:30", "10:00", "11:30", "14:00", "15:30", "17:00"], plaetze: 2 },
      5: { zeiten: ["08:30", "10:00", "11:30", "14:00", "15:30", "17:00"], plaetze: 2 },
      6: { zeiten: ["09:00", "10:30", "12:00"], plaetze: 2 },
      7: { zeiten: [], plaetze: 0 },
    },
    benutzer: [
      { id: 1, name: "inhaberin", anzeigename: "Mira Ohlendorf", rolle: "inhaber", passwort: DEMO_PASSWORT, totp: DEMO_GEHEIMNIS, totp_aktiv: 1, totp_letzter: 0, passwort_wechseln: 0, aktiv: 1, fehlversuche: 0, gesperrt_bis: null, letzte_anmeldung: iso(new Date(Date.now() - 864e5 * 1.2)), erstellt: iso(new Date(Date.now() - 864e5 * 200)), ersatz: [] },
      { id: 2, name: "jonas.k", anzeigename: "Jonas Kröger", rolle: "werkstatt", passwort: DEMO_PASSWORT, totp: DEMO_GEHEIMNIS, totp_aktiv: 1, totp_letzter: 0, passwort_wechseln: 0, aktiv: 1, fehlversuche: 0, gesperrt_bis: null, letzte_anmeldung: iso(new Date(Date.now() - 864e5 * 0.3)), erstellt: iso(new Date(Date.now() - 864e5 * 120)), ersatz: [] },
    ],
  };
  const am = (tag, std, min) => {
    const d = new Date(tagPlus(t0, tag) + "T00:00:00");
    d.setHours(std, min, 0, 0);
    return d;
  };
  const frueher = (d, schritt) => iso(d < jetzt ? d : new Date(jetzt.getTime() - (5 + schritt * 7) * 60000));
  const samstag = ["09:00", "10:30", "12:00"];
  for (const e of daten.auftraege) {
    let d = tagPlus(t0, e.tag);
    while (wochentag(d) === 7 || feiertag(d)) d = tagPlus(d, e.tag > 0 ? 1 : -1);
    let zeit = e.zeit;
    if (wochentag(d) === 6 && !samstag.includes(zeit)) zeit = samstag[crc(zeit) % 3];
    const anfang = Math.min(e.tag - 3, -1 - (crc(e.nummer) % 3));
    const erstellt = iso(am(anfang, 9, 12));
    const id = z.naechste++;
    z.auftraege.push({
      id, nummer: e.nummer, token_hash: await sha256(e.token), leistung: e.leistung, rad: e.rad, termin_datum: d, termin_zeit: zeit, status: e.status,
      name: e.name, email: e.email.toLowerCase(), telefon: e.telefon || null, nachricht: e.nachricht || null, quelle: e.quelle || "website",
      erstellt, geaendert: erstellt, abgeschlossen: e.status === "abgeschlossen" ? iso(am(e.tag + 2, 16, 40)) : null, anonymisiert: null,
    });
    e.verlauf.forEach((s, i) => z.verlauf.push({ auftrag_id: id, status: s, hinweis: null, zeit: frueher(am(anfang + i, 9 + i, 12 + i), e.verlauf.length - i) }));
    if (e.angebot) {
      const summe = e.angebot.positionen.reduce((a, p) => a + p.cent, 0);
      z.angebote.push({
        id: z.naechste++, auftrag_id: id, positionen: e.angebot.positionen, summe_cent: summe, erstellt: iso(am(e.tag + 1, 11, 0)),
        entscheidung: e.angebot.entscheidung || null, entschieden: e.angebot.entscheidung ? iso(am(e.tag + 1, 12, 30)) : null, vorzeitiger_beginn: false,
      });
    }
  }
  z.protokoll.push({ id: 1, zeit: iso(new Date(Date.now() - 864e5 * 1.2)), aktion: "anmeldung", objekt: "", details: "", benutzer_id: 1 });
  return z;
}

const titel = (art, k) => (art === "leistung" ? katalog.leistungen : katalog.raeder).find((x) => x.kennung === k)?.titel || k;
const fuss = () => texte.fusszeile;

function protokoll(benutzerId, aktion, objekt = "", details = "") {
  const id = (zustand.protokoll[zustand.protokoll.length - 1]?.id || 0) + 1;
  zustand.protokoll.push({ id, zeit: iso(), aktion, objekt, details, benutzer_id: benutzerId });
}
function post(an, betreff, text, art) {
  const id = (zustand.post[zustand.post.length - 1]?.id || 0) + 1;
  zustand.post.push({ id, an, betreff, text, art, erstellt: iso() });
}
const auftragPerId = (id) => {
  const a = zustand.auftraege.find((x) => x.id === id);
  if (!a) throw new Fehler(404, "nicht_gefunden", "Auftrag nicht gefunden.");
  return a;
};
async function auftragPerToken(token) {
  if (typeof token !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Fehler(404, "unbekannter_link", "Dieser Link ist ungültig oder abgelaufen.");
  const h = await sha256(token);
  const a = zustand.auftraege.find((x) => x.token_hash === h && !x.anonymisiert);
  if (!a) throw new Fehler(404, "unbekannter_link", "Dieser Link ist ungültig oder abgelaufen.");
  return a;
}
const verlauf = (id) => zustand.verlauf.filter((v) => v.auftrag_id === id).map((v) => ({ status: v.status, text: STATUS[v.status] || v.status, hinweis: v.hinweis, zeit: v.zeit }));
function angebote(id) {
  return zustand.angebote.filter((g) => g.auftrag_id === id).map((g) => {
    let widerrufBis = null;
    let widerrufbar = false;
    if (g.entscheidung === "angenommen" && g.entschieden) {
      const ende = new Date(g.entschieden);
      ende.setDate(ende.getDate() + WIDERRUFSFRIST_TAGE);
      widerrufBis = tagIso(ende);
      widerrufbar = Date.now() < ende.getTime();
    }
    return { id: g.id, positionen: g.positionen, summe_cent: g.summe_cent, erstellt: g.erstellt, entscheidung: g.entscheidung, entschieden: g.entschieden, vorzeitiger_beginn: !!g.vorzeitiger_beginn, widerruf_bis: widerrufBis, widerrufbar };
  });
}
function loeschdatumText(a) {
  if (a.status === "abgeschlossen") return "Kontaktdaten werden 24 Monate nach der Abholung gelöscht (Gewährleistung).";
  if (a.status === "storniert" || a.status === "nicht_erschienen") return "Kontaktdaten werden 30 Tage nach dem Termin gelöscht.";
  return "Kontaktdaten werden gelöscht, sobald der Auftrag abgeschlossen ist und die Fristen abgelaufen sind.";
}
function emailKuerzen(e) {
  const [lokal, domain = ""] = e.split("@");
  return [...lokal][0] + "•".repeat(Math.max(2, Math.min(6, [...lokal].length - 1))) + "@" + domain;
}
function statusAendern(a, status, hinweis) {
  const jetzt = iso();
  a.status = status;
  a.geaendert = jetzt;
  if (status === "abgeschlossen") a.abgeschlossen = jetzt;
  zustand.verlauf.push({ auftrag_id: a.id, status, hinweis: hinweis || null, zeit: jetzt });
}
function anonymisieren(a, benutzerId, anlass) {
  if (a.anonymisiert) return;
  const jetzt = iso();
  Object.assign(a, { name: null, email: null, telefon: null, nachricht: null, token_hash: zufallsToken(), anonymisiert: jetzt, geaendert: jetzt });
  for (const v of zustand.verlauf) if (v.auftrag_id === a.id) v.hinweis = null;
  zustand.notizen = zustand.notizen.filter((n) => n.auftrag_id !== a.id);
  protokoll(benutzerId, "anonymisiert", a.nummer, anlass);
}

function belegt(datum, zeit) {
  return zustand.auftraege.filter((a) => a.termin_datum === datum && a.termin_zeit === zeit && BELEGEND.includes(a.status)).length;
}
function tage() {
  const aus = [];
  const sperren = Object.fromEntries(zustand.sperrtage.map((s) => [s.datum, s.grund]));
  for (let i = VORLAUF_TAGE; i <= HORIZONT_TAGE; i++) {
    const datum = tagPlus(heute(), i);
    const w = wochentag(datum);
    const grund = feiertag(datum) || sperren[datum] || null;
    const k = zustand.kapazitaet[w] || { zeiten: [], plaetze: 0 };
    aus.push({ datum, wochentag: w, zeiten: grund ? [] : k.zeiten.map((zeit) => ({ zeit, frei: Math.max(0, k.plaetze - belegt(datum, zeit)) })), grund });
  }
  return aus;
}
function platzFrei(datum, zeit) {
  if (datum < tagPlus(heute(), VORLAUF_TAGE) || datum > tagPlus(heute(), HORIZONT_TAGE) || feiertag(datum)) return false;
  if (zustand.sperrtage.some((s) => s.datum === datum)) return false;
  const k = zustand.kapazitaet[wochentag(datum)];
  if (!k || !k.zeiten.includes(zeit)) return false;
  return belegt(datum, zeit) < k.plaetze;
}

const oeffentlich = {
  "GET termine": () => ({ tage: tage(), formular: String(sekunden()) }),

  "POST anfragen": async (d) => {
    const v = Pruefung.nur(d, ["leistung", "rad", "datum", "zeit", "name", "email", "telefon", "nachricht", "firma", "formular"]);
    const alter = /^\d+$/.test(d.formular || "") ? sekunden() - Number(d.formular) : -1;
    if ((d.firma || "") !== "" || alter < MINDESTZEIT || alter > 7200) {
      protokoll(null, "anfrage_verworfen", "", d.firma ? "lockfeld" : "zeit");
      throw new Fehler(422, "bitte_erneut", "Das Formular ist abgelaufen. Bitte laden Sie die Seite neu und senden Sie es noch einmal.");
    }
    const e = {
      leistung: v.auswahl("leistung", katalog.leistungen.map((l) => l.kennung)),
      rad: v.auswahl("rad", katalog.raeder.map((r) => r.kennung)),
      datum: v.datum("datum"), zeit: v.uhrzeit("zeit"), name: v.name("name"), email: v.email("email"),
      telefon: v.telefon("telefon"), nachricht: v.text("nachricht", 0, 1000, false, true),
    };
    v.pruefen();
    return [201, await anlegenAuftrag(e, "website")];
  },

  "POST status": async (d) => kundenansicht(await auftragPerToken(tokenAus(d))),

  "POST status/absagen": async (d) => {
    const a = await auftragPerToken(tokenAus(d));
    if (!["angefragt", "bestaetigt"].includes(a.status)) throw new Fehler(409, "nicht_absagbar", "Ihr Rad ist schon bei uns. Bitte rufen Sie uns an.");
    statusAendern(a, "storniert", "Vom Kunden online abgesagt.");
    protokoll(null, "kunde_abgesagt", a.nummer);
    return { ok: true };
  },

  "POST status/freigabe": async (d) => {
    const v = Pruefung.nur(d, ["token", "angebot", "annehmen", "vorzeitig"]);
    const angebotId = v.ganzzahl("angebot", 1, Number.MAX_SAFE_INTEGER);
    const annehmen = v.wahrheit("annehmen");
    const vorzeitig = v.wahrheit("vorzeitig");
    v.pruefen();
    const a = await auftragPerToken(d.token);
    const g = zustand.angebote.find((x) => x.id === angebotId && x.auftrag_id === a.id);
    if (!g) throw new Fehler(404, "nicht_gefunden", "Kostenvoranschlag nicht gefunden.");
    if (g.entscheidung) throw new Fehler(409, "schon_entschieden", "Über diesen Kostenvoranschlag ist schon entschieden.");
    const jetzt = iso();
    g.entscheidung = annehmen ? "angenommen" : "abgelehnt";
    g.entschieden = jetzt;
    g.vorzeitiger_beginn = annehmen && vorzeitig;
    const pruefsumme = await sha256(`${a.nummer}|${JSON.stringify(g.positionen)}|${g.summe_cent}|${jetzt}|${vorzeitig ? 1 : 0}|${texte.belehrung_fassung}`);
    statusAendern(a, "in_arbeit", annehmen ? "Zusatzarbeiten freigegeben." : "Zusatzarbeiten abgelehnt.");
    protokoll(null, annehmen ? "angebot_angenommen" : "angebot_abgelehnt", a.nummer);
    let fristBis = null;
    if (annehmen) {
      fristBis = tagPlus(heute(), WIDERRUFSFRIST_TAGE);
      const zeilen = g.positionen.map((p) => `- ${p.text}: ${euroText(p.cent)}`).join("\n");
      const beginn = vorzeitig
        ? "Sie haben ausdrücklich verlangt, dass wir vor Ablauf der Widerrufsfrist beginnen, und bestätigt, dass Sie Ihr Widerrufsrecht bei vollständiger Vertragserfüllung verlieren."
        : "Sie haben nicht verlangt, dass wir vor Ablauf der Widerrufsfrist beginnen. Wir beginnen mit den Zusatzarbeiten deshalb erst nach Ablauf der Frist, außer Sie teilen uns etwas anderes mit.";
      post(a.email, `Vertragsbestätigung Zusatzarbeiten ${a.nummer}`,
        `Guten Tag,\n\nhiermit bestätigen wir Ihren Auftrag über folgende Zusatzarbeiten an Ihrem Rad (${a.nummer}):\n\n${zeilen}\n\nGesamtpreis: ${euroText(g.summe_cent)} inkl. 19 % USt.\nZahlung bei Abholung in bar oder mit Karte.\nAuftrag erteilt am: ${zeitText(jetzt)}\n\n${beginn}\n\nVertrag widerrufen: ${texte.url}/widerruf/\n\n${texte.widerrufsbelehrung}\n\n${texte.widerrufsformular}\n\nPrüfsumme dieses Vertrags: ${pruefsumme}\n\n${fuss()}`,
        "vertrag");
    }
    return { entscheidung: g.entscheidung, frist_bis: fristBis };
  },

  "POST status/auskunft": async (d) => {
    const a = await auftragPerToken(tokenAus(d));
    protokoll(null, "kunde_auskunft", a.nummer);
    return auskunft(a);
  },

  "POST status/loeschen": async (d) => {
    Pruefung.nur(d, ["token", "bestaetigung"]);
    if (d.bestaetigung !== "LÖSCHEN") throw ungueltig({ bestaetigung: "Bitte LÖSCHEN eintippen." });
    const a = await auftragPerToken(d.token);
    if (IN_DER_WERKSTATT.includes(a.status)) {
      throw new Fehler(409, "rad_in_werkstatt", "Ihr Rad ist gerade bei uns. Solange wir es haben, brauchen wir Ihre Kontaktdaten. Wir löschen sie nach der gesetzlichen Frist automatisch; vorher können Sie uns jederzeit anrufen.");
    }
    if (a.status === "abgeschlossen" && zustand.angebote.some((g) => g.auftrag_id === a.id && g.entscheidung === "angenommen")) {
      a.token_hash = zufallsToken();
      a.geaendert = iso();
      protokoll(null, "kunde_loeschung_eingeschraenkt", a.nummer);
      return { geloescht: false, meldung: "Für ausgeführte Arbeiten müssen wir die Angaben bis zum Ende der Gewährleistung aufbewahren. Ihr Link ist jetzt gesperrt, die Daten werden danach automatisch gelöscht." };
    }
    anonymisieren(a, null, "kunde");
    return { geloescht: true, meldung: "Ihre Kontaktdaten und Nachrichten sind gelöscht." };
  },

  "POST status/link": async (d) => {
    const v = Pruefung.nur(d, ["nummer", "email"]);
    const nummer = (v.text("nummer", 12, 12) || "").toUpperCase();
    const email = v.email("email");
    if (!/^RF-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/.test(nummer)) v.melden("nummer", "Die Nummer hat die Form RF-XXXX-XXXX.");
    v.pruefen();
    const a = zustand.auftraege.find((x) => x.nummer === nummer && x.email === email && !x.anonymisiert);
    if (a) {
      const token = zufallsToken();
      a.token_hash = await sha256(token);
      protokoll(null, "link_erneuert", a.nummer);
      post(a.email, `Ihr Link zum Auftrag ${a.nummer}`, `Guten Tag,\n\nhier ist Ihr neuer Link. Der alte gilt nicht mehr.\n\n${texte.url}/status/#t=${token}\n\n${fuss()}`, "link");
    }
    return { ok: true, meldung: "Wenn Nummer und E-Mail-Adresse zusammenpassen, ist ein neuer Link unterwegs." };
  },

  "POST widerruf": (d) => {
    const v = Pruefung.nur(d, ["name", "nummer", "email", "grund"]);
    const name = v.name("name");
    const nummer = (v.text("nummer", 6, 20) || "").toUpperCase();
    const email = v.email("email");
    const grund = v.text("grund", 0, 500, false, true);
    if (nummer && !/^[A-Z0-9-]{6,20}$/.test(nummer)) v.melden("nummer", "Bitte die Auftragsnummer aus Ihrer Mail angeben, z. B. RF-ABCD-EFGH.");
    v.pruefen();
    const eingang = iso();
    const kennung = "W-" + [...crypto.getRandomValues(new Uint8Array(4))].map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
    const a = zustand.auftraege.find((x) => x.nummer === nummer && x.email === email);
    const id = (zustand.widerrufe[zustand.widerrufe.length - 1]?.id || 0) + 1;
    zustand.widerrufe.push({ id, eingang, auftragsnummer: nummer, name, email, grund, auftrag_id: a ? a.id : null, kennung, bearbeitet: null });
    protokoll(null, "widerruf_eingegangen", nummer, kennung);
    post(email, `Eingangsbestätigung Ihres Widerrufs ${kennung}`,
      `Guten Tag,\n\nwir bestätigen den Eingang Ihres Widerrufs.\n\nEingang: ${zeitText(eingang)}\nVorgang: ${kennung}\n\nInhalt Ihrer Erklärung:\nHiermit widerrufe ich den über die Website geschlossenen Vertrag über Zusatzarbeiten zum Auftrag ${nummer}.\nName: ${name}\nE-Mail für diese Bestätigung: ${email}\n${grund ? "Einen freiwilligen Grund haben Sie angegeben; er liegt uns vor.\n" : ""}\nDiese Mail bestätigt den Eingang. Wir prüfen den Widerruf und melden uns.\n\n${fuss()}`,
      "widerruf");
    return [201, { kennung, eingang }];
  },

  "POST einwilligung": (d) => {
    const v = Pruefung.nur(d, ["id", "fassung", "medien"]);
    const medien = v.wahrheit("medien");
    if (typeof d.id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(d.id) || d.fassung !== EINWILLIGUNG_FASSUNG) {
      throw ungueltig({ id: "Ungültige Kennung oder Fassung." });
    }
    v.pruefen();
    zustand.einwilligungen[d.id] = { tag: heute(), medien };
    return { ok: true };
  },

};

function tokenAus(d) {
  Pruefung.nur(d, ["token"]);
  if (typeof d.token !== "string") throw new Fehler(404, "unbekannter_link", "Dieser Link ist ungültig oder abgelaufen.");
  return d.token;
}

async function anlegenAuftrag(e, quelle) {
  if (!platzFrei(e.datum, e.zeit)) throw new Fehler(409, "termin_belegt", "Dieser Termin ist gerade vergeben worden. Bitte wählen Sie einen anderen.");
  let nummer;
  do nummer = neueNummer(); while (zustand.auftraege.some((a) => a.nummer === nummer));
  const token = zufallsToken();
  const jetzt = iso();
  const id = zustand.naechste++;
  zustand.auftraege.push({
    id, nummer, token_hash: await sha256(token), leistung: e.leistung, rad: e.rad, termin_datum: e.datum, termin_zeit: e.zeit, status: "angefragt",
    name: e.name, email: e.email, telefon: e.telefon, nachricht: e.nachricht, quelle, erstellt: jetzt, geaendert: jetzt, abgeschlossen: null, anonymisiert: null,
  });
  zustand.verlauf.push({ auftrag_id: id, status: "angefragt", hinweis: null, zeit: jetzt });
  post(e.email, `Ihre Terminanfrage ${nummer}`,
    `Guten Tag,\n\nvielen Dank für Ihre Anfrage. Wir melden uns, sobald der Termin bestätigt ist.\n\nAuftragsnummer: ${nummer}\nLeistung: ${titel("leistung", e.leistung)}\nWunschtermin: ${datumText(e.datum)}, ${e.zeit} Uhr\n\nHier sehen Sie jederzeit den Stand, können absagen, Ihre Daten herunterladen oder löschen:\n${texte.url}/status/#t=${token}\n\nBitte geben Sie diesen Link nicht weiter. Wer ihn hat, sieht den Stand Ihres Auftrags.\n\nDie Anfrage ist noch kein Auftrag. Den Reparaturauftrag besprechen wir bei der Annahme in der Werkstatt.\n\n${fuss()}`,
    "anfrage");
  return { nummer, token };
}

function kundenansicht(a) {
  return {
    nummer: a.nummer, status: a.status, status_text: STATUS[a.status] || a.status,
    leistung: titel("leistung", a.leistung), rad: titel("rad", a.rad),
    termin: { datum: a.termin_datum, zeit: a.termin_zeit },
    vorname: a.name.split(" ")[0], email: emailKuerzen(a.email),
    verlauf: verlauf(a.id), angebote: angebote(a.id),
    absagen_moeglich: ["angefragt", "bestaetigt"].includes(a.status),
    loeschen_sofort: !IN_DER_WERKSTATT.includes(a.status),
    erstellt: a.erstellt,
  };
}

function auskunft(a) {
  return {
    erstellt: iso(),
    verantwortlich: texte.anschrift,
    auftrag: {
      nummer: a.nummer, leistung: titel("leistung", a.leistung), rad: titel("rad", a.rad), termin: `${a.termin_datum} ${a.termin_zeit}`,
      status: STATUS[a.status] || a.status, angefragt_am: a.erstellt, zuletzt_geaendert: a.geaendert, abgeschlossen_am: a.abgeschlossen,
    },
    kontaktdaten: { name: a.name, email: a.email, telefon: a.telefon, nachricht: a.nachricht },
    verlauf: verlauf(a.id),
    kostenvoranschlaege: angebote(a.id),
    interne_notizen: zustand.notizen.filter((n) => n.auftrag_id === a.id).map((n) => ({ zeit: n.zeit, text: n.text })),
    speicherdauer: loeschdatumText(a),
  };
}

const benutzerPerId = (id) => zustand.benutzer.find((b) => b.id === id && b.aktiv);
const nichtAngemeldet = () => new Fehler(401, "nicht_angemeldet", "Bitte melden Sie sich an.");

function sitzungPruefen(stufe) {
  const s = zustand.sitzung;
  const jetzt = sekunden();
  const leerlauf = stufe === "passwort" ? 300 : LEERLAUF_SEK;
  if (!s || s.stufe !== stufe || s.zuletzt < jetzt - leerlauf || s.erstellt < jetzt - HOECHSTDAUER_SEK) {
    if (s && s.stufe === stufe) zustand.sitzung = null;
    throw nichtAngemeldet();
  }
  const b = benutzerPerId(s.benutzer_id);
  if (!b) {
    zustand.sitzung = null;
    throw nichtAngemeldet();
  }
  return { s, b };
}

function pruefen(csrf, schreibend, vollerZugang = true, rolle = null) {
  const { s, b } = sitzungPruefen("voll");
  s.zuletzt = sekunden();
  if (schreibend && (!csrf || csrf !== s.csrf)) throw new Fehler(403, "csrf", "Die Sitzung ist abgelaufen. Bitte laden Sie die Seite neu.");
  if (vollerZugang && (b.totp_aktiv !== 1 || b.passwort_wechseln === 1)) throw new Fehler(403, "einrichtung_noetig", "Bitte zuerst Passwort ändern und Zwei-Faktor-Anmeldung einrichten.");
  if (rolle && b.rolle !== rolle) throw new Fehler(403, "keine_berechtigung", "Dafür fehlt die Berechtigung.");
  return b;
}

function sitzungAnlegen(b, stufe) {
  zustand.sitzung = { benutzer_id: b.id, stufe, csrf: zufallsToken(), erstellt: sekunden(), zuletzt: sekunden() };
}

const fehlgeschlagen = () => new Fehler(401, "anmeldung_fehlgeschlagen", "Benutzername oder Passwort stimmen nicht, oder das Konto ist vorübergehend gesperrt.");

function erfolgreich(b) {
  b.fehlversuche = 0;
  b.gesperrt_bis = null;
  b.letzte_anmeldung = iso();
  protokoll(b.id, "anmeldung");
}

const SCHWACH = ["passwort", "password", "123456789012", "qwertzuiopü", "hallo1234567", "fahrradwerkstatt", "radhausfuhse", "werkstatt123"];
function schwaeche(p, name) {
  const n = [...p].length;
  if (n < 12) return "Mindestens 12 Zeichen.";
  if (n > 128) return "Höchstens 128 Zeichen.";
  const k = p.toLowerCase();
  if (name && k.includes(name.toLowerCase())) return "Das Passwort darf den Benutzernamen nicht enthalten.";
  const ohne = k.replace(/[0-9!.?]+$/, "");
  if (SCHWACH.includes(k) || SCHWACH.includes(ohne)) return "Dieses Passwort steht auf Listen häufiger Passwörter.";
  if (new Set([...k]).size < 5) return "Zu wenige verschiedene Zeichen.";
  return null;
}

function listenEintrag(a) {
  return {
    id: a.id, nummer: a.nummer, leistung: a.leistung, leistung_text: titel("leistung", a.leistung), rad: a.rad,
    termin_datum: a.termin_datum, termin_zeit: a.termin_zeit, status: a.status, name: a.anonymisiert ? null : a.name,
    offene_angebote: zustand.angebote.filter((g) => g.auftrag_id === a.id && !g.entscheidung).length, geaendert: a.geaendert,
  };
}
function liste({ status = null, offen = false, suche = null } = {}) {
  return zustand.auftraege
    .filter((a) => (!status || a.status === status) && (!offen || !["abgeschlossen", "storniert", "nicht_erschienen"].includes(a.status)) && (!suche || !/^RF-[A-Z0-9-]{1,9}$/i.test(suche) || a.nummer.startsWith(suche.toUpperCase())))
    .sort((a, b) => (b.termin_datum + b.termin_zeit).localeCompare(a.termin_datum + a.termin_zeit))
    .slice(0, 300)
    .map(listenEintrag);
}
function detail(id, benutzerId) {
  const a = auftragPerId(id);
  protokoll(benutzerId, "auftrag_angesehen", a.nummer);
  const offen = !a.anonymisiert;
  return {
    id, nummer: a.nummer, status: a.status, status_text: STATUS[a.status],
    naechste: (UEBERGAENGE[a.status] || []).map((s) => ({ status: s, text: STATUS[s] })),
    leistung: a.leistung, leistung_text: titel("leistung", a.leistung), rad: a.rad, rad_text: titel("rad", a.rad),
    termin_datum: a.termin_datum, termin_zeit: a.termin_zeit,
    name: offen ? a.name : null, email: offen ? a.email : null, telefon: offen ? a.telefon : null, nachricht: offen ? a.nachricht : null,
    verlauf: verlauf(id), angebote: angebote(id),
    notizen: zustand.notizen.filter((n) => n.auftrag_id === id).map((n) => ({ zeit: n.zeit, von: zustand.benutzer.find((b) => b.id === n.benutzer_id)?.anzeigename || null, text: n.text })),
    widerrufe: zustand.widerrufe.filter((w) => w.auftrag_id === id).map((w) => ({ oeffentliche_id: w.kennung, eingang: w.eingang, bearbeitet: w.bearbeitet })),
    erstellt: a.erstellt, anonymisiert: a.anonymisiert, loeschung: loeschdatumText(a),
  };
}

const verwaltung = [
  ["POST", /^anmelden$/, (d) => {
    const v = Pruefung.nur(d, ["name", "passwort"]);
    const name = v.text("name", 1, 64);
    if (typeof d.passwort !== "string" || d.passwort === "" || d.passwort.length > 512) v.melden("passwort", "Bitte ausfüllen.");
    v.pruefen();
    zustand.sitzung = null;
    const b = zustand.benutzer.find((x) => x.name === name.toLowerCase() && x.aktiv);
    if (b && b.gesperrt_bis && iso() < b.gesperrt_bis) {
      protokoll(b.id, "anmeldung_gesperrt");
      throw fehlgeschlagen();
    }
    if (!b || b.passwort !== d.passwort) {
      if (b) {
        b.fehlversuche++;
        if (b.fehlversuche >= 5) b.gesperrt_bis = iso(new Date(Date.now() + 15 * 2 ** Math.min(4, b.fehlversuche - 5) * 60000));
        protokoll(b.id, "anmeldung_falsch", "", `Versuch ${b.fehlversuche}`);
      }
      throw fehlgeschlagen();
    }
    const stufe = b.totp_aktiv === 1 ? "passwort" : "voll";
    if (stufe === "voll") erfolgreich(b);
    sitzungAnlegen(b, stufe);
    return { stufe };
  }],
  ["POST", /^code$/, async (d) => {
    Pruefung.nur(d, ["code"]);
    const { b } = sitzungPruefen("passwort");
    const code = typeof d.code === "string" ? d.code.trim() : "";
    const schritt = await totpPruefen(b.totp, code, b.totp_letzter);
    if (schritt !== null) b.totp_letzter = schritt;
    else {
      const i = b.ersatz.indexOf(code.toUpperCase());
      if (i >= 0) {
        b.ersatz.splice(i, 1);
        protokoll(b.id, "ersatzcode_verwendet");
      } else {
        b.fehlversuche++;
        if (b.fehlversuche >= 5) {
          b.gesperrt_bis = iso(new Date(Date.now() + 15 * 60000));
          zustand.sitzung = null;
        }
        protokoll(b.id, "code_falsch");
        throw new Fehler(401, "code_falsch", "Der Code stimmt nicht.");
      }
    }
    erfolgreich(b);
    sitzungAnlegen(b, "voll");
    return { stufe: "voll" };
  }],
  ["POST", /^abmelden$/, (d, csrf) => {
    pruefen(csrf, true, false);
    zustand.sitzung = null;
    return { ok: true };
  }],
  ["GET", /^ich$/, () => {
    const b = pruefen("", false, false);
    return { name: b.name, anzeigename: b.anzeigename, rolle: b.rolle, zweifaktor: b.totp_aktiv === 1, passwort_wechseln: b.passwort_wechseln === 1, csrf: zustand.sitzung.csrf, entwicklung: false };
  }],
  ["POST", /^passwort$/, (d, csrf) => {
    const b = pruefen(csrf, true, false);
    Pruefung.nur(d, ["alt", "neu"]);
    if (b.passwort !== d.alt) throw ungueltig({ alt: "Das bisherige Passwort stimmt nicht." });
    const s = schwaeche(String(d.neu || ""), b.name);
    if (s) throw ungueltig({ neu: s });
    b.passwort = String(d.neu);
    b.passwort_wechseln = 0;
    zustand.sitzung = null;
    protokoll(b.id, "passwort_geaendert");
    return { ok: true, meldung: "Passwort geändert. Bitte neu anmelden." };
  }],
  ["POST", /^zweifaktor\/start$/, (d, csrf) => {
    const b = pruefen(csrf, true, false);
    if (b.totp_aktiv === 1) throw new Fehler(409, "schon_aktiv", "Die Zwei-Faktor-Anmeldung ist bereits eingerichtet.");
    b.totp = neuesGeheimnis();
    return { geheimnis: b.totp, uri: `otpauth://totp/${encodeURIComponent("Radhaus Fuhse:" + b.name)}?secret=${b.totp}&issuer=${encodeURIComponent("Radhaus Fuhse")}&algorithm=SHA1&digits=6&period=30` };
  }],
  ["POST", /^zweifaktor\/bestaetigen$/, async (d, csrf) => {
    const b = pruefen(csrf, true, false);
    Pruefung.nur(d, ["code"]);
    if (b.totp_aktiv === 1 || !b.totp) throw new Fehler(409, "nicht_vorbereitet", "Bitte zuerst einen neuen Schlüssel anfordern.");
    const schritt = await totpPruefen(b.totp, String(d.code || ""), 0);
    if (schritt === null) throw new Fehler(422, "code_falsch", "Der Code stimmt nicht. Bitte die Uhrzeit des Telefons prüfen.");
    b.totp_aktiv = 1;
    b.totp_letzter = schritt;
    b.ersatz = Array.from({ length: 8 }, () => [...crypto.getRandomValues(new Uint8Array(10))].map((x) => ALPHABET[x % 32]).join("").replace(/(.{5})/, "$1-"));
    protokoll(b.id, "zweifaktor_eingerichtet");
    return { ersatzcodes: [...b.ersatz] };
  }],

  ["GET", /^uebersicht$/, () => {
    pruefen("", false);
    const zaehl = (s) => zustand.auftraege.filter((a) => a.status === s).length;
    const offen = liste({ offen: true });
    const bis = tagPlus(heute(), 7);
    const demnaechst = offen.filter((a) => a.termin_datum > heute() && a.termin_datum <= bis)
      .sort((a, b) => (a.termin_datum + a.termin_zeit).localeCompare(b.termin_datum + b.termin_zeit));
    return {
      heute: offen.filter((a) => a.termin_datum === heute()),
      demnaechst: demnaechst.slice(0, 8),
      zahlen: {
        angefragt: zaehl("angefragt"), bestaetigt: zaehl("bestaetigt"),
        in_werkstatt: zustand.auftraege.filter((a) => ["angenommen", "in_arbeit", "wartet_auf_freigabe"].includes(a.status)).length,
        abholbereit: zaehl("abholbereit"), widerrufe_offen: zustand.widerrufe.filter((w) => !w.bearbeitet).length,
      },
    };
  }],
  ["GET", /^auftraege$/, (d, csrf, q) => {
    pruefen("", false);
    const status = STATUS[q.get("status")] ? q.get("status") : null;
    return { auftraege: liste({ status, offen: q.get("offen") === "1", suche: q.get("suche") ? q.get("suche").slice(0, 12) : null }) };
  }],
  ["POST", /^auftraege$/, async (d, csrf) => {
    const b = pruefen(csrf, true);
    const v = Pruefung.nur(d, ["leistung", "rad", "datum", "zeit", "name", "email", "telefon", "nachricht"]);
    const e = {
      leistung: v.auswahl("leistung", katalog.leistungen.map((l) => l.kennung)), rad: v.auswahl("rad", katalog.raeder.map((r) => r.kennung)),
      datum: v.datum("datum"), zeit: v.uhrzeit("zeit"), name: v.name("name"), email: v.email("email"), telefon: v.telefon("telefon"), nachricht: v.text("nachricht", 0, 1000, false, true),
    };
    v.pruefen();
    const r = await anlegenAuftrag(e, "werkstatt");
    protokoll(b.id, "auftrag_angelegt", r.nummer);
    return [201, { nummer: r.nummer }];
  }],
  ["GET", /^auftraege\/(\d+)$/, (d, csrf, q, m) => detail(Number(m[1]), pruefen("", false).id)],
  ["POST", /^auftraege\/(\d+)\/status$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true);
    const v = Pruefung.nur(d, ["status", "hinweis"]);
    const status = v.auswahl("status", Object.keys(STATUS));
    const hinweis = v.text("hinweis", 0, 300, false, true);
    v.pruefen();
    const a = auftragPerId(Number(m[1]));
    if (!(UEBERGAENGE[a.status] || []).includes(status)) throw new Fehler(409, "falscher_wechsel", "Dieser Statuswechsel ist nicht möglich.");
    if (a.anonymisiert) throw new Fehler(409, "anonymisiert", "Dieser Auftrag ist bereits anonymisiert.");
    const alt = a.status;
    statusAendern(a, status, hinweis);
    protokoll(b.id, "status", a.nummer, `${alt} -> ${status}`);
    const text = { bestaetigt: `Ihr Termin am ${datumText(a.termin_datum)} um ${a.termin_zeit} Uhr ist bestätigt.`, abholbereit: "Ihr Rad ist fertig und kann abgeholt werden.", storniert: "Ihr Termin ist leider abgesagt." }[status];
    if (text) post(a.email, `${STATUS[status]} – ${a.nummer}`, `Guten Tag,\n\n${text}${hinweis ? `\n\nHinweis der Werkstatt: ${hinweis}` : ""}\n\nDen aktuellen Stand sehen Sie über den Link aus Ihrer ersten Mail.\n\n${fuss()}`, "status");
    return detail(a.id, b.id);
  }],
  ["POST", /^auftraege\/(\d+)\/angebot$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true);
    Pruefung.nur(d, ["positionen"]);
    const pos = d.positionen;
    if (!Array.isArray(pos) || !pos.length || pos.length > 12) throw ungueltig({ positionen: "Ein bis zwölf Positionen." });
    const sauber = pos.map((p, i) => {
      if (!p || typeof p !== "object") throw ungueltig({ [`positionen.${i}`]: "Ungültig." });
      const v = Pruefung.nur(p, ["text", "cent"]);
      const text = v.text("text", 2, 120);
      const cent = v.ganzzahl("cent", 0, 500000);
      v.pruefen();
      return { text, cent };
    });
    const a = auftragPerId(Number(m[1]));
    if (!["angenommen", "in_arbeit"].includes(a.status)) throw new Fehler(409, "falscher_status", "Ein Kostenvoranschlag ist nur möglich, solange das Rad in Arbeit ist.");
    if (zustand.angebote.some((g) => g.auftrag_id === a.id && !g.entscheidung)) throw new Fehler(409, "offenes_angebot", "Es gibt bereits einen offenen Kostenvoranschlag.");
    const summe = sauber.reduce((s, p) => s + p.cent, 0);
    zustand.angebote.push({ id: zustand.naechste++, auftrag_id: a.id, positionen: sauber, summe_cent: summe, erstellt: iso(), entscheidung: null, entschieden: null, vorzeitiger_beginn: false });
    statusAendern(a, "wartet_auf_freigabe", null);
    protokoll(b.id, "angebot_erstellt", a.nummer, euroText(summe));
    const zeilen = sauber.map((p) => `- ${p.text}: ${euroText(p.cent)}`).join("\n");
    post(a.email, `Kostenvoranschlag zu ${a.nummer}`, `Guten Tag,\n\nbei Ihrem Rad (${a.nummer}) haben wir weitere Arbeiten gefunden:\n\n${zeilen}\n\nSumme: ${euroText(summe)} inkl. 19 % USt.\n\nÜber den Link aus Ihrer ersten Mail können Sie die Arbeiten freigeben oder ablehnen. Ohne Ihre Freigabe machen wir nur die vereinbarten Arbeiten.\n\n${fuss()}`, "angebot");
    return [201, detail(a.id, b.id)];
  }],
  ["POST", /^auftraege\/(\d+)\/notiz$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true);
    const v = Pruefung.nur(d, ["text"]);
    const text = v.text("text", 1, 2000, true, true);
    v.pruefen();
    const a = auftragPerId(Number(m[1]));
    zustand.notizen.push({ auftrag_id: a.id, benutzer_id: b.id, text, zeit: iso() });
    protokoll(b.id, "notiz", a.nummer);
    return [201, detail(a.id, b.id)];
  }],
  ["GET", /^auftraege\/(\d+)\/auskunft$/, (d, csrf, q, m) => {
    const b = pruefen("", false, true, "inhaber");
    const a = auftragPerId(Number(m[1]));
    if (a.anonymisiert) throw new Fehler(409, "anonymisiert", "Zu diesem Auftrag sind keine Personendaten mehr gespeichert.");
    protokoll(b.id, "auskunft_erstellt", a.nummer);
    return auskunft(a);
  }],
  ["POST", /^auftraege\/(\d+)\/anonymisieren$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true, true, "inhaber");
    Pruefung.nur(d, ["bestaetigung"]);
    const a = auftragPerId(Number(m[1]));
    if (d.bestaetigung !== a.nummer) throw ungueltig({ bestaetigung: "Zur Bestätigung die Auftragsnummer eintippen." });
    anonymisieren(a, b.id, "verwaltung");
    return detail(a.id, b.id);
  }],
  ["GET", /^kapazitaet$/, () => {
    pruefen("", false);
    return { plan: zustand.kapazitaet, sperrtage: zustand.sperrtage.filter((s) => s.datum >= heute()).sort((a, b) => a.datum.localeCompare(b.datum)), tage: tage() };
  }],
  ["POST", /^kapazitaet$/, (d, csrf) => {
    const b = pruefen(csrf, true, true, "inhaber");
    Pruefung.nur(d, ["plan", "sperrtage"]);
    const plan = {};
    for (const [tag, k] of Object.entries(d.plan && typeof d.plan === "object" ? d.plan : {})) {
      if (!/^[1-7]$/.test(tag) || !k || typeof k !== "object") throw ungueltig({ plan: "Ungültiger Wochentag." });
      const v = Pruefung.nur(k, ["zeiten", "plaetze"]);
      const plaetze = v.ganzzahl("plaetze", 0, 20);
      let zeiten = k.zeiten ?? [];
      if (!Array.isArray(zeiten) || zeiten.length > 16) {
        v.melden("zeiten", "Höchstens 16 Zeiten.");
        zeiten = [];
      }
      if (zeiten.some((z) => typeof z !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(z))) v.melden("zeiten", "Zeiten im Format HH:MM.");
      v.pruefen();
      plan[tag] = { zeiten: [...new Set(zeiten)].sort(), plaetze };
    }
    const sperren = [];
    for (const s of Array.isArray(d.sperrtage) ? d.sperrtage : []) {
      if (!s || typeof s !== "object") continue;
      const v = Pruefung.nur(s, ["datum", "grund"]);
      const datum = v.datum("datum");
      const grund = v.text("grund", 1, 60);
      v.pruefen();
      sperren.push({ datum, grund });
    }
    Object.assign(zustand.kapazitaet, plan);
    if ("sperrtage" in d) zustand.sperrtage = [...zustand.sperrtage.filter((s) => s.datum < heute()), ...sperren];
    protokoll(b.id, "kapazitaet_geaendert");
    return { plan: zustand.kapazitaet, sperrtage: zustand.sperrtage.filter((s) => s.datum >= heute()), tage: tage() };
  }],
  ["GET", /^widerrufe$/, () => {
    pruefen("", false);
    return { widerrufe: widerrufListe() };
  }],
  ["POST", /^widerrufe\/(\d+)\/erledigt$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true);
    const w = zustand.widerrufe.find((x) => x.id === Number(m[1]));
    if (w && !w.bearbeitet) w.bearbeitet = iso();
    protokoll(b.id, "widerruf_bearbeitet", m[1]);
    return { widerrufe: widerrufListe() };
  }],
  ["GET", /^protokoll$/, () => {
    pruefen("", false, true, "inhaber");
    return { eintraege: [...zustand.protokoll].reverse().slice(0, 300).map((p) => ({ id: p.id, zeit: p.zeit, aktion: p.aktion, objekt: p.objekt, details: p.details, benutzer: zustand.benutzer.find((b) => b.id === p.benutzer_id)?.anzeigename || null })) };
  }],
  ["GET", /^benutzer$/, () => {
    pruefen("", false, true, "inhaber");
    return { benutzer: benutzerListe() };
  }],
  ["POST", /^benutzer$/, (d, csrf) => {
    const b = pruefen(csrf, true, true, "inhaber");
    const v = Pruefung.nur(d, ["name", "anzeigename", "rolle"]);
    let name = v.text("name", 3, 32);
    const anzeige = v.name("anzeigename");
    const rolle = v.auswahl("rolle", ["inhaber", "werkstatt"]);
    v.pruefen();
    name = name.toLowerCase();
    if (!/^[a-z][a-z0-9.-]{2,31}$/.test(name)) throw ungueltig({ name: "3 bis 32 Zeichen: Kleinbuchstaben, Ziffern, Punkt, Bindestrich." });
    if (zustand.benutzer.some((x) => x.name === name)) throw ungueltig({ name: "Diesen Namen gibt es schon." });
    const start = [...crypto.getRandomValues(new Uint8Array(16))].map((x) => "abcdefghjkmnpqrstuvwxyz23456789"[x % 31]).join("").replace(/(.{4})(?!$)/g, "$1-");
    const id = Math.max(...zustand.benutzer.map((x) => x.id)) + 1;
    zustand.benutzer.push({ id, name, anzeigename: anzeige, rolle, passwort: start, totp: null, totp_aktiv: 0, totp_letzter: 0, passwort_wechseln: 1, aktiv: 1, fehlversuche: 0, gesperrt_bis: null, letzte_anmeldung: null, erstellt: iso(), ersatz: [] });
    protokoll(b.id, "benutzer_angelegt", name, rolle);
    return [201, { id, startpasswort: start, hinweis: "Das Startpasswort wird nur jetzt angezeigt und muss bei der ersten Anmeldung geändert werden." }];
  }],
  ["POST", /^benutzer\/(\d+)\/sperren$/, (d, csrf, q, m) => {
    const b = pruefen(csrf, true, true, "inhaber");
    if (Number(m[1]) === b.id) throw new Fehler(409, "selbst", "Sie können sich nicht selbst sperren.");
    const ziel = zustand.benutzer.find((x) => x.id === Number(m[1]));
    if (ziel) ziel.aktiv = 0;
    protokoll(b.id, "benutzer_gesperrt", m[1]);
    return { benutzer: benutzerListe() };
  }],
  ["GET", /^post$/, () => {
    pruefen("", false, true, "inhaber");
    return { post: [...zustand.post].reverse().slice(0, 50) };
  }],
];

const benutzerListe = () => zustand.benutzer.map((b) => ({ id: b.id, name: b.name, anzeigename: b.anzeigename, rolle: b.rolle, totp_aktiv: b.totp_aktiv, aktiv: b.aktiv, letzte_anmeldung: b.letzte_anmeldung, erstellt: b.erstellt }));
const widerrufListe = () => [...zustand.widerrufe].reverse().map((w) => ({
  id: w.id, kennung: w.kennung, eingang: w.eingang, auftragsnummer: w.auftragsnummer, zugeordnet: w.auftrag_id !== null, auftrag_id: w.auftrag_id,
  name: w.name, email: w.email, grund: w.grund, bearbeitet: w.bearbeitet,
}));

export async function anfrage(methode, pfad, daten, { csrf = "" } = {}) {
  await laden();
  const koerper = daten === null || daten === undefined ? null : JSON.parse(JSON.stringify(daten));
  const [weg, abfrage = ""] = pfad.split("?");
  const q = new URLSearchParams(abfrage);
  await new Promise((r) => setTimeout(r, 90 + Math.random() * 120));
  try {
    if (methode === "POST" && koerper === null) throw new Fehler(415, "nur_json", "Bitte als JSON senden.");
    if (JSON.stringify(koerper || {}).length > 65536) throw new Fehler(413, "zu_gross", "Die Anfrage ist zu groß.");
    let ergebnis;
    if (weg.startsWith("verwaltung/")) {
      const rest = weg.slice(11);
      const treffer = verwaltung.map(([m, re, f]) => [m, rest.match(re), f]).filter(([, t]) => t);
      if (!treffer.length) throw new Fehler(404, "nicht_gefunden", "Diese Adresse gibt es nicht.");
      const passend = treffer.find(([m]) => m === methode);
      if (!passend) throw new Fehler(405, "methode", "Diese Methode ist hier nicht erlaubt.");
      ergebnis = await passend[2](koerper || {}, csrf, q, passend[1]);
    } else {
      const f = oeffentlich[`${methode} ${weg}`];
      if (!f) throw new Fehler(404, "nicht_gefunden", "Diese Adresse gibt es nicht.");
      ergebnis = await f(koerper || {});
    }
    speichern();
    const [status, antwort] = Array.isArray(ergebnis) ? ergebnis : [200, ergebnis];
    return { status, daten: JSON.parse(JSON.stringify(antwort)) };
  } catch (f) {
    speichern();
    if (f instanceof Fehler) return { status: f.status, daten: { fehler: f.fehler, meldung: f.message, ...(f.felder ? { felder: f.felder } : {}) } };
    console.error(f);
    return { status: 500, daten: { fehler: "intern", meldung: "Da ist etwas schiefgegangen. Bitte versuchen Sie es später noch einmal." } };
  }
}

export async function zugangsdaten() {
  await laden();
  const s = zustand.sitzung;
  const b = (s && zustand.benutzer.find((x) => x.id === s.benutzer_id && x.totp)) || zustand.benutzer[0];
  return {
    benutzer: "inhaberin",
    passwort: DEMO_PASSWORT,
    fuer: b.name,
    code: await totpCode(b.totp || DEMO_GEHEIMNIS, Math.floor(Date.now() / 30000)),
    restSekunden: 30 - (Math.floor(Date.now() / 1000) % 30),
  };
}

export async function beispielLink() {
  const d = await json("assets/daten/vorfuehrdaten.json");
  const e = d.auftraege.find((a) => a.status === "wartet_auf_freigabe") || d.auftraege[0];
  return new URL(`status/#t=${e.token}`, BASIS).href;
}
