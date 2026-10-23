# email-sms

Send email (JavaMail) and SMS (AWS) with accounts, templates and logs configured in the database. Checked against `extensions/email-sms` (modules `core`, `ui`) in framework 26.10. It adds an `Email` module with CRUDs for accounts, templates and sending logs; coordinates `tools.dynamia.modules.email` and `.email.ui` (check versions in your `pom.xml`).

## Model
`EmailAccount` (SMTP settings; one is the *preferred* account per tenant), `EmailTemplate` (`name`, `description`, `subject`, `content`, `enabled`, `to`, `cc`, `bcc`, `replyTo`, `parent` template, `sendSMS`, `smsNumber`, `smsText`), `EmailAddress` (log of addresses seen), `SMSMessageLog`. They are tenant-aware through the SaaS bases.

## Send
```java
emailService.send(new EmailMessage("a@x.com", "Subject", "Hello"));          // async: CompletableFuture<EmailSendResult>
emailService.send("a@x.com", "Subject", "Hello");                             // shortcut
EmailSendResult r = emailService.sendAndWait(message);                        // blocking
String smsId = smsService.send(new SMSMessage(person.getMobileNumber(), text));  // returns the sms uuid
```
- `EmailMessage`: `to`, `addTo/addCc/addBcc`, `subject`, `content`/`plainText`, `source`, `mailAccount`, `template`, `templateName`, `templateModel` (Map for the template).
- **Templates**: `new EmailMessage(template)` or `setTemplateName("welcome")` + `setTemplateModel(Map)`. `emailService.getTemplateByName(name[, autocreate[, accountId]])` finds one (with `autocreate` a missing template is created blank; without it you get `null`). If a template has an SMS configured (`sendSMS`), sending the email also sends the SMS.
- **Accounts**: `send` needs at least one preferred `EmailAccount`, picked automatically (`getPreferredEmailAccount([accountId])`, `setPreferredEmailAccount`). You can set `mailAccount` on the message to override, and AWS credentials in the `SMSMessage`. `getNotificationEmailAccount([accountId])` is the account for system notices.
- `logEmailAddress(...)` and `getEmailAddress(address)` keep track of addresses; `clearCache(account)` after changing account settings.

## Do / don't
- Sending is **asynchronous**: do not assume it was delivered when `send` returns; check the `EmailSendResult` (or use `sendAndWait` in jobs that must know).
- From a job or startup, bind the tenant (`AccountTenants.runAs(accountId, ...)`, `saas-tenancy.md`): accounts and templates are per tenant. A task started with `SchedulerUtil` carries it for you.
- Don't build HTML strings by hand: use templates with a model.
- Keep SMTP and AWS credentials in the account records (protect database access), not in code.
- Rate-limit bulk sends and send them off the request thread.
