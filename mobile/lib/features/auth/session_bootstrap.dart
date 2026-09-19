import '../../core/storage/session_storage.dart';
import 'session_model.dart';

class SessionBootstrap {
  const SessionBootstrap(this.storage);

  final SessionStorage storage;

  Future<Session?> restore() => storage.readSession();
}
