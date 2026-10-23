# file-importer

Import Excel files with async processing, progress and a stop button. Checked against `extensions/file-importer` (modules `core`, `ui`; coordinates `tools.dynamia.modules.importer`, `.importer.ui`) in framework 26.10. The `Importer` window and `GenerateImportFormatAction` are ZK (`ui`); the reading API is in `core`.

## Pieces
| Class | Role |
|---|---|
| `ImportExcelAction<T>` | base class to implement: `List<T> importFromExcel(InputStream, ProgressMonitor)` |
| `ImportAction` | base for other file types (add your own) |
| `ImportUtils` | `readExcel(stream, monitor, row -> ...)`, `getCellValue(row, col)` (string), `getCellValueObject(row, col)` (typed: `Date`, number, ...) |
| `ImportBeanParser`, `ImportReader`, `ImportExcelTemplate` | map columns to bean properties; read; generate the Excel format file |
| `ImportOperation`, `ImportStatus`, `ImportOperationException` | the running operation, its state and errors |
| `Importer` (ui) | the ZK window that shows the expected format, uploads and runs the action |

## An import action
```java
@InstallAction
class ImportPeopleAction extends AbstractCrudAction {
    ImportPeopleAction() { setName("Import"); setApplicableClass(Person.class); }
    @Override public void actionPerformed(CrudActionEvent evt) {
        var importer = new Importer();
        importer.addColumn("Code");                    // column header shown in the format
        importer.addColumn("Last Name", "name2");      // maps to property name2
        importer.addColumn("Start Date", "dateOfStart");
        importer.addAction(new PeopleExcelImport());   // what to do with the file
        importer.show("Import People");
    }
}
class PeopleExcelImport extends ImportExcelAction<Person> {
    @Override public List<Person> importFromExcel(InputStream excel, ProgressMonitor monitor) throws Exception {
        var result = new ArrayList<Person>();
        ImportUtils.readExcel(excel, monitor, row -> {
            var p = new Person();
            p.setCode(ImportUtils.getCellValue(row, 0));
            var date = ImportUtils.getCellValueObject(row, 3);
            if (date instanceof Date d) p.setDateOfStart(DateTimeUtils.toLocalDate(d));   // Excel gives Date: convert at the edge
            result.add(p);
        });
        return result;
    }
}
```
(The README example uses `Date` fields; for `LocalDate` fields convert as shown, `dynamia-platform:dates`.)

## Rules
- Update the `ProgressMonitor` and **check `monitor.isStopped()`** in long loops so the user can stop.
- Validate every row (required cells, types, duplicates) and collect row-numbered errors instead of failing the whole file; decide with the user whether a bad row aborts the import.
- Persist in batches inside a transaction per batch (`crudService.executeWithinTransaction`, `saveWithinTransaction`), not one giant transaction.
- Run under the right tenant (`saas-tenancy.md`); the importer runs in the background like other jobs.
- Check file size and sheet limits; read with streaming for big files.
- Excel formulas and formats can return unexpected types: use `getCellValueObject` and handle `null`.
