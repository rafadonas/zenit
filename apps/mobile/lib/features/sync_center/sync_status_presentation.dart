import 'package:flutter/material.dart';

import '../../domain/measurement_draft.dart';

String syncStateLabel(DraftSyncState state) => switch (state) {
  DraftSyncState.localOnly => 'somente local',
  DraftSyncState.pending => 'aguardando confirmação',
  DraftSyncState.acknowledged => 'persistido no servidor',
  DraftSyncState.rejected => 'rejeitado pelo servidor',
  DraftSyncState.conflict => 'conflito preservado',
};

IconData syncStateIcon(DraftSyncState state) => switch (state) {
  DraftSyncState.localOnly => Icons.phone_android,
  DraftSyncState.pending => Icons.sync,
  DraftSyncState.acknowledged => Icons.cloud_done,
  DraftSyncState.rejected => Icons.cloud_off,
  DraftSyncState.conflict => Icons.warning_amber,
};
