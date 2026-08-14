import { describe, expect, it } from "vitest";

import {
  mowingPostServiceExceptionMessage,
  mowingPostServiceExceptionReviewMessage,
  mowingPostServiceSummaryExportMessage,
} from "./mowing-post-service-operation-message";

describe("mowing post-service operation messages", () => {
  it("keeps exception creation and review states explicitly simulated and human-gated", () => {
    expect(mowingPostServiceExceptionMessage("created")).toBe(
      "Exceção pós-serviço simulada registrada para revisão humana.",
    );
    expect(mowingPostServiceExceptionReviewMessage("recorded")).toBe(
      "Revisão humana da exceção pós-serviço registrada na trilha append-only.",
    );
  });

  it("keeps unsafe exports blocked and does not show unknown states", () => {
    expect(mowingPostServiceSummaryExportMessage("unsafe-response")).toBe(
      "A exportação foi bloqueada porque o arquivo não confirmou todos os rótulos de segurança.",
    );
    expect(mowingPostServiceExceptionMessage("unknown")).toBeNull();
    expect(mowingPostServiceExceptionReviewMessage()).toBeNull();
    expect(mowingPostServiceSummaryExportMessage("created")).toBeNull();
  });
});
