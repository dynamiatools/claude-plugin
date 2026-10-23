---
name: dates
description: Migrates legacy java.util.Date, Calendar, SimpleDateFormat and java.sql date types to java.time (LocalDate, LocalDateTime, Instant) in Dynamia Platform code, and says which DateTimeUtils, LocalDateRange and QueryConditions methods to use. Use when the user asks to migrate dates, remove java.util.Date, fix date or time zone bugs, or writes new code that handles dates.
argument-hint: "[path or class]"
---

# dynamia-platform:dates

New code uses `java.time`. Migrate legacy code **one class or one feature at a time**, never as a side effect of another change. The map of old to new calls is in `references/api-map.md`.

## 1. Find what is there
```
grep -rnE "java\.util\.Date|java\.sql\.(Date|Timestamp|Time)|Calendar|SimpleDateFormat|@Temporal|TemporalType|new Date\(" src
```
Also `DateTimeUtils` calls that take or return `Date` (`now()`, `today()`, `tomorrow()`, `createDate`, `addDays(Date...)`), and `DateRange`.

## 2. Choose the target type by meaning
| It is | Use |
|---|---|
| a calendar day (birth date, due date, invoice date) | `LocalDate` |
| a local date and time without zone (appointment in the user's own wall clock) | `LocalDateTime` |
| a moment on the timeline (created at, event time, token expiry, anything compared across zones) | `Instant` (or `ZonedDateTime`/`OffsetDateTime` if the zone must travel) |
| a time of day (opening hour) | `LocalTime` |
| an amount of time | `Duration` (exact) or `Period` (calendar) |
| a start/end pair | `LocalDateRange` or `LocalDateTimeRange` (not `DateRange`) |

Ask when the meaning is not clear from the name: `new Date()` stored as "date only" is the most common ambiguity, and `java.util.Date` alone cannot tell you.

## 3. Migrate in this order
1. **Edge first**: keep the public contract (JSON, DB, other modules) as is, convert inside with `DateTimeUtils.toLocalDate / toLocalDateTime / toInstant / toDate`. Remove the conversion when the other side is migrated.
2. **Entities**: change the field type and drop `@Temporal` (not used with `java.time`). `LocalDate` maps to a `DATE` column, `LocalDateTime` to `TIMESTAMP`; check the existing column type and the zone assumption (a `TIMESTAMP` written as server time now reads as a wall clock `LocalDateTime`). `TemporalType.TIME` becomes `LocalTime`. `BaseEntity` already uses `java.time` for its creation and modification dates.
3. **Queries**: `QueryParameters.addLocalDate / addLocalDateTime / addLocalTime`, `QueryConditions.gt / geqt / lt / leqt / between` with `LocalDate`, `LocalDateTime`, `LocalDateRange`, `LocalDateTimeRange`. Remove `new Date()` parameters; see `dynamia-platform:backend` `references/query-builder.md`.
4. **Services and logic**: replace `Calendar` arithmetic with `plusDays`, `DateTimeUtils.addDays(LocalDate...)`, `daysBetween(LocalDate...)`. Compare with `isBefore`/`isAfter` (`DateTimeUtils.isBetween(ChronoLocalDate...)`), not `compareTo` on mixed types.
5. **Formatting and parsing**: `DateTimeFormatter` (immutable, thread-safe; `DateTimeUtils.getFormatter(pattern)`), `DateTimeUtils.format(TemporalAccessor, pattern)`, `parseLocalDate`, `Formatters.formatDate(LocalDate)`. Never share a `SimpleDateFormat`.
6. **UI and API**: descriptors take `localdate` as a field type; ZK `Datebox` maps `LocalDate`/`LocalDateTime` fields; JSON date-only values are `yyyy-MM-dd`. Vue keeps the calendar day of date-only values (fixed in 26.10), so do not send a date-only value as midnight UTC. `LegacyDateDeserializer` still reads `yyyy-MM-dd` and `yyyy-MM-dd HH:mm:ss` strings into `LocalDate` for old clients.
7. **Tests**: use a fixed `Clock` or fixed dates, never `now()`, in assertions. Add one test around DST and month end for any logic that adds time.

## Pitfalls
- `Calendar` months are 0-based; `Month` and `LocalDate.of` are 1-based. Check every converted `get(Calendar.MONTH)`.
- `java.sql.Date#toInstant()` throws `UnsupportedOperationException`; go through `DateTimeUtils.toLocalDate(Date)`, which handles it.
- `DateTimeUtils.toLocalDate(Date)` uses `Messages.getDefaultTimeZone()` (the app's configured zone), not necessarily the JVM default. `SchedulerUtil.schedule(cron, task)` uses `TimeZone.getDefault()`. Pass the zone explicitly where they can differ.
- `LocalDate` equals `LocalDate`; `Date` equality compares milliseconds. Logic that relied on "same day at 00:00" needs `getStartOfDay` or a `LocalDate` compare.
- `DateTimeUtils.getCurrentMonthRange()` and `DateRange` still return `Date`. For ranges use `LocalDateRange.currentMonth()`, `monthToDate()`, `today()`, `lastMonth()` and the like.
- Serializable entities and JSON contracts change when a field type changes: a migrated field is a breaking change for subclasses, extensions and clients. List them and say so before editing; the framework's own extensions still have a few legacy fields (`Account`, `AccountReseller`, `UserAccessToken`) that downstream apps may depend on.
- Do not mass-replace. A `Date` that comes from a third-party API stays `Date` at that boundary.

## Finish
Run the module's tests and a compile of its dependents. Re-run the grep from step 1 and report what is left and why (boundary code, third-party API, deliberate). End with one line: what was migrated, what was not, any compatibility risk.
