import * as THREE from "../vendor/three.module.min.js";

const BODEN_Y = -274;

function rauschen(ctx, b, h, staerke, groesse, farbe) {
  const bild = ctx.getImageData(0, 0, b, h);
  const d = bild.data;
  const raster = (n) => {
    const w = Math.ceil(b / n) + 2;
    const g = new Float32Array(w * (Math.ceil(h / n) + 2));
    for (let i = 0; i < g.length; i++) g[i] = Math.random();
    return (x, y) => {
      const gx = x / n, gy = y / n;
      const ix = Math.floor(gx), iy = Math.floor(gy);
      const fx = gx - ix, fy = gy - iy;
      const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
      const a = g[iy * w + ix], bb = g[iy * w + ix + 1], c = g[(iy + 1) * w + ix], e = g[(iy + 1) * w + ix + 1];
      return a + (bb - a) * sx + (c - a) * sy + (a - bb - c + e) * sx * sy;
    };
  };
  const ebenen = groesse.map((n) => raster(n));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < b; x++) {
      let v = 0;
      let gw = 0;
      ebenen.forEach((f, i) => {
        const w = 1 / (i + 1);
        v += f(x, y) * w;
        gw += w;
      });
      v = (v / gw - 0.5) * staerke;
      const o = (y * b + x) * 4;
      d[o] = Math.max(0, Math.min(255, d[o] + v * farbe[0]));
      d[o + 1] = Math.max(0, Math.min(255, d[o + 1] + v * farbe[1]));
      d[o + 2] = Math.max(0, Math.min(255, d[o + 2] + v * farbe[2]));
    }
  }
  ctx.putImageData(bild, 0, 0);
}

function betonTextur(gross) {
  const n = gross ? 1024 : 512;
  const c = document.createElement("canvas");
  c.width = c.height = n;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#3b3d3d";
  ctx.fillRect(0, 0, n, n);
  rauschen(ctx, n, n, 46, [n / 4, n / 16, n / 64, 3], [1, 1, 0.98]);
  for (let i = 0; i < 14; i++) {
    const x = Math.random() * n, y = Math.random() * n, r = n * (0.02 + Math.random() * 0.07);
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, "rgba(10,10,8,0.22)");
    g.addColorStop(1, "rgba(10,10,8,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  ctx.strokeStyle = "rgba(15,15,14,0.55)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, n * 0.5);
  ctx.lineTo(n, n * 0.5);
  ctx.moveTo(n * 0.5, 0);
  ctx.lineTo(n * 0.5, n);
  ctx.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}

