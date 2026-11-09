"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { Check, ChevronDown, Film, MessageSquare, Music2, PlaySquare } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AnalysisSource {
  analysis_id: string;
  video_id: string;
  video_title: string;
  thumbnail_url: string | null;
  platform: string;
  comments_analyzed: number;
  created_at: string;
}

interface VideoSourceSelectProps {
  sources: AnalysisSource[];
  value: string;
  onChange: (analysisId: string) => void;
  disabled?: boolean;
}

function formatAnalyzedAt(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function platformLabel(platform: string) {
  if (platform === "youtube") return "YouTube";
  if (platform === "tiktok") return "TikTok";
  return platform;
}

function PlatformIcon({
  platform,
  className,
}: {
  platform: string;
  className?: string;
}) {
  if (platform === "youtube") return <PlaySquare className={className} />;
  if (platform === "tiktok") return <Music2 className={className} />;
  return <Film className={className} />;
}

function SourceThumbnail({
  source,
  className,
}: {
  source: AnalysisSource;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "relative block shrink-0 overflow-hidden rounded-lg bg-surface-container-high",
        className,
      )}
    >
      {source.thumbnail_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={source.thumbnail_url}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
        />
      ) : (
        <span className="flex h-full w-full items-center justify-center text-on-surface-variant/40">
          <Film className="h-4 w-4" />
        </span>
      )}
    </span>
  );
}

export function VideoSourceSelect({
  sources,
  value,
  onChange,
  disabled = false,
}: VideoSourceSelectProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const baseId = useId();
  const listboxId = `${baseId}-listbox`;
  const optionId = (index: number) => `${baseId}-option-${index}`;

  const selectedIndex = sources.findIndex(
    (source) => source.analysis_id === value,
  );
  const selected = selectedIndex >= 0 ? sources[selectedIndex] : undefined;

  const close = useCallback((restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) triggerRef.current?.focus();
  }, []);

  const openList = useCallback(() => {
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  }, [selectedIndex]);

  const choose = useCallback(
    (index: number) => {
      const source = sources[index];
      if (!source) return;
      onChange(source.analysis_id);
      close(true);
    },
    [close, onChange, sources],
  );

  // Focus the listbox once it is rendered so keyboard navigation is immediate.
  useEffect(() => {
    if (open) listRef.current?.focus();
  }, [open]);

  // Keep the highlighted option visible while arrowing through the list.
  useEffect(() => {
    if (!open) return;
    document
      .getElementById(`${baseId}-option-${activeIndex}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, baseId, open]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  function handleTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openList();
    } else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      if (open) close();
      else openList();
    }
  }

  function handleListKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, sources.length - 1));
        break;
      case "ArrowUp":
        event.preventDefault();
        setActiveIndex((index) => Math.max(index - 1, 0));
        break;
      case "Home":
        event.preventDefault();
        setActiveIndex(0);
        break;
      case "End":
        event.preventDefault();
        setActiveIndex(sources.length - 1);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        choose(activeIndex);
        break;
      case "Escape":
        event.preventDefault();
        close(true);
        break;
      case "Tab":
        close();
        break;
    }
  }

  return (
    <div ref={containerRef} className="relative min-w-0 flex-1">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        disabled={disabled || sources.length === 0}
        onClick={() => {
          if (open) close();
          else openList();
        }}
        onKeyDown={handleTriggerKeyDown}
        className={cn(
          "group flex w-full items-center gap-3 rounded-2xl border bg-surface-container-lowest px-3 py-2.5 text-left transition-all duration-200",
          open
            ? "border-primary/40 shadow-md ring-1 ring-primary/10"
            : "border-outline-variant/30 hover:border-outline-variant/60 hover:shadow-sm",
          "disabled:cursor-not-allowed disabled:opacity-60",
        )}
      >
        {selected ? (
          <SourceThumbnail source={selected} className="h-11 w-16" />
        ) : (
          <span className="flex h-11 w-16 shrink-0 items-center justify-center rounded-lg bg-surface-container-high text-on-surface-variant/40">
            <Film className="h-4 w-4" />
          </span>
        )}

        <span className="min-w-0 flex-1">
          <span className="block truncate font-playfair text-sm font-semibold text-primary">
            {selected?.video_title ?? "Choose an analyzed video"}
          </span>
          {selected ? (
            <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-literata text-[11px] text-on-surface-variant">
              <span className="inline-flex items-center gap-1">
                <PlatformIcon
                  platform={selected.platform}
                  className="h-3 w-3"
                />
                {platformLabel(selected.platform)}
              </span>
              <span aria-hidden className="text-outline-variant">
                ·
              </span>
              <span className="inline-flex items-center gap-1">
                <MessageSquare className="h-3 w-3" />
                {selected.comments_analyzed.toLocaleString()} comments
              </span>
              <span aria-hidden className="text-outline-variant">
                ·
              </span>
              <span>Analyzed {formatAnalyzedAt(selected.created_at)}</span>
            </span>
          ) : (
            <span className="mt-0.5 block font-literata text-[11px] text-on-surface-variant">
              Pick a completed analysis to generate from
            </span>
          )}
        </span>

        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-on-surface-variant transition-transform duration-200",
            open && "rotate-180 text-primary",
          )}
        />
      </button>

      {open && (
        <div
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label="Analyzed videos"
          aria-activedescendant={optionId(activeIndex)}
          tabIndex={-1}
          onKeyDown={handleListKeyDown}
          className="absolute z-30 mt-2 w-full overflow-hidden rounded-2xl border border-outline-variant/20 bg-surface-container-lowest shadow-2xl shadow-primary/10 focus:outline-none"
        >
          <div className="flex items-center justify-between border-b border-outline-variant/10 px-4 py-2.5">
            <span className="font-literata text-[10px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant/70">
              Analyzed videos
            </span>
            <span className="rounded-full bg-surface-container px-2 py-0.5 font-literata text-[10px] font-semibold text-on-surface-variant">
              {sources.length}
            </span>
          </div>

          <div className="max-h-72 overflow-y-auto p-1.5">
            {sources.map((source, index) => {
              const isSelected = source.analysis_id === value;
              const isActive = index === activeIndex;

              return (
                <div
                  key={source.analysis_id}
                  id={optionId(index)}
                  role="option"
                  aria-selected={isSelected}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => choose(index)}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 rounded-xl px-2 py-2 transition-colors",
                    isActive && "bg-surface-container-low",
                    isSelected && "bg-primary/5",
                  )}
                >
                  <SourceThumbnail source={source} className="h-10 w-14" />

                  <span className="min-w-0 flex-1">
                    <span
                      className={cn(
                        "block truncate font-literata text-sm",
                        isSelected
                          ? "font-semibold text-primary"
                          : "font-medium text-on-surface",
                      )}
                    >
                      {source.video_title}
                    </span>
                    <span className="mt-0.5 flex items-center gap-1.5 font-literata text-[11px] text-on-surface-variant">
                      <PlatformIcon
                        platform={source.platform}
                        className="h-3 w-3"
                      />
                      <span>{platformLabel(source.platform)}</span>
                      <span aria-hidden className="text-outline-variant">
                        ·
                      </span>
                      <span>
                        {source.comments_analyzed.toLocaleString()} comments
                      </span>
                      <span aria-hidden className="text-outline-variant">
                        ·
                      </span>
                      <span>{formatAnalyzedAt(source.created_at)}</span>
                    </span>
                  </span>

                  <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                    {isSelected && <Check className="h-4 w-4 text-primary" />}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
