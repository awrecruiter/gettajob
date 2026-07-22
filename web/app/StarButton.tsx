"use client";

import { useOptimistic, useTransition } from "react";
import { toggleShortlist } from "@/lib/actions";

type Props = {
  jobId: number;
  starred: boolean;
  size?: "sm" | "md";
};

export function StarButton({ jobId, starred, size = "sm" }: Props) {
  const [pending, startTransition] = useTransition();
  const [optimisticStarred, setOptimisticStarred] = useOptimistic(starred);

  const cls =
    (optimisticStarred
      ? "text-amber-300"
      : "text-neutral-700 hover:text-neutral-400") +
    (size === "md" ? " text-2xl" : " text-lg") +
    " transition-colors disabled:opacity-50";

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        startTransition(async () => {
          setOptimisticStarred(!optimisticStarred);
          await toggleShortlist(jobId);
        });
      }}
      disabled={pending}
      className={cls}
      title={optimisticStarred ? "Remove from shortlist" : "Add to shortlist"}
      aria-label={optimisticStarred ? "Remove from shortlist" : "Add to shortlist"}
    >
      {optimisticStarred ? "★" : "☆"}
    </button>
  );
}
