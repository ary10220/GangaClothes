import 'package:flutter/material.dart';

/// Named colors extracted from the Angular customer visual system.
abstract final class GangaColors {
  static const paper = Color(0xFFF2F2ED);
  static const ink = Color(0xFF14161A);
  static const brand = Color(0xFFE8175D);
  static const success = Color(0xFF1F7A5C);
  static const alert = Color(0xFFC93400);
  static const line = Color(0xFFD9D9D2);
  static const gray = Color(0xFF6B6F76);
  static const soft = Color(0xFFFBFBF8);
  static const white = Color(0xFFFFFFFF);
  static const lightSuccess = Color(0xFFE4F2EC);
  static const lightError = Color(0xFFFCE9E2);
  static const lightBrand = Color(0xFFFCE3EC);
  static const missingImage = Color(0xFF9AA0A6);
}

/// Reusable text styles for the sans and monospace hierarchy.
abstract final class GangaTextStyles {
  static const sansFallback = <String>[
    '-apple-system',
    'Segoe UI',
    'Roboto',
    'Helvetica',
    'Arial',
  ];

  static const monoFallback = <String>[
    'SF Mono',
    'Cascadia Mono',
    'Consolas',
    'monospace',
  ];

  static const eyebrow = TextStyle(
    fontFamily: 'monospace',
    fontFamilyFallback: monoFallback,
    fontSize: 10,
    letterSpacing: 1.6,
    fontWeight: FontWeight.w700,
    color: GangaColors.gray,
  );

  static const label = TextStyle(
    fontFamily: 'monospace',
    fontFamilyFallback: monoFallback,
    fontSize: 10,
    letterSpacing: 1.2,
    fontWeight: FontWeight.w700,
    color: GangaColors.gray,
  );

  static const body = TextStyle(
    fontFamilyFallback: sansFallback,
    fontSize: 14,
    color: GangaColors.ink,
  );

  static const heading = TextStyle(
    fontFamilyFallback: sansFallback,
    fontSize: 20,
    height: 1.15,
    fontWeight: FontWeight.w800,
    letterSpacing: -0.4,
    color: GangaColors.ink,
  );

  static const subheading = TextStyle(
    fontFamilyFallback: sansFallback,
    fontSize: 17,
    height: 1.2,
    fontWeight: FontWeight.w800,
    color: GangaColors.ink,
  );

  static const metadata = TextStyle(
    fontFamily: 'monospace',
    fontFamilyFallback: monoFallback,
    fontSize: 12,
    color: GangaColors.gray,
  );

  static const money = TextStyle(
    fontFamily: 'monospace',
    fontFamilyFallback: monoFallback,
    fontSize: 13,
    fontWeight: FontWeight.w700,
    color: GangaColors.brand,
  );

  static const brandWordmark = TextStyle(
    fontFamilyFallback: sansFallback,
    fontSize: 22,
    fontWeight: FontWeight.w900,
    letterSpacing: -0.7,
    color: GangaColors.ink,
  );

  static TextTheme get material => const TextTheme(
    bodyLarge: body,
    bodyMedium: body,
    bodySmall: TextStyle(
      fontFamilyFallback: sansFallback,
      fontSize: 12,
      color: GangaColors.gray,
    ),
    labelLarge: TextStyle(
      fontFamilyFallback: sansFallback,
      fontSize: 12.5,
      fontWeight: FontWeight.w700,
    ),
    titleLarge: heading,
    headlineSmall: heading,
  );
}

/// Theme factory used by the root app and by isolated widget tests.
abstract final class GangaTheme {
  static ThemeData light() {
    final colorScheme = ColorScheme.light().copyWith(
      primary: GangaColors.brand,
      onPrimary: GangaColors.white,
      secondary: GangaColors.ink,
      onSecondary: GangaColors.white,
      tertiary: GangaColors.success,
      onTertiary: GangaColors.white,
      error: GangaColors.alert,
      onError: GangaColors.white,
      surface: GangaColors.white,
      onSurface: GangaColors.ink,
      surfaceContainerHighest: GangaColors.soft,
      outline: GangaColors.line,
      outlineVariant: GangaColors.line,
    );

    final fieldBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GangaColors.line, width: 1.5),
    );
    final fieldFocusBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GangaColors.ink, width: 1.5),
    );
    final fieldErrorBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GangaColors.alert, width: 1.5),
    );

    return ThemeData(
      colorScheme: colorScheme,
      useMaterial3: true,
      scaffoldBackgroundColor: GangaColors.paper,
      fontFamilyFallback: GangaTextStyles.sansFallback,
      textTheme: GangaTextStyles.material,
      materialTapTargetSize: MaterialTapTargetSize.padded,
      visualDensity: VisualDensity.standard,
      splashFactory: InkRipple.splashFactory,
      cardTheme: CardThemeData(
        color: GangaColors.white,
        surfaceTintColor: Colors.transparent,
        margin: EdgeInsets.zero,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(13),
          side: const BorderSide(color: GangaColors.line, width: 1.5),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: GangaColors.white,
        foregroundColor: GangaColors.ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: GangaColors.soft,
        constraints: const BoxConstraints(minHeight: 48),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 10,
        ),
        hintStyle: const TextStyle(
          fontFamilyFallback: GangaTextStyles.sansFallback,
          fontSize: 13,
          color: GangaColors.gray,
        ),
        border: fieldBorder,
        enabledBorder: fieldBorder,
        focusedBorder: fieldFocusBorder,
        errorBorder: fieldErrorBorder,
        focusedErrorBorder: fieldErrorBorder,
        errorStyle: const TextStyle(
          fontFamilyFallback: GangaTextStyles.sansFallback,
          fontSize: 11.5,
          color: GangaColors.alert,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(Size(0, 48)),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: 16, vertical: 9),
          ),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          textStyle: const WidgetStatePropertyAll(
            TextStyle(
              inherit: false,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(Size(0, 48)),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: 16, vertical: 9),
          ),
          side: const WidgetStatePropertyAll(
            BorderSide(color: GangaColors.ink, width: 1.5),
          ),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          textStyle: const WidgetStatePropertyAll(
            TextStyle(
              inherit: false,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: GangaColors.line,
        thickness: 1,
        space: 1,
      ),
    );
  }
}

ThemeData gangaTheme() => GangaTheme.light();
