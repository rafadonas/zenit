export type MowingRehearsalState =
  | "not_started"
  | "confirmed"
  | "in_progress"
  | "paused"
  | "finished";

export interface PreparedMowingRehearsalEvent {
  event_id: string;
  event_sequence: number;
  source_planning_approval_id: string;
  operation: "confirm" | "start" | "pause" | "resume" | "finish";
  client_occurred_at: string;
  location_status: "not_collected" | "simulated";
  simulation_scope: "demo_only";
  rehearsal_scope: "mowing_demo_rehearsal_only";
  data_status: "simulated";
  operational_approval_satisfied: false;
  authorizes_field_work: false;
  eligible_for_field_execution: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
}

export interface PreparedMowingPostServiceMeasurement {
  event_id: string;
  source_planning_approval_id: string;
  source_planned_point_id: string;
  source_point_sequence: 1 | 2 | 3;
  phase: "post_service";
  height_cm: string | number;
  client_captured_at: string;
  measurement_scope: "mowing_demo_post_service_only";
  location_status: "not_collected";
  photo_status: "not_collected";
  data_status: "simulated";
  quality_status: "simulated_unverified";
  evidence_claim_status: "simulated_unverified_no_field_completion_claim";
  operational_approval_satisfied: false;
  authorizes_field_work: false;
  eligible_for_field_execution: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
}

export interface PreparedMowingRehearsalSummary {
  mowing_order_id: string;
  road_code: string;
  segment_index: number;
  zone_type: "left" | "right" | "median" | "special";
  rehearsal_state: MowingRehearsalState;
  event_count: number;
  pause_count: number;
  started_at: string | null;
  finished_at: string | null;
  recorded_span_seconds: number | null;
  completion_claim_status: "rehearsal_only_no_field_completion_claim";
  data_status: "simulated";
  location_status: "simulated";
  operational_approval_satisfied: false;
  authorizes_field_work: false;
  eligible_for_field_execution: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  events: PreparedMowingRehearsalEvent[];
  post_service_measurements: PreparedMowingPostServiceMeasurement[];
}

export interface PreparedMowingRehearsalCollection {
  items: PreparedMowingRehearsalSummary[];
  result_count: number;
  limit: number;
  truncated: boolean;
  warning: "This history contains only a simulated mowing rehearsal and simulated, unverified typed post-service heights. It is not verified vegetation evidence, field execution, mowing efficacy, or official completion.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasSensitiveProjectionField(value: Record<string, unknown>): boolean {
  const sensitiveFragments = ["actor", "device", "latitude", "longitude", "server_received"];
  return Object.keys(value).some((key) =>
    sensitiveFragments.some((fragment) => key.toLowerCase().includes(fragment)));
}

function timestamp(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isDecimal(value: unknown): value is string | number {
  return (typeof value === "number" && Number.isFinite(value)) ||
    (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)));
}

function isEvent(value: unknown): value is PreparedMowingRehearsalEvent {
  if (!isRecord(value) || hasSensitiveProjectionField(value)) return false;
  const operation = String(value.operation);
  const expectedLocation = operation === "start" ? "simulated" : "not_collected";
  return typeof value.event_id === "string" &&
    Number.isInteger(value.event_sequence) && Number(value.event_sequence) >= 1 &&
    typeof value.source_planning_approval_id === "string" &&
    ["confirm", "start", "pause", "resume", "finish"].includes(operation) &&
    timestamp(value.client_occurred_at) !== null &&
    value.location_status === expectedLocation &&
    value.simulation_scope === "demo_only" &&
    value.rehearsal_scope === "mowing_demo_rehearsal_only" &&
    value.data_status === "simulated" &&
    value.operational_approval_satisfied === false &&
    value.authorizes_field_work === false &&
    value.eligible_for_field_execution === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false;
}

function isMeasurement(value: unknown): value is PreparedMowingPostServiceMeasurement {
  if (!isRecord(value) || hasSensitiveProjectionField(value) || !isDecimal(value.height_cm)) {
    return false;
  }
  const height = Number(value.height_cm);
  return typeof value.event_id === "string" &&
    typeof value.source_planning_approval_id === "string" &&
    typeof value.source_planned_point_id === "string" &&
    [1, 2, 3].includes(Number(value.source_point_sequence)) &&
    Number.isInteger(value.source_point_sequence) && height >= 0 && height <= 1000 &&
    timestamp(value.client_captured_at) !== null && value.phase === "post_service" &&
    value.measurement_scope === "mowing_demo_post_service_only" &&
    value.location_status === "not_collected" && value.photo_status === "not_collected" &&
    value.data_status === "simulated" && value.quality_status === "simulated_unverified" &&
    value.evidence_claim_status === "simulated_unverified_no_field_completion_claim" &&
    value.operational_approval_satisfied === false && value.authorizes_field_work === false &&
    value.eligible_for_field_execution === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false;
}

