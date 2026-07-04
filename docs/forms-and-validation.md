## Forms & Validation

### Where to validate

All input validation belongs in **Form classes**. Use standard `javax.validation` annotations wherever possible (`@NotBlank`, `@Email`, `@Size`, etc.).

Rules enforced by form validation must not be revalidated in controllers.

Controllers must rely on @Valid and must not duplicate validation logic.

Services may assume that input coming from forms is already validated.

However, when a business rule is critical for domain consistency, the method to validate it must live in the service layer and be used only by validators. 

| Concern                           | Location                             |
| --------------------------------- | ------------------------------------ |
| Simple field validation           | Bean Validation annotations on forms |
| Cross-field validation            | Custom class-level validators        |
| Validation requiring DB access    | Custom validator calling a service   |
| Business rules used by validators | Service methods                      |


### Custom validators

Custom validator classes live in `webapp/validation/`. Use subdirectories `webapp/validation/annotations` and `webapp/validation/validators` to keep them organised as the project grows.

### Validators that need database access

If a validator must look up data (e.g. checking whether a `productId` exists), inject a **Service** into the validator — never inject a DAO directly.

### Business-rule validation

When validation encodes a business rule (e.g. size/category compatibility), the logic belongs in the **Service** as a dedicated method (e.g. `validateSizeForCategory`). The custom validator calls that service method:

```java
productService.validateSizeForCategory(size, category);
```

The service does **not** need to re-validate these rules — anything that reaches the service is assumed to have already passed form validation.

### Cross-field validation

When a constraint spans more than one field, declare the annotation at **class level** on the form:

```java
@ProductSizeForCategory
public class PublishProductForm { ... }
```

In the validator, bind the error to a specific field so it renders next to the right input in the UI:

```java
context.buildConstraintViolationWithTemplate(message)
       .addPropertyNode("size")
       .addConstraintViolation();
```

### Summary

| Concern | Where it lives |
|---------|---------------|
| Simple constraints | Standard `javax.validation` annotations on form fields |
| Complex constraints | Custom validator in `webapp/validation/` |
| Business logic | Service method called by the validator |
| DB lookups | Via Service (never direct DAO) |
| Cross-field rules | Class-level annotation on the form |
| Controllers | Orchestrate only — no validation |

---

### Controller-side rules for forms

1. **`BindingResult` MUST be the parameter immediately after `@Valid`** — any other position throws an exception. Spring requires the binding result for *that* validated argument to come right after it.
2. On validation errors → return the form view (NOT redirect — a redirect drops the model, including the errors).
3. After a successful POST → return `new ModelAndView("redirect:/path")` (PRG pattern).
4. Form objects live in `ar.edu.itba.paw.webapp.form`. **Never** reuse domain model entities (`User`, `Product`) as form objects — they are immutable and have no setters.
5. `@ModelAttribute` at method level on the controller for common dropdown data (categories, conditions, locations).
6. The string in `@ModelAttribute("formName")` must match the `modelAttribute` of `<form:form modelAttribute="formName">` in the JSP.
7. Controllers do not handle validation exceptions — `@ControllerAdvice` (`GlobalExceptionHandler`) catches `MethodArgumentNotValidException`, `ConstraintViolationException`, etc.

### Folder layout for custom validators

The current convention is to split annotations and validator implementations into two subdirectories:

```
webapp/src/main/java/ar/edu/itba/paw/webapp/validation/
├── annotations/         <-- the @Annotation interfaces
│   ├── ExistingProductId.java
│   ├── FutureOrPresentDate.java
│   ├── NewUser.java
│   ├── PasswordMatch.java
│   ├── ProductSizeForCategory.java
│   ├── ValidProductImages.java
│   └── ValidRentDateRange.java
└── validators/          <-- the ConstraintValidator implementations
    ├── ExistingProductIdValidator.java
    ├── FutureOrPresentDateValidator.java
    ├── NewUserValidator.java
    ├── PasswordMatchValidator.java
    ├── ProductImagesValidator.java
    ├── ProductSizeForCategoryValidator.java
    └── RentDateRangeValidator.java
```

Additional groupings already in the project:
- `webapp/validation/groups/` — Bean Validation groups for selective validation across forms.

When adding a new custom validator, create the annotation under `annotations/` and the validator class under `validators/`.

### Current validators inventory

