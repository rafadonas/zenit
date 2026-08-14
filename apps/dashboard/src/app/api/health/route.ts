import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_HEALTH_TIMEOUT_MS = 2_000;

interface DependencyExpectation {
  name: string;
  required: boolean;
  status: string;
}

const EXPECTED_DEPENDENCIES: DependencyExpectation[] = [
  { name: "database", required: true, status: "ok" },
  { name: "object_storage", required: true, status: "ok" },
  { name: "queue", required: false, status: "not_configured" },
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isReadyApiHealth(payload: unknown): boolean {
  if (!isRecord(payload) || payload.status !== "ok" || !isRecord(payload.checks)) {
    return false;
  }
  const checks = payload.checks;
  return EXPECTED_DEPENDENCIES.every((expected) => {
    const check = checks[expected.name];
    return (
      isRecord(check) &&
      check.status === expected.status &&
      check.required === expected.required
    );
  });
}

function readinessResponse(status: "ok" | "degraded", httpStatus: 200 | 503) {
  return NextResponse.json(
    {
      checks: { api: { required: true, status } },
      service: "zenit-dashboard",
      status,
    },
    {
      headers: { "Cache-Control": "no-store" },
      status: httpStatus,
    },
  );
}

export async function GET() {
  const apiBaseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(API_HEALTH_TIMEOUT_MS),
    });
    if (!response.ok || !isReadyApiHealth(await response.json())) {
      return readinessResponse("degraded", 503);
    }
  } catch {
    return readinessResponse("degraded", 503);
  }
  return readinessResponse("ok", 200);
}
