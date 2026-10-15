import * as THREE from "../vendor/three.module.min.js";
import { SCAN } from "./materialien.js";
import { b2t } from "./modell.js";

const klemm = THREE.MathUtils.clamp;
const glatt = (a, b, x) => {
  const t = klemm((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const fenster = (a, b, c, d, x) => glatt(a, b, x) * (1 - glatt(c, d, x));

function speichenschleier() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 14, 128, 128, 128);
  g.addColorStop(0, "rgba(190,195,200,0)");
  g.addColorStop(0.2, "rgba(190,195,200,0.28)");
  g.addColorStop(0.85, "rgba(190,195,200,0.18)");
  g.addColorStop(0.95, "rgba(190,195,200,0.05)");
  g.addColorStop(1, "rgba(190,195,200,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
  const n = new THREE.Mesh(new THREE.CircleGeometry(300, 64), m);
  n.renderOrder = 2;
  return n;
}

function lichtvorhang() {
  const c = document.createElement("canvas");
  c.width = 16;
  c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, "rgba(111,230,214,0)");
  g.addColorStop(0.2, "rgba(111,230,214,0.55)");
  g.addColorStop(0.8, "rgba(111,230,214,0.55)");
  g.addColorStop(1, "rgba(111,230,214,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 16, 256);
  const t = new THREE.CanvasTexture(c);
  const m = new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, opacity: 0, color: new THREE.Color(1.6, 1.6, 1.6) });
  const n = new THREE.Mesh(new THREE.PlaneGeometry(900, 1700), m);
  n.rotation.y = Math.PI / 2;
  n.position.set(0, 520, 0);
  n.renderOrder = 3;
  n.frustumCulled = false;
  return n;
}

