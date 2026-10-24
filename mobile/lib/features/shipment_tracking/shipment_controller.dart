import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'shipment_models.dart';
import 'shipment_service.dart';

class ShipmentTrackingController extends ChangeNotifier {
  ShipmentTrackingController({
    required this.api,
    this.pollInterval = const Duration(seconds: 15),
  });

  final ShipmentDataSource api;
  final Duration pollInterval;

  List<Shipment> shipments = const [];
  ApiError? error;
  bool loading = false;

  Timer? _pollTimer;
  bool _requestInFlight = false;
  bool _disposed = false;

  bool get polling => _pollTimer != null;

  bool get hasActiveShipments =>
      shipments.any((shipment) => shipment.active && !shipment.isTerminal);

  Future<void> load() => _fetch(showLoading: true);

  Future<void> poll() => _fetch(showLoading: false);

  Future<void> _fetch({required bool showLoading}) async {
    if (_disposed || _requestInFlight) return;
    _requestInFlight = true;
    if (showLoading) {
      loading = true;
      error = null;
      _notify();
    }
    try {
      final fetched = await api.fetchShipments();
      if (_disposed) return;
      shipments = List<Shipment>.unmodifiable(fetched);
      loading = false;
      error = null;
      _syncPolling();
      _notify();
    } catch (caught) {
      if (_disposed) return;
      loading = false;
      // A failed poll keeps the last known server state and the timer alive;
      // the next tick or a manual retry can recover without a write request.
      error = _asApiError(caught);
      _syncPolling();
      _notify();
    } finally {
      _requestInFlight = false;
    }
  }

  void _syncPolling() {
    if (_disposed || !hasActiveShipments) {
      _pollTimer?.cancel();
      _pollTimer = null;
      return;
    }
    if (_pollTimer != null) return;
    _pollTimer = Timer.periodic(pollInterval, (_) => unawaited(poll()));
  }

  void _notify() {
    if (!_disposed && hasListeners) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _pollTimer?.cancel();
    _pollTimer = null;
    super.dispose();
  }
}

ApiError _asApiError(Object error) {
  if (error is ApiError) return error;
  return ApiError(
    statusCode: 0,
    message: 'No se pudo cargar el seguimiento.',
    cause: error,
  );
}
