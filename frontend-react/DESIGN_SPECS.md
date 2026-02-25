# Typography & Layout Specification Document

## Overview
This document outlines the standardized typography and layout rules for all introduction sections (Hero, Feature Sections) in the SweetSeek application. These rules ensure a consistent, justified, and rectangular visual block for text content across different screen sizes.

## 1. Container Layout
All text content is wrapped in a container with the following constraints to ensure alignment.

| Property | Value | Description |
| :--- | :--- | :--- |
| **Width** | `w-full` | Takes full available width up to max-width |
| **Max Width (Title)** | `600px` | Constrains title width to prevent excessive stretching |
| **Alignment** | Left / Start | Text block starts from the left edge |

## 2. Typography Specifications

### 2.1 Section Titles (H1 / H2)
Used for main section headers (e.g., "Welcome to Sweetseek", "Professional Q&A").

| Property | Value | CSS Class (Tailwind) |
| :--- | :--- | :--- |
| **Font Size (Desktop)** | `3rem` (48px) / `3.75rem` (60px) | `text-5xl md:text-6xl` (Hero) / `text-4xl md:text-5xl` (Features) |
| **Font Weight** | Bold / Extra Bold | `font-bold` / `font-extrabold` |
| **Line Height** | 1.25 | `leading-tight` |
| **Color** | Slate 800 (#1e293b) | `text-slate-800` |
| **Margin Bottom** | N/A (Handled by container gap) | - |

### 2.2 Body Text (Paragraphs)
Used for descriptive text below titles.

| Property | Value | CSS Class (Tailwind) |
| :--- | :--- | :--- |
| **Font Size** | `1.125rem` (18px) - `1.25rem` (20px) | `text-lg md:text-xl` |
| **Line Height** | `2rem` (32px) | `leading-8` |
| **Alignment** | **Justified** | `text-justify` |
| **Hyphenation** | Auto | `hyphens-auto` |
| **Letter Spacing** | Normal | `tracking-normal` |
| **Color** | Slate 600 (#475569) | `text-slate-600` |
| **Max Width** | `520px` | `max-w-[520px]` |
| **Margin Top** | `2rem` (32px) | `mt-8` |

## 3. Visual Consistency Rules

1.  **Rectangular Block Effect**:
    *   All paragraph text must use `text-justify` to ensure both left and right edges are aligned.
    *   `hyphens-auto` is mandatory to prevent large gaps in justified text.
    *   `max-w-[520px]` ensures the text block does not become too wide and hard to read, maintaining a rectangular aspect ratio.

2.  **Spacing**:
    *   There is a fixed `mt-8` (32px) spacing between the Title and the Body text to clearly separate the hierarchy.

3.  **Responsive Behavior**:
    *   On mobile (< 768px), text size reduces slightly (`text-lg`) but maintains the justified alignment and relative spacing.
    *   The max-width constraint ensures the text block remains centered or left-aligned properly without touching screen edges on larger displays.

## 4. Implementation Example

```tsx
<div className="w-full max-w-[600px]">
  <h2 className="text-4xl md:text-5xl font-bold text-slate-800 leading-tight">
    {title}
  </h2>
  <p className="mt-8 text-lg md:text-xl text-slate-600 leading-8 text-justify hyphens-auto w-full max-w-[520px] tracking-normal">
    {description}
  </p>
</div>
```
