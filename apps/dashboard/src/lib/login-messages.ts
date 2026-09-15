export type LoginNoticeTone = "error" | "info" | "success" | "warning";

export interface LoginNotice {
  detail: string;
  title: string;
  tone: LoginNoticeTone;
}

export function getLoginNotice(
  error: string | undefined,
  status: string | undefined,
): LoginNotice | null {
  if (status === "signed-out") {
    return {
      detail: "Você pode entrar novamente quando precisar.",
      title: "Sessão encerrada com segurança.",
      tone: "success",
    };
  }
  if (status === "signed-out-local") {
    return {
      detail: "A revogação remota não pôde ser confirmada. O acesso local foi removido.",
      title: "Sessão local encerrada.",
      tone: "warning",
    };
  }
  if (error === "credentials") {
    return {
      detail: "Revise os dados e tente novamente. A resposta não confirma se uma conta existe.",
      title: "Não foi possível entrar com os dados informados.",
      tone: "error",
    };
  }
  if (error === "rate-limited") {
    return {
      detail: "Espere alguns minutos antes de uma nova tentativa.",
      title: "Muitas tentativas de entrada.",
      tone: "warning",
    };
  }
  if (error === "session") {
    return {
      detail: "Entre novamente para continuar de onde parou.",
      title: "Sua sessão expirou ou não está mais ativa.",
      tone: "info",
    };
  }
  if (error === "service-unavailable") {
    return {
      detail: "Aguarde um momento e tente de novo. Seus dados não foram enviados para outra tela.",
      title: "A autenticação está indisponível no momento.",
      tone: "error",
    };
  }
  if (error === "invalid-request") {
    return {
      detail: "Preencha novamente o formulário e tente de novo.",
      title: "A solicitação de entrada não pôde ser validada.",
      tone: "error",
    };
  }
  return null;
}
