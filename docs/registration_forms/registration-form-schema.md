# Registration Form Schema — Developer Reference

Technical details on how the dynamic registration form system works across the backend, frontend, and database.

---

## Field ID casing convention

**Use camelCase for all field IDs.** This is the current standard across the codebase.

The backend Pydantic models use `alias_generator=to_camel` (see `events/models.py`), which converts Python snake_case attribute names to camelCase in JSON serialization. The TypeScript types in both `utesca-frontend` and `utesca-portal-frontend` use camelCase throughout. The name-extraction helpers in both the backend service (`registrations/service.py:_extract_name`) and the portal utility (`schema-utils.ts:extractName`) look for `fullName`, `firstName`, `lastName` first, falling back to `full_name`, `first_name`, `last_name` only for backward compatibility with data that was already persisted.

**Do not use snake_case for new field IDs.** Legacy snake_case fallbacks exist solely to avoid breaking existing registration data.

Examples:

| Correct | Incorrect (legacy only) |
|---|---|
| `firstName` | `first_name` |
| `lastName` | `last_name` |
| `yearOfStudy` | `year_of_study` |
| `dietaryRestrictions` | `dietary_restrictions` |
| `whyAttend` | `why_attend` |
| `tshirtSize` | `tshirt_size` |

The top-level schema key `autoAccept` (not `auto_accept`) is what the API serializes. In Python code the attribute is `auto_accept`, but `to_camel` converts it to `autoAccept` in JSON.

---

## Schema structure

The schema is stored as a JSONB column (`registration_form_schema`) in the `events` table. It is defined by the `RegistrationFormSchema` Pydantic model in `utesca-backend/src/domains/events/models.py`:

```python
class RegistrationFormSchema(BaseModel):
    auto_accept: bool = False                          # serializes as autoAccept
    fields: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
```

`fields` is typed as `List[dict]` in Pydantic — individual field structure is not enforced at the model level. Validation of field contents happens at submission time in `RegistrationService.validate_form_data`.

### TypeScript types

**Portal** (`utesca-portal-frontend/src/types/registration.ts`):

```typescript
interface FormField {
  id: string;
  label: string;
  type: string;
  required: boolean;
  validation?: Record<string, unknown>;
  options?: string[];
}

interface RegistrationFormSchema {
  autoAccept?: boolean;
  fields: FormField[];
}
```

**Public site** (`utesca-frontend/src/types/registration.ts`):

```typescript
type RegistrationFieldType = 'text' | 'textarea' | 'select' | 'radio' | 'checkbox' | 'file';

interface RegistrationFieldValidation {
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  maxSize?: number;
  allowedTypes?: string[];
}

interface RegistrationFormField {
  id: string;
  type: RegistrationFieldType;
  label: string;
  placeholder?: string;
  required?: boolean;
  options?: string[];
  helperText?: string;
  validation?: RegistrationFieldValidation;
}

interface RegistrationFormSchema {
  autoAccept?: boolean;
  fields: RegistrationFormField[];
}
```

The public-site types are more specific (enumerated `type`, typed `validation`). The portal types are looser because the portal may need to handle schemas that include fields or keys not yet reflected in a strict interface.

---

## Field definition properties

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Yes | camelCase. Used as the key in `form_data` on submission. Must be unique within a schema. |
| `type` | string | Yes | One of: `text`, `textarea`, `select`, `radio`, `checkbox`, `file`. |
| `label` | string | Yes | Displayed next to the input. Used as the CSV export header (converted to title case). |
| `required` | boolean | Yes | `true` = backend rejects submission if value is missing. |
| `placeholder` | string | No | Hint text inside the input. Supported on `text` and `textarea` only. |
| `helperText` | string | No | Shown below the input as a description. Rendered by the public form component. |
| `options` | string[] | Conditional | Required for `select`, `radio`, `checkbox`. Ignored for other types. |
| `validation` | object | No | Type-specific rules. See below. |

### Validation object shape by field type

**`text` and `textarea`:**

```json
{
  "minLength": 2,
  "maxLength": 500,
  "pattern": "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
}
```

- `minLength` / `maxLength`: enforced on the trimmed string value.
- `pattern`: a JavaScript-compatible regex string. Matched with `re.match` on the backend (Python). The pattern is tested against the raw value — anchor it (`^...$`) if you want a full-string match.

**`file`:**

```json
{
  "maxSize": 8388608,
  "allowedTypes": ["application/pdf", "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]
}
```

- `maxSize`: in bytes. The backend hard-caps at 8 MB (`8388608`) regardless of schema value. See `RegistrationService.MAX_FILE_SIZE`.
- `allowedTypes`: MIME types. The backend restricts to `{"application/pdf", "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}` regardless of schema value — types outside this set are rejected even if listed in the schema. See `RegistrationService.ALLOWED_TYPES`.

**`select`, `radio`, `checkbox`:** no `validation` object is used. Option membership is enforced against the `options` array at submission time.

