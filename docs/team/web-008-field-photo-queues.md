# WEB-008 field photo queues

Status: completed locally on branch `feature/web-008-field-photo-queues`.

## Scope

- Added shared field/photo queue navigation for inspection and post-service
  review pages.
- Added a shared photo evidence component with image, metadata, data-status
  labeling, and evidence ID.
- Added fallback copy inside the image frame so unavailable media does not block
  case reading.
- Applied the shared structure to prepared inspection photos and simulated
  post-service mowing photos.
- Added tests covering the shared structure plus existing prepared and simulated
  photo queue contracts.

## Safety Notes

- No checksum is invented when the upstream contract does not provide one; the UI
  displays the evidence ID and metadata instead.
- Prepared inspection photos and simulated post-service photos remain separated
  by route, navigation state, and data-status copy.
- Photo acceptance still does not validate height, authorize field work, promote
  training data, or create official reporting evidence.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- field-photo-queue.test.ts photo-reviews.test.ts mowing-photo-reviews.test.ts photo-review-routes.test.ts mowing-photo-review-routes.test.ts`
