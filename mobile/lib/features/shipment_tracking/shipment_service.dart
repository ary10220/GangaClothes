import '../../core/network/api_client.dart';
import 'shipment_models.dart';

abstract interface class ShipmentDataSource {
  Future<List<Shipment>> fetchShipments();
}

class ShipmentService implements ShipmentDataSource {
  const ShipmentService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<List<Shipment>> fetchShipments() async {
    final response = await apiClient.request<Object?>('/envios/mios');
    if (response.data is! List) {
      throw const FormatException('Shipment response is not a list');
    }
    return (response.data as List)
        .whereType<Map>()
        .map((item) => Shipment.fromJson(Map<String, dynamic>.from(item)))
        // The endpoint contract is paid-only. Keep the mobile screen from
        // treating a malformed or stale unpaid response as trackable.
        .where((shipment) => shipment.sale?.isPaid == true)
        .toList(growable: false);
  }
}
