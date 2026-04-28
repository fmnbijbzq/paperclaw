"use client";

import { ErrorPanel } from "@/components/error-panel";

interface AppErrorProps {
  error: Error & {
    digest?: string;
  };
  reset: () => void;
}

export default function AppError({ error, reset }: AppErrorProps) {
  return (
    <ErrorPanel
      title="This route could not finish loading"
      description="The companion console hit an unexpected problem while resolving this view. The underlying backend and demo dataset have not been modified."
      detail={error.digest ? `Reference: ${error.digest}` : "Try the route again or return to the dashboard overview."}
      onRetry={reset}
      actionHref="/"
      actionLabel="Back to dashboard"
    />
  );
}
