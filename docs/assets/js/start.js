import { BASIS } from "./api.js";

const wurzel = document.querySelector("[data-werkstatt]");

const kopf = document.querySelector(".kopf");
if (kopf && wurzel) {
  const pruefen = () => {
    const r = wurzel.getBoundingClientRect();
    kopf.classList.toggle("kopf--ueber", r.bottom > kopf.offsetHeight + 40);
  };
  pruefen();
  window.addEventListener("scroll", pruefen, { passive: true });
  window.addEventListener("resize", pruefen);
}

function webgl2() {
  try {
    const c = document.createElement("canvas");
    return !!c.getContext("webgl2");
  } catch (e) {
    return false;
  }
}

function standbild() {
  const bild = wurzel.querySelector("[data-standbild]");
  bild.hidden = false;
  wurzel.querySelector("[data-laden]").classList.add("ist-fertig");
  wurzel.classList.add("ohne-3d");
}

async function starten() {
  const sparen = navigator.connection && navigator.connection.saveData;
  if (!wurzel || !webgl2() || sparen || new URLSearchParams(location.search).has("ohne3d")) {
    standbild();
    return;
  }
  try {
    const [{ werkstattStarten }, leistungen] = await Promise.all([
      import("./rad/haupt.js"),
      fetch(new URL("assets/daten/leistungen.json", BASIS)).then((r) => r.json()),
    ]);
    await werkstattStarten({
      wurzel,
      basis: BASIS,
      leistungen,
    });
    wurzel.querySelector("[data-teile]").hidden = false;
  } catch (e) {
    console.error(e);
    standbild();
  }
}

starten();
