export interface AuthenticatedContext {
  user: {
    id: string;
    email: string;
    display_name: string;
  };
  road_roles: Array<{
    road_code: string;
    role: "manager" | "supervisor";
    data_status: "real" | "prepared" | "simulated";
  }>;
}

export interface AccessTokenContract {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isAccessTokenContract(value: unknown): value is AccessTokenContract {
  return (
    isRecord(value) &&
    typeof value.access_token === "string" &&
    value.access_token.length > 20 &&
    value.token_type === "bearer" &&
    typeof value.expires_in === "number" &&
    Number.isInteger(value.expires_in) &&
    value.expires_in >= 300 &&
    value.expires_in <= 86_400
  );
}

export function isAuthenticatedContext(value: unknown): value is AuthenticatedContext {
  if (!isRecord(value) || !isRecord(value.user) || !Array.isArray(value.road_roles)) {
    return false;
  }
  return (
    typeof value.user.id === "string" &&
    typeof value.user.email === "string" &&
    typeof value.user.display_name === "string" &&
    value.road_roles.every(
      (role) =>
        isRecord(role) &&
        typeof role.road_code === "string" &&
        ["manager", "supervisor"].includes(String(role.role)) &&
        ["real", "prepared", "simulated"].includes(String(role.data_status)),
    )
  );
}
