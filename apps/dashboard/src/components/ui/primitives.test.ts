import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createElement, Fragment } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  Alert,
  Button,
  Card,
  DataStatus,
  Dialog,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  IconButton,
  Select,
  Skeleton,
  Tabs,
} from "./primitives";

const sourceRoot = join(dirname(fileURLToPath(import.meta.url)), "../..");
const primitiveStyles = readFileSync(join(sourceRoot, "styles/primitives.css"), "utf8");

describe("accessible UI primitives", () => {
  it("keeps button states accessible", () => {
    const markup = renderToStaticMarkup(createElement(Button, { loading: true }, "Salvar"));

    expect(markup).toContain('type="button"');
    expect(markup).toContain('disabled=""');
    expect(markup).toContain('aria-busy="true"');
    expect(markup).toContain("Salvar");
    expect(markup).toContain("Carregando");
  });

  it("requires icon buttons to carry an accessible name", () => {
    const markup = renderToStaticMarkup(createElement(IconButton, { "aria-label": "Abrir filtros" }, "F"));

    expect(markup).toContain('aria-label="Abrir filtros"');
    expect(markup).toContain('class="ui-icon-button');
  });

  it("renders field descriptions and invalid state on the control", () => {
    const select = createElement(Select, {
      id: "road",
      name: "road",
      options: [{ label: "SP-021", value: "SP021" }],
      placeholder: "Selecione",
    });
    const markup = renderToStaticMarkup(
      createElement(Field, {
        error: "Obrigatorio",
        hint: "Escolha uma rodovia",
        htmlFor: "road",
        label: "Rodovia",
        required: true,
      }, select),
    );

    expect(markup).toContain('for="road"');
    expect(markup).toContain('id="road-hint"');
    expect(markup).toContain('id="road-error"');
    expect(markup).toContain('aria-describedby="road-hint road-error"');
    expect(markup).toContain('aria-invalid="true"');
  });

  it("publishes status, alert, card, state, tabs, and dialog semantics", () => {
    const markup = renderToStaticMarkup(
      createElement(Fragment, null,
        createElement(DataStatus, { status: "simulated" }),
        createElement(Alert, { tone: "critical", title: "Falha" }, "Tente novamente."),
        createElement(Card, {
          footer: createElement(Button, { variant: "secondary" }, "Ver"),
          title: "Resumo",
        }, "Conteudo"),
        createElement(EmptyState, { description: "Nada pendente.", title: "Fila vazia" }),
        createElement(ErrorState, { action: createElement(Button, null, "Recarregar") }),
        createElement(Skeleton, { label: "Carregando fila" }),
        createElement(Tabs, {
          items: [
            { id: "overview", label: "Overview", selected: true },
            { id: "map", label: "Mapa" },
          ],
          label: "Secoes",
        }),
        createElement(Dialog, { open: true, title: "Detalhe" }, "Corpo"),
        createElement(Drawer, { open: true, placement: "bottom", title: "Filtros" }, "Conteudo"),
      ),
    );

    expect(markup).toContain("Simulado");
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('role="tablist"');
    expect(markup).toContain('aria-selected="true"');
    expect(markup).toContain("<dialog");
    expect(markup).toContain("ui-drawer--bottom");
    expect(markup).toContain("Carregando fila");
  });

  it("documents hover, focus, disabled, loading, and 44px target styles", () => {
    expect(primitiveStyles).toContain(".ui-button:hover");
    expect(primitiveStyles).toContain(".ui-button:disabled");
    expect(primitiveStyles).toContain(".ui-button[aria-busy=\"true\"]");
    expect(primitiveStyles).toContain("min-height: 44px");
    expect(primitiveStyles).toContain("width: 44px");
    expect(primitiveStyles).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
