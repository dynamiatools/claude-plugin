# entity-files

Attach files to entities, with a file explorer, local, S3 or Buckie storage and REST upload/download. Checked against `extensions/entity-files` (modules `core`, `ui`, `s3`) in framework 26.10 and the Buckie site (https://dynamia.tools/buckie/). Storage backends: **local disk, AWS S3 (and S3-compatible endpoints) and Buckie**. There is no MinIO module; the README's mention of one is stale, and so are its version numbers: use the project's own `pom.xml`.

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
`EntityFileStorage` (`getId`, `getName`, `upload`, `download`, `delete`, `reloadParams`). Three implementations:
| Backend | Id | Module | Notes |
|---|---|---|---|
| `LocalEntityFileStorage` (default) | `LocalStorage` | `core` | files under `LOCAL_FILES_LOCATION`; also `LOCAL_USE_HTTPS`, `LOCAL_CONTEXT_PATH`, `LOCAL_STORAGE_DEFAULT_CDN` |
| `S3EntityFileStorage` | `AWSS3Storage` | `s3` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_KEY`, `AWS_S3_REGION`, `AWS_S3_BUCKET`, `AWS_S3_ENDPOINT`, `AWS_S3_OVERRIDE_ENDPOINT`; a custom endpoint lets S3-compatible servers work |
| `BuckieEntityFileStorage` | `buckie` | `core` (package `remote`) | a remote Buckie server, below |
Each parameter is read from the Spring environment first, then from the application parameters (the `Parameters` table the app manages). To add a backend, implement `EntityFileStorage` as a bean.

**Which backend is used.** Application parameter `DEFAULT_STORAGE_ID` (default `LocalStorage`) names the storage for new uploads; if no storage has that id the service logs a warning and falls back to local. Every `EntityFile` stores the id of its storage in `storageInfo`, so files uploaded earlier keep working from the storage they were written to. `FORCE_STORAGE` makes the service ignore `storageInfo` and always use the default one (use it only when migrating, after copying the content). `getStorage(name)` returns a storage by id. The action `MoveEntityFileLocalToRemoteStorageAction` moves local files to the remote storage and `ReloadEntityFileStoragesAction` reloads the parameters.

## Buckie
Buckie is a lightweight file server with an S3-style REST API, built by Dynamia Soluciones (MIT, https://dynamia.tools/buckie/). No database and no cloud account: one process and a disk. It exists in Node.js (`npm install -g @dynamia-tools/buckie`, `buckie serve --host 0.0.0.0 --port 8080`; also local filesystem and SFTP buckets, thumbnails with Sharp, a TypeScript SDK) and in PHP (Composer `dynamia-tools/buckie`; local filesystem, GD/Imagick thumbnails). Both expose the same API.
- **Concepts**: a *bucket* is a named pointer to a directory; an *identity* is a name with a bcrypt-hashed secret (a service account); a *grant* links an identity to a bucket with `read`/`write`/`delete` and an optional path prefix (for example a per-tenant folder). Everything is stored in `.buckie/config.json`, created on first run: back it up or inject it in Docker.
- **CLI**: `buckie create bucket <name> <path>`, `buckie create identity <name> <secret>`, `buckie grant <identity> <bucket> --read --write --delete [--prefix /path/]`, or `buckie provision` for all three; `buckie list buckets|identities`.
- **API**: `PUT /{bucket}/{key}` upload, `GET` download, `DELETE`, `GET /{bucket}/{dir}/` list, `GET /{bucket}?limit=50` paged list, `GET /health` public. Auth on every other call: headers `X-Buckie-Identity` and `X-Buckie-Secret`, or HTTP Basic. Images can be resized with `?w=&h=&fit=cover|contain|fill&format=webp|jpeg|png` and are cached.
- **Dynamia parameters** (environment or application parameters; the names keep the old `SFS_` prefix): `SFS_URL` (default `http://localhost:8081`), `SFS_BUCKET` (default `files`), `SFS_IDENTITY`, `SFS_SECRET`. The storage sends the identity and secret in the `X-Buckie-*` headers.
- **Keys** follow the local layout: `account{accountId}/{subfolder}/{storedFileName or uuid_name}` (the file name is simplified: accents and special characters replaced), so one bucket can serve all tenants, and a grant with prefix `account5/` confines an identity to one.
- Upload streams the input (no whole-file buffering); the browser gets the file through the application's `/storage/...` handler, which keeps the credentials on the server; image thumbnails are requested from Buckie with `w`/`h`.
- Setup: run Buckie, create a bucket and an identity with `write`/`read`/`delete` on it, add the four parameters, set `DEFAULT_STORAGE_ID=buckie`. The Vue `@dynamia-tools/files-sdk` works with all three storages.
- Don't put the secret in source control; use environment variables or the parameters table. Check that the Buckie port is reachable only from the application servers, or behind HTTPS.

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
