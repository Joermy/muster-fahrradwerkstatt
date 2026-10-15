import * as THREE from "../vendor/three.module.min.js";
import { EffectComposer, RenderPass, UnrealBloomPass, OutputPass, ShaderPass, BokehPass, GTAOPass } from "../vendor/three-zusatz.min.js";

const ABSCHLUSS = {
  uniforms: {
    tDiffuse: { value: null },
    zeit: { value: 0 },
    seiten: { value: 1 },
    korn: { value: 0.028 },
    vignette: { value: 0.5 },
    versatz: { value: 0.0012 },
  },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float zeit; uniform float seiten; uniform float korn; uniform float vignette; uniform float versatz;
    varying vec2 vUv;
    float hash(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
    void main(){
      vec2 m = vUv - 0.5;
      float r2 = dot(m * vec2(seiten, 1.0), m * vec2(seiten, 1.0));
      vec2 d = m * versatz * (0.4 + r2 * 3.0);
      vec3 c = vec3(texture2D(tDiffuse, vUv + d).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - d).b);
      c *= 1.0 - vignette * smoothstep(0.18, 0.95, r2 * 1.25);
      float n = hash(vUv * 1024.0 + fract(zeit * 7.0) * 113.0) - 0.5;
      c += n * korn * (0.3 + 0.7 * (1.0 - dot(c, vec3(0.333))));
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export function stufeErmitteln() {
  const url = new URLSearchParams(location.search);
  if (url.has("stufe")) return Math.max(1, Math.min(3, Number(url.get("stufe")) || 2));
  const fein = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const kerne = navigator.hardwareConcurrency || 4;
  const speicher = navigator.deviceMemory || 4;
  const klein = Math.min(screen.width, screen.height) < 600;
  if (!fein || klein) return speicher <= 2 || kerne <= 4 ? 1 : 2;
  return kerne >= 6 ? 3 : 2;
}

export function buehneBauen(canvas, stufe) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance", stencil: false });
  renderer.setClearColor(0x0d1112, 1);
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = stufe >= 2;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const szene = new THREE.Scene();
  const kamera = new THREE.PerspectiveCamera(30, 1, 20, 30000);

  const ziel = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: stufe >= 2 ? 4 : 0 });
  const composer = new EffectComposer(renderer, ziel);
  composer.addPass(new RenderPass(szene, kamera));

  let ao = null;
  if (stufe >= 3) {
    ao = new GTAOPass(szene, kamera, 4, 4);
    ao.output = GTAOPass.OUTPUT.Default;
    ao.blendIntensity = 0.85;
    ao.updateGtaoMaterial({ radius: 60, distanceExponent: 1.6, thickness: 30, scale: 1, samples: 12 });
    ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 12 });
    composer.addPass(ao);
  }
  const bloom = new UnrealBloomPass(new THREE.Vector2(4, 4), 0.32, 0.55, 1.15);
  bloom.enabled = stufe >= 2;
  composer.addPass(bloom);
  const schaerfe = new BokehPass(szene, kamera, { focus: 2500, aperture: 0.0, maxblur: 0.006 });
  schaerfe.enabled = false;
  schaerfe.userData = { erlaubt: stufe >= 3 };
  composer.addPass(schaerfe);
  composer.addPass(new OutputPass());
  const abschluss = new ShaderPass(ABSCHLUSS);
  composer.addPass(abschluss);

  let breite = 0;
  let hoehe = 0;
  let dichteGrenze = stufe >= 3 ? 1.75 : stufe === 2 ? 1.5 : 1;

  const sonde = document.createElement("div");
  sonde.style.cssText = "position:fixed;left:0;top:0;width:1px;height:100lvh;visibility:hidden;pointer-events:none";
  document.body.appendChild(sonde);

  function groesse(erzwingen = false) {
    const b = Math.max(1, Math.round(canvas.clientWidth || window.innerWidth));
    const h = Math.max(1, Math.round(sonde.offsetHeight || window.innerHeight));
    if (!erzwingen && b === breite && Math.abs(h - hoehe) < 2) return false;
    breite = b;
    hoehe = h;
    const dichte = Math.min(window.devicePixelRatio || 1, dichteGrenze);
    renderer.setPixelRatio(dichte);
    renderer.setSize(b, h, false);
    composer.setPixelRatio(dichte);
    composer.setSize(b, h);
    bloom.resolution.set(b * dichte * 0.5, h * dichte * 0.5);
    if (ao) ao.setSize(b * dichte, h * dichte);
    kamera.aspect = b / h;
    kamera.updateProjectionMatrix();
    abschluss.uniforms.seiten.value = b / h;
    return true;
  }

  return {
    renderer, szene, kamera, composer, bloom, schaerfe, ao, abschluss, groesse,
    get breite() { return breite; },
    get hoehe() { return hoehe; },
    senken() {
      if (ao && ao.enabled) { ao.enabled = false; return true; }
      if (schaerfe.userData.erlaubt) { schaerfe.userData.erlaubt = false; schaerfe.enabled = false; return true; }
      if (dichteGrenze > 1) { dichteGrenze = Math.max(1, dichteGrenze - 0.25); groesse(true); return true; }
      if (bloom.enabled) { bloom.enabled = false; return true; }
      if (renderer.shadowMap.enabled) { renderer.shadowMap.enabled = false; szene.traverse((o) => { if (o.material) o.material.needsUpdate = true; }); return true; }
      return false;
    },
    zeichnen(sek) {
      abschluss.uniforms.zeit.value = sek;
      composer.render();
    },
  };
}
