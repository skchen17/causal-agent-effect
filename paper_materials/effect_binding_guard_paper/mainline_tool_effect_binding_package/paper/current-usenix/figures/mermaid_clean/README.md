# Mermaid figures used by main.tex

`mmd/` contains the editable Mermaid sources and `pdf/` the final vector PDFs
included by the LaTeX wrappers under `figures/`.

| Figure | Source | PDF |
|---|---|---|
| Figure 2(a) normal flow | `mmd/fig2_normal_lane.mmd` | `pdf/fig2_normal_lane.pdf` |
| Figure 2(b) our system | `mmd/fig2_ours_lane.mmd` | `pdf/fig2_ours_lane.pdf` |
| Runtime mediation sequence | `mmd/fig2_runtime_sequence.mmd` | `pdf/fig2_runtime_sequence.pdf` |
| Registration loop | `mmd/fig_registration_loop_horizontal.mmd` | `pdf/fig_registration_loop_horizontal.pdf` |
| Evaluation evidence chain | `mmd/fig_evaluation_evidence_chain.mmd` | `pdf/fig_evaluation_evidence_chain.pdf` |

Regenerate one PDF from its source with:

```bash
npx -y @mermaid-js/mermaid-cli -i mmd/<name>.mmd -o /tmp/<name>.svg -b white -w 600
node scripts/render_svg_pdf.js /tmp/<name>.svg pdf/<name>.pdf
```

`render_svg_pdf.js` is a small Puppeteer wrapper that renders the SVG at its
native viewBox size so font sizes remain readable when LaTeX scales the PDF to
`\textwidth`.
