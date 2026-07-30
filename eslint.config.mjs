import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // The swatches are pre-cropped WebP already at their display size and the
      // image optimizer is switched off in next.config.ts, so next/image would
      // add a pipeline without changing a byte that reaches the browser.
      "@next/next/no-img-element": "off",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "pipeline/**"]),
]);

export default eslintConfig;
