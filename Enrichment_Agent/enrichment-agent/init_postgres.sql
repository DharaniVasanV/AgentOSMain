-- PostgreSQL Database Schema Initialization Script for Enrichment Agent Project
-- Supports UUID generation, JSONB data types, indices, and meeting enrichment storage.

-- 1. Enable UUID Extension (PostgreSQL 13+ standard uuid-ossp or pgcrypto)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Meetings Table
-- Mock schema based on meetings_schema.md
-- Added `searched_details` (JSONB) column to store data searched & extracted via the `description` column.
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    meeting_url TEXT,
    meeting_date DATE,
    start_time TIME,
    end_time TIME,
    platform VARCHAR(50) DEFAULT 'google_meet',
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    
    -- Platform Specifics
    meeting_id VARCHAR(255),
    passcode VARCHAR(255),
    
    -- Email Agent Columns
    email_id VARCHAR(255),
    organizer VARCHAR(255),
    description TEXT,                  -- Used as input for enrichment
    time_zone VARCHAR(50),
    
    -- Searched & Enriched Details Column
    searched_details JSONB DEFAULT '{}'::jsonb, -- Stores search results and extracted details
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indices for Meetings Table
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_meeting_date ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_meetings_email_id ON meetings(email_id);

-- 3. Enrichment Records Table
CREATE TABLE IF NOT EXISTS enrichment_records (
    id SERIAL PRIMARY KEY,
    external_record_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT DEFAULT '',       -- Input description for enrichment
    sender VARCHAR(255) DEFAULT '',
    priority VARCHAR(50) DEFAULT 'MEDIUM',
    original_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    enriched_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    searched_details JSONB DEFAULT '{}'::jsonb,  -- Stores additional web search details
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indices for Enrichment Records Table
CREATE INDEX IF NOT EXISTS idx_enrichment_records_ext_id ON enrichment_records(external_record_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_records_category ON enrichment_records(category);
CREATE INDEX IF NOT EXISTS idx_enrichment_records_status ON enrichment_records(status);

-- 4. Enrichment Sources Table
CREATE TABLE IF NOT EXISTS enrichment_sources (
    id SERIAL PRIMARY KEY,
    enrichment_record_id INTEGER NOT NULL REFERENCES enrichment_records(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    source_url TEXT NOT NULL,
    source_type VARCHAR(50) DEFAULT 'web_search',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_record_id ON enrichment_sources(enrichment_record_id);

-- 5. Discovered Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    enrichment_record_id INTEGER NOT NULL REFERENCES enrichment_records(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    document_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_record_id ON documents(enrichment_record_id);
