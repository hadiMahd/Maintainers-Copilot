# Widget Embed Guide

*Placeholder — will be populated during Phase 9 implementation.*

## Overview

The embeddable widget is a Vite React chatbot surface delivered through a
loader script and iframe isolation.

## Installation

```html
<script src="{backend}/widget/loader.js" data-widget-id="{widget_id}"></script>
```

## Configuration

- Allowed origins
- Theme
- Greeting
- Position
- Enabled tools

## Security

- Origin allowlisting
- CSP frame-ancestors
- Anonymous session tokens
- No Streamlit coupling
