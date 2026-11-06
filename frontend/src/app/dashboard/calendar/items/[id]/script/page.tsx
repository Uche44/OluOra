"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  FileText,
  Loader2,
  Plus,
  Quote,
  RefreshCw,
  Save,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { authedFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CalendarItem {
  id: string;
  opportunity_id: string | null;
  title: string;
  angle: string;
  notes: string;
  content_context: string;
  format: string;
  length: string;
  platform: string;
  scheduled_date: string;
  scheduled_time: string | null;
  status: string;
}

interface Evidence {
  id: string;
  insight_id: string | null;
  cluster_id: string | null;
  comment_id: string | null;
  quote: string | null;
}

interface Opportunity {
  id: string;
  title: string;
  rationale: string;
  suggested_format: string;
  suggested_length: string;
  suggested_angle: string;
  priority: string;
  source_video_title: string | null;
  evidence: Evidence[];
}

interface ScriptSection {
  heading: string;
  content: string;
}

interface Script {
  id: string;
  calendar_item_id: string;
  version: number;
  working_title: string;
  hook: string;
  body: string;
  sections: ScriptSection[];
  talking_points: string[];
  examples: string[];
  cta: string;
  caption: string;
  description: string;
  alt_titles: string[];
  model: string | null;
  generated_at: string;
  user_edited_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ScriptForm {
  working_title: string;
  hook: string;
  sections: ScriptSection[];
  talking_points: string[];
  examples: string[];
  cta: string;
  caption: string;
  description: string;
  alt_titles: string[];
}

function toForm(script: Script): ScriptForm {
  const sections =
    script.sections && script.sections.length > 0
      ? script.sections
      : script.body
        ? [{ heading: "", content: script.body }]
        : [];

  return {
    working_title: script.working_title,
    hook: script.hook,
    sections,
    talking_points: script.talking_points || [],
    examples: script.examples || [],
    cta: script.cta,
    caption: script.caption,
    description: script.description,
    alt_titles: script.alt_titles || [],
  };
}

function emptyForm(): ScriptForm {
  return {
    working_title: "",
    hook: "",
    sections: [],
    talking_points: [],
    examples: [],
    cta: "",
    caption: "",
    description: "",
    alt_titles: [],
  };
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function evidenceLabel(evidence: Evidence) {
  if (evidence.comment_id) return "Viewer comment";
  if (evidence.insight_id) return "Analysis insight";
  if (evidence.cluster_id) return "Topic theme";
  return "Audience evidence";
}

export default function ScriptEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: itemId } = use(params);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [item, setItem] = useState<CalendarItem | null>(null);
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [versions, setVersions] = useState<Script[]>([]);
  const [form, setForm] = useState<ScriptForm>(emptyForm());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  const loadVersions = useCallback(
    async (): Promise<Script[]> => {
      const res = await authedFetch(
        `${apiUrl}/api/v1/content/calendar/items/${itemId}/scripts`,
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not load script versions.");
      }
      const list: Script[] = data.data || [];
      setVersions(list);
      return list;
    },
    [apiUrl, itemId],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const itemRes = await authedFetch(
        `${apiUrl}/api/v1/content/calendar/items/${itemId}`,
      );
      const itemData = await itemRes.json().catch(() => ({}));
      if (!itemRes.ok) {
        throw new Error(itemData?.detail?.message || "Could not load the calendar item.");
      }
      setItem(itemData);

      if (itemData.opportunity_id) {
        const oppRes = await authedFetch(
          `${apiUrl}/api/v1/content/opportunities/${itemData.opportunity_id}`,
        );
        if (oppRes.ok) {
          setOpportunity(await oppRes.json());
        } else {
          setOpportunity(null);
        }
      } else {
        setOpportunity(null);
      }

      await loadVersions();

      const scriptRes = await authedFetch(
        `${apiUrl}/api/v1/content/calendar/items/${itemId}/script`,
      );
      if (scriptRes.ok) {
        const current: Script = await scriptRes.json();
        setScript(current);
        setForm(toForm(current));
      } else if (scriptRes.status === 404) {
        setScript(null);
        setForm(emptyForm());
      } else {
        const data = await scriptRes.json().catch(() => ({}));
        throw new Error(data?.detail?.message || "Could not load the script.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the script.");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, itemId, loadVersions]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const updateField = (field: keyof ScriptForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateSection = (
    index: number,
    field: "heading" | "content",
    value: string,
  ) => {
    setForm((current) => {
      const next = [...current.sections];
      next[index] = { ...next[index], [field]: value };
      return { ...current, sections: next };
    });
  };

  const addSection = () => {
    setForm((current) => ({
      ...current,
      sections: [...current.sections, { heading: "", content: "" }],
    }));
  };

  const removeSection = (index: number) => {
    setForm((current) => ({
      ...current,
      sections: current.sections.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const moveSection = (index: number, direction: -1 | 1) => {
    setForm((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.sections.length) return current;
      const next = [...current.sections];
      [next[index], next[target]] = [next[target], next[index]];
      return { ...current, sections: next };
    });
  };

  const updateList = (
    field: "talking_points" | "examples" | "alt_titles",
    index: number,
    value: string,
  ) => {
    setForm((current) => {
      const next = [...current[field]];
      next[index] = value;
      return { ...current, [field]: next };
    });
  };

  const addListItem = (field: "talking_points" | "examples" | "alt_titles") => {
    setForm((current) => ({ ...current, [field]: [...current[field], ""] }));
  };

  const removeListItem = (
    field: "talking_points" | "examples" | "alt_titles",
    index: number,
  ) => {
    setForm((current) => ({
      ...current,
      [field]: current[field].filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const handleSave = async () => {
    if (!script) return;
    if (!form.working_title.trim()) {
      setError("Give the script a working title.");
      return;
    }
    if (
      !form.sections.some(
        (section) => section.heading.trim() || section.content.trim(),
      )
    ) {
      setError("Add at least one script section.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/scripts/${script.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not save the script.");
      }
      setScript(data);
      setForm(toForm(data));
      await loadVersions();
      setNotice("Script saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the script.");
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async (force: boolean) => {
    if (
      force &&
      !window.confirm(
        "Generate a new version? Your current edits stay saved in the existing version.",
      )
    ) {
      return;
    }
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const res = await authedFetch(
        `${apiUrl}/api/v1/content/calendar/items/${itemId}/script/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ force }),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not generate the script.");
      }
      setScript(data.data);
      setForm(toForm(data.data));
      await loadVersions();
      setNotice(
        data.cached
          ? "Showing the existing script for this item."
          : `Generated version ${data.data.version}. Previous versions are kept.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the script.");
    } finally {
      setGenerating(false);
    }
  };

  const loadVersion = (version: Script) => {
    setScript(version);
    setForm(toForm(version));
    setNotice(
      version.id === versions[0]?.id
        ? null
        : `Viewing version ${version.version}. Edits save to this version.`,
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse p-2">
        <div className="h-6 bg-surface-container rounded w-1/4" />
        <div className="h-10 bg-surface-container rounded w-2/3" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 bg-surface-container rounded-3xl" />
          <div className="h-96 bg-surface-container rounded-3xl" />
        </div>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="p-6 bg-amber-50 border border-amber-200 text-amber-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl mx-auto my-12">
        <div className="flex items-center gap-2 text-amber-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Could not load this calendar item</span>
        </div>
        <p>{error || "The item may have been removed."}</p>
        <Link
          href="/dashboard/calendar"
          className="px-5 py-2 rounded-full border border-amber-300 hover:bg-amber-100/50 transition text-center font-medium"
        >
          Back to Calendar
        </Link>
      </div>
    );
  }

  const isLatest = Boolean(script && versions[0]?.id === script.id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-6 text-on-surface pb-12"
    >
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/dashboard/calendar"
          className="flex items-center gap-1.5 text-xs font-semibold font-literata text-on-surface-variant hover:text-primary transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Calendar
        </Link>
        {script && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving || generating}
              className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5" />
              )}
              {saving ? "Saving..." : "Save changes"}
            </button>
            <button
              onClick={() => handleGenerate(true)}
              disabled={saving || generating}
              className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container text-xs font-semibold font-literata transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? "animate-spin" : ""}`} />
              Regenerate
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <div className="inline-flex items-center gap-2">
          <span className="ai-badge bg-[#0b3d2e]/10 text-primary border-[#0b3d2e]/20">
            Script / Brief
          </span>
          {script && (
            <span className="text-[10px] font-semibold font-literata px-2 py-0.5 rounded-full bg-surface-container border border-outline-variant/20 text-on-surface-variant">
              Version {script.version}
              {!isLatest ? " · older" : ""}
            </span>
          )}
          {script?.user_edited_at && (
            <span className="text-[10px] font-semibold font-literata px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700">
              Edited
            </span>
          )}
        </div>
        <h1 className="font-playfair text-3xl font-bold text-primary leading-tight">
          {item.title}
        </h1>
        <p className="text-xs font-literata text-on-surface-variant">
          {item.format} · {item.length === "short" ? "Short" : "Long-form"} ·{" "}
          {item.platform} · {formatDate(item.scheduled_date)}
        </p>
      </div>

      {error && (
        <div className="p-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl flex items-start gap-2 font-literata text-xs">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto font-bold p-0.5 cursor-pointer"
            aria-label="Dismiss error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {notice && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl flex items-center gap-2 font-literata text-xs">
          <Check className="w-4 h-4" />
          <span>{notice}</span>
        </div>
      )}

      {!script ? (
        <div className="bg-white border border-outline-variant/10 rounded-3xl p-10 shadow-sm flex flex-col items-center gap-5 text-center">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <FileText className="w-7 h-7 text-primary" />
          </div>
          <div className="flex flex-col gap-2 max-w-md">
            <h2 className="font-playfair text-xl font-bold text-primary">
              No script yet
            </h2>
            <p className="font-literata text-sm text-on-surface-variant leading-relaxed">
              Generate a draft from this calendar item
              {opportunity ? " and its audience evidence" : ""}. You can edit every
              section afterward.
            </p>
          </div>
          <button
            onClick={() => handleGenerate(false)}
            disabled={generating}
            className="px-6 py-3 rounded-full bg-primary hover:bg-primary-container text-on-primary text-sm font-semibold font-literata transition shadow-md disabled:opacity-50 flex items-center gap-2 cursor-pointer"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {generating ? "Generating..." : "Generate script"}
          </button>
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6 items-start">
          <div className="lg:col-span-2 flex flex-col gap-5">
            <div className="bg-white border border-outline-variant/10 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Working title
                </span>
                <input
                  value={form.working_title}
                  onChange={(event) => updateField("working_title", event.target.value)}
                  className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Hook
                </span>
                <textarea
                  value={form.hook}
                  onChange={(event) => updateField("hook", event.target.value)}
                  rows={3}
                  className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
              </label>

              <div className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                      Main script
                    </span>
                    <span className="text-[10px] font-literata text-on-surface-variant/60">
                      Edit each section separately. Use blank lines between
                      paragraphs.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={addSection}
                    className="flex items-center gap-1 text-[10px] font-semibold font-literata text-primary hover:underline cursor-pointer whitespace-nowrap"
                  >
                    <Plus className="w-3 h-3" />
                    Add section
                  </button>
                </div>

                {form.sections.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-outline-variant/30 p-6 text-center">
                    <p className="text-xs font-literata text-on-surface-variant/60">
                      No sections yet.
                    </p>
                    <button
                      type="button"
                      onClick={addSection}
                      className="mt-2 text-xs font-semibold font-literata text-primary hover:underline cursor-pointer"
                    >
                      Add the first section
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {form.sections.map((section, index) => (
                      <div
                        key={`section-${index}`}
                        className="rounded-2xl border border-outline-variant/20 bg-surface-container-lowest/50 p-4 flex flex-col gap-3"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/50 whitespace-nowrap">
                            Section {index + 1}
                          </span>
                          <input
                            value={section.heading}
                            onChange={(event) =>
                              updateSection(index, "heading", event.target.value)
                            }
                            placeholder="Section heading (e.g. The problem)"
                            className="flex-1 min-w-0 px-3 py-2 rounded-xl border border-outline-variant/30 text-sm font-semibold font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <button
                            type="button"
                            onClick={() => moveSection(index, -1)}
                            disabled={index === 0}
                            className="p-2 rounded-lg text-on-surface-variant/50 hover:text-primary hover:bg-primary/5 transition disabled:opacity-25 disabled:hover:bg-transparent cursor-pointer"
                            aria-label="Move section up"
                          >
                            <ArrowUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => moveSection(index, 1)}
                            disabled={index === form.sections.length - 1}
                            className="p-2 rounded-lg text-on-surface-variant/50 hover:text-primary hover:bg-primary/5 transition disabled:opacity-25 disabled:hover:bg-transparent cursor-pointer"
                            aria-label="Move section down"
                          >
                            <ArrowDown className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => removeSection(index)}
                            className="p-2 rounded-lg text-on-surface-variant/40 hover:text-rose-500 hover:bg-rose-50 transition cursor-pointer"
                            aria-label="Remove section"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <textarea
                          value={section.content}
                          onChange={(event) =>
                            updateSection(index, "content", event.target.value)
                          }
                          rows={6}
                          placeholder="Write this section in paragraphs. Separate paragraphs with a blank line."
                          className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary resize-y leading-relaxed"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white border border-outline-variant/10 rounded-3xl p-6 shadow-sm flex flex-col gap-5">
              {(
                [
                  ["talking_points", "Key talking points"],
                  ["examples", "Examples / demonstrations"],
                  ["alt_titles", "Alternative titles"],
                ] as const
              ).map(([field, label]) => (
                <div key={field} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                      {label}
                    </span>
                    <button
                      onClick={() => addListItem(field)}
                      className="flex items-center gap-1 text-[10px] font-semibold font-literata text-primary hover:underline cursor-pointer"
                    >
                      <Plus className="w-3 h-3" />
                      Add
                    </button>
                  </div>
                  {form[field].length === 0 ? (
                    <span className="text-xs font-literata text-on-surface-variant/50 italic">
                      None yet.
                    </span>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {form[field].map((value, index) => (
                        <div key={`${field}-${index}`} className="flex items-center gap-2">
                          <input
                            value={value}
                            onChange={(event) =>
                              updateList(field, index, event.target.value)
                            }
                            className="flex-1 px-3 py-2 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <button
                            onClick={() => removeListItem(field, index)}
                            className="p-2 rounded-lg text-on-surface-variant/40 hover:text-rose-500 hover:bg-rose-50 transition cursor-pointer"
                            aria-label="Remove"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="bg-white border border-outline-variant/10 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Call to action
                </span>
                <textarea
                  value={form.cta}
                  onChange={(event) => updateField("cta", event.target.value)}
                  rows={2}
                  className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Caption
                </span>
                <textarea
                  value={form.caption}
                  onChange={(event) => updateField("caption", event.target.value)}
                  rows={2}
                  className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Description
                </span>
                <textarea
                  value={form.description}
                  onChange={(event) => updateField("description", event.target.value)}
                  rows={4}
                  className="px-4 py-3 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
              </label>
            </div>
          </div>

          {/* Context sidebar */}
          <aside className="flex flex-col gap-5 lg:sticky lg:top-24">
            <div className="bg-white border border-outline-variant/10 rounded-3xl p-5 shadow-sm flex flex-col gap-3">
              <h3 className="font-playfair text-base font-bold text-primary">
                Source context
              </h3>
              <div className="flex flex-col gap-1 text-xs font-literata text-on-surface-variant">
                <span>
                  <span className="font-semibold">Angle:</span>{" "}
                  {item.angle || "Not specified"}
                </span>
                {item.notes && (
                  <span>
                    <span className="font-semibold">Notes:</span> {item.notes}
                  </span>
                )}
                {item.content_context && (
                  <span className="whitespace-pre-line line-clamp-6">
                    <span className="font-semibold">Video context:</span>{" "}
                    {item.content_context}
                  </span>
                )}
              </div>

              {opportunity ? (
                <div className="flex flex-col gap-3 pt-3 border-t border-outline-variant/10">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70">
                      Opportunity
                    </span>
                    <span className="font-literata text-sm font-semibold text-primary">
                      {opportunity.title}
                    </span>
                    <span className="text-xs font-literata text-on-surface-variant leading-relaxed">
                      {opportunity.rationale}
                    </span>
                    {opportunity.source_video_title && (
                      <span className="text-[10px] font-literata text-on-surface-variant/60">
                        From: {opportunity.source_video_title}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70 flex items-center gap-1">
                      <Quote className="w-3 h-3" />
                      Audience evidence ({opportunity.evidence.length})
                    </span>
                    {opportunity.evidence.length === 0 ? (
                      <span className="text-xs font-literata text-on-surface-variant/60 italic">
                        No direct evidence attached.
                      </span>
                    ) : (
                      opportunity.evidence.slice(0, 5).map((evidence) => (
                        <blockquote
                          key={evidence.id}
                          className="text-xs font-literata text-on-surface-variant leading-relaxed border-l-2 border-primary/20 pl-3"
                        >
                          <span className="block text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/50 mb-0.5">
                            {evidenceLabel(evidence)}
                          </span>
                          {evidence.quote || "Source no longer available."}
                        </blockquote>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <span className="text-xs font-literata text-on-surface-variant/60 italic pt-3 border-t border-outline-variant/10">
                  This item is not linked to an opportunity, so no audience
                  evidence is attached.
                </span>
              )}

              <Link
                href="/dashboard/settings"
                className="text-[10px] font-literata text-primary hover:underline pt-3 border-t border-outline-variant/10"
              >
                Style preferences are applied during generation. Manage in Settings.
              </Link>
            </div>

            <div className="bg-white border border-outline-variant/10 rounded-3xl p-5 shadow-sm flex flex-col gap-3">
              <h3 className="font-playfair text-base font-bold text-primary">
                Version history
              </h3>
              <div className="flex flex-col gap-1.5">
                {versions.map((version) => (
                  <button
                    key={version.id}
                    onClick={() => loadVersion(version)}
                    className={cn(
                      "flex items-center justify-between text-left px-3 py-2 rounded-xl border transition cursor-pointer",
                      script.id === version.id
                        ? "border-primary/30 bg-primary/[0.04]"
                        : "border-outline-variant/10 hover:bg-surface-container",
                    )}
                  >
                    <span className="flex flex-col">
                      <span className="text-xs font-semibold font-literata text-primary">
                        Version {version.version}
                      </span>
                      <span className="text-[9px] font-literata text-on-surface-variant/60">
                        {formatDate(version.generated_at)}
                      </span>
                    </span>
                    {version.user_edited_at && (
                      <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Edited
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </motion.div>
  );
}
