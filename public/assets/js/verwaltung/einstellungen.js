import { zustand, va, el, leeren, seitenkopf, tafel, feld, absenden, formularmeldung, hinweis, rueckfrage, leer, istInhaber, ereignisse, VORFUEHRUNG } from "./gemeinsam.js";
import { zeitpunkt } from "../dom.js";

export async function ansicht(weg, ziel) {
  const ansichten = { widerrufe, protokoll, benutzer, post, konto };
  return (ansichten[weg] || konto)(ziel);
}

async function widerrufe(ziel) {
  const { widerrufe: liste } = await va("widerrufe");
  const zeichnen = (eintraege) => {
    leeren(ziel).append(
      seitenkopf("Widerrufe", "Eingänge über den Widerrufsknopf der Website. Die Kundin oder der Kunde hat sofort eine Eingangsbestätigung per Mail bekommen."),
      eintraege.length
        ? el("div", { klasse: "tafel tafel--tabelle" }, el("table", { klasse: "vw-tabelle vw-tabelle--auftraege" },
          el("thead", {}, el("tr", {},
            el("th", { scope: "col", text: "Eingang" }), el("th", { scope: "col", text: "Kennung" }), el("th", { scope: "col", text: "Auftrag" }),
            el("th", { scope: "col", text: "Von" }), el("th", { scope: "col", text: "Grund" }), el("th", { scope: "col", text: "Stand" }),
          )),
          el("tbody", {}, eintraege.map((w) => el("tr", { klasse: w.bearbeitet ? null : "ist-neu" },
            el("td", { "data-titel": "Eingang", klasse: "zahl", text: zeitpunkt(w.eingang) }),
            el("td", { "data-titel": "Kennung", klasse: "zahl", text: w.kennung }),
            el("td", { "data-titel": "Auftrag" }, w.zugeordnet ? el("a", { klasse: "vw-nummer zahl", href: `#auftrag/${w.auftrag_id}`, text: w.auftragsnummer }) : el("span", {}, el("span", { klasse: "zahl", text: w.auftragsnummer || "–" }), el("span", { klasse: "vw-tabelle__neben", text: "Keinem Auftrag zugeordnet, bitte prüfen" }))),
            el("td", { "data-titel": "Von" }, el("span", { text: w.name }), el("a", { klasse: "vw-tabelle__neben", href: "mailto:" + w.email, text: w.email })),
            el("td", { "data-titel": "Grund", text: w.grund || "ohne Angabe" }),
            el("td", { "data-titel": "Stand" }, w.bearbeitet
              ? el("span", { text: "Bearbeitet " + zeitpunkt(w.bearbeitet) })
              : el("button", {
                klasse: "knopf knopf--leise", type: "button", text: "Als bearbeitet markieren",
                onclick: async (e) => {
                  const ok = await rueckfrage({ titel: "Widerruf bearbeitet?", text: "Bitte erst den Betrag erstatten bzw. die Arbeiten stoppen und der Kundin oder dem Kunden antworten. Danach hier abhaken.", knopf: "Als bearbeitet markieren" });
                  if (!ok) return;
                  e.target.disabled = true;
                  try {
                    zeichnen((await va(`widerrufe/${w.id}/erledigt`, { methode: "POST", daten: {} })).widerrufe);
                    hinweis("Widerruf als bearbeitet markiert.");
                    ereignisse.dispatchEvent(new Event("zahlen"));
                  } catch (f) {
                    hinweis(f.message, "fehler");
                    e.target.disabled = false;
                  }
                },
              })),
          ))),
        ))
        : leer("Bisher ist kein Widerruf eingegangen."),
      tafel("Was zu tun ist",
        el("ol", { klasse: "vw-liste" },
          el("li", { text: "Prüfen, ob der Widerruf in der Frist liegt (14 Tage ab Freigabe des Kostenvoranschlags)." }),
          el("li", { text: "Arbeiten stoppen, sofern noch nicht ausgeführt. Bei gewünschtem sofortigem Beginn ist ein anteiliger Betrag für bereits geleistete Arbeit fällig." }),
          el("li", { text: "Bereits gezahlte Beträge innerhalb von 14 Tagen auf demselben Zahlungsweg zurückzahlen." }),
        ),
      ),
    );
    ziel.querySelector("h1")?.focus({ preventScroll: true });
  };
  zeichnen(liste);
}

