import { api, ApiFehler, BASIS } from "./api.js";
import { el, leeren, euro, datum, feldfehler } from "./dom.js";

const formular = document.querySelector("[data-termin]");
const schritte = [...formular.querySelectorAll("[data-schritt]")];
const anzeigen = [...document.querySelectorAll("[data-schritt-anzeige]")];
const zurueck = formular.querySelector("[data-zurueck]");
const weiter = formular.querySelector("[data-weiter]");
const senden = formular.querySelector("[data-senden]");
const kalender = formular.querySelector("[data-kalender]");
const sendefehler = formular.querySelector("[data-sendefehler]");

const stand = { schritt: 1, datum: null, zeit: null, formular: null, katalog: null };

const WOCHENTAGE = ["", "Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

async function katalogLaden() {
  stand.katalog = await fetch(new URL("assets/daten/leistungen.json", BASIS)).then((r) => r.json());
  const vorgabe = new URLSearchParams(location.search).get("leistung");
  const leistungen = formular.querySelector("[data-leistungen]");
  for (const l of stand.katalog.leistungen) {
    const id = `l-${l.kennung}`;
    const radio = el("input", { type: "radio", name: "leistung", value: l.kennung, id, required: true });
    if (l.kennung === vorgabe) radio.checked = true;
    leistungen.append(el("label", { for: id }, radio, el("b", { text: l.titel }), el("span", { text: `${euro(l.preis_cent)} ${l.einheit}` })));
  }
  const raeder = formular.querySelector("[data-raeder]");
  for (const r of stand.katalog.raeder) {
    const id = `r-${r.kennung}`;
    raeder.append(el("label", { for: id }, el("input", { type: "radio", name: "rad", value: r.kennung, id, required: true }), el("b", { text: r.titel })));
  }
}

async function termineLaden() {
  leeren(kalender).append(el("p", { text: "Freie Zeiten werden geladen …" }));
  try {
    const t = await api("termine");
    stand.formular = t.formular;
    leeren(kalender);
    for (const tag of t.tage) {
      const kopf = el("h3", {}, `${WOCHENTAGE[tag.wochentag]}, ${datum(tag.datum, false).slice(0, 6)}`);
      if (!tag.zeiten.length) {
        kalender.append(el("div", { klasse: "tag tag--zu" }, kopf, el("p", { text: tag.grund || "geschlossen" })));
        continue;
      }
      const knoepfe = el("div", { klasse: "zeiten-knoepfe" });
      for (const z of tag.zeiten) {
        const gewaehlt = stand.datum === tag.datum && stand.zeit === z.zeit;
        const k = el("button", {
          type: "button",
          "aria-pressed": gewaehlt ? "true" : "false",
          disabled: z.frei < 1,
          "aria-label": `${datum(tag.datum)}, ${z.zeit} Uhr${z.frei < 1 ? ", vergeben" : ""}`,
          text: z.zeit,
          onclick: () => {
            stand.datum = tag.datum;
            stand.zeit = z.zeit;
            for (const b of kalender.querySelectorAll("button[aria-pressed]")) b.setAttribute("aria-pressed", "false");
            k.setAttribute("aria-pressed", "true");
            formular.querySelector('[data-fehler="termin"]').textContent = "";
          },
        });
        if (z.frei < 1 && gewaehlt) {
          stand.datum = null;
          stand.zeit = null;
        }
        knoepfe.append(k);
      }
      kalender.append(el("div", { klasse: "tag" }, kopf, knoepfe));
    }
  } catch (e) {
    leeren(kalender).append(el("p", { klasse: "fehlertext", text: e.message }));
  }
}

function wert(name) {
  const f = formular.elements[name];
  if (!f) return "";
  return (f.value ?? "").trim();
}

function pruefen(schritt) {
  const fehler = {};
  if (schritt === 1) {
    if (!wert("leistung")) fehler.schritt1 = "Bitte eine Leistung wählen.";
    else if (!wert("rad")) fehler.schritt1 = "Bitte wählen Sie Ihren Radtyp.";
  }
  if (schritt === 2 && !stand.datum) fehler.termin = "Bitte eine freie Zeit wählen.";
  if (schritt === 3) {
    const name = wert("name");
    if (name.length < 2) fehler.name = "Bitte Ihren Namen angeben.";
    else if (!/^[\p{L}][\p{L}\p{M} .'-]*$/u.test(name)) fehler.name = "Bitte nur Buchstaben, Leerzeichen, Punkt, Bindestrich oder Apostroph.";
    const email = wert("email");
    if (!/^[^\s@,;<>"]+@[^\s@,;<>"]+\.[^\s@,;<>"]{2,}$/.test(email)) fehler.email = "Bitte eine gültige E-Mail-Adresse angeben.";
    const tel = wert("telefon");
    if (tel && !/^\+?[0-9][0-9 ()/-]{4,23}$/.test(tel)) fehler.telefon = "Bitte nur Ziffern, Leerzeichen, +, -, / und Klammern.";
  }
  if (schritt === 1 || schritt === 2) {
    for (const f of formular.querySelectorAll("[data-fehler]")) if (fehler[f.dataset.fehler] === undefined && (f.dataset.fehler === "schritt1" || f.dataset.fehler === "termin")) f.textContent = "";
    for (const [k, v] of Object.entries(fehler)) formular.querySelector(`[data-fehler="${k}"]`).textContent = v;
  } else {
    feldfehler(formular, fehler);
  }
  return Object.keys(fehler).length === 0;
}

function zeigen(n) {
  stand.schritt = n;
  schritte.forEach((s) => { s.hidden = Number(s.dataset.schritt) !== n; });
  anzeigen.forEach((a) => {
    const i = Number(a.dataset.schrittAnzeige);
    a.toggleAttribute("aria-current", i === n);
    if (i === n) a.setAttribute("aria-current", "step");
    a.classList.toggle("ist-erledigt", i < n);
  });
  zurueck.hidden = n === 1;
  weiter.hidden = n === 4;
  senden.hidden = n !== 4;
  if (n === 2) termineLaden();
  if (n === 4) zusammenfassen();
  const ziel = schritte[n - 1].querySelector("legend, h2, p, input");
  if (ziel) {
    ziel.setAttribute("tabindex", "-1");
    ziel.focus({ preventScroll: false });
  }
}

function zusammenfassen() {
  const l = stand.katalog.leistungen.find((x) => x.kennung === wert("leistung"));
  const r = stand.katalog.raeder.find((x) => x.kennung === wert("rad"));
  const z = formular.querySelector("[data-zusammenfassung]");
  leeren(z);
  const zeile = (k, v) => [el("dt", { text: k }), el("dd", { text: v })];
  z.append(
    ...zeile("Leistung", `${l.titel} (${euro(l.preis_cent)} ${l.einheit})`),
    ...zeile("Rad", r.titel),
    ...zeile("Termin", `${datum(stand.datum)}, ${stand.zeit} Uhr`),
    ...zeile("Name", wert("name")),
    ...zeile("E-Mail", wert("email")),
    ...zeile("Telefon", wert("telefon") || "–"),
    ...zeile("Nachricht", wert("nachricht") || "–"),
  );
}

weiter.addEventListener("click", () => {
  if (pruefen(stand.schritt)) zeigen(stand.schritt + 1);
});
zurueck.addEventListener("click", () => zeigen(stand.schritt - 1));

formular.addEventListener("submit", async (e) => {
  e.preventDefault();
  sendefehler.hidden = true;
  senden.disabled = true;
  senden.textContent = "Wird gesendet …";
  try {
    const antwort = await api("anfragen", {
      methode: "POST",
      daten: {
        leistung: wert("leistung"), rad: wert("rad"), datum: stand.datum, zeit: stand.zeit,
        name: wert("name"), email: wert("email"), telefon: wert("telefon"), nachricht: wert("nachricht"),
        firma: formular.elements.firma.value, formular: stand.formular,
      },
    });
    formular.hidden = true;
    document.querySelector("[data-schritte]").hidden = true;
    const erfolg = document.querySelector("[data-erfolg]");
    erfolg.hidden = false;
    erfolg.querySelector("[data-erfolg-nummer]").textContent = antwort.nummer;
    erfolg.querySelector("[data-erfolg-termin]").textContent = `${datum(stand.datum)}, ${stand.zeit} Uhr`;
    erfolg.querySelector("[data-erfolg-link]").href = new URL(`status/#t=${antwort.token}`, BASIS).href;
    erfolg.querySelector("[data-erfolg-fokus]").focus();
  } catch (f) {
    if (!(f instanceof ApiFehler)) throw f;
    if (f.kennung === "termin_belegt") {
      stand.datum = null;
      stand.zeit = null;
      zeigen(2);
      formular.querySelector('[data-fehler="termin"]').textContent = f.message;
    } else if (f.kennung === "ungueltig") {
      const schritt3 = ["name", "email", "telefon", "nachricht"];
      if (Object.keys(f.felder).some((k) => schritt3.includes(k))) {
        zeigen(3);
        feldfehler(formular, f.felder);
      } else {
        sendefehler.hidden = false;
        sendefehler.textContent = f.message;
      }
    } else {
      if (f.kennung === "bitte_erneut") {
        const t = await api("termine").catch(() => null);
        if (t) stand.formular = t.formular;
      }
      sendefehler.hidden = false;
      sendefehler.textContent = f.message;
    }
  } finally {
    senden.disabled = false;
    senden.textContent = "Termin anfragen";
  }
});

await katalogLaden();
api("termine").then((t) => { stand.formular = t.formular; }).catch(() => {});
