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

async function starten() {
  if (!wurzel || new URLSearchParams(location.search).has("standbild")) return;
  try {
    const [{ werkstattStarten }, leistungen] = await Promise.all([
      import("./werkstatt/spieler.js"),
      fetch(new URL("assets/daten/leistungen.json", BASIS)).then((r) => r.json()),
    ]);
    await werkstattStarten({ wurzel, basis: BASIS, leistungen });
    wurzel.querySelector("[data-teile]").hidden = false;
  } catch (e) {
    // Ohne Bildfolge bleibt das Standbild aus dem HTML stehen
    console.error(e);
  }
}

starten();
