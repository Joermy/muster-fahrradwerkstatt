import * as THREE from "../vendor/three.module.min.js";
import { b2t } from "./modell.js";

const TAU = Math.PI * 2;

function teilkreis(zaehne, teilung) {
  return teilung / (2 * Math.sin(Math.PI / zaehne));
}

function tangente(a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const d = Math.hypot(dx, dy);
  const ux = dx / d;
  const uy = dy / d;
  const k = (a.s * a.r - b.s * b.r) / d;
  const c = Math.max(-1, Math.min(1, k));
  const s = Math.sqrt(1 - c * c);
  const mx = c * ux - s * uy;
  const my = c * uy + s * ux;
  return {
    von: { x: a.x + a.s * a.r * mx, y: a.y + a.s * a.r * my },
    nach: { x: b.x + b.s * b.r * mx, y: b.y + b.s * b.r * my },
  };
}

function winkel(k, p) {
  return Math.atan2(p.y - k.y, p.x - k.x);
}

function weg(kreise) {
  const n = kreise.length;
  const t = [];
  for (let i = 0; i < n; i++) t.push(tangente(kreise[i], kreise[(i + 1) % n]));
  const stuecke = [];
  let laenge = 0;
  for (let i = 0; i < n; i++) {
    const k = kreise[i];
    const ein = t[(i - 1 + n) % n].nach;
    const aus = t[i].von;
    const w0 = winkel(k, ein);
    const w1 = winkel(k, aus);
    let dw = k.s > 0 ? w0 - w1 : w1 - w0;
    dw = ((dw % TAU) + TAU) % TAU;
    const lb = dw * k.r;
    stuecke.push({ art: "bogen", k, w0, dw, l: lb, z0: k.z, z1: k.z });
    laenge += lb;
    const g = t[i];
    const lg = Math.hypot(g.nach.x - g.von.x, g.nach.y - g.von.y);
    stuecke.push({ art: "gerade", von: g.von, nach: g.nach, l: lg, z0: k.z, z1: kreise[(i + 1) % n].z });
    laenge += lg;
  }
  return { stuecke, laenge };
}

function punktAuf(w, s, ziel) {
  let rest = ((s % w.laenge) + w.laenge) % w.laenge;
  for (const st of w.stuecke) {
    if (rest <= st.l || st === w.stuecke[w.stuecke.length - 1]) {
      const f = st.l > 0 ? Math.min(1, rest / st.l) : 0;
      if (st.art === "bogen") {
        const a = st.w0 - st.k.s * st.dw * f;
        ziel.set(st.k.x + st.k.r * Math.cos(a), st.k.y + st.k.r * Math.sin(a), st.z0);
      } else {
        ziel.set(st.von.x + (st.nach.x - st.von.x) * f, st.von.y + (st.nach.y - st.von.y) * f, st.z0 + (st.z1 - st.z0) * f);
      }
      return ziel;
    }
    rest -= st.l;
  }
  return ziel;
}

