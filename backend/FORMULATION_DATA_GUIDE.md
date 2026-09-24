# Formulation Data File Guide

## Required CSV Format

Your formulation data file must follow this exact format:

### Column Headers (First Row)
```
Run Order,Oil,Smix,Water,Particle Size (nm),Spreadability (h),% in vitro Drug Release (t24),% in vitro Drug Release (t40),% Ex vivo drug release (t24),Viscocity (cps)
```

### Data Format (Subsequent Rows)
Each row represents one experimental run with all columns filled:

**Example Row:**
```
1,15,65,20,70,60,77,91,75,8.9
```

**Breakdown:**
- Run Order: 1 (experiment number)
- Oil: 15 (percentage)
- Smix: 65 (percentage) 
- Water: 20 (percentage)
- Particle Size (nm): 70
- Spreadability (h): 60
- % in vitro Drug Release (t24): 77
- % in vitro Drug Release (t40): 91
- % Ex vivo drug release (t24): 75
- Viscocity (cps): 8.9

## Column Descriptions

### Input Columns (What you control)
- **Oil**: Oil percentage in formulation (0-100)
- **Smix**: Surfactant mixture percentage (0-100)
- **Water**: Water percentage (0-100)

### Output Columns (What gets predicted)
- **Particle Size (nm)**: Measured particle size in nanometers
- **Spreadability (h)**: Spreadability time in hours
- **% in vitro Drug Release (t24)**: Drug release percentage at 24 hours
- **% in vitro Drug Release (t40)**: Drug release percentage at 40 hours
- **% Ex vivo drug release (t24)**: Ex vivo release percentage at 24 hours
- **Viscocity (cps)**: Viscosity in centipoise

## Important Rules

1. **Exact Headers**: Column names must match exactly (case-sensitive)
2. **Numeric Values**: All data must be numbers (no text)
3. **No Empty Cells**: Every cell must have a value
4. **Sum to 100%**: Oil + Smix + Water should ideally equal 100
5. **Consistent Units**: Use the specified units for each column

## Creating Your Data File

### Option 1: Using Excel/Google Sheets
1. Create a new spreadsheet
2. Add the exact headers in the first row
3. Fill in your experimental data
4. Save as CSV format
5. Upload to the formulation tool

### Option 2: Using Text Editor
1. Open a text editor (Notepad, TextEdit, etc.)
2. Copy the headers from above
3. Add your data rows (comma-separated)
4. Save with .csv extension
5. Upload to the formulation tool

## Example Complete File

```csv
Run Order,Oil,Smix,Water,Particle Size (nm),Spreadability (h),% in vitro Drug Release (t24),% in vitro Drug Release (t40),% Ex vivo drug release (t24),Viscocity (cps)
1,15,65,20,70,60,77,91,75,8.9
2,20,60,20,170,55,75,93,74,8.1
3,10,60,20,150,24,93,96,92,3.1
4,10,60,20,158,24,92,97,93,2.9
5,15,65,20,69,60,76,89,77,7.9
```

## Testing Your File

Before uploading, check:
- ✅ File extension is .csv
- ✅ First row has exact headers
- ✅ All rows have same number of columns
- ✅ All values are numeric
- ✅ No empty cells
- ✅ No special characters in headers

## Common Mistakes to Avoid

❌ **Wrong header names**: "oil" instead of "Oil"
❌ **Missing columns**: Skipping any of the 10 required columns
❌ **Text values**: "high" instead of numeric values
❌ **Empty cells**: Leaving cells blank
❌ **Wrong units**: Using different units than specified

## Need Help?

If you have existing data in a different format, you can:
1. Map your columns to the required format
2. Convert units if necessary
3. Ensure all values are numeric
4. Save as CSV and upload

The formulation tool will automatically detect your columns and train models on your data!