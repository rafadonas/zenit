import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zenit_mobile/data/zenit_gateway.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';

import 'support/fakes.dart';

void main() {
  test(
    'login uses OAuth form fields and creates an expiring session',
    () async {
      final gateway = HttpZenitGateway(
        baseUrl: 'https://api.example.test',
        clock: () => DateTime.utc(2026, 8, 9),
        client: MockClient((request) async {
          expect(request.url.path, '/v1/auth/token');
          expect(request.bodyFields, {
            'username': 'field@example.test',
            'password': 'secret',
          });
          return http.Response(
            jsonEncode({
              'access_token': 'signed-token',
              'expires_in': 900,
              'user': {
                'id': '33333333-3333-4333-8333-333333333333',
                'email': 'field@example.test',
                'display_name': 'Field User',
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      final session = await gateway.login(' field@example.test ', 'secret');

      expect(session.accessToken, 'signed-token');
      expect(session.expiresAt, DateTime.utc(2026, 8, 9, 0, 15));
    },
  );

  test('downloads prepared orders with bearer authentication', () async {
    final gateway = HttpZenitGateway(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.url.path, '/v1/work-orders');
        expect(request.url.queryParameters['limit'], '100');
        expect(request.headers['Authorization'], 'Bearer signed-token');
        return http.Response(
          jsonEncode({
            'items': [preparedOrderJson()],
          }),
          200,
        );
      }),
    );

    final orders = await gateway.listPreparedOrders('signed-token');

    expect(orders, hasLength(1));
    expect(orders.single.points, hasLength(3));
  });

  test(
    'registers device and receives persistent batch acknowledgements',
    () async {
      var call = 0;
      final gateway = HttpZenitGateway(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          call++;
          expect(request.headers['Authorization'], 'Bearer signed-token');
          final body = jsonDecode(request.body) as Map<String, Object?>;
          if (call == 1) {
            expect(request.url.path, '/v1/mobile/devices');
            expect(body['device_id'], '44444444-4444-4444-8444-444444444444');
            return http.Response(
              jsonEncode({
                'device_id': '44444444-4444-4444-8444-444444444444',
                'platform': 'android',
                'registered_app_version': '1.0.0+1',
                'registered_at': '2026-08-09T17:00:00Z',
                'registration_status': 'active',
                'data_status': 'prepared',
                'authorizes_field_work': false,
              }),
              200,
            );
          }
          expect(request.url.path, '/v1/sync/batch');
          expect((body['events']! as List<Object?>), hasLength(1));
          return http.Response(
            jsonEncode({
              'batch_id': '55555555-5555-4555-8555-555555555555',
              'accepted': [
                {
                  'event_id': '66666666-6666-4666-8666-666666666666',
                  'persisted': true,
                },
              ],
              'rejected': [],
              'conflicts': [],
              'next_sync_cursor': 7,
              'data_status': 'prepared',
              'authorizes_field_work': false,
              'eligible_for_official_reporting': false,
            }),
            200,
          );
        }),
      );
      const deviceId = '44444444-4444-4444-8444-444444444444';
      const eventId = '66666666-6666-4666-8666-666666666666';
      final draft = MeasurementDraft(
        eventId: eventId,
        orderId: '11111111-1111-4111-8111-111111111111',
        plannedPointId: '22222222-2222-4222-8222-222222222221',
        sequence: 1,
        heightCm: 0,
        recordedAt: DateTime.utc(2026, 8, 9, 17),
        syncState: DraftSyncState.pending,
      );
      const batch = PendingSyncBatch(
        batchId: '55555555-5555-4555-8555-555555555555',
        deviceId: deviceId,
        orderId: '11111111-1111-4111-8111-111111111111',
        baseSyncCursor: 6,
        eventIds: [eventId],
      );

      await gateway.registerDevice('signed-token', deviceId, '1.0.0+1');
      final result = await gateway.syncBatch('signed-token', batch, [
        draft.toSyncEventJson(),
      ]);

      expect(result.acceptedEventIds, {eventId});
      expect(result.nextSyncCursor, 7);
      expect(call, 2);
    },
  );
}
