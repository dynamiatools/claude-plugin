# Security: chains, JWT, sessions and CurrentUser

Extension `security` (`DynamiaSecurityConfig`, `JWTAuthenticationFilter`, `CurrentUser`, `SecurityTenancy`) and `docs/backend/WEB_SECURITY_SESSIONS.md`, framework 26.10. Needs Spring Security and Spring Boot. The README of the extension is a stub with old versions: use the project's `pom.xml`.

## Three filter chains
| Chain | Matches | Authenticates with | State |
|---|---|---|---|
| API | `/api/**` | `DYNAMIA_JWT` cookie or `Authorization: Bearer` (`JWTAuthenticationFilter`) | stateless, CSRF off. Public: `/api/public/**`, `/api/v2/public/**`, `/api/security/login` |
| Apps API | `/apps/api/**` | web session (it never creates one) or Bearer; the JWT cookie is ignored; `AppsApiAccountFilter` resolves the account | writes (`POST`, `PUT`, `PATCH`, `DELETE`) must be same-origin (`AppsApiSameOriginAuthorizationManager`); unauthenticated gets a JSON 401 |
| Web | everything else (the shell, `/login`, `/logout`) | the HTTP session (`JSESSIONID`), form login at `/login`, JSON login at `/login/json` | `IF_REQUIRED` |
`POST /login/json` creates both the session (read by the shell) and the JWT cookie (read by the API). **A page refresh depends on the `JSESSIONID`**, not on the JWT: the web chain has no JWT filter.

## Rules the code follows (do not undo them)
- The API chain **never rotates the `JSESSIONID`** (`sessionFixation().none()`): Spring's default ran on every JWT call and parallel calls left the browser with an invalid id, so the next refresh went to `/login`.
- A token request leaves no session behind: `JWTAuthenticationFilter` invalidates sessions created while serving a request that came without one (SDKs, mobile, scripts). The response may still carry a `Set-Cookie` of that invalid session.
- `CurrentUser` is session scoped and **not rebuilt on every call**: a change of permissions is seen after at most 5 minutes (or on a new session).
- Unauthenticated `/api` and `/apps/api` calls answer JSON `401`, never a redirect to `/login`.

## Known limits
- A JWT without `JSESSIONID` (cookie deleted, server restarted with in-memory sessions) still ends at `/login` for the shell although the API would accept it.
- The JWT lifetime and the container session timeout are separate: the doc says 60 minutes (15 days with `X-Remember-Me`) while the property default is 2 hours; set `dynamia.security.*` explicitly (`configuration-properties.md`) and align the session timeout.

## Model and services
- `User` (`BaseEntity`, `UserDetails`, `AccountAware`, `@TenantId` account): `username`, `password`, `uuid`, account/credentials flags, `passwordExpired`, `fullname`, `email`, `phoneNumber`, `mobileNumber`, `photo` (an `EntityFile`), `profiles` (`UserProfile`), `userKey`, `reference`. `Profile` and `Permission` give roles and fine permissions; `UserAccessToken` is an API access token.
- `SecurityService`: `createUser`, `setNewPassword`, `resetPassword`, `validatePassword`, `loadUserByUsername`, `getUserByEmail`, `getProfilesByAccountId`, `findAccessToken`, `requestToken`, `getCurrentSessionUser`. `UserService`: lookups by account and username/token. `JWTService`: `generateToken`, `extractUsername`/`Roles`/`Claim`, `isTokenValid`, `shouldRefresh`. Passwords go through the app's `PasswordEncoder`; never store plain text.
- `CurrentUser.get()` in UI/session code: `getUser()`, `getUsername()`, `hasProfile(name|id)`, `hasPermission(name)`, `isAdmin()`, `isLogged()`, `getPermissions()`, `reload()`. Prefer permission checks over profile names in code.
- Tenancy: `User` is tenant-aware. Lookups that happen before an account exists (login by username/token, startup defaults) use `SecurityTenancy.withRootIfNoAccount(...)` (`saas-tenancy.md`).

## Extension points
- `SecurityConfigurationInterceptor` (beans): `configure(AuthenticationProvider)`, `configure(HttpSecurity)`, `configure(WebSecurity)` to add rules, filters or ignored paths to the chains.
- `IgnoringSecurityMatcher`: paths Spring Security should ignore (static resources).
- `LoginListener` (`onLoginSuccess(User)`, `onTokenLogin(User)`, `onLoginPage(params)`, `getPriority()`) and `LoginControllerInterceptor` (`login(request, viewName, params)`): hook into login.
- `SecurityContextCapturer` carries the security context into async tasks (`SchedulerUtil`), like the tenant capturer.
- Audit: `AuditableSecurityCrudServiceListener`, `UserLoginLogger`.

## Properties (`dynamia.security`)
`jwt-secret-key` (set it; without it a random key is used with a warning and tokens break on restart and between nodes), `jwt-expiration`, `jwt-refresh-interval`, `remember-me-duration`, `issuer`.

## Rules
- A new endpoint under `/api/**` is JWT-only; a new one for your own front end belongs under `/apps/api/**` (`navigation-metadata.md`). Authorize in the method too (roles, ownership), not only by path.
- Don't disable CSRF or same-origin checks on `/apps/api` writes; don't accept the JWT cookie there.
- Don't put secrets in tokens' custom claims; tokens are signed, not encrypted.
- Don't store the `User` entity in long-lived caches; use ids.
- When login "works but refresh goes to /login", check `JSESSIONID`, the session timeout and the proxy cookie settings before the JWT.
