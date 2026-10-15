export function el(tag, eigenschaften = {}, ...kinder) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(eigenschaften || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "text") e.textContent = v;
    else if (k === "klasse") e.className = v;
    else if (k === "daten") for (const [dk, dv] of Object.entries(v)) e.dataset[dk] = dv;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else e.setAttribute(k, String(v));
  }
  for (const k of kinder.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return e;
}

export function leeren(e) {
  while (e.firstChild) e.firstChild.remove();
  return e;
}

export const euro = (cent) => (cent / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" });

export function datum(iso, mitWochentag = true) {
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  return d.toLocaleDateString("de-DE", mitWochentag ? { weekday: "long", day: "numeric", month: "long" } : { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function zeitpunkt(iso) {
  const d = new Date(iso);
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " Uhr";
}

export function feldfehler(formular, felder = {}) {
  for (const f of formular.querySelectorAll("[data-fehler]")) f.textContent = "";
  for (const i of formular.querySelectorAll("[aria-invalid]")) i.removeAttribute("aria-invalid");
  let erstes = null;
  for (const [name, meldung] of Object.entries(felder)) {
    const ziel = formular.querySelector(`[data-fehler="${CSS.escape(name)}"]`);
    if (ziel) ziel.textContent = meldung;
    const eingabe = formular.querySelector(`[name="${CSS.escape(name)}"]`);
    if (eingabe) {
      eingabe.setAttribute("aria-invalid", "true");
      erstes ??= eingabe;
    }
  }
  if (erstes) erstes.focus();
  return erstes;
}
