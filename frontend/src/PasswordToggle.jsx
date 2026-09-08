import React, { useState } from "react";

export default function PasswordToggle({ value, onChange, placeholder, required, minLength, className = "" }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className={`password-toggle-wrap ${className}`}>
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        minLength={minLength}
        className="password-toggle-input"
      />
      <button
        type="button"
        className="password-toggle-btn"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        tabIndex={-1}
      >
        {visible ? "\u{1F441}" : "\u{1F441}‍\u{1F5E8}"}
      </button>
    </div>
  );
}
