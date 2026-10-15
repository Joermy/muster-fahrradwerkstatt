import * as THREE from "../vendor/three.module.min.js";

export const EINSTELLUNGEN = [
  { name: "ankunft", auge: [2650, 700, 3150], ziel: [620, 460, 0], fov: 28, drift: [-260, 40, 120], versatz: 0.16 },
  { name: "diagnose", auge: [575, 560, 3900], ziel: [575, 470, 0], fov: 27, drift: [0, 0, -120], versatz: 0.14 },
  { name: "zerlegen", auge: [2500, 1750, 3600], ziel: [560, 380, 0], fov: 31, drift: [-220, -60, 120], versatz: -0.14 },
  { name: "antrieb", auge: [250, 440, 1000], ziel: [130, 330, 40], fov: 30, drift: [60, -20, -40], fokus: 820, blende: 0.0016, versatz: 0.14 },
  { name: "bremse", auge: [1290, 520, -560], ziel: [1075, 398, -52], fov: 29, drift: [-50, 20, -30], fokus: 590, blende: 0.0022, versatz: -0.14 },
  { name: "laufrad", auge: [-1500, 760, 1250], ziel: [40, 370, 10], fov: 27, drift: [80, -30, -60], fokus: 2000, blende: 0.0006, versatz: 0.14 },
  { name: "akku", auge: [900, 260, 1500], ziel: [660, 430, 40], fov: 32, drift: [-80, 30, -40], fokus: 1500, blende: 0.0009, versatz: -0.14 },
  { name: "uebergabe", auge: [3150, 330, 1900], ziel: [560, 470, 0], fov: 30, drift: [-220, 40, 120], versatz: 0.14 },
];

const HALTEN = 0.6;
const sanft = (x) => x * x * x * (x * (x * 6 - 15) + 10);

export function regieBauen(kamera, schaerfe) {
  const auge = new THREE.Vector3();
  const ziel = new THREE.Vector3();
  const tmpA = new THREE.Vector3();
  const tmpB = new THREE.Vector3();
  const aktAuge = new THREE.Vector3(...EINSTELLUNGEN[0].auge);
  const aktZiel = new THREE.Vector3(...EINSTELLUNGEN[0].ziel);
  let aktFov = EINSTELLUNGEN[0].fov;
  let aktFokus = 2500;
  let aktBlende = 0;
  let aktVersatz = EINSTELLUNGEN[0].versatz || 0;
  let ersterAufruf = true;
  let zugWinkel = 0;
  let zugZiel = 0;

  function einstellung(i, f, a, z) {
    const e = EINSTELLUNGEN[Math.max(0, Math.min(EINSTELLUNGEN.length - 1, i))];
    const d = (f - 0.3) * 1.0;
    a.set(e.auge[0] + e.drift[0] * d, e.auge[1] + e.drift[1] * d, e.auge[2] + e.drift[2] * d);
    z.set(...e.ziel);
    return e;
  }

  function fovFuer(fov, seiten) {
    if (seiten >= 16 / 9) return fov;
    const h = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * (16 / 9));
    const v = 2 * Math.atan(Math.tan(h / 2) / seiten);
    return Math.min(72, THREE.MathUtils.radToDeg(v) * (seiten < 1 ? 0.86 : 1));
  }

  function aktualisieren(p, dt, { seiten, breite, hoehe, bewegung = true }) {
    const k = Math.floor(p);
    const f = p - k;
    const e1 = einstellung(k, bewegung ? f : 0.3, auge, ziel);
    let fov = e1.fov;
    let fokus = e1.fokus || auge.distanceTo(ziel);
    let blende = e1.blende || 0;
    let versatz = e1.versatz || 0;
    if (f > HALTEN && k < EINSTELLUNGEN.length - 1) {
      const u = sanft((f - HALTEN) / (1 - HALTEN));
      const e2 = einstellung(k + 1, 0, tmpA, tmpB);
      const mitte = new THREE.Vector3().lerpVectors(auge, tmpA, 0.5);
      const hub = Math.sin(u * Math.PI) * Math.min(900, auge.distanceTo(tmpA) * 0.25);
      auge.lerp(tmpA, u);
      auge.y += hub * 0.35;
      auge.addScaledVector(mitte.sub(ziel).normalize(), hub * 0.4);
      ziel.lerp(tmpB, u);
      fov = THREE.MathUtils.lerp(fov, e2.fov, u);
      fokus = THREE.MathUtils.lerp(fokus, e2.fokus || tmpA.distanceTo(tmpB), u);
      blende = THREE.MathUtils.lerp(blende, e2.blende || 0, u) * (1 - Math.sin(u * Math.PI) * 0.8);
      versatz = THREE.MathUtils.lerp(versatz, e2.versatz || 0, u);
    }

    zugWinkel += (zugZiel - zugWinkel) * Math.min(1, dt * 6);
    if (Math.abs(zugWinkel) > 1e-4) {
      tmpA.copy(auge).sub(ziel).applyAxisAngle(new THREE.Vector3(0, 1, 0), zugWinkel);
      auge.copy(ziel).add(tmpA);
    }

    const weich = ersterAufruf ? 1 : 1 - Math.exp(-dt * 7);
    ersterAufruf = false;
    aktAuge.lerp(auge, weich);
    aktZiel.lerp(ziel, weich);
    aktFov += (fovFuer(fov, seiten) - aktFov) * weich;
    aktFokus += (fokus - aktFokus) * weich;
    aktBlende += (blende - aktBlende) * weich;
    aktVersatz += (versatz - aktVersatz) * weich;

    kamera.position.copy(aktAuge);
    kamera.lookAt(aktZiel);
    kamera.fov = aktFov;
    if (seiten < 1) kamera.setViewOffset(breite, hoehe, 0, hoehe * 0.14, breite, hoehe);
    else kamera.setViewOffset(breite, hoehe, -aktVersatz * breite * Math.min(1, (seiten - 1) * 1.6), 0, breite, hoehe);
    kamera.updateProjectionMatrix();

    if (schaerfe) {
      const an = aktBlende > 0.0002 && schaerfe.userData.erlaubt !== false;
      schaerfe.enabled = an;
      if (an) {
        schaerfe.uniforms.focus.value = aktFokus;
        schaerfe.uniforms.aperture.value = aktBlende;
      }
    }
    return { kapitel: k, anteil: f, name: e1.name };
  }

  return {
    aktualisieren,
    ziehen(dx) {
      zugZiel = THREE.MathUtils.clamp(zugZiel - dx * 0.004, -0.9, 0.9);
    },
    loslassen() {
      zugZiel = 0;
    },
  };
}
