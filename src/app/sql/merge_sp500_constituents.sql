MERGE INTO dim_index_tracker AS target
USING stg.dim_index_tracker AS source
ON (target.symbol = source.symbol AND target.index_name = source.index_name)
WHEN MATCHED THEN
    UPDATE SET
        target.security_name = source.security_name,
        target.gics_sector = source.gics_sector,
        target.gics_sub_industry = source.gics_sub_industry,
        target.date_added = source.date_added
WHEN NOT MATCHED THEN
    INSERT (index_name, symbol, security_name, gics_sector, gics_sub_industry, date_added)
    VALUES (source.index_name, source.symbol, source.security_name, source.gics_sector, source.gics_sub_industry, source.date_added);