const AKTIONEN = {
  anmeldung: "Angemeldet", anmeldung_falsch: "Anmeldung fehlgeschlagen", anmeldung_gesperrt: "Anmeldung bei gesperrtem Konto", code_falsch: "Falscher Zwei-Faktor-Code",
  ersatzcode_verwendet: "Ersatzcode verwendet", passwort_geaendert: "Passwort geändert", zweifaktor_eingerichtet: "Zwei-Faktor eingerichtet",
  benutzer_angelegt: "Benutzer angelegt", benutzer_gesperrt: "Benutzer gesperrt", auftrag_angesehen: "Auftrag angesehen", auftrag_angelegt: "Auftrag eingetragen",
  status: "Status geändert", angebot_erstellt: "Kostenvoranschlag gesendet", angebot_angenommen: "Kostenvoranschlag freigegeben (Kunde)", angebot_abgelehnt: "Kostenvoranschlag abgelehnt (Kunde)",
  notiz: "Notiz gespeichert", auskunft_erstellt: "Auskunft erstellt", anonymisiert: "Personendaten gelöscht", kapazitaet_geaendert: "Wochenplan geändert",
  widerruf_eingegangen: "Widerruf eingegangen", widerruf_bearbeitet: "Widerruf bearbeitet", kunde_abgesagt: "Termin abgesagt (Kunde)", kunde_auskunft: "Auskunft abgerufen (Kunde)",
  kunde_loeschung_eingeschraenkt: "Löschung eingeschränkt, Gewährleistung (Kunde)", link_erneuert: "Status-Link neu verschickt", anfrage_verworfen: "Anfrage als Spam verworfen", aufgaben: "Tägliche Aufräumarbeiten",
};
const KRITISCH = new Set(["anmeldung_falsch", "anmeldung_gesperrt", "code_falsch", "ersatzcode_verwendet", "anonymisiert", "auskunft_erstellt", "benutzer_gesperrt"]);

async function protokoll(ziel) {
  const { eintraege } = await va("protokoll");
  let filter = "alle";
  const liste = el("div", { klasse: "tafel tafel--tabelle" });
  const zeichnen = () => {
    const sicht = eintraege.filter((e) => filter === "alle" || (filter === "sicherheit" ? KRITISCH.has(e.aktion) || e.aktion.startsWith("anmeldung") : e.aktion === "auftrag_angesehen" || e.aktion === "auskunft_erstellt"));
    leeren(liste).append(sicht.length
      ? el("table", { klasse: "vw-tabelle vw-tabelle--protokoll" },
        el("thead", {}, el("tr", {}, ["Zeit", "Wer", "Was", "Betrifft", "Einzelheiten"].map((t) => el("th", { scope: "col", text: t })))),
        el("tbody", {}, sicht.map((e) => el("tr", { klasse: KRITISCH.has(e.aktion) ? "ist-auffaellig" : null },
          el("td", { "data-titel": "Zeit", klasse: "zahl", text: zeitpunkt(e.zeit) }),
          el("td", { "data-titel": "Wer", text: e.benutzer || "Website / System" }),
          el("td", { "data-titel": "Was", text: AKTIONEN[e.aktion] || e.aktion }),
          el("td", { "data-titel": "Betrifft", klasse: "zahl", text: e.objekt || "" }),
          el("td", { "data-titel": "Einzelheiten", text: e.details || "" }),
        ))))
      : leer("Keine Einträge für diese Auswahl."));
  };
  const auswahl = el("div", { klasse: "vw-segmente", role: "group", "aria-label": "Einträge filtern" },
    [["alle", "Alle"], ["sicherheit", "Anmeldung und Sicherheit"], ["zugriffe", "Zugriffe auf Personendaten"]].map(([w, t]) => el("button", {
      type: "button", "aria-pressed": String(w === filter), text: t,
      onclick: (e) => {
        filter = w;
        for (const b of auswahl.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === e.currentTarget));
        zeichnen();
      },
    })),
  );
  ziel.append(
    seitenkopf("Zugriffsprotokoll", "Wer hat wann was getan. Die letzten 300 Einträge, gelöscht wird nach zwölf Monaten. Ohne IP-Adressen und ohne Inhalte."),
    auswahl,
    liste,
  );
  zeichnen();
}

