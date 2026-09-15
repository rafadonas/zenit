import { describe, expect, it } from "vitest";

import { getLoginNotice } from "./login-messages";

describe("dashboard login notices", () => {
  it("uses a generic credential error without confirming account existence", () => {
    const notice = getLoginNotice("credentials", undefined);

    expect(notice).toEqual({
      detail: "Revise os dados e tente novamente. A resposta não confirma se uma conta existe.",
      title: "Não foi possível entrar com os dados informados.",
      tone: "error",
    });
    expect(JSON.stringify(notice)).not.toMatch(/usuário inexistente|conta encontrada/i);
  });

  it("explains session expiry and the recovery action", () => {
    expect(getLoginNotice("session", undefined)).toEqual({
      detail: "Entre novamente para continuar de onde parou.",
      title: "Sua sessão expirou ou não está mais ativa.",
      tone: "info",
    });
  });

  it("does not render unrecognized query-string messages", () => {
    expect(getLoginNotice("private-upstream-detail", "unknown")).toBeNull();
  });
});
