// Zeitleiste der Werkstatt: dieselben Formeln wie scripts/szene/regie.py, damit Anzeige und Bild zusammenpassen.
// p läuft von 0 bis 8, ein Kapitel je Bildschirmhöhe Scrollweg.

export const KAPITEL = 8;
export const NAMEN = ["ankunft", "diagnose", "zerlegen", "antrieb", "bremse", "laufrad", "akku", "uebergabe"];
const KASSETTE = [10, 12, 14, 16, 18, 21, 24, 28, 32, 38, 44, 52];
const KETTENBLATT = 34;
const T_RAD = 6.0;

const klemm = (x, a, b) => Math.max(a, Math.min(b, x));
export const glatt = (a, b, x) => {
  const t = klemm((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
export const fenster = (a, b, c, d, x) => glatt(a, b, x) * (1 - glatt(c, d, x));
const lerp = (a, b, t) => a + (b - a) * t;

export function gangBei(p) {
  const k = Math.floor(p);
  const f = p - k;
  if (p < 3) return 0;
  if (k === 3) {
    const g = klemm((f - 0.05) / 0.55, 0, 1) * 11;
    const stufe = Math.floor(g);
    return Math.min(11, stufe + glatt(0.65, 1, g - stufe));
  }
  return lerp(11, 6, glatt(3.97, 4.12, p));
}

function omegaZiel(p) {
  const k = Math.floor(p);
  const f = p - k;
  if (k === 4) return lerp(26, 0, glatt(0.18, 0.5, f));
  return k > 4 ? 0 : 1.2;
}

// Drehzahl des Vorderrads: geglättet wie in Blender, einmal vorab über p integriert
const SCHRITTE = 8192;
const DP = KAPITEL / SCHRITTE;
const OMEGA = new Float32Array(SCHRITTE + 1);
{
  let om = 1.2;
  OMEGA[0] = om;
  for (let i = 0; i < SCHRITTE; i++) {
    const p = i * DP;
    const k = Math.floor(p);
    const rate = k === 4 && p - k < 0.18 ? 2.5 : 4.0;
    om += (omegaZiel(p) - om) * Math.min(1, rate * T_RAD * DP);
    OMEGA[i + 1] = om;
  }
}

function omegaBei(p) {
  const x = klemm(p / DP, 0, SCHRITTE);
  const i = Math.floor(x);
  const j = Math.min(SCHRITTE, i + 1);
  return lerp(OMEGA[i], OMEGA[j], x - i);
}

const hitzeBei = (p) => {
  const k = Math.floor(p);
  const f = p - k;
  return k === 4 ? glatt(0.2, 0.52, f) * (1 - 0.75 * glatt(0.6, 1, f)) : 0;
};

export function werteBei(p) {
  const k = Math.min(Math.floor(p), KAPITEL - 1);
  const f = p - k;
  const g = gangBei(p);
  const gang = Math.round(g);
  const hitze = hitzeBei(p);
  const omega = omegaBei(p);
  const schlag = k === 5 ? 1 - glatt(0.12, 0.66, f) : k < 5 ? 1 : 0;
  return {
    kapitel: k,
    name: NAMEN[k],
    anteil: f,
    scan: fenster(0.92, 1.05, 1.82, 1.97, p),
    scanX: lerp(-520, 1820, glatt(1.05, 1.78, p)),
    zerlegt: glatt(2.02, 2.55, p) * (1 - glatt(2.66, 2.98, p)),
    gang: gang + 1,
    ritzel: KASSETTE[gang],
    kettenblatt: KETTENBLATT,
    uebersetzung: KETTENBLATT / KASSETTE[gang],
    temperatur: Math.round(24 + hitze * 410),
    drehzahl: Math.round((omega * 60) / (2 * Math.PI)),
    schlag: (3.2 * schlag + 0.15 * (1 - schlag)).toFixed(1).replace(".", ","),
    spannung: Math.round(18 * schlag + 2 * (1 - schlag)),
  };
}
