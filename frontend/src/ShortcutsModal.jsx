import React, { useEffect } from "react";

const SHORTCUTS = [
  { keys: ["/"], description: "Focus search input" },
  { keys: ["Esc"], description: "Close active modal" },
  { keys: ["?"], description: "Open keyboard shortcuts" },
  { keys: ["1-9"], description: "Switch navigation tabs (when not in input)" },
];

export default function ShortcutsModal({ isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-label="Keyboard shortcuts">
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 440 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Keyboard Shortcuts</h3>
          <button type="button" className="btn-secondary" onClick={onClose} aria-label="Close" style={{ padding: "2px 8px", fontSize: "1.1rem" }}>
            &times;
          </button>
        </div>
        <div className="shortcuts-list">
          {SHORTCUTS.map((s, i) => (
            <div key={i} className="shortcut-row">
              <div className="shortcut-keys">
                {s.keys.map((k, j) => (
                  <kbd key={j} className="shortcut-key">{k}</kbd>
                ))}
              </div>
              <span className="shortcut-desc">{s.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
