import { api, ApiFehler } from "./api.js";
import { feldfehler, zeitpunkt } from "./dom.js";

const formular = document.querySelector("[data-widerruf]");
const schritt1 = formular.querySelector('[data-widerruf-schritt="1"]');
const schritt2 = formular.querySelector('[data-widerruf-schritt="2"]');
const text = formular.querySelector("[data-widerruf-text]");
const fehler = formular.querySelector("[data-sendefehler]");
const erfolg = document.querySelector("[data-widerruf-erfolg]");
const f = formular.elements;

const vorgabe = /(?:^|[#&])nr=(RF-[A-Z0-9]{4}-[A-Z0-9]{4})/.exec(location.hash);
if (vorgabe) f.nummer.value = vorgabe[1];

function pruefen() {
  const e = {};
  if (f.name.value.trim().length < 2) e.name = "Bitte Ihren Namen angeben.";
  if (f.nummer.value.trim().length < 6) e.nummer = "Bitte die Auftragsnummer aus Ihrer Mail angeben, z. B. RF-ABCD-EFGH.";
  if (!/^[^\s@,;<>"]+@[^\s@,;<>"]+\.[^\s@,;<>"]{2,}$/.test(f.email.value.trim())) e.email = "Bitte eine gültige E-Mail-Adresse angeben.";
  feldfehler(formular, e);
  return Object.keys(e).length === 0;
}

formular.querySelector("[data-widerruf-weiter]").addEventListener("click", () => {
  if (!pruefen()) return;
  text.textContent = `Hiermit widerrufe ich, ${f.name.value.trim()}, den über die Website geschlossenen Vertrag über Zusatzarbeiten zum Auftrag ${f.nummer.value.trim().toUpperCase()}. Die Eingangsbestätigung bitte an ${f.email.value.trim()}.`;
  schritt1.hidden = true;
  schritt2.hidden = false;
  schritt2.querySelector("h2").setAttribute("tabindex", "-1");
  schritt2.querySelector("h2").focus();
});
formular.querySelector("[data-widerruf-zurueck]").addEventListener("click", () => {
  schritt2.hidden = true;
  schritt1.hidden = false;
  f.name.focus();
});

formular.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (schritt2.hidden) {
    formular.querySelector("[data-widerruf-weiter]").click();
    return;
  }
  fehler.hidden = true;
  try {
    const r = await api("widerruf", { methode: "POST", daten: { name: f.name.value.trim(), nummer: f.nummer.value.trim().toUpperCase(), email: f.email.value.trim(), grund: f.grund.value.trim() } });
    formular.hidden = true;
    erfolg.hidden = false;
    erfolg.querySelector("[data-widerruf-eingang]").textContent = `Eingang: ${zeitpunkt(r.eingang)}, Vorgang ${r.kennung}.`;
    erfolg.focus();
  } catch (x) {
    if (x instanceof ApiFehler && x.kennung === "ungueltig") {
      schritt2.hidden = true;
      schritt1.hidden = false;
      feldfehler(formular, x.felder);
    } else {
      fehler.hidden = false;
      fehler.textContent = x.message;
    }
  }
});
