# entity-files

Attach files to entities, with a file explorer, local or S3 storage and REST upload/download. Checked against `extensions/entity-files` (modules `core`, `ui`, `s3`) in framework 26.10. The README still shows old versions and a `minio` module that is not in the repository: use the project's own `pom.xml`.

## Model
`EntityFile` (`tools.dynamia.modules.entityfile.domain`, table `mod_entity_files`) is a `BaseEntity` with: `name`, `type` (`EntityFileType`), `extension` (`dir` for directories), `contentType`, `size`, `description`, `state`, `uuid` (random, used in URLs), `parent` (directories), `shared`, `targetEntity` + `targetEntityId`/`targetEntitySId` (the owner), `storageInfo`, `subfolder`, `storedFileName`, `remoteURL`, `externalRef`, `accountId`. It has its own `accountId` but is **not** a `@TenantId` entity (entity-files does not depend on SaaS): filter by account yourself in custom queries.

## Attach to an entity
A one-file field is a plain association:
```java
@OneToOne private EntityFile photo;
@OneToOne private EntityFile cover;
```
The UI module adds `FileAction` (CRUD read state) to open the file explorer for any entity; in code: `EntityFileUtils.showFileExplorer(entity)`. Implement `EntityFileAware` (`getFilesCount`/`setFilesCount`) to keep a count of attached files on the entity (the module updates it; `syncEntityFileAware()` resyncs all).

## EntityFileService (inject it)
| Need | Method |
|---|---|
| Create a file for an entity | `createEntityFile(UploadedFileInfo, target[, description])` |
| Directory | `createDirectory(ownerEntity | parentFile, name, description)` |
| List | `getEntityFiles(entity[, parentDirectory])`, `getEntityFiles(Class, id, parent)` |
| Get by uuid | `getEntityFile(uuid)` |
| Content | `download(entityFile)` returns `StoredEntityFile`; `download(entityFile, File out)` |
| Delete | `delete(entityFile)` (finds the file's storage and calls its `delete`; check in the project whether the row is also removed) |
| Upload before the owner exists | `createTemporalEntityFile(UploadedFileInfo)`, then `configureEntityFile(target, entityFile)` |
```java
var info = new UploadedFileInfo(file);               // also Path, FileInfo, or fullName + contentType + inputStream
EntityFile photo = entityFileService.createEntityFile(info, person);
person.setPhoto(photo);
crudService.update(person);
```
`UploadedFileInfo` carries `fullName`, `contentType`, `inputStream`, `length`, `parent`, `shared`, `subfolder`, `storedFileName`, `accountId`, `externalRef`.
**Temporal files**: a form can upload first and save the entity later. A temporal file has `targetEntity = "temporal"`. `TemporalEntityFileCrudListener` runs after create/update, finds properties of type `EntityFile` holding a temporal file, calls `configureEntityFile(entity, file)` to bind it to the new owner, and increments `filesCount` when the entity is `EntityFileAware`. Do not delete the temporal row yourself.

## Storage
`EntityFileStorage` (`getId`, `getName`, `upload`, `download`, `delete`, `reloadParams`). Implementations: `LocalEntityFileStorage` (default), `S3EntityFileStorage` (module `s3`), a remote `BuckieEntityFileStorage`. Pick by name with `getStorage(name)`; `isForceEntityFileStorage()` says whether a storage is forced. Local path: the environment property or application parameter `LOCAL_FILES_LOCATION`. To add a backend, implement `EntityFileStorage` as a bean.

## Serving, access, cache
- REST: `GET /storage/{uuid}/{file}` (serves the file), `POST /api/storage/upload` (multipart), `POST /api/storage/upload-base64` (JSON), `GET /api/storage/{uuid}/export`. The Vue client is `@dynamia-tools/files-sdk`.
- Access control: a `shared` file is public. For a non-shared file the controller asks an `EntityFileSecurityProvider` bean (`canAccess(entityFile, params, headers)`; `generateToken(entityFile)` appends a token to the URL) and answers 403 when it says no. **Without such a bean nothing is checked**, so anyone who has the uuid URL can download any file. Register one before exposing the module.
- `EntityFileAccountProvider` resolves the current account id and validates a file against it (multi-account apps).
- `EntityFileCache` (`get/put/evict/clear`, `resolveTtl`) caches downloaded content; the local cache is the default.

## Headless actions
`ReloadEntityFileStoragesAction` and `MoveEntityFileLocalToRemoteStorageAction` are headless: they work from the Vue front end.

## Do / don't
- Store the `EntityFile` reference on the entity, not a path or URL.
- Use the uuid URL, never a filesystem path, in views.
- Large files: stream (`StoredEntityFile`, transfers), do not read whole bytes into memory.
- Back up the storage location together with the database; the table holds metadata only.
- Do not query `mod_entity_files` directly; use the service and `CrudService`.
