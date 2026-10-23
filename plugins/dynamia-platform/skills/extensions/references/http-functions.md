# http-functions

A versioned function runtime over HTTP: configure a call to a third-party API once (method, URL, headers, body template) and call it by name from Java or over REST. Checked against `extensions/http-functions` and its README in framework 26.10 (modules `core`, `ui`).

## Model
`DynamiaHttpFunction`: `name` (free text; use `Namespace.action`, for example `WhatsApp.sendMessage`), `functionVersion` (int from 1), `method`, `url`, `contentType` (default `application/json`), `bodyTemplate`, `headers` (one `Name: value` per line), `status` (`DRAFT`, `ACTIVE`, `INACTIVE`, `DELETED`; only `ACTIVE` can be called), `metadata` (informative), `parameters`. `url`, `bodyTemplate` and `headers` use `${param}` placeholders filled at call time. `(name, functionVersion)` is unique **per account** (database index and `DynamiaHttpFunctionValidator`); a function needs a `url` to become `ACTIVE`. `interfaceName`/`methodName` are reserved and not implemented.
`DynamiaHttpFunctionParameter`: `name`, `type` (`STRING` default, `NUMBER`, `BOOLEAN`, `DATE` `yyyy-MM-dd`, `DATETIME` `yyyy-MM-dd HH:mm:ss`), `required`, `defaultValue`, `position`.

## Register
Through the back office page (module `ui`, a "Http Functions" group in the `saas` module) or code:
```java
var f = new DynamiaHttpFunction();
f.setName("WhatsApp.sendMessage");
f.setFunctionVersion(1);
f.setMethod(HttpMethod.POST);
f.setUrl("https://api.example.com/v1/messages");
f.setBodyTemplate("{\"to\":\"${number}\",\"text\":\"${message}\"}");
f.setHeaders("Authorization: Bearer ${apiToken}");
f.setStatus(FunctionStatus.ACTIVE);
// addParameter(...) for number, message (required) and apiToken
crudService.create(f);
```

## Call
```java
FunctionResult r = DynamiaFunctions.call("WhatsApp.sendMessage", Map.of("number", "123", "message", "Hi"));
FunctionResult v2 = DynamiaFunctions.call("WhatsApp.sendMessage", 2, params);        // explicit version
FunctionResult d  = DynamiaFunctions.call("Invoicing.generatePdf", params, true);     // auto-register a DRAFT placeholder instead of throwing
DynamiaFunctions.callAsync("WhatsApp.sendMessage", params).thenAccept(x -> ...);      // virtual thread
```
`FunctionResult`: `isSuccess()`, `isBinary()`, `isJson()`, `toJson()` (a Map), `toJson(Dto.class)`, `getBinaryData()`. Without a version, the **highest ACTIVE** version runs; an explicit version runs whatever its status (test a DRAFT before promoting it). Versions are explicit and only grow; do not edit a released version, add the next one.
Over HTTP: `POST /api/functions/{name}` with `{ "params": { ... } }`, version by header `X-Dynamia-Version: 2` or `?v=2`. JSON answers `{ "success": true, "data": ... }` or `{ "success": false, "error": "..." }`; binary targets (image, PDF, CSV) are streamed as is with their content type. The TypeScript client is `@dynamia-tools/http-functions-sdk`.

## Errors
Java: `FunctionNotFoundException` (404), `FunctionInactiveException` (404), `ValidationError` (400: missing required parameter or value not coercible), `FunctionExecutionException` (500: network error or non-2xx from the target; wraps the cause). Catch the ones you can act on.

## Security (read this)
- **The module does not authorize callers.** `/api/functions/{name}` is under `/api`, so protect that path in the host app's security chain (JWT or roles). Anyone allowed to call it can run any ACTIVE function with any `params`.
- Secrets are usually passed as parameters (`${apiToken}`). From REST, the caller supplies them. For third-party credentials, either do not expose the endpoint to untrusted callers, or call the function from server code with the secret taken from server configuration and never from the request.
- Do not log full `headers`/`bodyTemplate` after rendering; they contain tokens.
- Functions are per account (tenant): create them under the right account; use `AccountTenants.runAs` in jobs (`saas-tenancy.md`).
- No response cache, metrics or sandbox exist yet.

## Do / don't
- Use it for integrations whose URL or credentials change per environment or tenant; for a stable internal call, a normal client class is simpler.
- Name `Namespace.action`, one version per contract change, keep old versions ACTIVE until callers move.
- Wrap `DynamiaFunctions.call` in a small typed service so callers do not depend on string names and parameter maps.
- Test each function with the back office "Test" action before using it in code.
