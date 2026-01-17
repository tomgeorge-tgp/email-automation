# 📧 Bulk Email Sender (Azure Communication Services)

A high-performance, asynchronous bulk email sender built with FastAPI, Streamlit, and Polars. This application allows you to send personalized emails using HTML templates and data from Excel files.

## Features

- **Parallel Processing**: Emails are sent in parallel with controlled concurrency to optimize throughput.
- **Polars Integration**: Uses Polars for lightning-fast Excel parsing and data handling.
- **Jinja2 Templating**: Full support for dynamic HTML templates.
- **Azure Communication Services**: Reliable email delivery through Azure's enterprise-grade infrastructure.
- **Streamlit Frontend**: A simple, user-friendly interface for uploading templates and data.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed (recommended for dependency management).
- Azure Communication Services Resource (Connection String and Verified Sender Domain).
- Python 3.12+

## Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd email_sender
   ```

2. **Environment Variables**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Fill in your Azure details in `.env`:
   ```env
   ACS_CONNECTION_STRING="your_connection_string_here"
   ACS_SENDER_EMAIL="DoNotReply@your-verified-domain.com"
   ```

3. **Install Dependencies**:
   ```bash
   uv sync
   ```

## Running the Application

You can use the provided `Makefile` to run the application easily.

- **Start both Backend & Frontend**:
  ```bash
  make dev
  ```
  - Backend (FastAPI) will be available at: `http://localhost:9000`
  - Frontend (Streamlit) will be available at: `http://localhost:8501`

- **Stop the application**:
  Press `Ctrl+C` in the terminal.

## Usage Guide

1. **Prepare your Excel file**:
   - Ensure your Excel file (`.xlsx`) has a column named `email` for the recipient addresses.
   - Ensure it has a column named `subject` for the email subject of each recipient.
   - Any other columns can be used as variables in your HTML template (e.g., `first_name`, `company`).

2. **Prepare your HTML template**:
   - Use Jinja2 syntax for variables: `Hello {{ first_name }}!`

3. **Send Emails**:
   - Upload the HTML template and the Excel file in the Streamlit UI.
   - Click **Send Emails**.

---

## ⚠️ Security Warning: Git Secret Leak

If you accidentally committed your `.env` file (as seen in recent git attempts), follow these steps to secure your repository:

1. **Remove `.env` from git tracking**:
   ```bash
   git rm --cached .env
   git commit -m "fix: remove sensitive .env from git tracking"
   ```

2. **Rewrite History (Optional but Recommended)**:
   Since secrets were already pushed (or attempted), the history still contains them. Use a tool like `bfg` or `git-filter-repo` to wipe them permanently.

3. **Rotate your Keys**:
   **CRITICAL**: If your Azure Connection String was exposed, go to the Azure Portal and **Regenerate your Keys** immediately.

4. **Push Protection**:
   If GitHub blocked your push, it is protecting you! Do not bypass it until you have removed the secret from the current commit.
