import { va, el, leeren, feld, absenden, formularmeldung, VORFUEHRUNG } from "./gemeinsam.js";
import qrcode from "../vendor/qrcode.min.js";

function karte(titel, ...inhalt) {
  return el("div", { klasse: "vw-zugang" },
    el("div", { klasse: "vw-zugang__karte" },
      el("div", { klasse: "vw-zugang__anhaenger", "aria-hidden": "true" }),
      el("h1", { text: titel, tabindex: "-1" }),
      ...inhalt,
    ),
  );
}

async function vorfuehrHinweis() {
  if (!VORFUEHRUNG) return null;
  const { zugangsdaten } = await import("../vorfuehrung/server.js");
  const kasten = el("div", { klasse: "vw-vorfuehrung" });
  const zeichnen = async () => {
    const z = await zugangsdaten();
    leeren(kasten).append(
      el("p", {}, el("strong", { text: "Vorführzugang. " }), el("span", { text: "Alles läuft in diesem Browser-Tab, nichts wird gesendet." })),
      el("dl", {},
        el("dt", { text: "Benutzer" }), el("dd", { text: z.benutzer }),
        el("dt", { text: "Passwort" }), el("dd", { text: z.passwort }),
        el("dt", { text: z.fuer === z.benutzer ? "Code der App" : `Code für ${z.fuer}` }), el("dd", { klasse: "zahl", text: z.code + ` (noch ${z.restSekunden} s)` }),
      ),
    );
  };
  await zeichnen();
  const takt = setInterval(() => (kasten.isConnected ? zeichnen() : clearInterval(takt)), 1000);
  return kasten;
}

export async function anmeldungZeigen(ziel, weiter, meldung = null) {
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    meldung ? el("div", { klasse: "meldung", role: "status" }, el("p", { text: meldung })) : null,
    formularmeldung(),
    feld({ name: "name", label: "Benutzername", pflicht: true, attribute: { autocomplete: "username", autocapitalize: "none", spellcheck: "false" } }),
    feld({ name: "passwort", label: "Passwort", typ: "password", pflicht: true, attribute: { autocomplete: "current-password" } }),
    el("button", { klasse: "knopf", type: "submit", text: "Anmelden" }),
  );
  leeren(ziel).append(karte("Anmelden", el("p", { text: "Zugang für das Team der Werkstatt." }), await vorfuehrHinweis(), form));
  form.querySelector("[name=name]").focus();
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const r = await va("anmelden", { methode: "POST", daten: { name: form.name.value.trim(), passwort: form.passwort.value } });
      form.passwort.value = "";
      if (r.stufe === "passwort") codeZeigen(ziel, weiter);
      else weiter();
    });
  });
}

async function codeZeigen(ziel, weiter) {
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    feld({
      name: "code", label: "Code", pflicht: true,
      hilfe: "Sechs Ziffern aus Ihrer Authenticator-App. Ohne Telefon geht auch einer Ihrer Ersatzcodes.",
      attribute: { autocomplete: "one-time-code", inputmode: "numeric", maxlength: "14", spellcheck: "false" },
    }),
    el("button", { klasse: "knopf", type: "submit", text: "Bestätigen" }),
  );
  leeren(ziel).append(karte("Zweiter Schritt", await vorfuehrHinweis(), form));
  form.querySelector("[name=code]").focus();
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      await va("code", { methode: "POST", daten: { code: form.code.value.replace(/\s+/g, "") } });
      weiter();
    });
  });
}

export function einrichtungZeigen(ziel, ich, weiter) {
  if (ich.passwort_wechseln) passwortZeigen(ziel, weiter);
  else zweifaktorZeigen(ziel, weiter);
}

function passwortZeigen(ziel, weiter) {
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    feld({ name: "alt", label: "Startpasswort", typ: "password", pflicht: true, attribute: { autocomplete: "current-password" } }),
    feld({ name: "neu", label: "Neues Passwort", typ: "password", pflicht: true, hilfe: "Mindestens 12 Zeichen. Am besten ein Satz aus mehreren Wörtern oder ein Passwort aus dem Passwort-Manager.", attribute: { autocomplete: "new-password", minlength: "12", maxlength: "128" } }),
    el("button", { klasse: "knopf", type: "submit", text: "Passwort speichern" }),
  );
  leeren(ziel).append(karte("Eigenes Passwort festlegen",
    el("ol", { klasse: "vw-schritte", "aria-label": "Einrichtung" }, el("li", { "aria-current": "step", text: "Passwort" }), el("li", { text: "Zwei-Faktor" }), el("li", { text: "Ersatzcodes" })),
    el("p", { text: "Das Startpasswort gilt nur für die erste Anmeldung." }),
    form));
  form.querySelector("[name=alt]").focus();
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const r = await va("passwort", { methode: "POST", daten: { alt: form.alt.value, neu: form.neu.value } });
      anmeldungZeigen(ziel, weiter, r.meldung);
    });
  });
}

