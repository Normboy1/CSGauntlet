# CS Gauntlet Design System

## Overview

This document serves as the technical specification for the CS Gauntlet frontend design system. It provides exact values, classes, and implementation details that MUST be followed when adding new components or features. The styling must remain consistent with the existing dark theme and color scheme.

## Technical Specifications

### 1. Tailwind Configuration

The project uses Tailwind CSS with the following configuration:

```js
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      // Any theme extensions should maintain the dark color scheme
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
```

### 2. Base CSS Variables

```css
/* in index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-rgb: 0, 0, 0;
  }
  
  body {
    color: rgb(var(--foreground-rgb));
    background: rgb(var(--background-rgb));
    background-color: #1a1a1a;
  }
}

/* Animation utilities */
@layer utilities {
  .animate-fade-in {
    animation: fadeIn 0.3s ease-in-out;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Critical overrides */
body {
  background-color: #1a1a1a;
  color: #ffffff;
}

* {
  color: #ffffff !important;
  background-color: transparent !important;
}
```

### 3. Exact Hex Color Codes

| Element | Tailwind Class | Hex Code |
|---------|----------------|----------|
| Primary Background | `bg-black` | `#000000` |
| Secondary Background | `bg-gray-900` | `#111827` |
| Component Background | `bg-gray-800` | `#1f2937` |
| Primary Text | `text-white` | `#ffffff` |
| Secondary Text | `text-gray-300` | `#d1d5db` |
| Muted Text | `text-gray-400` | `#9ca3af` |
| Primary Accent | `bg-indigo-600` | `#4f46e5` |
| Primary Accent Hover | `hover:bg-indigo-700` | `#4338ca` |
| Secondary Accent | `text-indigo-400` | `#818cf8` |
| Success | `bg-green-600` | `#16a34a` |
| Warning | `bg-amber-600` | `#d97706` |
| Error | `bg-red-600` | `#dc2626` |

### 4. Component Implementation

#### Button Components

```tsx
// Primary Button
<button 
  className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900"
>
  Button Text
</button>

// Secondary Button
<button 
  className="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900"
>
  Button Text
</button>

// Danger Button
<button 
  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-900"
>
  Delete
</button>
```

#### Card Components

```tsx
// Standard Card
<div className="bg-gray-800 p-6 rounded-lg shadow-lg">
  <h3 className="text-xl font-semibold text-white mb-2">Card Title</h3>
  <p className="text-gray-400">Card content goes here...</p>
</div>

// Interactive Card
<div className="bg-gray-800 p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow cursor-pointer">
  <h3 className="text-xl font-semibold text-white mb-2">Interactive Card</h3>
  <p className="text-gray-400">Click me...</p>
</div>
```

#### Form Components

```tsx
// Input Field
<div className="mb-4">
  <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
    Email
  </label>
  <input
    type="email"
    id="email"
    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white"
    placeholder="your@email.com"
  />
</div>

// Select Field
<div className="mb-4">
  <label htmlFor="country" className="block text-sm font-medium text-gray-300 mb-1">
    Country
  </label>
  <select
    id="country"
    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white"
  >
    <option>United States</option>
    <option>Canada</option>
    <option>Mexico</option>
  </select>
</div>
```

#### Navigation Components

```tsx
// Active Link
<Link
  to="/dashboard"
  className="inline-flex items-center px-1 pt-1 border-b-2 border-indigo-500 text-sm font-medium text-white"
>
  Dashboard
</Link>

// Inactive Link
<Link
  to="/profile"
  className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-300 hover:border-gray-300 hover:text-white"
>
  Profile
</Link>
```

### 5. Page Layout Structure

Always follow this structure for page layouts:

```tsx
const PageComponent: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Page content goes in a container */}
      <div className="container mx-auto px-4 py-8">
        {/* Page header */}
        <h1 className="text-4xl font-bold text-white mb-6">Page Title</h1>
        
        {/* Content section */}
        <section className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Section Title</h2>
          {/* Section content */}
        </section>
        
        {/* Grid layout for cards/items */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Grid items */}
        </div>
      </div>
    </div>
  );
};
```

## Warnings and Non-Negotiable Elements

### ⚠️ NEVER CHANGE THESE ELEMENTS:

1. **Never change the dark theme** to a light theme
2. **Never use background colors lighter than `#1f2937`** for any component
3. **Never use text colors darker than `#d1d5db`** for readability
4. **Always use the indigo accent color** (`#4f46e5`) for primary actions and highlights
5. **Never remove the rounded corners** (`rounded-lg`) from interactive elements
6. **Never change the base font family** from the system UI sans-serif stack

## Implementation Example

Here's a complete example of a new page component that follows all styling guidelines:

```tsx
import React from 'react';
import { Link } from 'react-router-dom';

const NewFeaturePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-white">
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-white mb-6">New Feature</h1>
        
        <div className="bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
          <p className="text-gray-300 mb-4">
            This is a new feature that follows the exact styling guidelines.
          </p>
          <button className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
            Primary Action
          </button>
        </div>
        
        <h2 className="text-2xl font-bold text-white mb-4">Feature Options</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-2">Option One</h3>
            <p className="text-gray-400 mb-4">Description for option one.</p>
            <button className="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors w-full">
              Select
            </button>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-2">Option Two</h3>
            <p className="text-gray-400 mb-4">Description for option two.</p>
            <button className="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors w-full">
              Select
            </button>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-2">Option Three</h3>
            <p className="text-gray-400 mb-4">Description for option three.</p>
            <button className="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors w-full">
              Select
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default NewFeaturePage;
```

By adhering strictly to this design system, you will maintain the consistent styling and user experience of the CS Gauntlet application.
