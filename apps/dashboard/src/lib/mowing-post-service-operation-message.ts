export function mowingPostServiceExceptionMessage(status?: string): string | null {
  if (status === "created") {
    return "Exceção pós-serviço simulada registrada para revisão humana.";
  }
  if (status === "forbidden") {
    return "Seu usuário não pode avaliar exceção pós-serviço nesta rodovia.";
  }
  if (status === "missing") return "O resumo pós-serviço simulado não foi encontrado.";
  if (status === "conflict") return "A exceção já existe ou a chave entrou em conflito.";
  if (status === "invalid") return "A justificativa da exceção pós-serviço é inválida.";
  if (status === "service-unavailable") {
    return "O serviço de exceções pós-serviço não está disponível agora.";
  }
  return null;
}

export function mowingPostServiceExceptionReviewMessage(status?: string): string | null {
  if (status === "recorded") {
    return "Revisão humana da exceção pós-serviço registrada na trilha append-only.";
  }
  if (status === "forbidden") {
    return "Seu usuário não pode revisar esta exceção pós-serviço nesta rodovia.";
  }
  if (status === "missing") return "A exceção pós-serviço simulada não foi encontrada.";
  if (status === "conflict") {
    return "A chave de repetição ou a revisão efetiva da exceção entrou em conflito.";
  }
  if (status === "invalid") {
    return "A decisão da exceção pós-serviço está incompleta ou inconsistente.";
  }
  if (status === "service-unavailable") {
    return "O serviço de revisão da exceção pós-serviço não está disponível agora.";
  }
  return null;
}

export function mowingPostServiceSummaryExportMessage(status?: string): string | null {
  if (status === "missing") {
    return "O resumo pós-serviço simulado não foi encontrado ou não está acessível.";
  }
  if (status === "conflict") {
    return "A chave da exportação entrou em conflito com outra solicitação.";
  }
  if (status === "invalid") return "Informe um propósito válido para exportar o resumo.";
  if (status === "unsafe-response") {
    return "A exportação foi bloqueada porque o arquivo não confirmou todos os rótulos de segurança.";
  }
  if (status === "service-unavailable") {
    return "O serviço de exportação não está disponível agora.";
  }
  return null;
}
