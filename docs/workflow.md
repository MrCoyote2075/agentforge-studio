# AgentForge Studio - Workflow Guide

## Overview

AgentForge Studio follows a structured 6-stage workflow to transform client requirements into fully functional websites. This document explains each stage and how agents collaborate throughout the process.

## The 6-Stage Process

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Project Workflow                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Stage 1         Stage 2         Stage 3         Stage 4                │
│ ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│ │ Intake   │──►│ Planning │──►│ Building │──►│ Review   │              │
│ └──────────┘   └──────────┘   └──────────┘   └──────────┘              │
│      │                                             │                    │
│      │                                             ▼                    │
│      │                                       Stage 5                    │
│      │                                      ┌──────────┐                │
│      │                          ◄───────────│ Testing  │                │
│      │                         (if issues)  └──────────┘                │
│      │                                             │                    │
│      │                                             ▼                    │
│      │                                       Stage 6                    │
│      │                                      ┌──────────┐                │
│      └─────────────(feedback)───────────────│ Delivery │                │
│                                             └──────────┘                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Stage Details

### Stage 1: Intake

**Lead Agent**: Intermediator

**Purpose**: Gather and understand client requirements

**Activities**:
1. Receive initial request from client
2. Ask clarifying questions
3. Understand project scope
4. Document requirements
5. Set expectations

**Inputs**:
- Client description (natural language)
- Reference examples
- Preferences and constraints

**Outputs**:
- Structured requirements document
- Feature list
- Priority ranking
- Timeline expectations

**Example Dialogue**:
```
Client: "I need a website for my bakery"

Intermediator: "I'd love to help you create a bakery website! 
To make sure we build exactly what you need, let me ask a few questions:

1. What's your bakery's name?
2. Do you want to display a menu/products?
3. Should customers be able to place orders online?
4. Do you have any color preferences or existing branding?
5. Are there any bakery websites you like that I can use as inspiration?"
```

### Stage 2: Planning

**Lead Agent**: Planner (with Orchestrator coordination)

**Purpose**: Create technical blueprint for the project

**Activities**:
1. Analyze requirements
2. Research best practices
3. Design architecture
4. Create file structure
5. Define component breakdown
6. Create task roadmap

**Inputs**:
- Structured requirements
- Client preferences
- Technical constraints

**Outputs**:
- Technical specification
- File structure plan
- Component list
- Task breakdown with dependencies
- Technology recommendations

**Specification Example**:
```yaml
project:
  name: "Sweet Delights Bakery"
  type: "static-website"
  
technologies:
  - HTML5
  - CSS3 (with Tailwind)
  - JavaScript (vanilla)
  
pages:
  - home:
      sections: [hero, featured-products, about-preview, testimonials]
  - menu:
      sections: [categories, product-grid, search-filter]
  - about:
      sections: [story, team, gallery]
  - contact:
      sections: [form, map, hours]

components:
  - ProductCard: { image, name, price, description }
  - CategoryNav: { categories[], activeFilter }
  - ContactForm: { fields[], validation, submit }
  
file_structure:
  src/:
    - index.html
    - menu.html
    - about.html
    - contact.html
    css/:
      - main.css
      - components.css
    js/:
      - main.js
      - menu.js
      - contact.js
    assets/:
      images/
      fonts/
```

### Stage 3: Building

**Lead Agents**: Frontend Agent, Backend Agent, Helper

**Purpose**: Generate the actual code and assets

**Activities**:
1. Create HTML structure
2. Write CSS styles
3. Implement JavaScript
4. Build backend (if needed)
5. Organize assets
6. Commit changes to Git

**Parallel Workflows**:
```
Frontend Agent                Backend Agent                Helper
      │                             │                         │
      ├─► HTML Structure            ├─► API Routes            ├─► Documentation
      │                             │                         │
      ├─► CSS Styling              ├─► Database Schema        ├─► .gitignore
      │                             │                         │
      ├─► JavaScript               ├─► Authentication        ├─► README
      │                             │                         │
      └─► React Components         └─► Server Config         └─► Asset Organization
```

**Build Progress Messages**:
```
Orchestrator → FrontendAgent: "Build home page hero section"
FrontendAgent → Orchestrator: "Hero section complete - index.html:10-45"

Orchestrator → FrontendAgent: "Build product card component"
FrontendAgent → Orchestrator: "ProductCard component ready - components/ProductCard.jsx"

Orchestrator → BackendAgent: "Create contact form endpoint"
BackendAgent → Orchestrator: "POST /api/contact endpoint ready - routes/contact.py"
```

### Stage 4: Review

**Lead Agent**: Reviewer

**Purpose**: Ensure code quality and best practices

**Activities**:
1. Review all generated code
2. Check for security issues
3. Verify best practices
4. Suggest improvements
5. Document findings

**Review Checklist**:
- [ ] HTML semantic structure
- [ ] CSS organization and naming
- [ ] JavaScript best practices
- [ ] Accessibility (a11y)
- [ ] Security vulnerabilities
- [ ] Performance optimizations
- [ ] Mobile responsiveness
- [ ] Browser compatibility

