import 'package:shared_preferences/shared_preferences.dart';

abstract interface class BranchPreferenceStore {
  Future<int?> readSelectedBranch();

  Future<void> saveSelectedBranch(int? branchId);
}

class PreferencesStorage implements BranchPreferenceStore {
  const PreferencesStorage(this._preferences);

  PreferencesStorage.fromInstance(SharedPreferences preferences)
    : _preferences = Future.value(preferences);

  PreferencesStorage.load() : _preferences = SharedPreferences.getInstance();

  static const selectedBranchKey = 'gc_sucursal_tienda';

  final Future<SharedPreferences> _preferences;

  @override
  Future<int?> readSelectedBranch() async {
    final preferences = await _preferences;
    final raw = preferences.getString(selectedBranchKey);
    final branchId = raw == null ? null : int.tryParse(raw);
    if (raw != null && branchId == null) {
      await preferences.remove(selectedBranchKey);
    }
    return branchId;
  }

  @override
  Future<void> saveSelectedBranch(int? branchId) async {
    final preferences = await _preferences;
    if (branchId == null) {
      await preferences.remove(selectedBranchKey);
      return;
    }
    await preferences.setString(selectedBranchKey, '$branchId');
  }
}
