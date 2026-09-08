import React from "react";

export function SkeletonLine({ width = "100%", height = 14, style = {} }) {
  return (
    <div
      className="skeleton skeleton-line"
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ lines = 3, style = {} }) {
  return (
    <div className="skeleton-card" style={style} aria-busy="true">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine
          key={i}
          width={i === lines - 1 ? "60%" : "100%"}
          height={i === 0 ? 18 : 12}
          style={{ marginBottom: i < lines - 1 ? 8 : 0 }}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="skeleton-table" aria-busy="true">
      <div className="skeleton-table-header">
        {Array.from({ length: cols }).map((_, i) => (
          <SkeletonLine key={i} height={12} style={{ flex: 1 }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, c) => (
            <SkeletonLine key={c} height={12} style={{ flex: 1 }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonList({ items = 4 }) {
  return (
    <div className="skeleton-list" aria-busy="true">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="skeleton-list-item">
          <div className="skeleton skeleton-circle" />
          <div style={{ flex: 1 }}>
            <SkeletonLine width="70%" height={14} style={{ marginBottom: 6 }} />
            <SkeletonLine width="40%" height={10} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="skeleton-dashboard" aria-busy="true" aria-label="Loading dashboard">
      <div className="skeleton-dash-stats">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton-card" style={{ padding: 16 }}>
            <SkeletonLine width="50%" height={10} style={{ marginBottom: 8 }} />
            <SkeletonLine width="30%" height={24} />
          </div>
        ))}
      </div>
      <SkeletonCard lines={4} />
      <SkeletonTable rows={4} cols={5} />
    </div>
  );
}
