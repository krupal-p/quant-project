
IF NOT EXISTS (SELECT 1
FROM sys.databases
WHERE name = 'quant_db')
BEGIN
    CREATE DATABASE quant_db;
END;

USE quant_db;

DROP SCHEMA IF EXISTS stg;
GO

CREATE SCHEMA stg;
GO

DROP TABLE IF EXISTS dim_index_tracker;
DROP TABLE IF EXISTS dim_sec_master;
DROP TABLE IF EXISTS dim_item_master;
DROP TABLE IF EXISTS fct_market_data;
DROP TABLE IF EXISTS stg.fct_market_data;
DROP TABLE IF EXISTS stg.dim_sec_master;

CREATE TABLE dim_sec_master
(
    symbol VARCHAR(14) PRIMARY KEY CHECK (symbol = UPPER(symbol)),
    underlyingSymbol VARCHAR(14),
    isin CHAR(12),
    shortName TEXT,
    longName TEXT,
    quoteType VARCHAR(10),
    currency VARCHAR(3),
    exchange VARCHAR(10),
    industryKey VARCHAR(50),
    sectorKey VARCHAR(50),
    uuid UNIQUEIDENTIFIER,
    longBusinessSummary TEXT
);
CREATE TABLE dim_item_master
(
    item_id smallint PRIMARY KEY,
    item_name TEXT,
    item_desc TEXT
);

CREATE TABLE dim_index_tracker
(
    symbol VARCHAR(14) REFERENCES dim_sec_master (symbol),
    index_name VARCHAR(50),
    date_added DATE,
    date_removed DATE,
    PRIMARY KEY (symbol, index_name)
);

CREATE TABLE fct_market_data
(
    symbol VARCHAR(14) REFERENCES dim_sec_master (symbol),
    item_id smallint REFERENCES dim_item_master (item_id),
    date_ DATE,
    value_ NUMERIC(30, 4),
    PRIMARY KEY (symbol, item_id, date_)
);

CREATE TABLE stg.fct_market_data
(
    symbol VARCHAR(14) REFERENCES dim_sec_master (symbol),
    item_id smallint REFERENCES dim_item_master (item_id),
    date_ DATE,
    value_ NUMERIC(30, 4),
    PRIMARY KEY (symbol, item_id, date_)
);

CREATE TABLE stg.dim_sec_master
(
    symbol VARCHAR(14) PRIMARY KEY
);