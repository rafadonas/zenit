import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/prepared_work_order.dart';

import 'support/fakes.dart';

void main() {
  test('accepts exactly three ordered non-operational prepared points', () {
    final order = PreparedWorkOrder.fromJson(preparedOrderJson());

    expect(order.points.map((point) => point.sequence), [1, 2, 3]);
    expect(order.authorizesFieldWork, isFalse);
    expect(order.eligibleForFieldExecution, isFalse);
    expect(PreparedWorkOrder.fromJson(order.toJson()).id, order.id);
  });

  test('rejects an API payload that claims field authorization', () {
    final payload = preparedOrderJson()..['authorizes_field_work'] = true;
    expect(() => PreparedWorkOrder.fromJson(payload), throwsFormatException);
  });

  test('rejects missing or unordered planned points', () {
    final payload = preparedOrderJson();
    final points = payload['planned_points']! as List<Map<String, Object?>>;
    points[1]['sequence'] = 3;
    expect(() => PreparedWorkOrder.fromJson(payload), throwsFormatException);
  });
}
