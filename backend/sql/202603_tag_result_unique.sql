-- Idempotent MySQL 8 migration for tags-v2 concurrent verification.
-- Keep the newest row for each (fkdbh, tag_path), then add the uniqueness guard.

DELETE older
FROM jq_tag_result AS older
JOIN jq_tag_result AS newer
  ON newer.fkdbh = older.fkdbh
 AND newer.tag_path = older.tag_path
 AND newer.id > older.id;

SET @has_index := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'jq_tag_result'
    AND index_name = 'uq_jq_tag_result_fkdbh_tag_path'
);
SET @ddl := IF(
  @has_index = 0,
  'ALTER TABLE jq_tag_result ADD UNIQUE INDEX uq_jq_tag_result_fkdbh_tag_path (fkdbh, tag_path)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Rollback (only if duplicates are acceptable again):
-- ALTER TABLE jq_tag_result DROP INDEX uq_jq_tag_result_fkdbh_tag_path;