export function antriebBauen(modell, masse, M) {
  const { G, teile, glieder, P } = modell;
  const teilung = masse.teilung;
  const zaehne = masse.kassette.zaehne;
  const rKb = teilkreis(masse.kettenblatt.zaehne, teilung);
  const rRolle = teilkreis(masse.rolle_zaehne, teilung);
  const kaefig = masse.kaefig;
  const zKb = -masse.kettenblatt.y;
  const zRitzel = (g) => -masse.kassette.y_gross + (zaehne.length - 1 - g) * masse.kassette.abstand;
  const rRitzel = (g) => {
    const i = Math.max(0, Math.min(zaehne.length - 1, g));
    const a = Math.floor(i);
    const b = Math.min(zaehne.length - 1, a + 1);
    const f = i - a;
    return teilkreis(zaehne[a], teilung) * (1 - f) + teilkreis(zaehne[b], teilung) * f;
  };
  const H = P.hinten;
  const T = P.tretlager;
  const SPALT = 7;
  const RICHTUNG = THREE.MathUtils.degToRad(-100);

  function rolleOben(g) {
    const r = rRitzel(g) + rRolle + SPALT;
    return { x: H.x + r * Math.cos(RICHTUNG), y: H.y + r * Math.sin(RICHTUNG) };
  }

  function kreiseFuer(g, phi) {
    const j1 = rolleOben(g);
    const z = zRitzel(g);
    return [
      { x: T.x, y: T.y, r: rKb, s: 1, z: zKb },
      { x: j1.x + kaefig * Math.sin(phi), y: j1.y - kaefig * Math.cos(phi), r: rRolle, s: 1, z },
      { x: j1.x, y: j1.y, r: rRolle, s: -1, z },
      { x: H.x, y: H.y, r: rRitzel(g), s: 1, z },
    ];
  }

  const lMax = weg(kreiseFuer(zaehne.length - 1, THREE.MathUtils.degToRad(12))).laenge;
  const glieder_n = Math.ceil(lMax / teilung / 2) * 2;
  const laenge = glieder_n * teilung;

  function kaefigWinkel(g) {
    let a = THREE.MathUtils.degToRad(-40);
    let b = THREE.MathUtils.degToRad(120);
    for (let i = 0; i < 40; i++) {
      const m = (a + b) / 2;
      if (weg(kreiseFuer(g, m)).laenge > laenge) a = m;
      else b = m;
    }
    return (a + b) / 2;
  }

  const matrix = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const sk = new THREE.Vector3(1, 1, 1);
  const p0 = new THREE.Vector3();
  const p1 = new THREE.Vector3();
  const mitte = new THREE.Vector3();
  const zAchse = new THREE.Vector3(0, 0, 1);
  const instanz = (vorlage, anzahl) => {
    const netz = vorlage.children.find((c) => c.isMesh) || vorlage;
    const geo = netz.geometry;
    const mat = netz.material;
    const im = new THREE.InstancedMesh(geo, mat, anzahl);
    im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    im.castShadow = true;
    im.receiveShadow = true;
    im.frustumCulled = false;
    im.userData.teil = "kette";
    return im;
  };
  const netzeVon = (vorlage) => {
    const n = [];
    vorlage.traverse((c) => c.isMesh && n.push(c));
    return n;
  };
  const halb = glieder_n / 2;
  const kette = new THREE.Group();
  kette.name = "kette";
  kette.userData.teil = "kette";
  const aussen = netzeVon(glieder.aussen).map((n) => { const v = new THREE.Group(); v.add(n.clone()); return instanz(v, halb); });
  const innen = netzeVon(glieder.innen).map((n) => { const v = new THREE.Group(); v.add(n.clone()); return instanz(v, halb); });
  [...aussen, ...innen].forEach((im) => kette.add(im));
  modell.rad.add(kette);

  const halterOrt = b2t(JSON.parse(teile.schaltwerk_halter.userData.ort || "[0,0,0]"));
  const kaefigObj = teile.schaltwerk_kaefig;
  const rolleO = teile.rolle_oben;
  const rolleU = teile.rolle_unten;
  const arm = teile.schaltwerk_arm;
  const schaltwerkGruppe = G.schaltwerk;
  const kaefigGruppe = new THREE.Group();
  schaltwerkGruppe.add(kaefigGruppe);
  for (const o of [kaefigObj, rolleO, rolleU]) {
    kaefigGruppe.add(o);
    o.position.copy(o.userData.basis.p);
  }
  kaefigObj.position.set(0, 0, 0);
  rolleO.position.set(0, 0, 0);
  rolleU.position.set(0, -kaefig, 0);

  const zustand = {
    gang: 6,
    ziel: 6,
    s: 0,
    v: 0,
    phi: kaefigWinkel(6),
    wRad: 0,
    wKurbel: 0,
    zerlegt: 0,
    linie: new THREE.Vector3(),
  };

  function versatzRitzel(g) {
    const i = Math.round(g);
    return 0.13 * (zaehne.length - 1 - i);
  }

  function aktualisieren(dt) {
    const schritt = Math.min(1, dt * 3.2);
    zustand.gang += (zustand.ziel - zustand.gang) * schritt;
    if (Math.abs(zustand.ziel - zustand.gang) < 0.002) zustand.gang = zustand.ziel;
    const g = zustand.gang;
    zustand.phi += (kaefigWinkel(g) - zustand.phi) * Math.min(1, dt * 12);
    zustand.s += zustand.v * dt;

    const kreise = kreiseFuer(g, zustand.phi);
    const w = weg(kreise);
    const rG = kreise[3].r;

    zustand.wKurbel -= (zustand.v * dt) / rKb;
    zustand.wRad -= (zustand.v * dt) / rG;
    G.kurbel.rotation.z = zustand.wKurbel;
    G.laufradH.rotation.z = zustand.wRad;
    teile.pedal_r.rotation.z = -zustand.wKurbel;
    teile.pedal_l.rotation.z = -zustand.wKurbel;
    rolleO.rotation.z = zustand.s / rRolle;
    rolleU.rotation.z = -zustand.s / rRolle;

    const ri = Math.round(g);
    const zr = zaehne[ri];
    const sStart = w.stuecke.slice(0, 6).reduce((a, st) => a + st.l, 0);
    const kZiel = Math.ceil((sStart - zustand.s) / teilung);
    punktAuf(w, zustand.s + kZiel * teilung, p0);
    const wBolzen = Math.atan2(p0.y - H.y, p0.x - H.x);
    const lueckeLokal = wBolzen - zustand.wRad - versatzRitzel(g);
    const schritte = TAU / zr;
    const korr = lueckeLokal - Math.round(lueckeLokal / schritte) * schritte;
    G.ritzel.userData.korr = (G.ritzel.userData.korr ?? korr) + (korr - (G.ritzel.userData.korr ?? korr)) * Math.min(1, dt * 20);
    G.ritzel.rotation.z = G.ritzel.userData.korr;

    const j1 = { x: kreise[2].x, y: kreise[2].y };
    const lokal = schaltwerkGruppe.worldToLocal(new THREE.Vector3(j1.x, j1.y, kreise[2].z));
    kaefigGruppe.position.copy(lokal);
    kaefigGruppe.rotation.z = zustand.phi;
    const halterLokal = schaltwerkGruppe.worldToLocal(halterOrt.clone());
    const kopf = lokal.clone().add(new THREE.Vector3(10, 30, 6));
    const d = kopf.clone().sub(halterLokal);
    arm.position.copy(halterLokal);
    arm.rotation.set(0, Math.atan2(-d.z, Math.hypot(d.x, d.y)) * 0.6, Math.atan2(d.y, d.x));
    arm.scale.set(Math.max(0.5, d.length() / 64), 1, 1);

    const unten = modell.P.tretlager.y - 520;
    for (let i = 0; i < glieder_n; i++) {
      const s0 = zustand.s + i * teilung;
      punktAuf(w, s0, p0);
      punktAuf(w, s0 + teilung, p1);
      if (zustand.zerlegt > 0) {
        const f = THREE.MathUtils.smoothstep(zustand.zerlegt * 1.6 - (i / glieder_n) * 0.6, 0, 1);
        const lx = -250 + i * teilung * 0.98;
        p0.lerp(mitte.set(lx, unten, 140), f);
        p1.lerp(mitte.set(lx + teilung, unten, 140), f);
      }
      const dx = p1.x - p0.x;
      const dy = p1.y - p0.y;
      q.setFromAxisAngle(zAchse, Math.atan2(dy, dx));
      matrix.compose(p0, q, sk);
      const liste = i % 2 === 0 ? aussen : innen;
      const k = i >> 1;
      for (const im of liste) im.setMatrixAt(k, matrix);
    }
    for (const im of [...aussen, ...innen]) im.instanceMatrix.needsUpdate = true;
    return { gang: g, rRitzel: rG, glieder: glieder_n, phi: zustand.phi };
  }

  aktualisieren(0);
  return {
    zustand, aktualisieren, kette, glieder: glieder_n,
    ritzelZaehne: (g) => zaehne[Math.round(g)],
    kettenblattZaehne: masse.kettenblatt.zaehne,
    rRitzel,
  };
}
