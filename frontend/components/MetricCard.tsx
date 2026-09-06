import type { Metric } from "@/lib/types";

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <h4 className="font-medium">{metric.name}</h4>
        <span className="text-xl font-semibold tabular-nums text-indigo-600">
          {metric.display}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-600">{metric.explanation}</p>
      <p className="mt-2 rounded-lg bg-slate-50 px-3 py-1.5 font-mono text-xs text-slate-500">
        {metric.formula}
      </p>
      <p className="mt-2 text-sm font-medium text-slate-700">
        {metric.interpretation}
      </p>
    </div>
  );
}