---

## Validation flow

Validation runs in two places.

### Frontend (public site)

`RegistrationForm.tsx` calls `validateField` for each field on submit. The logic is split by type:

- `validateTextField` — checks required, minLength, maxLength, pattern (via `new RegExp`).
- `validateCheckboxField` — checks that at least one option is selected if required.
- `validateFileField` — checks required, maxSize, allowedTypes. Note: file validation on the frontend also has a hard 2 MB / PDF-only guard in `handleFileUpload` that runs before the upload begins.

Errors are rendered inline under each field. The form does not submit if any field has errors.

### Backend

`RegistrationService.validate_form_data` (`registrations/service.py`) iterates over `fields` in the schema and validates the corresponding values in the submitted `form_data` dict:

- `_validate_text` — minLength, maxLength, pattern (via `re.match`). Used for both `text` and `textarea`.
- `_validate_choice` — checks value is in `options`. Used for `select` and `radio`.
- `_validate_checkboxes` — checks all selected values are in `options`. Used for `checkbox`.
- `_validate_files` — checks maxSize and allowedTypes against `FileMeta` records. Used for `file`.
- `_is_missing_required` — checks for missing values across all types. For `file`, "missing" means no linked file records for that field.

If any errors are returned, the endpoint responds with 400 and the error details. The submission is not persisted.

---

## Auto-accept and capacity

When `autoAccept` is `true`, `submit_registration` sets the registration status to `accepted` immediately (line 254 of `service.py`). A confirmation email with an RSVP link is sent as a background task.

If the event has `max_capacity` set, `_disable_auto_accept_if_capacity_reached` runs after each submission. If the total registration count meets or exceeds capacity, the schema's `autoAccept` is flipped to `false` in the database. Subsequent submissions will land in the review queue.

---

## File upload mechanics

File uploads are two-phase. See `docs/file-upload.md` for the full flow. Summary:

1. Frontend uploads the file to Uploadthing, receives a `ufsUrl`.
2. Frontend calls `POST /api/v1/events/{slug}/upload-file` with file metadata and an `uploadSessionId` (generated once per form load). Backend persists a row in `registration_files`.
3. On form submit, the same `uploadSessionId` is sent to `POST /api/v1/events/{slug}/register`. Backend links all file records with that session ID to the new registration and sets `scheduled_deletion_date` to event date + 30 days.

Pre-submit delete: if the user removes a file before submitting, the frontend calls `DELETE /events/{slug}/upload-file/{file_id}` (removes the DB row) and then the Next.js `/api/uploadthing/delete` route (removes the file from Uploadthing).

---

## Name and email extraction

Several parts of the system need to pull a name or email out of arbitrary `form_data`. The conventions are:

- **Email:** always use `"id": "email"`. Both `_extract_name` in the backend service and `extractEmail` in `schema-utils.ts` look for this key directly.
- **Name:** use either `"id": "fullName"` (single field) or a pair `"id": "firstName"` / `"id": "lastName"`. The extraction helpers try `fullName` first, then concatenate `firstName` + `lastName`.

If your form does not include any of these IDs, name extraction returns `null` (backend) or `"Unknown"` (portal). Confirmation and acceptance emails will send with a missing name in that case.

---

## CSV export

`RegistrationService.export_registrations` flattens `form_data` and builds rows with metadata columns (Registration ID, Status, timestamps, etc.) followed by one column per form field.

- Field IDs are converted to title case via `_camel_to_title`. `yearOfStudy` becomes `Year Of Study`.
- Nested objects are flattened with dot separators (e.g., `address.city`).
- Arrays of strings (checkbox values) are joined with `, `.
- File fields get a separate column with the header `{Field} File URL` containing the Uploadthing URL(s).

---

## Key file locations

| File | What it contains |
|---|---|
| `utesca-backend/src/domains/events/models.py` | `RegistrationFormSchema` Pydantic model, `EventCreate`/`EventUpdate`/`EventResponse` |
| `utesca-backend/src/domains/events/registrations/service.py` | Validation logic, submission, auto-accept, export, email dispatch |
| `utesca-backend/src/domains/events/registrations/repository.py` | DB operations for registrations |
| `utesca-backend/src/domains/events/registrations/files_repository.py` | DB operations for `registration_files` |
| `utesca-backend/src/domains/events/registrations/public_api.py` | Public endpoints (register, upload, RSVP) |
| `utesca-backend/src/domains/events/registrations/portal_api.py` | Portal endpoints (list, accept, reject, export) |
| `utesca-frontend/src/types/registration.ts` | Public-site TypeScript types |
| `utesca-frontend/src/components/pages/events/RegistrationForm.tsx` | Public registration form component |
| `utesca-portal-frontend/src/types/registration.ts` | Portal TypeScript types |
| `utesca-portal-frontend/src/lib/schema-utils.ts` | Name/email extraction, field formatting utilities |
