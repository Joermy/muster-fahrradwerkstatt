import { zustand, ereignisse, va, el, leeren, istInhaber, hinweis, VORFUEHRUNG, ApiFehler } from "./gemeinsam.js";
import { anmeldungZeigen, einrichtungZeigen } from "./anmeldung.js";

const inhalt = document.querySelector("[data-inhalt]");
const nav = document.querySelector("[data-nav]");
const konto = document.querySelector("[data-konto]");
const menueknopf = document.querySelector("[data-menue]");

const ANSICHTEN = [
  { weg: "start", text: "Übersicht", laden: () => import("./uebersicht.js") },
  { weg: "auftraege", text: "Aufträge", laden: () => import("./auftraege.js"), zaehler: "angefragt" },
  { weg: "neu", text: "Anfrage eintragen", laden: () => import("./auftraege.js"), nebenweg: true },
  { weg: "auftrag", laden: () => import("./auftraege.js"), versteckt: true, gehoertZu: "auftraege" },
  { weg: "kalender", text: "Termine und Kapazität", laden: () => import("./kalender.js") },
  { weg: "widerrufe", text: "Widerrufe", laden: () => import("./einstellungen.js"), zaehler: "widerrufe_offen" },
  { weg: "protokoll", text: "Zugriffsprotokoll", laden: () => import("./einstellungen.js"), inhaber: true },
  { weg: "benutzer", text: "Benutzer", laden: () => import("./einstellungen.js"), inhaber: true },
  { weg: "post", text: "Postausgang", laden: () => import("./einstellungen.js"), inhaber: true, nurTest: true },
  { weg: "konto", text: "Mein Konto", laden: () => import("./einstellungen.js"), versteckt: true },
];

let zaehler = {};

