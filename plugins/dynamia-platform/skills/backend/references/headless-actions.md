# Headless (stateless) actions

One action class, many front ends. Checked against `dynamiatools/framework` 26.10 (`docs/design/HEADLESS_ACTIONS.md`, `docs/backend/DEVELOPMENT_PATTERNS.md`).

## What it is
A `LocalAction` that talks to the user only through UI-neutral ports and is marked `HeadlessCapable`. ZK runs it as always. A REST client (Vue, React, mobile) runs the same class through `POST /apps/api/metadata/entities/{id}/action/{action}`. The server keeps **no state between requests**: it uses *replay*.

## How replay works
1. The action runs from the start. Each question (`UIMessages.showQuestion`, `showInput`...) is answered, in order, with the answers the client already gave.
2. The first question without an answer stops the pass and goes to the client as an `ActionFlowStep` (status `PENDING`).
3. The original request and the answers travel in a **signed, expiring `resumeToken`**. The client calls again with the token and the new answer; the action runs again from the start, until it finishes (`SUCCESS`, step `DONE`).
4. Every pass runs in a transaction (`ReplayTransactions`); **only the pass that runs to the end commits**. A pass stopped at a question is rolled back.

## Writing one
```java
@InstallAction
public class ArchiveAction extends AbstractCrudAction implements HeadlessCapable {
    public ArchiveAction() {
        setName("Archive");
        setApplicableStates(CrudState.get(CrudState.READ));
    }
    @Override
    public void actionPerformed(CrudActionEvent evt) {
        Invoice invoice = (Invoice) evt.getData();
        UIMessages.showQuestion("Archive invoice " + invoice.getNumber() + "?", () -> {
            invoice.setArchived(true);
            evt.getController().getCrudService().save(invoice);
            UIMessages.showMessage("Archived");
        });
    }
}
```
A headless run executes the action once per question, plus one.

## Rules (break one and replay breaks)
- **Deterministic**: same request and answers give the same questions in the same order. No randomness, no `now()`-dependent branching before a question.
- **Side effects that are not database writes** (mail, files, calls to other systems) go inside the **last callback**, never before a question; a stopped pass is only rolled back for the database.
- **Ports only**: `UIMessages`, `CrudControllerAPI`, `CrudViewComponent`, and the facades `UIProgress`, `UIFiles`, `UIChoices`, `UINavigation`, `UIViews.showView`. No ZK classes. An action that imports ZK stays ZK-only (that is fine for pure-UI actions).
- Where each port ends up for a remote client: messages give `CONFIRM`/`INPUT`/`NOTIFY` steps, choices `CHOICE`, files `UPLOAD`, progress `PROGRESS`, views `DIALOG`/`VIEW`, navigation `REDIRECT`. Metadata publishes each action with a runtime: `HEADLESS`, `FLOW`, `REMOTE`, `FRONTEND` or `UNDECLARED`.
- The id REST clients see is the class name without `Action`, lower case (`archive`). Override `headlessId()` to change it, `headlessSupported()` to leave a subclass out.
- The entity class comes from the URL (`EntityMetadata.getClassName()`), never from the client. `ActionRestrictions`, state checks and `ActionFilter`s apply as for any remote action.

## What the framework already has
- `SaveAction` and `DeleteAction` are headless. `SaveAndEditAction` and `SaveAndNewAction` opt out (they leave the form on a record, which is the client's job). Reports, entity-files and saas actions were declared headless too. An arch rule (R6) fails when a standard action is neither headless nor declared `FRONTEND`.
- The hand-written `SaveRemoteAction`, `SaveFlowRemoteAction`, `DeleteRemoteAction`, `DeleteFlowRemoteAction` and `DeleteSupport` were removed: do not recreate them, make the local action headless.
- `UIMessages.withDisplayer(...)` binds a displayer per execution with a `ScopedValue`.
- Files: `UIFiles` over the `FileTransfer` SPI; uploads and downloads stream through a `TransferStore` (`/apps/api/transfers`). Check the design doc for current size limits before promising any.

## Config
`dynamia.actions.flow.secret` signs the token (set it in production), `dynamia.actions.flow.token-ttl` is its lifetime. The token is bound to the action id, so a client cannot change what it confirmed.

## When not to use replay
- The action must be written for REST clients only, needs a step replay does not produce, or is not deterministic: write a `FlowRemoteAction` (explicit `start` / `resume` state machine). `DIALOG`, `REDIRECT`, `CALL` and `CUSTOM` steps still come from `FlowRemoteAction`; REDIRECT/CALL flow steps are marked experimental.
- Pure UI actions (find, filters, renderers) are `FRONTEND`: the front end writes its own client action in TypeScript (`registerClientAction`).
- Remote actions no longer have a `CLIENT` runtime (`ActionRuntime.CLIENT` was removed).

## Testing
Use the `runEverywhere` style tests (the same assertions in ZK and headless mode) as the converted actions in `entity-files` do.
