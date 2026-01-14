import React, { useState } from 'react';
import './inline-edit.css';

export interface InlineEditProps {
  value: string;
  label?: string;
  placeholder?: string;
  onSave: (next: string) => Promise<void> | void;
  disabled?: boolean;
  className?: string;
  displayClassName?: string;
  inputClassName?: string;
  activation?: 'click' | 'double-click';
}

export const InlineEdit: React.FC<InlineEditProps> = ({
  value,
  label,
  placeholder,
  onSave,
  disabled = false,
  className,
  displayClassName,
  inputClassName,
  activation = 'click',
}) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the draft in sync when the parent changes the value (e.g., after save or when switching records)
  React.useEffect(() => {
    setDraft(value);
  }, [value]);

  const handleSubmit = async () => {
    if (disabled) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } catch (err: any) {
      setError(err?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const activate = () => {
    if (!disabled) {
      setEditing(true);
      setError(null);
    }
  };

  return (
    <div className={`inline-edit${className ? ` ${className}` : ''}`}>
      {label && <div className="inline-edit-label">{label}</div>}
      {editing ? (
        <div className="inline-edit-control">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            disabled={saving || disabled}
            className={inputClassName}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleSubmit();
              }
              if (e.key === 'Escape') {
                setDraft(value);
                setEditing(false);
              }
            }}
          />
          <div className="inline-edit-actions">
            <button onClick={handleSubmit} disabled={saving || disabled}>{saving ? 'Saving…' : 'Save'}</button>
            <button onClick={() => { setDraft(value); setEditing(false); }} disabled={saving}>Cancel</button>
          </div>
          {error && <div className="inline-edit-error">{error}</div>}
        </div>
      ) : (
        <button
          className={`inline-edit-display${displayClassName ? ` ${displayClassName}` : ''}`}
          onClick={activation === 'click' ? activate : undefined}
          onDoubleClick={activation === 'double-click' ? activate : undefined}
          aria-label="Edit field"
        >
          <span>{value || placeholder || 'Click to edit'}</span>
        </button>
      )}
    </div>
  );
};
