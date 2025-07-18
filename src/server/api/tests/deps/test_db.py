import pytest
from sqlalchemy import select
from acontext_server.client.db import DB_CLIENT, init_database
from acontext_server.schema.orm import Project, Space, Session


@pytest.mark.asyncio
async def test_db():
    await init_database()

    await DB_CLIENT.health_check()
    print(DB_CLIENT.get_pool_status())
    async with DB_CLIENT.get_session_context() as session:
        p = Project(configs={"name": "Test Project"})
        session.add(p)
        s = Space(configs={"name": "asdasd"})
        s.project = p
        session.add(s)
        se = Session(configs={"name": "asdasd"})
        se.space = s
        session.add(se)
        await session.commit()

        pid = p.id
        sid = s.id
        seid = se.id

    async with DB_CLIENT.get_session_context() as session:
        # Use select() instead of session.query()
        se_result = await session.execute(select(Session).filter(Session.id == seid))
        se = se_result.scalar_one_or_none()
        print(se)
        p = Session.validate_data(configs=se.configs)
        print(p.unpack())

        s_result = await session.execute(select(Space).filter(Space.id == sid))
        s = s_result.scalar_one_or_none()
        print(s)

        p_result = await session.execute(select(Project).filter(Project.id == pid))
        p = p_result.scalar_one_or_none()
        print(p)
