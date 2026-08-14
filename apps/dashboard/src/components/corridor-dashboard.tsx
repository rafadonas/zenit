"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  createMapProjection,
  findSegmentIdByIndex,
  formatDistance,
  projectSegments,
  type SegmentCollection,
  type SegmentProperties,
} from "../lib/segments";
import {
  cachedNdviCells,
  ndviCellColor,
  observationSupportsCachedNdviLayer,
} from "../lib/cached-ndvi-layer";
import {
  formatAcquisitionDate,
  isSatelliteObservationCollection,
  type SatelliteObservationCollection,
} from "../lib/satellite-observations";

interface CorridorDashboardProps {
  collection: SegmentCollection;
  initialSegmentIndex?: number | null;
}

function SegmentDetails({ segment }: { segment: SegmentProperties | null }) {
  if (!segment) {
    return (
      <div className="empty-selection">
        <span aria-hidden="true">↗</span>
        <p>Selecione um trecho no mapa para consultar seus metadados.</p>
      </div>
    );
  }
  return (
    <dl className="detail-list">
      <div>
        <dt>Trecho</dt>
        <dd>#{segment.segment_index.toString().padStart(3, "0")}</dd>
      </div>
      <div>
        <dt>Extensão geométrica</dt>
        <dd>{formatDistance(segment.end_distance_m - segment.start_distance_m)}</dd>
      </div>
      <div>
        <dt>Posição no eixo estimado</dt>
        <dd>
          {formatDistance(segment.start_distance_m)} – {formatDistance(segment.end_distance_m)}
        </dd>
      </div>
      <div>
        <dt>Origem</dt>
        <dd><span className="status-pill estimated">Estimado</span></dd>
      </div>
      <div>
        <dt>Validação</dt>
        <dd><span className="status-pill review">Pendente de validação</span></dd>
      </div>
      <div>
        <dt>Uso operacional</dt>
        <dd>{segment.eligible_for_operations ? "Liberado" : "Bloqueado"}</dd>
      </div>
    </dl>
  );
}

type ObservationState =
  | { segmentId: string; status: "ready"; collection: SatelliteObservationCollection }
  | { segmentId: string; status: "error" }
  | null;

