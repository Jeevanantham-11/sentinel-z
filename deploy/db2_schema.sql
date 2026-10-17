-- ==============================================================================
-- IBM Sentinel-Z: IBM Db2 for z/OS Native DDL & Audit Ledger Schema
-- Target: IBM Db2 for z/OS (v12 / v13) on IBM z16 / LinuxONE (s390x)
-- Purpose: In-Transaction Clinical Deterioration & Sepsis Interception Audit
-- ==============================================================================

-- 1. Create Dedicated Mainframe Storage Database
CREATE DATABASE SENTZDB
  CCSID UNICODE
  BUFFERPOOL BP1
  INDEXBP BP2;

-- 2. Create Universal Table Space (UTS - Partition-by-Growth)
CREATE TABLESPACE SENTZTS
  IN SENTZDB
  USING STOGROUP SYSDEFLT
  PRIQTY 10240
  SECQTY 2048
  ERASE NO
  LOCKSIZE ROW
  MAXROWS 255
  MAXPARTITIONS 32
  BUFFERPOOL BP1
  CLOSE NO;

-- 3. Core In-Transaction Immutable Audit Table
CREATE TABLE SENTINEL_AUDIT (
    TXN_ID          BIGINT          NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    TS              TIMESTAMP       NOT NULL DEFAULT CURRENT TIMESTAMP,
    PATIENT_ID      VARCHAR(32)     NOT NULL,
    RISK_SCORE      DECIMAL(5, 2)   NOT NULL,
    ACTION          VARCHAR(48)     NOT NULL,
    INFERENCE_MS    DECIMAL(8, 3)   NOT NULL,
    GUARDRAIL       VARCHAR(32)     NOT NULL,
    ALERT_STATUS    VARCHAR(24)     NOT NULL,
    CB_STATE        VARCHAR(12)     NOT NULL,
    PLATFORM        VARCHAR(24)     NOT NULL DEFAULT 's390x-Telum',
    PRIMARY KEY (TXN_ID)
) IN SENTZDB.SENTZTS;

-- 4. High-Performance Look-up Index for Patient Longitudinal Trajectory
CREATE INDEX IX_SENTINEL_PATIENT
  ON SENTINEL_AUDIT (PATIENT_ID, TS DESC)
  BUFFERPOOL BP2
  CLOSE NO;

-- 5. Index for Interception Audits & Hospital Quality Assurance
CREATE INDEX IX_SENTINEL_ACTION
  ON SENTINEL_AUDIT (ACTION, TS DESC)
  BUFFERPOOL BP2
  CLOSE NO;

-- 6. Enable Native Db2 Audit Policy for HIPAA Compliance & RACF Integration
AUDIT ALL ON TABLE SENTINEL_AUDIT;

COMMENT ON TABLE SENTINEL_AUDIT IS 
  'Sentinel-Z in-transaction pre-commit clinical deterrence ledger on IBM z16.';
