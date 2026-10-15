import { einrichten } from "./einwilligung.js";

const knopf = document.querySelector("[data-menue]");
const nav = document.getElementById("hauptnav");
if (knopf && nav) {
  knopf.addEventListener("click", () => {
    const offen = nav.classList.toggle("ist-offen");
    knopf.setAttribute("aria-expanded", String(offen));
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("ist-offen")) {
      nav.classList.remove("ist-offen");
      knopf.setAttribute("aria-expanded", "false");
      knopf.focus();
    }
  });
}

einrichten();
