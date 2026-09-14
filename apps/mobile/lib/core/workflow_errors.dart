part of '../app_controller.dart';

sealed class MobileWorkflowException implements Exception {
  const MobileWorkflowException(this.message);
  final String message;
}

class LocalPendingEventsError extends MobileWorkflowException {
  const LocalPendingEventsError()
    : super('Há eventos não confirmados de outro usuário neste aparelho.');
}

class PendingBatchEditError extends MobileWorkflowException {
  const PendingBatchEditError()
    : super('Um lote já foi preparado; sincronize-o antes de editar.');
}

class PersistedDraftEditError extends MobileWorkflowException {
  const PersistedDraftEditError()
    : super(
        'A medição já recebeu resultado persistente e não pode ser sobrescrita.',
      );
}

class IncompleteDraftBatchError extends MobileWorkflowException {
  const IncompleteDraftBatchError()
    : super('Salve exatamente três medições antes de sincronizar.');
}

class AnotherOrderPendingError extends MobileWorkflowException {
  const AnotherOrderPendingError()
    : super('Existe um lote pendente de outra ordem neste aparelho.');
}

class CorruptedPendingBatchError extends MobileWorkflowException {
  const CorruptedPendingBatchError()
    : super('O lote pendente não corresponde às medições locais.');
}

class InvalidDemoLifecycleError extends MobileWorkflowException {
  const InvalidDemoLifecycleError()
    : super(
        'A sequência demonstrativa deve ser confirmar, iniciar e finalizar.',
      );
}

class DemoOrderNotStartedError extends MobileWorkflowException {
  const DemoOrderNotStartedError()
    : super('Confirme e inicie a demonstração antes das medições.');
}

class IncompleteDemoLifecycleError extends MobileWorkflowException {
  const IncompleteDemoLifecycleError()
    : super('Finalize a demonstração antes de sincronizar.');
}

class PersistedPhotoEditError extends MobileWorkflowException {
  const PersistedPhotoEditError()
    : super(
        'O manifesto da foto já foi persistido e não pode ser substituído.',
      );
}

class PhotoCaptureCancelledError extends MobileWorkflowException {
  const PhotoCaptureCancelledError() : super('Captura de foto cancelada.');
}

class IncompletePhotoBatchError extends MobileWorkflowException {
  const IncompletePhotoBatchError()
    : super('Capture uma foto preparada em cada um dos três pontos.');
}

class MowingDemoNotEligibleError extends MobileWorkflowException {
  const MowingDemoNotEligibleError()
    : super(
        'O ensaio exige planejamento efetivo e declarações preparadas de clima e segurança livres.',
      );
}

class MowingDemoSourcePointError extends MobileWorkflowException {
  const MowingDemoSourcePointError()
    : super(
        'O ponto estimado da inspeção de origem não está disponível neste aparelho.',
      );
}

class InvalidMowingDemoLifecycleError extends MobileWorkflowException {
  const InvalidMowingDemoLifecycleError()
    : super(
        'Use confirmar, iniciar, pausar/retomar em pares e finalizar o ensaio.',
      );
}

class IncompleteMowingDemoLifecycleError extends MobileWorkflowException {
  const IncompleteMowingDemoLifecycleError()
    : super('Finalize uma sequência válida antes de sincronizar o ensaio.');
}

class PersistedMowingDemoEditError extends MobileWorkflowException {
  const PersistedMowingDemoEditError()
    : super('Um evento do ensaio já tem resultado persistente e é imutável.');
}

class InvalidMowingDemoTimeError extends MobileWorkflowException {
  const InvalidMowingDemoTimeError()
    : super('O relógio do aparelho retrocedeu durante o ensaio.');
}

class MowingPostServiceNotReadyError extends MobileWorkflowException {
  const MowingPostServiceNotReadyError()
    : super(
        'Finalize um ensaio local válido ou confirmado antes das medições pós-serviço.',
      );
}

class IncompleteMowingPostServiceMeasurementError
    extends MobileWorkflowException {
  const IncompleteMowingPostServiceMeasurementError()
    : super(
        'Salve uma medição pós-serviço simulada para cada um dos três pontos.',
      );
}

class PersistedMowingPostServiceMeasurementEditError
    extends MobileWorkflowException {
  const PersistedMowingPostServiceMeasurementEditError()
    : super('A medição pós-serviço já tem resultado persistente e é imutável.');
}

class InvalidMowingPostServiceMeasurementTimeError
    extends MobileWorkflowException {
  const InvalidMowingPostServiceMeasurementTimeError()
    : super('A medição pós-serviço não pode ser anterior ao fim do ensaio.');
}

class MowingPostServicePhotoNotReadyError extends MobileWorkflowException {
  const MowingPostServicePhotoNotReadyError()
    : super(
        'Salve a medição simulada do ponto antes de capturar sua foto pós-serviço.',
      );
}

class IncompleteMowingPostServicePhotoError extends MobileWorkflowException {
  const IncompleteMowingPostServicePhotoError()
    : super(
        'Capture uma foto pós-serviço simulada para cada um dos três pontos.',
      );
}

class PersistedMowingPostServicePhotoEditError extends MobileWorkflowException {
  const PersistedMowingPostServicePhotoEditError()
    : super('O manifesto da foto pós-serviço já tem resultado persistente.');
}

class InvalidMowingPostServicePhotoTimeError extends MobileWorkflowException {
  const InvalidMowingPostServicePhotoTimeError()
    : super('A foto pós-serviço não pode ser anterior à medição do ponto.');
}

class MowingPostServiceMeasurementHasPhotoError
    extends MobileWorkflowException {
  const MowingPostServiceMeasurementHasPhotoError()
    : super(
        'Remova ou conclua as fotos antes de alterar as medições vinculadas.',
      );
}
