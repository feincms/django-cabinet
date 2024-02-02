module.exports = {
  env: {
    browser: true,
    node: true,
    es2020: true,
  },
  extends: ["eslint:recommended"],
  rules: {
    "no-unused-vars": [
      "error",
      {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      },
    ],
  },
}
