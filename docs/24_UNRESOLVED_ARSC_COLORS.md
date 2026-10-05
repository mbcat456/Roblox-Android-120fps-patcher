# Unresolved ARSC Color Entries

The ARSC dump reported 264 public IDs with no resolved value row. This
document classifies that residual set.

## Corrected Count

```text
public_resources.csv rows without a resolved_values.csv row: 264
unique IDs:  207
unique names: 207
```

The duplicate rows are repeated public entries for the same Material color ID.
There are no unresolved non-color resources.

## Classification

| Prefix / family | Unique names | Meaning |
| --- | --- | --- |
| `m3_sys_color_dynamic_*` | 122 | Material 3 dynamic system colors |
| `m3_ref_palette_dynamic_*` | 65 | Material 3 dynamic reference palette |
| `material_dynamic_*` | 64 | legacy Material dynamic palette aliases |
| `abc_*` | 2 | AppCompat search URL colors |
| `design_*` | 1 | Design support library color |
| legacy `*_material_*` | 6 | dark/light foreground/inverse colors |
| `pi2_overlay_stroke_color` | 1 | PII/overlay stroke color |

## Why They Have No Static Value

These are runtime theme aliases. Android resolves them from the active
dynamic-color / Material theme at app startup rather than from a fixed
`<color>` literal. The ARSC value dumper therefore leaves them unassigned,
but they are valid public resources.

The complete name list is saved in:

```text
analysis/docs/artifacts/unresolved_public_colors.txt
```

This closes the resource-ID portion of the coverage matrix; the remaining
resource mapping work is the static classification above, not missing
application data.
