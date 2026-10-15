import * as THREE from "../vendor/three.module.min.js";
import { GLTFLoader, MeshoptDecoder } from "../vendor/three-zusatz.min.js";

export function b2t(v) {
  return new THREE.Vector3(v[0], v[2], -v[1]);
}

export const TEIL_ZU = {
  rahmen: ["rahmen", "Rahmen"],
  aufkleber: ["rahmen", "Rahmen"],
  akku: ["akku", "Akku"],
  motor: ["motor", "Antriebsmotor"],
  gabel: ["federgabel", "Federgabel"],
  gabel_unten: ["federgabel", "Federgabel"],
  vorbau: ["lenker", "Vorbau"],
  lenker: ["lenker", "Lenker"],
  griffe: ["lenker", "Griffe"],
  display: ["display", "Display"],
  bildschirm: ["display", "Display"],
  bremshebel_l: ["bremshebel", "Bremshebel hinten"],
  bremshebel_r: ["bremshebel", "Bremshebel vorn"],
  schalthebel: ["schalthebel", "Schalthebel"],
  sattel: ["sattel", "Sattel"],
  sattelstuetze: ["sattel", "Sattelstütze"],
  felge_v: ["laufrad", "Felge vorn"],
  felge_h: ["laufrad", "Felge hinten"],
  reifen_v: ["reifen", "Reifen vorn"],
  reifen_h: ["reifen", "Reifen hinten"],
  speichen_v: ["speichen", "Speichen vorn"],
  speichen_h: ["speichen", "Speichen hinten"],
  nabe_v: ["nabe", "Nabe vorn"],
  nabe_h: ["nabe", "Nabe hinten"],
  bremsscheibe_v: ["bremsscheibe", "Bremsscheibe vorn"],
  bremsscheibe_h: ["bremsscheibe", "Bremsscheibe hinten"],
  bremssattel_v: ["bremssattel", "Bremssattel vorn"],
  bremssattel_h: ["bremssattel", "Bremssattel hinten"],
  kassette: ["kassette", "Kassette"],
  kettenblatt: ["kettenblatt", "Kettenblatt"],
  kurbel_r: ["kettenblatt", "Kurbel"],
  kurbel_l: ["kettenblatt", "Kurbel"],
  pedal_r: ["kettenblatt", "Pedal"],
  pedal_l: ["kettenblatt", "Pedal"],
  schaltwerk_halter: ["schaltwerk", "Schaltwerk"],
  schaltwerk_arm: ["schaltwerk", "Schaltwerk"],
  schaltwerk_kaefig: ["schaltwerk", "Schaltwerk"],
  rolle_oben: ["schaltwerk", "Schaltrolle"],
  rolle_unten: ["schaltwerk", "Schaltrolle"],
  kette: ["kette", "Kette"],
  licht_vorne: ["lenker", "Scheinwerfer"],
  licht_gehaeuse: ["lenker", "Scheinwerfer"],
  ruecklicht: ["sattel", "Rücklicht"],
  licht_hinten: ["sattel", "Rücklicht"],
};

function entpacken(teil) {
  teil.updateMatrixWorld(true);
  const netze = [];
  teil.traverse((k) => {
    if (k.isMesh) netze.push(k);
  });
  for (const netz of netze) {
    const geo = netz.geometry;
    for (const name of Object.keys(geo.attributes)) {
      const a = geo.attributes[name];
      if (a.isInterleavedBufferAttribute || !(a.array instanceof Float32Array) || a.normalized) {
        const neu = new Float32Array(a.count * a.itemSize);
        for (let i = 0; i < a.count; i++) {
          for (let c = 0; c < a.itemSize; c++) neu[i * a.itemSize + c] = a.getComponent(i, c);
        }
        geo.setAttribute(name, new THREE.BufferAttribute(neu, a.itemSize));
      }
    }
    if (netz !== teil) {
      const rel = new THREE.Matrix4().copy(teil.matrixWorld).invert().multiply(netz.matrixWorld);
      geo.applyMatrix4(rel);
      if (netz.parent !== teil) teil.add(netz);
      netz.position.set(0, 0, 0);
      netz.quaternion.identity();
      netz.scale.set(1, 1, 1);
      netz.updateMatrix();
    }
    geo.computeBoundingBox();
    geo.computeBoundingSphere();
  }
  return netze;
}

export function modellHolen(url, fortschritt = () => {}) {
  const lader = new GLTFLoader();
  lader.setMeshoptDecoder(MeshoptDecoder);
  return lader.loadAsync(url, (e) => {
    if (e.total) fortschritt(e.loaded / e.total);
  });
}

function umhaengen(teil, gruppe) {
  teil.updateMatrixWorld(true);
  gruppe.updateMatrixWorld(true);
  const w = teil.matrixWorld.clone();
  gruppe.add(teil);
  teil.matrix.copy(gruppe.matrixWorld.clone().invert().multiply(w));
  teil.matrix.decompose(teil.position, teil.quaternion, teil.scale);
}

