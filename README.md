# FleetBook — Vehicle Booking System

**CST8917 Lab 3** — Serverless Applications | Winter 2026

## Overview

FleetBook is a serverless vehicle booking system built with Azure Service Bus, Azure Logic Apps, and Azure Functions. Customers submit bookings through a web app, a Logic App orchestrates processing by calling an Azure Function for fleet evaluation and pricing, then sends confirmation or rejection emails and publishes results to a Service Bus Topic with filtered subscriptions.

## Architecture

```
Web Client → Service Bus Queue → Logic App → Azure Function
                                      ↓
                              Condition (confirmed/rejected)
                             /                        \
                  Confirmation Email           Rejection Email
                  Publish to Topic             Publish to Topic
                  (label=confirmed)            (label=rejected)
                         ↓                           ↓
                   confirmed-sub               rejected-sub
```

## Project Files

| File | Description |
|------|-------------|
| `function_app.py` | Azure Function with booking evaluation and pricing logic |
| `requirements.txt` | Python dependencies (`azure-functions`) |
| `host.json` | Azure Functions host configuration |
| `test-function.http` | REST Client test requests for local testing |
| `client.html` | FleetBook web app for submitting bookings |
| `local.settings.example.json` | Local settings template (placeholder values) |
| `test_function_app.py` | Unit tests and property-based tests (pytest + Hypothesis) |

## Setup Instructions

### Prerequisites

- Python 3.11 or 3.12
- Azure Functions Core Tools v4
- Azure CLI
- An Azure subscription

### Local Development

1. Clone the repository
2. Copy `local.settings.example.json` to `local.settings.json` and fill in your values:
   ```
   cp local.settings.example.json local.settings.json
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Start Azurite (for local storage emulation)
5. Run the function locally:
   ```
   func start
   ```
6. Verify the health endpoint: `http://localhost:7071/api/health`

### Running Tests

```
pip install pytest hypothesis
pytest test_function_app.py -v
```

### Azure Resources

The following resources are provisioned in resource group `rg-serverless-lab3`:

| Resource | Name |
|----------|------|
| Service Bus Namespace | `fleetbook-booking-sb-9674` (Standard tier) |
| Queue | `booking-queue` |
| Topic | `booking-results` |
| Subscription | `confirmed-sub` (filter: `sys.label = 'confirmed'`) |
| Subscription | `rejected-sub` (filter: `sys.label = 'rejected'`) |
| Azure Function App | `fleetbook-func-9674` (Consumption, Linux, Python 3.12) |
| Logic App | `process-booking` (Consumption) |

### Web Client Configuration

1. Open `client.html` in a browser
2. Enter your Service Bus namespace name and SAS primary key in the config panel
3. Submit bookings and monitor results

## Demo Video

[YouTube link here]
