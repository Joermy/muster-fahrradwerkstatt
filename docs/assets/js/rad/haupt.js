import * as THREE from "../vendor/three.module.min.js";
import { buehneBauen, stufeErmitteln } from "./buehne.js";
import { studioBauen } from "./studio.js";
import { werkstattBauen } from "./werkstatt.js";
import { materialienBauen } from "./materialien.js";
import { modellHolen, modellEinrichten, TEIL_ZU } from "./modell.js";
import { antriebBauen } from "./kette.js";
import { zerlegerBauen } from "./zerlegen.js";
import { regieBauen, EINSTELLUNGEN } from "./regie.js";
import { effekteBauen, BEFUNDE } from "./effekte.js";

export async function werkstattStarten({ wurzel, basis, leistungen }) {
  const canvas = wurzel.querySelector("canvas");
  const laden = wurzel.querySelector("[data-laden]");
  const balken = wurzel.querySelector("[data-laden-balken]");
  const befundEbene = wurzel.querySelector("[data-befunde]");
  const anzeige = wurzel.querySelector("[data-anzeige]");
  const karte = wurzel.querySelector("[data-teil-karte]");
  const kapitelEbene = document.querySelector("[data-kapitel-liste]");
  const kapitel = [...document.querySelectorAll("[data-kapitel]")];
  const ruhig = window.matchMedia("(prefers-reduced-motion: reduce)");
  const sofort = new URLSearchParams(location.search).has("sofort");

  const stufe = stufeErmitteln();
  const b = buehneBauen(canvas, stufe);
  b.groesse(true);
  const studio = studioBauen(b.renderer, stufe);
  b.szene.environment = studio.env;
  b.szene.environmentIntensity = 1;
  b.szene.background = new THREE.Color(0x0b0f10);
  b.szene.fog = new THREE.Fog(0x0b0f10, 5200, 11000);
  b.szene.add(studio.licht);
  const raum = werkstattBauen({ stufe });
  b.szene.add(raum.gruppe);

  const fortschritt = (f) => {
    if (balken) balken.style.transform = `scaleX(${Math.max(0.04, f)})`;
  };
  fortschritt(0.05);
  const masseVersprechen = fetch(new URL("assets/js/rad/masse.json", basis)).then((r) => r.json());
  const gltfVersprechen = modellHolen(new URL("assets/modelle/rad.glb", basis).href, (f) => fortschritt(0.1 + f * 0.7));
  try {
    await document.fonts.load("600 20px 'Barlow Semi Condensed'");
  } catch (e) {
  }
  const M = materialienBauen({ stufe, renderer: b.renderer });
  const [masse, gltf] = await Promise.all([masseVersprechen, gltfVersprechen]);
  const modell = modellEinrichten(gltf, M, masse);
  b.szene.add(modell.rad);
  const antrieb = antriebBauen(modell, masse, M);
  const zerleger = zerlegerBauen(modell);
  const regie = regieBauen(b.kamera, b.schaerfe);
  const effekte = effekteBauen({ modell, M, antrieb, zerleger, szene: b.szene });
  fortschritt(0.9);
  try {
    await b.renderer.compileAsync(b.szene, b.kamera);
  } catch (e) {
    b.renderer.compile(b.szene, b.kamera);
  }
  fortschritt(1);

  const befunde = BEFUNDE.map((d) => {
    const el = document.createElement("div");
    el.className = `befund befund--${d.stand}`;
    const t = document.createElement("strong");
    t.textContent = d.titel;
    const w = document.createElement("span");
    w.textContent = d.wert;
    el.append(t, w);
    befundEbene.append(el);
    return { ...d, el, p: new THREE.Vector3(...d.anker) };
  });

  const felder = {};
  for (const el of anzeige.querySelectorAll("[data-feld]")) felder[el.dataset.feld] = el;
  const setzeFeld = (name, wert) => {
    if (felder[name] && felder[name].textContent !== String(wert)) felder[name].textContent = wert;
  };

  const strahl = new THREE.Raycaster();
  const zeiger = new THREE.Vector2();
  const pickbar = [];
  modell.rad.traverse((o) => {
    if (o.isMesh || o.isInstancedMesh) {
      let t = o;
      while (t && !t.userData.teil) t = t.parent;
      const name = o.userData.teil || (t && t.userData.teil);
      if (name && TEIL_ZU[name]) pickbar.push(o);
    }
  });
  const leistungFuer = (kennung) => leistungen.leistungen.find((l) => l.teile.includes(kennung));
  let schwebt = null;
  let gewaehlt = null;
  const hervor = new Map();
  const materialienVon = (teil) => (teil === "kette" ? [...M.vonTeil("glied_aussen"), ...M.vonTeil("glied_innen")] : M.vonTeil(teil));

  function teilUnter(x, y) {
    const r = canvas.getBoundingClientRect();
    zeiger.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    strahl.setFromCamera(zeiger, b.kamera);
    const treffer = strahl.intersectObjects(pickbar, false)[0];
    if (!treffer) return null;
    let o = treffer.object;
    while (o && !o.userData.teil) o = o.parent;
    return o ? o.userData.teil : null;
  }

  function karteZeigen(teil) {
    const zuordnung = TEIL_ZU[teil];
    if (!zuordnung) return;
    const [kennung, bezeichnung] = zuordnung;
    const l = leistungFuer(kennung);
    gewaehlt = teil;
    karte.querySelector("[data-karte-teil]").textContent = bezeichnung;
    if (l) {
      karte.querySelector("[data-karte-titel]").textContent = l.titel;
      karte.querySelector("[data-karte-text]").textContent = l.kurz;
      karte.querySelector("[data-karte-preis]").textContent = `${(l.preis_cent / 100).toLocaleString("de-DE", { minimumFractionDigits: 2 })} € ${l.einheit}`;
      const a = karte.querySelector("[data-karte-link]");
      a.href = new URL(`termin/?leistung=${encodeURIComponent(l.kennung)}`, basis).href;
    }
    karte.hidden = false;
  }

  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    schwebt = teilUnter(e.clientX, e.clientY);
    canvas.style.cursor = schwebt ? "pointer" : "";
  });
  canvas.addEventListener("pointerleave", () => {
    schwebt = null;
  });
  let druck = null;
  canvas.addEventListener("pointerdown", (e) => {
    druck = { x: e.clientX, y: e.clientY, t: performance.now() };
  });
  canvas.addEventListener("pointerup", (e) => {
    if (!druck) return;
    const weit = Math.hypot(e.clientX - druck.x, e.clientY - druck.y);
    if (weit < 8 && performance.now() - druck.t < 500) {
      const t = teilUnter(e.clientX, e.clientY);
      if (t) karteZeigen(t);
    }
    druck = null;
  });
  karte.querySelector("[data-karte-zu]").addEventListener("click", () => {
    karte.hidden = true;
    gewaehlt = null;
  });
  for (const knopf of wurzel.querySelectorAll("[data-teil-knopf]")) {
    knopf.addEventListener("click", () => karteZeigen(knopf.dataset.teilKnopf));
    knopf.addEventListener("mouseenter", () => { schwebt = knopf.dataset.teilKnopf; });
    knopf.addEventListener("mouseleave", () => { schwebt = null; });
    knopf.addEventListener("focus", () => { schwebt = knopf.dataset.teilKnopf; });
    knopf.addEventListener("blur", () => { schwebt = null; });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !karte.hidden) {
      karte.hidden = true;
      gewaehlt = null;
    }
  });

  let p = 0;
  function fortschrittMessen() {
    if (!kapitelEbene) return 0;
    const r = kapitelEbene.getBoundingClientRect();
    const vh = window.innerHeight || 1;
    const n = EINSTELLUNGEN.length;
    return THREE.MathUtils.clamp(-r.top / vh, 0, n - 0.001);
  }
  let pZiel = fortschrittMessen();
  p = pZiel;
  window.addEventListener("scroll", () => { pZiel = fortschrittMessen(); }, { passive: true });

  let sichtbar = true;
  new IntersectionObserver((e) => { sichtbar = e[0].isIntersecting; }, { rootMargin: "100px" }).observe(wurzel);
  let letzte = performance.now();
  let zeit = 0;
  const messung = { summe: 0, n: 0, start: performance.now() };
  const v3 = new THREE.Vector3();
  let aktivesKapitel = -1;

  function bild(jetzt) {
    requestAnimationFrame(bild);
    const dt = Math.min(0.05, (jetzt - letzte) / 1000);
    letzte = jetzt;
    if (!sichtbar || document.hidden) return;
    zeit += dt;
    if (b.groesse()) regie.aktualisieren(p, 1, { seiten: b.kamera.aspect, breite: b.breite, hoehe: b.hoehe });
    const bewegung = !ruhig.matches;
    p += (pZiel - p) * (bewegung && !sofort ? Math.min(1, dt * 8) : 1);
    const lage = regie.aktualisieren(p, sofort ? 10 : dt, { seiten: b.kamera.aspect, breite: b.breite, hoehe: b.hoehe, bewegung });
    const werte = effekte.setzen(p, dt, zeit, bewegung);

    const ziel = schwebt || gewaehlt;
    for (const name of new Set([...hervor.keys(), ziel].filter(Boolean))) {
      const alt = hervor.get(name) || 0;
      const neu = alt + ((name === ziel ? 1 : 0) - alt) * Math.min(1, dt * 10);
      hervor.set(name, neu);
      for (const m of materialienVon(name)) m.userData.hervor.value = neu * 0.55;
      if (neu < 0.002 && name !== ziel) hervor.delete(name);
    }

    for (const d of befunde) {
      const an = werte.scan > 0.05 && werte.scanX > d.p.x;
      d.el.classList.toggle("ist-an", an);
      if (an || d.el.classList.contains("ist-an")) {
        v3.copy(d.p).project(b.kamera);
        d.el.style.transform = `translate(${((v3.x + 1) / 2) * b.breite}px, ${((1 - v3.y) / 2) * b.hoehe}px)`;
      }
    }

    if (lage.kapitel !== aktivesKapitel) {
      aktivesKapitel = lage.kapitel;
      anzeige.dataset.kapitel = lage.name;
      kapitel.forEach((k, i) => k.classList.toggle("ist-aktiv", i === aktivesKapitel));
    }
    setzeFeld("gang", `${werte.gang} / 12`);
    setzeFeld("ritzel", `${antrieb.kettenblattZaehne} : ${werte.ritzel}`);
    setzeFeld("temperatur", `${werte.temperatur} °C`);
    setzeFeld("drehzahl", `${werte.drehzahl} U/min`);
    setzeFeld("schlag", `${werte.schlag} mm`);
    setzeFeld("spannung", `± ${werte.spannung} %`);
    M.display.zeichnen(displayInhalt(lage.kapitel, werte));

    b.zeichnen(zeit);

    if (sofort) return;
    messung.summe += dt;
    messung.n++;
    if (jetzt - messung.start > 2500) {
      const mittel = messung.summe / messung.n;
      if (mittel > 1 / 40 && b.senken()) messung.start = jetzt + 1500;
      else messung.start = jetzt;
      messung.summe = 0;
      messung.n = 0;
    }
  }

  function displayInhalt(k, w) {
    switch (k) {
      case 1: return { kopf: "Diagnose", zeilen: [{ text: "Fehlerspeicher wird gelesen" }, { text: `Software 4.2.1`, ok: false }, { text: "Motor: keine Fehler", ok: true }] };
      case 2: return { kopf: "Service", zeilen: [{ text: "Antrieb aus" }] };
      case 3: return { kopf: `Gang ${w.gang}`, gross: String(Math.round(62 + w.gang * 0.6)), einheit: "U/min", zeilen: [{ text: `Übersetzung ${w.uebersetzung.toFixed(2).replace(".", ",")}` }] };
      case 4: return { kopf: "Bremstest", gross: String(Math.round(w.drehzahl * 0.135)), einheit: "km/h", zeilen: [{ text: `Scheibe ${w.temperatur} °C`, ok: w.temperatur < 200 }] };
      case 5: return { kopf: "Laufrad", zeilen: [{ text: `Seitenschlag ${w.schlag} mm`, ok: Number(w.schlag.replace(",", ".")) < 0.5 }, { text: `Spannung ± ${w.spannung} %`, ok: w.spannung < 5 }] };
      case 6: return { kopf: "Akku", akku: 0.86, zeilen: [{ text: "Kapazität 86 %", ok: true }, { text: "412 Ladezyklen" }, { text: "Software 4.3.0", ok: true }] };
      case 7: return { kopf: "Fertig", gross: "0", einheit: "km/h", zeilen: [{ text: "Gute Fahrt!", ok: true }] };
      default: return { kopf: "Bereit", gross: "0", einheit: "km/h", zeilen: [{ text: "Unterstützung: Tour" }] };
    }
  }

  let ziehen = null;
  canvas.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse") ziehen = e.clientX;
  });
  window.addEventListener("pointermove", (e) => {
    if (ziehen !== null) {
      regie.ziehen(e.clientX - ziehen);
      ziehen = e.clientX;
    }
  });
  window.addEventListener("pointerup", () => {
    if (ziehen !== null) regie.loslassen();
    ziehen = null;
  });

  regie.aktualisieren(p, 1, { seiten: b.kamera.aspect, breite: b.breite, hoehe: b.hoehe });
  effekte.setzen(p, 0, 0, !ruhig.matches);
  b.zeichnen(0);
  laden.classList.add("ist-fertig");
  wurzel.classList.add("ist-bereit");
  document.documentElement.dataset.werkstatt = "bereit";
  requestAnimationFrame(bild);
  window.__werkstatt = { b, modell, antrieb, stufe, regie };
  return { b, modell, antrieb, stufe };
}
