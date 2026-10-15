import { api, ApiFehler, BASIS, VORFUEHRUNG } from "./api.js";
import { el, leeren, euro, datum, zeitpunkt, feldfehler } from "./dom.js";

const bereich = document.querySelector("[data-status]");
const ohneLink = document.querySelector("[data-ohne-link]");
const einleitung = document.querySelector("[data-status-einleitung]");

function token() {
  const m = /(?:^|[#&])t=([A-Za-z0-9_-]{43})(?:&|$)/.exec(location.hash);
  return m ? m[1] : null;
}

async function laden() {
  const t = token();
  if (!t) {
    ohneLink.hidden = false;
    if (VORFUEHRUNG && !document.querySelector("[data-beispiel]")) {
      const { beispielLink } = await import("./vorfuehrung/server.js");
      ohneLink.before(el("div", { klasse: "meldung", daten: { beispiel: "" } },
        el("p", {}, el("strong", { text: "Vorführung: " }), el("span", { text: "In echt kommt der Link per Mail. Hier können Sie einen erfundenen Auftrag mit offenem Kostenvoranschlag öffnen." })),
        el("p", {}, el("a", { klasse: "knopf", href: await beispielLink(), text: "Beispielauftrag ansehen" })),
      ));
    }
    return;
  }
  document.querySelector("[data-beispiel]")?.remove();
  try {
    const s = await api("status", { methode: "POST", daten: { token: t } });
    zeichnen(s, t);
  } catch (f) {
    bereich.hidden = false;
    leeren(bereich).append(el("div", { klasse: "meldung meldung--fehler", role: "alert" }, el("p", { text: f.message })));
    ohneLink.hidden = false;
  }
}

function zeichnen(s, t) {
  einleitung.textContent = `Guten Tag ${s.vorname}, hier steht, wie weit wir mit Ihrem Rad sind.`;
  bereich.hidden = false;
  leeren(bereich);
  bereich.append(
    el("div", { klasse: "zwei" },
      el("div", {},
        el("div", { klasse: "anhaenger" },
          el("p", { klasse: "anhaenger__zeile", text: s.leistung + " · " + s.rad }),
          el("p", { klasse: "anhaenger__nummer zahl", text: s.nummer }),
          el("p", { klasse: "anhaenger__zeile" }, el("strong", { text: s.status_text })),
          el("p", { klasse: "anhaenger__zeile", text: `Termin: ${datum(s.termin.datum)}, ${s.termin.zeit} Uhr` }),
        ),
        el("ol", { klasse: "verlauf", "aria-label": "Verlauf" },
          s.verlauf.map((v) => el("li", {}, el("strong", { text: v.text }), v.hinweis ? el("span", { text: " – " + v.hinweis }) : null, el("time", { datetime: v.zeit, text: zeitpunkt(v.zeit) }))),
        ),
      ),
      el("div", {}, ...angebote(s, t), ...aktionen(s, t)),
    ),
  );
}

function angebote(s, t) {
  const teile = [];
  for (const a of s.angebote) {
    const tabelle = el("table", { klasse: "preistafel" },
      el("caption", { text: "Preise inklusive 19 % Umsatzsteuer." }),
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Position" }), el("th", { scope: "col", klasse: "preis", text: "Preis" }))),
      el("tbody", {},
        a.positionen.map((p) => el("tr", {}, el("td", { text: p.text }), el("td", { klasse: "preis" }, el("b", { text: euro(p.cent) })))),
        el("tr", {}, el("th", { scope: "row", text: "Summe" }), el("td", { klasse: "preis" }, el("b", { text: euro(a.summe_cent) }))),
      ),
    );
    const block = el("section", { klasse: "karte", "aria-labelledby": `angebot-${a.id}` },
      el("h2", { id: `angebot-${a.id}`, text: a.entscheidung ? "Zusatzarbeiten" : "Zusatzarbeiten freigeben?" }),
      el("p", { text: `Kostenvoranschlag vom ${zeitpunkt(a.erstellt)}.` }),
      tabelle,
    );
    if (!a.entscheidung) {
      const vorzeitig = el("input", { type: "checkbox", id: `vorzeitig-${a.id}` });
      const meldung = el("div", { klasse: "meldung meldung--fehler", role: "alert", hidden: true });
      const entscheiden = async (annehmen, knopf) => {
        knopf.disabled = true;
        try {
          await api("status/freigabe", { methode: "POST", daten: { token: t, angebot: a.id, annehmen, vorzeitig: annehmen && vorzeitig.checked } });
          laden();
        } catch (f) {
          meldung.hidden = false;
          meldung.textContent = f.message;
          knopf.disabled = false;
        }
      };
      block.append(
        el("p", {}, "Ohne Ihre Freigabe machen wir nur die vereinbarten Arbeiten. Für diesen Zusatzauftrag haben Sie ein Widerrufsrecht von 14 Tagen, siehe ",
          el("a", { href: new URL("widerrufsbelehrung/", BASIS).href, text: "Widerrufsbelehrung" }), "."),
        el("label", { klasse: "wahl", for: `vorzeitig-${a.id}` }, vorzeitig,
          el("span", { text: "Ich verlange ausdrücklich, dass Sie vor Ablauf der Widerrufsfrist mit den Arbeiten beginnen. Mir ist bekannt, dass ich mein Widerrufsrecht verliere, sobald die Arbeiten vollständig ausgeführt sind." })),
        el("p", { klasse: "hilfe", text: "Ohne dieses Häkchen beginnen wir erst nach Ablauf der 14 Tage, Ihr Rad bleibt so lange bei uns." }),
        meldung,
        el("div", { klasse: "formular-aktionen" },
          el("button", { klasse: "knopf", type: "button", text: `Zusatzarbeiten für ${euro(a.summe_cent)} zahlungspflichtig beauftragen`, onclick: (e) => entscheiden(true, e.currentTarget) }),
          el("button", { klasse: "knopf knopf--leise", type: "button", text: "Ablehnen", onclick: (e) => entscheiden(false, e.currentTarget) }),
        ),
      );
    } else if (a.entscheidung === "angenommen") {
      block.append(el("p", {}, el("strong", { text: `Beauftragt am ${zeitpunkt(a.entschieden)}.` }), " Die Vertragsbestätigung mit Widerrufsbelehrung haben wir Ihnen per Mail geschickt."));
      if (a.widerrufbar) {
        block.append(el("p", {}, `Widerrufen können Sie bis zum ${datum(a.widerruf_bis)}.`),
          el("p", {}, el("a", { klasse: "knopf knopf--leise", href: new URL(`widerruf/#nr=${s.nummer}`, BASIS).href, text: "Vertrag widerrufen" })));
      }
    } else {
      block.append(el("p", { text: `Abgelehnt am ${zeitpunkt(a.entschieden)}. Wir machen nur die vereinbarten Arbeiten.` }));
    }
    teile.push(block);
  }
  return teile;
}

function aktionen(s, t) {
  const meldung = el("div", { klasse: "meldung", role: "status", hidden: true });
  const zeigen = (text, art = "") => {
    meldung.hidden = false;
    meldung.className = "meldung" + (art ? ` meldung--${art}` : "");
    meldung.textContent = text;
  };
  const kasten = el("section", { "aria-labelledby": "ihre-daten" }, el("h2", { id: "ihre-daten", text: "Ihr Termin und Ihre Daten" }), meldung);

  if (s.absagen_moeglich) {
    kasten.append(el("p", {}, el("button", { klasse: "knopf knopf--leise", type: "button", text: "Termin absagen", onclick: async (e) => {
      if (!confirm("Termin wirklich absagen?")) return;
      e.currentTarget.disabled = true;
      try {
        await api("status/absagen", { methode: "POST", daten: { token: t } });
        laden();
      } catch (f) {
        zeigen(f.message, "fehler");
      }
    } })));
  }
  kasten.append(
    el("p", { text: "Alles, was wir zu diesem Auftrag gespeichert haben, als Datei:" }),
    el("p", {}, el("button", { klasse: "knopf knopf--leise", type: "button", text: "Meine Daten herunterladen", onclick: async () => {
      try {
        const d = await api("status/auskunft", { methode: "POST", daten: { token: t } });
        const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
        const a = el("a", { href: URL.createObjectURL(blob), download: `radhaus-${s.nummer}.json` });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      } catch (f) {
        zeigen(f.message, "fehler");
      }
    } })),
  );

  const eingabe = el("input", { id: "loeschen-bestaetigung", name: "bestaetigung", autocomplete: "off", "aria-describedby": "loeschen-hilfe loeschen-fehler" });
  const loeschForm = el("form", { klasse: "karte", novalidate: true },
    el("h3", { text: "Daten löschen" }),
    el("p", { id: "loeschen-hilfe", text: s.loeschen_sofort ? "Wir löschen Ihren Namen, Ihre Kontaktdaten und Nachrichten sofort. Danach funktioniert dieser Link nicht mehr. Tippen Sie zur Bestätigung LÖSCHEN ein." : "Solange Ihr Rad bei uns ist, brauchen wir Ihre Kontaktdaten. Nach Abschluss löschen wir sie automatisch nach den Fristen aus der Datenschutzerklärung." }),
  );
  if (s.loeschen_sofort) {
    loeschForm.append(
      el("div", { klasse: "feld" }, el("label", { for: "loeschen-bestaetigung", text: "Bestätigung" }), eingabe, el("p", { klasse: "fehlertext", id: "loeschen-fehler", "data-fehler": "bestaetigung" })),
      el("button", { klasse: "knopf knopf--gefahr", type: "submit", text: "Daten jetzt löschen" }),
    );
    loeschForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await api("status/loeschen", { methode: "POST", daten: { token: t, bestaetigung: eingabe.value.trim() } });
        leeren(bereich).append(el("div", { klasse: "meldung meldung--gut", role: "status" }, el("p", { text: r.meldung })));
        history.replaceState(null, "", location.pathname);
      } catch (f) {
        if (f instanceof ApiFehler && f.kennung === "ungueltig") feldfehler(loeschForm, f.felder);
        else zeigen(f.message, "fehler");
      }
    });
  }
  kasten.append(loeschForm);
  return [kasten];
}

const linkFormular = document.querySelector("[data-link-formular]");
linkFormular.addEventListener("submit", async (e) => {
  e.preventDefault();
  const meldung = linkFormular.querySelector("[data-link-meldung]");
  meldung.hidden = true;
  try {
    const r = await api("status/link", { methode: "POST", daten: { nummer: linkFormular.elements.nummer.value.trim().toUpperCase(), email: linkFormular.elements.email.value.trim() } });
    feldfehler(linkFormular, {});
    meldung.hidden = false;
    meldung.textContent = r.meldung;
  } catch (f) {
    if (f instanceof ApiFehler && f.kennung === "ungueltig") feldfehler(linkFormular, f.felder);
    else {
      meldung.hidden = false;
      meldung.textContent = f.message;
    }
  }
});

window.addEventListener("hashchange", () => {
  bereich.hidden = true;
  ohneLink.hidden = true;
  laden();
});
laden();
