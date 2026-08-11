import layerData from "../data/cached-ndvi-preview.json";

import type { SatelliteObservation } from "./satellite-observations";
import type { Position } from "./segments";

export interface CachedNdviCell {
  column: number;
  row: number;
  value: number | null;
  northWest: Position;
  southEast: Position;
}

export const CACHED_NDVI_ASSET_SHA256 = layerData.source_asset_sha256;

export function observationSupportsCachedNdviLayer(
  observation: SatelliteObservation,
): boolean {
  return (
    observation.sensor === "sentinel-2" &&
    observation.cache_status === "partially_cached" &&
    observation.scene_data_status === "real" &&
    observation.zone_data_status === "prepared" &&
    observation.conclusion === "inconclusive" &&
    observation.recommendation === "inspect" &&
    observation.eligible_for_official_reporting === false &&
    observation.assets.some(
      (asset) =>
        asset.media_type === "image/tiff" &&
        asset.role.startsWith("ndvi_aoi_crop_") &&
        asset.checksum_sha256 === CACHED_NDVI_ASSET_SHA256,
    )
  );
}

export function cachedNdviCells(): CachedNdviCell[] {
  const { bounds_epsg_4326: bounds, height, values, width } = layerData;
  if (values.length !== width * height) {
    throw new Error("Cached NDVI layer dimensions do not match its values");
  }
  const longitudeStep = (bounds.east - bounds.west) / width;
  const latitudeStep = (bounds.north - bounds.south) / height;
  return values.map((value, index) => {
    const row = Math.floor(index / width);
    const column = index % width;
    return {
      column,
      row,
      value,
      northWest: [
        bounds.west + column * longitudeStep,
        bounds.north - row * latitudeStep,
      ],
      southEast: [
        bounds.west + (column + 1) * longitudeStep,
        bounds.north - (row + 1) * latitudeStep,
      ],
    };
  });
}

export function ndviCellColor(value: number | null): string {
  if (value === null) return "#3f4654";
  if (value < 0) return "#5d86c2";
  if (value < 0.1) return "#d9c98a";
  if (value < 0.2) return "#a8c96a";
  if (value < 0.3) return "#4d9b50";
  if (value < 0.5) return "#237a3b";
  return "#0b4f2b";
}
