import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Search, Clock, Compass, Zap } from 'lucide-react';
export interface CommandPaletteAction {
  id: string;
  label: string;
  shortcut?: string;
  section?: string;
  handler: () => void;
}
import './CommandPalette.css';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  actions: CommandPaletteAction[];
  sectionsOrder?: string[];
  onQueryChange?: (query: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, actions, sectionsOrder, onQueryChange }) => {
  const [query, setQuery] = useState('');
  const [recent, setRecent] = useState<CommandPaletteAction[]>([]);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      onQueryChange?.('');
    }
  }, [isOpen, onQueryChange]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return actions.filter(action =>
      action.label.toLowerCase().includes(q) ||
      action.shortcut?.toLowerCase().includes(q) ||
      action.section?.toLowerCase().includes(q)
    );
  }, [actions, query]);

  const grouped = useMemo(() => {
    const map = new Map<string, CommandPaletteAction[]>();
    filtered.forEach((action) => {
      const key = action.section || 'General';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(action);
    });
    const entries = Array.from(map.entries());
    if (sectionsOrder && sectionsOrder.length) {
      const orderIndex = (s: string) => {
        const idx = sectionsOrder.indexOf(s);
        return idx === -1 ? sectionsOrder.length + 1 : idx;
      };
      return entries.sort((a, b) => orderIndex(a[0]) - orderIndex(b[0]));
    }
    return entries;
  }, [filtered, sectionsOrder]);

  const handleSelect = (action: CommandPaletteAction) => {
    action.handler();
    setRecent((prev) => {
      const next = [action, ...prev.filter((a) => a.id !== action.id)].slice(0, 5);
      return next;
    });
    onClose();
  };

  if (!isOpen) return null;

  useEffect(() => {
    if (!isOpen) return;
    const root = dialogRef.current;
    const focusable = root?.querySelectorAll<HTMLElement>('input, button, [tabindex]:not([tabindex="-1"])');
    focusable?.[0]?.focus();
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
      if (e.key === 'Tab' && focusable && focusable.length > 0) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  return (
    <div className="command-palette-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="command-palette-header">
          <Search size={16} />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              onQueryChange?.(e.target.value);
            }}
            placeholder="Search commands…"
          />
          <button onClick={onClose} aria-label="Close command palette">Esc</button>
        </div>

        <div className="command-palette-list">
          {query.length === 0 && recent.length > 0 && (
            <div className="command-section-block">
              <div className="section-title"><Clock size={14} /> Recent</div>
              {recent.map(action => (
                <button
                  key={action.id}
                  className="command-palette-item"
                  onClick={() => handleSelect(action)}
                >
                  <div>
                    <div className="command-label">{action.label}</div>
                    {action.section && <div className="command-section">{action.section}</div>}
                  </div>
                  {action.shortcut && <span className="command-shortcut">{action.shortcut}</span>}
                </button>
              ))}
            </div>
          )}

          {query.length === 0 && (
            <div className="command-section-block">
              <div className="section-title"><Zap size={14} /> Shortcuts</div>
              <div className="command-hints">
                <span><span className="keycap">⌘/Ctrl</span> + <span className="keycap">K</span> Open</span>
                <span><span className="keycap">⌘/Ctrl</span> + <span className="keycap">1-7</span> Navigate</span>
                <span><span className="keycap">Esc</span> Close</span>
              </div>
            </div>
          )}

          {filtered.length === 0 && (
            <div className="command-palette-empty">No commands found</div>
          )}
          {grouped.map(([section, items]) => (
            <div key={section} className="command-section-block">
              <div className="section-title">{section}</div>
              {items.map((action) => (
                <button
                  key={action.id}
                  className="command-palette-item"
                  onClick={() => handleSelect(action)}
                >
                  <div>
                    <div className="command-label">{action.label}</div>
                    {action.section && <div className="command-section">{action.section}</div>}
                  </div>
                  {action.shortcut && <span className="command-shortcut">{action.shortcut}</span>}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
