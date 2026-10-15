import * as THREE from "../vendor/three.module.min.js";

export function studioBauen(renderer, stufe) {
  const zelt = new THREE.Scene();
  zelt.background = new THREE.Color(0x07090a);
  const flaeche = (farbe, staerke, b, h, pos, blick) => {
    const m = new THREE.MeshBasicMaterial({ color: new THREE.Color(farbe).multiplyScalar(staerke), side: THREE.DoubleSide });
    const n = new THREE.Mesh(new THREE.PlaneGeometry(b, h), m);
    n.position.set(...pos);
    n.lookAt(...blick);
    zelt.add(n);
    return n;
  };
  for (let i = -2; i <= 2; i++) flaeche(0xeaf2ff, 9.0, 0.3, 5.0, [i * 1.6, 6, 0], [i * 1.6, 0, 0]);
  flaeche(0xffd6a8, 3.2, 3.2, 2.2, [-6, 2.2, 2.5], [0, 1, 0]);
  flaeche(0x9fd4d2, 2.6, 6, 0.6, [0, 1.4, -6], [0, 1, 0]);
  flaeche(0x22272a, 1.0, 20, 20, [0, -1.2, 0], [0, 1, 0]);
  flaeche(0xffffff, 6.0, 0.25, 4.0, [5, 1.5, -1.5], [0, 1, 0]);
  flaeche(0xffffff, 6.0, 0.25, 4.0, [-5, 1.5, 1.5], [0, 1, 0]);
  flaeche(0xffffff, 0.9, 4, 2.4, [3, 1.8, 6], [0, 1, 0]);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromScene(zelt, 0.02).texture;
  pmrem.dispose();

  const licht = new THREE.Group();
  const sonne = new THREE.SpotLight(0xfff1e0, 8.0, 0, THREE.MathUtils.degToRad(25), 0.9, 0);
  sonne.position.set(900, 3900, 1500);
  sonne.target.position.set(560, -100, 0);
  sonne.castShadow = stufe >= 2;
  const s = sonne.shadow;
  s.mapSize.set(stufe >= 3 ? 2048 : 1024, stufe >= 3 ? 2048 : 1024);
  s.camera.near = 1200;
  s.camera.far = 7000;
  s.bias = -0.00025;
  s.normalBias = 1.2;
  s.radius = 3;
  licht.add(sonne, sonne.target);
  const kante = new THREE.SpotLight(0xa8dcd8, 3.2, 0, THREE.MathUtils.degToRad(19), 0.75, 0);
  kante.position.set(-1500, 3300, -2600);
  kante.target.position.set(620, 380, 0);
  licht.add(kante, kante.target);
  const fuell = new THREE.HemisphereLight(0xcfe3ff, 0x1b1712, 0.1);
  licht.add(fuell);

  return { env, licht, sonne, kante, fuell };
}
