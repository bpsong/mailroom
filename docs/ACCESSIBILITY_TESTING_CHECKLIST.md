# Accessibility Testing Checklist

Use this checklist to verify accessibility compliance for the Mailroom Tracking System.

## Keyboard Navigation Testing

### General Navigation
- [ ] Tab key moves focus through all interactive elements in logical order
- [ ] Shift+Tab moves focus backwards
- [ ] Enter/Space activates buttons and links
- [ ] Escape closes modals and dropdowns
- [ ] Arrow keys navigate within menus and select dropdowns
- [ ] Focus is visible on all interactive elements
- [ ] No keyboard traps (focus can always move away)

### Specific Components
- [ ] Navigation menu is fully keyboard accessible
- [ ] User dropdown menu works with keyboard
- [ ] Theme toggle button is keyboard accessible
- [ ] All form inputs can be reached and filled via keyboard
- [ ] Modal dialogs trap focus appropriately
- [ ] Modal close buttons are keyboard accessible
- [ ] Package status update modal works with keyboard
- [ ] Photo upload modal works with keyboard
- [ ] Search autocomplete works with keyboard (arrow keys to select)

## Screen Reader Testing

### NVDA (Windows) / JAWS (Windows) / VoiceOver (Mac)
- [ ] Page title is announced correctly
- [ ] Heading hierarchy is logical (h1 → h2 → h3)
- [ ] Navigation landmarks are announced (navigation, main, complementary, contentinfo)
- [ ] Skip to content link is announced and functional
- [ ] Form labels are announced with inputs
- [ ] Required fields are announced as required
- [ ] Error messages are announced
- [ ] Status badges announce status text
- [ ] Loading states are announced (aria-live regions)
- [ ] Success/error toasts are announced
- [ ] Table headers are announced correctly
- [ ] Modal dialog titles are announced
- [ ] Button purposes are clear from labels

### Test Pages
- [ ] Login page
- [ ] Dashboard
- [ ] Package list
- [ ] Package registration form
- [ ] Package detail page
- [ ] User management (admin)
- [ ] Recipient management (admin)
- [ ] Reports page (admin)

## Color Contrast Testing

### Tools
- Use WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Use browser DevTools accessibility panel
- Use axe DevTools browser extension

### Elements to Test
- [ ] Body text on light background (minimum 4.5:1)
- [ ] Body text on dark background (minimum 4.5:1)
- [ ] Button text on primary color (minimum 4.5:1)
- [ ] Link text (minimum 4.5:1)
- [ ] Status badge text:
  - [ ] Registered (badge-neutral)
  - [ ] Awaiting Pickup (badge-warning)
  - [ ] Out for Delivery (badge-info)
  - [ ] Delivered (badge-success)
  - [ ] Returned (badge-error)
- [ ] Form input text (minimum 4.5:1)
- [ ] Placeholder text (minimum 4.5:1)
- [ ] Error message text (minimum 4.5:1)
- [ ] Disabled element text (minimum 3:1)

## Focus Indicators

### Visual Focus Testing
- [ ] All buttons show clear focus state
- [ ] All links show clear focus state
- [ ] All form inputs show clear focus state
- [ ] All checkboxes/radios show clear focus state
- [ ] All select dropdowns show clear focus state
- [ ] Menu items show clear focus state
- [ ] Focus indicators have sufficient contrast (minimum 3:1)
- [ ] Focus indicators are not obscured by other elements

## Form Accessibility

### Form Labels
- [ ] All inputs have associated labels
- [ ] Labels are properly linked (for/id attributes)
- [ ] Labels are visible (not just placeholder text)
- [ ] Required fields are marked visually and programmatically

### Form Validation
- [ ] Validation errors are clearly visible
- [ ] Error messages are descriptive and helpful
- [ ] Errors are announced to screen readers
- [ ] Invalid fields are marked with aria-invalid
- [ ] Error messages are associated with inputs (aria-describedby)
- [ ] Form can be submitted with keyboard (Enter key)

### Specific Forms
- [ ] Login form
- [ ] Package registration form
- [ ] Recipient search/autocomplete
- [ ] Status update form
- [ ] Photo upload form
- [ ] User creation form
- [ ] Password change form

## Mobile Accessibility

