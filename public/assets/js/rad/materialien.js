import * as THREE from "../vendor/three.module.min.js";

export const SCAN = {
  uScanPos: { value: -1e5 },
  uScanStaerke: { value: 0 },
  uScanFarbe: { value: new THREE.Color(0x6fe6d6) },
};

const SCAN_VERTEX_KOPF = "varying vec3 vWeltPos;\n";
const SCAN_VERTEX = `
  {
    vec4 wp = vec4(transformed, 1.0);
    #ifdef USE_INSTANCING
      wp = instanceMatrix * wp;
    #endif
    vWeltPos = (modelMatrix * wp).xyz;
  }
`;
const SCAN_FRAGMENT_KOPF = `
  varying vec3 vWeltPos;
  uniform float uScanPos;
  uniform float uScanStaerke;
  uniform vec3 uScanFarbe;
  uniform float uHervor;
  uniform vec3 uHervorFarbe;
`;
const SCAN_FRAGMENT = `
  {
    float d = vWeltPos.x - uScanPos;
    float band = exp(-d * d / 1800.0);
    float vorlauf = exp(-max(d, 0.0) / 60.0) * step(0.0, d) * 0.25;
    vec3 g = abs(fract(vWeltPos / 36.0) - 0.5);
    float raster = smoothstep(0.47, 0.5, max(max(g.x, g.y), g.z));
    float erfasst = smoothstep(0.0, 260.0, -d) * (1.0 - smoothstep(900.0, 1900.0, -d));
    gl_FragColor.rgb += uScanFarbe * uScanStaerke * (band * 3.2 + vorlauf + raster * erfasst * 0.35);
    vec3 nv = normalize(vNormal);
    float rand = pow(1.0 - abs(nv.z), 2.5);
    gl_FragColor.rgb += uHervorFarbe * uHervor * (0.12 + rand * 0.9);
  }
`;

function effekteEinbauen(m, zusatz = {}) {
  m.userData.hervor = { value: 0 };
  m.userData.uniforms = zusatz.uniforms || {};
  const alt = m.onBeforeCompile;
  m.onBeforeCompile = (shader, renderer) => {
    if (alt) alt(shader, renderer);
    Object.assign(shader.uniforms, SCAN, m.userData.uniforms, {
      uHervor: m.userData.hervor,
      uHervorFarbe: { value: new THREE.Color(0xf2c94c) },
    });
    shader.vertexShader = SCAN_VERTEX_KOPF + (zusatz.vertexKopf || "") + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\n" + (zusatz.vertex || ""));
    shader.vertexShader = shader.vertexShader.replace("#include <fog_vertex>", "#include <fog_vertex>\n" + SCAN_VERTEX);
    shader.fragmentShader = SCAN_FRAGMENT_KOPF + (zusatz.fragmentKopf || "") + shader.fragmentShader;
    if (zusatz.emissiv) {
      shader.fragmentShader = shader.fragmentShader.replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\n" + zusatz.emissiv);
    }
    if (zusatz.farbe) {
      shader.fragmentShader = shader.fragmentShader.replace("#include <color_fragment>", "#include <color_fragment>\n" + zusatz.farbe);
    }
    shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", "#include <opaque_fragment>\n" + SCAN_FRAGMENT);
  };
  if (zusatz.defines) m.defines = { ...(m.defines || {}), ...zusatz.defines };
  m.customProgramCacheKey = () => m.name + (zusatz.schluessel || "");
  return m;
}

function leinwand(b, h) {
  const c = document.createElement("canvas");
  c.width = b;
  c.height = h;
  return [c, c.getContext("2d")];
}

