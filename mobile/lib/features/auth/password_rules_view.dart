import 'package:flutter/material.dart';

import '../../app/theme.dart';
import 'auth_validation.dart';

class PasswordRulesView extends StatelessWidget {
  const PasswordRulesView({required this.value, super.key});

  final String value;

  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Requisitos de la contraseña',
    container: true,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final rule in passwordRules)
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: rule.matches(value) ? '✓ ' : '○ ',
                    style: TextStyle(
                      color: rule.matches(value)
                          ? GangaColors.success
                          : GangaColors.gray,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  TextSpan(
                    text: rule.label,
                    style: TextStyle(
                      color: rule.matches(value)
                          ? GangaColors.success
                          : GangaColors.gray,
                      fontSize: 11.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    ),
  );
}
