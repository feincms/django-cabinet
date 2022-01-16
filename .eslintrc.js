module.exports = {
  parser: "@babel/eslint-parser",
  env: {
    browser: true,
    es6: true,
    node: true,
  },
  extends: ["eslint:recommended", "prettier", "plugin:react/recommended"],
  globals: {
    Atomics: "readonly",
    SharedArrayBuffer: "readonly",
    __API_HOST: "readonly",
  },
  parserOptions: {
    ecmaFeatures: {
      experimentalObjectRestSpread: true,
      jsx: true,
    },
    ecmaVersion: 2021,
    requireConfigFile: false,
    sourceType: "module",
  },
  plugins: ["react", "react-hooks"],
  rules: {
    "no-unused-vars": [
      "error",
      {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "React|Fragment|h|^_",
      },
    ],
    "react/prop-types": "off",
    "react/display-name": "off",
    "react-hooks/rules-of-hooks": "warn", // Checks rules of Hooks
    "react-hooks/exhaustive-deps": "warn", // Checks effect dependencies
  },
  settings: {
    react: {
      version: "detect",
    },
  },
}
