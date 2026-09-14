"use client";

import { useEffect, useRef, useState } from "react";

import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  ScaleControl,
  type GeoJSONSource,
  type MapLayerMouseEvent,
  type StyleSpecification,
} from "maplibre-gl";

import { cachedNdviCells, ndviCellColor } from "../lib/cached-ndvi-layer";
import type { SegmentCollection } from "../lib/segments";
import {
  vegetationClassLabel,
  type VegetationClass,
  type VegetationMapCollection,
} from "../lib/vegetation-map";

interface RealisticCorridorMapProps {
  collection: SegmentCollection;
  ndviVisible: boolean;
  onSelectSegment: (segmentId: string, segmentIndex: number) => void;
  selectedId: string | null;
  tileUrl: string;
  vegetationMap: VegetationMapCollection;
}

function createMapStyle(tileUrl: string): StyleSpecification {
  return {
    version: 8,
    sources: {
      "openstreetmap-base": {
        type: "raster",
        tiles: [tileUrl],
        tileSize: 256,
        minzoom: 0,
        maxzoom: 19,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [{
      id: "openstreetmap-base",
      type: "raster",
      source: "openstreetmap-base",
    }],
  };
}

const ndviGeoJson = {
  type: "FeatureCollection" as const,
  features: cachedNdviCells().map((cell) => ({
    type: "Feature" as const,
    geometry: {
      type: "Polygon" as const,
      coordinates: [[
        cell.northWest,
        [cell.southEast[0], cell.northWest[1]],
        cell.southEast,
        [cell.northWest[0], cell.southEast[1]],
        cell.northWest,
      ]],
    },
    properties: { color: ndviCellColor(cell.value), value: cell.value },
  })),
};

function corridorBounds(collection: SegmentCollection): LngLatBounds {
  const bounds = new LngLatBounds();
  for (const feature of collection.features) {
    for (const [longitude, latitude] of feature.geometry.coordinates) {
      bounds.extend([longitude, latitude]);
    }
  }
  return bounds;
}

function segmentCenter(collection: SegmentCollection, segmentId: string) {
  const feature = collection.features.find(
    (candidate) => candidate.properties.segment_id === segmentId,
  );
  if (!feature || feature.geometry.coordinates.length === 0) return null;
  const middle = feature.geometry.coordinates[Math.floor(feature.geometry.coordinates.length / 2)];
  return middle ? { longitude: middle[0], latitude: middle[1] } : null;
}

export function RealisticCorridorMap({
  collection,
  ndviVisible,
  onSelectSegment,
  selectedId,
  tileUrl,
  vegetationMap,
}: RealisticCorridorMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectRef = useRef(onSelectSegment);
  const selectedIdRef = useRef(selectedId);
  const ndviVisibleRef = useRef(ndviVisible);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    onSelectRef.current = onSelectSegment;
  }, [onSelectSegment]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new MapLibreMap({
      attributionControl: false,
      center: [-46.78, -23.52],
      container: containerRef.current,
      maxZoom: 19,
      minZoom: 8,
      pitchWithRotate: false,
      style: createMapStyle(tileUrl),
      zoom: 11,
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new ScaleControl({ maxWidth: 120, unit: "metric" }), "bottom-right");
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");
    map.on("error", () => setMapStatus((status) => status === "ready" ? status : "error"));

    const selectFromFeature = (event: MapLayerMouseEvent) => {
      const properties = event.features?.[0]?.properties;
      const segmentId = properties?.segment_id ?? properties?.nearest_segment_id;
      const segmentIndex = Number(properties?.segment_index);
      if (typeof segmentId === "string" && Number.isInteger(segmentIndex)) {
        onSelectRef.current(segmentId, segmentIndex);
      }
    };
    const selectVegetationArea = (event: MapLayerMouseEvent) => {
      selectFromFeature(event);
      const properties = event.features?.[0]?.properties;
      const vegetationClass = String(properties?.vegetation_class) as VegetationClass;
      const content = document.createElement("div");
      content.className = "vegetation-popup";
      const title = document.createElement("strong");
      title.textContent = vegetationClassLabel(vegetationClass);
      const detail = document.createElement("span");
      detail.textContent = `Trecho #${properties?.segment_index} · referência 28/03/2025`;
      const warning = document.createElement("small");
      warning.textContent = "Associação histórica inferida · não representa condição atual";
      content.append(title, detail, warning);
      new Popup({ closeButton: true, closeOnClick: true, offset: 8 })
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    };
    const showPointer = () => { map.getCanvas().style.cursor = "pointer"; };
    const hidePointer = () => { map.getCanvas().style.cursor = ""; };

    map.on("load", () => {
      map.addSource("vegetation-areas", { type: "geojson", data: vegetationMap });
      map.addLayer({
        id: "vegetation-area-fill",
        type: "fill",
        source: "vegetation-areas",
        paint: {
          "fill-color": [
            "match", ["get", "vegetation_class"],
            "N1", "#35a566",
            "N2", "#f1b82d",
            "N3", "#e45745",
            "X", "#9da5ad",
            "#858e98",
          ],
          "fill-opacity": [
            "match", ["get", "vegetation_class"],
            "X", 0.18,
            "unknown", 0.24,
            0.58,
          ],
        },
      });
      map.addLayer({
        id: "vegetation-area-outline",
        type: "line",
        source: "vegetation-areas",
        paint: { "line-color": "#ffffff", "line-opacity": 0.8, "line-width": 1 },
      });

      map.addSource("cached-ndvi", { type: "geojson", data: ndviGeoJson });
      map.addLayer({
        id: "cached-ndvi-fill",
        type: "fill",
        source: "cached-ndvi",
        layout: { visibility: ndviVisibleRef.current ? "visible" : "none" },
        paint: {
          "fill-color": ["get", "color"],
          "fill-opacity": 0.72,
          "fill-outline-color": "rgba(255,255,255,0.45)",
        },
      });

      map.addSource("road-segments", { type: "geojson", data: collection });
      map.addLayer({
        id: "road-segments-casing",
        type: "line",
        source: "road-segments",
        paint: { "line-color": "#ffffff", "line-opacity": 0.9, "line-width": 6 },
      });
      map.addLayer({
        id: "road-segments-line",
        type: "line",
        source: "road-segments",
        paint: { "line-color": "#5a26ff", "line-opacity": 0.9, "line-width": 2.5 },
      });
      map.addLayer({
        id: "road-segments-selected",
        type: "line",
        source: "road-segments",
        filter: ["==", ["get", "segment_id"], selectedIdRef.current ?? ""],
        paint: { "line-color": "#15131a", "line-width": 7 },
      });
      map.addLayer({
        id: "road-segments-hit",
        type: "line",
        source: "road-segments",
        paint: { "line-color": "#000000", "line-opacity": 0, "line-width": 18 },
      });

      map.on("click", "road-segments-hit", selectFromFeature);
      map.on("click", "vegetation-area-fill", selectVegetationArea);
      map.on("mouseenter", "road-segments-hit", showPointer);
      map.on("mouseenter", "vegetation-area-fill", showPointer);
      map.on("mouseleave", "road-segments-hit", hidePointer);
      map.on("mouseleave", "vegetation-area-fill", hidePointer);

      const bounds = corridorBounds(collection);
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 48, duration: 0 });
      if (selectedIdRef.current) {
        const center = segmentCenter(collection, selectedIdRef.current);
        if (center) map.jumpTo({ center: [center.longitude, center.latitude], zoom: 15 });
      }
      setMapStatus("ready");
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [collection, tileUrl, vegetationMap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("cached-ndvi-fill")) return;
    map.setLayoutProperty(
      "cached-ndvi-fill",
      "visibility",
      ndviVisible ? "visible" : "none",
    );
  }, [ndviVisible]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("road-segments-selected")) return;
    map.setFilter("road-segments-selected", [
      "==",
      ["get", "segment_id"],
      selectedId ?? "",
    ]);
    if (selectedId) {
      const center = segmentCenter(collection, selectedId);
      if (center) {
        map.easeTo({ center: [center.longitude, center.latitude], duration: 450, zoom: 15 });
      }
    }
  }, [collection, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    const segmentSource = map?.getSource("road-segments") as GeoJSONSource | undefined;
    const vegetationSource = map?.getSource("vegetation-areas") as GeoJSONSource | undefined;
    segmentSource?.setData(collection);
    vegetationSource?.setData(vegetationMap);
  }, [collection, vegetationMap]);

  return (
    <div className="realistic-map-shell">
      <div className="realistic-map" ref={containerRef} />
      {mapStatus !== "ready" ? (
        <div className={`map-load-state ${mapStatus}`} role={mapStatus === "error" ? "alert" : "status"}>
          <span aria-hidden="true" />
          <strong>{mapStatus === "loading" ? "Carregando mapa" : "Mapa-base indisponível"}</strong>
          <small>
            {mapStatus === "loading"
              ? "Preparando ruas, segmentos e áreas históricas de vegetação."
              : "A lista equivalente, filtros e detalhes continuam disponíveis sem os tiles."}
          </small>
        </div>
      ) : null}
    </div>
  );
}
