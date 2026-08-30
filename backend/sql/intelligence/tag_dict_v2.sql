-- ----------------------------
-- 警情打标 v2（已在业务库建表；此处仅作结构说明）
-- tag_dict_v2：四级标签字典
-- jq_tag_result：打标结果（一行一标签，按 fkdbh 关联 fkd_fkd）
-- ----------------------------

CREATE TABLE IF NOT EXISTS `tag_dict_v2` (
  `tag_id`   BIGINT NOT NULL AUTO_INCREMENT,
  `tag_code` VARCHAR(32)  NOT NULL COMMENT '稳定编码 TD-域缩写-序号',
  `domain`   VARCHAR(50)  NOT NULL COMMENT '标签域',
  `level1`   VARCHAR(100) DEFAULT NULL,
  `level2`   VARCHAR(100) DEFAULT NULL,
  `level3`   VARCHAR(100) DEFAULT NULL,
  `level4`   VARCHAR(100) DEFAULT NULL,
  `tag_path` VARCHAR(500) NOT NULL COMMENT '全路径/连接',
  `tag_rule` VARCHAR(1000) DEFAULT NULL COMMENT '打标规则说明',
  `method`   VARCHAR(20)  NOT NULL DEFAULT 'llm' COMMENT '打标方式 rule/map/llm',
  `status`   CHAR(1) DEFAULT '0' COMMENT '0正常1停用',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `uk_code` (`tag_code`),
  UNIQUE KEY `uk_path` (`tag_path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='警情标签字典(新版四级)';

CREATE TABLE IF NOT EXISTS `jq_tag_result` (
  `id`      BIGINT NOT NULL AUTO_INCREMENT,
  `fkdbh`   CHAR(27) NOT NULL COMMENT '反馈单编号',
  `jqqh`    VARCHAR(10) DEFAULT NULL COMMENT '警情区划',
  `bjsj`    DATETIME DEFAULT NULL COMMENT '报警时间',
  `tag_code` VARCHAR(32) NOT NULL COMMENT '标签编码',
  `tag_path` VARCHAR(500) NOT NULL COMMENT '标签全路径',
  `domain`  VARCHAR(50) NOT NULL COMMENT '标签域',
  `source`  VARCHAR(20) NOT NULL COMMENT 'llm/rule/map/manual',
  `confidence` DECIMAL(5,2) DEFAULT NULL COMMENT '置信度0-1',
  `evidence` VARCHAR(1000) DEFAULT NULL COMMENT '依据摘录',
  `cjqk`    LONGTEXT DEFAULT NULL COMMENT '处警情况原文',
  `batch`   VARCHAR(32) DEFAULT NULL COMMENT '批次',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `ajlbbh`  DECIMAL(10,0) DEFAULT NULL COMMENT '反馈案件类别编号',
  `ajlxbh`  VARCHAR(16) DEFAULT NULL COMMENT '反馈案件类型编号',
  `ajxlbh`  VARCHAR(32) DEFAULT NULL COMMENT '反馈案件细类编号',
  `fkdwdm`  VARCHAR(40) DEFAULT NULL COMMENT '反馈单位代码',
  `cljgdm`  VARCHAR(8) DEFAULT NULL COMMENT '处理结果代码',
  `czyj`    VARCHAR(200) DEFAULT NULL COMMENT '处置意见内容',
  PRIMARY KEY (`id`),
  KEY `idx_fkdbh` (`fkdbh`),
  KEY `idx_tagcode` (`tag_code`),
  KEY `idx_domain` (`domain`),
  KEY `idx_jq_tag_result_bjsj_fk` (`bjsj`, `fkdbh`),
  KEY `idx_jq_tag_result_fkdwdm` (`fkdwdm`),
  KEY `idx_jq_tag_result_ajlb` (`ajlbbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='警情打标结果表';

-- 已有库补字段/索引（可按需执行）
-- ALTER TABLE `jq_tag_result` ADD COLUMN `cjqk` LONGTEXT NULL COMMENT '处警情况原文' AFTER `evidence`;
-- ALTER TABLE `jq_tag_result` ADD COLUMN `ajlbbh` DECIMAL(10,0) NULL COMMENT '反馈案件类别编号';
-- ALTER TABLE `jq_tag_result` ADD COLUMN `ajlxbh` VARCHAR(16) NULL COMMENT '反馈案件类型编号';
-- ALTER TABLE `jq_tag_result` ADD COLUMN `ajxlbh` VARCHAR(32) NULL COMMENT '反馈案件细类编号';
-- ALTER TABLE `jq_tag_result` ADD COLUMN `fkdwdm` VARCHAR(40) NULL COMMENT '反馈单位代码';
-- ALTER TABLE `jq_tag_result` ADD INDEX `idx_jq_tag_result_bjsj_fk` (`bjsj`, `fkdbh`);
-- ALTER TABLE `jq_tag_result` ADD INDEX `idx_jq_tag_result_fkdwdm` (`fkdwdm`);
-- ALTER TABLE `jq_tag_result` ADD INDEX `idx_jq_tag_result_ajlb` (`ajlbbh`);
