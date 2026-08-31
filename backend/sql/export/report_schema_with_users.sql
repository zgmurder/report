-- 警情智能报告系统数据库导出
-- 内容：全部基础表结构；仅 sys_users 表包含账户数据
-- 不包含其他业务表数据、视图、存储过程、触发器和事件
-- 账户密码保持数据库中的哈希值，不包含数据库连接凭据

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

CREATE DATABASE IF NOT EXISTS `report` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `report`;

-- ----------------------------
-- Table structure for community_org_mappings
-- ----------------------------
DROP TABLE IF EXISTS `community_org_mappings`;
CREATE TABLE `community_org_mappings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `seed_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_row` int NOT NULL,
  `fasqdm` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fasqmc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `xzqh` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gxdwdm` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mapping_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `station_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `org_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `org_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `match_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_community_org_mapping_seed_key` (`seed_key`),
  KEY `ix_community_org_mapping_org` (`org_type`,`org_name`),
  KEY `ix_community_org_mapping_name_type` (`fasqmc`,`org_type`),
  KEY `ix_community_org_mapping_station_type` (`station_name`,`org_type`),
  KEY `ix_community_org_mapping_code_type` (`fasqdm`,`org_type`)
) ENGINE=InnoDB AUTO_INCREMENT=337 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for data_source_configs
-- ----------------------------
DROP TABLE IF EXISTS `data_source_configs`;
CREATE TABLE `data_source_configs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(160) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_json` json NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for departments
-- ----------------------------
DROP TABLE IF EXISTS `departments`;
CREATE TABLE `departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `parent_id` int DEFAULT NULL,
  `sort_order` int NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_departments_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for fkd_fkd
