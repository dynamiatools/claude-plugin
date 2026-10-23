# Configuration properties (`dynamia.*`)

Read from framework 26.10 (`ApplicationConfigurationProperties`, `DynamiaSecurityConfigurationProperties`, `AccountMigrationProperties`, `@Value` keys in `platform` and `extensions`, the example apps). Spring relaxed binding applies: `open-persistence-in-view`, `openPersistenceInView` and `OPEN_PERSISTENCE_IN_VIEW` are the same key. Some values are **application parameters** (the `Parameters` table the app manages) instead of properties; the entity-files and Buckie names (`LOCAL_FILES_LOCATION`, `SFS_URL`, `DEFAULT_STORAGE_ID`...) are read from the environment first, then from there.

## `dynamia.app` (`ApplicationConfigurationProperties`)
| Key | Default | Meaning |
|---|---|---|
| `name`, `shortName`, `description`, `company`, `author`, `license`, `url` | none | identity shown in the UI and in the app metadata |
| `version`, `build` | none | version and build id (often filled by Maven filtering: `@project.version@`, `@timestamp@`) |
| `template` | none (`default` if blank) | UI template/theme, for ZK `Dynamical` or a custom one |
| `defaultSkin`, `defaultLogo`, `defaultIcon` | none | skin and image paths (`/zkau/web/images/logo.png`) |
| `basePackage` | none | base package for scanning the app's own components |
| `jdni` (sic) | none | JNDI datasource name |
| `webCacheEnabled` | `false` | web caching of resources |
| `open-persistence-in-view` | `true` | keep one `EntityManager` open while ZK renders; `false` makes views use `BeanMap` rows and requires `@InitializeOnLoad` (see `loading-collections.md`, `bean-map-dto.md`) |
| `lazy-load-no-trans` | `false` | temporary Hibernate safety net for lazy loads outside a transaction |
| `apiBasePath` | `/api` | base path of REST endpoints |
| `properties` | empty map | free key-values for the app (`dynamia.app.properties.foo=bar`) |
| `metadata.http-cache` | off | `etag` turns on ETag caching of metadata endpoints (`navigation-metadata.md`) |

## Persistence and CRUD
| Key | Default | Meaning |
|---|---|---|
| `dynamia.crud.load-collections` | `annotated` | `annotated`, `all` or `none` (`loading-collections.md`) |
| `dynamia.crud.load-depth` | `1` | depth for `all` |
| `spring.jpa.open-in-view` | Spring's | only affects Spring MVC; set `false` in Dynamia apps and use `dynamia.app.open-persistence-in-view` for ZK |

## Actions and files (headless)
| Key | Default | Meaning |
|---|---|---|
| `dynamia.actions.flow.secret` | random per JVM, with a warning | signs `resumeToken`; **min 32 characters**; must be the same on all nodes |
| `dynamia.actions.flow.require-secret` | `false` | startup fails without a secret; also required when the `prod` profile is active |
| `dynamia.actions.flow.token-ttl` | `PT10M` | lifetime of a resume token |
| `dynamia.actions.flow.max-token-bytes` | `16384` | largest accepted token (characters) |
| `dynamia.ui.files.dir` | `${java.io.tmpdir}/dynamia-transfers` | where transferred files wait |
| `dynamia.ui.files.ttl` | `PT30M` | how long they live |
| `dynamia.ui.files.quota` | `0` (no limit) | total bytes in the store |
| `dynamia.ui.files.max-file-size` | `104857600` (100 MB) | per file; a bigger upload gets `413` |
| `dynamia.ui.files.max-files` | `10` | files per transfer |
The transfers endpoint (`POST /apps/api/transfers`) streams raw bodies and bypasses Spring multipart limits; `max-file-size` is the limit that applies. Define your own `TransferStore` bean to replace the local disk store.

## Reports (`extensions/reports`)
`dynamia.reports.ui` (`vue`|`zk`, default `vue`), `max-rows` (100000), `query-timeout` (60 s), `preview-limit` (50), `designer-roles` (empty = nobody), `allowed-drivers` (default MySQL, MariaDB, PostgreSQL, Oracle, SQL Server), `encryption-key` (AES-256-GCM for datasource passwords; set once, never change).

## Security (`dynamia.security`, extension `security`)
| Key | Default |
|---|---|
| `jwt-secret-key` | none: a temporary random key with a warning, so tokens break on restart and between nodes; always set it |
| `jwt-expiration` | `2h` |
| `jwt-refresh-interval` | `10d` |
| `remember-me-duration` | `15d` |
| `issuer` | `dynamia` |

## SaaS
`dynamia.saas.root-tenant-id` (default `0`, never `-1`; `saas-tenancy.md`). Account migration, prefix `dynamia.saas.migration`: `chunk-size` (500), `output-directory` (`${java.io.tmpdir}/saas-migration`, transient only), `compression-enabled` (`false`), `max-concurrent-jobs` (5), `export-parallelism` (4), `fail-on-entity-error` (`false`).

## Other keys
`schedulingEnabled` (no prefix, default `true`) is read by `SchedulerUtil.isSchedulingEnabled()` (`utilities.md`). Entity-files / Buckie / S3 parameters are listed in `dynamia-platform:extensions` `references/entity-files.md`.

## Example (`application.yml`)
```yaml
spring:
  jpa:
    open-in-view: false
dynamia:
  app:
    name: My App
    basePackage: com.acme.app
    template: Dynamical
    open-persistence-in-view: false      # use BeanMap rows, plan collections
    metadata:
      http-cache: etag
  crud:
    load-collections: annotated
  actions:
    flow:
      secret: ${FLOW_SECRET}             # 32+ chars
  security:
    jwt-secret-key: ${JWT_SECRET}
```

## Rules
- Secrets (`flow.secret`, `jwt-secret-key`, `reports.encryption-key`, Buckie/S3 keys) come from the environment or a vault, never from the committed file.
- Don't change `dynamia.reports.encryption-key` or `dynamia.saas.root-tenant-id` once data exists.
- Check a key in the project's version before relying on it (`grep -rn '"dynamia\.' src` in the framework sources).
