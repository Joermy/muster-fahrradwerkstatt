import * as THREE from "../vendor/three.module.min.js";

const WEGE = [
  ["G:laufradV", 560, -110, -40, 0.12, 0.55, 0.0],
  ["G:laufradH", -600, -110, 80, 0.12, 0.55, 0.0],
  ["T:reifen_v", 0, 0, -110, 0.5, 0.45, 0.0],
  ["T:reifen_h", 0, 0, -110, 0.5, 0.45, 0.0],
  ["T:bremsscheibe_v", 0, 0, -170, 0.45, 0.45, 0.0],
  ["T:bremsscheibe_h", 0, 0, -170, 0.45, 0.45, 0.0],
  ["G:ritzel", 0, 0, 150, 0.42, 0.45, 0.0],
  ["G:vorderbau", 210, 110, 0, 0.0, 0.5, 0.0],
  ["G:federung", 50, -170, 0, 0.22, 0.5, 0.0],
  ["G:cockpit", 30, 190, 0, 0.3, 0.5, 0.0],
  ["T:sattel", -60, 200, 0, 0.18, 0.5, 0.0],
  ["T:ruecklicht", -200, 110, 0, 0.3, 0.45, 0.0],
  ["T:licht_hinten", -200, 110, 0, 0.3, 0.45, 0.0],
  ["G:akku", 60, -230, -190, 0.32, 0.5, 0.0],
  ["G:motor", 40, -290, 30, 0.42, 0.5, 0.0],
  ["G:kurbel", 0, -40, 230, 0.28, 0.5, 0.0],
  ["G:schaltwerk", -140, -110, 230, 0.36, 0.5, 0.0],
  ["G:bremseV", 0, 40, -200, 0.38, 0.45, 0.0],
  ["G:bremseH", 30, 60, -220, 0.38, 0.45, 0.0],
];

const sanft = (x) => x * x * x * (x * (x * 6 - 15) + 10);

export function zerlegerBauen(modell) {
  const { G, teile } = modell;
  const eintraege = WEGE.map(([ziel, x, y, z, ein, dauer, dreh]) => {
    const obj = ziel.startsWith("G:") ? G[ziel.slice(2)] : teile[ziel.slice(2)];
    return { obj, weg: new THREE.Vector3(x, y, z), ein, dauer, dreh, basis: obj.userData.basis.p.clone() };
  });

  function setzen(e) {
    for (const t of eintraege) {
      const f = sanft(THREE.MathUtils.clamp((e - t.ein) / t.dauer, 0, 1));
      t.obj.position.copy(t.basis).addScaledVector(t.weg, f);
      t.f = f;
    }
    teile.leitungen.visible = e < 0.04;
  }

  function anker(name) {
    const o = G[name] || teile[name];
    const box = new THREE.Box3().setFromObject(o);
    return box.getCenter(new THREE.Vector3());
  }

  return { setzen, anker, eintraege };
}