function SatelliteEvidence({
  ndviVisible,
  onNdviVisibilityChange,
  segmentId,
}: {
  ndviVisible: boolean;
  onNdviVisibilityChange: (visible: boolean) => void;
  segmentId: string | null;
}) {
  const [state, setState] = useState<ObservationState>(null);
  const [selectedRun, setSelectedRun] = useState<{ segmentId: string; runId: string } | null>(null);

  useEffect(() => {
    if (!segmentId) return;
    const controller = new AbortController();
    void fetch(`/api/segments/${encodeURIComponent(segmentId)}/satellite-observations`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Observation request failed");
        const payload: unknown = await response.json();
        if (!isSatelliteObservationCollection(payload)) throw new Error("Invalid observation contract");
        setState({ segmentId, status: "ready", collection: payload });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({ segmentId, status: "error" });
      });
    return () => controller.abort();
  }, [segmentId]);

  if (!segmentId) return null;
  if (!state || state.segmentId !== segmentId) {
    return <div className="evidence-state" role="status">Consultando evidências satelitais…</div>;
  }
  if (state.status === "error") {
    return <div className="evidence-state error" role="alert">Não foi possível consultar as evidências. Nenhum resultado foi presumido.</div>;
  }
  if (state.collection.items.length === 0) {
    return <div className="evidence-state">Nenhuma observação satelital registrada para este trecho.</div>;
  }

  const selectedRunId = selectedRun?.segmentId === segmentId ? selectedRun.runId : null;
  const observation =
    state.collection.items.find((item) => item.analysis_run_id === selectedRunId) ??
    state.collection.items[0];
  return (
    <section className="satellite-evidence" aria-label="Evidências satelitais persistidas">
      <div className="evidence-heading">
        <div>
          <p className="eyebrow">Evidência satelital</p>
          <h3>{selectedRunId ? "Observação selecionada" : "Última observação"}</h3>
          <small>
            {state.collection.metadata.result_count} de {state.collection.metadata.total_count}
            {" registro(s) persistido(s)"}
          </small>
        </div>
        <span className={`status-pill ${observation.conclusion === "inconclusive" ? "review" : "estimated"}`}>
          {observation.conclusion === "inconclusive" ? "Inconclusiva" : "Conclusiva"}
        </span>
      </div>
      {state.collection.items.length > 1 ? (
        <div className="observation-history" aria-label="Histórico de observações">
          {state.collection.items.map((item, index) => (
            <button
              aria-pressed={item.analysis_run_id === observation.analysis_run_id}
              key={item.analysis_run_id}
              onClick={() => {
                setSelectedRun({ segmentId, runId: item.analysis_run_id });
                onNdviVisibilityChange(false);
              }}
              type="button"
            >
              <strong>{index === 0 ? "Mais recente" : formatAcquisitionDate(item.acquired_at)}</strong>
              <span>{item.zone_type} · {item.conclusion === "inconclusive" ? "inconclusiva" : "conclusiva"}</span>
            </button>
          ))}
        </div>
      ) : null}
      {state.collection.metadata.truncated ? (
        <p className="history-warning" role="status">
          Histórico parcial: exibindo os {state.collection.metadata.limit} registros mais recentes.
        </p>
      ) : null}
      <dl className="evidence-grid">
        <div><dt>Aquisição</dt><dd>{formatAcquisitionDate(observation.acquired_at)}</dd></div>
        <div><dt>Zona</dt><dd>{observation.zone_type}</dd></div>
        <div><dt>NDVI médio</dt><dd>{observation.mean_ndvi?.toFixed(3) ?? "Sem dado"}</dd></div>
        <div><dt>Pixels válidos</dt><dd>{observation.valid_pixel_percent.toLocaleString("pt-BR")}%</dd></div>
        <div><dt>Confiança</dt><dd>{observation.confidence_band === "low" ? "Baixa" : observation.confidence_band}</dd></div>
        <div><dt>Recomendação</dt><dd>{observation.recommendation === "inspect" ? "Inspecionar" : observation.recommendation}</dd></div>
      </dl>
      {observationSupportsCachedNdviLayer(observation) ? (
        <div className="ndvi-layer-control">
          <button
            aria-pressed={ndviVisible}
            onClick={() => onNdviVisibilityChange(!ndviVisible)}
            type="button"
          >
            {ndviVisible ? "Ocultar recorte NDVI" : "Mostrar recorte NDVI no mapa"}
          </button>
          <small>5 × 11 pixels · 10 m · AOI preparada · checksum verificado</small>
        </div>
      ) : null}
      <div className="evidence-gates">
        <strong>{observation.requires_human_approval ? "Aprovação humana obrigatória" : "Revisão humana preservada"}</strong>
        <span>Relatório oficial: {observation.eligible_for_official_reporting ? "elegível" : "bloqueado"}</span>
      </div>
      <details>
        <summary>Proveniência e artefatos</summary>
        <p>
          {observation.provider} · {observation.collection} · regra {observation.rule_version}
          {" · "}processador {observation.processor_version}
        </p>
        <ul>
          {observation.assets.map((asset) => (
            <li key={`${asset.role}-${asset.checksum_sha256}`}>
              <span>{asset.role}</span>
              <code title={asset.checksum_sha256}>{asset.checksum_sha256.slice(0, 12)}…</code>
            </li>
          ))}
        </ul>
      </details>
      <p className="evidence-warning">
        NDVI e qualidade de pixels não medem altura da vegetação nem autorizam roçada.
      </p>
    </section>
  );
}

