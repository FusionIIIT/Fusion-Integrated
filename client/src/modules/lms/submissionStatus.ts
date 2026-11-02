export type SubmissionStatus = "submitted" | "late" | "missing";

export function submissionStatus(
  dueAt: string,
  submission: { status: SubmissionStatus } | undefined,
  now = Date.now(),
): SubmissionStatus | undefined {
  if (submission) return submission.status;
  return new Date(dueAt).getTime() <= now ? "missing" : undefined;
}