-- ----------------------------
DROP TABLE IF EXISTS `fkd_fkd`;
CREATE TABLE `fkd_fkd` (
  `afsq` text,
  `bjsj` datetime DEFAULT NULL,
  `cjqk` text NOT NULL,
  `fksj` datetime NOT NULL,
  `fkzj` decimal(10,0) DEFAULT NULL,
  `jdxz` varchar(64) DEFAULT NULL,
  `sdsq` varchar(64) DEFAULT NULL,
  `sdxq` varchar(64) DEFAULT NULL,
  `zrmj` varchar(32) DEFAULT NULL,
  `fkdbh` char(27) NOT NULL,
  `sdpcs` varchar(120) DEFAULT NULL,
  `ajlbbh` decimal(10,0) DEFAULT NULL,
  `ajlxbh` varchar(16) DEFAULT NULL,
  `ajxlbh` varchar(32) DEFAULT NULL,
  `fkdwdm` varchar(40) NOT NULL,
  `fkdwmc` varchar(120) NOT NULL,
  `jdxzmc` text,
  `zzfkbs` decimal(10,0) DEFAULT NULL,
  `txfkdwdm` varchar(40) NOT NULL,
  `txfkdwmc` varchar(120) NOT NULL,
  `jjdbh` char(19) DEFAULT NULL,
  `cjdbh` char(23) DEFAULT NULL,
  PRIMARY KEY (`fkdbh`),
  KEY `idx_fkd_fksj_fkdwdm` (`fksj`,`fkdwdm`),
  KEY `idx_fkd_bjsj_fkdwdm` (`bjsj`,`fkdwdm`),
  KEY `idx_fkd_bjsj_ajlbbh` (`bjsj`,`ajlbbh`),
  KEY `idx_fkd_bjsj_ajlxbh` (`bjsj`,`ajlxbh`),
  KEY `idx_fkd_bjsj_ajxlbh` (`bjsj`,`ajxlbh`),
  KEY `idx_fkd_jjdbh` (`jjdbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for intel_tag_package
-- ----------------------------
DROP TABLE IF EXISTS `intel_tag_package`;
CREATE TABLE `intel_tag_package` (
  `package_id` bigint NOT NULL AUTO_INCREMENT,
  `package_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tags_json` text COLLATE utf8mb4_unicode_ci,
  `preset_flag` char(1) COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `dept_id` bigint DEFAULT NULL,
  `create_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `create_time` datetime DEFAULT NULL,
  `update_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `update_time` datetime DEFAULT NULL,
  `remark` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`package_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for intel_tag_taxonomy
-- ----------------------------
DROP TABLE IF EXISTS `intel_tag_taxonomy`;
CREATE TABLE `intel_tag_taxonomy` (
  `tag_id` bigint NOT NULL AUTO_INCREMENT,
  `tag_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sheet_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `tag_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `extract_content` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sort_order` int DEFAULT '0',
  `status` char(1) COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `create_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `create_time` datetime DEFAULT NULL,
  `update_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `update_time` datetime DEFAULT NULL,
  `remark` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `tag_code` (`tag_code`)
) ENGINE=InnoDB AUTO_INCREMENT=600 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for jjd_jjd
-- ----------------------------
DROP TABLE IF EXISTS `jjd_jjd`;
CREATE TABLE `jjd_jjd` (
  `bjsj` datetime NOT NULL,
  `fkzj` decimal(10,0) DEFAULT NULL,
  `jjdbh` char(30) NOT NULL,
  `bjlbdm` decimal(10,0) DEFAULT NULL,
  `bjlxdm` decimal(10,0) DEFAULT NULL,
  `bjxldm` decimal(10,0) DEFAULT NULL,
  `gxdwdm` varchar(40) DEFAULT NULL,
  `jjdwdm` varchar(40) NOT NULL,
  `jjdwmc` varchar(120) NOT NULL,
  `insert_time` datetime DEFAULT NULL,
  `zjjdbh` char(19) DEFAULT NULL,
  `bjfsdm` decimal(10,0) DEFAULT NULL,
  `jjlxdm` decimal(10,0) DEFAULT NULL,
  `jjdcllxdm` decimal(10,0) DEFAULT NULL,
  `jjybh` varchar(32) DEFAULT NULL,
  `jjyxm` text,
  `jjtbh` varchar(20) DEFAULT NULL,
  `jjtip` varchar(23) DEFAULT NULL,
  `hrsj` datetime DEFAULT NULL,
  `hzsj` datetime DEFAULT NULL,
  `hrsc` decimal(10,0) DEFAULT NULL,
  `jjsc` decimal(10,0) DEFAULT NULL,
  `bjdh` varchar(20) DEFAULT NULL,
  `yhxm` varchar(150) DEFAULT NULL,
  `yhsfz` varchar(18) DEFAULT NULL,
  `yhdz` varchar(150) DEFAULT NULL,
  `jjlyh` varchar(50) DEFAULT NULL,
  `bjrxm` text,
  `bjrxb` decimal(10,0) DEFAULT NULL,
  `lxdh` varchar(50) DEFAULT NULL,
  `zzdw` varchar(120) DEFAULT NULL,
  `bm` decimal(10,0) DEFAULT NULL,
  `afsj` datetime DEFAULT NULL,
  `xzqh` char(6) DEFAULT NULL,
  `afdd` text,
  `bjp` varchar(30) DEFAULT NULL,
  `bjnr` text,
  `jqgjz` text,
  `jjdzt` varchar(5) DEFAULT NULL,
  `sjgxsj` datetime DEFAULT NULL,
  `jqjb` decimal(10,0) DEFAULT NULL,
  `dhdwjd` decimal(19,8) DEFAULT NULL,
  `dhdwwd` decimal(19,8) DEFAULT NULL,
  `fxdwjd` decimal(19,8) DEFAULT NULL,
  `fxdwwd` decimal(19,8) DEFAULT NULL,
  `jqhm` varchar(20) DEFAULT NULL,
  `xxaj` decimal(10,0) DEFAULT NULL,
  `afxzqh` char(6) DEFAULT NULL,
  `sjdwdm` text,
  `gxdwzt` decimal(10,0) DEFAULT NULL,
  `cjllbh` text,
  `cjlllbbh` text,
  `bjsdxq` decimal(10,0) DEFAULT NULL,
  `bjsdxs` decimal(10,0) DEFAULT NULL,
  `xsza` decimal(10,0) DEFAULT NULL,
  `bjsdfz` decimal(10,0) DEFAULT NULL,
  `rksj` datetime DEFAULT NULL,
  PRIMARY KEY (`jjdbh`),
  KEY `idx_jjd_bjsj_gxdwdm` (`bjsj`,`gxdwdm`),
  KEY `idx_jjd_bjlxdm_bjxldm` (`bjlxdm`,`bjxldm`),
  KEY `idx_jjd_bjsj_bjlbdm` (`bjsj`,`bjlbdm`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for jq-total-cf
-- ----------------------------
DROP TABLE IF EXISTS `jq-total-cf`;
CREATE TABLE `jq-total-cf` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tjsj` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ryxm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rysfz` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dhhm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pcsdm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pcsmc` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjdbh` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bjsj` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bjcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for jq-total-day
-- ----------------------------
DROP TABLE IF EXISTS `jq-total-day`;
CREATE TABLE `jq-total-day` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rq` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` bigint DEFAULT NULL,
  `drjqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `zr_pcsjjzs` bigint DEFAULT NULL,
  `zr_jqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qr_pcsjjzs` bigint DEFAULT NULL,
  `qr_jqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `q3r_pcsjjzs` bigint DEFAULT NULL,
  `q4r_pcsjjzs` bigint DEFAULT NULL,
  `q5r_pcsjjzs` bigint DEFAULT NULL,
  `q6r_pcsjjzs` bigint DEFAULT NULL,
  `q7r_pcsjjzs` bigint DEFAULT NULL,
  `gwyxzb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tjsj` datetime DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for jq-total-qk
-- ----------------------------
DROP TABLE IF EXISTS `jq-total-qk`;
CREATE TABLE `jq-total-qk` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rq` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tjwdbq` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tsrybq` text COLLATE utf8mb4_unicode_ci,
  `ryxm` text COLLATE utf8mb4_unicode_ci,
  `rysfz` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjdbh` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bjsj` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jqsl` text COLLATE utf8mb4_unicode_ci,
  `tjsj` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_status` char(1) COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `handle_remark` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `handle_time` datetime DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for jq-total-week
-- ----------------------------
DROP TABLE IF EXISTS `jq-total-week`;
CREATE TABLE `jq-total-week` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `week_start` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `week_end` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dzjqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sz_pcsjjzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sz_jqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ssz_pcsjjzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ssz_jqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sssz_pcsjjzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ssssz_pcsjjzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `q4zjqzs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `q4zjqpjs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gwyxzb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tjsj` datetime DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for jq_person_tag_result
-- ----------------------------
DROP TABLE IF EXISTS `jq_person_tag_result`;
CREATE TABLE `jq_person_tag_result` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fkdbh` char(27) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `jjdbh` varchar(27) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cjdbh` varchar(27) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bjsj` datetime DEFAULT NULL,
  `fkdwdm` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jqqh` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `person_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `person_role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tag_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tag_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tag_domain` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'person',
  `source` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `enrich_status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `enrich_batch` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `evidence` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `batch` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_fkdbh_role_idno_tag` (`fkdbh`,`person_role`,`id_no`,`tag_path`(191)) USING BTREE,
  KEY `idx_bjsj_role` (`bjsj`,`person_role`) USING BTREE,
  KEY `idx_fkdbh` (`fkdbh`) USING BTREE,
  KEY `idx_idno` (`id_no`) USING BTREE,
  KEY `idx_tag_path` (`tag_path`(191)) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=896 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for jq_person_zj_tags
-- ----------------------------
DROP TABLE IF EXISTS `jq_person_zj_tags`;
CREATE TABLE `jq_person_zj_tags` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `id_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '身份证号',
  `tag_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '治安标签代码',
  `tag_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '治安标签名称',
  `source` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'zj-api' COMMENT '来源',
  `batch` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_idno_tag` (`id_no`,`tag_code`) USING BTREE,
  KEY `idx_zj_idno` (`id_no`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7699 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='人治安标签(独立接口采集)';

-- ----------------------------
-- Table structure for jq_tag_result
-- ----------------------------
DROP TABLE IF EXISTS `jq_tag_result`;
CREATE TABLE `jq_tag_result` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fkdbh` char(27) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '反馈单编号',
  `jqqh` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '警情区划',
  `bjsj` datetime DEFAULT NULL COMMENT '报警时间',
  `tag_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签编码',
  `tag_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签全路径',
  `domain` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签域',
  `source` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'llm/rule/map/manual',
  `confidence` decimal(5,2) DEFAULT NULL COMMENT '置信度0-1',
  `evidence` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '依据摘录',
  `cjqk` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '出警情况原文',
  `batch` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '批次',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `ajlbbh` decimal(10,0) DEFAULT NULL COMMENT '官方案件类别编号',
  `ajlxbh` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '官方案件类型编号',
  `ajxlbh` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '官方案件细类编号',
  `fkdwdm` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '反馈单位代码',
  `cljgdm` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处理结果代码',
  `czyj` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处置意见代码',
  PRIMARY KEY (`id`),
  KEY `idx_domain` (`domain`) USING BTREE,
  KEY `idx_fkdbh` (`fkdbh`) USING BTREE,
  KEY `idx_jq_tag_result_bjsj_fk` (`bjsj`,`fkdbh`) USING BTREE,
  KEY `idx_tagcode` (`tag_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3285 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='警情打标结果表';

-- ----------------------------
-- Table structure for jz_dept
-- ----------------------------
DROP TABLE IF EXISTS `jz_dept`;
CREATE TABLE `jz_dept` (
  `dept_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '机构编号',
  `parent_dept_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '机构上级编号',
  `short_dept_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '机构简称',
  `detail_dept_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '机构详称',
  `area_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行政区划',
  `id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '警综id',
  `parent_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '警综父id',
  `centre_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '大数据中心id',
  `centre_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '大数据中心code',
  `dept_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '部门类型 1-本级中心 2-协同部门',
  `dept_category` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '部门类别 1-正式部门 2-虚拟部门',
  `approve_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '审批类型 1所队审批、2-区县局审批 3-支队审批 4-市局审批 5-总队审批',
  `sort` double(4,1) DEFAULT NULL COMMENT '排序',
  `like_right_dept_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '右模糊查询截取部门code，例如：330300000000，温州市局截取为3303，使用查询3303%',
  `level` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '所属层级 1-省市级大数据中心 2-区县大数据中心 3-协同部门',
  `is_show` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '1' COMMENT '是否展示 0-否 1-是',
  `create_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '创建人',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '更新人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '0' COMMENT '删除标志',
  `sys_dept_id` bigint DEFAULT NULL,
  `ancestors` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '祖级机构编号列表',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '0' COMMENT '部门状态',
  PRIMARY KEY (`dept_code`),
  KEY `idx_dept_code` (`dept_code`) USING BTREE,
  KEY `idx_parent_dept_code` (`parent_dept_code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for mx_pcs_day_hb_30
-- ----------------------------
DROP TABLE IF EXISTS `mx_pcs_day_hb_30`;
CREATE TABLE `mx_pcs_day_hb_30` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `rq` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` bigint DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` bigint DEFAULT NULL,
  `drjqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `zr_pcsjjzs` bigint DEFAULT NULL,
  `tjsj` bigint DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for mx_pcs_month_hb_30
-- ----------------------------
DROP TABLE IF EXISTS `mx_pcs_month_hb_30`;
CREATE TABLE `mx_pcs_month_hb_30` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` bigint DEFAULT NULL,
  `month_start` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `month_end` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` bigint DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` bigint DEFAULT NULL,
  `dyjqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sy_pcsjjzs` bigint DEFAULT NULL,
  `tjsj` bigint DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for mx_pcs_month_tb_30
-- ----------------------------
DROP TABLE IF EXISTS `mx_pcs_month_tb_30`;
CREATE TABLE `mx_pcs_month_tb_30` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `lx` bigint DEFAULT NULL,
  `month_start` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `month_end` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` bigint DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` bigint DEFAULT NULL,
  `dyjqtb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sy_jjzs` bigint DEFAULT NULL,
  `tjsj` bigint DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for mx_pcs_week_hb_30
-- ----------------------------
DROP TABLE IF EXISTS `mx_pcs_week_hb_30`;
CREATE TABLE `mx_pcs_week_hb_30` (
  `xlbh` bigint NOT NULL AUTO_INCREMENT,
  `week_start` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `week_end` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sdpcsdm` bigint DEFAULT NULL,
  `sdpcs` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ajlb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jjzs` bigint DEFAULT NULL,
  `dzjqhb` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sz_pcsjjzs` bigint DEFAULT NULL,
  `tjsj` bigint DEFAULT NULL,
  PRIMARY KEY (`xlbh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for report_documents
-- ----------------------------
DROP TABLE IF EXISTS `report_documents`;
CREATE TABLE `report_documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `report_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `folder_id` int DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_query` json NOT NULL,
  `generation_key` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `editor_config` json DEFAULT NULL,
  `content_json` json DEFAULT NULL,
  `draft_json` json DEFAULT NULL,
  `html_snapshot` longtext COLLATE utf8mb4_unicode_ci,
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_report_generation_owner` (`created_by`,`generation_key`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for report_folders
-- ----------------------------
DROP TABLE IF EXISTS `report_folders`;
CREATE TABLE `report_folders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `parent_id` int DEFAULT NULL,
  `sort_order` int NOT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for report_templates
-- ----------------------------
DROP TABLE IF EXISTS `report_templates`;
CREATE TABLE `report_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_json` json NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_size` int DEFAULT NULL,
  `mime_type` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for stat_components
-- ----------------------------
DROP TABLE IF EXISTS `stat_components`;
CREATE TABLE `stat_components` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(160) COLLATE utf8mb4_unicode_ci NOT NULL,
  `component_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_source` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `usage` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_json` json NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for statistics_dictionary_exclusions
-- ----------------------------
DROP TABLE IF EXISTS `statistics_dictionary_exclusions`;
CREATE TABLE `statistics_dictionary_exclusions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `source` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `level` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` int NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_statistics_dictionary_exclusion_user` (`created_by`,`source`,`level`,`code`),
  KEY `ix_statistics_dictionary_exclusions_level` (`level`),
  KEY `ix_statistics_dictionary_exclusions_source` (`source`)
) ENGINE=InnoDB AUTO_INCREMENT=17683 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for sys_users
-- ----------------------------
DROP TABLE IF EXISTS `sys_users`;
CREATE TABLE `sys_users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `roles` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `unit_code` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_users_username` (`username`),
  KEY `ix_sys_users_unit_code` (`unit_code`),
  KEY `ix_sys_users_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for tag_dict_v2
-- ----------------------------
DROP TABLE IF EXISTS `tag_dict_v2`;
CREATE TABLE `tag_dict_v2` (
  `tag_id` bigint NOT NULL AUTO_INCREMENT,
  `tag_code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `domain` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `level1` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level3` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level4` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tag_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tag_rule` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `method` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'llm',
  `status` char(1) COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `create_time` datetime DEFAULT NULL,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `tag_code` (`tag_code`),
  UNIQUE KEY `tag_path` (`tag_path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for zd_bjlbdm
-- ----------------------------
DROP TABLE IF EXISTS `zd_bjlbdm`;
CREATE TABLE `zd_bjlbdm` (
  `bjlbdm` decimal(10,0) DEFAULT NULL COMMENT '报警类别代码',
  `bjlbmc` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '报警类别名称',
  `sm` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '说明',
  `pxh` decimal(10,0) DEFAULT NULL COMMENT '排序号',
  `ymlx` varchar(4) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT 'cs接警的动态页面类型',
  `bh` decimal(10,0) NOT NULL COMMENT '编号',
  `fkymlx` varchar(6) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '反馈页面类型',
  PRIMARY KEY (`bh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC COMMENT='报警类别代码表';

-- ----------------------------
-- Table structure for zd_bjlxdm
-- ----------------------------
DROP TABLE IF EXISTS `zd_bjlxdm`;
CREATE TABLE `zd_bjlxdm` (
  `bjlxdm` decimal(10,0) DEFAULT NULL COMMENT '报警类型代码',
  `bjlxmc` varchar(96) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '报警类型名称',
  `sm` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '说明',
  `sfyjjq` varchar(2) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '是否一级警情',
  `jqdjdm` varchar(8) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '警情等级代码',
  `ms` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '描述',
  `pxh` decimal(10,0) DEFAULT NULL COMMENT '排序号',
  `jqdjxs` decimal(10,0) DEFAULT NULL COMMENT '1，表示不显示（一般警情）；2，显示在紧急警情里；3，显示在危机警情里',
  `bjlb` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '与报警类别关联用',
  `ymlx` varchar(4) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT 'cs接警的动态页面类型',
  `bh` decimal(10,0) NOT NULL COMMENT '编号',
  `fkymlx` varchar(6) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '反馈单的页面类型',
  `jjddts` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '接警调度提示（接警界面)',
  `czts` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '处置提示(发派出所)',
  PRIMARY KEY (`bh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC COMMENT='报警类型代码表';

-- ----------------------------
-- Table structure for zd_bjxldm
-- ----------------------------
DROP TABLE IF EXISTS `zd_bjxldm`;
CREATE TABLE `zd_bjxldm` (
  `bjxldm` decimal(10,0) NOT NULL COMMENT '报警细类代码',
  `bjxlmc` varchar(96) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '报警细类名称',
  `sm` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT '说明',
  `pxh` decimal(10,0) DEFAULT NULL COMMENT '排序号',
  `bjlx` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '报警类型',
  PRIMARY KEY (`bjxldm`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC COMMENT='报警细类代码表';

-- ----------------------------
-- Table structure for zd_fasqdm
-- ----------------------------
DROP TABLE IF EXISTS `zd_fasqdm`;
CREATE TABLE `zd_fasqdm` (
  `fasqdm` bigint NOT NULL COMMENT '发案社区代码',
  `fasqmc` varchar(64) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '发案社区名称',
  `xzqh` char(6) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '行政区划',
  `gxdwdm` varchar(40) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '管辖单位代码',
  `scbz` decimal(10,0) DEFAULT NULL COMMENT '删除标志，0：未删除；1：已删除',
  PRIMARY KEY (`fasqdm`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC COMMENT='发案社区代码（引用打防控）';

-- ----------------------------
-- Table structure for zd_fklbdm
-- ----------------------------
DROP TABLE IF EXISTS `zd_fklbdm`;
CREATE TABLE `zd_fklbdm` (
  `code` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '反馈类别代码',
  `name` varchar(48) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '反馈类别名称',
  `sm` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '说明',
  `bh` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '编号',
  PRIMARY KEY (`bh`),
  KEY `idx_zd_fklbdm_code` (`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='反馈类别代码表';

-- ----------------------------
-- Table structure for zd_fklxdm
-- ----------------------------
DROP TABLE IF EXISTS `zd_fklxdm`;
CREATE TABLE `zd_fklxdm` (
  `code` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '反馈类型代码',
  `name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '反馈类型名称',
  `sm` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '说明',
  `pxh` int DEFAULT '0' COMMENT '排序号',
  `fklbdm` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '与反馈类别对应，多个类别用逗号分隔',
  `jqdjxs` tinyint DEFAULT NULL COMMENT '1 不显示一般警情；2 紧急警情；3 危机警情',
  PRIMARY KEY (`code`),
  KEY `idx_zd_fklxdm_fklbdm` (`fklbdm`) USING BTREE,
  KEY `idx_zd_fklxdm_pxh` (`pxh`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='反馈类型代码表';

-- ----------------------------
-- Table structure for zd_fkxldm
-- ----------------------------
DROP TABLE IF EXISTS `zd_fkxldm`;
CREATE TABLE `zd_fkxldm` (
  `code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '反馈细类代码',
  `name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '反馈细类名称',
  `sm` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '说明',
  `pxh` int DEFAULT '0' COMMENT '排序号',
  `fklxdm` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '与反馈类型对应',
  PRIMARY KEY (`code`),
  KEY `idx_zd_fkxldm_fklxdm` (`fklxdm`) USING BTREE,
  KEY `idx_zd_fkxldm_pxh` (`pxh`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='反馈细类代码表';

-- ----------------------------
-- Account data for sys_users only
-- Password values remain hashed exactly as stored in the database
-- ----------------------------
LOCK TABLES `sys_users` WRITE;
INSERT INTO `sys_users` (`id`, `username`, `password_hash`, `display_name`, `roles`, `unit_code`, `status`, `created_at`, `updated_at`) VALUES
  (1, 'admin', 'pbkdf2_sha256$120000$e0df3d4dbb19e1c8db0cd109a65bcf8a$6fce11c081bdcb645f64d591f2daf8a38339907de3345c6f3247b1282fc1c738', '系统管理员', 'admin', '330782000000', 'enabled', '2026-08-29 11:40:24', '2026-08-29 11:40:24'),
  (6, 'pcs_51', 'pbkdf2_sha256$120000$14e228de004cf44f78ab517e6e492cd9$8a2c395517cf655116f6e0cb4d98c1c62dda204ebc1ca75e66d35bda1d2ff10a', '稠城派出所', 'user', '330782510000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (7, 'pcs_52', 'pbkdf2_sha256$120000$44fb1e9b117571981020eb215a8be7e0$59f2feb2bb094749eda74c3f5d96cc39cab1680a469245be9f3b2044a20a4ad1', '稠北派出所', 'user', '330782520000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (8, 'pcs_53', 'pbkdf2_sha256$120000$1dc970501880ae4c2e11cd3374d909da$0e44e6954c47219862ffab34b6297ff8a89d0e24611c554eeefb634eb9366397', '江东派出所', 'user', '330782530000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (9, 'pcs_54', 'pbkdf2_sha256$120000$4782e5ca7547d96714701adf9a9dd105$2e82e1a2fb23262b7701bebc38cb0016659f1c723954f6c4580c589c86b3d357', '稠江派出所', 'user', '330782540000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (10, 'pcs_55', 'pbkdf2_sha256$120000$672853635726fc454ed84c6534b46944$4ff3d620a89bcde4ae6c1ae126993d7a901f32bab295808be09ddb1e1884e1d8', '北苑派出所', 'user', '330782550000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (11, 'pcs_56', 'pbkdf2_sha256$120000$cbd4fb4682ee9b50b856959bed1bb38c$4cb508b0ac0583299d7bcf55d364d4d4223be44ef3c829f02b3fde4c94a2e5c2', '后宅派出所', 'user', '330782560000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (12, 'pcs_57', 'pbkdf2_sha256$120000$1fd52c766d53e2e97ca9002ee06bc829$0c35924068d669f34922d6757f2ee1c28861de3977e926693f7dcc5828d95ec4', '商城派出所', 'user', '330782570000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (13, 'pcs_58', 'pbkdf2_sha256$120000$50d0af1c8b858be7464f4a88c84cac63$a2ecb77468b1cb8e220fcb0e9ac80ef5b4e8c33a442f1b27ec11abdb420673d4', '佛堂派出所', 'user', '330782580000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (14, 'pcs_59', 'pbkdf2_sha256$120000$1262d723fef28e6317392689bba0ac88$d80c93e435cde0c96783a0e6abe72ce87aaa7eab4ce6e329742aa1653a9f5954', '赤岸派出所', 'user', '330782590000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (15, 'pcs_61', 'pbkdf2_sha256$120000$9b188ac6f7ce6e69808660d891a3925b$701fe8c247ec892e42b4eeba065b4cd78b53773a9ecdd455162812753f61879b', '上溪派出所', 'user', '330782610000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (16, 'pcs_62', 'pbkdf2_sha256$120000$7797c008fec4586a6f9fbe30d9938741$3c527854c17fce10ad92c3560b939cac08ec5c969d1327d356e86e48a3744812', '城西派出所', 'user', '330782620000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (17, 'pcs_63', 'pbkdf2_sha256$120000$cd681ec2bbfc3eb8f825d43ac0fcdf0c$58e87d72f6670a828c127907db3a9e51d9efcfbfff232d80f6e352e7b9e08bb1', '苏溪派出所', 'user', '330782630000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (18, 'pcs_64', 'pbkdf2_sha256$120000$0e362649ef2dab86519b7403aecc64db$85e508b1102f8e5a7939594614e41811f43ffae97914639b2105c4be38672277', '大陈派出所', 'user', '330782640000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (19, 'pcs_65', 'pbkdf2_sha256$120000$6f9b388b04a0e6ef798ea0582ebafce7$46121e046a2dfab95a1411837dd6805a4581cd020995e4248646e0706a1b2a4b', '廿三里派出所', 'user', '330782650000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (20, 'pcs_67', 'pbkdf2_sha256$120000$7e06e6817ef98328fd0c4bf2256d5f13$bef0f0ae5f8a18492a8c7be4a9591cb4e9663ca8c96c91bf7e5a49dc130f2509', '义亭派出所', 'user', '330782670000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (21, 'pcs_70', 'pbkdf2_sha256$120000$9de91bc605b5c5fb1d72d5e103f8dc05$040de06a33e9703b5c6536a78d8899f2b35a91d0d5755f27a4460d94a5f73921', '轨道交通派出所', 'user', '330782700000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (22, 'pcs_72', 'pbkdf2_sha256$120000$38c634cc0c284bb3f2cb983243e4e587$89a4a328826d381c9922f151ab6eec2d999ce5811f29ce28c4cb3793188e674d', '交通派出所', 'user', '330782720000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (23, 'pcs_74', 'pbkdf2_sha256$120000$3335f6b4d809fedebfa4a6193ee26ffb$6d863a7d7221664af8ff9139f1ea8cf5efd929bc2eba5498e68461d7440f807f', '福田派出所', 'user', '330782740000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02'),
  (24, 'pcs_75', 'pbkdf2_sha256$120000$a3b2959edcbe3ab3a7c5292a185ba283$881a2df8bcd5f38fa02f6ab53720a078ad4a25e9edcf7aeb9aa0fe45a62ba46e', '站前派出所', 'user', '330782750000', 'enabled', '2026-08-30 22:13:02', '2026-08-30 22:13:02');
UNLOCK TABLES;

SET FOREIGN_KEY_CHECKS = 1;
