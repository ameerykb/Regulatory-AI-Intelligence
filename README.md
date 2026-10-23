# Regulatory AI Intelligence System

An AI-powered regulatory intelligence and compliance impact analysis system built using Python, LangChain, LangGraph, ChromaDB, and a locally hosted large language model.

The system analyzes regulatory changes, evaluates their potential impact on a fictional company's privacy policy, and provides evidence-grounded answers to regulatory questions.

## Project Overview

This project uses India's Digital Personal Data Protection (DPDP) Rules 2025 as a case study.

It compares draft and final regulatory documents to identify changes and assess how those changes may affect an organization's existing privacy policy.

The application combines document processing, semantic search, retrieval-augmented generation (RAG), AI-assisted analysis, citation validation, and human review workflows.

## Key Features

- **Regulatory Document Processing:** Extracts and structures information from regulatory PDF documents.
- **Regulatory Change Detection:** Compares draft and final regulations to identify modifications.
- **Policy Impact Analysis:** Evaluates regulatory changes against a predefined fictional company privacy policy.
- **AI Regulatory Chatbot:** Answers regulatory questions using retrieved evidence and source citations.
- **Semantic Search:** Retrieves relevant regulatory content using embeddings and ChromaDB.
- **Claim Verification:** Extracts claims and evaluates their supporting evidence.
- **Prompt Injection Detection:** Identifies suspicious instructions within retrieved content.
- **Human Review Workflow:** Supports review of AI-generated findings.
- **Report Generation:** Produces structured regulatory analysis and impact reports.
- **Streamlit Dashboard:** Provides an interface for exploring the system's capabilities.

## Technology Stack

| Category | Technologies |