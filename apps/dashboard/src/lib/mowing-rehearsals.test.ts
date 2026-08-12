import { describe, expect, it } from "vitest";

import { isPreparedMowingRehearsalCollection } from "./mowing-rehearsals";

function event(operation: string, sequence: number, seconds: number) {
  return {
    event_id: `event-${sequence}`,
    event_sequence: sequence,
    source_planning_approval_id: "approval-1",
    operation,
    client_occurred_at: new Date(Date.UTC(2026, 7, 11, 20, 0, seconds)).toISOString(),
    location_status: operation === "start" ? "simulated" : "not_collected",
    simulation_scope: "demo_only",
    rehearsal_scope: "mowing_demo_rehearsal_only",
    data_status: "simulated",
    operational_approval_satisfied: false,
    authorizes_field_work: false,
    eligible_for_field_execution: false,
    eligible_for_model_training: false,
    eligible_for_official_reporting: false,
  };
}

function measurement(sequence = 1) {
  return {
    event_id: `measurement-${sequence}`,
    source_planning_approval_id: "approval-1",
    source_planned_point_id: `point-${sequence}`,
    source_point_sequence: sequence,
    phase: "post_service",
    height_cm: "7.50",
    client_captured_at: new Date(Date.UTC(2026, 7, 11, 20, 1, 0)).toISOString(),
    measurement_scope: "mowing_demo_post_service_only",
    location_status: "not_collected",
    photo_status: "not_collected",
    data_status: "simulated",
    quality_status: "simulated_unverified",
    evidence_claim_status: "simulated_unverified_no_field_completion_claim",
    operational_approval_satisfied: false,
    authorizes_field_work: false,
    eligible_for_field_execution: false,
    eligible_for_model_training: false,
    eligible_for_official_reporting: false,
  };
}

function collection() {
  const events = [
    event("confirm", 10, 0),
    event("start", 11, 5),
    event("pause", 12, 20),
    event("resume", 13, 30),
    event("finish", 14, 50),
  ];
  return {
    items: [{
      mowing_order_id: "mowing-1",
      road_code: "SP-021",
      segment_index: 195,
      zone_type: "left",
      rehearsal_state: "finished",
      event_count: 5,
      pause_count: 1,
      started_at: events[1]?.client_occurred_at,
      finished_at: events[4]?.client_occurred_at,
      recorded_span_seconds: 45,
      completion_claim_status: "rehearsal_only_no_field_completion_claim",
      data_status: "simulated",
      location_status: "simulated",
      operational_approval_satisfied: false,
      authorizes_field_work: false,
      eligible_for_field_execution: false,
      eligible_for_model_training: false,
      eligible_for_official_reporting: false,
      events,
      post_service_measurements: [measurement()],
    }],
    result_count: 1,
    limit: 50,
    truncated: false,
    warning: "This history contains only a simulated mowing rehearsal and simulated, unverified typed post-service heights. It is not verified vegetation evidence, field execution, mowing efficacy, or official completion.",
  };
}

describe("prepared mowing rehearsal history safety contract", () => {
  it("accepts a coherent finished append-only timeline", () => {
    expect(isPreparedMowingRehearsalCollection(collection())).toBe(true);
  });

  it("rejects operational promotion and derived-state mismatches", () => {
    const promoted = collection();
    promoted.items[0]!.authorizes_field_work = true;
    expect(isPreparedMowingRehearsalCollection(promoted)).toBe(false);

    const mismatched = collection();
    mismatched.items[0]!.rehearsal_state = "in_progress";
    expect(isPreparedMowingRehearsalCollection(mismatched)).toBe(false);
  });

  it("rejects invalid sequencing and real-location claims", () => {
    const invalid = collection();
    invalid.items[0]!.events[2]!.operation = "finish";
    expect(isPreparedMowingRehearsalCollection(invalid)).toBe(false);

    const location = collection();
    location.items[0]!.events[1]!.location_status = "not_collected";
    expect(isPreparedMowingRehearsalCollection(location)).toBe(false);
  });

  it("rejects promoted or inconsistent post-service measurements", () => {
    const promoted = collection();
    promoted.items[0]!.post_service_measurements[0]!.eligible_for_official_reporting = true;
    expect(isPreparedMowingRehearsalCollection(promoted)).toBe(false);

    const predated = collection();
    predated.items[0]!.post_service_measurements[0]!.client_captured_at =
      new Date(Date.UTC(2026, 7, 11, 20, 0, 40)).toISOString();
    expect(isPreparedMowingRehearsalCollection(predated)).toBe(false);

    const mismatchedApproval = collection();
    mismatchedApproval.items[0]!.post_service_measurements[0]!.source_planning_approval_id =
      "approval-2";
    expect(isPreparedMowingRehearsalCollection(mismatchedApproval)).toBe(false);

    const identityLeak = collection();
    Object.assign(identityLeak.items[0]!.post_service_measurements[0]!, {
      device_id: "device-1",
    });
    expect(isPreparedMowingRehearsalCollection(identityLeak)).toBe(false);
  });
});
