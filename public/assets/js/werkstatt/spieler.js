// Werkstatt auf der Startseite: pfadverfolgte Bildfolge (Blender/Cycles), per Scrollen abgespielt.
// Kein Ladebildschirm: Das erste Bild steht schon im HTML, die übrigen kommen grob-zu-fein nach
// (jedes 24., 8., 4., 2., dann alle). Zwischen zwei geladenen Bildern wird überblendet.

import { werteBei, KAPITEL } from "./zeitleiste.js";

const klemm = (x, a, b) => Math.max(a, Math.min(b, x));

function satzWaehlen(manifest) {
  const verbindung = navigator.connection || {};
  const langsam = verbindung.saveData || /(^|-)2g|3g/.test(verbindung.effectiveType || "");
  const klein = Math.min(window.innerWidth, window.innerHeight) < 700 || (navigator.deviceMemory || 8) <= 2;
  return manifest.saetze[langsam || klein ? "klein" : "gross"];
}

export async function werkstattStarten({ wurzel, basis, leistungen }) {
  const canvas = wurzel.querySelector("canvas");
  const ctx = canvas.getContext("2d", { alpha: true });
  const standbild = wurzel.querySelector("[data-standbild]");
  const befundEbene = wurzel.querySelector("[data-befunde]");
  const markenEbene = wurzel.querySelector("[data-marken]");
  const anzeige = wurzel.querySelector("[data-anzeige]");
  const karte = wurzel.querySelector("[data-teil-karte]");
  const kapitelEbene = document.querySelector("[data-kapitel-liste]");
  const kapitel = [...document.querySelectorAll("[data-kapitel]")];
  const ruhig = window.matchMedia("(prefers-reduced-motion: reduce)");
  const ordner = new URL("assets/werkstatt/", basis);

  const [manifest, lagen] = await Promise.all([
    fetch(new URL("manifest.json", ordner)).then((r) => r.json()),
    fetch(new URL("lagen.json", ordner)).then((r) => r.json()),
  ]);
  const satz = satzWaehlen(manifest);
  const n = manifest.bilder;
  const jeKapitel = manifest.je_kapitel;
  const sparsam = () => ruhig.matches || (navigator.connection && navigator.connection.saveData);
  const bilder = new Array(n).fill(null);
  const url = (i) => new URL(satz.muster.replace("{i}", String(i).padStart(4, "0")), ordner).href;

  // ---------------------------------------------------------------- Laden, grob zu fein
  const reihenfolge = [];
  const vorgemerkt = new Set();
  // Eine unvollständige Folge nennt ihre fertigen Bilder; die übrigen gar nicht erst anfragen
  const gibt = manifest.vorhanden ? new Set(manifest.vorhanden) : null;
  const merken = (i) => {
    if (i >= 0 && i < n && !vorgemerkt.has(i) && (!gibt || gibt.has(i))) {
      vorgemerkt.add(i);
      reihenfolge.push(i);
    }
  };
  merken(0);
  manifest.schluessel.forEach(merken);
  if (!sparsam()) for (const schritt of [8, 4, 2, 1]) for (let i = 0; i < n; i += schritt) merken(i);
  let laufend = 0;
  let schmutzig = true;
  function weiterLaden() {
    while (laufend < 4 && reihenfolge.length) {
      const i = reihenfolge.shift();
      const img = new Image();
      img.decoding = "async";
      img.src = url(i);
      laufend++;
      img.decode().then(() => {
        bilder[i] = img;
        schmutzig = true;
      }).catch(() => {}).finally(() => {
        laufend--;
        weiterLaden();
      });
    }
  }
  weiterLaden();

  // ---------------------------------------------------------------- Abbildung Bild → Bühne
  let breite = 0;
  let hoehe = 0;
  let dichte = 1;
  function groesse() {
    const b = canvas.clientWidth;
    const h = canvas.clientHeight;
    const d = Math.min(window.devicePixelRatio || 1, 2);
    if (b === breite && h === hoehe && d === dichte) return false;
    breite = b;
    hoehe = h;
    dichte = d;
    canvas.width = Math.round(b * d);
    canvas.height = Math.round(h * d);
    return true;
  }

  function abbildung(fokus) {
    const fb = satz.breite;
    const fh = satz.hoehe;
    if (breite / hoehe >= 1.1) {
      const s = Math.max(breite / fb, hoehe / fh);
      return { s, ox: (breite - fb * s) / 2, oy: (hoehe - fh * s) / 2, hochkant: false };
    }
    // Hochkant: Bild in den oberen Teil, auf den Bildschwerpunkt zentriert
    const s = Math.max(breite / fb, (hoehe * 0.6) / fh);
    const ox = klemm(breite / 2 - fokus * fb * s, breite - fb * s, 0);
    return { s, ox, oy: Math.max(48, hoehe * 0.06), hochkant: true };
  }

  // ---------------------------------------------------------------- Teile antippen
  const leistungFuer = (kennung) => leistungen.leistungen.find((l) => l.teile.includes(kennung));
  let gewaehlt = null;
  let markiert = null;

  function karteZeigen(teil) {
    const zuordnung = manifest.teile[teil];
    if (!zuordnung) return;
    const [kennung, bezeichnung] = zuordnung;
    const l = leistungFuer(kennung);
    gewaehlt = teil;
    karte.querySelector("[data-karte-teil]").textContent = bezeichnung;
    if (l) {
      karte.querySelector("[data-karte-titel]").textContent = l.titel;
      karte.querySelector("[data-karte-text]").textContent = l.kurz;
      karte.querySelector("[data-karte-preis]").textContent = `${(l.preis_cent / 100).toLocaleString("de-DE", { minimumFractionDigits: 2 })} € ${l.einheit}`;
      karte.querySelector("[data-karte-link]").href = new URL(`termin/?leistung=${encodeURIComponent(l.kennung)}`, basis).href;
    }
    karte.hidden = false;
    schmutzig = true;
  }
  const karteZu = () => {
    karte.hidden = true;
    gewaehlt = null;
    schmutzig = true;
  };
  karte.querySelector("[data-karte-zu]").addEventListener("click", karteZu);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !karte.hidden) karteZu();
  });
  for (const knopf of wurzel.querySelectorAll("[data-teil-knopf]")) {
    const teil = knopf.dataset.teilKnopf;
    knopf.addEventListener("click", () => karteZeigen(teil));
    for (const [ereignis, wert] of [["mouseenter", teil], ["focus", teil], ["mouseleave", null], ["blur", null]]) {
      knopf.addEventListener(ereignis, () => {
        markiert = wert;
        schmutzig = true;
      });
    }
  }
  const marken = Object.entries(manifest.teile).map(([teil, [, bezeichnung]]) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "teilmarke";
    el.setAttribute("aria-label", `${bezeichnung}: Leistung und Preis zeigen`);
    el.tabIndex = -1;
    el.addEventListener("click", () => karteZeigen(teil));
    markenEbene.append(el);
    return { teil, el };
  });

  const befunde = manifest.befunde.map((d) => {
    const el = document.createElement("div");
    el.className = `befund befund--${d.stand}`;
    const t = document.createElement("strong");
    t.textContent = d.titel;
    const w = document.createElement("span");
    w.textContent = d.wert;
    el.append(t, w);
    befundEbene.append(el);
    return { ...d, el };
  });

  const felder = {};
  for (const el of anzeige.querySelectorAll("[data-feld]")) felder[el.dataset.feld] = el;
  const setzeFeld = (name, wert) => {
    if (felder[name] && felder[name].textContent !== String(wert)) felder[name].textContent = wert;
  };

  // ---------------------------------------------------------------- Scrollen
  function fortschritt() {
    if (!kapitelEbene) return 0;
    const r = kapitelEbene.getBoundingClientRect();
    return klemm(-r.top / (window.innerHeight || 1), 0, KAPITEL - 0.001);
  }
  let p = fortschritt();
  window.addEventListener("scroll", () => {
    const neu = fortschritt();
    if (neu !== p) {
      p = neu;
      schmutzig = true;
    }
  }, { passive: true });
  window.addEventListener("resize", () => { schmutzig = true; });
  ruhig.addEventListener?.("change", () => { schmutzig = true; });

  let sichtbar = true;
  new IntersectionObserver((e) => {
    sichtbar = e[0].isIntersecting;
    if (sichtbar) schmutzig = true;
  }, { rootMargin: "120px" }).observe(wurzel);

  // Nächstes geladenes Bild unter- und oberhalb von x suchen
  function nachbarn(x) {
    if (sparsam()) {
      const k = Math.min(Math.floor(x / jeKapitel), KAPITEL - 1);
      const i = manifest.schluessel[k];
      return bilder[i] ? [i, i, 0] : [0, 0, 0];
    }
    const i0 = Math.floor(x);
    let a = i0;
    while (a > 0 && !bilder[a]) a--;
    let b = Math.min(n - 1, i0 + 1);
    while (b < n - 1 && !bilder[b]) b++;
    if (!bilder[b]) b = a;
    const t = b > a ? klemm((x - a) / (b - a), 0, 1) : 0;
    return [a, b, t];
  }

  const holen = (lage, wahl) => {
    try {
      return lage ? wahl(lage) || null : null;
    } catch (e) {
      return null;
    }
  };
  const lageMischen = (a, b, t, wahl) => {
    const la = holen(lagen[a], wahl);
    const lb = holen(lagen[b], wahl);
    if (!la || !lb) return la || lb;
    return [la[0] + (lb[0] - la[0]) * t, la[1] + (lb[1] - la[1]) * t, la[2] && lb[2]];
  };

  let aktivesKapitel = -1;
  let ersterStrich = true;

  function zeichnen() {
    requestAnimationFrame(zeichnen);
    if (groesse()) schmutzig = true;
    if (!schmutzig || !sichtbar || document.hidden) return;
    schmutzig = false;
    const x = p * jeKapitel;
    const [a, b, t] = nachbarn(x);
    if (!bilder[a]) return;
    const fokus = lageMischen(a, b, t, (l) => l.f) || [0.5, 0.5];
    const m = abbildung(fokus[0]);
    ctx.setTransform(dichte, 0, 0, dichte, 0, 0);
    ctx.clearRect(0, 0, breite, hoehe);
    const fb = satz.breite * m.s;
    const fh = satz.hoehe * m.s;
    ctx.globalAlpha = 1;
    ctx.drawImage(bilder[a], m.ox, m.oy, fb, fh);
    if (b !== a && t > 0.01 && bilder[b]) {
      ctx.globalAlpha = t;
      ctx.drawImage(bilder[b], m.ox, m.oy, fb, fh);
      ctx.globalAlpha = 1;
    }
    if (m.hochkant) {
      const unten = m.oy + fh;
      const verlauf = ctx.createLinearGradient(0, unten - 90, 0, unten);
      verlauf.addColorStop(0, "rgba(11,15,16,0)");
      verlauf.addColorStop(1, "rgba(11,15,16,1)");
      ctx.fillStyle = verlauf;
      ctx.fillRect(0, unten - 90, breite, 90);
      const oben = ctx.createLinearGradient(0, m.oy, 0, m.oy + 60);
      oben.addColorStop(0, "rgba(11,15,16,1)");
      oben.addColorStop(1, "rgba(11,15,16,0)");
      ctx.fillStyle = oben;
      ctx.fillRect(0, m.oy, breite, 60);
    }
    if (ersterStrich) {
      ersterStrich = false;
      wurzel.classList.add("ist-bereit");
      document.documentElement.dataset.werkstatt = "bereit";
    }

    const werte = werteBei(p);
    const nachBild = (l) => [m.ox + l[0] * fb, m.oy + l[1] * fh];
    befunde.forEach((d, j) => {
      const l = lageMischen(a, b, t, (lage) => lage.b[j]);
      const an = !!l && l[2] && werte.scan > 0.05 && werte.scanX > d.x;
      d.el.classList.toggle("ist-an", an);
      if (an) {
        const [px, py] = nachBild(l);
        d.el.style.transform = `translate(${px}px, ${py}px)`;
      }
    });
    const ruhigesBild = (werte.kapitel === 0 || werte.kapitel === 7) && werte.anteil < 0.6;
    for (const mk of marken) {
      const l = lageMischen(a, b, t, (lage) => lage.t[mk.teil]);
      const zeigen = !!l && l[2] && (ruhigesBild || markiert === mk.teil || gewaehlt === mk.teil);
      mk.el.classList.toggle("ist-an", zeigen);
      mk.el.classList.toggle("ist-markiert", markiert === mk.teil || gewaehlt === mk.teil);
      mk.el.tabIndex = -1;
      if (zeigen) {
        const [px, py] = nachBild(l);
        mk.el.style.transform = `translate(${px}px, ${py}px)`;
      }
    }

    if (werte.kapitel !== aktivesKapitel) {
      aktivesKapitel = werte.kapitel;
      anzeige.dataset.kapitel = werte.name;
      wurzel.dataset.kapitel = String(werte.kapitel);
      kapitel.forEach((k, i) => k.classList.toggle("ist-aktiv", i === aktivesKapitel));
    }
    setzeFeld("gang", `${werte.gang} / 12`);
    setzeFeld("ritzel", `${werte.kettenblatt} : ${werte.ritzel}`);
    setzeFeld("temperatur", `${werte.temperatur} °C`);
    setzeFeld("drehzahl", `${werte.drehzahl} U/min`);
    setzeFeld("schlag", `${werte.schlag} mm`);
    setzeFeld("spannung", `± ${werte.spannung} %`);
  }
  requestAnimationFrame(zeichnen);
  standbild.classList.add("ist-unterlegt");
  window.__werkstatt = { manifest, satz, bilder, get p() { return p; } };
}
