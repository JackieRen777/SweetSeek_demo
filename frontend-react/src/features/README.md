# Frontend Features Architecture

This directory contains the feature-based modules of the application. Each feature is self-contained with its own components, hooks, and views.

## Structure

```
features/
  ├── database/           # Compound Database Feature
  │   ├── components/     # Feature-specific components
  │   ├── DatabaseInterface.tsx  # Main Feature View
  │   └── DatabaseSection.tsx    # Landing/Entry Section
  │
  ├── equation/           # Equation Modeler Feature
  │   ├── components/
  │   ├── EquationSection.tsx
  │   └── ...
  │
  ├── qa/                 # Q&A / Chat Feature
  │   ├── components/
  │   └── QASection.tsx
  │
  └── landing/            # Landing Page / Hero
      ├── components/
      └── HeroSection.tsx
```

## Guidelines

1.  **Isolation**: Components inside `features/*/components` should generally only be used within that feature.
2.  **Shared Components**: Reusable UI elements (buttons, inputs, layout) should be placed in `src/components/ui` or `src/components/layout`.
3.  **Entry Points**: Each feature exposes a "Section" component (for the main scroll view) and optionally an "Interface" component (for the full-screen modal/view).
