import 'prepared_work_order.dart';

class PreparedMowingPlan {
  const PreparedMowingPlan({
    required this.id,
    required this.proposalId,
    required this.sourceReviewId,
    required this.sourceInspectionWorkOrderId,
    required this.roadCode,
    required this.segmentIndex,
    required this.zoneType,
    required this.sourceReviewState,
    required this.planningRationale,
    required this.creationPolicyVersion,
    required this.createdAt,
    required this.resourcePlanCount,
    required this.resourcePlanId,
    required this.teamReference,
    required this.equipmentReference,
    required this.resourcePlanRationale,
    required this.resourcePlanCreatedAt,
    required this.readinessAssessmentCount,
    required this.readinessAssessmentId,
    required this.readinessResourcePlanId,
    required this.weatherResult,
    required this.weatherSourceReference,
    required this.safetyResult,
    required this.safetySourceReference,
    required this.readinessRationale,
    required this.readinessAssessedAt,
    required this.planningApprovalCount,
    required this.planningApprovalId,
    required this.planningApprovalReadinessId,
    required this.planningDecision,
    required this.planningDecisionRationale,
    required this.planningDecidedAt,
  });

  final String id;
  final String proposalId;
  final String sourceReviewId;
  final String sourceInspectionWorkOrderId;
  final String roadCode;
  final int segmentIndex;
  final String zoneType;
  final String sourceReviewState;
  final String planningRationale;
  final String creationPolicyVersion;
  final DateTime createdAt;
  final int resourcePlanCount;
  final String? resourcePlanId;
  final String? teamReference;
  final String? equipmentReference;
  final String? resourcePlanRationale;
  final DateTime? resourcePlanCreatedAt;
  final int readinessAssessmentCount;
  final String? readinessAssessmentId;
  final String? readinessResourcePlanId;
  final String? weatherResult;
  final String? weatherSourceReference;
  final String? safetyResult;
  final String? safetySourceReference;
  final String? readinessRationale;
  final DateTime? readinessAssessedAt;
  final int planningApprovalCount;
  final String? planningApprovalId;
  final String? planningApprovalReadinessId;
  final String? planningDecision;
  final String? planningDecisionRationale;
  final DateTime? planningDecidedAt;

  bool get canConfirm => false;
  bool get canStart => false;
  bool get canTrack => false;
  bool get canFinish => false;
  bool get operationalApprovalSatisfied => false;

