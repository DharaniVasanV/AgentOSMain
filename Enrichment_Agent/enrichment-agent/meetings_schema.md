# [meetings](file:///d:/Downloads/meeting-agent/email-agent/app/main.py#35-38) Table Schema

The [meetings](file:///d:/Downloads/meeting-agent/email-agent/app/main.py#35-38) table is the central source of truth for both your Email Agent and your Meeting Agent. It contains the following properties based on your SQLAlchemy models:

## Primary Core Columns
| Column Name | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `title` | `String(255)` | Name of the meeting (e.g. "Agent Meet 8") |
| `meeting_url` | `Text` | The explicit Google Meet/Zoom URL to join |
| `meeting_date` | `Date` | The exact calendar date of the meeting |
| `start_time` | [Time](file:///d:/Downloads/meeting-agent/email-agent/app/templates/dashboard.html#449-465) | The 24h start time |
| `end_time` | [Time](file:///d:/Downloads/meeting-agent/email-agent/app/templates/dashboard.html#449-465) | The 24h end time |
| `platform` | `String(50)` | `"google_meet"`, `"zoom"`, or `"teams"` |
| [status](file:///d:/Downloads/meeting-agent/meeting-agent/app/db/crud.py#73-82) | `String(50)` | Current agent status: `"scheduled"`, `"joining"`, `"in_progress"`, `"completed"`, or `"failed"`. |
| `updated_at` | `DateTime` | Auto-updates when the bot transitions state. |

## Platform Specifics (Optional)
| Column Name | Type | Description |
|---|---|---|
| `meeting_id` | `String(255)` | The internal explicit ID (e.g. `tnr-tkov-bgv`) |
| `passcode` | `String(255)` | Zoom/Teams passcodes if needed |

## Email Agent Extra Columns
When your email agent parses an invitation, it also natively fills these into the exact same database row:
| Column Name | Type | Description |
|---|---|---|
| `email_id` | `String(255)` | The unique identifier from Gmail |
| `organizer` | `String(255)` | Email/Name of the host |
| `description` | `Text` | The agenda or email body text |
| `time_zone` | `String(50)` | Free-text timezone string |
| `created_at` | `DateTime` | Auto timestamp for insertion time |

---
*Note: The Meeting Agent only ever reads from this table, and is strictly restricted to updating the [status](file:///d:/Downloads/meeting-agent/meeting-agent/app/db/crud.py#73-82) column. All specific transcript data is stored cleanly inside the `meeting_transcripts` table referencing this Primary Key.*
