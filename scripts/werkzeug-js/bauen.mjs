import { build } from "esbuild";
import plugin from "./plugin.mjs";
await build({ entryPoints: ["zusatz.js"], bundle: true, format: "esm", minify: true, outfile: "three-zusatz.min.js", plugins: [plugin], legalComments: "none" });
