# CS Gauntlet Frontend Styling Guide

This document serves as the definitive reference for CS Gauntlet's frontend styling. All new features and components MUST adhere to these styling rules.

## Core Color Palette

- **Background Colors**:
  - Primary background: Black (`#000000`, `bg-black`)
  - Secondary background: Dark gray (`#1a1a1a`, `bg-gray-900`)
  - Component background: Medium dark gray (`#1f2937`, `bg-gray-800`)
  - Input fields: Dark gray (`#111827`, `bg-gray-900`)

- **Text Colors**:
  - Primary text: White (`#ffffff`, `text-white`)
  - Secondary text: Light gray (`#d1d5db`, `text-gray-300`)
  - Tertiary text: Medium gray (`#9ca3af`, `text-gray-400`)

- **Accent Colors**:
  - Primary accent: Indigo (`#4f46e5`, `bg-indigo-600`, `text-indigo-600`)
  - Highlight: Light indigo (`#818cf8`, `text-indigo-400`)
  - Hover accent: Dark indigo (`#4338ca`, `hover:bg-indigo-700`)
  - Success: Green (`#16a34a`, `bg-green-600`)
  - Warning: Amber (`#d97706`, `bg-amber-600`)
  - Error: Red (`#dc2626`, `bg-red-600`)

## Typography

- **Font Family**: System UI sans-serif
  - `font-family: ui-sans-serif, system-ui, sans-serif`
  
- **Font Sizes**:
  - Headings:
    - H1: `text-5xl font-bold`
    - H2: `text-3xl font-bold`
    - H3: `text-xl font-semibold`
  - Body text: `text-base`
  - Small text: `text-sm`

## Component Styling

### Buttons

- **Primary Button**:
  ```html
  <button class="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
    Button Text
  </button>
  ```

- **Secondary Button**:
  ```html
  <button class="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors">
    Button Text
  </button>
  ```

### Cards

- **Standard Card**:
  ```html
  <div class="bg-gray-800 p-6 rounded-lg shadow-lg">
    <!-- Card content -->
  </div>
  ```

- **Interactive Card**:
  ```html
  <div class="bg-gray-800 p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
    <!-- Card content -->
  </div>
  ```

### Navigation

- **Navigation Bar**: Dark gray background with white/light gray text
  ```html
  <nav class="bg-gray-800 shadow-lg">
    <!-- Navigation content -->
  </nav>
  ```

- **Active Navigation Link**:
  ```html
  <a class="border-b-2 border-indigo-500 text-white">Link Text</a>
  ```

- **Inactive Navigation Link**:
  ```html
  <a class="border-b-2 border-transparent text-gray-300 hover:border-gray-300 hover:text-white">Link Text</a>
  ```

### Forms

- **Input Field**:
  ```html
  <input type="text" class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white" />
  ```

- **Label**:
  ```html
  <label class="block text-sm font-medium text-gray-300 mb-1">Label Text</label>
  ```

## Layout Principles

1. **Container Width**: Use `container mx-auto` for centered content with responsive width
2. **Padding**: Consistent padding with `px-4 py-8` for section containers
3. **Spacing**: Use consistent margin spacing between elements
   - Small gap: `space-y-2` or `gap-2`
   - Medium gap: `space-y-4` or `gap-4`
   - Large gap: `space-y-8` or `gap-8`
4. **Grid System**: Use Tailwind's grid system for responsive layouts
   - `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3`

## Animation

- **Transitions**: Use `transition-colors`, `transition-transform`, etc.
- **Hover Effects**: Subtle color changes on hover
- **Fade In**: Use `animate-fade-in` class for elements that should fade in

## CSS Variables

```css
:root {
  --foreground-rgb: 255, 255, 255;
  --background-rgb: 0, 0, 0;
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
  background-color: #1a1a1a;
}
```

## DO NOT CHANGE

The following styling aspects must NEVER be changed:

1. The dark theme (black/dark gray backgrounds with white text)
2. The indigo accent color scheme
3. The rounded corners on interactive elements
4. The shadow effects on cards and containers
5. The hover state transitions
6. The font family and base text sizes

## Example Page Structure

```html
<div class="min-h-screen bg-black">
  <!-- Navigation -->
  <nav class="bg-gray-800 shadow-lg">
    <!-- Nav content -->
  </nav>

  <!-- Main Content -->
  <main class="container mx-auto px-4 py-8">
    <!-- Page content -->
    <h1 class="text-4xl font-bold text-white">Page Title</h1>
    
    <!-- Content cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-8">
      <div class="bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 class="text-xl font-semibold text-white mb-2">Card Title</h3>
        <p class="text-gray-400">Card description text goes here</p>
      </div>
      <!-- More cards -->
    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-gray-900 py-8">
    <!-- Footer content -->
  </footer>
</div>
```

By following this styling guide precisely, you will maintain the consistent, dark-themed design of the CS Gauntlet application.