| Annotation | Validator | What it checks |
|---|---|---|
| `@ExistingProductId` | `ExistingProductIdValidator` | The `productId` exists in the DB (via `ProductService`) |
| `@FutureOrPresentDate` | `FutureOrPresentDateValidator` | Date is today or in the future |
| `@PastOrPresentDate` | `PastOrPresentDateValidator` | Date is today or in the past (not future). Field-level. Used on `ReportFilterDateRangeForm` (the `/admin/reports` date filter — a report can't exist for a date that hasn't happened); front-end mirrors it via the calendar's `allowFuture="${false}"` |
| `@NewUser` | `NewUserValidator` | The email is not already registered (via `UserService`). **Class-level** on `RegisterForm`: reads `email` + `adminInviteToken`, so when an admin-invite token is present it skips the uniqueness check (the invited email legitimately exists as a stub; the token is validated server-side). Error bound to the `email` field |
| `@PasswordMatch` | `PasswordMatchValidator` | `password` and `confirmPassword` are equal (class-level) |
| `@ProductSizeForCategory` | `ProductSizeForCategoryValidator` | Size is compatible with category (class-level) |
| `@ValidProductImages` | `ProductImagesValidator` | Image count, size and MIME type for the upload |
| `@ValidReviewImages` | `ReviewImagesValidator` | Optional review photos: count (≤5), size (≤10 MB) and MIME type (PNG/JPEG) |
| `@ValidRentDateRange` | `RentDateRangeValidator` | `startDate <= endDate` (class-level) |
| `@ReportReasonRequired` | `ReportReasonRequiredValidator` | A `ReportReason` was selected (rejects the empty placeholder) |
| `@ValidAvailabilityRange` | `ValidAvailabilityRangeValidator` | Optional per-product availability: both ends null or both set with `from < to` (class-level, via `HasAvailabilityRange` contract; error on `availabilityFrom`) |
| `@UniquePickupSpotEntries` | `UniquePickupSpotEntriesValidator` | No two **inline new** pickup spots share a description (trimmed, case-insensitive). Class-level, via `HasPickupSpotSelection` contract (covers `PublishProductForm` + `EditProductForm`); error on `newSpots`. This is the **within-form** guard only. Catalog-level uniqueness (an inline or profile-added spot duplicating one of the owner's existing *active* spots) is enforced authoritatively in `PickupSpotServiceImpl.addSpot`, which owns the `userId` and throws `DuplicatePickupSpotException` (→ 409); a validator can't see the logged user, so it can't do the DB check (the DB has no UNIQUE — insert-always soft-delete). Re-creating a soft-deleted spot stays allowed (only active spots compared) |
| `@ValidPriceRange` | `PriceRangeValidator` | Catalog per-currency price filter: for each currency, `minPrice.<slug> <= maxPrice.<slug>` (a `null`/blank bound is never in conflict). Class-level on `CatalogPriceRangeForm`, via `PriceRangeBounds` contract; error bound to `maxPrice.<slug>`. The catalog is a GET endpoint, so it binds `@Valid @ModelAttribute`, the controller only drops the offending currency's bound (never 500), and the **view renders the message straight from the `BindingResult` via `<spring:bind>`** (the GET-form equivalent of the publish form's `<form:errors>`) — the controller never formats messages. Same wiring as `@ValidDateRange` on `CatalogDateRangeForm` |
| `@ValidProductPaymentMethods` | `ProductPaymentMethodsValidator` | Publish/edit/replicate product form: at least one payment method must be selected (error on `acceptsCash`), and if bank transfer is selected the provider must have a CBU (error on `acceptsBankTransfer`, message links to `/profile`). Class-level on `PublishProductForm` (inherited by `EditProductForm`), via `ProductPaymentSelection` contract (`isAcceptsCash`/`isAcceptsBankTransfer`/`isProviderHasCbu`). `providerHasCbu` is **server-supplied context**: the controller sets it from `loggedUser` in a `@ModelAttribute("publishForm")` factory and disallows its binding with `@InitBinder` (`setDisallowedFields("providerHasCbu")`) — the controller supplies a *fact*, the rule stays in the validator. The "two checkboxes → `PaymentPreference`" mapping lives in `PaymentPreference.of(...)`, not the form/controller |
| `@ProviderSettableStatus` | `ProviderSettableStatusValidator` | `POST /products/{id}/status` form (`UpdateProductStatusForm.status`): the target `ProductStatus` must be one a provider may set on their own publication — `ACTIVE`/`PAUSED`/`DELETED`. Rejects forged POSTs that try to reach a system/admin-managed state (`PENDING_LOCATION`, `UNDER_REVIEW`, `PAUSED_NO_PICKUP_SPOT`). Field-level; `null` left to `@NotNull`. The whitelist is the SSOT method `ProductStatus.isProviderSettable()`, reused as a defense-in-depth guard in `ProductServiceImpl.updateStatus` (→ `ConflictException`/409). Closes audit finding **S1** |
| `@AdminSelectableResolution` | `AdminSelectableResolutionValidator` | `POST /admin/reports/*` forms (`ResolveReportForm.resolution`, `BulkResolveReportsForm.resolution`): the target `ReportResolution` must be one an admin may select manually — excludes auto-only `PROVIDER_DELETED_PRODUCT`. Rejects forged POSTs that try to apply an auto-only resolution. Field-level; `null` left to `@NotNull`. The whitelist is the SSOT method `ReportResolution.isAdminSelectable()`, reused as a defense-in-depth guard in `ReportServiceImpl.resolveReport`/`bulkResolveProductReports` (→ `ConflictException`/409). Mirrors the S1 pattern for `@ProviderSettableStatus`. |

