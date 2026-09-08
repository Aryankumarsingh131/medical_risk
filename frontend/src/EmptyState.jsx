import React from "react";

export default function EmptyState({ icon = "\u{1F4CB}", title, description, action, onAction }) {
  return (
    <div className="empty-state" role="status">
      <div className="empty-state-icon">{icon}</div>
      {title && <div className="empty-state-title">{title}</div>}
      {description && <div className="empty-state-desc">{description}</div>}
      {action && onAction && (
        <button type="button" onClick={onAction} className="empty-state-action">
          {action}
        </button>
      )}
    </div>
  );
}
