# Completion verification recipe

Use only for the assigned snapshot and criteria. Compare the claimed behavior,
changed files and actual proof. Check relevant happy/failure paths and reachable
configuration; inspect whether tests exercise the real target. Report missing
proof, exact impact and uncertainty as findings, not a new mandatory suite.

Return the canonical result with executorExtensions.review: verdict, findings,
reviewedOrderId, reviewedResultSha256 and productSnapshotSha256. A completed
review can report verdict fail. The lead accepts or requests correction; the
reviewer never edits product, accepts the release or assigns a successor reviewer.
