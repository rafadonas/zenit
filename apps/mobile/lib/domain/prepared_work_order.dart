typedef JsonMap = Map<String, Object?>;

class PlannedInspectionPoint {
  const PlannedInspectionPoint({
    required this.id,
    required this.sequence,
    required this.positionFraction,
    required this.longitude,
    required this.latitude,
    required this.dataStatus,
  });

  final String id;
  final int sequence;
  final double positionFraction;
  final double longitude;
  final double latitude;
  final String dataStatus;

  factory PlannedInspectionPoint.fromJson(JsonMap json) {
    if (json['eligible_for_field_execution'] != false ||
        json['geometry_srid'] != 4326 ||
        json['planning_method'] != 'segment_centerline_fraction') {
      throw const FormatException(
        'Point is not a non-operational prepared point',
      );
    }
    return PlannedInspectionPoint(
      id: json['planned_point_id']! as String,
      sequence: json['sequence']! as int,
      positionFraction: (json['position_fraction']! as num).toDouble(),
      longitude: (json['longitude']! as num).toDouble(),
      latitude: (json['latitude']! as num).toDouble(),
      dataStatus: json['data_status']! as String,
    );
  }

  JsonMap toJson() => {
    'planned_point_id': id,
    'sequence': sequence,
    'position_fraction': positionFraction,
    'longitude': longitude,
    'latitude': latitude,
    'geometry_srid': 4326,
    'planning_method': 'segment_centerline_fraction',
    'data_status': dataStatus,
    'eligible_for_field_execution': false,
  };
}

class PreparedWorkOrder {
  const PreparedWorkOrder({
    required this.id,
    required this.roadCode,
    required this.segmentIndex,
    required this.zoneType,
    required this.planningRationale,
    required this.createdAt,
    required this.points,
  });

  final String id;
  final String roadCode;
  final int segmentIndex;
  final String zoneType;
  final String planningRationale;
  final DateTime createdAt;
  final List<PlannedInspectionPoint> points;

  bool get authorizesFieldWork => false;
  bool get eligibleForFieldExecution => false;

  factory PreparedWorkOrder.fromJson(JsonMap json) {
    if (json['status'] != 'prepared' ||
        json['order_type'] != 'inspection' ||
        json['order_data_status'] != 'prepared' ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_field_execution'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException(
        'Order is not an eligible prepared inspection order',
      );
    }

    final rawPoints = json['planned_points']! as List<Object?>;
    final points = rawPoints
        .map(
          (point) => PlannedInspectionPoint.fromJson(
            (point! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
    if (points.length != 3 ||
        points[0].sequence != 1 ||
        points[1].sequence != 2 ||
        points[2].sequence != 3) {
      throw const FormatException(
        'Prepared order must have exactly three ordered points',
      );
    }

    return PreparedWorkOrder(
      id: json['work_order_id']! as String,
      roadCode: json['road_code']! as String,
      segmentIndex: json['segment_index']! as int,
      zoneType: json['zone_type']! as String,
      planningRationale: json['planning_rationale']! as String,
      createdAt: DateTime.parse(json['created_at']! as String).toUtc(),
      points: points,
    );
  }

  JsonMap toJson() => {
    'work_order_id': id,
    'road_code': roadCode,
    'segment_index': segmentIndex,
    'zone_type': zoneType,
    'planning_rationale': planningRationale,
    'created_at': createdAt.toUtc().toIso8601String(),
    'status': 'prepared',
    'order_type': 'inspection',
    'order_data_status': 'prepared',
    'authorizes_field_work': false,
    'eligible_for_field_execution': false,
    'eligible_for_official_reporting': false,
    'planned_points': points.map((point) => point.toJson()).toList(),
  };
}