function lochwandTextur() {
  const n = 512;
  const c = document.createElement("canvas");
  c.width = c.height = n;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#4a3e30";
  ctx.fillRect(0, 0, n, n);
  rauschen(ctx, n, n, 30, [n / 8, n / 32, 2], [1, 0.9, 0.75]);
  ctx.fillStyle = "#120f0c";
  const raster = n / 16;
  for (let y = raster / 2; y < n; y += raster) {
    for (let x = raster / 2; x < n; x += raster) {
      ctx.beginPath();
      ctx.arc(x, y, raster * 0.12, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

function werkzeug(form, tiefe, material) {
  const g = new THREE.ExtrudeGeometry(form, { depth: tiefe, bevelEnabled: true, bevelThickness: 1.5, bevelSize: 1.5, bevelSegments: 2, curveSegments: 16 });
  return new THREE.Mesh(g, material);
}

function maulschluessel(laenge) {
  const s = new THREE.Shape();
  const b = laenge * 0.07;
  s.moveTo(-b / 2, 0);
  s.lineTo(b / 2, 0);
  s.lineTo(b / 2, laenge);
  s.absarc(0, laenge + b * 0.9, b * 1.2, -Math.PI / 2 + 0.6, Math.PI * 1.5 - 0.6, false);
  s.lineTo(-b / 2, laenge);
  s.lineTo(-b / 2, 0);
  const maul = new THREE.Path();
  maul.moveTo(-b * 0.35, laenge + b * 0.6);
  maul.lineTo(b * 0.35, laenge + b * 0.6);
  maul.lineTo(b * 0.35, laenge + b * 2.4);
  maul.lineTo(-b * 0.35, laenge + b * 2.4);
  s.holes.push(maul);
  return s;
}

function zange(laenge) {
  const s = new THREE.Shape();
  s.moveTo(-6, 0);
  s.quadraticCurveTo(-14, laenge * 0.5, -5, laenge * 0.72);
  s.lineTo(-3, laenge);
  s.lineTo(3, laenge);
  s.lineTo(5, laenge * 0.72);
  s.quadraticCurveTo(14, laenge * 0.5, 6, 0);
  s.lineTo(-6, 0);
  return s;
}

export function werkstattBauen({ stufe }) {
  const gruppe = new THREE.Group();
  gruppe.name = "werkstatt";

  const beton = betonTextur(stufe >= 3);
  beton.repeat.set(3, 3);
  const boden = new THREE.Mesh(
    new THREE.PlaneGeometry(9000, 9000),
    new THREE.MeshStandardMaterial({ map: beton, color: 0x4b4f4e, roughness: 0.4, metalness: 0.0, envMapIntensity: 0.5 }),
  );
  boden.rotation.x = -Math.PI / 2;
  boden.position.set(600, BODEN_Y, -400);
  boden.receiveShadow = true;
  gruppe.add(boden);

  const markierung = new THREE.MeshStandardMaterial({ color: 0xc9971c, roughness: 0.66, metalness: 0, envMapIntensity: 0.3 });
  const linie = (b, t, x, z) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(b, t), markierung);
    m.rotation.x = -Math.PI / 2;
    m.position.set(x, BODEN_Y + 0.6, z);
    m.receiveShadow = true;
    gruppe.add(m);
  };
  linie(3200, 60, 600, 1150);
  linie(60, 2000, -1000, 150);
  linie(60, 2000, 2200, 150);

  const wand = new THREE.Mesh(
    new THREE.PlaneGeometry(9000, 4200),
    new THREE.MeshStandardMaterial({ color: 0x1d2224, roughness: 0.9, metalness: 0 }),
  );
  wand.position.set(600, BODEN_Y + 2100, -2300);
  wand.receiveShadow = true;
  gruppe.add(wand);
  const loch = lochwandTextur();
  loch.repeat.set(5, 2.4);
  const lochwand = new THREE.Mesh(new THREE.PlaneGeometry(3400, 1500), new THREE.MeshStandardMaterial({ map: loch, roughness: 0.8, metalness: 0 }));
  lochwand.position.set(500, BODEN_Y + 1750, -2290);
  gruppe.add(lochwand);

  const stahl = new THREE.MeshStandardMaterial({ color: 0x9aa0a4, roughness: 0.35, metalness: 1 });
  const griff = new THREE.MeshStandardMaterial({ color: 0xb8321e, roughness: 0.55, metalness: 0 });
  for (let i = 0; i < 9; i++) {
    const w = werkzeug(maulschluessel(180 + i * 22), 6, stahl);
    w.position.set(-650 + i * 70, BODEN_Y + 1350, -2282);
    gruppe.add(w);
  }
  for (let i = 0; i < 4; i++) {
    const z = werkzeug(zange(200 + i * 10), 10, i % 2 ? stahl : griff);
    z.position.set(220 + i * 95, BODEN_Y + 1420, -2280);
    gruppe.add(z);
  }
  for (let i = 0; i < 8; i++) {
    const h = new THREE.Mesh(new THREE.CylinderGeometry(14, 16, 110, 16), i % 3 ? griff : new THREE.MeshStandardMaterial({ color: 0xe8b62c, roughness: 0.5 }));
    h.position.set(700 + i * 52, BODEN_Y + 1830, -2250);
    const k = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 140, 8), stahl);
    k.position.set(700 + i * 52, BODEN_Y + 1705, -2250);
    gruppe.add(h, k);
  }
  const leiste = new THREE.Mesh(new THREE.BoxGeometry(520, 24, 60), new THREE.MeshStandardMaterial({ color: 0x2b2f31, roughness: 0.6 }));
  leiste.position.set(880, BODEN_Y + 1760, -2255);
  gruppe.add(leiste);

  const gummi = new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.85 });
  for (let i = 0; i < 4; i++) {
    const r = new THREE.Mesh(new THREE.TorusGeometry(330, 26, 12, 64), gummi);
    r.position.set(-1500 + i * 65, BODEN_Y + 1950, -2150 + i * 20);
    r.rotation.y = 0.15;
    gruppe.add(r);
  }
  const holz = new THREE.MeshStandardMaterial({ color: 0x6b4f33, roughness: 0.7 });
  const bank = new THREE.Mesh(new THREE.BoxGeometry(2200, 60, 700), holz);
  bank.position.set(2600, BODEN_Y + 900, -1700);
  bank.castShadow = true;
  bank.receiveShadow = true;
  gruppe.add(bank);
  const bankUnten = new THREE.Mesh(new THREE.BoxGeometry(2100, 840, 640), new THREE.MeshStandardMaterial({ color: 0x23292b, roughness: 0.8 }));
  bankUnten.position.set(2600, BODEN_Y + 440, -1700);
  gruppe.add(bankUnten);

  const roehre = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xf4f8ff).multiplyScalar(3.2) });
  for (let i = 0; i < 3; i++) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(18, 18, 1500, 12), roehre);
    r.rotation.z = Math.PI / 2;
    r.position.set(600, BODEN_Y + 3400, -1400 + i * 1400);
    gruppe.add(r);
  }

  gruppe.traverse((o) => {
    if (o.isMesh && o !== boden) o.receiveShadow = true;
  });
  return { gruppe, bodenY: BODEN_Y };
}
