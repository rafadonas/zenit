import { describe, expect, it } from "vitest";

import {
  DEMO_GUIDE_CONTEXT,
  DEMO_GUIDE_HUMAN_DECISION,
  DEMO_GUIDE_STEPS,
  DEMO_GUIDE_SUMMARY,
} from "./demo-guide";

const DASHBOARD_ROUTES = ["/overview", "/corridor", "/recommendations", "/photo-reviews"];
const VISIBLE_STATUS_LABELS = ["Real", "Estimado", "Preparado", "Simulado", "Inconclusivo"];

describe("demo usage guide", () => {
  it("follows the presentation order, from segmentation to the limits of simulation", () => {
    expect(DEMO_GUIDE_STEPS.map((step) => step.title)).toEqual([
      "Entenda como a rodovia é dividida",
      "Abra o mapa da rodovia",
      "Selecione um trecho",
      "Analise a rodovia parte por parte",
      "Priorize os trechos que precisam de atenção",
      "Identifique o que é real e o que é simulado",
      "Leia o resultado com o limite certo",
    ]);
  });

  it("describes the 100 m segments and the four zones", () => {
    const division = DEMO_GUIDE_STEPS[0].body;

    expect(division).toContain("100 metros");
    for (const zone of ["lado esquerdo", "lado direito", "canteiro central", "áreas especiais"]) {
      expect(division).toContain(zone);
    }
  });

  it("only links to screens that exist in the dashboard", () => {
    for (const step of DEMO_GUIDE_STEPS) {
      if (step.action) expect(DASHBOARD_ROUTES).toContain(step.action.href);
    }
  });

  it("names the controls exactly as the screens label them", () => {
    const text = DEMO_GUIDE_STEPS.map((step) => step.body).join(" ");

    for (const control of ["Mapa", "Lista equivalente ao mapa", "Localizar", "Detalhes do trecho",
      "Classe histórica", "Atenção e próxima ação", "Revisar decisão"]) {
      expect(text).toContain(control);
    }
    for (const label of VISIBLE_STATUS_LABELS) expect(text).toContain(label);
  });

  it("keeps the human decision and the simulation limit explicit", () => {
    expect(DEMO_GUIDE_HUMAN_DECISION).toContain("não substitui a decisão humana");
    const limit = DEMO_GUIDE_STEPS[DEMO_GUIDE_STEPS.length - 1].body;
    expect(limit).toContain("não prova um resultado operacional real");
    expect(limit).toContain("revisão humana");
  });

  it("never presents the historical class as current vegetation condition", () => {
    const analysis = DEMO_GUIDE_STEPS[3];

    expect(analysis.note).toContain("não representa a condição atual");
    const everything = [...DEMO_GUIDE_CONTEXT, DEMO_GUIDE_SUMMARY, ...DEMO_GUIDE_STEPS.map((s) => s.body)].join(" ");
    expect(everything).not.toMatch(/classifica(ção)? de cobertura/i);
    expect(everything).not.toMatch(/autoriza|libera(r)? (a )?roçada/i);
  });
});