  factory PreparedMowingPlan.fromJson(JsonMap json) {
    if (json['creation_recommendation'] != 'mowing_review' ||
        json['order_type'] != 'mowing' ||
        json['status'] != 'prepared' ||
        json['version'] != 1 ||
        json['data_status'] != 'prepared' ||
        json['location_status'] != 'simulated' ||
        json['source_evidence_status'] != 'prepared_reviewed_non_operational' ||
        json['team_assignment_status'] != 'unassigned' ||
        json['equipment_assignment_status'] != 'unassigned' ||
        json['weather_check_status'] != 'pending' ||
        json['safety_check_status'] != 'pending' ||
        json['requires_operational_approval'] != true ||
        json['operational_approval_satisfied'] != false ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_field_execution'] != false ||
        json['eligible_for_model_training'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException(
        'Mowing plan is not a non-operational prepared snapshot',
      );
    }
    final zoneType = json['zone_type']! as String;
    final sourceReviewState = json['source_review_state']! as String;
    if (!const {'left', 'right', 'median', 'special'}.contains(zoneType) ||
        !const {'effective', 'superseded'}.contains(sourceReviewState)) {
      throw const FormatException('Mowing plan has invalid domain state');
    }

    final resourcePlanCount = json['resource_plan_count']! as int;
    final resourcePlanId = json['latest_resource_plan_id'] as String?;
    final resourceMetadata = [
      resourcePlanId,
      json['latest_team_reference'],
      json['latest_equipment_reference'],
      json['latest_resource_plan_rationale'],
      json['latest_resource_plan_created_at'],
    ];
    if (resourcePlanCount < 0 ||
        (resourcePlanCount == 0 &&
            (json['resource_plan_state'] != 'not_planned' ||
                resourceMetadata.any((value) => value != null))) ||
        (resourcePlanCount > 0 &&
            (json['resource_plan_state'] !=
                    'candidate_resources_pending_validation' ||
                resourceMetadata.any((value) => value is! String)))) {
      throw const FormatException('Mowing plan has invalid resource metadata');
    }

    final readinessAssessmentCount = json['readiness_assessment_count']! as int;
    final readinessAssessmentId =
        json['latest_readiness_assessment_id'] as String?;
    final readinessResourcePlanId =
        json['latest_readiness_resource_plan_id'] as String?;
    final weatherResult = json['latest_weather_result'] as String?;
    final safetyResult = json['latest_safety_result'] as String?;
    final readinessMetadata = [
      readinessAssessmentId,
      readinessResourcePlanId,
      json['latest_weather_source_reference'],
      json['latest_safety_source_reference'],
      json['latest_readiness_rationale'],
      json['latest_readiness_assessed_at'],
    ];
    const readinessResults = {'clear', 'blocked', 'inconclusive'};
    if (readinessAssessmentCount < 0 ||
        (readinessAssessmentCount == 0 &&
            (readinessMetadata.any((value) => value != null) ||
                weatherResult != null ||
                safetyResult != null)) ||
        (readinessAssessmentCount > 0 &&
            (readinessMetadata.any((value) => value is! String) ||
                readinessResourcePlanId != resourcePlanId ||
                !readinessResults.contains(weatherResult) ||
                !readinessResults.contains(safetyResult)))) {
      throw const FormatException('Mowing plan has invalid readiness metadata');
    }

    final planningApprovalCount = json['planning_approval_count']! as int;
    final planningApprovalId = json['latest_planning_approval_id'] as String?;
    final planningApprovalReadinessId =
        json['latest_planning_approval_readiness_id'] as String?;
    final planningDecision = json['latest_planning_decision'] as String?;
    final approvalMetadata = [
      planningApprovalId,
      planningApprovalReadinessId,
      json['latest_planning_decision_rationale'],
      json['latest_planning_decided_at'],
    ];
    const planningDecisions = {
      'approved_for_planning',
      'changes_requested',
      'rejected',
    };
    if (planningApprovalCount < 0 ||
        (planningApprovalCount == 0 &&
            (approvalMetadata.any((value) => value != null) ||
                planningDecision != null)) ||
        (planningApprovalCount > 0 &&
            (approvalMetadata.any((value) => value is! String) ||
                planningApprovalReadinessId != readinessAssessmentId ||
                !planningDecisions.contains(planningDecision)))) {
      throw const FormatException('Mowing plan has invalid decision metadata');
    }

    return PreparedMowingPlan(
      id: json['mowing_order_id']! as String,
      proposalId: json['proposal_id']! as String,
      sourceReviewId: json['source_review_id']! as String,
      sourceInspectionWorkOrderId:
          json['source_inspection_work_order_id']! as String,
      roadCode: json['road_code']! as String,
      segmentIndex: json['segment_index']! as int,
      zoneType: zoneType,
      sourceReviewState: sourceReviewState,
      planningRationale: json['planning_rationale']! as String,
      creationPolicyVersion: json['creation_policy_version']! as String,
      createdAt: DateTime.parse(json['created_at']! as String).toUtc(),
      resourcePlanCount: resourcePlanCount,
      resourcePlanId: resourcePlanId,
      teamReference: json['latest_team_reference'] as String?,
      equipmentReference: json['latest_equipment_reference'] as String?,
      resourcePlanRationale: json['latest_resource_plan_rationale'] as String?,
      resourcePlanCreatedAt: _optionalDate(
        json['latest_resource_plan_created_at'],
      ),
      readinessAssessmentCount: readinessAssessmentCount,
      readinessAssessmentId: readinessAssessmentId,
      readinessResourcePlanId: readinessResourcePlanId,
      weatherResult: weatherResult,
      weatherSourceReference:
          json['latest_weather_source_reference'] as String?,
      safetyResult: safetyResult,
      safetySourceReference: json['latest_safety_source_reference'] as String?,
      readinessRationale: json['latest_readiness_rationale'] as String?,
      readinessAssessedAt: _optionalDate(json['latest_readiness_assessed_at']),
      planningApprovalCount: planningApprovalCount,
      planningApprovalId: planningApprovalId,
      planningApprovalReadinessId: planningApprovalReadinessId,
      planningDecision: planningDecision,
      planningDecisionRationale:
          json['latest_planning_decision_rationale'] as String?,
      planningDecidedAt: _optionalDate(json['latest_planning_decided_at']),
    );
  }

  JsonMap toJson() => {
    'mowing_order_id': id,
    'proposal_id': proposalId,
    'source_review_id': sourceReviewId,
    'source_inspection_work_order_id': sourceInspectionWorkOrderId,
    'road_code': roadCode,
    'segment_index': segmentIndex,
    'zone_type': zoneType,
    'creation_recommendation': 'mowing_review',
    'source_review_state': sourceReviewState,
    'order_type': 'mowing',
    'status': 'prepared',
    'version': 1,
    'planning_rationale': planningRationale,
    'creation_policy_version': creationPolicyVersion,
    'data_status': 'prepared',
    'location_status': 'simulated',
    'source_evidence_status': 'prepared_reviewed_non_operational',
    'team_assignment_status': 'unassigned',
    'equipment_assignment_status': 'unassigned',
    'weather_check_status': 'pending',
    'safety_check_status': 'pending',
    'requires_operational_approval': true,
    'operational_approval_satisfied': false,
    'authorizes_field_work': false,
    'eligible_for_field_execution': false,
    'eligible_for_model_training': false,
    'eligible_for_official_reporting': false,
    'created_at': createdAt.toUtc().toIso8601String(),
    'resource_plan_count': resourcePlanCount,
    'latest_resource_plan_id': resourcePlanId,
    'latest_team_reference': teamReference,
    'latest_equipment_reference': equipmentReference,
    'latest_resource_plan_rationale': resourcePlanRationale,
    'latest_resource_plan_created_at': resourcePlanCreatedAt
        ?.toUtc()
        .toIso8601String(),
    'resource_plan_state': resourcePlanId == null
        ? 'not_planned'
        : 'candidate_resources_pending_validation',
    'readiness_assessment_count': readinessAssessmentCount,
    'latest_readiness_assessment_id': readinessAssessmentId,
    'latest_readiness_resource_plan_id': readinessResourcePlanId,
    'latest_weather_result': weatherResult,
    'latest_weather_source_reference': weatherSourceReference,
    'latest_safety_result': safetyResult,
    'latest_safety_source_reference': safetySourceReference,
    'latest_readiness_rationale': readinessRationale,
    'latest_readiness_assessed_at': readinessAssessedAt
        ?.toUtc()
        .toIso8601String(),
    'planning_approval_count': planningApprovalCount,
    'latest_planning_approval_id': planningApprovalId,
    'latest_planning_approval_readiness_id': planningApprovalReadinessId,
    'latest_planning_decision': planningDecision,
    'latest_planning_decision_rationale': planningDecisionRationale,
    'latest_planning_decided_at': planningDecidedAt?.toUtc().toIso8601String(),
  };

  static DateTime? _optionalDate(Object? value) =>
      value == null ? null : DateTime.parse(value as String).toUtc();
}
