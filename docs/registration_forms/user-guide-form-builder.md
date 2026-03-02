# Form Builder User Guide

This guide covers how to create, configure, and publish custom registration forms for events in the UTESCA Portal. Intended for VPs and Co-Presidents.

---

## What is the form builder?

The form builder lets you define a custom registration or application form for each event. Instead of using a single fixed form for every event, you choose which fields to include, what types of inputs to use, and what validation rules to apply. The form you configure here is what attendees see on the public site when they register.

When auto-accept is off, the form acts as an application — submissions land in a review queue and you accept or reject them individually. When auto-accept is on, submitters are accepted immediately upon submission (when we reach accepted capacity limits, auto-accept is automatically turned off).

---

## Getting started

### Accessing the form builder

1. Go to your event in the portal dashboard.
2. Open the event details.
3. The registration form schema is part of the event configuration. Edit it directly in the event form section.

### Understanding field types

Each field has a **type** that determines what the registrant sees:

| Type | What the registrant sees |
|---|---|
| `text` | A single-line text input |
| `textarea` | A multi-line text box |
| `select` | A dropdown menu (pick one) |
| `radio` | Buttons in a list (pick one) |
| `checkbox` | Checkboxes in a list (pick multiple) |
| `file` | A drag-and-drop file upload area |

### Required vs optional fields

Set `required: true` on any field that must be filled in before the form can be submitted. Required fields show a red asterisk (*) on the public form. The backend rejects submissions with missing required fields regardless of frontend validation.

---

## Step-by-step tutorial

### Creating a new form from scratch

A registration form schema is a JSON object with two top-level keys:

- `fields` — an array of field definitions.
- `autoAccept` — a boolean. `true` means registrants are accepted on submission; `false` means submissions go to your review queue.

Minimal example (a single-field form with manual review):

```json
{
  "fields": [
    {
      "id": "email",
      "type": "text",
      "label": "Email Address",
      "required": true,
      "validation": {
        "pattern": "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
      },
      "placeholder": "you@mail.utoronto.ca"
    }
  ],
  "autoAccept": false
}
```

### Adding field types — with examples

**Text (short answer)**

Use for names, single-line answers, or any short input.

```json
{
  "id": "firstName",
  "type": "text",
  "label": "First Name",
  "required": true,
  "validation": { "minLength": 2, "maxLength": 100 },
  "placeholder": "Jane"
}
```

**Textarea (long answer)**

Use for open-ended questions. A character counter is shown to registrants when min/max length is set.

```json
{
  "id": "whyAttend",
  "type": "textarea",
  "label": "Why do you want to attend?",
  "required": true,
  "validation": { "minLength": 50, "maxLength": 500 },
  "placeholder": "Tell us about your interest..."
}
```

**Select (dropdown)**

Use when the registrant must pick exactly one option from a list. The dropdown is compact — good for longer option lists.

```json
{
  "id": "yearOfStudy",
  "type": "select",
  "label": "Year of Study",
  "required": true,
  "options": ["1st Year", "2nd Year", "3rd Year", "4th Year", "Graduate"]
}
```

**Radio (single choice)**

Same as select semantically (one choice), but rendered as visible radio buttons. Better when you have a short list (under ~6 items) and want all options visible at once.

```json
{
  "id": "tshirtSize",
  "type": "radio",
  "label": "T-Shirt Size",
  "required": true,
  "options": ["XS", "S", "M", "L", "XL", "XXL"]
}
```

**Checkbox (multiple choice)**

Use when the registrant can select more than one option. If required, at least one option must be checked.

```json
{
  "id": "dietaryRestrictions",
  "type": "checkbox",
  "label": "Dietary Restrictions",
  "required": false,
  "options": ["Vegetarian", "Vegan", "Gluten-free", "Halal", "Kosher", "None"]
}
```

**File upload**

Supports PDF and image files (JPEG, PNG, WebP, HEIC/HEIF), max 8 MB. The public form renders a drag-and-drop upload area. Files are uploaded to Uploadthing and linked to the registration on submit. Use the `allowedTypes` validation to restrict to specific formats for a given field (e.g., images only for a payment screenshot, PDF only for a resume).

```json
{
  "id": "resume",
  "type": "file",
  "label": "Resume (PDF only)",
  "required": false,
  "validation": {
    "maxSize": 8388608,
    "allowedTypes": ["application/pdf"]
  }
}
```

Payment screenshot example:

```json
{
  "id": "paymentScreenshot",
  "type": "file",
  "label": "Payment Screenshot",
  "required": true,
  "helperText": "Upload a screenshot of your e-transfer confirmation.",
  "validation": {
    "maxSize": 8388608,
    "allowedTypes": ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]
  }
}
```

### Configuring validation rules

