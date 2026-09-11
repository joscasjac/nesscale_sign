import { readFile, writeFile } from "node:fs/promises";
const source = await readFile(
  new URL("../../nesscale_sign/public/frontend/index.html", import.meta.url),
  "utf8",
);
const boot =
  "<script>{% for key in boot %}window[{{ key | tojson }}] = {{ boot[key] | tojson }};{% endfor %}</script>";
await writeFile(
  new URL("../../nesscale_sign/www/nesscale_sign.html", import.meta.url),
  source.replace("</head>", boot + "</head>"),
);