### Touch Targets
- [ ] All buttons are at least 44x44px
- [ ] All links are at least 44x44px
- [ ] Adequate spacing between touch targets (minimum 8px)
- [ ] Form inputs are large enough for touch

### Mobile Screen Readers
- [ ] VoiceOver (iOS) announces all elements correctly
- [ ] TalkBack (Android) announces all elements correctly
- [ ] Swipe gestures work correctly
- [ ] Form inputs don't cause unwanted zoom (font-size ≥ 16px)

### Responsive Design
- [ ] All content is accessible at 320px width
- [ ] No horizontal scrolling required
- [ ] Text remains readable at all viewport sizes
- [ ] Touch targets remain adequate on small screens

## Image and Icon Accessibility

### Images
- [ ] All content images have descriptive alt text
- [ ] Decorative images have empty alt="" or are CSS backgrounds
- [ ] Alt text is concise and descriptive

### Icons
- [ ] Decorative icons are hidden from screen readers (aria-hidden="true")
- [ ] Functional icons have descriptive labels (aria-label)
- [ ] Icon-only buttons have text alternatives
- [ ] SVG icons have appropriate titles when needed

## ARIA Attributes

### Landmarks
- [ ] Main content uses `<main>` or role="main"
- [ ] Navigation uses `<nav>` or role="navigation"
- [ ] Sidebar uses `<aside>` or role="complementary"
- [ ] Footer uses `<footer>` or role="contentinfo"

### Dynamic Content
- [ ] Loading states use aria-live="polite"
- [ ] Error messages use aria-live="assertive"
- [ ] Toast notifications are announced
- [ ] HTMX updates are announced when appropriate

### Interactive Elements
- [ ] Buttons use `<button>` element (not div with onclick)
- [ ] Links use `<a>` element with href
- [ ] Modal dialogs use proper dialog element or role
- [ ] Expandable sections use aria-expanded
- [ ] Tabs use proper ARIA tab pattern (if applicable)

## Automated Testing

### Tools to Run
- [ ] axe DevTools browser extension
- [ ] WAVE Web Accessibility Evaluation Tool
- [ ] Lighthouse accessibility audit (Chrome DevTools)
- [ ] Pa11y or similar CLI tool

### Pages to Test
- [ ] All public pages
- [ ] All authenticated pages
- [ ] All admin pages
- [ ] All forms
- [ ] All modals

## Browser and Device Testing

### Desktop Browsers
- [ ] Chrome (Windows)
- [ ] Firefox (Windows)
- [ ] Edge (Windows)
- [ ] Safari (macOS)

### Mobile Browsers
- [ ] Safari (iOS)
- [ ] Chrome (Android)

### Screen Readers
- [ ] NVDA + Chrome (Windows)
- [ ] JAWS + Chrome (Windows)
- [ ] VoiceOver + Safari (macOS)
- [ ] VoiceOver + Safari (iOS)
- [ ] TalkBack + Chrome (Android)

## Zoom and Magnification

### Zoom Testing
- [ ] Page is usable at 200% zoom
- [ ] No horizontal scrolling at 200% zoom
- [ ] All content remains visible at 200% zoom
- [ ] Text doesn't overlap at 200% zoom
- [ ] Interactive elements remain clickable at 200% zoom

### Text Resize
- [ ] Page is usable when browser text size is increased
- [ ] Layout doesn't break with larger text
- [ ] No content is cut off with larger text

## Additional Checks

### Motion and Animation
- [ ] Respects prefers-reduced-motion setting
- [ ] No auto-playing animations that can't be paused
- [ ] Animations don't cause seizures (no flashing > 3 times/second)

### Timing
- [ ] Session timeout warnings are provided
- [ ] Users have adequate time to complete forms
- [ ] No time limits on reading content

### Language
- [ ] Page language is set (lang attribute on html)
- [ ] Language changes are marked (lang attribute on elements)

### Error Prevention
- [ ] Destructive actions require confirmation
- [ ] Form data can be reviewed before submission
- [ ] Users can undo or correct mistakes

## Sign-off

### Tester Information
- Tester Name: ___________________________
- Date: ___________________________
- Browser/Device: ___________________________
- Screen Reader (if applicable): ___________________________

### Results
- [ ] All critical issues resolved
- [ ] All major issues resolved
- [ ] Minor issues documented for future improvement
- [ ] WCAG 2.1 Level AA compliance achieved

### Notes
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
