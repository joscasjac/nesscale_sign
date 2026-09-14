# Design system

A document register: warm white working surface, ink typography, ruled rows, small forest-green actions. The page is a place to work, not an analytics advertisement.

## Surface contract
Operate mode. Documents and next actions occupy the first viewport. Left navigation is compact; heading, search and status tabs sit above a real document table. A detail view has the document on the left, recipients and evidence on the right. The signer sees the document and one clear completion action.

## Tokens
Canvas #f6f5f1; paper #ffffff; ink #242a27; muted #626963; line #dedfd8; accent #255b45. Georgia headings pair with system sans-serif controls. 4px control radius, 8px large panel radius. 14px body, 12px metadata, 36px primary heading. No gradients, metric-card grid, decorative charts or noisy shadows.

## Behavior
Keyboard-visible focus, native form controls, explicit labels, error recovery, request-in-flight disabling. Tables become a scrollable register on small screens, editor sidebars stack. Signature fields are positioned as percentages against the actual rendered PDF.

## Identity and feature coverage
One shared document-and-signature mark links home in workspace and signer headers. Light and dark appearances preserve the same hierarchy; PDFs and signature canvases retain white paper. Feature coverage must be checked against docs/FEATURES.md before removing or hiding controls. Advanced settings use labelled disclosure sections or direct native Desk links.

## Document builder

Use a full-width white and cool-gray editor with one icon toolbar and hover labels. Keep Pages, Variables, Recipients and Settings in the top toolbar. One card library contains blocks and fillable fields. Created content follows a stacked block layout with visible insertion positions; imported PDFs retain their original page layout. Text and table cells edit inline; properties hold spacing and appearance. Text starts with a heading and paragraph. Table actions distinguish rows from columns and addition from deletion; Enter advances down a column or creates a row, while Shift+Enter stays inside the cell. New documents start with the actual title “New Document.” Email templates hide custom subject/body controls, and selecting Custom reveals them.
