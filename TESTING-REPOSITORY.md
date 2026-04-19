# ACERS E2E Testing Repository

This document explains the end-to-end testing repository for the ACERS project.

## Overview

The `acers-e2e-cucumber-selenium-maven` directory contains a Maven-based end-to-end testing suite using:

- **Cucumber** for behavior-driven development (BDD) testing
- **Selenium** for browser automation
- **Maven** for dependency management and build automation
- **Java** as the programming language

## Environment Setup

This project uses [mise-en-place](https://mise.jdx.dev/) (mise) to manage development tools. The required tools are:

- **Java JDK 26.0.0**
- **Apache Maven 4.0.0-rc-5**

These tools are automatically managed by mise as defined in `~/.config/mise/config.toml`.

To verify your environment:

```bash
mise ls
java --version
mvn --version
```

## Test Execution

### Using Regular Maven (mvn)

#### Default Execution (Firefox)

```bash
mvn clean test "-Dbrowser=firefox"
```

#### Chrome Execution

If Firefox is not available, you can use Chrome:

```bash
mvn clean test "-Dbrowser=chrome"
```

### Using Maven Daemon (mvnd)

For faster builds, you can use Maven Daemon (mvnd) instead of regular Maven:

#### Firefox Execution with mvnd

```bash
mvnd clean test "-Dbrowser=firefox"
```

#### Chrome Execution with mvnd

```bash
mvnd clean test "-Dbrowser=chrome"
```

**Note:** mvnd provides parallel processing and daemon-based execution for improved performance, especially for large projects.

## Project Structure

```text
acers-e2e-cucumber-selenium-maven/
├── src/
│   ├── main/
│   │   └── java/                 # Page Object Model classes
│   └── test/
│       ├── java/                 # Step definitions and test runners
│       └── resources/
│           └── features/         # Cucumber feature files (.feature)
├── pom.xml                       # Maven configuration
└── Readme.md                     # Basic execution instructions
```

## Test Results Interpretation

**Current Status:** Tests are currently failing with login timeout issues.

From the test execution logs (both mvn and mvnd):

### Common Issues and Solutions

1. **SLF4J Warning** - "No SLF4J providers were found"
   - This is a logging configuration warning that doesn't affect test execution
   - Can be ignored or resolved by adding an SLF4J binding to pom.xml

2. **CDP Version Warning** - "Unable to find version of CDP to use for 147"
   - Occurs when ChromeDriver version doesn't match Chrome browser version
   - Solution: Update selenium-devtools dependency to match Chrome version

3. **TimeoutException** - "Expected condition failed: waiting for visibility of element"
   - Indicates that the expected web element was not found within the timeout period
   - Common causes:
     - Page navigation issues
     - Element locators that no longer match the UI
     - Authentication problems
     - Network/loading delays

### Current Test Failure Analysis

**Status:** Failing
**Error:** Login timeout - email input field not found
**Failure Location:** `pages.Loginpage.login(Loginpage.java:24)`

The test failure occurs at:

```bash
org.openqa.selenium.TimeoutException:
Expected condition failed: waiting for visibility of element located by By.xpath: //input[@type='email']
(tried for 20 second(s) with 500 milliseconds interval)
```

**Root Cause Analysis:**

- The login page is not loading properly or the email input field locator is outdated
- Possible issues:
  - Authentication flow changes in the application
  - Network connectivity problems to the test environment
  - UI changes that broke the XPath locator `//input[@type='email']`
  - Page loading delays exceeding the 20-second timeout

**Next Steps:**

1. Verify the application is running and accessible
2. Check the login page HTML structure manually
3. Update element locators if the UI has changed
4. Consider increasing timeout values for slow-loading pages

## Maintenance Notes

1. The project uses Maven 4.0.0-rc-5 which may show reflective access warnings - these are expected with this version
2. Plugin versions in pom.xml should be explicitly defined to avoid version binding warnings
3. Test data and credentials may need periodic updates
4. Browser drivers are managed automatically by Selenium 4+

## Troubleshooting

### Current Test Failure Resolution

The primary issue is the login timeout. To resolve:

1. **Verify Application Accessibility:**
   - Ensure the ACERS application is running and accessible
   - Check network connectivity to the test environment
   - Confirm the login page URL is correct

2. **Inspect Login Page Structure:**
   - Manually navigate to the login page in a browser
   - Use browser developer tools to inspect the email input field
   - Verify the XPath `//input[@type='email']` still matches the element

3. **Update Element Locators:**
   - If the login page HTML has changed, update the locator in `Loginpage.java`
   - Consider using more robust locators (ID, CSS selectors, or data attributes)

4. **Check for Authentication Changes:**
   - Verify if the authentication flow has been modified
   - Check if additional steps are required before the email field appears

### General Troubleshooting Steps

For other potential issues:

1. Review browser console logs for JavaScript errors
2. Check for UI changes that might affect other element locators
3. Consider increasing timeout values in WebDriverWait calls for slow-loading pages
4. Verify browser and WebDriver versions are compatible
5. Check for conflicting browser extensions that might interfere with automation
