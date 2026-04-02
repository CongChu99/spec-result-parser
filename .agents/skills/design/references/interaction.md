# Interaction Design

## Eight Interactive States

Every interactive element must handle all eight states:
1. **Default** — resting appearance
2. **Hover** — mouse over (never seen by keyboard users)
3. **Focus** — keyboard active (never seen by mouse users)
4. **Active** — pressed/pressed
5. **Disabled** — unavailable (never dim text alone)
6. **Loading** — async operation in progress
7. **Error** — validation failed or action failed
8. **Success** — action completed

## Focus Rings

Focus rings must never be removed without replacement.

```css
:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```

Rules:
- Use `:focus-visible` to show focus only for keyboard users
- 3:1 contrast minimum
- 2–3px thickness
- Consistent offset

Hover and Focus are often confused — keyboard users never see hover states.

## Forms

- **Visible labels always** — placeholders disappear on input
- Validate on blur, not keystroke
- Place errors below fields with `aria-describedby`
- Show all errors at once, not one at a time

```html
<label for="email">Email</label>
<input id="email" type="email" aria-describedby="email-error">
<span id="email-error" role="alert">Please include an @ symbol</span>
```

## Loading States

- Optimistic updates work for low-stakes actions
- Skeleton screens feel faster than spinners
- Show progress for long operations

## Modals

Use the native `<dialog>` element. It handles focus trapping automatically.

```js
const dialog = document.querySelector('dialog');
dialog.showModal(); // modal with backdrop
dialog.show();      // modeless
```

## Destructive Actions

Prefer **undo** over confirmation dialogs. Users click through confirmations mindlessly.

"Deleted. Undo?" is better than "Are you sure you want to delete?"

## Keyboard Navigation

- Roving tabindex for component groups (tabs, radio groups)
- Skip links for main content
- All custom controls must have ARIA + keyboard support
- Arrow keys for navigating within a component

## Gestures

Gestures are invisible — hint at their existence through partial reveals or visible alternatives. **Never rely on gestures as the only action method.**
