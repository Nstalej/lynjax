---
version: alpha
name: Lynjax
description: Intelligent network visibility with audit-grade traceability.
colors:
  primary: "#083B5C"
  secondary: "#0E7490"
  tertiary: "#2DD4BF"
  neutral: "#F2FAF8"
  surface: "#FFFFFF"
  ink: "#0F172A"
  muted: "#48606A"
  line: "#B7CDD1"
  danger: "#B42318"
  success: "#047857"
typography:
  h1:
    fontFamily: Inter
    fontSize: 3.75rem
    fontWeight: 760
    lineHeight: 1.02
    letterSpacing: "-0.045em"
  h2:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: 720
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 450
    lineHeight: 1.65
  label:
    fontFamily: Inter
    fontSize: 0.78rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.11em"
  mono:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.5
rounded:
  sm: 6px
  md: 12px
  lg: 22px
  xl: 32px
spacing:
  xs: 6px
  sm: 10px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 72px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: 14px
  button-primary-hover:
    backgroundColor: "{colors.secondary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: 14px
  card-technical:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 24px
  badge-trace:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 8px
---

## Overview

Lynjax is a calm technical brand for intelligent network visibility, authorized assessment and audit-grade traceability. It should feel precise and trustworthy rather than aggressive or cyberpunk.

## Colors

- **Primary / Deep Navy (#083B5C):** Main trust anchor for headings, navigation and primary actions.
- **Secondary / Signal Blue (#0E7490):** Used for active states, links and network paths.
- **Tertiary / Trace Teal (#2DD4BF):** Used sparingly for highlights, node pulses and trace confirmation.
- **Neutral / Ice Background (#F2FAF8):** Clean technical background, especially for landing and report covers.
- **Ink (#0F172A):** Primary text color.
- **Muted (#48606A):** Secondary copy that still maintains readable contrast.

## Typography

Use Inter as the main product and marketing font. Use JetBrains Mono only for IPs, command snippets, evidence IDs, device identifiers and technical metadata. Do not set the entire interface in monospace.

## Layout

Prefer spacious technical layouts with strong alignment, visible hierarchy and restrained surfaces. Use node/path graphics as structural elements, not decorative filler.

## Elevation & Depth

Use subtle borders and soft shadows. Avoid heavy glassmorphism. Technical trust comes from clarity, not glow.

## Shapes

Cards use 22px radius for modern product surfaces. Buttons use 12px. Nodes can be circular, but the icon should include angular path geometry to avoid a generic blob network.

## Components

Primary buttons are deep navy with white text. Trace badges use the ice background and primary text. Technical cards should include clear labels, short copy and evidence-oriented metadata.

## Do's and Don'ts

Do:

- Use short, precise product copy.
- Keep the interface readable in reports and dashboards.
- Use teal as a trace/highlight color.
- Show evidence and scope clearly.

Don't:

- Overuse glowing gradients.
- Fill dashboards with fake numbers.
- Use hacker/cyber fear visuals.
- Make the node icon too generic.