function gruppeAn(name, punkt, eltern) {
  const g = new THREE.Group();
  g.name = name;
  eltern.updateMatrixWorld(true);
  g.position.copy(eltern.worldToLocal(punkt.clone()));
  eltern.add(g);
  g.updateMatrixWorld(true);
  return g;
}

export function modellEinrichten(gltf, M, masse) {
  const quelle = gltf.scene;
  const teile = {};
  quelle.traverse((o) => {
    if (o.parent === quelle) teile[o.name] = o;
  });
  for (const [name, obj] of Object.entries(teile)) {
    const netze = entpacken(obj);
    const radSeite = name.endsWith("_v") ? "_v" : name.endsWith("_h") || name === "kassette" ? "_h" : "";
    for (const netz of netze) {
      const ersetzen = (m) => (m ? M.holen(m.name, { rad: radSeite, teil: name }) : m);
      netz.material = Array.isArray(netz.material) ? netz.material.map(ersetzen) : ersetzen(netz.material);
      const leuchtet = ["Licht", "Ruecklicht", "LED", "Bildschirm"].includes(netz.material.name);
      netz.castShadow = !leuchtet && name !== "aufkleber" && name !== "bildschirm";
      netz.receiveShadow = true;
      netz.userData.teil = name;
    }
    obj.userData.teil = name;
  }

  const rad = new THREE.Group();
  rad.name = "rad";
  rad.add(quelle);
  rad.updateMatrixWorld(true);

  const P = {
    vorn: b2t(masse.vorn),
    hinten: b2t(masse.hinten),
    tretlager: b2t(masse.tretlager),
    krone: b2t(masse.krone),
    lenkachse: b2t(masse.lenkachse).normalize(),
    lenkermitte: b2t(masse.lenkermitte),
    sitzrohrOben: b2t(masse.sitzrohr_oben),
  };

  const G = {};
  G.vorderbau = gruppeAn("vorderbau", P.krone, rad);
  G.federung = gruppeAn("federung", P.vorn, G.vorderbau);
  G.laufradV = gruppeAn("laufradV", P.vorn, G.federung);
  G.laufradH = gruppeAn("laufradH", P.hinten, rad);
  G.ritzel = gruppeAn("ritzel", P.hinten, G.laufradH);
  G.kurbel = gruppeAn("kurbel", P.tretlager, rad);
  G.cockpit = gruppeAn("cockpit", P.lenkermitte, G.vorderbau);
  G.sattel = gruppeAn("sattel", P.sitzrohrOben, rad);
  G.akku = gruppeAn("akku", teile.akku.position.clone(), rad);
  G.motor = gruppeAn("motor", P.tretlager, rad);
  G.bremseH = gruppeAn("bremseH", teile.bremssattel_h.position.clone(), rad);
  G.bremseV = gruppeAn("bremseV", teile.bremssattel_v.position.clone(), G.federung);
  G.schaltwerk = gruppeAn("schaltwerk", P.hinten, rad);

  const nach = {
    vorderbau: ["gabel", "leitungen"],
    federung: ["gabel_unten"],
    laufradV: ["felge_v", "reifen_v", "speichen_v", "nabe_v", "bremsscheibe_v"],
    laufradH: ["felge_h", "reifen_h", "speichen_h", "nabe_h", "bremsscheibe_h"],
    ritzel: ["kassette"],
    kurbel: ["kettenblatt", "kurbel_r", "kurbel_l"],
    cockpit: ["vorbau", "lenker", "griffe", "bremshebel_l", "bremshebel_r", "schalthebel", "display", "bildschirm", "licht_gehaeuse", "licht_vorne"],
    sattel: ["sattel", "sattelstuetze", "ruecklicht", "licht_hinten"],
    akku: ["akku"],
    motor: ["motor"],
    bremseH: ["bremssattel_h", "belag_h_l", "belag_h_r"],
    bremseV: ["bremssattel_v", "belag_v_l", "belag_v_r"],
    schaltwerk: ["schaltwerk_halter", "schaltwerk_arm", "schaltwerk_kaefig", "rolle_oben", "rolle_unten"],
  };
  for (const [g, namen] of Object.entries(nach)) {
    for (const n of namen) if (teile[n]) umhaengen(teile[n], G[g]);
  }
  for (const n of ["pedal_r", "pedal_l"]) umhaengen(teile[n], G.kurbel);

  const glieder = { aussen: teile.glied_aussen, innen: teile.glied_innen };
  for (const g of Object.values(glieder)) g.parent.remove(g);

  for (const t of Object.values(teile)) t.userData.basis = { p: t.position.clone(), q: t.quaternion.clone(), s: t.scale.clone() };
  for (const g of Object.values(G)) g.userData.basis = { p: g.position.clone(), q: g.quaternion.clone() };

  return { rad, teile, G, P, glieder, staender: teile.staender };
}
