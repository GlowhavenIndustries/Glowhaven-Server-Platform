## 2026-10-02 - Modal Dialog Accessibility and Keyboard Dismissal
**Learning:** Modal dialogs in Helix lacked ARIA semantics (`role="dialog"`, `aria-modal="true"`) and icon-only close buttons lacked `aria-label`, preventing screen reader users from identifying modal contexts. In addition, modals could not be dismissed via Escape key or backdrop click.
**Action:** Ensure all modal components in Helix include `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, explicit `aria-label="Close modal"` on icon controls, and keyboard `Escape` + backdrop click listeners.
