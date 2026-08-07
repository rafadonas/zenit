import { CorridorDashboard } from "../components/corridor-dashboard";
import { isSegmentCollection, type SegmentCollection } from "../lib/segments";

export const dynamic = "force-dynamic";

const FULL_CORRIDOR_BBOX = {
  min_lon: -46.84,
  min_lat: -23.64,
  max_lon: -46.72,
  max_lat: -23.4,
};

async function loadSegments(): Promise<SegmentCollection> {
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const search = new URLSearchParams(
    Object.entries(FULL_CORRIDOR_BBOX).map(([key, value]) => [key, String(value)]),
  );
  const response = await fetch(`${baseUrl}/v1/roads/SP021/segments?${search}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Segment API returned HTTP ${response.status}`);
  }
  const payload: unknown = await response.json();
  if (!isSegmentCollection(payload)) {
    throw new Error("Segment API returned an invalid GeoJSON contract");
  }
  return payload;
}

export default async function Home() {
  const segments = await loadSegments();
  return <CorridorDashboard collection={segments} />;
}