When you add a new validator, append it here so future contributors know it exists.

### Custom annotation skeleton

```java
@Constraint(validatedBy = MyConstraintValidator.class)
@Target({ ElementType.FIELD, ElementType.METHOD })   // or ElementType.TYPE for class-level
@Retention(RetentionPolicy.RUNTIME)
public @interface MyConstraint {
    String message() default "{my.constraint.message}";   // resolves via messages.properties
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
```

The `message()` default uses `{...}` so it resolves through the `MessageSource` (i18n). Define the key in `messages.properties` / `messages_en.properties`.

### Validator that talks to the DB

Always go through a **Service**, never a DAO:

```java
public class ExistingProductIdValidator implements ConstraintValidator<ExistingProductId, Long> {

    @Autowired
    private ProductService productService;

    @Override
    public boolean isValid(final Long productId, final ConstraintValidatorContext ctx) {
        if (productId == null) {
            return true;   // @NotNull is a separate constraint
        }
        return productService.findById(productId).isPresent();
    }
}
```

Rules:
- A custom validator may inject **services** (interfaces from `service-contracts`) — never DAOs.
- A `null` input is typically considered "valid" by the custom constraint; combine with `@NotNull` to enforce presence. This avoids forcing every custom annotation to also reimplement null-checks.

### Cross-field validation — bind error to a specific field

When `@Target(TYPE)` (class-level), the default behavior is to attach the error to the form as a whole. To make `<form:errors path="size"/>` show the error, redirect it to the specific field with `addPropertyNode`:

```java
context.disableDefaultConstraintViolation();
context.buildConstraintViolationWithTemplate(message)
       .addPropertyNode("size")
       .addConstraintViolation();
```

This is required for `@ProductSizeForCategory`, `@PasswordMatch`, `@ValidRentDateRange` — anywhere the error message is conceptually about a field but the constraint needs to read multiple fields.

### Decoupling validators from specific forms

A validator like `@PasswordMatch` should not assume it is validating exactly `RegisterForm`. Use reflection / a contract interface (e.g., `PasswordsMatching` with `getPassword()` / `getConfirmPassword()`) so the same constraint can be reused on `ResetPasswordForm`, `ChangePasswordForm`, etc. This was a TP1 finding for groups that had to reimplement the same matcher for each form.

### Validation message resolution (messages.properties)

Hibernate Validator looks up messages with this hierarchy (most specific to least):

```
{Constraint}.{ClassName}.{field}        e.g. NotBlank.RegisterForm.email
{Constraint}.{field}                    e.g. NotBlank.email
{Constraint}.{type}                     e.g. NotBlank.String
{Constraint}                            e.g. NotBlank
```

Examples in `messages.properties`:

```properties
# Generic — applies to every @Size in every form
Size=El campo debe tener entre {2} y {1} caracteres.

# Field-specific override
Pattern.RegisterForm.email=Formato de email inválido.

# Custom constraint default message
product.size.invalid=El talle no es válido para la categoría seleccionada.
```

Argument indices for built-in constraints:
- `{0}` = field name
- `{1}` = max
- `{2}` = min

### `@DateTimeFormat` for date binding

Spring binds `LocalDate` / `LocalDateTime` from form fields, but the format is locale-dependent unless declared. Annotate every date field explicitly:

```java
@NotNull
@FutureOrPresentDate
@DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
private LocalDate startDate;
```

This binds `<input type="date">` (browser sends `yyyy-MM-dd`) reliably across locales. Without it, a Spanish locale might expect `dd/MM/yyyy` and break the form.

### File upload — two layers of size limits

The project applies two independent limits:

1. **Hard limit at the Spring layer** (`web.xml` / `multipartResolver`): rejects requests above ~50 MB before they reach the controller. Throws `MaxUploadSizeExceededException`.
2. **Business limit at the validator layer** (e.g., `@ValidProductImages` — 10 MB/file): rejects files that are technically allowed by Spring but too big for the product use case.

The Spring exception bubbles up to `GlobalExceptionHandler` and renders `error/413`. Validator failures land in the form via `BindingResult` and re-render the form with the error.

### Controllers must NOT redo validation

If a constraint is enforced by a form validator, the **service** assumes the input is already valid and does not re-check. Exception: when a business rule is critical for **domain consistency** (e.g., size/category compatibility), the rule lives in the service as a method (`validateSizeForCategory`) that the validator calls. The service still does not redo it on every call — only the validator triggers it.

### Service-thrown business exceptions in lieu of validator

If a flow cannot be expressed as a constraint (e.g., concurrent state-machine race), the service throws a domain exception. The exception is mapped by `GlobalExceptionHandler`. The controller does NOT try-catch it.
