# Old to new

Names read from framework 26.10 (`commons/DateTimeUtils`, `LocalDateRange`, `LocalDateTimeRange`, `domain/query/QueryConditions`, `QueryParameters`). Check signatures in the project's version.

| Legacy | Replace with |
|---|---|
| `new Date()`, `DateTimeUtils.now()` | `Instant.now()` (moment) or `LocalDateTime.now()` (wall clock) |
| `DateTimeUtils.today()`, `tomorrow()`, `yesterday()` (return `Date`) | `LocalDate.now()`, `.plusDays(1)`, `.minusDays(1)` |
| `DateTimeUtils.createDate(y, m, d)` | `DateTimeUtils.createLocalDate(y, m, d)` or `LocalDate.of(y, m, d)` |
| `DateTimeUtils.createDate(String)` / `parse(text, pattern)` (throw `ParseException`) | `DateTimeUtils.parseLocalDate(text, pattern)` or `LocalDate.parse` |
| `addDays/Months/Years/Weeks(Date, n)` | `addDays/Months/Years/Weeks(LocalDate, n)` or `plusDays(n)` |
| `addHours/Minutes(Date, n)` | `addHours/Minutes(LocalDateTime, n)` |
| `daysBetween/monthsBetween/yearsBetween(Date, Date)` | same names with `LocalDate`; `hoursBetween/minutesBetween/secondsBetween` with `LocalDateTime` |
| `isBefore/isAfter/isBetween(Date...)`, `isAfterOrEquals`, `isBeforeOrEquals` | same names with `ChronoLocalDate`, `LocalDateTime` or `Instant` |
| `isFuture/isPast/isToday(Date)` | same names with `TemporalAccessor` |
| `getStartOfDay/getEndOfDay(Date)` | `getStartOfDay/getEndOfDay(LocalDate)` (return `LocalDateTime`) |
| `getYear/getMonth/getDay(Date)` | same names with `LocalDate`, or `date.getYear()` |
| `format(Date, pattern)`, `formatTime(Date)` | `DateTimeUtils.format(TemporalAccessor, pattern)`, `Formatters.formatDate(LocalDate)`, `formatDateTime(LocalDateTime)` |
| `Calendar` arithmetic | `LocalDate`/`LocalDateTime` `plus*`/`minus*`, `with*`, `TemporalAdjusters` |
| `SimpleDateFormat` | `DateTimeFormatter` (`DateTimeUtils.getFormatter(pattern)`) |
| `java.sql.Date/Timestamp/Time` | `LocalDate` / `LocalDateTime` or `Instant` / `LocalTime` |
| `DateRange` | `LocalDateRange` (`of`, `today`, `yesterday`, `tomorrow`, `lastMonth`, `nextMonth`, `currentMonth`, `currentYear`, `monthToDate`, `yearToDate`, `fromDaysAgo(n)`, `untilDaysFromNow(n)`, `isBetween`, `isAfter`, `isBefore`, `getDaysBetween`) or `LocalDateTimeRange` |
| `@Temporal(TemporalType.DATE)` on `Date` | `LocalDate` field, no `@Temporal` |
| `@Temporal(TemporalType.TIMESTAMP)` on `Date` | `LocalDateTime` or `Instant`, no `@Temporal` |
| `@Temporal(TemporalType.TIME)` | `LocalTime` |
| `QueryParameters.addDate(key, Date)` | `addLocalDate`, `addLocalDateTime`, `addLocalTime` |
| `QueryConditions.gt/geqt/lt/leqt(Date)` | the same with `LocalDate` or `LocalDateTime` |
| `QueryConditions.between(DateRange)` | `between(LocalDateRange)` or `between(LocalDateTimeRange)` |
| `SchedulerUtil.schedule(Date, task)` | `schedule(LocalDateTime, task)` or `schedule(LocalDateTime, ZoneId, task)` |
| `Randoms` test dates as `Date` | `Randoms.nextDate`, `nextPastDate`, `nextFutureDate`, `nextDateTime`, `nextTime` |

## Conversions kept for boundaries
`DateTimeUtils.toLocalDate(Date | LocalDateTime | LocalTime)`, `toLocalDateTime(Date | LocalDate)`, `toLocalTime(Date)`, `toInstant(Date)`, `toDate(LocalDate | LocalDateTime | LocalTime)`, each with a `ZoneId` variant where there is one. Use them at the edge of code you are not migrating, and delete them when the other side moves.

## Quick checks
- Compare two moments: `Instant#isBefore`; two days: `LocalDate#isBefore`.
- A deadline "end of the day": `LocalDate` due date, compare against `LocalDate.now(zone)`.
- Display: format in the user's locale and zone at the view, store neutral values.
