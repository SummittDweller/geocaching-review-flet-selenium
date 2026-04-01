# HTML Elements Used By Selenium Automation

This document lists every HTML element locator currently used by the automation in [src/functions.py](src/functions.py).

## Queue Filter Selection

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.ID` | `ctl00_ContentBody_ddFilter` | Reads/sets the queue filter dropdown so startup uses value `1` (All Caches Not On Hold) and Dump On-Hold to CSV uses value `3` (All Caches I'm Holding). | [src/functions.py#L62](src/functions.py#L62), [src/functions.py#L327](src/functions.py#L327), [src/functions.py#L1052](src/functions.py#L1052) | Low | Keep as-is; `id` is stable and purpose-specific. |

## Queue Scrape (Dump On-Hold to CSV)

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.TAG_NAME` | `table` | Waits for at least one table to exist before parsing the review queue page. | [src/functions.py#L279](src/functions.py#L279) | High | Wait for a queue-specific container if available (for example `#ctl00_ContentBody_...`), otherwise wait for an ID-pattern cell with XPath: `//*[self::td or self::th][contains(normalize-space(), 'GC')]`. |
| `By.CSS_SELECTOR` | `table` | Collects all tables and scores them to find the queue table that contains GC codes and publish text. | [src/functions.py#L305](src/functions.py#L305) | High | Prefer targeted table candidates: `table:has(thead th)` plus text guard (`ID`, `Title`, `Owner`) and keep score fallback only if targeted match fails. |
| `By.CSS_SELECTOR` | `tbody tr` | Reads data rows from each candidate table. | [src/functions.py#L307](src/functions.py#L307) | Medium | Keep primary selector but scope to validated queue table only; avoid scanning non-queue tables. |
| `By.CSS_SELECTOR` | `tr` | Fallback row lookup when `tbody` is not present. | [src/functions.py#L309](src/functions.py#L309) | High | Use stricter fallback: `tr:has(td)` (or XPath `./tr[td]`) to avoid header-only and layout rows. |
| `By.CSS_SELECTOR` | `thead th` | Reads column headers to map semantic columns (`ID`, `Title`, `Owner`). | [src/functions.py#L332](src/functions.py#L332) | Medium | Keep, but verify with normalized text map before trusting indices. |
| `By.CSS_SELECTOR` | `tr th` | Fallback header lookup when headers are not in `thead`. | [src/functions.py#L334](src/functions.py#L334) | High | Use first-row scoped header fallback: XPath `./tbody/tr[1]/th | ./tr[1]/th` instead of all `tr th`. |
| `By.CSS_SELECTOR` | `td` | Reads each row cell to extract listing ID, publish text, title, and owner. | [src/functions.py#L347](src/functions.py#L347) | High | Prefer semantic extraction from validated columns; for fallback, extract via per-cell regex checks (`GC...`, `Set to publish at`) and require minimum signal threshold. |

## Disable With Same Message

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.ID` | `ctl00_ContentBody_lnkDisable` | Clicks the Disable action on a review listing to open the disable-log tab. | [src/functions.py#L550](src/functions.py#L550) | Low | Keep as-is. |
| `By.ID` | `gc-md-editor_md` | Detects the disable-log editor tab and targets the text area for message entry. | [src/functions.py#L580](src/functions.py#L580), [src/functions.py#L613](src/functions.py#L613), [src/functions.py#L614](src/functions.py#L614) | Low | Keep as-is. |
| `By.CLASS_NAME` | `gc-button-primary` | Clicks the primary Post button to submit the disable message/log. | [src/functions.py#L650](src/functions.py#L650) | Medium | Prefer action-specific button locator, for example XPath constrained by text/context: `//button[contains(@class,'submit-button') and normalize-space()='Post']`. |

## Add To Bookmark List

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.ID` | `ctl00_ContentBody_lnkBookmark` | Opens the bookmark dialog/tab from the listing page. | [src/functions.py#L702](src/functions.py#L702) | Low | Keep as-is. |
| `By.ID` | `ctl00_ContentBody_Bookmark_ddBookmarkList` | Waits for and accesses the bookmark dropdown list. | [src/functions.py#L707](src/functions.py#L707), [src/functions.py#L710](src/functions.py#L710) | Low | Keep as-is. |
| `By.XPATH` | `//option[normalize-space()='{bookmark_name}']` | Finds the exact bookmark list option by visible text (trimmed). | [src/functions.py#L718](src/functions.py#L718) | Medium | Scope the XPath to the known select: `//select[@id='ctl00_ContentBody_Bookmark_ddBookmarkList']/option[normalize-space()='{bookmark_name}']`. |
| `By.ID` | `ctl00_ContentBody_Bookmark_btnCreate` | Confirms and creates the bookmark assignment. | [src/functions.py#L727](src/functions.py#L727) | Low | Keep as-is. |

## Timed Publish

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.CLASS_NAME` | `time-publish-btn` | Opens the Time Publish popup on a listing. | [src/functions.py#L779](src/functions.py#L779) | Medium | Prefer ID or stable data-attribute if available; fallback to class + nearby text match (`Time publish`). |
| `By.NAME` | `ctl00$ContentBody$timePublishDateInput` | Targets the date input used by the date picker control. | [src/functions.py#L795](src/functions.py#L795) | Low | Keep as-is. |
| `By.ID` | `timePublishTimeSelect` | Opens/selects the time dropdown control. | [src/functions.py#L816](src/functions.py#L816) | Low | Keep as-is. |
| `By.XPATH` | `//select[@id='timePublishTimeSelect']/option` | Enumerates all available time options and matches the intended time exactly. | [src/functions.py#L825](src/functions.py#L825) | Medium | Keep ID-scoped option lookup but prefer direct `Select` helper where possible. |
| `By.ID` | `ctl00_ContentBody_timePublishButton` | Confirms the timed publish schedule. | [src/functions.py#L849](src/functions.py#L849) | Low | Keep as-is. |

## Cookie Banner Handling

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.ID` | `CybotCookiebotDialogBodyButtonDecline` | Dismisses Cookiebot consent popup that can block clicks. | [src/functions.py#L1005](src/functions.py#L1005) | Medium | Add fallback button text selector (`Decline`/`Reject all`) to handle Cookiebot config variants. |
| `By.ID` | `CybotCookiebotDialog` | Waits for banner invisibility so overlays no longer intercept UI actions. | [src/functions.py#L1017](src/functions.py#L1017) | Medium | Keep invisibility wait and also verify `document.elementFromPoint(...)` is not overlaying target before click. |

## Geocaching Sign-in

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `By.ID` | `UsernameOrEmail` | Username/email field on sign-in page. | [src/functions.py#L1092](src/functions.py#L1092) | Low | Keep as-is. |
| `By.ID` | `Password` | Password field on sign-in page. | [src/functions.py#L1097](src/functions.py#L1097) | Low | Keep as-is. |
| `By.ID` | `SignIn` | Sign-in submit button. | [src/functions.py#L1102](src/functions.py#L1102) | Low | Keep as-is. |

## Review Tab Processing Helper

| Locator type | Selector | Why the script looks for it | Source | Stability risk | Hardened alternative |
|---|---|---|---|---|---|
| `"tag name"` | `a` | Collects all anchor links on a review tab for diagnostics/logging (`Found X links`). | [src/functions.py#L1223](src/functions.py#L1223) | High | Restrict to relevant links only, such as anchors with href containing `review.aspx` or admin actions. |

## Notes On Selector Strategy

- Stability risk legend: `Low` = anchored by stable `id`/`name`; `Medium` = framework/theme class or text-dependent lookup; `High` = broad structural selector likely to drift with layout changes.

- Hardened alternative notes: recommendations are intended as drop-in fallback/upgrade paths; keep current selector as primary where it is already low risk.

- The script mostly prefers stable server-generated `id` attributes for actions and form fields.
- Queue scraping intentionally uses broad table selectors plus text scoring because queue markup can vary.
- Fallback selectors (`tr`, `tr th`) are used when semantic wrappers (`tbody`, `thead`) are missing.
- Dynamic option matching in XPath uses `normalize-space()` so extra whitespace in option text does not break matching.