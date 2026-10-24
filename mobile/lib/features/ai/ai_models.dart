class AiModelInfo {
  const AiModelInfo({
    required this.mode,
    required this.available,
    this.model,
    this.reason,
  });

  final String mode;
  final bool available;
  final String? model;
  final String? reason;

  bool get isWithoutModel => mode == 'sin_modelo' || !available;

  factory AiModelInfo.fromJson(Object? value) {
    if (value is! Map) {
      return const AiModelInfo(mode: 'sin_modelo', available: false);
    }
    final json = Map<String, dynamic>.from(value);
    final mode = _string(json['modo']) ?? 'sin_modelo';
    return AiModelInfo(
      mode: mode,
      available: json['disponible'] == true && mode != 'sin_modelo',
      model: _string(json['modelo']),
      reason: _string(json['motivo']),
    );
  }
}

class AiRecommenderInfo {
  const AiRecommenderInfo({
    required this.available,
    this.strategy,
    this.reason,
  });

  final bool available;
  final String? strategy;
  final String? reason;

  factory AiRecommenderInfo.fromJson(Object? value) {
    if (value is! Map) return const AiRecommenderInfo(available: false);
    final json = Map<String, dynamic>.from(value);
    return AiRecommenderInfo(
      available: json['disponible'] == true || json['habilitado'] == true,
      strategy: _string(json['estrategia']),
      reason: _string(json['motivo']),
    );
  }
}

class AiStatus {
  const AiStatus({required this.model, required this.recommender});

  final AiModelInfo model;
  final AiRecommenderInfo recommender;

  factory AiStatus.fromJson(Map<String, dynamic> json) => AiStatus(
    model: AiModelInfo.fromJson(json['modelo']),
    recommender: AiRecommenderInfo.fromJson(json['recomendador']),
  );

  static const withoutModel = AiStatus(
    model: AiModelInfo(mode: 'sin_modelo', available: false),
    recommender: AiRecommenderInfo(available: false),
  );
}

class AiPromotion {
  const AiPromotion({this.name, this.label, this.discountType, this.value});

  final String? name;
  final String? label;
  final String? discountType;
  final double? value;

  factory AiPromotion.fromJson(Object? value) {
    if (value is! Map) return const AiPromotion();
    final json = Map<String, dynamic>.from(value);
    return AiPromotion(
      name: _string(json['nombre']),
      label: _string(json['etiqueta']),
      discountType: _string(json['tipo_descuento']),
      value: _number(json['valor']),
    );
  }
}

class AiRecommendationItem {
  const AiRecommendationItem({
    required this.id,
    required this.name,
    this.description,
    this.brand,
    this.salePrice,
    this.finalPrice,
    this.discount,
    this.promotion,
    this.imageUrl,
    this.stock,
    this.score,
    this.reason,
  });

  final int id;
  final String name;
  final String? description;
  final String? brand;
  final double? salePrice;
  final double? finalPrice;
  final double? discount;
  final AiPromotion? promotion;
  final String? imageUrl;
  final int? stock;
  final double? score;
  final String? reason;

  factory AiRecommendationItem.fromJson(Map<String, dynamic> json) =>
      AiRecommendationItem(
        id: _int(json['id'] ?? json['prenda_id']) ?? 0,
        name: _string(json['nombre'] ?? json['prenda']) ?? 'Prenda',
        description: _string(json['descripcion']),
        brand: _string(json['marca']),
        salePrice: _number(json['precio_venta']),
        finalPrice: _number(json['precio_final']),
        discount: _number(json['descuento']),
        promotion: json['promocion'] == null
            ? null
            : AiPromotion.fromJson(json['promocion']),
        imageUrl: _string(json['imagen_url']),
        stock: _int(
          json['disponible_total'] ?? json['stock'] ?? json['disponible'],
        ),
        score: _number(json['puntaje']),
        reason: _string(json['motivo']),
      );
}

class AiRecommendations {
  const AiRecommendations({
    this.strategy,
    this.personalized = false,
    this.usualSize,
    this.items = const [],
  });

  final String? strategy;
  final bool personalized;
  final String? usualSize;
  final List<AiRecommendationItem> items;

  factory AiRecommendations.fromJson(Object? value) {
    final json = value is Map ? Map<String, dynamic>.from(value) : const {};
    final rawItems = json['items'] ?? json['recomendaciones'] ?? value;
    return AiRecommendations(
      strategy: _string(json['estrategia']),
      personalized: json['personalizada'] == true,
      usualSize: _string(json['talla_habitual']),
      items: _maps(
        rawItems,
      ).map(AiRecommendationItem.fromJson).toList(growable: false),
    );
  }
}

class AiChatMessage {
  const AiChatMessage({required this.role, required this.text});

  final String role;
  final String text;

  bool get isUser => role == 'usuario' || role == 'user';

  factory AiChatMessage.fromJson(Map<String, dynamic> json) => AiChatMessage(
    role: _string(json['rol'] ?? json['role']) ?? 'assistant',
    text:
        _string(json['mensaje'] ?? json['contenido'] ?? json['respuesta']) ??
        '',
  );
}

class AiChatResponse {
  const AiChatResponse({
    this.conversationId,
    this.title,
    required this.response,
    this.mode,
    this.queries = const [],
    this.products = const [],
    this.notice,
  });

  final int? conversationId;
  final String? title;
  final String response;
  final String? mode;
  final List<String> queries;
  final List<AiRecommendationItem> products;
  final String? notice;

  factory AiChatResponse.fromJson(Map<String, dynamic> json) => AiChatResponse(
    conversationId: _int(
      json['conversacion_id'] ?? json['conversation_id'] ?? json['id'],
    ),
    title: _string(json['titulo'] ?? json['title']),
    response: _string(json['respuesta']) ?? '',
    mode: _string(json['modo']),
    queries: _strings(json['consultas']),
    products: _maps(
      json['prendas'],
    ).map(AiRecommendationItem.fromJson).toList(growable: false),
    notice: _string(json['aviso']),
  );
}

class AiConversationSummary {
  const AiConversationSummary({
    required this.id,
    required this.title,
    this.updatedAt,
  });

  final int id;
  final String title;
  final String? updatedAt;

  factory AiConversationSummary.fromJson(Map<String, dynamic> json) =>
      AiConversationSummary(
        id: _int(json['id'] ?? json['conversacion_id']) ?? 0,
        title: _string(json['titulo'] ?? json['title']) ?? 'Conversación',
        updatedAt: _string(json['actualizado_en'] ?? json['updated_at']),
      );
}

class AiConversationDetail extends AiConversationSummary {
  const AiConversationDetail({
    required super.id,
    required super.title,
    super.updatedAt,
    this.messages = const [],
  });

  final List<AiChatMessage> messages;

  factory AiConversationDetail.fromJson(Map<String, dynamic> json) =>
      AiConversationDetail(
        id: _int(json['id'] ?? json['conversacion_id']) ?? 0,
        title: _string(json['titulo'] ?? json['title']) ?? 'Conversación',
        updatedAt: _string(json['actualizado_en'] ?? json['updated_at']),
        messages: _maps(
          json['mensajes'] ?? json['messages'],
        ).map(AiChatMessage.fromJson).toList(growable: false),
      );
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value : null;

int? _int(Object? value) => value is int ? value : int.tryParse('$value');

double? _number(Object? value) =>
    value is num ? value.toDouble() : double.tryParse('$value');

List<String> _strings(Object? value) => value is Iterable
    ? value.whereType<String>().toList(growable: false)
    : const [];

List<Map<String, dynamic>> _maps(Object? value) => value is Iterable
    ? value
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList(growable: false)
    : const [];