function flakeNormalen(n) {
  const [c, ctx] = leinwand(n, n);
  const bild = ctx.createImageData(n, n);
  for (let i = 0; i < n * n; i++) {
    const x = (Math.random() - 0.5) * 0.9;
    const y = (Math.random() - 0.5) * 0.9;
    bild.data[i * 4] = 128 + x * 127;
    bild.data[i * 4 + 1] = 128 + y * 127;
    bild.data[i * 4 + 2] = 255;
    bild.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(bild, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(26, 3);
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

function flankenTextur(stufe) {
  const b = 64;
  const h = stufe >= 3 ? 4096 : 2048;
  const [c, ctx] = leinwand(b, h);
  ctx.fillStyle = "#5a3d24";
  ctx.fillRect(0, 0, b, h);
  for (let i = 0; i < 400; i++) {
    ctx.fillStyle = `rgba(30,18,8,${Math.random() * 0.12})`;
    ctx.fillRect(Math.random() * b, Math.random() * h, 1, 20 + Math.random() * 80);
  }
  ctx.save();
  ctx.translate(b * 0.55, 0);
  ctx.rotate(Math.PI / 2);
  ctx.fillStyle = "rgba(225,205,175,0.55)";
  ctx.font = `600 ${Math.round(h / 150)}px Barlow, sans-serif`;
  const texte = ["50-622  ·  28 × 2.00", "3,0 – 4,5 bar  ·  45 – 65 psi", "E-BIKE 25 km/h", "50-622  ·  28 × 2.00", "PANNENSCHUTZ"];
  texte.forEach((t, i) => ctx.fillText(t, (h / texte.length) * i + 40, 0));
  ctx.restore();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}

function aufkleberTextur() {
  const [c, ctx] = leinwand(256, 180);
  ctx.fillStyle = "#f2f3ef";
  ctx.fillRect(0, 0, 256, 180);
  ctx.fillStyle = "#0e4a4c";
  ctx.fillRect(0, 0, 256, 44);
  ctx.fillStyle = "#f2f3ef";
  ctx.font = "700 26px 'Barlow Semi Condensed', Barlow, sans-serif";
  ctx.fillText("Radhaus Fuhse", 14, 31);
  ctx.fillStyle = "#1b2326";
  ctx.font = "600 21px Barlow, sans-serif";
  ctx.fillText("Inspektion", 14, 80);
  ctx.font = "500 36px 'Barlow Semi Condensed', Barlow, sans-serif";
  ctx.fillText("10 / 2026", 14, 124);
  ctx.font = "500 15px Barlow, sans-serif";
  ctx.fillText("Nächste: 10 / 2027", 14, 160);
  ctx.strokeStyle = "#1b2326";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(208, 118, 30, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(193, 118);
  ctx.lineTo(205, 131);
  ctx.lineTo(226, 104);
  ctx.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function displayBauen() {
  const [c, ctx] = leinwand(320, 240);
  const textur = new THREE.CanvasTexture(c);
  textur.colorSpace = THREE.SRGBColorSpace;
  let zuletzt = "";
  function zeichnen(z) {
    const schluessel = JSON.stringify(z);
    if (schluessel === zuletzt) return;
    zuletzt = schluessel;
    ctx.fillStyle = "#06090a";
    ctx.fillRect(0, 0, 320, 240);
    ctx.fillStyle = "#0e4a4c";
    ctx.fillRect(0, 0, 320, 36);
    ctx.fillStyle = "#d9f4ef";
    ctx.font = "600 22px 'Barlow Semi Condensed', Barlow, sans-serif";
    ctx.fillText(z.kopf || "", 14, 26);
    const p = Math.max(0, Math.min(1, z.akku ?? 0.86));
    ctx.strokeStyle = "#d9f4ef";
    ctx.lineWidth = 2;
    ctx.strokeRect(232, 9, 64, 18);
    ctx.fillRect(296, 14, 5, 8);
    ctx.fillStyle = p > 0.2 ? "#4fd98a" : "#f2c94c";
    ctx.fillRect(235, 12, 58 * p, 12);
    ctx.fillStyle = "#ffffff";
    if (z.gross) {
      ctx.font = "600 92px 'Barlow Semi Condensed', Barlow, sans-serif";
      ctx.fillText(z.gross, 14, 140);
      ctx.font = "500 24px Barlow, sans-serif";
      ctx.fillStyle = "#9ab8b4";
      ctx.fillText(z.einheit || "", 14 + ctx.measureText(z.gross).width * 0 + 190, 140);
    }
    ctx.font = "500 22px Barlow, sans-serif";
    (z.zeilen || []).forEach((zeile, i) => {
      ctx.fillStyle = zeile.ok === false ? "#f2c94c" : zeile.ok ? "#4fd98a" : "#d9f4ef";
      ctx.fillText(zeile.text, 14, (z.gross ? 182 : 76) + i * 32);
    });
    textur.needsUpdate = true;
  }
  zeichnen({ kopf: "Bereit", gross: "0", einheit: "km/h", zeilen: [{ text: "Unterstützung: Tour" }] });
  return { textur, zeichnen };
}

export function materialienBauen({ stufe, renderer }) {
  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const flakes = flakeNormalen(stufe >= 3 ? 256 : 128);
  const flanke = flankenTextur(stufe);
  flanke.anisotropy = aniso;
  const display = displayBauen();

  const hitze = { uHitze: { value: 0 }, uAnlauf: { value: 0 }, uZeit: { value: 0 }, uScheibeR: { value: 101.5 } };
  const scheibenRadius = (seite) => ({ value: seite === "_h" ? 90.0 : 101.5 });
  const rad = {
    uSchlag: { value: 0 },
    uSpannung: { value: 0 },
    uSpannungZeigen: { value: 0 },
  };

  const phys = (p) => new THREE.MeshPhysicalMaterial(p);
  const std = (p) => new THREE.MeshStandardMaterial(p);

  const RADVERFORMUNG_KOPF = `
    uniform float uSchlag;
    varying float vRadWinkel;
    varying float vRadAnteil;
  `;
  const RADVERFORMUNG = `
    {
      float r = length(position.xy);
      float w = atan(position.y, position.x);
      vRadWinkel = w;
      vRadAnteil = smoothstep(30.0, 300.0, r);
      float beule = exp(-pow(mod(w - 0.6 + 3.14159, 6.28318) - 3.14159, 2.0) * 3.2) - 0.55 * exp(-pow(mod(w + 2.2 + 3.14159, 6.28318) - 3.14159, 2.0) * 5.0);
      transformed.z += uSchlag * beule * vRadAnteil;
    }
  `;
  const SPANNUNG_KOPF = `
    uniform float uSpannung;
    uniform float uSpannungZeigen;
    varying float vRadWinkel;
    varying float vRadAnteil;
  `;
  const SPANNUNG = `
    {
      float s = sin(vRadWinkel * 3.0 + 0.7) * 0.6 + sin(vRadWinkel * 7.0 - 1.3) * 0.4;
      s *= uSpannung;
      vec3 niedrig = vec3(0.02, 0.22, 1.0);
      vec3 hoch = vec3(1.0, 0.12, 0.02);
      vec3 gut = vec3(0.05, 0.85, 0.35);
      vec3 farbe = s > 0.0 ? mix(gut, hoch, smoothstep(0.0, 0.7, s)) : mix(gut, niedrig, smoothstep(0.0, 0.7, -s));
      // Eigenfarbe dämpfen, sonst überstrahlt das Metall die Anzeige
      diffuseColor.rgb *= 1.0 - 0.85 * uSpannungZeigen;
      totalEmissiveRadiance += farbe * uSpannungZeigen * 0.95 * (0.45 + 0.55 * vRadAnteil);
    }
  `;

  const def = {
    Rahmenlack: () => phys({ color: 0x0e5052, metalness: 0.55, roughness: 0.36, clearcoat: 1, clearcoatRoughness: 0.05, normalMap: flakes, normalScale: new THREE.Vector2(0.22, 0.22), envMapIntensity: 1.15, iridescence: 0.08, iridescenceIOR: 1.6 }),
    Rahmen_matt: () => std({ color: 0x111314, roughness: 0.7, metalness: 0.2 }),
    Alu_schwarz: () => phys({ color: 0x131416, metalness: 0.65, roughness: 0.34, clearcoat: 0.25, clearcoatRoughness: 0.3 }),
    Alu_blank: () => std({ color: 0xcfd2d4, metalness: 1, roughness: 0.18 }),
    Stahl: () => std({ color: 0xb4b7ba, metalness: 1, roughness: 0.24, envMapIntensity: 1.4 }),
    Stahl_dunkel: () => std({ color: 0x4d5054, metalness: 1, roughness: 0.32 }),
    Kette: () => phys({ color: 0x9a9da1, metalness: 1, roughness: 0.27, clearcoat: 0.5, clearcoatRoughness: 0.2 }),
    Kassette: () => std({ color: 0xdadcdf, metalness: 1, roughness: 0.16, envMapIntensity: 1.6 }),
    Kettenblatt: () => phys({ color: 0x1b1c1f, metalness: 0.8, roughness: 0.3, clearcoat: 0.3 }),
    Gummi: () => std({ color: 0x151515, roughness: 0.86, metalness: 0 }),
    Gummi_Flanke: () => std({ color: 0xffffff, map: flanke, roughness: 0.8, metalness: 0 }),
    Griff: () => std({ color: 0x121212, roughness: 0.92, metalness: 0 }),
    Kunststoff: () => std({ color: 0x141517, roughness: 0.5, metalness: 0 }),
    Motor: () => phys({ color: 0x1d2023, roughness: 0.42, metalness: 0.45, clearcoat: 0.3, clearcoatRoughness: 0.35 }),
    Akku: () => phys({ color: 0x0c0d0f, roughness: 0.3, metalness: 0.2, clearcoat: 0.6, clearcoatRoughness: 0.12 }),
    Bremsscheibe: () => std({ color: 0xc8cacd, metalness: 1, roughness: 0.2, envMapIntensity: 1.5 }),
    Bremssattel: () => phys({ color: 0xc2602a, metalness: 1, roughness: 0.3, clearcoat: 0.4, clearcoatRoughness: 0.15 }),
    Belag: () => std({ color: 0x3a342e, roughness: 0.92, metalness: 0.1 }),
    Standrohr: () => phys({ color: 0xc9a25a, metalness: 1, roughness: 0.16, clearcoat: 0.7, clearcoatRoughness: 0.08 }),
    Tauchrohr: () => phys({ color: 0x121315, metalness: 0.35, roughness: 0.42, clearcoat: 0.5, clearcoatRoughness: 0.2 }),
    Felge: () => phys({ color: 0x141517, metalness: 0.6, roughness: 0.32, clearcoat: 0.3 }),
    Speiche: () => std({ color: 0xb9bcbf, metalness: 1, roughness: 0.26 }),
    Nippel: () => std({ color: 0xd8dadc, metalness: 1, roughness: 0.2 }),
    Nabe: () => phys({ color: 0x151618, metalness: 0.7, roughness: 0.3, clearcoat: 0.4 }),
    Sattel: () => phys({ color: 0x1f1c19, roughness: 0.62, metalness: 0, sheen: 0.6, sheenRoughness: 0.5, sheenColor: new THREE.Color(0x4b4038) }),
    Display: () => phys({ color: 0x07080a, roughness: 0.25, metalness: 0.2, clearcoat: 1 }),
    Bildschirm: () => std({ color: 0x000000, emissive: 0xffffff, emissiveMap: display.textur, emissiveIntensity: 1.3, roughness: 0.15, metalness: 0 }),
    Licht: () => std({ color: 0xffffff, emissive: 0xfff6e6, emissiveIntensity: 5, roughness: 0.1 }),
    Ruecklicht: () => std({ color: 0x400000, emissive: 0xff2010, emissiveIntensity: 3.2, roughness: 0.2 }),
    Leitung: () => std({ color: 0x0b0c0d, roughness: 0.45, metalness: 0 }),
    LED: () => std({ color: 0x0a2a14, emissive: 0x40ff8c, emissiveIntensity: 2.6 }),
    Staender: () => phys({ color: 0xa3281b, roughness: 0.48, metalness: 0.1, clearcoat: 0.3, clearcoatRoughness: 0.4 }),
    Staender_Stahl: () => std({ color: 0xa4a9ad, metalness: 1, roughness: 0.28 }),
    Aufkleber: () => std({ map: aufkleberTextur(), roughness: 0.45, metalness: 0 }),
  };

  const zusatz = {
    Bremsscheibe: {
      schluessel: "hitze",
      uniforms: hitze,
      vertexKopf: "uniform float uScheibeR;\nvarying vec2 vScheibe;\n",
      vertex: "vScheibe = vec2(length(position.xy) / uScheibeR, atan(position.y, position.x) / 6.28318 + 0.5);\n",
      fragmentKopf: "uniform float uHitze; uniform float uAnlauf; uniform float uZeit;\nvarying vec2 vScheibe;\n",
      farbe: `
        {
          float ring = smoothstep(0.82, 0.86, vScheibe.x) * (1.0 - smoothstep(0.995, 1.0, vScheibe.x));
          vec3 anlauf = mix(vec3(0.72, 0.55, 0.35), vec3(0.32, 0.36, 0.62), smoothstep(0.88, 0.97, vScheibe.x));
          diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * anlauf, uAnlauf * ring * 0.7);
        }
      `,
      emissiv: `
        {
          float ring = smoothstep(0.82, 0.86, vScheibe.x) * (1.0 - smoothstep(0.995, 1.0, vScheibe.x));
          float flecken = 0.75 + 0.25 * sin(vScheibe.y * 6.28318 * 9.0 + uZeit * 0.7) * sin(vScheibe.y * 6.28318 * 4.0 - 1.3);
          float h = clamp(uHitze * flecken * ring * (0.7 + 0.3 * smoothstep(0.86, 0.94, vScheibe.x)), 0.0, 1.0);
          vec3 glut = mix(vec3(0.35, 0.02, 0.0), vec3(1.0, 0.25, 0.02), smoothstep(0.1, 0.55, h));
          glut = mix(glut, vec3(1.0, 0.75, 0.35), smoothstep(0.6, 1.0, h));
          totalEmissiveRadiance += glut * h * h * 9.0;
        }
      `,
    },
    Felge: { schluessel: "rad", uniforms: rad, vertexKopf: RADVERFORMUNG_KOPF, vertex: RADVERFORMUNG },
    Gummi: { schluessel: "rad", uniforms: rad, vertexKopf: RADVERFORMUNG_KOPF, vertex: RADVERFORMUNG },
    Gummi_Flanke: { schluessel: "rad", uniforms: rad, vertexKopf: RADVERFORMUNG_KOPF, vertex: RADVERFORMUNG },
    Nippel: { schluessel: "rad", uniforms: rad, vertexKopf: RADVERFORMUNG_KOPF, vertex: RADVERFORMUNG },
    Speiche: { schluessel: "speiche", uniforms: rad, vertexKopf: RADVERFORMUNG_KOPF, vertex: RADVERFORMUNG, fragmentKopf: SPANNUNG_KOPF, emissiv: SPANNUNG },
  };

  const cache = new Map();
  const radSaetze = new Map();
  const hitzeSaetze = new Map();
  function holen(name, { rad: radSeite = "", teil = "" } = {}) {
    const schluessel = name + "|" + radSeite + "|" + teil;
    if (cache.has(schluessel)) return cache.get(schluessel);
    const bau = def[name] || (() => std({ color: 0x888888, roughness: 0.5 }));
    const m = bau();
    m.name = name;
    let z = zusatz[name] || {};
    if (z.uniforms === rad) {
      if (!radSaetze.has(radSeite)) radSaetze.set(radSeite, { uSchlag: { value: 0 }, uSpannung: { value: 0 }, uSpannungZeigen: { value: 0 } });
      z = { ...z, uniforms: radSaetze.get(radSeite) };
    }
    if (z.uniforms === hitze) {
      if (!hitzeSaetze.has(radSeite)) hitzeSaetze.set(radSeite, { uHitze: { value: 0 }, uAnlauf: { value: 0 }, uZeit: hitze.uZeit, uScheibeR: scheibenRadius(radSeite) });
      z = { ...z, uniforms: hitzeSaetze.get(radSeite) };
    }
    effekteEinbauen(m, z);
    if (m.map) m.map.anisotropy = aniso;
    m.userData.teil = teil;
    cache.set(schluessel, m);
    return m;
  }

  const radUniforms = (seite) => {
    if (!radSaetze.has(seite)) radSaetze.set(seite, { uSchlag: { value: 0 }, uSpannung: { value: 0 }, uSpannungZeigen: { value: 0 } });
    return radSaetze.get(seite);
  };
  const hitzeUniforms = (seite) => {
    if (!hitzeSaetze.has(seite)) hitzeSaetze.set(seite, { uHitze: { value: 0 }, uAnlauf: { value: 0 }, uZeit: hitze.uZeit, uScheibeR: scheibenRadius(seite) });
    return hitzeSaetze.get(seite);
  };
  const vonTeil = (teil) => [...cache.values()].filter((m) => m.userData.teil === teil);

  return { holen, display, hitze, radUniforms, hitzeUniforms, vonTeil };
}
