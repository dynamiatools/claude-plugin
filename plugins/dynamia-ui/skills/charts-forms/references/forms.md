# Forms

Adapted from ui-ux-pro-max form guidance (MIT), see NOTICE.

## Structure
- One column. Group related fields with `fieldset` and `legend`. Ask only what is needed; split long forms into steps with a progress indicator and a way back.
- Every field has a visible `<label for>` above it. A placeholder is an example, not a label. Helper text is linked with `aria-describedby`.
- Mark the exception: say "optional" for optional fields when most are required.
- Primary action is one clear button with a verb ("Create account"), secondary actions look secondary. Keep the submit reachable with the keyboard open on mobile.

## Inputs
- Correct `type`, `autocomplete`, `inputmode`, `enterkeyhint`; do not use `type="number"` for codes, ids or phone numbers (use `inputmode="numeric"`/`tel`).
- Font size 16px or more on mobile. Native pickers for date and select on small screens. Allow paste in password and code fields; offer a show-password toggle.
- Masks and formats help, but accept what people type (spaces, dashes) and normalize in code.
- Sensible defaults; remember what the user already gave.

## Validation and errors
- Validate on blur or on submit, not on every keystroke; clear the error as soon as the value is fixed. Server validation is the truth; client validation is a convenience.
- Error message next to the field, says what is wrong and how to fix it ("Use at least 8 characters"), linked with `aria-describedby`, `aria-invalid="true"` on the field, not color alone. On submit with errors, move focus to the first error and give a summary for long forms.
- Never clear the input on error. Keep partial progress.

## Submit and after
- Disable or guard the button while sending, show progress, prevent double submits (idempotency on the server).
- Success is explicit: confirmation, next step, or the created thing. Failure keeps the data and offers retry. Offline: queue or say clearly it cannot be sent (`dynamia-ui:offline-review`).
- Destructive or irreversible: confirm with the specific consequence, or allow undo.

## Special cases
- Login: allow password managers, no CAPTCHA before it is needed, clear "forgot password", no user-enumeration in error text.
- Payment and address: autocomplete tokens (`cc-number`, `postal-code`), one-line errors, show totals before the final step.
- Search and filters: apply on change with a visible result count, reset in one click, keep state in the URL.