function qrSvg(text) {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const n = qr.getModuleCount();
  const rand = 4;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${n + rand * 2} ${n + rand * 2}`);
  svg.setAttribute("width", "220");
  svg.setAttribute("height", "220");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "QR-Code für die Authenticator-App");
  svg.setAttribute("shape-rendering", "crispEdges");
  const grund = document.createElementNS(ns, "rect");
  grund.setAttribute("width", "100%");
  grund.setAttribute("height", "100%");
  grund.setAttribute("fill", "#ffffff");
  svg.append(grund);
  let d = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (qr.isDark(r, c)) d += `M${c + rand},${r + rand}h1v1h-1z`;
  const pfad = document.createElementNS(ns, "path");
  pfad.setAttribute("d", d);
  pfad.setAttribute("fill", "#182124");
  svg.append(pfad);
  return svg;
}

async function zweifaktorZeigen(ziel, weiter) {
  let daten;
  try {
    daten = await va("zweifaktor/start", { methode: "POST", daten: {} });
  } catch (f) {
    leeren(ziel).append(karte("Zwei-Faktor einrichten", el("div", { klasse: "meldung meldung--fehler", role: "alert" }, el("p", { text: f.message }))));
    return;
  }
  const gruppiert = daten.geheimnis.replace(/(.{4})/g, "$1 ").trim();
  const form = el("form", { klasse: "vw-formular", novalidate: true },
    formularmeldung(),
    feld({ name: "code", label: "Code aus der App", pflicht: true, attribute: { autocomplete: "one-time-code", inputmode: "numeric", maxlength: "6", spellcheck: "false" } }),
    el("button", { klasse: "knopf", type: "submit", text: "Zwei-Faktor einschalten" }),
  );
  leeren(ziel).append(karte("Zwei-Faktor einrichten",
    el("ol", { klasse: "vw-schritte", "aria-label": "Einrichtung" }, el("li", { text: "Passwort" }), el("li", { "aria-current": "step", text: "Zwei-Faktor" }), el("li", { text: "Ersatzcodes" })),
    el("p", { text: "Scannen Sie den Code mit einer Authenticator-App, zum Beispiel Aegis, 2FAS, Google oder Microsoft Authenticator. Danach fragt die Anmeldung zusätzlich nach dem sechsstelligen Code aus der App." }),
    el("div", { klasse: "vw-qr" }, qrSvg(daten.uri)),
    el("details", { klasse: "vw-details" },
      el("summary", { text: "Code lässt sich nicht scannen?" }),
      el("p", { text: "Geben Sie diesen Schlüssel von Hand in der App ein (Typ: zeitbasiert, 6 Ziffern, 30 Sekunden):" }),
      el("p", { klasse: "vw-schluessel zahl", text: gruppiert }),
    ),
    VORFUEHRUNG ? await vorfuehrHinweis() : null,
    form));
  form.querySelector("[name=code]").focus();
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absenden(form, async () => {
      const r = await va("zweifaktor/bestaetigen", { methode: "POST", daten: { code: form.code.value.replace(/\s+/g, "") } });
      ersatzcodesZeigen(ziel, r.ersatzcodes, weiter);
    });
  });
}

function ersatzcodesZeigen(ziel, codes, weiter) {
  const bestaetigt = el("input", { type: "checkbox", id: "ersatz-ok" });
  const knopf = el("button", { klasse: "knopf", type: "button", text: "Weiter zur Verwaltung", disabled: true, onclick: () => weiter() });
  bestaetigt.addEventListener("change", () => (knopf.disabled = !bestaetigt.checked));
  const kopieren = el("button", {
    klasse: "knopf knopf--leise", type: "button", text: "Codes kopieren",
    onclick: async () => {
      try {
        await navigator.clipboard.writeText(codes.join("\n"));
        kopieren.textContent = "Kopiert";
      } catch {
        kopieren.textContent = "Kopieren nicht möglich, bitte abschreiben";
      }
    },
  });
  leeren(ziel).append(karte("Ersatzcodes sichern",
    el("ol", { klasse: "vw-schritte", "aria-label": "Einrichtung" }, el("li", { text: "Passwort" }), el("li", { text: "Zwei-Faktor" }), el("li", { "aria-current": "step", text: "Ersatzcodes" })),
    el("p", { text: "Falls das Telefon verloren geht, kommen Sie mit einem dieser Codes noch einmal hinein. Jeder Code gilt genau einmal. Sie werden nur jetzt angezeigt; gespeichert ist nur ein Prüfwert." }),
    el("ol", { klasse: "vw-ersatzcodes zahl" }, codes.map((c) => el("li", { text: c }))),
    el("p", {}, kopieren),
    el("div", { klasse: "wahl" }, bestaetigt, el("label", { for: "ersatz-ok", text: "Ich habe die Codes ausgedruckt oder im Passwort-Manager gespeichert." })),
    el("p", { klasse: "vw-zugang__weiter" }, knopf),
  ));
}