function derivedMetrics(events: PreparedMowingRehearsalEvent[]) {
  let previous: PreparedMowingRehearsalEvent | undefined;
  let startedAt: string | null = null;
  let finishedAt: string | null = null;
  let pauseCount = 0;
  let planningApprovalId: string | undefined;
  for (const event of events) {
    if (planningApprovalId === undefined) planningApprovalId = event.source_planning_approval_id;
    else if (event.source_planning_approval_id !== planningApprovalId) return null;
    const priorOperation = previous?.operation;
    const valid =
      (event.operation === "confirm" && priorOperation === undefined) ||
      (event.operation === "start" && priorOperation === "confirm") ||
      (event.operation === "pause" && ["start", "resume"].includes(String(priorOperation))) ||
      (event.operation === "resume" && priorOperation === "pause") ||
      (event.operation === "finish" && ["start", "resume"].includes(String(priorOperation)));
    const eventTime = timestamp(event.client_occurred_at);
    const previousTime = previous ? timestamp(previous.client_occurred_at) : null;
    if (!valid || eventTime === null ||
      (previous !== undefined && (event.event_sequence <= previous.event_sequence ||
        previousTime === null || eventTime < previousTime))) return null;
    if (event.operation === "start") startedAt = event.client_occurred_at;
    if (event.operation === "pause") pauseCount += 1;
    if (event.operation === "finish") finishedAt = event.client_occurred_at;
    previous = event;
  }
  const state: MowingRehearsalState = previous === undefined ? "not_started"
    : previous.operation === "confirm" ? "confirmed"
    : previous.operation === "pause" ? "paused"
    : previous.operation === "finish" ? "finished" : "in_progress";
  const startMilliseconds = timestamp(startedAt);
  const lastMilliseconds = previous ? timestamp(previous.client_occurred_at) : null;
  return {
    state,
    eventCount: events.length,
    pauseCount,
    startedAt,
    finishedAt,
    recordedSpanSeconds: startMilliseconds === null || lastMilliseconds === null
      ? null : (lastMilliseconds - startMilliseconds) / 1000,
  };
}

function isSummary(value: unknown): value is PreparedMowingRehearsalSummary {
  if (!isRecord(value) || !Array.isArray(value.events) || !value.events.every(isEvent) ||
    !Array.isArray(value.post_service_measurements) ||
    !value.post_service_measurements.every(isMeasurement)) {
    return false;
  }
  const metrics = derivedMetrics(value.events);
  if (metrics === null) return false;
  const measurements = value.post_service_measurements;
  if (measurements.length > 3) return false;
  const sequences = measurements.map((measurement) => measurement.source_point_sequence);
  const eventIds = measurements.map((measurement) => measurement.event_id);
  const pointIds = measurements.map((measurement) => measurement.source_planned_point_id);
  const planningApprovalIds = new Set(value.events.map((event) => event.source_planning_approval_id));
  const finishedMilliseconds = timestamp(metrics.finishedAt);
  if (sequences.some((sequence, index) => index > 0 && sequence <= sequences[index - 1]!) ||
    new Set(eventIds).size !== eventIds.length || new Set(pointIds).size !== pointIds.length ||
    (measurements.length > 0 && (metrics.state !== "finished" || finishedMilliseconds === null ||
      planningApprovalIds.size !== 1 || measurements.some((measurement) =>
        !planningApprovalIds.has(measurement.source_planning_approval_id) ||
        timestamp(measurement.client_captured_at)! < finishedMilliseconds)))) return false;
  const startedAtMatches = metrics.startedAt === null
    ? value.started_at === null
    : timestamp(value.started_at) === timestamp(metrics.startedAt);
  const finishedAtMatches = metrics.finishedAt === null
    ? value.finished_at === null
    : timestamp(value.finished_at) === timestamp(metrics.finishedAt);
  return typeof value.mowing_order_id === "string" &&
    typeof value.road_code === "string" && Number.isInteger(value.segment_index) &&
    Number(value.segment_index) >= 0 &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    value.rehearsal_state === metrics.state && value.event_count === metrics.eventCount &&
    value.pause_count === metrics.pauseCount && startedAtMatches && finishedAtMatches &&
    value.recorded_span_seconds === metrics.recordedSpanSeconds &&
    value.completion_claim_status === "rehearsal_only_no_field_completion_claim" &&
    value.data_status === "simulated" && value.location_status === "simulated" &&
    value.operational_approval_satisfied === false && value.authorizes_field_work === false &&
    value.eligible_for_field_execution === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false;
}

export function isPreparedMowingRehearsalCollection(
  value: unknown,
): value is PreparedMowingRehearsalCollection {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(isSummary) &&
    value.result_count === value.items.length && Number.isInteger(value.limit) &&
    Number(value.limit) >= 1 && Number(value.limit) <= 100 &&
    typeof value.truncated === "boolean" &&
    value.warning === "This history contains only a simulated mowing rehearsal and simulated, unverified typed post-service heights. It is not verified vegetation evidence, field execution, mowing efficacy, or official completion.";
}