async function benutzer(ziel) {
  const { benutzer: liste } = await va("benutzer");
  const tabelle = (eintraege) => el("table", { klasse: "vw-tabelle vw-tabelle--auftraege" },
    el("thead", {}, el("tr", {}, ["Name", "Benutzername", "Rolle", "Zwei-Faktor", "Zuletzt angemeldet"].map((t) => el("th", { scope: "col", text: t })), el("th", { scope: "col" }, el("span", { klasse: "unsichtbar", text: "Aktion" })))),
    el("tbody", {}, eintraege.map((b) => el("tr", { klasse: b.aktiv ? null : "ist-aus" },
      el("td", { "data-titel": "Name", text: b.anzeigename }),
      el("td", { "data-titel": "Benutzername", klasse: "zahl", text: b.name }),
      el("td", { "data-titel": "Rolle", text: b.rolle === "inhaber" ? "Inhaberin" : "Werkstatt" }),
      el("td", { "data-titel": "Zwei-Faktor", text: b.totp_aktiv ? "eingerichtet" : "noch nicht" }),
      el("td", { "data-titel": "Zuletzt angemeldet", klasse: "zahl", text: b.letzte_anmeldung ? zeitpunkt(b.letzte_anmeldung) : "noch nie" }),
      el("td", { "data-titel": "Aktion" }, !b.aktiv ? el("span", { text: "gesperrt" }) : b.name === zustand.ich.name ? el("span", { klasse: "vw-still", text: "Sie" }) : el("button", {
        klasse: "knopf knopf--leise", type: "button", text: "Sperren",
        onclick: async () => {
          const ok = await rueckfrage({ titel: `${b.anzeigename} sperren?`, text: "Alle Sitzungen enden sofort, eine Anmeldung ist nicht mehr möglich. Einträge im Protokoll bleiben erhalten.", knopf: "Sperren", gefahr: true });
          if (!ok) return;
          try {
            const r = await va(`benutzer/${b.id}/sperren`, { methode: "POST", daten: {} });
            leeren(tafelInhalt).append(tabelle(r.benutzer));
            hinweis(`${b.anzeigename} ist gesperrt.`);
          } catch (f) {
            hinweis(f.message, "fehler");
          }
        },
      })),
    ))),
  );
  const tafelInhalt = el("div", { klasse: "tafel tafel--tabelle" }, tabelle(liste));
  const ergebnis = el("div", { "aria-live": "polite" });
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    el("div", { klasse: "raster-2 raster-2--eng" },
      feld({ name: "anzeigename", label: "Name", pflicht: true, attribute: { maxlength: "80", autocomplete: "off" } }),
      feld({ name: "name", label: "Benutzername", pflicht: true, hilfe: "Kleinbuchstaben, Ziffern, Punkt oder Bindestrich, z. B. jonas.k", attribute: { maxlength: "32", autocomplete: "off", autocapitalize: "none", spellcheck: "false" } }),
      feld({ name: "rolle", label: "Rolle", typ: "select", pflicht: true, wert: "werkstatt", attribute: { optionen: [["werkstatt", "Werkstatt: Aufträge, Termine, Widerrufe"], ["inhaber", "Inhaberin: zusätzlich Benutzer, Protokoll, Löschung"]] } }),
    ),
    el("button", { klasse: "knopf", type: "submit", text: "Benutzer anlegen" }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const r = await va("benutzer", { methode: "POST", daten: { name: form.name.value.trim(), anzeigename: form.anzeigename.value.trim(), rolle: form.rolle.value } });
      leeren(ergebnis).append(el("div", { klasse: "meldung meldung--gut startpasswort" },
        el("p", { text: `Startpasswort für ${form.name.value.trim()}:` }),
        el("p", { klasse: "vw-schluessel zahl", text: r.startpasswort }),
        el("p", { text: r.hinweis + " Am besten persönlich übergeben, nicht per Mail." }),
      ));
      form.reset();
      leeren(tafelInhalt).append(tabelle((await va("benutzer")).benutzer));
    });
  });
  ziel.append(
    seitenkopf("Benutzer", "Jede Person bekommt einen eigenen Zugang. So bleibt im Protokoll nachvollziehbar, wer was getan hat."),
    tafelInhalt,
    tafel("Neuen Zugang anlegen", el("p", { klasse: "vw-still", text: "Bei der ersten Anmeldung muss die Person ein eigenes Passwort wählen und die Zwei-Faktor-Anmeldung einrichten." }), form, ergebnis),
  );
}

