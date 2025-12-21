TEMPLATE REPORT FEATURE
=======================

Place your custom Excel template file in this folder with the name:

    TEMPLATE.XLSM

Requirements:
- The template should contain a sheet named "DATA".
- Grid data will be written to the DATA sheet starting at row 2.
- Row 1 will contain column headers.
- Macros (.xlsm) are preserved during export.

Usage:
1. Place your TEMPLATE.XLSM file in this folder.
2. In the application, go to File > Export > Template Report.
3. Choose a save location.
4. The app will copy your template and inject the grid data.
