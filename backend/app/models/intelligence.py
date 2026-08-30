"""研判/预警/打标相关 ORM（表名与旧库一致）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, Integer, Numeric, String, Text

from app.core.database import Base


class IntelTagPackage(Base):
    __tablename__ = "intel_tag_package"

    package_id = Column(BigInteger, primary_key=True, autoincrement=True)
    package_name = Column(String(200), nullable=False)
    tags_json = Column(Text, nullable=True)
    preset_flag = Column(CHAR(1), server_default="0")
    dept_id = Column(BigInteger, nullable=True)
    create_by = Column(String(64), server_default="")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    remark = Column(String(500), nullable=True)


class IntelTagTaxonomy(Base):
    __tablename__ = "intel_tag_taxonomy"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_code = Column(String(64), nullable=False, unique=True)
    sheet_name = Column(String(100), nullable=False)
    category_name = Column(String(200), server_default="")
    tag_name = Column(String(200), nullable=False)
    extract_content = Column(String(2000), nullable=True)
    description = Column(String(2000), nullable=True)
    sort_order = Column(Integer, server_default="0")
    status = Column(CHAR(1), server_default="0")
    create_by = Column(String(64), server_default="")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    remark = Column(String(500), nullable=True)


class IntelSuspectWarning(Base):
    __tablename__ = "jq-total-qk"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(String(500), nullable=True)
    rq = Column(String(500), nullable=True)
    sdpcsdm = Column(String(500), nullable=True)
    sdpcs = Column(String(500), nullable=True)
    tjwdbq = Column(String(500), nullable=True)
    tsrybq = Column(Text, nullable=True)
    ryxm = Column(Text, nullable=True)
    rysfz = Column(String(500), nullable=True)
    jjdbh = Column(String(500), nullable=True)
    bjsj = Column(String(500), nullable=True)
    jqsl = Column(Text, nullable=True)
    tjsj = Column(String(500), nullable=True)
    handle_status = Column(CHAR(1), server_default="0")
    handle_remark = Column(String(500), nullable=True)
    handle_by = Column(String(64), server_default="")
    handle_time = Column(DateTime, nullable=True)


class IntelWeekRiseWarning(Base):
    __tablename__ = "jq-total-week"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(String(500), nullable=True)
    week_start = Column(String(500), nullable=True)
    week_end = Column(String(500), nullable=True)
    sdpcsdm = Column(String(500), nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(String(500), nullable=True)
    dzjqhb = Column(String(500), nullable=True)
    sz_pcsjjzs = Column(String(500), nullable=True)
    sz_jqhb = Column(String(500), nullable=True)
    ssz_pcsjjzs = Column(String(500), nullable=True)
    ssz_jqhb = Column(String(500), nullable=True)
    sssz_pcsjjzs = Column(String(500), nullable=True)
    ssssz_pcsjjzs = Column(String(500), nullable=True)
    q4zjqzs = Column(String(500), nullable=True)
    q4zjqpjs = Column(String(500), nullable=True)
    gwyxzb = Column(String(500), nullable=True)
    tjsj = Column(DateTime, nullable=True)


class IntelDayRiseWarning(Base):
    __tablename__ = "jq-total-day"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(String(500), nullable=True)
    rq = Column(String(500), nullable=True)
    sdpcsdm = Column(String(500), nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(BigInteger, nullable=True)
    drjqhb = Column(String(500), nullable=True)
    zr_pcsjjzs = Column(BigInteger, nullable=True)
    zr_jqhb = Column(String(500), nullable=True)
    qr_pcsjjzs = Column(BigInteger, nullable=True)
    qr_jqhb = Column(String(500), nullable=True)
    q3r_pcsjjzs = Column(BigInteger, nullable=True)
    q4r_pcsjjzs = Column(BigInteger, nullable=True)
    q5r_pcsjjzs = Column(BigInteger, nullable=True)
    q6r_pcsjjzs = Column(BigInteger, nullable=True)
    q7r_pcsjjzs = Column(BigInteger, nullable=True)
    gwyxzb = Column(String(500), nullable=True)
    tjsj = Column(DateTime, nullable=True)


class IntelRepeatWarning(Base):
    __tablename__ = "jq-total-cf"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(String(500), nullable=True)
    tjsj = Column(String(500), nullable=True)
    ryxm = Column(String(500), nullable=True)
    rysfz = Column(String(500), nullable=True)
    dhhm = Column(String(500), nullable=True)
    pcsdm = Column(String(500), nullable=True)
    pcsmc = Column(String(500), nullable=True)
    jjdbh = Column(String(500), nullable=True)
    bjsj = Column(String(500), nullable=True)
    bjcs = Column(String(500), nullable=True)


class IntelPcsDayHb30Warning(Base):
    __tablename__ = "mx_pcs_day_hb_30"

    xlbh = Column(BigInteger, primary_key=True)
    rq = Column(String(500), nullable=True)
    sdpcsdm = Column(BigInteger, nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(BigInteger, nullable=True)
    drjqhb = Column(String(500), nullable=True)
    zr_pcsjjzs = Column(BigInteger, nullable=True)
    tjsj = Column(BigInteger, nullable=True)


class IntelPcsWeekHb30Warning(Base):
    __tablename__ = "mx_pcs_week_hb_30"

    xlbh = Column(BigInteger, primary_key=True)
    week_start = Column(String(500), nullable=True)
    week_end = Column(String(500), nullable=True)
    sdpcsdm = Column(BigInteger, nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(BigInteger, nullable=True)
    dzjqhb = Column(String(500), nullable=True)
    sz_pcsjjzs = Column(BigInteger, nullable=True)
    tjsj = Column(BigInteger, nullable=True)


class IntelPcsMonthHb30Warning(Base):
    __tablename__ = "mx_pcs_month_hb_30"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(BigInteger, nullable=True)
    month_start = Column(String(500), nullable=True)
    month_end = Column(String(500), nullable=True)
    sdpcsdm = Column(BigInteger, nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(BigInteger, nullable=True)
    dyjqhb = Column(String(500), nullable=True)
    sy_pcsjjzs = Column(BigInteger, nullable=True)
    tjsj = Column(BigInteger, nullable=True)


class IntelPcsMonthTb30Warning(Base):
    __tablename__ = "mx_pcs_month_tb_30"

    xlbh = Column(BigInteger, primary_key=True)
    lx = Column(BigInteger, nullable=True)
    month_start = Column(String(500), nullable=True)
    month_end = Column(String(500), nullable=True)
    sdpcsdm = Column(BigInteger, nullable=True)
    sdpcs = Column(String(500), nullable=True)
    ajlb = Column(String(500), nullable=True)
    jjzs = Column(BigInteger, nullable=True)
    dyjqtb = Column(String(500), nullable=True)
    sy_jjzs = Column(BigInteger, nullable=True)
    tjsj = Column(BigInteger, nullable=True)


class TagDictV2(Base):
    __tablename__ = "tag_dict_v2"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_code = Column(String(32), nullable=False, unique=True)
    domain = Column(String(50), nullable=False)
    level1 = Column(String(100), nullable=True)
    level2 = Column(String(100), nullable=True)
    level3 = Column(String(100), nullable=True)
    level4 = Column(String(100), nullable=True)
    tag_path = Column(String(500), nullable=False, unique=True)
    tag_rule = Column(String(1000), nullable=True)
    method = Column(String(20), nullable=False, server_default="llm")
    status = Column(CHAR(1), server_default="0")
    create_time = Column(DateTime, default=datetime.now)


class JqTagResult(Base):
    __tablename__ = "jq_tag_result"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fkdbh = Column(String(27), nullable=False)
    jqqh = Column(String(10), nullable=True)
    bjsj = Column(DateTime, nullable=True)
    tag_code = Column(String(32), nullable=False)
    tag_path = Column(String(500), nullable=False)
    domain = Column(String(50), nullable=False)
    source = Column(String(20), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=True)
    evidence = Column(String(1000), nullable=True)
    cjqk = Column(Text, nullable=True)
    batch = Column(String(32), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    ajlbbh = Column(Numeric(10, 0), nullable=True)
    ajlxbh = Column(String(16), nullable=True)
    ajxlbh = Column(String(32), nullable=True)
    fkdwdm = Column(String(40), nullable=True)
    cljgdm = Column(String(8), nullable=True)
    czyj = Column(String(200), nullable=True)


class JqPersonTagResult(Base):
    __tablename__ = "jq_person_tag_result"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fkdbh = Column(String(27), nullable=False)
    jjdbh = Column(String(27), nullable=True)
    cjdbh = Column(String(27), nullable=True)
    bjsj = Column(DateTime, nullable=True)
    fkdwdm = Column(String(40), nullable=True)
    jqqh = Column(String(10), nullable=True)
    id_no = Column(String(32), nullable=True)
    person_name = Column(String(50), nullable=True)
    phone = Column(String(30), nullable=True)
    person_role = Column(String(20), nullable=False)
    tag_code = Column(String(32), nullable=True)
    tag_path = Column(String(500), nullable=True)
    source = Column(String(20), nullable=False, server_default="extract")
    enrich_status = Column(CHAR(1), server_default="0")
    evidence = Column(String(1000), nullable=True)
    batch = Column(String(32), nullable=True)
    create_time = Column(DateTime, default=datetime.now)


class JqPersonZjTags(Base):
    __tablename__ = "jq_person_zj_tags"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    id_no = Column(String(32), nullable=True)
    tag_code = Column(String(64), nullable=True)
    tag_name = Column(String(128), nullable=True)
    source = Column(String(32), nullable=True, server_default="zj-api")
    batch = Column(String(64), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
