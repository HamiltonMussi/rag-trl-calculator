# araucárIA - TRL Calculator Extension

A modern, refactored Chrome extension that provides AI assistance for Technology Readiness Level (TRL) calculations.

## Features

- **AI-Powered Assistance**: Get intelligent suggestions for TRL questionnaire answers
- **Document Management**: Upload and manage technology documentation
- **Multi-page Support**: Works across different stages of the TRL assessment process
- **Modern Architecture**: Clean, maintainable code with ES6+ modules
- **Accessibility**: Full WCAG compliance with screen reader support
- **Responsive Design**: Works seamlessly on all device sizes

## Architecture

### File Structure

```
extension/
├── manifest.json              # Extension configuration
├── assets/
│   └── icons/                # Extension icons
├── src/
│   ├── css/                  # Stylesheets
│   │   ├── components.css    # Component styles
│   │   ├── animations.css    # Animation definitions
│   │   ├── utilities.css     # Utility classes
│   │   └── accessibility.css # Accessibility styles
│   ├── js/                   # Main scripts
│   │   ├── initial.js        # Initial questions page
│   │   ├── questionnaire.js  # Main questionnaire page
│   │   ├── trl-questions.js  # TRL criteria pages
│   │   └── background.js     # Service worker
│   ├── utils/                # Utility modules
│   │   ├── api.js           # API communication
│   │   ├── storage.js       # Chrome storage helpers
│   │   └── dom.js           # DOM manipulation utilities
│   └── components/           # UI components
│       ├── ui.js            # UI helper functions
│       └── fileManager.js   # File management component
```

### Key Components

#### Background Service (`src/js/background.js`)
- Handles API requests through a centralized proxy
- Manages Chrome storage operations
- Maintains session state and technology context

#### Content Scripts
- **Initial Script** (`src/js/initial.js`): Parses and stores technology information
- **Questionnaire Script** (`src/js/questionnaire.js`): Handles main questionnaire and file management
- **TRL Questions Script** (`src/js/trl-questions.js`): Provides AI assistance for individual TRL criteria

#### Utility Modules
- **API Utils** (`src/utils/api.js`): Centralized API communication with error handling
- **Storage Utils** (`src/utils/storage.js`): Chrome storage abstraction layer
- **DOM Utils** (`src/utils/dom.js`): DOM manipulation and event handling helpers

#### UI Components
- **UI Components** (`src/components/ui.js`): Reusable UI elements (loader, notifications, buttons)
- **File Manager** (`src/components/fileManager.js`): Complete file upload and management system

## Installation

1. Clone or download the extension files
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked" and select the extension directory
5. The extension should now appear in your extensions list

## Usage

### Technology Selection
The extension automatically detects technology selection on the initial questions page and stores this information for use across all pages.

### Document Management
1. Navigate to the questionnaire page
2. The file manager modal will appear automatically if no documents are uploaded
3. Upload PDF, DOC, DOCX, or TXT files containing technology documentation
4. Files are processed and indexed for AI queries

### AI Assistance
Once documents are uploaded:
1. AI assistance buttons appear on questionnaire and TRL criteria pages
2. Click any AI button to get intelligent suggestions based on your documentation
3. Answers are formatted with justifications and confidence levels

## API Integration

The extension integrates with a local backend service at `http://127.0.0.1:8000` with the following endpoints:

- `POST /set-technology-context`: Initialize technology context
- `POST /upload-files`: Upload document chunks
- `POST /list-files`: List uploaded documents
- `POST /remove-file`: Remove documents
- `POST /answer`: Get AI responses to questions
- `POST /status`: Check document processing status

## Requirements

- Chrome 88+ (Manifest V3 compliant)
- Backend server running at `http://127.0.0.1:8000`

## Technical Details

- **Architecture**: ES6+ modules with modern JavaScript
- **Accessibility**: WCAG 2.1 AA compliant
- **Security**: Content Security Policy compliant
- **Performance**: Optimized file upload with chunking