async function post(ziel) {
  const { post: liste } = await va("post");
  ziel.append(
    seitenkopf("Postausgang", VORFUEHRUNG ? "In der Vorführung werden keine Mails verschickt. Hier steht, was Kundinnen und Kunden bekommen würden." : "Testbetrieb: Mails werden nicht verschickt, sondern hier abgelegt."),
    liste.length
      ? el("ol", { klasse: "postliste" }, liste.map((m) => el("li", {},
        el("details", {},
          el("summary", {}, el("strong", { text: m.betreff }), el("span", { text: `an ${m.an} · ${zeitpunkt(m.erstellt)}` })),
          el("pre", { klasse: "postliste__text", text: m.text }),
        ),
      )))
      : leer("Noch keine Mails."),
  );
}

async function konto(ziel) {
  const ich = zustand.ich;
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    feld({ name: "alt", label: "Bisheriges Passwort", typ: "password", pflicht: true, attribute: { autocomplete: "current-password" } }),
    feld({ name: "neu", label: "Neues Passwort", typ: "password", pflicht: true, hilfe: "Mindestens 12 Zeichen. Danach sind Sie überall abgemeldet und melden sich neu an.", attribute: { autocomplete: "new-password", minlength: "12", maxlength: "128" } }),
    el("button", { klasse: "knopf", type: "submit", text: "Passwort ändern" }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const r = await va("passwort", { methode: "POST", daten: { alt: form.alt.value, neu: form.neu.value } });
      ereignisse.dispatchEvent(new CustomEvent("abgemeldet", { detail: r.meldung }));
    });
  });
  ziel.append(
    seitenkopf("Mein Konto"),
    el("div", { klasse: "raster-2" },
      tafel("Zugang",
        el("dl", { klasse: "vw-daten" },
          el("dt", { text: "Name" }), el("dd", { text: ich.anzeigename }),
          el("dt", { text: "Benutzername" }), el("dd", { klasse: "zahl", text: ich.name }),
          el("dt", { text: "Rolle" }), el("dd", { text: istInhaber() ? "Inhaberin" : "Werkstatt" }),
          el("dt", { text: "Zwei-Faktor" }), el("dd", { text: "eingerichtet" }),
        ),
        el("p", { klasse: "vw-still", text: "Telefon verloren? Mit einem Ersatzcode anmelden und die Inhaberin bitten, den Zugang neu anzulegen." }),
      ),
      tafel("Passwort ändern", form),
    ),
  );
}