**Review Report Example**:
```json
{
  "overall_score": 85,
  "categories": {
    "code_quality": 90,
    "security": 80,
    "accessibility": 85,
    "performance": 85
  },
  "findings": [
    {
      "severity": "warning",
      "file": "menu.js",
      "line": 23,
      "issue": "Missing error handling in fetch call",
      "fix": "Add try-catch block around API call"
    },
    {
      "severity": "info",
      "file": "styles.css",
      "line": 156,
      "issue": "Could use CSS custom properties for colors",
      "fix": "Define :root variables for brand colors"
    }
  ],
  "passed": true
}
```

### Stage 5: Testing

**Lead Agent**: Tester

**Purpose**: Validate functionality and catch bugs

**Activities**:
1. Write unit tests
2. Create integration tests
3. Perform manual testing
4. Validate against requirements
5. Report bugs

**Test Types**:

| Type | Purpose | Example |
|------|---------|---------|
| Unit | Test individual functions | Form validation |
| Integration | Test component interaction | Form submission flow |
| E2E | Test complete user flows | Ordering process |
| Visual | Check UI appearance | Responsive layout |

**Test Report Example**:
```
Test Results
============

Total Tests: 24
Passed: 22
Failed: 2
Skipped: 0

Pass Rate: 91.7%

Failed Tests:
1. contact.test.js:45 - Form should show error for invalid email
   Expected: "Invalid email" message
   Got: No error message displayed
   
2. menu.test.js:78 - Filter should update product count
   Expected: 5 products
   Got: 12 products (all products shown)

Bugs Filed:
- BUG-001: Email validation not triggering (High)
- BUG-002: Product filter not updating correctly (Medium)
```

### Stage 6: Delivery

**Lead Agent**: Intermediator (with Helper support)

**Purpose**: Package and deliver the final project

**Activities**:
1. Fix any remaining issues
2. Generate final documentation
3. Create downloadable package
4. Provide deployment instructions
5. Get client feedback

**Deliverables**:
- Complete source code
- Documentation (README, API docs)
- Deployment guide
- Git repository
- Live preview URL

**Delivery Message**:
```
Intermediator: "Great news! Your bakery website is ready! 🎉

Here's what we've built for you:

✅ Homepage with hero section and featured products
✅ Menu page with category filtering
✅ About page with your story and team
✅ Contact page with working form

You can:
1. Preview it live at: http://localhost:8080
2. Download the source code: [Download ZIP]
3. View the code: [Browse Files]

Next steps for going live:
1. Choose a hosting provider (Netlify, Vercel, etc.)
2. Upload the files
3. Point your domain to the hosting

Would you like any changes before we finalize?"
```

## Iteration Cycle

When issues are found during Review or Testing, the workflow loops back:

```
     ┌───────────────────────────────────────────┐
     │                                           │
     ▼                                           │
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──┴───────┐
│ Building │──►│ Review   │──►│ Testing  │──►│ Issues?  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
     ▲                                           │ Yes
     │                                           │
     └───────────────────────────────────────────┘
```

## Workflow Status Updates

Throughout the process, the Intermediator provides status updates:

```
[Status Update]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: Sweet Delights Bakery
Stage: Building (3/6)
Progress: 65%

Current Activity:
├─ FrontendAgent: Building menu page [in progress]
├─ BackendAgent: Contact form endpoint [completed]
└─ Helper: Generating README [waiting]

Completed:
✓ Homepage
✓ Contact page
✓ API endpoints

Remaining:
○ Menu page
○ About page
○ Documentation
○ Final review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Error Handling

When errors occur, the system:

1. **Captures** the error details
2. **Notifies** the Orchestrator
3. **Attempts** automatic recovery
4. **Reports** to the Intermediator (if user action needed)

```
Error Flow:
Agent Error → Orchestrator → Retry/Reassign → Success/Escalate

Example:
FrontendAgent: "Error generating React component - missing dependency"
Orchestrator: "Checking for alternative approach..."
Orchestrator → Helper: "Research alternative component library"
Helper → Orchestrator: "Suggested: Use vanilla JS for this component"
Orchestrator → FrontendAgent: "Rebuild with vanilla JS approach"
FrontendAgent: "Component rebuilt successfully"
```

## Best Practices

### For Efficient Workflows

1. **Clear Requirements**: Start with detailed requirements to minimize iterations
2. **Parallel Tasks**: Orchestrator assigns independent tasks simultaneously
3. **Early Review**: Review components as they're built, not just at the end
4. **Continuous Testing**: Run tests after each major component
5. **Regular Updates**: Keep client informed of progress

### For Quality Results

1. **Follow Standards**: Use consistent coding conventions
2. **Document Everything**: Generate comprehensive documentation
3. **Test Thoroughly**: Cover edge cases and error scenarios
4. **Review Carefully**: Don't skip the review stage
5. **Validate Requirements**: Ensure final output matches initial requirements
