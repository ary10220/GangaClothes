# Virtual fitting with automatic body placement

## Objective

Add a virtual-fitting action to the Flutter product detail that opens a camera modal and overlays whichever product image is currently selected. The frontend detects the user's body and places the image automatically; no AR asset or fitting metadata is required from the backend.

## Problem and why

The product detail currently has no virtual-fitting action. The Angular reference uses a camera modal and body landmarks to place a garment. Flutter needs a small mobile camera + pose-detection flow that uses the selected catalog image directly.

## Scope

- Use the selected variant image, falling back to the product image.
- Add a camera-backed modal from product detail.
- Detect shoulders and hips on-device and place the image automatically.
- Keep transient fitting state in the frontend only.
- Handle camera lifecycle, permissions, missing assets, and unsupported platforms.
- Add focused pose/placement and widget tests.

## Constraints

- Do not read or require `tiene_probador`, `recursos_ar`, or any backend AR record.
- Do not persist calibration or fitting state to the backend.
- Do not implement 3D assets in this slice.
- Preserve existing product selection, reservation, cart, and branch behavior.
- Use `fvm flutter` for checks.
- No commit or branch change; record verification in this document.

## Tasks

- [x] VF-1 Use selected variant/product image and remove backend AR eligibility from the mobile flow.
- [x] VF-2 Implement automatic shoulder/hip pose placement, lifecycle, and platform permissions.
- [x] VF-3 Add the product-detail action and connect the selected variant/product image to the modal.
- [x] VF-4 Add focused pose/placement tests and run analysis plus the full test suite.

## Authorized scope

- `mobile/pubspec.yaml`, `mobile/pubspec.lock`
- `mobile/lib/features/catalog/`
- `mobile/lib/features/virtual_fitting/`
- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/ios/Runner/Info.plist`
- `mobile/test/`
- This task document and its Engram mirror

## Acceptance criteria

- A product detail with a selected variant image, or fallback product image, shows `Vestidor virtual` and opens a modal.
- The modal uses the front camera and displays that selected image.
- The frontend detects shoulders and hips and updates the image placement automatically.
- No backend fitting asset or fitting record is read or written.
- Closing the modal releases the camera.
- Existing catalog tests and the full Flutter test suite pass.

## Checks

- `fvm dart format ...`
- `fvm flutter analyze`
- `fvm flutter test`
- `git diff --check`

## Progress

- Previous manual overlay implementation superseded by the user's clarified automatic-placement requirement.
- Route: delegated direct writer because this changes catalog integration, camera/pose dependencies, feature code, platform configuration, and tests.
- Verification: `fvm dart format` 7 files/0 changed; `fvm flutter analyze` no issues; `fvm flutter test` 147 passed; `git diff --check` passed.
- Next: physical Android/iOS device verification remains pending.
