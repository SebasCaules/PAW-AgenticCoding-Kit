## Domain Invariants

These business rules are enforced **once**, at the publish/edit form level. Every layer above (services, DAOs, controllers) trusts them and must NOT re-check or write defensive code for the cases they rule out. When writing tests, do not construct fixtures that violate these invariants — they cannot occur in production.

| Invariant | Where it's enforced | Implication |
|---|---|---|
| Every `Product` always has a current `Price`. | Publish/edit forms always create a price row. | DAO/service/test code never has to handle a publication without a price. Don't write tests for "publication without price" — it's an impossible state. |
| If a `Category` admits size (`Category.usesSize()` → `CLOTHING` or `FOOTWEAR`), the size is **mandatory** and never `null`. | `validateSizeForCategory` in `ProductServiceImpl`, called from the form. | DAO/test fixtures for clothing/footwear products must always include a non-null size. `JACKET` with `size=null` is an impossible state. |
| If a `Category` does NOT admit size (`ACCESSORIES`, `EQUIPMENT`), the size is **always** `null`. | Same validation as above. | Helmet/goggles/skis with a non-null size is an impossible state. |

Rule of thumb: if the publish form rejects it, no other layer needs to handle it. Do not add fallbacks, null checks, or test cases for states that the form makes unreachable.

## Layering Rules

### Controllers

Controllers must only orchestrate the HTTP flow:

- receive request parameters or validated forms;
- call services;
- choose the view or redirect;
- add already-computed data to the model.

Controllers must NOT contain business logic. Any rule about prices, rents, users, permissions, publication states, date ranges, or domain decisions belongs in the service layer.

Bad examples in controllers:
- deciding which price is effective for a date;
- selecting the default price;
- deduplicating special prices;
- checking whether a rent can be created;
- validating category/size compatibility;

Controllers must not perform complex data transformations.

They must not:
- filter collections;
- sort domain data;
- deduplicate entities;
- resolve conflicts.

These transformations belong to the service layer.

### Services

All business logic belongs in services.

A service may directly inject only its corresponding DAO. If it needs data managed by another DAO, it must depend on the service responsible for that DAO instead of injecting the DAO directly.

Example:

```java
public class ProductServiceImpl {
    private final ProductDao productDao;
    private final PriceService priceService; // OK

    // Do NOT inject PriceDao here directly.
}
```

This keeps DAO ownership clear and prevents services from bypassing each other's business rules.

### Views (JSP) & JavaScript

Views and JavaScript must NOT contain business logic.

They are only responsible for:
- rendering data already computed by the server;
- simple UI transformations (formatting, filtering already resolved data).

They must NOT:
- decide which price applies;
- resolve conflicts between domain entities;
- apply fallback rules;
- infer business decisions from raw data.

All such logic must be resolved in the service layer before reaching the view.

### Single Source of Truth

Every business rule must have a single authoritative implementation.

The same rule must NOT be duplicated across:
- controllers;
- services;
- JSP/JavaScript;
- validators.

If multiple layers need the same rule, it must live in the service layer and be reused.

### DTOs / View Models

DTOs and view models are data carriers only.
DTOs must be fully ready to be consumed by the view.
Views should not need to interpret or resolve DTO data.

They must NOT:
- contain business logic;
- compute values;
- apply rules;
- depend on services or DAOs.

All computations must be done before constructing the DTO.

### Transactions

Transactions must be defined at the service layer, not in DAOs or controllers.

A service method represents a complete business operation and must:
- start and end the transaction;
- ensure consistency across multiple DAOs.

DAOs must not manage transactions.
Controllers must not manage transactions.

### Rule of Thumb

If a piece of code answers a business question, it belongs in the service layer.
