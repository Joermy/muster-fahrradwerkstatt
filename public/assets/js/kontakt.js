import { erlaubt, beobachten, speichern } from "./einwilligung.js";

const rahmen = document.querySelector("[data-karte]");
const QUELLE = "https://www.openstreetmap.org/export/embed.html?bbox=10.2185%2C52.3156%2C10.2485%2C52.3276&layer=mapnik&marker=52.3216%2C10.2335";

function laden() {
  if (!rahmen || rahmen.querySelector("iframe")) return;
  const f = document.createElement("iframe");
  f.title = "Karte von Peine mit der Lage der Werkstatt (OpenStreetMap)";
  f.src = QUELLE;
  f.loading = "lazy";
  f.referrerPolicy = "no-referrer";
  f.setAttribute("sandbox", "allow-scripts allow-same-origin allow-popups");
  rahmen.querySelector("[data-karte-vorhang]").remove();
  rahmen.append(f);
}

if (rahmen) {
  if (erlaubt("medien")) laden();
  rahmen.querySelector("[data-karte-laden]").addEventListener("click", () => {
    if (rahmen.querySelector("[data-karte-merken]").checked) speichern(true);
    laden();
  });
  beobachten((s) => {
    if (s.medien) laden();
  });
}
