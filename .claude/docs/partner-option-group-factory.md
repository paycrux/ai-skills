# OptionGroupFactory Pattern (Advanced Search)

> Search filter implementation reference for the `white_label` project's admin and partner apps. Extracted from actual usage across `apps/partner/src`.

```ts
import {
  OptionGroupButton,
  OptionGroupCheckbox,
  OptionGroupContainer,
  OptionGroupFactory,
  OptionGroupInput,
  OptionGroupPeriod,
  OptionGroupRadio,
  OptionGroupSelect,
  OptionGroupSwitch,
  OptionGroupText,
} from "core-ui";
```

---

## Basic Structure

```tsx
<OptionGroupFactory initialQueryString={{ page: 0, size: 10 }} gap={16} responsive={true}>
  <OptionGroupContainer id="top-container" layoutDirection="vertical">

    {/* Row 1: filters + action buttons */}
    <OptionGroupContainer
      layoutDirection="horizontal"
      style={{ width: "100%", justifyContent: "space-between" }}>

      {/* Filter area */}
      <OptionGroupContainer layoutDirection="horizontal">
        <OptionGroupText id="type-label" text="Exposure Type" variant="label" />
        <OptionGroupSelect id="exposureType" options={typeOptions} defaultValue="ALL" />
      </OptionGroupContainer>

      {/* Button area */}
      <OptionGroupContainer id="button-container">
        <OptionGroupButton id="excel" color="blue" icon="excel" onClick={onExcelDownload} />
        <OptionGroupButton id="search" color="dark" icon="search" onClick={onSearch} />
      </OptionGroupContainer>
    </OptionGroupContainer>

    {/* Row 2: additional filters (toggled via expand button) */}
    {isOpen && (
      <OptionGroupContainer layoutDirection="horizontal">
        <OptionGroupText id="status-label" text="Status" variant="label" />
        <OptionGroupCheckbox
          id="exposureStatus"
          variant="chip"
          options={statusOptions}
          defaultValue={statusOptions.map((o) => String(o.value))}
        />
      </OptionGroupContainer>
    )}

  </OptionGroupContainer>
</OptionGroupFactory>
```

---

## initialQueryString Defaults

```ts
// Basic (most common)
{ page: 0, size: 10 }

// With storeId
{ page: 0, size: 10, storeId: selectedStoreId ? Number(selectedStoreId) : storeId }

// With date range
{ page: 0, size: 10, startDate: formatDate(today.startDate), endDate: formatDate(today.endDate) }

// With enum array defaults
{ page: 0, size: 10, exposureType: "ALL", exposureStatus: ["ACTIVE", "SCHEDULED", "ENDED"] }
```

---

## Advanced OptionGroupFactory Props

```tsx
// Parse URL query string values to JS types
parseTypes={{ includeOption: "boolean", sort: "number", keyword: "string" }}

// Transform between UI state and URL query (use for non-trivial conversions)
transformForm={{
  toQuery: (values) => ({ ...values, startDt: values.startDt?.replace(/-/g, "") }),
  toState: (params) => ({ ...params, startDt: params.startDt?.replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3") })
}}

// Sync fields (reset dependent field when another changes)
onFieldSync={{ "searchType": { keyword: "" } }}

// Block search until condition is met
predicate={(values) => Boolean(values.keyword)}

// Trigger TanStack Query refetch on search
invalidateQueryKeys={[["my-query-key"]]}
```

---

## Filter Component Recipes

**Date range with period shortcuts:**
```tsx
<OptionGroupContainer id="period-container" wrap={true} style={{ minWidth: "591px" }}>
  <OptionGroupText id="period-label" text="Period" variant="label" />
  <OptionGroupPeriod
    id="period"
    startDateId="startDate"
    endDateId="endDate"
    defaultValue={{ startDate, endDate }}
    onChange={handleChangeDate}
  />
  <OptionGroupRadio
    id="periodType"
    variant="button"
    defaultValue={periodType}
    options={[{ label: "Today", value: "TODAY" }, { label: "1 Week", value: "WEEK" }, ...]}
  />
</OptionGroupContainer>
```

**Chip checkbox filter:**

> **Convention:** Use lowercase `"all"` for the select-all option value.
> Also use `v !== "all"` when filtering it out in `toQuery`.
> Exception: use `"ALL"` only when the user explicitly requests it.

```tsx
// ✅ Default — lowercase "all"
const ALL_STATUS_VALUES = ["all", "ACTIVE", "SCHEDULED", "ENDED"];
const STATUS_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Active", value: "ACTIVE" },
  { label: "Scheduled", value: "SCHEDULED" },
  { label: "Ended", value: "ENDED" },
];

// toQuery filter example
const filteredStatuses = statuses.filter((v) => v !== "all");

// ✅ Exception — uppercase "ALL" only when explicitly requested by the user
const STATUS_OPTIONS = [{ label: "All", value: "ALL" }, ...];
const filteredStatuses = statuses.filter((v) => v !== "ALL");
```

```tsx
<OptionGroupContainer id="status-container">
  <OptionGroupText id="status-label" text="Status" variant="label" />
  <OptionGroupCheckbox
    id="exposureStatus"
    variant="chip"
    options={[
      { label: "Active", value: "ACTIVE" },
      { label: "Scheduled", value: "SCHEDULED" },
      { label: "Ended", value: "ENDED" },
    ]}
    defaultValue={["ACTIVE", "SCHEDULED", "ENDED"]}
  />
</OptionGroupContainer>
```

**Select + keyword search:**
```tsx
<OptionGroupContainer id="search-container" style={{ flex: 1 }}>
  <OptionGroupText id="keyword-label" text="Search" variant="label" />
  <OptionGroupSelect id="searchType" options={searchTypeOptions} defaultValue="TITLE" />
  <OptionGroupInput id="keyword" placeholder="Enter keyword" />
</OptionGroupContainer>
```

**Toggle expand button:**
```tsx
<OptionGroupButton id="toggle" variant="ghost" icon="toggle" toggle={isOpen} onClick={onToggle} />
```

---

## Layout Patterns

```tsx
// Filters on left, buttons on right
<OptionGroupContainer layoutDirection="horizontal" style={{ width: "100%", justifyContent: "space-between" }}>

// Allow wrapping
<OptionGroupContainer layoutDirection="horizontal" wrap={true}>

// Filter area with background and border
<OptionGroupContainer
  id="filter-row"
  layoutDirection="vertical"
  gap={8}
  style={{
    padding: "8px",
    backgroundColor: theme.colors.grayScale70,
    border: `1px solid ${theme.colors.grayScale60}`,
    alignItems: "unset"
  }}>
```

---

## URL-Based State

`OptionGroupFactory` uses URL query string as its state.
Search button click → URL params update → TanStack Query refetch triggered automatically.

```tsx
// Read URL params in TanStack Query hook
const [searchParams] = useSearchParams();
const page = Number(searchParams.get("page") ?? 0);
const exposureType = searchParams.get("exposureType") ?? "ALL";
```
