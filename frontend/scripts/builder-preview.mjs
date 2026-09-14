// Fictional local preview. Production uses the bounded ReportLab renderer.
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { resolveVariables } from "../src/variables.js";
export async function renderBuilder(data) {
  const doc = await PDFDocument.create();
  const fonts = {};
  for (const [name, id] of Object.entries({
    normal: StandardFonts.Helvetica,
    bold: StandardFonts.HelveticaBold,
    times: StandardFonts.TimesRoman,
    courier: StandardFonts.Courier,
  }))
    fonts[name] = await doc.embedFont(id);
  const colorOf = (value, fallback = "#242a27") =>
    rgb(
      ...(value || fallback)
        .slice(1)
        .match(/../g)
        .map((h) => parseInt(h, 16) / 255),
    );
  const values = data.resolvedVariables || [];
  for (const p of data.pages) {
    const page = doc.addPage([595, 842]);
    for (const b of p.blocks) {
      if (b.type === "Field") continue;
      const pad = b.padding || 0,
        x = b.x + pad,
        w = b.width - pad * 2,
        h = b.height - pad * 2,
        top = b.y + pad,
        color = colorOf(b.color),
        size = b.font_size || 12;
      page.drawRectangle({
        x: b.x,
        y: 842 - b.y - b.height,
        width: b.width,
        height: b.height,
        color: colorOf(b.background, "#ffffff"),
      });
      if (b.type === "Image" && b.image) {
        const image = b.image.startsWith("data:image/png")
          ? await doc.embedPng(b.image)
          : await doc.embedJpg(b.image);
        const fit = image.scaleToFit(
          Math.min(w, b.image_width || w),
          Math.min(h, b.image_height || h),
        );
        page.drawImage(image, {
          x:
            x +
            (w - fit.width) *
              ({ left: 0, center: 0.5, right: 1 }[b.align] || 0),
          y: 842 - top - fit.height,
          ...fit,
        });
        continue;
      }
      if (b.type === "Divider") {
        page.drawLine({
          start: { x, y: 842 - top - h / 2 },
          end: { x: x + w, y: 842 - top - h / 2 },
          color,
        });
        continue;
      }
      const font =
        b.type === "Heading"
          ? fonts.bold
          : b.font_family === "Times New Roman"
            ? fonts.times
            : b.font_family === "Courier New"
              ? fonts.courier
              : fonts.normal;
      const text = resolveVariables(b.text, values);
      if (/{{\s*[A-Za-z]/.test(text))
        throw Error("Set values for all document variables before previewing.");
      const leading = size * (b.line_height || 1.35);
      function lines(text, width) {
        const out = [];
        for (const line of text.split("\n")) {
          let cur = "";
          for (const word of line.split(" ")) {
            if (font.widthOfTextAtSize(cur + word, size) > width && cur) {
              out.push(cur.trimEnd());
              cur = "";
            }
            cur += word + " ";
          }
          out.push(cur.trimEnd());
        }
        return out;
      }
      if (b.type === "Table") {
        const rows = b.cells
            ? b.cells.map((r) => r.map((c) => resolveVariables(c, values)))
            : text.split("\n").map((l) => l.split("\t")),
          cw = w / Math.max(...rows.map((r) => r.length));
        let y = 842 - top;
        for (const [ri, row] of rows.entries()) {
          const ls = row.map((c) => lines(c, cw - 16)),
            rh = Math.max(...ls.map((l) => l.length)) * leading + 16;
          for (let c = 0; c < row.length; c++) {
            page.drawRectangle({
              x: x + c * cw,
              y: y - rh,
              width: cw,
              height: rh,
              borderColor: rgb(0.8, 0.83, 0.87),
              borderWidth: 0.5,
              color: ri === 0 ? rgb(0.94, 0.95, 0.96) : rgb(1, 1, 1),
            });
            ls[c].forEach((l, i) =>
              page.drawText(l, {
                x: x + c * cw + 8,
                y: y - 8 - size - i * leading,
                font,
                size,
                color,
              }),
            );
          }
          y -= rh;
        }
        continue;
      }
      if (b.html && /<(h[1-5]|p|div)[ >]/i.test(b.html)) {
        let y = 842 - top;
        const sections = [
          ...b.html.matchAll(/<(h[1-5]|p|div)[^>]*>([\s\S]*?)<\/\1>/gi),
        ];
        for (const [i, section] of sections.entries()) {
          const kind = section[1].toLowerCase(),
            sz = { h1: 32, h2: 28, h3: 24, h4: 20, h5: 18 }[kind] || size,
            f = kind.startsWith("h") ? fonts.bold : font,
            lead = sz * (kind.startsWith("h") ? 1.2 : b.line_height || 1.5);
          const value = resolveVariables(
            section[2]
              .replace(/<br\s*\/?\s*>/gi, "\n")
              .replace(/<[^>]+>/g, "")
              .replaceAll("&amp;", "&")
              .replaceAll("&lt;", "<")
              .replaceAll("&gt;", ">")
              .replaceAll("&nbsp;", " "),
            values,
          );
          let cur = "";
          const ls = [];
          for (const word of value.split(/\s+/)) {
            if (f.widthOfTextAtSize(cur + word, sz) > w && cur) {
              ls.push(cur.trim());
              cur = "";
            }
            cur += word + " ";
          }
          ls.push(cur.trim());
          for (const line of ls) {
            page.drawText(line, { x, y: y - sz, font: f, size: sz, color });
            y -= lead;
          }
          if (i < sections.length - 1) y -= 16;
        }
        continue;
      }
      lines(text, w).forEach((line, i) => {
        const offset =
          (w - font.widthOfTextAtSize(line, size)) *
          ({ left: 0, center: 0.5, right: 1 }[b.align] || 0);
        page.drawText(line, {
          x: x + offset,
          y: 842 - top - size - i * leading,
          font,
          size,
          color,
        });
      });
    }
  }
  return Buffer.from(await doc.save());
}
