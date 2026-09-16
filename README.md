# 💳 PayForensics — UPI Fraud Ring & Merchant Analytics

> An AI-powered FinTech fraud analytics and investigation platform for detecting suspicious transactions, analyzing merchant and user risk, identifying fraud rings, and assisting investigators with grounded natural-language analytics.

---

## 🚨 Problem Statement

Modern digital payment systems generate massive volumes of micro-transactions every day. Detecting fraud from these transactions is challenging because fraudulent activity can be distributed across multiple users, merchants, transactions, and accounts.

The challenge becomes even harder when payment data contains:

- Missing UTR numbers
- Inconsistent or messy transaction records
- Suspicious transaction patterns
- Compromised merchant accounts
- Synthetic identities
- Circular money movement
- Chargeback activity
- High-risk users and merchants

Traditional dashboards often focus on individual transactions and fail to provide a connected view of the entities involved.

**PayForensics** addresses this problem by transforming payment analytics data into an interactive fraud investigation platform.

---

# 🎯 Objective

The primary objective of PayForensics is to provide investigators with a centralized platform to:

- Analyze high-volume payment transactions
- Identify suspicious transactions
- Measure merchant-level risk
- Analyze user and KYC information
- Investigate chargebacks
- Detect and explore fraud rings
- Understand relationships between users, merchants, and transactions
- Ask natural-language questions about the project's analytics data using an AI Investigator

---

# 🧠 Key Features

## 📊 1. Executive Overview

Provides a high-level view of the payment ecosystem through interactive KPIs and visualizations.

Key insights include:

- Transaction volume
- Transaction amounts
- Risk distribution
- Transaction status
- Merchant category distribution
- Fraud-related metrics
- Daily activity trends

The overview allows investigators to quickly understand the overall state of the dataset.

---

## 💳 2. Transaction Intelligence

The Transactions section provides detailed transaction-level analysis.

Investigators can:

- Filter transactions by date
- Filter by merchant category
- Filter by risk level
- Filter by transaction status
- Filter by transaction amount
- Explore suspicious transactions
- Investigate individual transaction records

The dashboard provides an interactive way to move from aggregate transaction statistics to individual records.

---

## 🏪 3. Merchant Intelligence

The Merchant Intelligence module focuses on merchant-level risk.

It helps analyze:

- Merchant risk
- Transaction activity
- Chargeback behavior
- Disputed transactions
- Merchant categories
- Suspicious merchant activity

Investigators can use merchant-level insights to identify entities that may require further investigation.

---

## 👤 4. User & KYC Risk

The User & KYC section combines user-level analytics with KYC information.

It provides visibility into:

- User risk information
- KYC attributes
- Transaction activity
- User-level investigation
- Suspicious user behavior

This creates a connection between payment activity and identity-level information.

---

## 💰 5. Chargeback Analytics

Chargebacks can provide important signals for identifying potentially suspicious merchant or user activity.

PayForensics analyzes:

- Chargeback records
- Disputed amounts
- Merchant-level disputes
- User-level disputes
- Chargeback patterns

This allows investigators to identify entities with significant dispute activity.

---

## 🕸️ 6. Fraud Ring Detection

Fraud often involves multiple connected entities rather than a single transaction.

The Fraud Rings module provides analysis of detected fraud-ring structures using:

- Fraud ring information
- Ring membership data
- Connected users
- Transaction relationships

This helps investigators move beyond isolated transaction analysis and investigate potentially coordinated activity.

---

# 🤖 7. AI Investigator

PayForensics includes a **scope-restricted AI Investigator powered by Google Gemini**.

Unlike a general-purpose chatbot, the AI Investigator is designed specifically for analytics questions related to the PayForensics dataset.

### Example questions

```text
Which merchant has the highest chargeback ratio?
