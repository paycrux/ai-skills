# Jirisan DataTable Pattern

> Partner app table implementation reference. Extracted from actual usage across `apps/partner/src`.
>
> **When to use:** Only reference this document when working in the `white_label` project's admin or partner app.
> If Figma or requirements include table UI, confirm with the user whether to apply the Jirisan pattern before proceeding.

```ts
import { ColumnDef, DataTable } from "@paycrux/jirisan";
```

---

## Basic Structure

```tsx
<TableContainer $hideLastBorder={data.length >= size}>
  <DataTable
    columns={columns}
    data={data}
    onRowClick={handleRowClick}
    noDataRenderer={() => <EmptyMessage>No data available.</EmptyMessage>}
    tableSizeConfig={{ header: 40, row: 40, table: 40 * 11 }}
  />
</TableContainer>
```

`TableContainer` is a styled div. Reuse an existing one in the file, or create with this pattern:

```ts
const TableContainer = styled.div<{ $hideLastBorder?: boolean }>`
  background: white;
  font-size: 12px;
  table tbody tr td { border-left: 0; }
  ${({ $hideLastBorder }) =>
    $hideLastBorder && `table tbody tr:last-child { border-bottom: 0; }`}
`;
```

---

## tableSizeConfig Reference

| Use case | header | row | table |
|---|---|---|---|
| General lists (sales, settlements) | 32 | 32 | `32 * (N + 1)` |
| Events / inquiries / home messages | 40 | 40 | `40 * 11` (10 rows + header) |
| Summary single row | 32 | 32–50 | `32 * 2 - 1` |
| Dynamic with minimum height | 32 | 32 | `Math.max(400, (data.length + 1) * 32)` |

- `header` and `row` can be omitted when only `table` is needed
- Extract as a constant: `const TABLE_SIZE_CONFIG = { header: 40, row: 40, table: 40 * 11 }`
- Spread is supported: `tableSizeConfig={{ table: height, ...SIZE_STYLE }}`

---

## $hideLastBorder Pattern

Removes the bottom border of the last row in paginated lists:

```tsx
<TableContainer $hideLastBorder={data.length >= size}>
```

---

## Row Click Patterns

```tsx
// Navigate to detail page
onRowClick={(row) => navigate(`/operation/home-message/${row.id}`)}

// Open modal
onRowClick={(row) => openModal(row.id)}

// Conditional click (skip disabled rows)
onRowClick={(row) => { if (!row.deliveryConnect) setSelected(row.id); }}
```

---

## Sorting Patterns

Client-side sorting:
```tsx
const [sorting, setSorting] = useState<SortingState>([]);
<DataTable sorting={sorting} onSortingChange={setSorting} ... />
```

Server-side sorting:
```tsx
useEffect(() => {
  if (sorting.length > 0) {
    const sortParam = `${sorting[0].id},${sorting[0].desc ? "DESC" : "ASC"}`;
    onSortChange(sortParam);
  } else {
    onSortChange(undefined);
  }
}, [sorting]);
```

---

## Other Props

```tsx
// Dynamic column visibility
columnVisibility={columnVisibility}  // VisibilityState

// Row selection
enableRowSelection={true}
onRowClick={handleRowClick}

// Highlight selected row
shouldRowHighlight={(row) => row.id === selectedId}

// Grouped header (nested columns)
columns={[{
  header: "Pre-payment",
  accessorKey: "prePaid",
  columns: [
    { header: "Order count", accessorKey: "prePaidCount", size: 96 },
    ...
  ]
}]}

// Extend DataTable styles
const StyledTable = styled(DataTable)`
  .table .th { font-size: 12px; }
`;
```

---

## Summary + Data Split Pattern

```tsx
{/* Summary row */}
<DataTable
  data={summary ? [summary] : []}
  columns={summaryColumns}
  tableSizeConfig={{ header: 32, row: 50, table: 82 }}
/>
{/* Data rows */}
<DataTable
  data={data?.content ?? []}
  columns={dataColumns}
  noDataRenderer={() => <NoData>No results found.</NoData>}
  tableSizeConfig={{ header: 32, row: 32, table: Math.max(400, (data?.content?.length ?? 0 + 1) * 32) }}
/>
```
