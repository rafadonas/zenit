import { NextResponse } from "next/server";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(
  _request: Request,
  context: { params: Promise<{ segmentId: string }> },
) {
  const { segmentId } = await context.params;
  if (!UUID_PATTERN.test(segmentId)) {
    return NextResponse.json({ detail: "Invalid segment identifier" }, { status: 400 });
  }

  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${baseUrl}/v1/segments/${encodeURIComponent(segmentId)}/satellite-observations?limit=10`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    return NextResponse.json(
      { detail: "Satellite observation API is unavailable" },
      { status: response.status },
    );
  }
  return NextResponse.json(await response.json());
}
