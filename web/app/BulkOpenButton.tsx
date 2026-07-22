"use client";

type Props = {
  urls: string[];
};

export function BulkOpenButton({ urls }: Props) {
  if (urls.length === 0) return null;
  return (
    <button
      type="button"
      onClick={() => {
        // Browsers throttle rapid window.open calls — stagger to avoid popup blocking.
        urls.forEach((u, i) => {
          setTimeout(() => window.open(u, "_blank", "noopener,noreferrer"), i * 250);
        });
      }}
      className="px-3 py-1.5 rounded bg-amber-300 text-neutral-900 text-sm font-medium hover:bg-amber-200"
      title="Open every application URL in a new tab. Your browser may need popup permission."
    >
      Open all {urls.length} in tabs
    </button>
  );
}
