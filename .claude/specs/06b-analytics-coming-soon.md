# Spec: Analytics Coming Soon Page

## Overview
This feature adds an "Analytics" section to Spendly as a placeholder for the upcoming advanced analytics module. Logged-in users get an "Analytics" link in the navbar that opens a "coming soon" page announcing the feature. The page is visual only — no data, charts or database queries — and exists so the navigation and route are in place before real analytics are built.

## Depends on
- Step 3: Login + Logout (session must be set; `/analytics` must be a protected route)
- Step 5: Backend route for profile page (`g.user` loaded from the session on every request)

## Routes
- GET /analytics — render the analytics coming-soon page — logged-in only (redirect to /login if not authenticated)

## Database changes
No database changes.

## Templates
- Create: `templates/analytics.html` — extends `base.html`; a single centered card containing:
  1. A rounded-square icon tile with a clock icon (Lucide `clock`)
  2. A pill badge reading "Coming soon"
  3. The heading "Advanced Analytics"
  4. The description "We're working on powerful insights and visualizations to help you understand your spending patterns better."
  5. A row of three dots
  6. The note "We're crafting something special"
- Modify: `templates/base.html` — add an "Analytics" link to the navbar

## Files to change
- `app.py` — add an `analytics` view function for `/analytics` that redirects unauthenticated users to `/login` and renders `analytics.html`
- `templates/base.html` — navbar link, shown only to logged-in users, marked active on the analytics page
- `static/css/style.css` — styles for the coming-soon card and the navbar active state

## Files to create
- `templates/analytics.html`

## New dependencies
No new dependencies.

## Rules for implementation
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- No inline styles
- All internal links use `url_for(...)`
- Authentication guard: if no user is logged in, `redirect(url_for("login"))`
- The "Analytics" navbar link must not be rendered at all for logged-out users
- On `/analytics`, the navbar link has the `active` class and `aria-current="page"`; on other pages it has neither

## Definition of done
- [ ] Visiting `/analytics` without being logged in redirects to `/login`
- [ ] Visiting `/analytics` while logged in returns HTTP 200
- [ ] The page shows the heading "Advanced Analytics", the "Coming soon" badge, the description and the "We're crafting something special" note
- [ ] Logged-out users do not see an "Analytics" link in the navbar on any page
- [ ] Logged-in users see an "Analytics" link in the navbar that points to `/analytics`
- [ ] On `/analytics`, the navbar "Analytics" link is marked active (`active` class, `aria-current="page"`)
- [ ] On other pages (e.g. `/profile`), the "Analytics" link is not marked active
- [ ] No hex colour values appear in `analytics.html`
