from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.domain.atomic_metric.community_org_map import fold_community_rows_by_org
from app.models.community_org import CommunityOrgMapping


def test_fold_community_rows_reads_mapping_from_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            CommunityOrgMapping(
                seed_key="seed-1",
                source_row=2,
                fasqdm="330782580140",
                fasqmc="佛堂稽亭村",
                xzqh="330782",
                station_name="佛堂派出所",
                gxdwdm="330782580000",
                org_type="gongjianwei",
                org_name="合作工作委员会",
                mapping_name="稽亭村",
                match_status="matched",
            )
        )
        db.commit()

        rows = fold_community_rows_by_org(
            db,
            [{"fasqdm": "", "fasqmc": "稽亭村", "today_cnt": 3, "mom_cnt": 2, "yoy_cnt": 1}],
            org_type="gongjianwei",
        )

    assert rows == [
        {
            "unit_code": "合作工作委员会",
            "unit_name": "合作工作委员会",
            "fasqdm": "合作工作委员会",
            "fasqmc": "合作工作委员会",
            "today_cnt": 3,
            "mom_cnt": 2,
            "yoy_cnt": 1,
            "total": 3,
        }
    ]
