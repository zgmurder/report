from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.community_org import CommunityOrgMapping
from app.repositories.community_org_repository import CommunityOrgRepository


def test_list_all_reads_community_org_mappings_table():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            CommunityOrgMapping(
                seed_key="k1",
                source_row=1,
                fasqdm="330782580140",
                fasqmc="佛堂稽亭村",
                xzqh="330782",
                gxdwdm="330782580000",
                mapping_name="稽亭村",
                station_name="佛堂派出所",
                org_type="gongjianwei",
                org_name="合作工作委员会",
                match_status="matched",
            )
        )
        db.commit()

        repository = CommunityOrgRepository(db)
        rows = repository.list_all()
        assert len(rows) == 1
        assert rows[0]["fasqdm"] == "330782580140"
        assert rows[0]["fasqmc"] == "佛堂稽亭村"
        assert rows[0]["station_name"] == "佛堂派出所"
        assert rows[0]["org_type"] == "gongjianwei"
        assert rows[0]["org_name"] == "合作工作委员会"
        assert "稽亭村" in rows[0]["aliases"]
        assert repository.count() == 1