function energiefluss(von, nach) {
  const kurve = new THREE.QuadraticBezierCurve3(von, von.clone().lerp(nach, 0.5).add(new THREE.Vector3(30, -20, -40)), nach);
  const n = 46;
  const pos = new Float32Array(n * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.3, "rgba(120,255,190,0.8)");
  g.addColorStop(1, "rgba(60,255,160,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  const mat = new THREE.PointsMaterial({ size: 26, map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: new THREE.Color(0x9dffcf).multiplyScalar(2.2), opacity: 0 });
  const punkte = new THREE.Points(geo, mat);
  punkte.frustumCulled = false;
  return {
    punkte,
    setzen(zeit, staerke) {
      mat.opacity = staerke;
      punkte.visible = staerke > 0.01;
      for (let i = 0; i < n; i++) {
        const t = (i / n + zeit * 0.55) % 1;
        const p = kurve.getPoint(t);
        pos[i * 3] = p.x;
        pos[i * 3 + 1] = p.y;
        pos[i * 3 + 2] = p.z + Math.sin(i * 7.1 + zeit * 3) * 3;
      }
      geo.attributes.position.needsUpdate = true;
    },
  };
}

export const BEFUNDE = [
  { anker: [-8, 286, 78], titel: "Schaltauge", wert: "0,8 mm verbogen", stand: "achtung" },
  { anker: [0, 716, 0], titel: "Reifendruck hinten", wert: "2,1 bar (Soll 3,5)", stand: "fehler" },
  { anker: [-140, 250, 30], titel: "Speichenspannung", wert: "± 18 % ungleich", stand: "achtung" },
  { anker: [235, 395, 52], titel: "Kette", wert: "0,6 % gelängt", stand: "achtung" },
  { anker: [455, 220, 0], titel: "Motor", wert: "keine Fehler", stand: "ok" },
  { anker: [650, 470, 0], titel: "Akku", wert: "86 % · 412 Ladezyklen", stand: "ok" },
  { anker: [1000, 760, 0], titel: "Federgabel", wert: "Service fällig (50 h)", stand: "achtung" },
  { anker: [1070, 402, -52], titel: "Bremsbelag vorn", wert: "1,2 mm Rest", stand: "fehler" },
  { anker: [890, 1095, 0], titel: "Software", wert: "4.2.1 → 4.3.0 verfügbar", stand: "achtung" },
];

export function effekteBauen({ modell, M, antrieb, zerleger, szene }) {
  const { G, teile, P } = modell;
  const radV = M.radUniforms("_v");
  const radH = M.radUniforms("_h");
  const hitzeV = M.hitzeUniforms("_v");
  const hitzeH = M.hitzeUniforms("_h");

  const schleierV = speichenschleier();
  schleierV.position.z = 0;
  G.laufradV.add(schleierV);

  const akkuRichtung = b2t(JSON.parse(teile.akku.userData.richtung || "[0.5,0,-0.8]")).normalize();
  const akkuQuer = b2t(JSON.parse(teile.akku.userData.quer || "[0,0,-1]")).normalize();
  const fluss = energiefluss(G.akku.position.clone().add(new THREE.Vector3(0, -30, -10)), P.tretlager.clone().add(new THREE.Vector3(10, 30, -50)));
  modell.rad.add(fluss.punkte);

  const vorhang = lichtvorhang();
  szene.add(vorhang);
  const belagV = [teile.belag_v_l, teile.belag_v_r];
  const belagH = [teile.belag_h_l, teile.belag_h_r];
  const scheinwerfer = new THREE.SpotLight(0xfff4e0, 0, 0, THREE.MathUtils.degToRad(18), 0.6, 0);
  scheinwerfer.position.copy(teile.licht_vorne.getWorldPosition(new THREE.Vector3()));
  scheinwerfer.target.position.copy(scheinwerfer.position).add(new THREE.Vector3(2000, -700, 0));
  szene.add(scheinwerfer, scheinwerfer.target);

  let wVorn = 0;
  let omegaVorn = 1.2;
  let anlaufV = 0;
  const ledMats = [...M.vonTeil("akku")].filter((m) => m.name === "LED");
  const lichtMats = [...M.vonTeil("licht_vorne")];

  function setzen(p, dt, zeit, bewegung) {
    const k = Math.floor(p);
    const f = p - k;
    const aus = { kapitel: k };

    const scan = fenster(0.92, 1.05, 1.82, 1.97, p);
    SCAN.uScanStaerke.value = scan;
    SCAN.uScanPos.value = THREE.MathUtils.lerp(-520, 1700, glatt(1.05, 1.78, p));
    aus.scanX = SCAN.uScanPos.value;
    aus.scan = scan;
    vorhang.position.x = SCAN.uScanPos.value;
    vorhang.material.opacity = scan * 0.5;
    vorhang.visible = scan > 0.01;

    const zerlegt = glatt(2.02, 2.55, p) * (1 - glatt(2.66, 2.98, p));
    zerleger.setzen(zerlegt);
    antrieb.zustand.zerlegt = zerlegt;
    aus.zerlegt = zerlegt;

    const imAntrieb = fenster(2.7, 3.0, 3.75, 3.95, p);
    const imRad = fenster(4.75, 5.0, 5.8, 5.95, p);
    const grundtempo = bewegung ? 90 : 0;
    antrieb.zustand.v = grundtempo + (bewegung ? 520 : 0) * imAntrieb + (bewegung ? 240 : 0) * imRad;
    if (k === 3) {
      antrieb.zustand.ziel = Math.round(klemm((f - 0.05) / 0.55, 0, 1) * 11);
    } else if (k < 3) {
      antrieb.zustand.ziel = 0;
    } else {
      antrieb.zustand.ziel = 6;
    }
    if (!bewegung) antrieb.zustand.gang = antrieb.zustand.ziel;
    const zustand = antrieb.aktualisieren(dt);
    aus.gang = Math.round(zustand.gang) + 1;
    aus.ritzel = antrieb.ritzelZaehne(zustand.gang);
    aus.uebersetzung = antrieb.kettenblattZaehne / aus.ritzel;

    const bremsen = k === 4 ? glatt(0.18, 0.5, f) : 0;
    const zielOmega = k === 4 ? THREE.MathUtils.lerp(26, 0.0, bremsen) : k > 4 ? 0.0 : 1.2;
    omegaVorn += (zielOmega - omegaVorn) * Math.min(1, dt * (k === 4 && f < 0.18 ? 2.5 : 4));
    if (!bewegung) omegaVorn = 0;
    wVorn -= omegaVorn * dt;
    G.laufradV.rotation.z = wVorn;
    schleierV.material.opacity = glatt(6, 20, omegaVorn) * 0.9;
    teile.speichen_v.visible = omegaVorn < 24;
    const druck = k === 4 ? fenster(0.16, 0.22, 0.58, 0.66, f) : 0;
    belagV[0].position.z = belagV[0].userData.basis.p.z + druck * 0.9;
    belagV[1].position.z = belagV[1].userData.basis.p.z - druck * 0.9;
    const hitze = k === 4 ? glatt(0.2, 0.52, f) * (1 - 0.75 * glatt(0.6, 1.0, f)) : k === 3 ? 0 : 0;
    hitzeV.uHitze.value = hitze;
    anlaufV = Math.max(anlaufV, hitze * 0.9);
    if (p < 3.9) anlaufV = 0;
    hitzeV.uAnlauf.value = anlaufV;
    hitzeV.uZeit.value = zeit;
    hitzeH.uHitze.value = 0;
    aus.temperatur = Math.round(24 + hitze * 410);
    aus.drehzahl = Math.round((omegaVorn * 60) / (Math.PI * 2));
    void belagH;

    const schlag = k === 5 ? 1 - glatt(0.12, 0.66, f) : k < 5 ? 1 : 0;
    const zeigen = fenster(4.85, 5.05, 5.75, 5.92, p);
    radH.uSchlag.value = 10 * schlag * glatt(4.6, 4.95, p);
    radH.uSpannung.value = schlag;
    radH.uSpannungZeigen.value = zeigen;
    radV.uSchlag.value = 0;
    aus.schlag = (3.2 * schlag + 0.15 * (1 - schlag)).toFixed(1).replace(".", ",");
    aus.spannung = Math.round(18 * schlag + 2 * (1 - schlag));

    const raus = k === 6 ? glatt(0.04, 0.38, f) * (1 - glatt(0.6, 0.86, f)) : 0;
    const zBasis = G.akku.userData.basis.p;
    if (zerlegt < 0.001) {
      G.akku.position.copy(zBasis).addScaledVector(akkuRichtung, raus * 120).addScaledVector(akkuQuer, -raus * 70).add(new THREE.Vector3(0, 0, raus * 220));
    }
    const blinken = raus > 0.05 ? 0.5 + 0.5 * Math.sin(zeit * 6) : 1;
    for (const m of ledMats) m.emissiveIntensity = 2.6 * blinken;
    fluss.setzen(zeit, k === 6 ? fenster(0.82, 0.88, 0.97, 1.0, f) : 0);
    aus.akku = raus;

    const ende = glatt(6.85, 7.3, p);
    scheinwerfer.intensity = 0;
    for (const m of lichtMats) if (m.name === "Licht") m.emissiveIntensity = 3 + 5 * ende;
    scheinwerfer.intensity = ende * 26;
    aus.ende = ende;

    return aus;
  }

  return { setzen, schleierV };
}
