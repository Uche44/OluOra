---
name: OluOra
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e4e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#414944'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0f0'
  outline: '#717974'
  outline-variant: '#c0c8c3'
  surface-tint: '#396756'
  primary: '#00261b'
  on-primary: '#ffffff'
  primary-container: '#0b3d2e'
  on-primary-container: '#79a894'
  inverse-primary: '#a0d1bc'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#1f211f'
  on-tertiary: '#ffffff'
  tertiary-container: '#353634'
  on-tertiary-container: '#9f9f9c'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#bcedd7'
  primary-fixed-dim: '#a0d1bc'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#214f3f'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#e3e2e0'
  tertiary-fixed-dim: '#c7c6c4'
  on-tertiary-fixed: '#1a1c1a'
  on-tertiary-fixed-variant: '#464745'
  background: '#fcf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e1'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  display-md:
    fontFamily: Playfair Display
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-md:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Literata
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Literata
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Literata
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Literata
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1440px
  gutter: 32px
  margin-desktop: 64px
  section-gap: 120px
---

## Brand & Style
The design system is anchored in an "Editorial Intelligence" aesthetic, merging the high-end print world of *Kinfolk* with the precision of modern SaaS leaders like Vercel and Stripe. The personality is calm and authoritative, positioning AI not as a chaotic tool, but as a sophisticated creative partner for professional YouTube creators.

The style is **Minimalist-Glassmorphic**. It utilizes expansive white space, intentional lithographic layouts, and subtle translucent layers to create a sense of depth and focus. Every element is designed to feel permanent and premium, avoiding the frantic visuals common in creator tools in favor of a serene, studio-like atmosphere.

## Colors
The palette is rooted in organic, high-contrast tones that evoke stability and luxury.

- **Primary (Deep Forest Green):** Used for primary actions, navigation backgrounds, and high-impact brand moments. It represents growth and maturity.
- **Accent (Warm Gold):** Applied sparingly to draw attention to premium features, AI-generated insights, or "Pro" status indicators.
- **Surface (Soft Off-White):** The canvas of the application. It reduces eye strain and provides a softer contrast than pure white, enhancing the editorial feel.
- **Typography:** Rich Charcoal is used for maximum legibility in headings, while Softer Charcoal is reserved for metadata and secondary UI labels.

## Typography
This design system utilizes **Playfair Display** for headlines to inject a sense of craftsmanship and tradition. **Literata** (selected as a refined alternative to Lora for enhanced digital readability) handles all body text and UI labels, maintaining the scholarly, "intelligent" tone across the interface.

Line heights are intentionally generous to support the spacious brand narrative. Display styles use tighter letter spacing for a modern, editorial look, while small labels use increased tracking for better legibility on high-density displays.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy on desktop to ensure content remains centered and readable, mimicking the layout of a premium magazine spread. 

- **Grid:** A 12-column grid with wide 32px gutters to prevent visual clutter.
- **Rhythm:** An 8px linear scale is used for all internal component spacing.
- **Negative Space:** Content sections are separated by significant vertical gaps (120px+) to allow the user's focus to rest on one task or insight at a time. 
- **Desktop Focus:** While responsive, the desktop experience prioritizes a multi-pane layout where the left navigation is static and the right utility panel (AI insights) floats over the primary workspace.

## Elevation & Depth
Depth is communicated through **Glassmorphism** and **Ambient Shadows** rather than harsh borders.

- **Surface Layers:** The base is the Soft Off-White. Cards and containers use a pure white background with 80% opacity and a 20px backdrop blur when positioned over images or gradients.
- **Shadows:** Use a "Natural Diffusion" approach. Shadows should be long and very low opacity (e.g., `box-shadow: 0 20px 40px rgba(11, 61, 46, 0.04)`), tinted slightly with the Deep Forest Green to keep the elevation feeling organic.
- **Interaction:** On hover, elements should slightly lift (move -2px Y-axis) and the shadow should expand and soften, creating a tactile "float" effect.

## Shapes
The shape language is sophisticated and approachable. All primary containers, such as dashboard cards and content modules, use a **16px (rounded-lg)** or **24px (rounded-xl)** corner radius. 

Smaller UI components like buttons and input fields utilize the **8px (rounded)** base. This "nested rounding" ensures that the interface feels cohesive and soft, removing the clinical "tech" feel of sharp corners.

## Components
- **Buttons:** Primary buttons use the Deep Forest Green with white text and an 8px radius. Secondary buttons use a minimal 1px border of the primary color or a ghost style with the Primary Text.
- **Cards:** Cards are the heart of the system. They must feature a 1px stroke in a very faint version of the primary color (opacity 5-10%) to define edges without adding visual weight.
- **AI Insights (Chips):** Use the Warm Gold for subtle backgrounds (10% opacity) with the gold color for text to denote AI-generated content or suggestions.
- **Input Fields:** Use a subtle inset shadow and the Soft Off-White background to create a "pressed" paper effect.
- **Charts:** Use a refined palette of Forest Green, Gold, and muted Sage. Lines should be thin (1.5pt) and use curved interpolation for an elegant, fluid data visualization experience.
- **Lists:** Content lists should have generous vertical padding (24px) and use thin horizontal separators rather than boxes to maintain the editorial flow.