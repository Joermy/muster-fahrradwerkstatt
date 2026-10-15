export default {
  name: "three-extern",
  setup(build) {
    build.onResolve({ filter: /^three$/ }, () => ({ path: "./three.module.min.js", external: true }));
  },
};