Validation is defined per-field inside an optional `validation` object. See the [Validation Rules](#validation-rules) section for the full list. Validation runs both on the frontend (immediate feedback) and the backend (enforced on submit).

### Setting auto-accept mode

Set `autoAccept` at the top level of the schema:

- `"autoAccept": true` — registrants are accepted immediately. They receive a confirmation email with an RSVP link. If the event has a max capacity set, auto-accept flips off automatically once capacity is reached.
- `"autoAccept": false` — submissions enter a review queue. You accept or reject each one from the Applications tab in the portal.

### Previewing the form

The public registration form is rendered at `utesca.ca/events/{slug}` once the event is published. You can view (but not submit) the form by navigating to that URL while logged in. The form is not visible until the event status is set to `published`.

### Publishing the form

The registration form is active as soon as the event status is `published`. No separate publish step is needed for the form itself. Set the event status to `published` in the event details to make both the event listing and registration form live.

---

## Field types guide

| Type | Input rendered | Supports `options` | Supports `validation` | Supports `placeholder` |
|---|---|---|---|---|
| `text` | Single-line input | No | `minLength`, `maxLength`, `pattern` | Yes |
| `textarea` | Multi-line input | No | `minLength`, `maxLength` | Yes |
| `select` | Dropdown | Yes (required) | — | No |
| `radio` | Radio buttons | Yes (required) | — | No |
| `checkbox` | Checkboxes | Yes (required) | — | No |
| `file` | Drag-and-drop upload | No | `maxSize`, `allowedTypes` | No |

Fields that span the full form width (`textarea`, `checkbox`, `file`, `radio`) are rendered across both columns on desktop. `text` and `select` fields are rendered in a two-column grid.

---

## Validation rules

### Required fields

Set `"required": true` on any field. On the public form, required fields display a red asterisk next to the label. The backend rejects the submission if a required field is missing.

### Character limits (min / max)

Available on `text` and `textarea` fields via `minLength` and `maxLength` in the `validation` object. The textarea shows a live character counter when either limit is set.

```json
"validation": { "minLength": 10, "maxLength": 500 }
```

### Email format validation

Use a `pattern` to enforce email format on a `text` field. The pattern is a standard regex applied on both the frontend and backend.

```json
{
  "id": "email",
  "type": "text",
  "label": "Email Address",
  "required": true,
  "validation": {
    "pattern": "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
  }
}
```

To restrict to U of T email addresses specifically, tighten the pattern:

```json
"pattern": "^[^\\s@]+@(mail\\.)?utoronto\\.ca$"
```

### File size limits

File uploads enforce a hard max of **8 MB**. Set `maxSize` in bytes in the `validation` object. The value `8388608` equals 8 MB.

```json
"validation": { "maxSize": 8388608, "allowedTypes": ["application/pdf"] }
```

The backend enforces both the size limit and the allowed MIME type regardless of what is set in the schema.

---

## Best practices

### Recommended fields by event type

**Networking event**

- Name (text), Email (text with email pattern), Year of Study (select), Dietary Restrictions (checkbox if catering is involved).

**Workshop**

- Name (text), Email (text), Year of Study (select), Why Attend (textarea), any prerequisite question (radio or select).

**Social / fun event**

- Name (text), Email (text), T-Shirt Size (radio, if applicable), Dietary Restrictions (checkbox if catering).

**Application-style event (hiring fair, CEP, etc.)**

- First Name + Last Name (two text fields), Email (text with pattern), Year of Study (select), Why Attend (textarea), Resume (file). Set `autoAccept` to `false`.

### Keeping forms concise

Aim for 5–10 fields. Longer forms see higher drop-off. If you need a lot of information, consider splitting it into a short registration form and a follow-up process.

### Using clear labels and placeholders

- **Labels** are shown next to the input and appear as column headers in CSV exports. Use plain, descriptive text (e.g., "Year of Study", not "yr").
- **Placeholders** are shown inside the input as greyed-out hint text. Use them to clarify expected format (e.g., `"you@mail.utoronto.ca"`) or give a brief example.

---

## Screenshots

> Note: Screenshots below are placeholders. Replace with actual annotated screenshots once the form builder UI is finalized.

- **Form builder interface** — the event edit screen showing the registration form schema JSON editor.
- **Field editor panel** — a zoomed view of a single field definition being configured.
- **Preview mode** — the public-facing registration form as it appears on `utesca.ca/events/{slug}`.
- **Published form on public site** — the live form with a sample submission in progress, showing validation feedback.

---

## FAQ

**Can I edit a form after submissions have started?**

Yes. You can update the schema at any time. Be cautious: adding a new required field will cause future submissions to require it, but existing submissions are not retroactively validated. Removing a field does not delete data that was already collected — it will still appear in the CSV export.

**How do I require U of T email addresses?**

Add an `email` field of type `text` with a regex pattern that matches `@utoronto.ca` or `@mail.utoronto.ca`:

```json
"validation": { "pattern": "^[^\\s@]+@(mail\\.)?utoronto\\.ca$" }
```

The public form will show "Invalid format." if the pattern does not match.

**Can I export form responses?**

Yes. From the Applications tab in the portal, there is a CSV export option. It exports all registrations for the event (optionally filtered by status), including all form fields and file upload URLs. Field IDs are converted to title case in the export headers (e.g., `yearOfStudy` becomes `Year Of Study`).