export function CorridorDashboard({
  collection,
  initialSegmentIndex = null,
}: CorridorDashboardProps) {
  const projected = useMemo(() => projectSegments(collection.features), [collection.features]);
  const initialSelectedId =
    initialSegmentIndex === null
      ? null
      : findSegmentIdByIndex(collection.features, initialSegmentIndex);
  const [selectedId, setSelectedId] = useState<string | null>(initialSelectedId);
  const [segmentSearch, setSegmentSearch] = useState(
    initialSelectedId && initialSegmentIndex !== null ? String(initialSegmentIndex) : "",
  );
  const [searchError, setSearchError] = useState<string | null>(null);
  const [ndviVisible, setNdviVisible] = useState(false);
  const mapProjection = useMemo(
    () => createMapProjection(collection.features),
    [collection.features],
  );
  const projectedNdviCells = useMemo(() => {
    if (mapProjection === null) return [];
    return cachedNdviCells().map((cell) => {
      const northWest = mapProjection(cell.northWest);
      const southEast = mapProjection(cell.southEast);
      return {
        ...cell,
        x: northWest.x,
        y: northWest.y,
        width: southEast.x - northWest.x,
        height: southEast.y - northWest.y,
      };
    });
  }, [mapProjection]);
  const selected = projected.find((segment) => segment.id === selectedId)?.properties ?? null;
  const totalDistance = Math.max(
    0,
    ...collection.features.map((feature) => feature.properties.end_distance_m),
  );
  const maxSegmentIndex = Math.max(
    0,
    ...collection.features.map((feature) => feature.properties.segment_index),
  );

  function selectSegment(segmentId: string, segmentIndex: number, focus: boolean) {
    setSelectedId(segmentId);
    setSegmentSearch(String(segmentIndex));
    setSearchError(null);
    setNdviVisible(false);
    window.history.replaceState(null, "", `/?segment=${segmentIndex}`);
    if (focus) {
      requestAnimationFrame(() => document.getElementById(`segment-${segmentId}`)?.focus());
    }
  }

  function selectFromSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const segmentIndex = Number(segmentSearch);
    const segmentId = findSegmentIdByIndex(collection.features, segmentIndex);
    if (!segmentId) {
      setSearchError(`Trecho inexistente. Informe um número entre 0 e ${maxSegmentIndex}.`);
      return;
    }
    selectSegment(segmentId, segmentIndex, true);
  }

  return (
    <main className="dashboard-shell" id="main-content">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true"><i /></span>
          <div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div>
        </div>
        <nav className="topnav" aria-label="Navegação principal">
          <Link aria-current="page" href="/">Corredor</Link>
          <Link href="/recommendations">Recomendações</Link>
          <Link href="/photo-reviews">Fotos de inspeção</Link>
          <Link href="/mowing-photo-reviews">Fotos pós-serviço</Link>
          <Link href="/mowing-post-service-summaries">Resumos pós-serviço</Link>
        </nav>
        <div className="update-context">
          <span>Geometria</span>
          <strong>candidata v1</strong>
        </div>
      </header>

      <section className="hero-row">
        <div>
          <p className="eyebrow">Visão do corredor</p>
          <h1>Rodoanel Oeste</h1>
          <p className="subtitle">Segmentação geométrica para validação técnica</p>
        </div>
        <div className="warning-banner" role="status">
          <span className="warning-icon" aria-hidden="true">!</span>
          <div>
            <strong>Eixo estimado — uso operacional bloqueado</strong>
            <span>Marcos KM apresentam inversões e lacunas. Não usar para ordens ou geofence.</span>
          </div>
        </div>
      </section>

      <section className="kpi-grid" aria-label="Indicadores do corredor">
        <article><span>Segmentos</span><strong>{collection.features.length}</strong><small>unidades geométricas</small></article>
        <article><span>Extensão candidata</span><strong>{formatDistance(totalDistance)}</strong><small>não é KM oficial</small></article>
        <article><span>Trechos operacionais</span><strong>0</strong><small>validação necessária</small></article>
        <article><span>CRS métrico</span><strong>31983</strong><small>SIRGAS 2000 / UTM 23S</small></article>
      </section>

      <section className="workspace-grid">
        <article className="map-card">
          <div className="card-heading">
            <div><p className="eyebrow">Mapa de segmentos</p><h2>Corredor completo</h2></div>
            <div className="map-tools">
              <form className="segment-search" onSubmit={selectFromSearch}>
                <label htmlFor="segment-search">Ir para trecho</label>
                <div>
                  <input
                    id="segment-search"
                    inputMode="numeric"
                    max={maxSegmentIndex}
                    min={0}
                    onChange={(event) => setSegmentSearch(event.target.value)}
                    placeholder="195"
                    type="number"
                    value={segmentSearch}
                  />
                  <button type="submit">Localizar</button>
                </div>
                {searchError ? <span role="alert">{searchError}</span> : null}
              </form>
              <div className="map-meta"><span>EPSG:4326</span><span>100 m por trecho</span></div>
            </div>
          </div>

          {projected.length === 0 ? (
            <div className="map-empty"><p>Nenhum segmento encontrado nesta área.</p></div>
          ) : (
            <div className="map-frame">
              <svg viewBox="0 0 1000 680" role="img" aria-labelledby="map-title map-description">
                <title id="map-title">Mapa esquemático dos segmentos da SP-021</title>
                <desc id="map-description">Eixo estimado dividido em segmentos selecionáveis de aproximadamente cem metros.</desc>
                <defs>
                  <pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse">
                    <path d="M 38 0 L 0 0 0 38" className="grid-line" />
                  </pattern>
                  <filter id="route-glow" x="-30%" y="-30%" width="160%" height="160%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>
                <rect width="1000" height="680" fill="url(#grid)" />
                {ndviVisible ? (
                  <g className="ndvi-raster-layer" aria-label="Recorte NDVI Sentinel-2 preparado e não operacional">
                    {projectedNdviCells.map((cell) => (
                      <rect
                        fill={ndviCellColor(cell.value)}
                        height={cell.height}
                        key={`${cell.row}-${cell.column}`}
                        width={cell.width}
                        x={cell.x}
                        y={cell.y}
                      >
                        <title>
                          {cell.value === null
                            ? `NDVI NoData · linha ${cell.row + 1}, coluna ${cell.column + 1}`
                            : `NDVI ${cell.value.toFixed(3)} · linha ${cell.row + 1}, coluna ${cell.column + 1}`}
                        </title>
                      </rect>
                    ))}
                  </g>
                ) : null}
                <g className="route-shadow" aria-hidden="true">
                  {projected.map((segment) => <path d={segment.path} key={`shadow-${segment.id}`} />)}
                </g>
                <g className="segments-layer">
                  {projected.map((segment) => {
                    const isSelected = segment.id === selectedId;
                    return (
                      <path
                        aria-label={`Trecho ${segment.properties.segment_index}, ${formatDistance(segment.properties.end_distance_m - segment.properties.start_distance_m)}, estimado e não operacional`}
                        className={isSelected ? "segment selected" : "segment"}
                        d={segment.path}
                        id={`segment-${segment.id}`}
                        key={segment.id}
                        onClick={() => selectSegment(segment.id, segment.properties.segment_index, false)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectSegment(segment.id, segment.properties.segment_index, true);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                      />
                    );
                  })}
                </g>
              </svg>
              {ndviVisible ? (
                <div className="ndvi-inset" role="img" aria-label="Ampliação dos 55 pixels do recorte NDVI cacheado">
                  <div><strong>NDVI · ampliação</strong><span>Sentinel-2 · 29/07/2026</span></div>
                  <div className="ndvi-inset-grid" aria-hidden="true">
                    {projectedNdviCells.map((cell) => (
                      <i
                        key={`inset-${cell.row}-${cell.column}`}
                        style={{ backgroundColor: ndviCellColor(cell.value) }}
                        title={cell.value === null ? "NoData" : cell.value.toFixed(3)}
                      />
                    ))}
                  </div>
                  <small>AOI estimada · não operacional · NDVI não é altura</small>
                </div>
              ) : null}
              <div className="north-indicator" aria-hidden="true"><span>N</span><i /></div>
              <div className="map-legend" aria-label="Legenda">
                <strong>Legenda</strong>
                <span><i className="legend-line estimated-line" /> Eixo estimado</span>
                <span><i className="legend-line selected-line" /> Segmento selecionado</span>
                {ndviVisible ? <span><i className="legend-ndvi" /> NDVI cacheado · preparado</span> : null}
                <span><i className="legend-lock">×</i> Uso operacional bloqueado</span>
              </div>
            </div>
          )}
          <footer className="map-footer">
            <span>Fonte: marcos SP-021 importados · referência geométrica candidata</span>
            <span>Atualização do conjunto: 06/08/2026</span>
          </footer>
        </article>

        <aside className="side-panel">
          <div className="side-heading"><p className="eyebrow">Inspeção</p><h2>Detalhes do trecho</h2></div>
          <SegmentDetails segment={selected} />
          <SatelliteEvidence
            ndviVisible={ndviVisible}
            onNdviVisibilityChange={setNdviVisible}
            segmentId={selectedId}
          />
          <div className="quality-note">
            <span aria-hidden="true">i</span>
            <div><strong>Sobre esta camada</strong><p>Distâncias seguem a linha candidata de 30,85 km. A fonte não contém eixo rodoviário oficial.</p></div>
          </div>
        </aside>
      </section>
    </main>
  );
}