function hashLesen() {
  const roh = decodeURIComponent(location.hash.replace(/^#/, ""));
  const [pfad, abfrage = ""] = roh.split("?");
  const [weg, ...teile] = pfad.split("/");
  return { weg: weg || "start", teile, abfrage: new URLSearchParams(abfrage) };
}

function navBauen() {
  const aktuell = hashLesen().weg;
  const aktiv = ANSICHTEN.find((a) => a.weg === aktuell)?.gehoertZu || aktuell;
  const sichtbar = ANSICHTEN.filter((a) => !a.versteckt && (!a.inhaber || istInhaber()) && (!a.nurTest || zustand.ich.entwicklung || VORFUEHRUNG));
  leeren(nav).append(
    el("ul", {}, sichtbar.map((a) => {
      const n = a.zaehler ? zaehler[a.zaehler] || 0 : 0;
      return el("li", { klasse: a.nebenweg ? "vw-nav__neben" : null },
        el("a", { href: "#" + a.weg, "aria-current": a.weg === aktiv ? "page" : null },
          el("span", { text: a.text }),
          n > 0 ? el("span", { klasse: "vw-nav__zahl", text: String(n), "aria-label": `${n} offen` }) : null,
        ));
    })),
  );
  nav.hidden = false;
  menueknopf.hidden = false;
}

function kontoBauen() {
  const ich = zustand.ich;
  leeren(konto).append(
    el("a", { klasse: "vw-konto__name", href: "#konto" },
      el("span", { text: ich.anzeigename }),
      el("small", { text: ich.rolle === "inhaber" ? "Inhaberin" : "Werkstatt" })),
    el("button", { klasse: "vw-konto__ab", type: "button", text: "Abmelden", onclick: abmelden }),
  );
  konto.hidden = false;
}

export async function zahlenAktualisieren() {
  try {
    const u = await va("uebersicht");
    zaehler = u.zahlen;
    navBauen();
    return u;
  } catch {
    return null;
  }
}

async function abmelden() {
  try {
    await va("abmelden", { methode: "POST", daten: {} });
  } catch {
  }
  zustand.ich = null;
  zustand.csrf = "";
  oberflaecheLeeren();
  anmeldungZeigen(inhalt, starten, "Sie sind abgemeldet.");
}

function oberflaecheLeeren() {
  nav.hidden = true;
  konto.hidden = true;
  menueknopf.hidden = true;
  document.body.classList.remove("ist-angemeldet");
  for (const d of document.querySelectorAll("dialog")) d.remove();
}

let ladeNummer = 0;
async function zeigen() {
  if (!zustand.ich) return;
  const { weg, teile, abfrage } = hashLesen();
  let ansicht = ANSICHTEN.find((a) => a.weg === weg);
  if (!ansicht || (ansicht.inhaber && !istInhaber())) ansicht = ANSICHTEN[0];
  navBauen();
  nav.classList.remove("ist-offen");
  menueknopf.setAttribute("aria-expanded", "false");
  const nummer = ++ladeNummer;
  inhalt.setAttribute("aria-busy", "true");
  try {
    const modul = await ansicht.laden();
    if (nummer !== ladeNummer) return;
    leeren(inhalt);
    await modul.ansicht(ansicht.weg, inhalt, { teile, abfrage, neuLaden: zeigen });
  } catch (f) {
    if (f instanceof ApiFehler && (f.status === 401 || f.kennung === "einrichtung_noetig")) return;
    leeren(inhalt).append(el("div", { klasse: "meldung meldung--fehler", role: "alert" }, el("p", { text: f.message || "Die Ansicht konnte nicht geladen werden." })));
  } finally {
    if (nummer === ladeNummer) inhalt.removeAttribute("aria-busy");
  }
  const h1 = inhalt.querySelector("h1");
  if (h1 && nummer === ladeNummer) h1.focus({ preventScroll: true });
  document.title = (h1 ? h1.textContent + " – " : "") + "Verwaltung – Radhaus Fuhse";
}

async function starten() {
  let ich;
  try {
    ich = await va("ich");
  } catch (f) {
    oberflaecheLeeren();
    anmeldungZeigen(inhalt, starten, f instanceof ApiFehler && f.status === 401 ? null : f.message);
    return;
  }
  zustand.ich = ich;
  zustand.csrf = ich.csrf;
  if (ich.passwort_wechseln || !ich.zweifaktor) {
    oberflaecheLeeren();
    einrichtungZeigen(inhalt, ich, starten);
    return;
  }
  document.body.classList.add("ist-angemeldet");
  kontoBauen();
  await zahlenAktualisieren();
  zeigen();
}

ereignisse.addEventListener("abgemeldet", (e) => {
  if (!zustand.ich) return;
  zustand.ich = null;
  zustand.csrf = "";
  oberflaecheLeeren();
  anmeldungZeigen(inhalt, starten, e.detail);
});
ereignisse.addEventListener("einrichten", () => starten());
ereignisse.addEventListener("zahlen", () => zahlenAktualisieren());

window.addEventListener("hashchange", zeigen);

menueknopf.addEventListener("click", () => {
  const offen = nav.classList.toggle("ist-offen");
  menueknopf.setAttribute("aria-expanded", String(offen));
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && nav.classList.contains("ist-offen")) {
    nav.classList.remove("ist-offen");
    menueknopf.setAttribute("aria-expanded", "false");
    menueknopf.focus();
  }
});

for (const art of ["pointerdown", "keydown"]) {
  document.addEventListener(art, () => {
    if (zustand.ich && Date.now() - zustand.letzteAnfrage > 10 * 60 * 1000) va("ich").catch(() => {});
  }, { passive: true });
}
setInterval(() => {
  const still = Date.now() - zustand.letzteAnfrage;
  if (zustand.ich && still > 27 * 60 * 1000 && still < 28 * 60 * 1000) {
    hinweis("Ohne Aktivität endet die Sitzung in drei Minuten. Klicken Sie irgendwo, um angemeldet zu bleiben.", "warnung");
  }
}, 60 * 1000);

starten();
