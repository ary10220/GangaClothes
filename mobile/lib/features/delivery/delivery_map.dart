import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../app/theme.dart';

/// Santa Cruz de la Sierra: el centro por defecto cuando aún no hay puntos
/// (el mismo que usa el mapa de la web).
const LatLng deliveryMapDefaultCenter = LatLng(-17.7833, -63.1821);

/// Mapa OpenStreetMap para elegir dónde recibir la compra, igual que en la
/// web: se toca el mapa para marcar el destino y, cuando hay cotización, se
/// dibuja la sucursal de origen y la línea entre ambos.
class DeliveryMap extends StatefulWidget {
  const DeliveryMap({
    required this.onPick,
    this.destination,
    this.origin,
    this.originName,
    this.height = 280,
    this.enabled = true,
    this.hint = 'Toca el mapa para marcar dónde quieres recibir tu compra',
    super.key,
  });

  final ValueChanged<LatLng> onPick;
  final LatLng? destination;
  final LatLng? origin;
  final String? originName;
  final double height;
  final bool enabled;
  final String hint;

  @override
  State<DeliveryMap> createState() => _DeliveryMapState();
}

class _DeliveryMapState extends State<DeliveryMap> {
  final _controller = MapController();
  String _framed = '';

  @override
  void didUpdateWidget(DeliveryMap old) {
    super.didUpdateWidget(old);
    // Se reencuadra solo cuando aparece o cambia el origen: mientras el
    // cliente mueve su punto, la vista se queda quieta.
    final origin = widget.origin;
    final signature = origin == null
        ? ''
        : '${origin.latitude.toStringAsFixed(4)},${origin.longitude.toStringAsFixed(4)}';
    if (signature.isNotEmpty && signature != _framed) {
      _framed = signature;
      WidgetsBinding.instance.addPostFrameCallback((_) => _fit());
    }
  }

  void _fit() {
    final origin = widget.origin;
    final destination = widget.destination;
    if (!mounted || origin == null) return;
    if (destination == null) {
      _controller.move(origin, 14);
      return;
    }
    _controller.fitCamera(
      CameraFit.bounds(
        bounds: LatLngBounds.fromPoints([origin, destination]),
        padding: const EdgeInsets.all(40),
        maxZoom: 16,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final destination = widget.destination;
    final origin = widget.origin;
    return ClipRRect(
      borderRadius: BorderRadius.circular(13),
      child: SizedBox(
        height: widget.height,
        child: Stack(
          children: [
            FlutterMap(
              mapController: _controller,
              options: MapOptions(
                initialCenter: destination ?? deliveryMapDefaultCenter,
                initialZoom: destination == null ? 13 : 15,
                interactionOptions: const InteractionOptions(
                  flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
                ),
                onTap: widget.enabled
                    ? (_, point) => widget.onPick(point)
                    : null,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.example.mobile',
                  maxZoom: 19,
                ),
                if (origin != null && destination != null)
                  PolylineLayer(
                    polylines: [
                      Polyline(
                        points: [origin, destination],
                        color: GangaColors.brand.withValues(alpha: .8),
                        strokeWidth: 3,
                        pattern: const StrokePattern.dotted(spacingFactor: 2),
                      ),
                    ],
                  ),
                MarkerLayer(
                  markers: [
                    if (origin != null)
                      Marker(
                        point: origin,
                        width: 30,
                        height: 34,
                        alignment: Alignment.topCenter,
                        child: _Pin(
                          letter: 'T',
                          color: GangaColors.ink,
                          tooltip: widget.originName ?? 'Sucursal',
                        ),
                      ),
                    if (destination != null)
                      Marker(
                        point: destination,
                        width: 30,
                        height: 34,
                        alignment: Alignment.topCenter,
                        child: const _Pin(
                          letter: 'D',
                          color: GangaColors.brand,
                          tooltip: 'Tu entrega',
                        ),
                      ),
                  ],
                ),
                const SimpleAttributionWidget(
                  source: Text('© OpenStreetMap'),
                  backgroundColor: Colors.white70,
                ),
              ],
            ),
            Positioned(
              left: 10,
              right: 10,
              bottom: 10,
              child: IgnorePointer(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 7,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFF14161A).withValues(alpha: .82),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Text(
                    destination == null
                        ? widget.hint
                        : 'Ubicación marcada: ${destination.latitude.toStringAsFixed(5)}, ${destination.longitude.toStringAsFixed(5)}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white, fontSize: 11.5),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Marcador con la misma forma de "gota" que usa la web.
class _Pin extends StatelessWidget {
  const _Pin({
    required this.letter,
    required this.color,
    required this.tooltip,
  });

  final String letter;
  final Color color;
  final String tooltip;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: tooltip,
    child: Transform.rotate(
      angle: -0.785398,
      child: Container(
        width: 26,
        height: 26,
        decoration: BoxDecoration(
          color: color,
          border: Border.all(color: Colors.white, width: 2),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(13),
            topRight: Radius.circular(13),
            bottomRight: Radius.circular(13),
            bottomLeft: Radius.circular(4),
          ),
          boxShadow: const [
            BoxShadow(
              color: Colors.black38,
              blurRadius: 6,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Transform.rotate(
          angle: 0.785398,
          child: Center(
            child: Text(
              letter,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
