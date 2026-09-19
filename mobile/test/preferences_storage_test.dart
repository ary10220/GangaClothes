import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  test('round-trips the selected branch and removes it when cleared', () async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final storage = PreferencesStorage.fromInstance(preferences);

    await storage.saveSelectedBranch(12);
    expect(await storage.readSelectedBranch(), 12);

    await storage.saveSelectedBranch(null);
    expect(await storage.readSelectedBranch(), isNull);
  });

  test('discards a corrupt selected branch value', () async {
    SharedPreferences.setMockInitialValues({
      PreferencesStorage.selectedBranchKey: 'not-an-id',
    });
    final preferences = await SharedPreferences.getInstance();
    final storage = PreferencesStorage.fromInstance(preferences);

    expect(await storage.readSelectedBranch(), isNull);
    expect(preferences.getString(PreferencesStorage.selectedBranchKey), isNull);
  });
}
