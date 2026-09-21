import 'dart:typed_data';

import 'package:printing/printing.dart';

typedef ReceiptPdfPrinter = Future<bool?> Function(Uint8List bytes);

Future<void> printReceiptPdf(
  Uint8List bytes, {
  ReceiptPdfPrinter? printer,
}) async {
  final opened = await (printer ?? _printWithPrinting)(bytes);
  if (opened != true) {
    throw StateError('No se pudo abrir el diálogo de PDF.');
  }
}

Future<bool?> _printWithPrinting(Uint8List bytes) =>
    Printing.layoutPdf(onLayout: (_) async => bytes);
