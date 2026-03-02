# Echo — General-Purpose Inventory Tracker & Notifier

## Goal Description

The goal is to expand the "Testudo Crawler" (currently hardcoded for UMD courses) into a **general-purpose inventory checker**. The new tool will monitor arbitrary websites (e.g. e-commerce sites, event ticketing pages) using the existing Playwright scraper and AI agent architecture. We will abstract course-specific language and models into generic **"Targets"** and **"Items"**.

---

## User Review Required

> [!IMPORTANT]
> Please review the proposed generic names (`TargetConfig`, `ItemDetail`).

> [!IMPORTANT]
> Please review the changes proposed for the AI Agent's evaluation parameters. Instead of extracting `open_seats` and `waitlist`, the AI will extract a generic `status` and `details`.

> [!NOTE]
> Default generic Telegram message template proposal: `"🚨 ALERT: {target_name} is available!"`

---

## Proposed Changes

### Configuration & Models

#### [MODIFY] `app/models/schemas.py`
- Rename `SectionStatus` to `ItemDetail`.
- Modify `ItemDetail` properties to be generic: `identifier: str`, `status: str`, `details: str` (removing `open_seats`, `waitlist`, `total_seats`).
- Rename `CourseConfig` to `TargetConfig`.
- Update `AvailabilityCheck` to evaluate `ItemDetail` items instead of sections.

#### [MODIFY] `app/config.py`
- Rename the configuration file path variable from `courses_config_path` to `targets_config_path` and target the default file `config/targets.yaml`.
- Update config loading function names (e.g., `load_courses_config` → `load_targets_config`).

#### [DELETE] `config/courses.yaml`

#### [NEW] `config/targets.yaml`
- Provide an example configuration that demonstrates a general-purpose use case (e.g., tracking a product on an e-commerce store with generic user instructions).

---

### Core Services

#### [MODIFY] `app/services/scraper.py`
- Remove hardcoded course UI selection elements from the wait list (e.g. `.course-sections`) and fall back cleanly to page content.

#### [MODIFY] `app/services/ai_agent.py`
- Update the system prompt significantly. Instruct the AI to assess availability conceptually based strictly on `user_instructions`.
- Direct the AI to populate `ItemDetail` structures for any found matching elements instead of looking for sections and seats.

#### [MODIFY] `app/services/notification.py`
- Change parameter names from `course_name`/`course_url` to `target_name`/`target_url`.
- Generalize the default `_format_availability_alert` template text.

---

### Orchestration & Web

#### [MODIFY] `app/runner.py`
- Rename variable names and methods from `course` to `target` (e.g., `check_course` → `check_target`, `course_tasks` → `target_tasks`).
- Rename the main class `TestudoCrawler` to `InventoryCrawler` or `GeneralCrawler`.

#### [MODIFY] `app/web.py`
- Rename crawler instance and references matching `app/runner.py`.
- Update the string responses in `/` and `/health` endpoints to mention generic "inventory monitoring" instead of course monitoring.

---

### Tests

#### [MODIFY] `tests/test_notification.py`
#### [MODIFY] `tests/test_scraper.py`
#### [MODIFY] `tests/test_web_service.py`
- Update mocked methods, models, and asserts to match the renamed logic (`TargetConfig`, `ItemDetail`) and expect generic return values.
